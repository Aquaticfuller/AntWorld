#pragma once

#include "antworld/core/entities.hpp"
#include "antworld/core/behavior.hpp"
#include "antworld/core/physiology.hpp"
#include "antworld/core/geometry.hpp"
#include "antworld/core/care.hpp"
#include <span>

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
        Physiology, NutritionWake, IngestCargo, WithdrawNest, Trophallaxis, SoilAction, ExcavationWake, AutonomyWake,
        Reproduction, ResourceRelease, ReturnProtein, CareWake, CareBegin, CareEnd } kind{};
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
    GeometryConfigured, SoilExcavated, SoilDropped, SoilPickedUp, SoilFilled, ExcavationDecision, FoodPlaced,
    SocialConfigured, AutonomyChanged, AutonomyDecision, LongTermConfigured, ReproductionEnabled,
    ReproductionAttempt, AntBorn, ResourceCycleConfigured, ResourceReleased, ProteinRecycled,
    BiologyConfigured, CareProgramChanged, CareTick, BiologicalObservation, BroodMoved,
    FoundingConfigured, FoundingReserveSeeded, FoundingEggFunded, FoundingLipidConverted, FoundingRation,
    FoundingLipidMobilized, FoundingHatchCue
};
// F1-R1 CareWake annotation. Selection and material transfer are separate facts.
enum class FoundingCareWake : std::uint8_t { Ordinary, Expired, Unavailable, Repeat };
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
    BehaviorObservation observation; // Encoded only for BiologicalObservation facts.
    bool operator==(const WorldEvent&) const = default;
};
[[nodiscard]] constexpr bool founding_fact(FactKind kind) {
    return kind >= FactKind::FoundingConfigured && kind <= FactKind::FoundingHatchCue;
}
[[nodiscard]] constexpr bool founding_early_fact(FactKind kind) {
    return kind == FactKind::FoundingLipidMobilized || kind == FactKind::FoundingHatchCue;
}
// A participant ID, as opposed to a numeric dose, material quantity or fingerprint.
[[nodiscard]] inline EntityId related_individual(const WorldEvent& e) {
    if (e.kind == FactKind::BiologicalObservation) return e.observation.target;
    switch (e.kind) {
    case FactKind::NutritionTransferred: case FactKind::AntBorn: case FactKind::BroodMoved:
    case FactKind::FoundingEggFunded: case FactKind::FoundingRation: case FactKind::FoundingHatchCue: return {e.payload};
    default: return {};
    }
}
[[nodiscard]] inline bool valid_founding_payload(const WorldEvent& e) {
    if (e.resource.value || e.outcome != Outcome::Success || e.action != DiagnosticAction::Record ||
        e.deposited_units != 0 || e.forgot_memory || e.mode != BehaviorMode::Explore || e.reason != DecisionReason::None)
        return false;
    const auto dry_packet = !e.transferred.carbs_ug && !e.transferred.other_ug;
    switch (e.kind) {
    case FactKind::FoundingConfigured:
        return !e.actor.value && !e.colony.value && !e.source.value && e.time == SimTime{} &&
               e.stage == LifeStage::Egg && e.position == PositionM{} && e.random_value >= 1 && e.random_value <= 3 &&
               e.transferred == FoodMass{};
    case FactKind::FoundingReserveSeeded:
        return e.actor.value && e.colony.value && !e.source.value && e.time == SimTime{} && e.stage == LifeStage::Adult &&
               e.payload && !e.random_value && dry_packet && e.transferred.protein_ug && e.transferred.water_ug;
    case FactKind::FoundingEggFunded:
        return e.actor.value && e.colony.value && e.source.value && e.stage == LifeStage::Adult && e.payload &&
               e.payload != e.actor.value && e.random_value && e.transferred == FoodMass{};
    case FactKind::FoundingLipidConverted:
        return e.actor.value && e.colony.value && (e.source.value || e.time == SimTime{}) && e.stage < LifeStage::Dead &&
               e.payload && e.random_value && e.transferred == FoodMass{};
    case FactKind::FoundingRation:
        return e.actor.value && e.colony.value && e.source.value && e.stage == LifeStage::Adult && e.payload &&
               e.payload != e.actor.value && dry_packet && (e.random_value || e.transferred.protein_ug || e.transferred.water_ug);
    case FactKind::FoundingLipidMobilized:
        return e.actor.value && e.colony.value && e.source.value && e.stage == LifeStage::Larva && e.payload &&
               e.random_value && e.transferred == FoodMass{};
    case FactKind::FoundingHatchCue:
        return e.actor.value && e.colony.value && e.source.value && e.stage == LifeStage::Adult && e.payload &&
               e.payload != e.actor.value && e.random_value && e.transferred == FoodMass{};
    default: return false;
    }
}
[[nodiscard]] inline bool valid_founding_care_wake(const WorldEvent& e) {
    return e.kind == FactKind::CareTick && e.payload == static_cast<std::uint64_t>(ScheduledEvent::Kind::CareWake) &&
           e.random_value > 0 && e.random_value <= static_cast<std::uint64_t>(FoundingCareWake::Repeat) &&
           e.actor.value && e.source.value && e.stage == LifeStage::Adult && e.outcome == Outcome::Success &&
           e.action == DiagnosticAction::Record && e.transferred == FoodMass{};
}
// Canonical fact payload codec. It is not a full-world recovery format.
std::vector<std::uint8_t> encode_event(const WorldEvent&);
WorldEvent decode_event(std::span<const std::uint8_t>);
} // namespace antworld
