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
        !std::isfinite(e.temperature_c) || !probability(e.relative_humidity) ||
        !std::isfinite(e.arena_radius_m) || e.arena_radius_m<0 ||
        (!c.motion && (e.neutral_displacement_assay || e.arena_radius_m!=0)))
        throw std::invalid_argument("invalid ENGINEERING_FIXTURE care profiles");
    if (!c.motion) return;
    const auto& m=*c.motion;
    const auto speed=[&](double v) {
        return std::isfinite(v) && v>0 && c.step_m/std::min(v,w.max_speed_m_per_s)<=3600;
    };
    const auto interval=[](SimTime t) { return t.milliseconds>=1 && t.milliseconds<=3600000; };
    if (!c.local_retrieval || (m.integrate_autonomy && e.neutral_displacement_assay) ||
        !speed(m.worker_unloaded_m_per_s) || !speed(m.queen_unloaded_m_per_s) ||
        !speed(m.worker_loaded_m_per_s) || !speed(m.queen_loaded_m_per_s) ||
        !interval(m.pickup_duration) || !interval(m.placement_duration) || !interval(m.manipulation_duration) ||
        !interval(m.search_pause) || !m.search_steps || m.search_steps>64)
        throw std::invalid_argument("invalid ENGINEERING_FIXTURE care motion");
}
inline bool brood(LifeStage stage) { return stage==LifeStage::Egg || stage==LifeStage::Larva || stage==LifeStage::Pupa; }
inline bool handles_brood(CareAct a) {
    return (a>=CareAct::InspectBrood && a<=CareAct::FeedBrood) || a==CareAct::PickUpBrood || a==CareAct::PlaceBrood;
}
inline bool care_motion(CareAct act) {
    return act==CareAct::Walk || act==CareAct::ApproachBrood || act==CareAct::TransportBrood ||
           act==CareAct::ArrangeBrood || act==CareAct::RevisitBroodSite || act==CareAct::ReturnToCareShelter;
}
inline PositionM toward(PositionM a, PositionM b, double step) {
    const auto d=distance(a,b); if (d<=step) return b;
    return {a.x+(b.x-a.x)*step/d,a.y+(b.y-a.y)*step/d,a.z+(b.z-a.z)*step/d};
}
inline bool care_owned(const auto& s, EntityId id) { return s.care.contains(id) && s.care.at(id).enabled; }
inline bool integrated_care(const auto& s) {
    return s.care_profile && s.care_profile->motion && s.care_profile->motion->integrate_autonomy;
}
inline bool inside_care_arena(const EnvironmentCareProfile& environment,PositionM p) {
    return environment.arena_radius_m==0 || std::hypot(p.x,p.z)<=environment.arena_radius_m;
}
inline bool foreign_assay_stage(const auto& s,LifeStage stage) {
    return s.care_profile->motion && s.care_environment.neutral_displacement_assay &&
           (stage==LifeStage::Larva || stage==LifeStage::Pupa);
}
inline bool foreign_assay_act(CareAct act,ObservationPhase phase=ObservationPhase::Selected) {
    return act==CareAct::ApproachBrood || act==CareAct::PickUpBrood ||
           act==CareAct::TransportBrood || act==CareAct::PlaceBrood ||
           (phase==ObservationPhase::Opportunity && act==CareAct::InspectBrood);
}
inline bool surface_care_clear(const auto& s,PositionM from,PositionM to) {
    if (!s.care_profile->motion || !s.surface || s.geometry) return true;
    const auto a=s.surface->locate(from),b=s.surface->locate(to);
    if (!a || !b) return false;
    // Cell centers are authoritative for surface-only worlds. Reject corner cutting.
    for (auto x=std::min(a->x,b->x);x<=std::max(a->x,b->x);++x)
        for (auto z=std::min(a->z,b->z);z<=std::max(a->z,b->z);++z)
            if (!s.surface->open({x,z})) return false;
    return true;
}
inline PositionM care_toward(const auto& s,PositionM a,PositionM b,double step) {
    if (!s.care_profile->motion || !s.surface || s.geometry) return toward(a,b,step);
    const auto cell=s.surface->locate(a);
    if (!cell || s.surface->config.cell_size_m>step) return a;
    auto best=a;
    auto remaining=distance(a,b);
    for (const auto candidate:std::array<Cell,4>{{{cell->x+1,cell->z},{cell->x-1,cell->z},
                                                 {cell->x,cell->z+1},{cell->x,cell->z-1}}}) {
        if (!s.surface->open(candidate)) continue;
        const auto p=s.surface->center(candidate);
        const auto d=distance(p,b);
        if (d<remaining) { best=p; remaining=d; }
    }
    return best;
}
inline SimTime care_duration(const SpeciesCareProfile& cfg,const WorldConfig& world,Caste caste,
                             CareAct act,PositionM from,PositionM to) {
    if (act==CareAct::Inactive) return cfg.decision_interval;
    if (act==CareAct::CloseWorkerContact) return cfg.worker_contact_duration;
    if (!cfg.motion) return cfg.bout_duration;
    const auto& m=*cfg.motion;
    if (act==CareAct::PickUpBrood) return m.pickup_duration;
    if (act==CareAct::PlaceBrood) return m.placement_duration;
    if (!care_motion(act)) return m.manipulation_duration;
    const bool queen=caste==Caste::Queen;
    const auto preferred=act==CareAct::TransportBrood?
        (queen?m.queen_loaded_m_per_s:m.worker_loaded_m_per_s):
        (queen?m.queen_unloaded_m_per_s:m.worker_unloaded_m_per_s);
    const auto ms=static_cast<std::int64_t>(std::ceil(1000*distance(from,to)/std::min(preferred,world.max_speed_m_per_s)));
    return {std::max(ms,act==CareAct::ArrangeBrood?m.manipulation_duration.milliseconds:1)};
}
inline std::int32_t care_extent(const auto& s, std::int32_t body, CareAct act) {
    return s.geometry && (act==CareAct::TransportBrood || act==CareAct::PickUpBrood || act==CareAct::PlaceBrood)?
        std::max(body,s.geometry->config.loaded_half_q):body;
}
} // namespace antworld::detail
