#pragma once
#include "segmented_archive.hpp"

namespace antworld::storage::detail {
using Buckets = std::map<BucketKey,MetricBucket>;
struct IndividualDelta {
    std::optional<WorldEvent> origin;
    EventId last,death;
    std::optional<LifeStage> stage;
    std::optional<SimTime> died_at;
    std::uint64_t death_cause{};
};
struct HistoryIndex {
    std::map<EntityId,IndividualDelta> individuals;
    Buckets buckets;
    void record(const WorldEvent&,const GeometrySnapshot&,const GeometryEdit*);
    void observe(const Observation&);
};
[[nodiscard]] EntityId related_entity(const WorldEvent&);
[[nodiscard]] HistoryRecord segmented_record(sqlite3*,const WorldEvent&);
[[nodiscard]] std::vector<MetricValue> segmented_contributions(sqlite3*,const WorldEvent&);
[[nodiscard]] const GeometryEdit* find_edit(std::span<const GeometryEdit>,EventId);
void put_geometry(sqlite3*,WorldId,const GeometrySnapshot&,std::span<const GeometryEdit>,EventId after);
void verify_geometry(sqlite3*,WorldId,const GeometrySnapshot&,std::span<const GeometryEdit>,EventId through);
void put_people(sqlite3*,WorldId,const HistoryIndex&,std::span<const AntState>);
void verify_people(sqlite3*,WorldId,const HistoryIndex&,std::span<const AntState>);
void put_receipts(sqlite3*,WorldId,std::span<const CommandReceipt>,EventId after);
void verify_receipts(sqlite3*,WorldId,std::span<const CommandReceipt>);
void put_observation(sqlite3*,const Observation&,std::uint64_t generation);
void verify_observation(sqlite3*,const Observation&,std::uint64_t generation);
void read_observed_buckets(sqlite3*,WorldId,std::uint64_t generation,SimTime,EventId,HistoryIndex&);
void merge_buckets(sqlite3*,WorldId,const Buckets&);
void verify_buckets(sqlite3*,WorldId,const Buckets&);
} // namespace antworld::storage::detail
