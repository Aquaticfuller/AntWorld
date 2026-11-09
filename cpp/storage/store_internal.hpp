#pragma once
#include "sqlite_internal.hpp"
#include <bit>
#include <map>
#include <tuple>

namespace antworld::storage {
struct Store::Impl {
    sqlite3 *db{};
    RuntimeLimits limits;
    std::filesystem::path path;
    bool requires_recovery{};
    ~Impl() {
        if (db)
            sqlite3_close_v2(db);
    }
};
namespace detail {
inline constexpr std::int64_t bucket_ms = 60000;
inline std::uint64_t text_hash(const std::string &text,
                               std::uint64_t state = UINT64_C(14695981039346656037)) {
    return hash({reinterpret_cast<const std::uint8_t *>(text.data()), text.size()}, state);
}
inline std::uint64_t observation_header(const Observation &o) {
    return text_hash(o.world.str() + hex64(static_cast<std::uint64_t>(o.time.milliseconds)) +
                     hex64(o.revision) + hex64(o.cursor.value) +
                     hex64(std::bit_cast<std::uint64_t>(o.geometry_quantum_m)) + hex64(metric_version));
}
inline std::uint64_t observation_value(std::uint64_t state, MetricValue v) {
    return text_hash(hex64(v.owner.value) + hex64(static_cast<std::uint64_t>(v.metric)) + hex64(v.value),
                     state);
}
inline SaveToken token(Statement &q, WorldId world) {
    return {world, q.u64(0), q.u64(1), q.u64(2), q.u64(3)};
}
inline HistoryRecord record(Statement &q) {
    HistoryRecord r;
    r.fact = decode_event(q.blob(12, 159));
    r.related = {q.u64(4)};
    r.geometry_edit = {q.u64(10)};
    r.parcel = {q.u64(11)};
    const auto &e = r.fact;
    require(q.u64(0) == e.id.value && q.number(1) == e.time.milliseconds &&
                q.number(2) == static_cast<std::int64_t>(e.kind) && q.u64(3) == e.actor.value &&
                q.u64(5) == e.colony.value && q.u64(6) == e.resource.value && q.u64(7) == e.source.value &&
                q.u64(8) == e.revision && q.text(9) == e.world.str(),
            "history index disagrees with fact payload");
    require(r.related.value == (e.kind == FactKind::NutritionTransferred || e.kind==FactKind::AntBorn ? e.payload : 0),
            "invalid related-entity evidence");
    const bool soil = e.kind >= FactKind::SoilExcavated && e.kind <= FactKind::SoilFilled;
    require(r.parcel.value == (soil ? e.payload : 0), "invalid parcel evidence");
    return r;
}
inline constexpr const char *history_columns =
    "id,time_ms,kind,actor,related,colony,resource,source,revision,world,geometry_edit,parcel,payload";
using BucketKey = std::tuple<ColonyId, Metric, std::int64_t>;
inline void accumulate(MetricBucket &b, std::uint64_t value, EventId cursor) {
    if (!b.samples) {
        b.minimum = value;
        b.maximum = value;
        b.first_event = cursor;
    }
    b.samples = checked_add(b.samples, 1);
    b.sum = checked_add(b.sum, value);
    b.minimum = std::min(b.minimum, value);
    b.maximum = std::max(b.maximum, value);
    b.last = value;
    b.last_event = cursor;
}
inline void persist_bucket(sqlite3 *db, WorldId world, MetricValue value, SimTime time, EventId cursor) {
    const auto start = time.milliseconds - time.milliseconds % bucket_ms;
    Statement q(db, "SELECT count,total,minimum,maximum,last,first_event,last_event FROM buckets WHERE "
                    "world=? AND owner=? AND metric=? AND start_ms=?");
    q.text(1, world.str());
    q.u64(2, value.owner.value);
    q.number(3, static_cast<std::int64_t>(value.metric));
    q.number(4, start);
    MetricBucket b;
    if (q.row()) {
        b.samples = q.u64(0);
        b.sum = q.u64(1);
        b.minimum = q.u64(2);
        b.maximum = q.u64(3);
        b.last = q.u64(4);
        b.first_event = {q.u64(5)};
        b.last_event = {q.u64(6)};
    }
    accumulate(b, value.value, cursor);
    Statement put(db, "INSERT OR REPLACE INTO buckets VALUES(?,?,?,?,?,?,?,?,?,?,?)");
    put.text(1, world.str());
    put.u64(2, value.owner.value);
    put.number(3, static_cast<std::int64_t>(value.metric));
    put.number(4, start);
    put.u64(5, b.samples);
    put.u64(6, b.sum);
    put.u64(7, b.minimum);
    put.u64(8, b.maximum);
    put.u64(9, b.last);
    put.u64(10, b.first_event.value);
    put.u64(11, b.last_event.value);
    put.done();
}
} // namespace detail
} // namespace antworld::storage
