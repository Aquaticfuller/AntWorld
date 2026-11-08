#pragma once

#include "antworld/core/types.hpp"

namespace antworld {
enum class Phase : std::uint32_t {
    Input, Environment, Perception, Proposals, Resolution, Commit, Publish, Reschedule
};

struct EventKey {
    SimTime time;
    Phase phase{Phase::Environment};
    std::uint32_t priority{};
    std::uint64_t tie{}, sequence{};
    auto operator<=>(const EventKey&) const = default;
};

// Diagnostic actions exercise infrastructure only. They do not represent ants.
enum class DiagnosticAction : std::uint8_t { Record, DrawRandom, RepeatSameTime };
struct EventRequest {
    SimTime time;
    Phase phase{Phase::Environment};
    std::uint32_t priority{};
    std::uint64_t tie{}, payload{};
    DiagnosticAction action{DiagnosticAction::Record};
};
struct ScheduledEvent {
    ScheduledId id;
    EventKey key;
    DiagnosticAction action{};
    std::uint64_t payload{};
    bool operator==(const ScheduledEvent&) const = default;
};
struct WorldEvent {
    EventId id;
    WorldId world;
    SimTime time;
    ScheduledId source;
    DiagnosticAction action{};
    std::uint64_t revision{}, payload{}, random_value{};
    bool operator==(const WorldEvent&) const = default;
};
} // namespace antworld
