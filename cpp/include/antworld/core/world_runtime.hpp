#pragma once

#include "antworld/core/event.hpp"

#include <memory>
#include <optional>
#include <span>
#include <vector>

namespace antworld {
struct WorldSnapshot {
    WorldId world;
    SimTime now;
    std::uint64_t seed{}, revision{}, pending_events{}, committed_events{};
    std::uint64_t next_entity_id{}, next_scheduled_id{}, next_event_id{}, next_sequence{};
    std::uint64_t rng_state{}, state_hash{}, trace_hash{};
    std::uint64_t ant_count{}, colony_count{}, food_source_count{}, living_ants{};
    FoodLedger food_ledger;
    std::optional<EventKey> execution_watermark;
    std::uint64_t events_at_current_time{};
    bool operator==(const WorldSnapshot&) const = default;
};

// Single-threaded owner. Query results are detached values, never live pointers.
class WorldRuntime {
public:
    static constexpr std::uint32_t schema_version = 2;
    static constexpr std::uint32_t physics_version = 2;
    static constexpr std::size_t max_records = 65536;
    static constexpr std::size_t max_same_time_events = 1024;

    WorldRuntime(WorldId world, std::uint64_t seed, WorldConfig config = {}, RuntimeLimits limits = {});
    ~WorldRuntime();
    WorldRuntime(WorldRuntime&&) noexcept;
    WorldRuntime& operator=(WorldRuntime&&) noexcept;
    WorldRuntime(const WorldRuntime&) = delete;
    WorldRuntime& operator=(const WorldRuntime&) = delete;

    EntityId allocate_entity_id();
    ScheduledId schedule(const EventRequest& request);
    bool cancel(ScheduledId id);
    void advance_to(SimTime target);
    ColonyRef seed_colony();
    AntRef seed_ant(ColonyRef colony, const AntSeed& seed);
    FoodRef seed_food(PositionM position, FoodMass mass);
    ScheduledId submit(const ActionProposal& proposal);
    ScheduledId schedule_lifecycle(AntRef actor, SimTime at, LifeStage stage);

    [[nodiscard]] WorldSnapshot snapshot() const;
    // Cheap metadata query; hash fields are zero. snapshot() additionally computes audit hashes.
    [[nodiscard]] WorldSnapshot summary() const;
    [[nodiscard]] std::optional<AntState> query_ant(AntRef ref) const;
    [[nodiscard]] std::optional<Colony> query_colony(ColonyRef ref) const;
    [[nodiscard]] std::optional<FoodSource> query_food(FoodRef ref) const;
    [[nodiscard]] WorldConfig config() const;
    [[nodiscard]] std::vector<ScheduledEvent> pending_events() const;
    [[nodiscard]] std::vector<WorldEvent> committed_events() const;
    [[nodiscard]] std::vector<WorldEvent> events_after(EventId cursor, std::size_t limit) const;
    [[nodiscard]] std::vector<std::uint8_t> checkpoint() const;
    void restore(std::span<const std::uint8_t> bytes);

private:
    struct State;
    class Transaction;
    std::unique_ptr<State> state_;
    RuntimeLimits limits_;
    void resolve_actions(Transaction&, const std::vector<ScheduledEvent>&);
    void execute(Transaction&, const ScheduledEvent&);
    static std::vector<std::uint8_t> encode(const State&, std::size_t byte_limit);
    static std::unique_ptr<State> decode(std::span<const std::uint8_t>, const RuntimeLimits&);
};
} // namespace antworld
