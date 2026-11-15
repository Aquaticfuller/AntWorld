#pragma once

#include "antworld/core/types.hpp"
#include <optional>

namespace antworld {
struct WorkerActivityTiming {
    SimTime check_interval, minimum_program_time;
    bool operator==(const WorkerActivityTiming&) const = default;
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
    bool operator==(const EcologicalClosureConfig&) const = default;
};
} // namespace antworld
