#include "store_internal.hpp"

namespace antworld::storage {
using namespace detail;
std::optional<WorldCoverage> Store::coverage(WorldId world) const {
    Statement query(
        impl_->db,
        "SELECT generation,revision,cursor,checkpoint_hash,time_ms,quantum_m FROM worlds WHERE world=?");
    query.text(1, world.str());
    if (!query.row())
        return {};
    return WorldCoverage{token(query, world), {query.number(4)}, sqlite3_column_double(query.p, 5)};
}
std::vector<HistoryRecord> Store::history(const HistoryFilter &filter) const {
    range(filter.begin, filter.end, filter.limit);
    if (filter.kind && *filter.kind > FactKind::FoodPlaced)
        throw std::invalid_argument("invalid fact kind");
    std::string sql = "SELECT ";
    sql += history_columns;
    sql += " FROM events WHERE world=? AND id>? AND time_ms>=? AND time_ms<?";
    if (filter.individual)
        sql += " AND id IN (SELECT event FROM participants WHERE world=? AND individual=? AND event>?)";
    if (filter.kind)
        sql += " AND kind=?";
    sql += " ORDER BY id LIMIT ?";
    Statement q(impl_->db, sql.c_str());
    q.text(1, filter.world.str());
    q.u64(2, filter.after.value);
    q.number(3, filter.begin.milliseconds);
    q.number(4, filter.end.milliseconds);
    int i = 5;
    if (filter.individual) {
        q.text(i++, filter.world.str());
        q.u64(i++, filter.individual->value);
        q.u64(i++, filter.after.value);
    }
    if (filter.kind)
        q.number(i++, static_cast<std::int64_t>(*filter.kind));
    q.number(i, static_cast<std::int64_t>(filter.limit));
    std::vector<HistoryRecord> result(0);
    while (q.row())
        result.push_back(record(q));
    return result;
}
std::optional<IndividualRecord> Store::individual(AntRef ref) const {
    Statement q(impl_->db, "SELECT "
                           "colony,caste,seed_stage,stage,created_ms,created_event,last_event,death_event,"
                           "death_ms,death_cause FROM individuals WHERE world=? AND id=?");
    q.text(1, ref.world.str());
    q.u64(2, ref.id.value);
    if (!q.row())
        return {};
    IndividualRecord r;
    r.ant = ref;
    r.colony = {q.u64(0)};
    r.caste = static_cast<Caste>(q.number(1));
    r.seeded_stage = static_cast<LifeStage>(q.number(2));
    r.current_stage = static_cast<LifeStage>(q.number(3));
    r.created_at = {q.number(4)};
    r.created_event = {q.u64(5)};
    r.last_event = {q.u64(6)};
    r.death_event = {q.u64(7)};
    if (q.number(8) >= 0)
        r.died_at = SimTime{q.number(8)};
    r.death_cause_code = q.u64(9);
    return r;
}
std::vector<MetricPoint> Store::series(WorldId world, ColonyId owner, Metric metric, SimTime begin,
                                       SimTime end, std::uint64_t after, std::size_t limit) const {
    range(begin, end, limit);
    require(metric_definition(metric).kind == MetricKind::Gauge, "series requires a gauge");
    Statement q(
        impl_->db,
        "SELECT time_ms,generation,revision,value,cursor,definition FROM samples WHERE world=? AND owner=? "
        "AND metric=? AND time_ms>=? AND time_ms<? AND generation>? ORDER BY time_ms,generation LIMIT ?");
    q.text(1, world.str());
    q.u64(2, owner.value);
    q.number(3, static_cast<std::int64_t>(metric));
    q.number(4, begin.milliseconds);
    q.number(5, end.milliseconds);
    q.u64(6, after);
    q.number(7, static_cast<std::int64_t>(limit));
    std::vector<MetricPoint> result(0);
    while (q.row()) {
        require(q.number(5) == metric_version, "unsupported metric definition");
        result.push_back({{q.number(0)}, q.u64(1), q.u64(2), q.u64(3), {q.u64(4)}});
    }
    return result;
}
std::vector<MetricBucket> Store::buckets(WorldId world, ColonyId owner, Metric metric, SimTime begin,
                                         SimTime end, std::size_t limit) const {
    range(begin, end, limit);
    (void)metric_definition(metric);
    Statement q(impl_->db,
                "SELECT start_ms,count,total,minimum,maximum,last,first_event,last_event FROM buckets WHERE "
                "world=? AND owner=? AND metric=? AND start_ms>=? AND start_ms<=? ORDER BY start_ms LIMIT ?");
    q.text(1, world.str());
    q.u64(2, owner.value);
    q.number(3, static_cast<std::int64_t>(metric));
    q.number(4, begin.milliseconds);
    q.number(5, end.milliseconds >= bucket_ms ? end.milliseconds - bucket_ms : -1);
    q.number(6, static_cast<std::int64_t>(limit));
    std::vector<MetricBucket> result(0);
    while (q.row())
        result.push_back({{q.number(0)},
                          {q.number(0) + bucket_ms},
                          q.u64(1),
                          q.u64(2),
                          q.u64(3),
                          q.u64(4),
                          q.u64(5),
                          {q.u64(6)},
                          {q.u64(7)}});
    return result;
}
std::uint64_t Store::flow_total(WorldId world, ColonyId owner, Metric metric, SimTime begin,
                                SimTime end) const {
    range(begin, end);
    require(metric_definition(metric).kind == MetricKind::Flow, "flow query requires an event metric");
    const auto known = coverage(world);
    require(known.has_value(), "no durable history coverage for world");
    require(end.milliseconds == 0 || end.milliseconds - 1 <= known->observed_through.milliseconds,
            "flow window extends beyond durable evidence");
    // Complete interior buckets use precomputed exact totals; two boundary fragments use indexed facts.
    const auto first = begin.milliseconds / bucket_ms + (begin.milliseconds % bucket_ms != 0);
    const auto last = end.milliseconds / bucket_ms;
    const auto full_begin = first <= INT64_MAX / bucket_ms ? first * bucket_ms : INT64_MAX;
    const auto full_end = last * bucket_ms;
    std::uint64_t total = 0;
    auto bind = [&](Statement &q) {
        q.text(1, world.str());
        q.u64(2, owner.value);
        q.number(3, static_cast<std::int64_t>(metric));
    };
    if (full_begin < full_end) {
        Statement q(impl_->db, "SELECT total FROM buckets WHERE world=? AND owner=? AND metric=? AND "
                               "start_ms>=? AND start_ms<?");
        bind(q);
        q.number(4, full_begin);
        q.number(5, full_end);
        while (q.row())
            total = checked_add(total, q.u64(0));
    }
    auto fragment = [&](std::int64_t a, std::int64_t b) {
        Statement q(
            impl_->db,
            "SELECT value FROM flows WHERE world=? AND owner=? AND metric=? AND time_ms>=? AND time_ms<?");
        bind(q);
        q.number(4, a);
        q.number(5, b);
        while (q.row())
            total = checked_add(total, q.u64(0));
    };
    if (full_begin >= full_end)
        fragment(begin.milliseconds, end.milliseconds);
    else {
        fragment(begin.milliseconds, full_begin);
        fragment(full_end, end.milliseconds);
    }
    return total;
}
} // namespace antworld::storage
