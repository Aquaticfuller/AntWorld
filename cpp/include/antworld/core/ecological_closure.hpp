#pragma once

#include "antworld/core/types.hpp"

namespace antworld {
// Independent opt-in hypotheses. All numbers are ENGINEERING_FIXTURE.
struct EcologicalClosureConfig {
    bool distance_clock{}, floor_space{}, recruitment{}, activity_cost{};
    double unloaded_m_per_s{0.005}, loaded_m_per_s{0.0025};
    SimTime soil_handling{5000}, cue_lifetime{120000};
    std::uint64_t cue_minimum_carbs_ug{50}, water_sip_ug{};
    std::uint32_t cue_response_ppm{350000}, first_ration_ppm{};
    bool portable_field{}; // Physics 25 fixes the numerical representation of the same local field.
    bool suppress_foundress_hatch_cue{}; // Physics 26. Matched founding assay only.
    bool operator==(const EcologicalClosureConfig&) const = default;
};
} // namespace antworld
