#pragma once

#include "antworld/core/types.hpp"
#include <optional>

namespace antworld {
struct WorkerActivityTiming {
    SimTime check_interval, minimum_program_time;
    bool operator==(const WorkerActivityTiming&) const = default;
};

enum class NestScoring : std::uint8_t { Original, Hex, Reinforcement, SpatialDemand };
// FoodDelivered carries this tag for a blocked carrier's off-floor oral handoff in Physics 42+.
inline constexpr std::uint64_t wall_delivery_payload=1;

struct NestDynamics {
    bool worker_motor{};
    NestScoring excavation{NestScoring::Original};
    bool operator==(const NestDynamics&) const = default;
};

struct TrailExposure {
    bool ventilated{};
    bool porous{};
    bool operator==(const TrailExposure&) const = default;
};

enum class FoundingNutrition : std::uint8_t { Original, LocalFeeding, BroodBudget, SustainedSupply, ProtectedFounding, LocalExcavation, CallowHydration, MealSearch, SocialCrop, CropExchange, ChamberReturn, MouthRange, CheckedLarvalOffer, LocalDeparture, MealRendezvous, FirstMeal, ResponsiveMeal };

// ENGINEERING_FIXTURE for a single founding chamber and a separate handoff site.
// The brood site is familiar to the founding queen and her own offspring.
struct FoundingHabitat {
    PositionM brood_site;
    std::uint64_t pantry_buffer_ug{};
    bool alternate_berth{}; // Physics 37. Seek another locally reachable depot contact.
    bool sealed_chamber{}; // Physics 38. Posterior laying site and close brood handling.
    bool anatomical{}; // Physics 39. Body-relative birth, contact and swept clearance.
    bool mouth_access{}; // Physics 40. Local oral access to supplies in the sealed pocket.
    bool adult_offers{}; // Physics 41. A payable offer at mutual oral contact.
    bool wall_handoff{}; // Physics 42. A blocked returning carrier can unload from a real mouth contact.
    bool anatomical_handoff{}; // Physics 43. Use mouth reach at that handoff and keep the actual connector.
    bool familiar_return{}; // Physics 44. An empty returner can recognize its own mouth-contact berth.
    // Physics 45. Bounded behavioral intervals and experimental surface exposure.
    std::optional<TrailExposure> variable_conditions{};
    FoundingNutrition nutrition{FoundingNutrition::Original}; // Physics 46. Local feeding and optional brood allocation.
    bool operator==(const FoundingHabitat&) const = default;
};

// Independent opt-in hypotheses. All numbers are ENGINEERING_FIXTURE.
struct EcologicalClosureConfig {
    bool distance_clock{}, floor_space{}, recruitment{}, activity_cost{};
    double unloaded_m_per_s{0.005}, loaded_m_per_s{0.0025};
    SimTime soil_handling{5000}, cue_lifetime{120000};
    std::uint64_t cue_minimum_carbs_ug{50}, water_sip_ug{};
    std::uint32_t cue_response_ppm{350000}, first_ration_ppm{};
    bool portable_field{}; // Physics 25 fixes the numerical representation of the same local field.
    bool suppress_foundress_hatch_cue{}; // Physics 26. Matched founding assay only.
    bool brood_space{}; // Physics 27. Local single-layer brood placement and handling envelope.
    bool portable_care_motion{}; // Physics 29. Fixed binary64 arithmetic for timed care.
    std::optional<WorkerActivityTiming> worker_activity_timing; // Physics 31. Worker-only review clocks.
    bool local_nest_activity{}; // Physics 32. Paid rest relocation and local floor demand.
    std::optional<NestDynamics> nest_dynamics; // Physics 33. Independent motor and dig scoring.
    bool local_traffic{}; // Physics 34. Experimental local contact approaches and adult body clearance.
    bool yield_to_loaded{}; // Physics 35. A stationary worker can clear a locally blocked return.
    bool local_pantry_checks{}; // Physics 35. A locally observed low food store can prompt foraging.
    std::optional<FoundingHabitat> founding_habitat; // Physics 36. Familiar brood site and local working buffer.
    bool operator==(const EcologicalClosureConfig&) const = default;
};
} // namespace antworld
