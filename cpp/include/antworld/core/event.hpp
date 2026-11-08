#pragma once

#include "antworld/core/entities.hpp"
#include "antworld/core/behavior.hpp"
#include "antworld/core/physiology.hpp"
#include "antworld/core/geometry.hpp"

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
    enum class Kind : std::uint8_t { Diagnostic, Move, CollectFood, Lifecycle, Wake, DeliverFood, Rest, TrailMaintenance,
        Physiology, NutritionWake, IngestCargo, WithdrawNest, Trophallaxis, SoilAction, ExcavationWake } kind{};
    EntityId actor;
    ResourceId resource;
    PositionM destination;
    std::uint64_t requested_ug{};
    SimTime issued_at;
    std::uint64_t observed_position_revision{};
    LifeStage stage{};
    bool operator==(const ScheduledEvent&) const = default;
};
enum class FactKind : std::uint8_t {
    Diagnostic, ColonySeeded, AntSeeded, FoodSeeded, Moved, FoodCollected,
    ActionRejected, StageChanged, AntDied, SurfaceConfigured, ForagingStarted,
    ForagingDecision, FoodDelivered, Rested, TrailMaintenance,
    PhysiologyEnabled, PhysiologyUpdated, BehaviorChanged, NutritionDecision, CargoIngested, NestIngested, NutritionTransferred,
    GeometryConfigured, SoilExcavated, SoilDropped, SoilPickedUp, SoilFilled, ExcavationDecision
};
struct WorldEvent {
    EventId id;
    WorldId world;
    SimTime time;
    ScheduledId source;
    DiagnosticAction action{};
    std::uint64_t revision{}, payload{}, random_value{};
    FactKind kind{FactKind::Diagnostic};
    EntityId actor;
    ColonyId colony;
    ResourceId resource;
    PositionM position;
    FoodMass transferred;
    LifeStage stage{};
    Outcome outcome{Outcome::Success};
    BehaviorMode mode{BehaviorMode::Explore};
    DecisionReason reason{DecisionReason::None};
    double deposited_units{};
    bool forgot_memory{};
    bool operator==(const WorldEvent&) const = default;
};
} // namespace antworld
