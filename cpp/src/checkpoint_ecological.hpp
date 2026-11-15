#pragma once

#include "checkpoint_codec.hpp"
#include "ecological_internal.hpp"

namespace antworld::detail {
inline constexpr auto ecological_magic = UINT64_C(0x4d54504b435741); // AWCKPTM
inline constexpr unsigned ecological_schema = 22, ecological_physics = 24;
inline constexpr unsigned portable_ecological_physics = 25;
inline constexpr unsigned suppressed_hatch_physics = 26;
inline constexpr unsigned micro_world_schema = 23, micro_world_physics = 27;
inline constexpr unsigned micro_world_no_hatch_physics = 28;
inline constexpr unsigned portable_micro_world_physics = 29;
inline constexpr unsigned portable_micro_world_no_hatch_physics = 30;
inline constexpr unsigned worker_timing_schema = 24, worker_timing_physics = 31;

inline bool micro_world_version(unsigned version) {
    return version==micro_world_physics || version==micro_world_no_hatch_physics ||
           version==portable_micro_world_physics || version==portable_micro_world_no_hatch_physics;
}

inline unsigned ecological_version(const EcologicalClosureConfig& c) {
    if (c.worker_activity_timing) return worker_timing_physics;
    if (c.portable_care_motion)
        return c.suppress_foundress_hatch_cue?portable_micro_world_no_hatch_physics:portable_micro_world_physics;
    if (c.brood_space) return c.suppress_foundress_hatch_cue?micro_world_no_hatch_physics:micro_world_physics;
    if (c.suppress_foundress_hatch_cue) return suppressed_hatch_physics;
    return c.portable_field?portable_ecological_physics:ecological_physics;
}

inline void write_ecological(Writer& w, const EcologicalClosureConfig& c) {
    w.put(c.distance_clock, 1); w.put(c.floor_space, 1);
    w.put(c.recruitment, 1); w.put(c.activity_cost, 1);
    w.real(c.unloaded_m_per_s); w.real(c.loaded_m_per_s);
    w.time(c.soil_handling); w.time(c.cue_lifetime);
    w.put(c.cue_minimum_carbs_ug); w.put(c.water_sip_ug);
    w.put(c.cue_response_ppm, 4); w.put(c.first_ration_ppm, 4);
    if (c.worker_activity_timing) {
        w.time(c.worker_activity_timing->check_interval);
        w.time(c.worker_activity_timing->minimum_program_time);
    }
}
inline EcologicalClosureConfig read_ecological(Reader& r, const WorldConfig& world, unsigned version) {
    EcologicalClosureConfig c;
    c.distance_clock = r.flag(); c.floor_space = r.flag();
    c.recruitment = r.flag(); c.activity_cost = r.flag();
    c.unloaded_m_per_s = r.real(); c.loaded_m_per_s = r.real();
    c.soil_handling = r.time(); c.cue_lifetime = r.time();
    c.cue_minimum_carbs_ug = r.get(); c.water_sip_ug = r.get();
    c.cue_response_ppm = static_cast<std::uint32_t>(r.get(4));
    c.first_ration_ppm = static_cast<std::uint32_t>(r.get(4));
    c.portable_field = version >= portable_ecological_physics;
    c.suppress_foundress_hatch_cue = version == suppressed_hatch_physics ||
        version == micro_world_no_hatch_physics || version == portable_micro_world_no_hatch_physics;
    c.brood_space = micro_world_version(version) || version == worker_timing_physics;
    c.portable_care_motion = version == portable_micro_world_physics ||
        version == portable_micro_world_no_hatch_physics || version == worker_timing_physics;
    if (version == worker_timing_physics) c.worker_activity_timing = WorkerActivityTiming{r.time(), r.time()};
    validate_ecological_closure(c, world);
    return c;
}
} // namespace antworld::detail
