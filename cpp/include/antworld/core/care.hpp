#pragma once
#include "antworld/core/entities.hpp"
#include <array>
#include <optional>
#include <vector>

namespace antworld {
// ENGINEERING_FIXTURE preferred speeds and separate handling clocks.
struct CareMotionProfile {
    double worker_unloaded_m_per_s{.020}, queen_unloaded_m_per_s{.006};
    double worker_loaded_m_per_s{.004}, queen_loaded_m_per_s{.003};
    SimTime pickup_duration{500}, placement_duration{500}, manipulation_duration{2000}, search_pause{1000};
    std::uint8_t search_steps{8};
    bool integrate_autonomy{};
    bool operator==(const CareMotionProfile&) const = default;
};
// B01/B02 support the capability and qualitative plasticity, not these coefficients.
// All numeric defaults are ENGINEERING_FIXTURE; no metabolic parameter is changed.
struct SpeciesCareProfile {
    SimTime decision_interval{60000}, bout_duration{10000}, worker_contact_duration{2000};
    SimTime social_memory_horizon{21600000};
    double care_probability{0.5}, worker_contact_probability{0.25}, maximum_inhibition{0.8};
    double perception_radius_m{0.006}, step_m{0.001}, arrangement_m{0.00025};
    // ENGINEERING_FIXTURE opt-in local persistence and one return to a visited pickup site.
    bool local_retrieval{};
    std::optional<CareMotionProfile> motion;
    bool operator==(const SpeciesCareProfile&) const = default;
};
enum class CareContext : std::uint8_t { FoundingQueen, EstablishedQueen, Worker };
struct IndividualCareProfile {
    CareContext context{CareContext::FoundingQueen};
    SimTime age_at_enrollment{}; // Declared fixture context, not a fabricated life history or rate multiplier.
    bool operator==(const IndividualCareProfile&) const = default;
};
struct EnvironmentCareProfile {
    double temperature_c{21}, relative_humidity{0.8}; // Assay metadata only; P04 is excluded.
    bool neutral_displacement_assay{};
    double arena_radius_m{}; // Optional care-only disc centered at the test origin.
    bool operator==(const EnvironmentCareProfile&) const = default;
};
enum class CareAct : std::uint8_t {
    Inactive, Walk, ApproachBrood, InspectBrood, ArrangeBrood, CleanBrood,
    TransportBrood, FeedBrood, CloseWorkerContact, CollectFood, DeliverFood,
    IngestFood, TransferNutrition, Excavate, HandleSoil, RevisitBroodSite,
    PickUpBrood, PlaceBrood, ReturnToCareShelter, Count
};
enum class ObservationPhase : std::uint8_t { Opportunity, Selected, Started, Completed, Interrupted };
struct BehaviorObservation {
    ObservationPhase phase{};
    CareAct act{};
    EntityId target;
    ScheduledId bout;
    SimTime began_at;
    bool duration_known{};
    PositionM destination{};
    bool operator==(const BehaviorObservation&) const = default;
};
struct RetrievalMemory {
    EntityId target;
    ScheduledId pickup_bout;
    PositionM pickup_site;
    bool operator==(const RetrievalMemory&) const = default;
};
struct CareState {
    IndividualCareProfile profile;
    PositionM familiar_shelter;
    bool enabled{}, active{}, has_worker_contact{};
    SimTime enrolled_at, began_at, last_worker_contact;
    std::uint64_t decisions{};
    CareAct act{CareAct::Inactive};
    EntityId target;
    PositionM destination;
    ScheduledId pending, bout;
    RetrievalMemory retrieval;
    PositionM grip_offset; // Continuous-contract translation from carrier to held brood.
    bool carrying_brood{}, returning{};
    std::uint8_t search_remaining{};
    bool operator==(const CareState&) const = default;
};
struct BehaviorWindow {
    SimTime begin, end;
    std::array<std::uint64_t, static_cast<std::size_t>(CareAct::Count)> selected{}, started{}, completed{}, interrupted{}, duration_ms{};
    std::array<std::uint64_t, 5> legacy_program_ms{};
    std::uint64_t care_program_ms{}, known_active_ms{}, known_inactive_ms{}, unknown_activity_ms{};
    std::uint64_t contact_opportunities{}, successful_contacts{}, unknown_duration_completions{};
    FoodMass transferred;
    bool operator==(const BehaviorWindow&) const = default;
};
} // namespace antworld
