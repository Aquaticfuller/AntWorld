#pragma once

#include "motion_numeric.hpp"
#include "antworld/core/ecological_closure.hpp"
#include "antworld/core/entities.hpp"
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
        c.cue_response_ppm > 1000000 || c.first_ration_ppm > 1000000 ||
        (c.suppress_foundress_hatch_cue && !c.portable_field) ||
        (c.brood_space && !c.portable_field) || (c.portable_care_motion && !c.brood_space))
        throw std::invalid_argument("invalid ecological closure ENGINEERING_FIXTURE");
    if (c.local_nest_activity && (!c.portable_care_motion || c.suppress_foundress_hatch_cue || !c.activity_cost || !c.floor_space))
        throw std::invalid_argument("local nest activity requires the portable active MicroWorld profile");
    if (c.nest_dynamics && (!c.local_nest_activity || !c.distance_clock ||
        c.nest_dynamics->excavation > NestScoring::SpatialDemand ||
        (!c.nest_dynamics->worker_motor && c.nest_dynamics->excavation == NestScoring::Original)))
        throw std::invalid_argument("nest dynamics requires the physical R0 treatment and an explicit mechanism");
    if (c.local_traffic && (!c.nest_dynamics || !c.nest_dynamics->worker_motor))
        throw std::invalid_argument("local traffic requires the worker motor");
    if ((c.yield_to_loaded || c.local_pantry_checks) && !c.local_traffic)
        throw std::invalid_argument("nursery work and traffic policy requires local traffic");
    if (const auto& timing = c.worker_activity_timing;
        timing && (!c.portable_care_motion || c.suppress_foundress_hatch_cue ||
                   timing->check_interval.milliseconds < 60000 ||
                   timing->minimum_program_time < timing->check_interval ||
                   timing->minimum_program_time.milliseconds > 6 * 3600000))
        throw std::invalid_argument("invalid MicroWorld worker review timing ENGINEERING_FIXTURE");
}
inline bool local_nest_activity(const auto& s) {
    return s.ecological && s.ecological->local_nest_activity;
}
inline bool worker_motor(const auto& s) {
    return s.ecological && s.ecological->nest_dynamics && s.ecological->nest_dynamics->worker_motor;
}
inline bool local_traffic(const auto& s) {
    return s.ecological && s.ecological->local_traffic;
}
inline bool yield_to_loaded(const auto& s) {
    return s.ecological && s.ecological->yield_to_loaded;
}
inline NestScoring nest_scoring(const auto& s) {
    return s.ecological && s.ecological->nest_dynamics ? s.ecological->nest_dynamics->excavation : NestScoring::Original;
}
inline const WorkerActivityTiming* worker_timing(const auto& s, Caste caste) {
    return caste == Caste::Worker && s.ecological && s.ecological->worker_activity_timing
        ? &*s.ecological->worker_activity_timing : nullptr;
}
inline SimTime segment_duration(const EcologicalClosureConfig& c, PositionM from, PositionM to, bool loaded) {
    const auto speed = loaded ? c.loaded_m_per_s : c.unloaded_m_per_s;
    const auto milliseconds = std::ceil(distance(from, to) * 1000 / speed);
    if (!std::isfinite(milliseconds) || milliseconds >= static_cast<double>(INT64_MAX))
        throw std::overflow_error("physical travel exceeds the simulation clock");
    return {std::max<std::int64_t>(1, static_cast<std::int64_t>(milliseconds))};
}
inline bool timed_activity(const auto& s) { return s.ecological && s.ecological->activity_cost; }
inline bool bounded_brood_space(const auto& s) { return s.ecological && s.ecological->brood_space; }
inline bool hatch_cue_enabled(const auto& s) {
    return s.founding && s.founding->profile.early_access && s.founding->profile.early_access->local_hatch_cue &&
           (!s.ecological || !s.ecological->suppress_foundress_hatch_cue);
}
inline bool sip_source(const auto& s, PositionM position, FoodMass mass) {
    return s.ecological && s.ecological->water_sip_ug && s.surface &&
           position.y < s.surface->config.origin_m.y && mass.water_ug &&
           mass.total_ug() == mass.water_ug;
}
} // namespace antworld::detail
