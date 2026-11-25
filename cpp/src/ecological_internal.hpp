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
    if (const auto& habitat=c.founding_habitat; habitat) {
        const auto& p=habitat->brood_site;
        if (!c.local_pantry_checks || !c.recruitment || !c.worker_activity_timing ||
            (habitat->sealed_chamber && !habitat->alternate_berth) ||
            (habitat->anatomical && !habitat->sealed_chamber) ||
            (habitat->mouth_access && !habitat->anatomical) || (habitat->adult_offers && !habitat->mouth_access) ||
            (habitat->wall_handoff && !habitat->adult_offers) ||
            (habitat->anatomical_handoff && !habitat->wall_handoff) ||
            (habitat->familiar_return && !habitat->anatomical_handoff) ||
            (habitat->variable_conditions && (!habitat->anatomical_handoff || habitat->familiar_return)) ||
            habitat->nutrition > FoundingNutrition::TripLoad ||
            (habitat->nutrition != FoundingNutrition::Original && !habitat->variable_conditions) ||
            !habitat->pantry_buffer_ug || habitat->pantry_buffer_ug>1'000'000'000 ||
            !std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z) ||
            p.x<world.min_m.x || p.y<world.min_m.y || p.z<world.min_m.z ||
            p.x>world.max_m.x || p.y>world.max_m.y || p.z>world.max_m.z)
            throw std::invalid_argument("invalid founding habitat or local buffer");
    }
    if (const auto& timing = c.worker_activity_timing;
        timing && (!c.portable_care_motion || c.suppress_foundress_hatch_cue ||
                   timing->check_interval.milliseconds < 60000 ||
                   timing->minimum_program_time < timing->check_interval ||
                   timing->minimum_program_time.milliseconds > 6 * 3600000))
        throw std::invalid_argument("invalid MicroWorld worker review timing ENGINEERING_FIXTURE");
}
inline PositionM familiar_brood_site(const auto& s, const Colony& colony) {
    return s.ecological && s.ecological->founding_habitat ? s.ecological->founding_habitat->brood_site : colony.nest_position;
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
inline bool sealed_chamber(const auto& s) {
    return s.ecological && s.ecological->founding_habitat && s.ecological->founding_habitat->sealed_chamber;
}
inline bool anatomical_nest(const auto& s) {
    return sealed_chamber(s) && s.ecological->founding_habitat->anatomical;
}
inline bool mouth_access(const auto& s) {
    return anatomical_nest(s) && s.ecological->founding_habitat->mouth_access;
}
inline bool adult_offers(const auto& s) {
    return mouth_access(s) && s.ecological->founding_habitat->adult_offers;
}
inline bool wall_handoff(const auto& s) {
    return adult_offers(s) && s.ecological->founding_habitat->wall_handoff;
}
inline bool anatomical_handoff(const auto& s) {
    return wall_handoff(s) && s.ecological->founding_habitat->anatomical_handoff;
}
inline bool familiar_return(const auto& s) {
    return anatomical_handoff(s) && s.ecological->founding_habitat->familiar_return;
}
inline bool variable_conditions(const auto& s) {
    return s.ecological && s.ecological->founding_habitat &&
           s.ecological->founding_habitat->variable_conditions.has_value();
}
inline FoundingNutrition founding_nutrition(const auto& s) {
    return s.ecological && s.ecological->founding_habitat ? s.ecological->founding_habitat->nutrition : FoundingNutrition::Original;
}
inline bool local_founding_feeding(const auto& s) { return founding_nutrition(s) != FoundingNutrition::Original; }
inline bool protected_founding(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::ProtectedFounding; }
inline bool local_excavation(const auto& s) { return founding_nutrition(s)==FoundingNutrition::LocalExcavation; }
inline bool provision_callow_water(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::CallowHydration; }
inline bool sustained_supply(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::SustainedSupply; }
inline bool social_crop(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::SocialCrop; }
inline bool crop_exchange(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::CropExchange; }
inline bool chamber_return(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::ChamberReturn; }
inline bool departure_review(const auto& s) {
    const auto mode=founding_nutrition(s);
    return mode==FoundingNutrition::LocalDeparture || mode>=FoundingNutrition::FirstMeal;
}
inline bool local_entrance_work(const auto& s) { return local_excavation(s) || departure_review(s); }
inline bool local_crop_return(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::LocalCropReturn; }
inline bool worked_exit(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::WorkedExit; }
inline bool sustained_contact(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::SustainedContact; }
inline bool yielding_return(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::YieldingReturn; }
inline bool chamber_handoff(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::ChamberHandoff; }
inline bool body_orientation_enabled(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::BodyOrientation; }
inline bool local_solicitation(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::LocalSolicitation; }
inline bool source_refill(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::SourceRefill; }
inline bool founder_appetite(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::FounderAppetite; }
inline bool tracks_trip_load(const auto& s) { return founding_nutrition(s)==FoundingNutrition::TripLoad; }
inline bool work_face_search(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::WorkFaceSearch; }
inline bool responsive_meal(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::ResponsiveMeal; }
inline bool meal_rendezvous(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::MealRendezvous; }
inline bool mouth_range(const auto& s) { return founding_nutrition(s)>=FoundingNutrition::MouthRange; }

inline constexpr std::uint64_t completed_return_wake=1, carbohydrate_delivery_wake=2, solicited_meal_wake=3;
inline bool local_brood_budget(const auto& s) {
    return founding_nutrition(s)==FoundingNutrition::BroodBudget || sustained_supply(s);
}
inline bool sealed_seed_shape(const auto& geometry, bool bands) {
    const auto& rooms=geometry.voids;
    if (rooms.empty() || rooms.size()>(bands?64u:1u)) return false;
    const auto& bed=geometry.config.initial_solid;
    for (std::size_t i=0;i<rooms.size();++i) {
        const auto& room=rooms[i];
        if (room.min.x<=bed.min.x || room.max.x>=bed.max.x ||
            room.min.y<=bed.min.y || room.max.y>=bed.max.y ||
            room.min.z<=bed.min.z || room.max.z>=bed.max.z) return false;
        if (i) {
            const auto& prior=rooms[i-1];
            if (room.min.z!=prior.max.z || room.min.y!=prior.min.y || room.max.y!=prior.max.y ||
                std::max(room.min.x,prior.min.x)>=std::min(room.max.x,prior.max.x)) return false;
        }
    }
    return true;
}
inline double brood_handling_reach(const auto& s) {
    // ENGINEERING_FIXTURE. The legacy contact radius remains available for
    // social encounters and familiar nursery membership.
    return sealed_chamber(s) ? std::min(s.config.contact_distance_m,.00125) : s.config.contact_distance_m;
}
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
