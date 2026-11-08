#include "store_internal.hpp"
#include <algorithm>

namespace antworld::storage {
using namespace detail;
LoadedWorld Store::load(WorldId world, std::optional<std::uint64_t> requested) const {
    Transaction tx(impl_->db, false);
    const auto newest = latest(world);
    require(newest.has_value(), "no durable world; journal alone cannot recover continuation");
    const auto generation = requested.value_or(newest->generation);
    Statement q(impl_->db, "SELECT generation,revision,cursor,checkpoint_hash,checkpoint,time_ms FROM "
                           "generations WHERE world=? AND generation=?");
    q.text(1, world.str());
    q.u64(2, generation);
    require(q.row(), "complete checkpoint generation unavailable");
    const auto saved = token(q, world);
    const auto bytes = q.blob(4, impl_->limits.checkpoint_bytes);
    const auto time = q.number(5);
    require(hash(bytes) == saved.checkpoint_hash, "durable checkpoint checksum mismatch; no silent rollback");
    WorldRuntime runtime(world, 0, {}, impl_->limits);
    runtime.restore(bytes);
    const auto state = runtime.summary();
    require(state.world == world && state.revision == saved.revision &&
                state.committed_events == saved.cursor && state.now.milliseconds == time,
            "checkpoint envelope disagrees with restored authority");
    if (generation == newest->generation)
        require(saved == *newest, "latest generation metadata mismatch");
    const auto facts = runtime.committed_events();
    std::map<EventId, GeometryEdit> edits;
    for (const auto &edit : runtime.geometry_edits())
        edits.emplace(edit.event, edit);
    std::string sql = "SELECT ";
    sql += history_columns;
    sql += " FROM events WHERE world=? AND id<=? ORDER BY id";
    Statement history_query(impl_->db, sql.c_str());
    history_query.text(1, world.str());
    history_query.u64(2, saved.cursor);
    auto prefix = UINT64_C(14695981039346656037);
    using FlowKey = std::tuple<ColonyId, Metric, EventId>;
    std::map<FlowKey, std::pair<SimTime, std::uint64_t>> expected_flows;
    const auto geometry = runtime.geometry_snapshot();
    std::map<EntityId, IndividualRecord> people;
    std::map<std::pair<EntityId, EventId>, bool> expected_participants;
    for (const auto &fact : facts) {
        require(history_query.row(), "missing durable history");
        const auto r = record(history_query);
        require(r.fact == fact &&
                    r.geometry_edit.value == (edits.contains(fact.id) ? edits.at(fact.id).id.value : 0),
                "history disagrees with checkpoint evidence");
        prefix = hash(encode_event(fact), prefix);
        const auto *edit = edits.contains(fact.id) ? &edits.at(fact.id) : nullptr;
        for (const auto &value : contributions(fact, geometry, edit))
            expected_flows.emplace(FlowKey{value.owner, value.metric, fact.id},
                                   std::pair{fact.time, value.value});
        if (fact.kind == FactKind::AntSeeded) {
            IndividualRecord p;
            p.ant = {world, fact.actor};
            p.colony = fact.colony;
            p.seeded_stage = fact.stage;
            p.current_stage = fact.stage;
            p.created_at = fact.time;
            p.created_event = fact.id;
            people.emplace(fact.actor, p);
        }
        if (fact.actor.value)
            people.at(fact.actor).last_event = fact.id;
        if (fact.actor.value)
            expected_participants[{fact.actor, fact.id}] = true;
        if (fact.kind == FactKind::NutritionTransferred)
            expected_participants[{{fact.payload}, fact.id}] = true;
        if (fact.kind == FactKind::NutritionTransferred)
            people.at(EntityId{fact.payload}).last_event = fact.id;
        if (fact.kind == FactKind::StageChanged || fact.kind == FactKind::AntDied)
            people.at(fact.actor).current_stage = fact.stage;
        if (fact.kind == FactKind::AntDied) {
            auto &p = people.at(fact.actor);
            p.death_event = fact.id;
            p.died_at = fact.time;
            p.death_cause_code = fact.payload;
        }
    }
    require(!history_query.row(), "extra durable history before cursor");
    Statement participants(
        impl_->db,
        "SELECT individual,event FROM participants WHERE world=? AND event<=? ORDER BY individual,event");
    participants.text(1, world.str());
    participants.u64(2, saved.cursor);
    for (const auto &[key, unused] : expected_participants) {
        (void)unused;
        require(participants.row() && participants.u64(0) == key.first.value &&
                    participants.u64(1) == key.second.value,
                "participant index disagrees with facts");
    }
    require(!participants.row(), "invented event participant");
    Statement flow(impl_->db, "SELECT owner,metric,event,time_ms,value FROM flows WHERE world=? AND event<=? "
                              "ORDER BY owner,metric,event");
    flow.text(1, world.str());
    flow.u64(2, saved.cursor);
    for (const auto &[key, value] : expected_flows) {
        require(flow.row() && flow.u64(0) == std::get<0>(key).value &&
                    flow.number(1) == static_cast<std::int64_t>(std::get<1>(key)) &&
                    flow.u64(2) == std::get<2>(key).value && flow.number(3) == value.first.milliseconds &&
                    flow.u64(4) == value.second,
                "metric flow disagrees with committed evidence");
    }
    require(!flow.row(), "fabricated metric flow");
    const auto observation = observe(runtime);
    Statement points(impl_->db, "SELECT owner,metric,value,time_ms,revision,cursor,definition FROM samples "
                                "WHERE world=? AND generation=? ORDER BY owner,metric");
    points.text(1, world.str());
    points.u64(2, generation);
    for (const auto &value : observation.values) {
        require(points.row() && points.u64(0) == value.owner.value &&
                    points.number(1) == static_cast<std::int64_t>(value.metric) &&
                    points.u64(2) == value.value && points.number(3) == observation.time.milliseconds &&
                    points.u64(4) == observation.revision && points.u64(5) == observation.cursor.value &&
                    points.number(6) == metric_version,
                "snapshot gauge disagrees with actual state");
    }
    require(!points.row(), "extra snapshot gauge");
    if (generation == newest->generation) {
        Statement meta(impl_->db, "SELECT seed,time_ms,prefix_hash FROM worlds WHERE world=?");
        meta.text(1, world.str());
        require(meta.row() && meta.u64(0) == state.seed && meta.number(1) == time && meta.u64(2) == prefix,
                "world metadata/prefix mismatch");
        Statement counts(impl_->db,
                         "SELECT (SELECT count(*) FROM events WHERE world=?),(SELECT count(*) FROM "
                         "individuals WHERE world=?),(SELECT count(*) FROM receipts WHERE world=?)");
        for (int i = 1; i <= 3; ++i)
            counts.text(i, world.str());
        require(counts.row(), "missing history counts");
        require(static_cast<std::uint64_t>(counts.number(0)) == facts.size() &&
                    static_cast<std::uint64_t>(counts.number(1)) == people.size() &&
                    static_cast<std::uint64_t>(counts.number(2)) == runtime.command_receipts().size(),
                "durable evidence count mismatch");
        for (const auto &ant : runtime.ant_states()) {
            const auto actual = individual({world, ant.id});
            const auto &expected = people.at(ant.id);
            require(actual && actual->colony == ant.colony && actual->caste == ant.caste &&
                        actual->current_stage == ant.stage && actual->created_at == expected.created_at &&
                        actual->seeded_stage == expected.seeded_stage &&
                        actual->created_event == expected.created_event &&
                        actual->last_event == expected.last_event &&
                        actual->death_event == expected.death_event && actual->died_at == expected.died_at &&
                        actual->death_cause_code == expected.death_cause_code,
                    "individual history disagrees with identity/life evidence");
        }
        for (const auto &receipt : runtime.command_receipts()) {
            Statement row(impl_->db, "SELECT event,resource FROM receipts WHERE world=? AND command=?");
            row.text(1, world.str());
            row.text(2, hex64(receipt.command.id.high) + hex64(receipt.command.id.low));
            require(row.row() && row.u64(0) == receipt.event.value && row.u64(1) == receipt.resource.value,
                    "durable command receipt mismatch");
        }
        // Recompute every retained bucket from raw observations/flows, independent of bucket queries.
        std::map<BucketKey, MetricBucket> expected_buckets;
        Statement anchors(impl_->db, "SELECT generation,time_ms,revision,cursor,quantum_m,digest FROM "
                                     "observations WHERE world=? ORDER BY generation");
        anchors.text(1, world.str());
        std::uint64_t anchors_seen = 0, point_count = 0;
        while (anchors.row()) {
            ++anchors_seen;
            const auto gen = anchors.u64(0);
            Observation anchor;
            anchor.world = world;
            anchor.time = {anchors.number(1)};
            anchor.revision = anchors.u64(2);
            anchor.cursor = {anchors.u64(3)};
            anchor.geometry_quantum_m = sqlite3_column_double(anchors.p, 4);
            auto digest = observation_header(anchor);
            require(gen <= generation && anchor.time <= state.now && anchor.cursor.value <= saved.cursor,
                    "future observation in current generation");
            Statement rows(impl_->db, "SELECT owner,metric,value,time_ms,revision,cursor,definition FROM "
                                      "samples WHERE world=? AND generation=? ORDER BY owner,metric");
            rows.text(1, world.str());
            rows.u64(2, gen);
            std::size_t n = 0;
            while (rows.row()) {
                ++point_count;
                ++n;
                MetricValue value{{rows.u64(0)}, static_cast<Metric>(rows.number(1)), rows.u64(2)};
                require(metric_definition(value.metric).kind == MetricKind::Gauge &&
                            rows.number(3) == anchor.time.milliseconds && rows.u64(4) == anchor.revision &&
                            rows.u64(5) == anchor.cursor.value && rows.number(6) == metric_version,
                        "invalid historical observation envelope");
                digest = observation_value(digest, value);
                const auto start = anchor.time.milliseconds - anchor.time.milliseconds % bucket_ms;
                accumulate(expected_buckets[{value.owner, value.metric, start}], value.value, anchor.cursor);
            }
            require(n && digest == anchors.u64(5), "historical observation checksum mismatch");
        }
        require(anchors_seen == generation, "missing observation generation");
        Statement sample_count(impl_->db, "SELECT count(*) FROM samples WHERE world=?");
        sample_count.text(1, world.str());
        require(sample_count.row() && static_cast<std::uint64_t>(sample_count.number(0)) == point_count,
                "unanchored metric observation");
        // Event order, rather than owner/metric map order, defines the bucket's last value.
        Statement raw(
            impl_->db,
            "SELECT owner,metric,time_ms,event,value FROM flows WHERE world=? ORDER BY event,owner,metric");
        raw.text(1, world.str());
        std::size_t raw_count = 0;
        while (raw.row()) {
            ++raw_count;
            const auto t = raw.number(2);
            accumulate(
                expected_buckets[{{raw.u64(0)}, static_cast<Metric>(raw.number(1)), t - t % bucket_ms}],
                raw.u64(4), {raw.u64(3)});
        }
        require(raw_count == expected_flows.size(), "extra flow after durable cursor");
        Statement stored(
            impl_->db, "SELECT owner,metric,start_ms,count,total,minimum,maximum,last,first_event,last_event "
                       "FROM buckets WHERE world=? ORDER BY owner,metric,start_ms");
        stored.text(1, world.str());
        for (const auto &[key, b] : expected_buckets) {
            require(stored.row() && stored.u64(0) == std::get<0>(key).value &&
                        stored.number(1) == static_cast<std::int64_t>(std::get<1>(key)) &&
                        stored.number(2) == std::get<2>(key) && stored.u64(3) == b.samples &&
                        stored.u64(4) == b.sum && stored.u64(5) == b.minimum && stored.u64(6) == b.maximum &&
                        stored.u64(7) == b.last && stored.u64(8) == b.first_event.value &&
                        stored.u64(9) == b.last_event.value,
                    "stored aggregate disagrees with raw evidence");
        }
        require(!stored.row(), "fabricated aggregate bucket");
    }
    tx.commit();
    return {std::move(runtime), saved};
}
} // namespace antworld::storage
