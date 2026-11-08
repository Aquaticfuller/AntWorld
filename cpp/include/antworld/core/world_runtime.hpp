#pragma once

#include "antworld/core/event.hpp"

#include <memory>
#include <span>
#include <vector>

namespace antworld {
struct WorldSnapshot {
    WorldId world;
    SimTime now;
    std::uint64_t seed{}, revision{}, pending_events{}, committed_events{};
    std::uint64_t next_entity_id{}, next_scheduled_id{}, next_event_id{}, next_sequence{};
    std::uint64_t rng_state{}, state_hash{}, trace_hash{};
    bool operator==(const WorldSnapshot&) const = default;
};

// Single-threaded owner. Query results are detached values, never live pointers.
class WorldRuntime {
public:
    static constexpr std::uint32_t schema_version = 1;
    static constexpr std::uint32_t physics_version = 1;
    static constexpr std::size_t max_records = 65536;
    static constexpr std::size_t max_same_time_events = 1024;

    WorldRuntime(WorldId world, std::uint64_t seed);
    ~WorldRuntime();
    WorldRuntime(WorldRuntime&&) noexcept;
    WorldRuntime& operator=(WorldRuntime&&) noexcept;
    WorldRuntime(const WorldRuntime&) = delete;
    WorldRuntime& operator=(const WorldRuntime&) = delete;

    EntityId allocate_entity_id();
    ScheduledId schedule(const EventRequest& request);
    bool cancel(ScheduledId id);
    void advance_to(SimTime target);

    [[nodiscard]] WorldSnapshot snapshot() const;
    [[nodiscard]] std::vector<ScheduledEvent> pending_events() const;
    [[nodiscard]] std::vector<WorldEvent> committed_events() const;
    [[nodiscard]] std::vector<std::uint8_t> checkpoint() const;
    void restore(std::span<const std::uint8_t> bytes);

private:
    struct State;
    std::unique_ptr<State> state_;
    static ScheduledId schedule_in(State&, const EventRequest&);
    static std::vector<std::uint8_t> encode(const State&);
    static std::unique_ptr<State> decode(std::span<const std::uint8_t>);
};
} // namespace antworld
