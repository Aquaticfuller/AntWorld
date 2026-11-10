#pragma once
#include "antworld/storage/analytics.hpp"
#include <filesystem>
#include <functional>
#include <stdexcept>

namespace antworld::storage {
class RecoveryRequired : public std::runtime_error {
  public:
    using std::runtime_error::runtime_error;
};
struct SaveToken {
    WorldId world;
    std::uint64_t generation{}, revision{}, cursor{}, checkpoint_hash{};
    bool operator==(const SaveToken &) const = default;
};
enum class SaveStage {
    BeforeTransaction, AfterCheckpoint, AfterHistory, BeforeCommit, AfterCommit,
    BeforeBlocks, AfterBlocks, BeforeManifest, AfterManifest
};
enum class StoreFormat { Legacy, Segmented };
struct SaveOptions {
    // v1 checkpoint retention. Published v2 frames remain available.
    std::size_t retained_generations{2};
    // Fault injection only; production leaves this empty. AfterCommit is already durable.
    std::function<void(SaveStage)> fault_hook;
};
struct LoadedWorld {
    WorldRuntime world;
    SaveToken token;
};
struct WorldCoverage {
    SaveToken token;
    SimTime observed_through;
    double geometry_quantum_m{};
};
struct HistoryFilter {
    WorldId world{};
    EventId after{};
    SimTime begin{}, end{INT64_MAX};
    std::optional<EntityId> individual{};
    std::optional<FactKind> kind{};
    std::size_t limit{100};
};
struct HistoryRecord {
    WorldEvent fact;
    EntityId related;
    GeometryEditId geometry_edit;
    SoilParcelId parcel;
};
struct IndividualRecord {
    AntRef ant;
    ColonyId colony;
    Caste caste{};
    LifeStage seeded_stage{}, current_stage{};
    SimTime created_at;
    EventId created_event, last_event, death_event;
    std::optional<SimTime> died_at;
    // A seeded record never claims an observed biological birth.
    bool seeded{true};
    std::uint64_t death_cause_code{};
};
struct HistoryStorageStats {
    std::uint64_t blocks{}, facts{}, raw_bytes{}, packed_bytes{}, frames{}, frame_bytes{};
};
struct SaveFrame;
class LiveHistoryWriter;
class Store {
  public:
    // The format preference applies only to a new file.
    explicit Store(const std::filesystem::path &,RuntimeLimits = {},StoreFormat = StoreFormat::Legacy);
    ~Store();
    Store(Store &&) noexcept;
    Store &operator=(Store &&) noexcept;
    Store(const Store &) = delete;
    Store &operator=(const Store &) = delete;
    SaveToken save(const WorldRuntime &, std::optional<SaveToken> expected = {}, const SaveOptions & = {});
    LoadedWorld load(WorldId, std::optional<std::uint64_t> generation = {}) const;
    LoadedWorld recover(WorldId,std::uint64_t base_generation,std::uint64_t target_generation) const;
    void rebuild_history_indexes(WorldId);
    static void migrate_legacy(const std::filesystem::path& source,const std::filesystem::path& shadow,
                               RuntimeLimits = {});
    CommandReceipt place_food(WorldRuntime &, SaveToken &, const PlaceFoodCommand &,
                              const SaveOptions & = {});
    std::optional<SaveToken> latest(WorldId) const;
    std::optional<WorldCoverage> coverage(WorldId) const;
    std::vector<HistoryRecord> history(const HistoryFilter &) const;
    std::optional<IndividualRecord> individual(AntRef) const;
    std::vector<MetricPoint> series(WorldId, ColonyId, Metric, SimTime begin, SimTime end,
                                    std::uint64_t after_generation = 0, std::size_t limit = 100) const;
    // Fixed one-minute buckets, returned only when fully contained in [begin,end).
    std::vector<MetricBucket> buckets(WorldId, ColonyId, Metric, SimTime begin, SimTime end,
                                      std::size_t limit = 100) const;
    std::uint64_t flow_total(WorldId, ColonyId, Metric, SimTime begin, SimTime end) const;
    void checkpoint_wal();
    [[nodiscard]] std::uint64_t database_bytes() const;
    [[nodiscard]] std::uint64_t sqlite_memory_bytes() const;
    [[nodiscard]] static const char *sqlite_version();
    [[nodiscard]] StoreFormat format() const noexcept;
    [[nodiscard]] HistoryStorageStats history_storage(WorldId) const;

  private:
    friend class LiveHistoryWriter;
    struct Impl;
    std::unique_ptr<Impl> impl_;
    SaveToken save_segmented(const SaveFrame&,std::optional<SaveToken>,const SaveOptions&);
    LoadedWorld load_legacy(WorldId,std::optional<std::uint64_t>) const;
    LoadedWorld load_segmented(WorldId,std::optional<std::uint64_t>,bool validate_indexes) const;
    std::shared_ptr<const EventPrefix> published_prefix(const SaveToken&) const;
    std::vector<HistoryRecord> segmented_history(const HistoryFilter&) const;
    std::uint64_t segmented_flow(WorldId,ColonyId,Metric,SimTime,SimTime) const;
};
} // namespace antworld::storage
