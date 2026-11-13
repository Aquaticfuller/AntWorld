#pragma once

#include "motion_numeric.hpp"
#include "antworld/core/ecological_closure.hpp"
#include <algorithm>
#include <stdexcept>

namespace antworld::detail {
inline void validate_ecological_closure(const EcologicalClosureConfig& c, const WorldConfig& world) {
    if (!world.continuous_spatial_motion || !std::isfinite(c.unloaded_m_per_s) ||
        !std::isfinite(c.loaded_m_per_s) || c.loaded_m_per_s < 0.0001 ||
        c.loaded_m_per_s > c.unloaded_m_per_s || c.unloaded_m_per_s > world.max_speed_m_per_s ||
        c.soil_handling.milliseconds < 1 || c.soil_handling.milliseconds > 86400000 ||
        c.cue_lifetime.milliseconds < 1 || c.cue_lifetime.milliseconds > 86400000 ||
        !c.cue_minimum_carbs_ug || c.cue_minimum_carbs_ug > 1000000000 || c.water_sip_ug > 1000000000 ||
        c.cue_response_ppm > 1000000 || c.first_ration_ppm > 1000000)
        throw std::invalid_argument("invalid ecological closure ENGINEERING_FIXTURE");
}
inline SimTime segment_duration(const EcologicalClosureConfig& c, PositionM from, PositionM to, bool loaded) {
    const auto speed = loaded ? c.loaded_m_per_s : c.unloaded_m_per_s;
    const auto milliseconds = std::ceil(distance(from, to) * 1000 / speed);
    if (!std::isfinite(milliseconds) || milliseconds >= static_cast<double>(INT64_MAX))
        throw std::overflow_error("physical travel exceeds the simulation clock");
    return {std::max<std::int64_t>(1, static_cast<std::int64_t>(milliseconds))};
}
inline bool timed_activity(const auto& s) { return s.ecological && s.ecological->activity_cost; }
inline bool sip_source(const auto& s, PositionM position, FoodMass mass) {
    return s.ecological && s.ecological->water_sip_ug && s.surface &&
           position.y < s.surface->config.origin_m.y && mass.water_ug &&
           mass.total_ug() == mass.water_ug;
}
} // namespace antworld::detail
