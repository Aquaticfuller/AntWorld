#include "segmented_analytics.hpp"
#include <algorithm>

namespace antworld::storage::detail {
namespace {
bool geometry_edit(FactKind kind) { return kind==FactKind::SoilExcavated || kind==FactKind::SoilFilled; }

struct GeometryEvidence {
    GeometryEdit edit;
    GeometrySnapshot geometry;
};

GeometryEvidence geometry_evidence(sqlite3* db,const WorldEvent& event) {
    Statement q(db,"SELECT edit,volume,dry,water FROM geometry_evidence WHERE world=? AND event=?");
    q.text(1,event.world.str()); q.u64(2,event.id.value);
    require(q.row(),"missing derived soil evidence");
    GeometryEvidence result{};
    result.edit.id={q.u64(0)};
    result.edit.event=event.id;
    result.edit.volume_q3=q.u64(1);
    result.geometry.configured=true;
    result.geometry.config.dry_ug_per_q3=q.u64(2);
    result.geometry.config.water_ug_per_q3=q.u64(3);
    return result;
}

const AntState& ant_at(std::span<const AntState> ants,EntityId id) {
    const auto it=std::lower_bound(ants.begin(),ants.end(),id,
        [](const auto& ant,EntityId key) { return ant.id<key; });
    require(it!=ants.end() && it->id==id,"individual index lacks authoritative identity");
    return *it;
}

std::int64_t minute(SimTime time) { return time.milliseconds-time.milliseconds%bucket_ms; }
void bucket_key(Statement& q,WorldId world,const BucketKey& key) {
    q.text(1,world.str()); q.u64(2,std::get<0>(key).value);
    q.number(3,static_cast<std::int64_t>(std::get<1>(key)));
    q.number(4,std::get<2>(key));
}
} // namespace

EntityId related_entity(const WorldEvent& fact) {
    if (fact.kind==FactKind::BiologicalObservation) return fact.observation.target;
    if (fact.kind==FactKind::NutritionTransferred || fact.kind==FactKind::AntBorn || fact.kind==FactKind::BroodMoved)
        return {fact.payload};
    return {};
}

HistoryRecord segmented_record(sqlite3* db,const WorldEvent& fact) {
    const auto edit=geometry_edit(fact.kind)?geometry_evidence(db,fact).edit.id:GeometryEditId{};
    const bool soil=fact.kind>=FactKind::SoilExcavated && fact.kind<=FactKind::SoilFilled;
    return {fact,related_entity(fact),edit,{soil?fact.payload:0}};
}

std::vector<MetricValue> segmented_contributions(sqlite3* db,const WorldEvent& fact) {
    if (!geometry_edit(fact.kind)) return contributions(fact,{});
    const auto evidence=geometry_evidence(db,fact);
    return contributions(fact,evidence.geometry,&evidence.edit);
}

const GeometryEdit* find_edit(std::span<const GeometryEdit> edits,EventId id) {
    const auto it=std::lower_bound(edits.begin(),edits.end(),id,
        [](const auto& edit,EventId key) { return edit.event<key; });
    return it!=edits.end() && it->event==id?&*it:nullptr;
}

void HistoryIndex::record(const WorldEvent& fact,const GeometrySnapshot& geometry,const GeometryEdit* edit) {
    if (fact.actor.value) {
        auto& delta=individuals[fact.actor];
        delta.last=fact.id;
        if (fact.kind==FactKind::AntSeeded || fact.kind==FactKind::AntBorn) {
            require(!delta.origin,"duplicate derived individual origin");
            delta.origin=fact;
            delta.stage=fact.stage;
        }
        if (fact.kind==FactKind::StageChanged || fact.kind==FactKind::AntDied) delta.stage=fact.stage;
        if (fact.kind==FactKind::AntDied) {
            delta.death=fact.id; delta.died_at=fact.time; delta.death_cause=fact.payload;
        }
    }
    if (const auto related=related_entity(fact);related.value) individuals[related].last=fact.id;
    for (const auto& value:contributions(fact,geometry,edit))
        accumulate(buckets[{value.owner,value.metric,minute(fact.time)}],value.value,fact.id);
}

void HistoryIndex::observe(const Observation& observation) {
    for (const auto& value:observation.values)
        accumulate(buckets[{value.owner,value.metric,minute(observation.time)}],value.value,observation.cursor);
}

void put_geometry(sqlite3* db,WorldId world,const GeometrySnapshot& geometry,
                  std::span<const GeometryEdit> edits,EventId after) {
    Statement q(db,"INSERT INTO geometry_evidence VALUES(?,?,?,?,?,?)");
    for (const auto& edit:edits) if (edit.event>after) {
        require(geometry.configured,"geometry evidence without geometry");
        q.text(1,world.str()); q.u64(2,edit.event.value); q.u64(3,edit.id.value); q.u64(4,edit.volume_q3);
        q.u64(5,geometry.config.dry_ug_per_q3); q.u64(6,geometry.config.water_ug_per_q3);
        q.done(); q.reset();
    }
}

void verify_geometry(sqlite3* db,WorldId world,const GeometrySnapshot& geometry,
                     std::span<const GeometryEdit> edits,EventId through) {
    Statement q(db,"SELECT event,edit,volume,dry,water FROM geometry_evidence "
                   "WHERE world=? AND event<=? ORDER BY event");
    q.text(1,world.str()); q.u64(2,through.value);
    for (const auto& edit:edits)
        require(q.row() && q.u64(0)==edit.event.value && q.u64(1)==edit.id.value && q.u64(2)==edit.volume_q3 &&
                q.u64(3)==geometry.config.dry_ug_per_q3 && q.u64(4)==geometry.config.water_ug_per_q3,
                "derived soil index disagrees with geometry authority");
    require(!q.row(),"invented derived geometry evidence");
}

void put_people(sqlite3* db,WorldId world,const HistoryIndex& index,std::span<const AntState> ants) {
    Statement insert(db,"INSERT INTO individuals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)");
    Statement last(db,"UPDATE individuals SET last_event=? WHERE world=? AND id=?");
    Statement stage(db,"UPDATE individuals SET stage=?,death_event=?,death_ms=?,death_cause=? WHERE world=? AND id=?");
    for (const auto& [id,delta]:index.individuals) {
        const auto& ant=ant_at(ants,id);
        const auto died=delta.died_at?delta.died_at->milliseconds:-1;
        if (delta.origin) {
            const auto& origin=*delta.origin;
            insert.text(1,world.str()); insert.u64(2,id.value); insert.u64(3,origin.colony.value);
            insert.number(4,static_cast<std::int64_t>(ant.caste));
            insert.number(5,static_cast<std::int64_t>(origin.stage));
            insert.number(6,static_cast<std::int64_t>(*delta.stage)); insert.number(7,origin.time.milliseconds);
            insert.u64(8,origin.id.value); insert.u64(9,delta.last.value); insert.u64(10,delta.death.value);
            insert.number(11,died); insert.u64(12,delta.death_cause);
            // The v2 origin flag is the last column.
            insert.number(13,origin.kind==FactKind::AntSeeded?1:0);
            insert.done(); insert.reset();
        } else {
            last.u64(1,delta.last.value); last.text(2,world.str()); last.u64(3,id.value);
            last.done();
            require(sqlite3_changes(db)==1,"missing individual row before index update");
            last.reset();
            if (delta.stage) {
                stage.number(1,static_cast<std::int64_t>(*delta.stage)); stage.u64(2,delta.death.value);
                stage.number(3,died); stage.u64(4,delta.death_cause); stage.text(5,world.str()); stage.u64(6,id.value);
                stage.done(); stage.reset();
            }
        }
    }
}

void verify_people(sqlite3* db,WorldId world,const HistoryIndex& index,std::span<const AntState> ants) {
    Statement q(db,"SELECT id,colony,caste,seed_stage,stage,created_ms,created_event,last_event,death_event,"
                   "death_ms,death_cause,seeded FROM individuals WHERE world=? ORDER BY id");
    q.text(1,world.str());
    require(index.individuals.size()==ants.size(),"individual index count differs from Core");
    for (const auto& [id,delta]:index.individuals) {
        const auto& ant=ant_at(ants,id);
        require(delta.origin && delta.stage && q.row(),"missing derived individual or origin");
        const auto& origin=*delta.origin;
        require(q.u64(0)==id.value && q.u64(1)==ant.colony.value && q.number(2)==static_cast<std::int64_t>(ant.caste) &&
                q.number(3)==static_cast<std::int64_t>(origin.stage) && q.number(4)==static_cast<std::int64_t>(ant.stage) &&
                q.number(5)==origin.time.milliseconds && q.u64(6)==origin.id.value && q.u64(7)==delta.last.value &&
                q.u64(8)==delta.death.value && q.number(9)==(delta.died_at?delta.died_at->milliseconds:-1) &&
                q.u64(10)==delta.death_cause && q.number(11)==(origin.kind==FactKind::AntSeeded?1:0),
                "derived individual index disagrees with facts and Core");
    }
    require(!q.row(),"invented derived individual");
}

void put_receipts(sqlite3* db,WorldId world,std::span<const CommandReceipt> receipts,EventId after) {
    Statement q(db,"INSERT INTO receipts VALUES(?,?,?,?)");
    for (const auto& receipt:receipts) if (receipt.event>after) {
        q.text(1,world.str()); q.text(2,hex64(receipt.command.id.high)+hex64(receipt.command.id.low));
        q.u64(3,receipt.event.value); q.u64(4,receipt.resource.value);
        q.done(); q.reset();
    }
}

void verify_receipts(sqlite3* db,WorldId world,std::span<const CommandReceipt> receipts) {
    Statement q(db,"SELECT command,event,resource FROM receipts WHERE world=? ORDER BY command");
    q.text(1,world.str());
    for (const auto& receipt:receipts)
        require(q.row() && q.text(0)==hex64(receipt.command.id.high)+hex64(receipt.command.id.low) &&
                q.u64(1)==receipt.event.value && q.u64(2)==receipt.resource.value,"derived command receipt mismatch");
    require(!q.row(),"invented derived command receipt");
}

void put_observation(sqlite3* db,const Observation& observation,std::uint64_t generation) {
    Statement sample(db,"INSERT INTO samples VALUES(?,?,?,?,?,?,?,?,?)");
    auto digest=observation_header(observation);
    for (const auto& value:observation.values) {
        digest=observation_value(digest,value);
        sample.text(1,observation.world.str()); sample.u64(2,generation);
        sample.u64(3,value.owner.value); sample.number(4,static_cast<std::int64_t>(value.metric));
        sample.number(5,observation.time.milliseconds); sample.u64(6,observation.revision);
        sample.u64(7,observation.cursor.value); sample.u64(8,value.value); sample.number(9,metric_version);
        sample.done(); sample.reset();
    }
    Statement anchor(db,"INSERT INTO observations VALUES(?,?,?,?,?,?,?)");
    anchor.text(1,observation.world.str()); anchor.u64(2,generation); anchor.number(3,observation.time.milliseconds);
    anchor.u64(4,observation.revision); anchor.u64(5,observation.cursor.value);
    anchor.real(6,observation.geometry_quantum_m); anchor.u64(7,digest);
    anchor.done();
}

void verify_observation(sqlite3* db,const Observation& actual,std::uint64_t generation) {
    Statement q(db,"SELECT owner,metric,value,time_ms,revision,cursor,definition FROM samples "
                   "WHERE world=? AND generation=? ORDER BY owner,metric");
    q.text(1,actual.world.str()); q.u64(2,generation);
    auto digest=observation_header(actual);
    for (const auto& value:actual.values) {
        require(q.row() && q.u64(0)==value.owner.value && q.number(1)==static_cast<std::int64_t>(value.metric) &&
                q.u64(2)==value.value && q.number(3)==actual.time.milliseconds && q.u64(4)==actual.revision &&
                q.u64(5)==actual.cursor.value && q.number(6)==metric_version,"checkpoint gauge differs from sample");
        digest=observation_value(digest,value);
    }
    require(!q.row(),"extra checkpoint gauge");
    Statement anchor(db,"SELECT time_ms,revision,cursor,quantum_m,digest FROM observations WHERE world=? AND generation=?");
    anchor.text(1,actual.world.str()); anchor.u64(2,generation);
    require(anchor.row() && anchor.number(0)==actual.time.milliseconds && anchor.u64(1)==actual.revision &&
            anchor.u64(2)==actual.cursor.value && sqlite3_column_double(anchor.p,3)==actual.geometry_quantum_m &&
            anchor.u64(4)==digest,"checkpoint observation anchor differs from authority");
}

void read_observed_buckets(sqlite3* db,WorldId world,std::uint64_t generation,SimTime time,
                           EventId through,HistoryIndex& index) {
    Statement anchors(db,"SELECT generation,time_ms,revision,cursor,quantum_m,digest FROM observations "
                         "WHERE world=? ORDER BY generation");
    anchors.text(1,world.str());
    std::uint64_t observed=0,samples=0;
    while (anchors.row()) {
        const auto gen=anchors.u64(0);
        Observation observation{world,{anchors.number(1)},anchors.u64(2),{anchors.u64(3)},
                                sqlite3_column_double(anchors.p,4),std::vector<MetricValue>(0)};
        require(gen==++observed && gen<=generation && observation.time.milliseconds>=0 &&
                observation.time<=time && observation.cursor<=through,"invalid observation sequence");
        auto digest=observation_header(observation);
        Statement q(db,"SELECT owner,metric,value,time_ms,revision,cursor,definition FROM samples "
                       "WHERE world=? AND generation=? ORDER BY owner,metric");
        q.text(1,world.str()); q.u64(2,gen);
        while (q.row()) {
            const MetricValue value{{q.u64(0)},static_cast<Metric>(q.number(1)),q.u64(2)};
            require(metric_definition(value.metric).kind==MetricKind::Gauge && q.number(3)==observation.time.milliseconds &&
                    q.u64(4)==observation.revision && q.u64(5)==observation.cursor.value && q.number(6)==metric_version,
                    "invalid historical gauge envelope");
            digest=observation_value(digest,value);
            observation.values.push_back(value);
            ++samples;
        }
        require(!observation.values.empty() && digest==anchors.u64(5),"historical gauge digest mismatch");
        index.observe(observation);
    }
    require(observed==generation,"missing historical observation generation");
    Statement count(db,"SELECT count(*) FROM samples WHERE world=?");
    count.text(1,world.str());
    require(count.row() && static_cast<std::uint64_t>(count.number(0))==samples,"unanchored gauge sample");
}

void merge_buckets(sqlite3* db,WorldId world,const Buckets& buckets) {
    Statement old(db,"SELECT count,total,minimum,maximum,first_event FROM buckets "
                     "WHERE world=? AND owner=? AND metric=? AND start_ms=?");
    Statement put(db,"INSERT OR REPLACE INTO buckets VALUES(?,?,?,?,?,?,?,?,?,?,?)");
    for (const auto& [key,update]:buckets) {
        auto value=update;
        bucket_key(old,world,key);
        if (old.row()) {
            value.samples=checked_add(value.samples,old.u64(0));
            value.sum=checked_add(value.sum,old.u64(1));
            value.minimum=std::min(value.minimum,old.u64(2));
            value.maximum=std::max(value.maximum,old.u64(3));
            value.first_event={old.u64(4)};
        }
        old.reset();
        bucket_key(put,world,key); put.u64(5,value.samples); put.u64(6,value.sum);
        put.u64(7,value.minimum); put.u64(8,value.maximum); put.u64(9,value.last);
        put.u64(10,value.first_event.value); put.u64(11,value.last_event.value);
        put.done(); put.reset();
    }
}

void verify_buckets(sqlite3* db,WorldId world,const Buckets& buckets) {
    Statement q(db,"SELECT owner,metric,start_ms,count,total,minimum,maximum,last,first_event,last_event "
                   "FROM buckets WHERE world=? ORDER BY owner,metric,start_ms");
    q.text(1,world.str());
    for (const auto& [key,value]:buckets)
        require(q.row() && q.u64(0)==std::get<0>(key).value && q.number(1)==static_cast<std::int64_t>(std::get<1>(key)) &&
                q.number(2)==std::get<2>(key) && q.u64(3)==value.samples && q.u64(4)==value.sum &&
                q.u64(5)==value.minimum && q.u64(6)==value.maximum && q.u64(7)==value.last &&
                q.u64(8)==value.first_event.value && q.u64(9)==value.last_event.value,"derived minute bucket differs from raw evidence");
    require(!q.row(),"invented derived minute bucket");
}
} // namespace antworld::storage::detail
