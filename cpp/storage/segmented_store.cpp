#include "segmented_analytics.hpp"
#include "storage_timing.hpp"
#include <algorithm>

namespace antworld::storage {
using namespace detail;
namespace {
constexpr std::uint64_t unused_legacy_prefix=0;

void put_world(sqlite3* db,const SaveToken& token,const WorldSnapshot& state,double quantum) {
    Statement q(db,"INSERT INTO worlds VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(world) DO UPDATE SET "
                   "generation=excluded.generation,revision=excluded.revision,time_ms=excluded.time_ms,"
                   "cursor=excluded.cursor,checkpoint_hash=excluded.checkpoint_hash,"
                   "prefix_hash=excluded.prefix_hash,quantum_m=excluded.quantum_m");
    q.text(1,state.world.str()); q.u64(2,state.seed); q.u64(3,token.generation); q.u64(4,state.revision);
    q.number(5,state.now.milliseconds); q.u64(6,token.cursor); q.u64(7,token.checkpoint_hash);
    q.u64(8,unused_legacy_prefix); q.real(9,quantum);
    q.done();
}

void put_frame(sqlite3* db,const SaveToken& token,SimTime time,std::span<const std::uint8_t> frame) {
    Statement q(db,"INSERT INTO generations VALUES(?,?,?,?,?,?,?)");
    q.text(1,token.world.str()); q.u64(2,token.generation); q.u64(3,token.revision);
    q.number(4,time.milliseconds); q.u64(5,token.cursor); q.u64(6,token.checkpoint_hash); q.blob(7,frame);
    q.done();
}

HistoryAnchor verified_anchor(sqlite3* db,WorldId world,std::uint64_t generation,std::size_t byte_limit) {
    Statement list(db,"SELECT generation FROM generations WHERE world=? AND generation<=? ORDER BY generation");
    list.text(1,world.str()); list.u64(2,generation);
    Digest parent{};
    std::optional<HistoryAnchor> last;
    while (list.row()) {
        auto current=read_anchor(db,world,list.u64(0),byte_limit);
        require(current.parent==parent && (!last || (current.token.generation==last->token.generation+1 &&
                current.token.cursor>=last->token.cursor && current.token.revision>=last->token.revision &&
                current.time>=last->time)),"invalid checkpoint anchor chain");
        parent=current.digest;
        last=std::move(current);
    }
    require(last && last->token.generation==generation,"missing requested checkpoint anchor");
    return std::move(*last);
}

void validate_manifest(sqlite3* db,const HistoryAnchor& anchor,const WorldSnapshot& state,double quantum,bool latest) {
    Statement q(db,"SELECT seed,time_ms,quantum_m,prefix_hash,cursor FROM worlds WHERE world=?");
    q.text(1,state.world.str());
    require(state.world==anchor.token.world && state.now==anchor.time && state.revision==anchor.token.revision &&
            state.committed_events==anchor.token.cursor && q.row() && q.u64(0)==state.seed &&
            q.u64(3)==unused_legacy_prefix && (!latest || (q.number(1)==state.now.milliseconds &&
            q.u64(4)==state.committed_events && sqlite3_column_type(q.p,2)==SQLITE_FLOAT &&
            sqlite3_column_double(q.p,2)==quantum)),"checkpoint frame disagrees with world manifest");
    if (latest) {
        Statement extra(db,"SELECT 1 FROM fact_blocks WHERE world=? AND last_id>? LIMIT 1");
        extra.text(1,state.world.str()); extra.u64(2,state.committed_events);
        require(!extra.row(),"durable facts extend beyond the published manifest");
    }
}

EventId time_cursor(sqlite3* db,WorldId world,SimTime begin,EventId through) {
    if (!begin.milliseconds) return {};
    Statement q(db,"SELECT last_id FROM fact_blocks WHERE world=? AND end_ms<? AND last_id<=? "
                   "ORDER BY end_ms DESC,last_id DESC LIMIT 1");
    q.text(1,world.str()); q.number(2,begin.milliseconds); q.u64(3,through.value);
    return q.row()?EventId{q.u64(0)}:EventId{};
}

template<class Read>
HistoryIndex collect_index(Read read,EventId after,EventId through,const GeometrySnapshot& geometry,
                           std::span<const GeometryEdit> edits) {
    HistoryIndex index;
    while (after<through) {
        const auto count=static_cast<std::size_t>(std::min<std::uint64_t>(through.value-after.value,block_records));
        const auto page=read(after,count);
        require(page.size()==count,"missing committed facts while building index");
        for (const auto& fact:page) index.record(fact,geometry,find_edit(edits,fact.id));
        after=page.back().id;
    }
    return index;
}

HistoryIndex rederive(sqlite3* db,const WorldRuntime& world,const SaveToken& token) {
    const auto edits=world.geometry_edits();
    auto index=collect_index([&](EventId after,std::size_t count){return world.events_after(after,count);},
                             {},{token.cursor},world.geometry_snapshot(),edits);
    read_observed_buckets(db,token.world,token.generation,world.summary().now,{token.cursor},index);
    return index;
}

void audit_indexes(sqlite3* db,const WorldRuntime& world,const SaveToken& token,bool latest) {
    verify_geometry(db,token.world,world.geometry_snapshot(),world.geometry_edits(),{token.cursor});
    if (latest) {
        const auto derived=rederive(db,world,token);
        verify_people(db,token.world,derived,world.ant_states());
        verify_buckets(db,token.world,derived.buckets);
        verify_receipts(db,token.world,world.command_receipts());
    }
}

std::optional<SaveToken> preceding_token(sqlite3* db,WorldId world,std::uint64_t generation) {
    Statement q(db,"SELECT generation,revision,cursor,checkpoint_hash FROM generations "
                   "WHERE world=? AND generation<? ORDER BY generation DESC LIMIT 1");
    q.text(1,world.str()); q.u64(2,generation);
    return q.row()?std::optional{token(q,world)}:std::nullopt;
}
} // namespace

SaveToken Store::save_segmented(const SaveFrame& frame,std::optional<SaveToken> expected,const SaveOptions& options) {
    if (impl_->requires_recovery) throw RecoveryRequired("reopen and recover after an uncertain database commit");
    const auto& state=frame.state;
    const auto world=state.world;
    require(format()==StoreFormat::Segmented,"segmented writer requires a v2 database");
    if (frame.checkpoint.size()>impl_->limits.checkpoint_bytes ||
        state.committed_events>impl_->limits.committed_events || frame.history.size()!=state.committed_events)
        throw std::length_error("segmented state or history host budget exceeded");
    const auto hook=[&](SaveStage stage){if(options.fault_hook) options.fault_hook(stage);};
    hook(SaveStage::BeforeTransaction);
    auto* db=impl_->db;
    Transaction tx(db);
    const auto previous=latest(world);
    auto parent=Digest{};
    auto start=EventId{};
    if (previous) {
        const auto durable=read_anchor(db,world,previous->generation,impl_->limits.checkpoint_bytes);
        require(durable.token==*previous,"latest anchor and manifest differ");
        Statement q(db,"SELECT seed,time_ms,prefix_hash FROM worlds WHERE world=?");
        q.text(1,world.str());
        require(q.row() && q.u64(0)==state.seed && q.number(1)==durable.time.milliseconds &&
                q.u64(2)==unused_legacy_prefix && state.now>=durable.time &&
                state.revision>=previous->revision && state.committed_events>=previous->cursor,
                "stale or divergent world state");
        start={previous->cursor};
        parent=durable.digest;
        require(compatible_fact_schema(frame_fact_schema(frame.checkpoint),frame_fact_schema(durable.frame)),
                "experimental founding models require independent published histories");
        if (state.now==durable.time && state.revision==previous->revision) {
            const auto retry_parent=preceding_token(db,world,previous->generation);
            require((expected==previous || (expected==retry_parent && (retry_parent || previous->generation==1))) &&
                    frame.checkpoint==durable.frame && state.committed_events==previous->cursor,
                    "conflicting duplicate save or predecessor");
            require_history_prefix(db,world,frame.history,start,durable.tail);
            tx.commit();
            return *previous;
        }
        require(previous==expected,"stale or missing predecessor save token");
        require_history_prefix(db,world,frame.history,start,durable.tail);
    } else require(!expected,"initial publication has a predecessor token");

    const auto generation=previous?checked_add(previous->generation,1):1;
    const SaveToken result{world,generation,state.revision,state.committed_events,hash(frame.checkpoint)};
    hook(SaveStage::BeforeBlocks);
    const auto tail=[&] {
        timing::Scope phase(timing::Phase::SealBlocks);
        return append_blocks(db,world,frame.history,start,{result.cursor},frame_fact_schema(frame.checkpoint));
    }();
    hook(SaveStage::AfterBlocks);
    const auto derived=[&] {
        timing::Scope phase(timing::Phase::DeriveIndexes);
        auto index=collect_index([&](EventId after,std::size_t count){return frame.history.read(after,count);},
                                 start,{result.cursor},frame.geometry,frame.edits);
        index.observe(frame.observation);
        return index;
    }();
    {
        timing::Scope phase(timing::Phase::WriteIndexes);
        hook(SaveStage::BeforeManifest);
        put_world(db,result,state,frame.observation.geometry_quantum_m);
        put_frame(db,result,state.now,frame.checkpoint);
        put_anchor(db,result,state.now,frame.checkpoint,parent,tail);
        hook(SaveStage::AfterCheckpoint);
        put_geometry(db,world,frame.geometry,frame.edits,start);
        put_people(db,world,derived,frame.ants);
        put_receipts(db,world,frame.receipts,start);
        hook(SaveStage::AfterHistory);
        put_observation(db,frame.observation,generation);
        merge_buckets(db,world,derived.buckets);
    }
    hook(SaveStage::AfterManifest);
    hook(SaveStage::BeforeCommit);
    try {
        timing::Scope phase(timing::Phase::Commit);
        tx.commit();
    } catch (const std::exception& error) {
        impl_->requires_recovery=true;
        throw RecoveryRequired(std::string("segmented commit requires reopening/recovery: ")+error.what());
    }
    try { hook(SaveStage::AfterCommit); } catch (...) {}
    return result;
}

std::shared_ptr<const EventPrefix> Store::published_prefix(const SaveToken& saved) const {
    const auto anchor=read_anchor(impl_->db,saved.world,saved.generation,impl_->limits.checkpoint_bytes);
    require(anchor.token==saved,"published prefix token mismatch");
    return std::make_shared<SqlEventPrefix>(impl_->path,saved.world,static_cast<std::size_t>(saved.cursor),anchor.tail);
}

LoadedWorld Store::load_segmented(WorldId world,std::optional<std::uint64_t> requested,bool validate_indexes) const {
    const auto current=latest(world);
    require(current.has_value(),"no published world");
    const auto generation=requested.value_or(current->generation);
    require(generation<=current->generation,"requested generation exceeds the manifest");
    const auto anchor=verified_anchor(impl_->db,world,generation,impl_->limits.checkpoint_bytes);
    const bool newest=generation==current->generation;
    require(!newest || anchor.token==*current,"latest frame and manifest differ");
    {
        timing::Scope phase(timing::Phase::VerifyBlocks);
        verify_blocks(impl_->db,world,{},{anchor.token.cursor},anchor.tail,frame_fact_schema(anchor.frame));
    }
    WorldRuntime runtime(world,0,{},impl_->limits);
    {
        timing::Scope phase(timing::Phase::RestoreFrame);
        runtime.restore_frame(anchor.frame,std::make_shared<SqlEventPrefix>(impl_->path,world,
            static_cast<std::size_t>(anchor.token.cursor),anchor.tail));
    }
    {
        timing::Scope phase(timing::Phase::CheckIndexes);
        const auto observation=observe(runtime);
        validate_manifest(impl_->db,anchor,runtime.summary(),observation.geometry_quantum_m,newest);
        verify_observation(impl_->db,observation,generation);
        if (validate_indexes) audit_indexes(impl_->db,runtime,anchor.token,newest);
    }
    return {std::move(runtime),anchor.token};
}

LoadedWorld Store::recover(WorldId world,std::uint64_t base_generation,std::uint64_t target_generation) const {
    require(format()==StoreFormat::Segmented && base_generation<=target_generation,
            "historical recovery requires ordered v2 generations");
    Transaction tx(impl_->db,false);
    auto base=load_segmented(world,base_generation,true);
    if (base_generation!=target_generation) {
        const auto current=latest(world);
        require(current && target_generation<=current->generation,"target exceeds the manifest");
        const auto target=verified_anchor(impl_->db,world,target_generation,impl_->limits.checkpoint_bytes);
        const auto schema=frame_fact_schema(target.frame);
        const auto base_profile=base.world.founding_profile();
        const auto base_schema=base_profile ? static_cast<FactSchema>(base_profile->model_version()+1) : FactSchema::Legacy;
        require(compatible_fact_schema(schema,base_schema),"experimental recovery cannot cross model versions");
        verify_blocks(impl_->db,world,{base.token.cursor},{target.token.cursor},target.tail,schema);
        base.world.restore_frame(target.frame,std::make_shared<SqlEventPrefix>(impl_->path,world,
            static_cast<std::size_t>(target.token.cursor),target.tail));
        const bool newest=target_generation==current->generation;
        require(!newest || target.token==*current,"target frame and manifest differ");
        const auto observation=observe(base.world);
        validate_manifest(impl_->db,target,base.world.summary(),observation.geometry_quantum_m,newest);
        verify_observation(impl_->db,observation,target_generation);
        audit_indexes(impl_->db,base.world,target.token,newest);
        base.token=target.token;
    }
    tx.commit();
    return base;
}

void Store::rebuild_history_indexes(WorldId world) {
    require(format()==StoreFormat::Segmented && !impl_->requires_recovery,"rebuild requires a writable v2 store");
    auto* db=impl_->db;
    Transaction tx(db);
    const auto loaded=load_segmented(world,{},false);
    const auto derived=rederive(db,loaded.world,loaded.token);
    for (const auto* table:{"geometry_evidence","individuals","buckets","receipts"}) {
        const auto sql=std::string("DELETE FROM ")+table+" WHERE world=?";
        Statement q(db,sql.c_str()); q.text(1,world.str()); q.done();
    }
    put_geometry(db,world,loaded.world.geometry_snapshot(),loaded.world.geometry_edits(),{});
    put_people(db,world,derived,loaded.world.ant_states());
    put_receipts(db,world,loaded.world.command_receipts(),{});
    merge_buckets(db,world,derived.buckets);
    try { tx.commit(); } catch (const std::exception& error) {
        impl_->requires_recovery=true;
        throw RecoveryRequired(std::string("index rebuild requires reopening/recovery: ")+error.what());
    }
}

std::vector<HistoryRecord> Store::segmented_history(const HistoryFilter& filter) const {
    auto* db=impl_->db;
    Transaction tx(db,false);
    std::vector<HistoryRecord> out(0);
    const auto current=latest(filter.world);
    if (current && filter.after.value<current->cursor && filter.begin<filter.end &&
        (!filter.individual || filter.individual->value)) {
        const EventId through{current->cursor};
        BlockCursor cursor(db,filter.world,std::max(filter.after,time_cursor(db,filter.world,filter.begin,through)),through);
        while (const auto block=cursor.next()) {
            if (block->header.begin>=filter.end) break;
            if (block->header.end<filter.begin) continue;
            for (const auto& fact:read_block(block->bytes,block->header)) {
                if (fact.id<=filter.after || fact.time<filter.begin || fact.time>=filter.end ||
                    (filter.kind && fact.kind!=*filter.kind) ||
                    (filter.individual && fact.actor!=*filter.individual && related_entity(fact)!=*filter.individual))
                    continue;
                out.push_back(segmented_record(db,fact));
                if (out.size()==filter.limit) break;
            }
            if (out.size()==filter.limit) break;
        }
    }
    tx.commit();
    return out;
}

std::uint64_t Store::segmented_flow(WorldId world,ColonyId owner,Metric metric,SimTime begin,SimTime end) const {
    std::uint64_t total=0;
    const auto current=latest(world);
    if (!current || begin>=end) return total;
    const EventId through{current->cursor};
    BlockCursor cursor(impl_->db,world,time_cursor(impl_->db,world,begin,through),through);
    while (const auto block=cursor.next()) {
        if (block->header.begin>=end) break;
        if (block->header.end<begin) continue;
        for (const auto& fact:read_block(block->bytes,block->header)) if (fact.time>=begin && fact.time<end)
            for (const auto& value:segmented_contributions(impl_->db,fact))
                if (value.owner==owner && value.metric==metric) total=checked_add(total,value.value);
    }
    return total;
}

HistoryStorageStats Store::history_storage(WorldId world) const {
    require(format()==StoreFormat::Segmented,"block statistics require a v2 store");
    Transaction tx(impl_->db,false);
    HistoryStorageStats stats{};
    if (const auto current=latest(world)) {
        stats.facts=current->cursor;
        Statement blocks(impl_->db,"SELECT count(*),coalesce(sum(raw_bytes),0),coalesce(sum(length(envelope)),0) "
                                  "FROM fact_blocks WHERE world=?");
        blocks.text(1,world.str());
        require(blocks.row(),"missing block statistics");
        stats.blocks=static_cast<std::uint64_t>(blocks.number(0));
        stats.raw_bytes=static_cast<std::uint64_t>(blocks.number(1));
        stats.packed_bytes=static_cast<std::uint64_t>(blocks.number(2));
        Statement frames(impl_->db,"SELECT count(*),coalesce(sum(length(checkpoint)),0) FROM generations WHERE world=?");
        frames.text(1,world.str());
        require(frames.row(),"missing frame statistics");
        stats.frames=static_cast<std::uint64_t>(frames.number(0));
        stats.frame_bytes=static_cast<std::uint64_t>(frames.number(1));
    }
    tx.commit();
    return stats;
}
} // namespace antworld::storage
