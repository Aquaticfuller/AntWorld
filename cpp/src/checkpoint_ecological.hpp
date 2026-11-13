#pragma once

#include "checkpoint_codec.hpp"
#include "ecological_internal.hpp"

namespace antworld::detail {
inline constexpr auto ecological_magic = UINT64_C(0x4d54504b435741); // AWCKPTM
inline constexpr unsigned ecological_schema = 22, ecological_physics = 24;

inline void write_ecological(Writer& w, const EcologicalClosureConfig& c) {
    w.put(c.distance_clock, 1); w.put(c.floor_space, 1);
    w.put(c.recruitment, 1); w.put(c.activity_cost, 1);
    w.real(c.unloaded_m_per_s); w.real(c.loaded_m_per_s);
    w.time(c.soil_handling); w.time(c.cue_lifetime);
    w.put(c.cue_minimum_carbs_ug); w.put(c.water_sip_ug);
    w.put(c.cue_response_ppm, 4); w.put(c.first_ration_ppm, 4);
}
inline EcologicalClosureConfig read_ecological(Reader& r, const WorldConfig& world) {
    EcologicalClosureConfig c;
    c.distance_clock = r.flag(); c.floor_space = r.flag();
    c.recruitment = r.flag(); c.activity_cost = r.flag();
    c.unloaded_m_per_s = r.real(); c.loaded_m_per_s = r.real();
    c.soil_handling = r.time(); c.cue_lifetime = r.time();
    c.cue_minimum_carbs_ug = r.get(); c.water_sip_ug = r.get();
    c.cue_response_ppm = static_cast<std::uint32_t>(r.get(4));
    c.first_ration_ppm = static_cast<std::uint32_t>(r.get(4));
    validate_ecological_closure(c, world);
    return c;
}
} // namespace antworld::detail
