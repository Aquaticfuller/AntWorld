#pragma once
#include "state.hpp"

namespace antworld::detail {
inline void validate_care_profile(const SpeciesCareProfile& c, const EnvironmentCareProfile& e, const WorldConfig& w) {
    const auto probability=[](double p) { return std::isfinite(p) && p>=0 && p<=1; };
    if (c.decision_interval.milliseconds<1 || c.decision_interval.milliseconds>86400000 ||
        c.bout_duration.milliseconds<1 || c.bout_duration.milliseconds>3600000 ||
        c.worker_contact_duration.milliseconds<1 || c.worker_contact_duration.milliseconds>3600000 ||
        c.social_memory_horizon.milliseconds<1 || c.social_memory_horizon.milliseconds>2592000000LL ||
        !probability(c.care_probability) || !probability(c.worker_contact_probability) || !probability(c.maximum_inhibition) ||
        !std::isfinite(c.perception_radius_m) || c.perception_radius_m<w.contact_distance_m || c.perception_radius_m>0.1 ||
        !std::isfinite(c.step_m) || c.step_m<=0 || c.step_m>c.perception_radius_m ||
        !std::isfinite(c.arrangement_m) || c.arrangement_m<=0 || c.arrangement_m>w.contact_distance_m ||
        c.step_m/(static_cast<double>(c.bout_duration.milliseconds)/1000)>w.max_speed_m_per_s ||
        c.arrangement_m/(static_cast<double>(c.bout_duration.milliseconds)/1000)>w.max_speed_m_per_s ||
        !std::isfinite(e.temperature_c) || !probability(e.relative_humidity))
        throw std::invalid_argument("invalid ENGINEERING_FIXTURE care profiles");
}
inline bool brood(LifeStage stage) { return stage==LifeStage::Egg || stage==LifeStage::Larva || stage==LifeStage::Pupa; }
inline bool handles_brood(CareAct a) { return a>=CareAct::InspectBrood && a<=CareAct::FeedBrood; }
inline bool care_motion(CareAct act) {
    return act==CareAct::Walk || act==CareAct::ApproachBrood || act==CareAct::TransportBrood ||
           act==CareAct::ArrangeBrood || act==CareAct::RevisitBroodSite;
}
inline PositionM toward(PositionM a, PositionM b, double step) {
    const auto d=distance(a,b); if (d<=step) return b;
    return {a.x+(b.x-a.x)*step/d,a.y+(b.y-a.y)*step/d,a.z+(b.z-a.z)*step/d};
}
inline bool care_owned(const auto& s, EntityId id) { return s.care.contains(id) && s.care.at(id).enabled; }
inline std::int32_t care_extent(const auto& s, std::int32_t body, CareAct act) {
    return s.geometry && act==CareAct::TransportBrood?std::max(body,s.geometry->config.loaded_half_q):body;
}
} // namespace antworld::detail
