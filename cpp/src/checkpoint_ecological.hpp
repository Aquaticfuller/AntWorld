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
inline constexpr unsigned nest_activity_schema = 25, nest_activity_physics = 32;
inline constexpr unsigned nest_dynamics_schema = 26, nest_dynamics_physics = 33;
inline constexpr unsigned local_traffic_schema = 27, local_traffic_physics = 34;
inline constexpr unsigned carrier_yield_schema = 28, carrier_yield_physics = 35;
inline constexpr unsigned founding_habitat_schema = 29, founding_habitat_physics = 36;
inline constexpr unsigned reachable_berth_schema = 30, reachable_berth_physics = 37;
inline constexpr unsigned sealed_chamber_schema = 31, sealed_chamber_physics = 38;
inline constexpr unsigned anatomical_schema = 32, anatomical_physics = 39;
inline constexpr unsigned mouth_access_schema = 33, mouth_access_physics = 40;
inline constexpr unsigned adult_offer_schema = 34, adult_offer_physics = 41;
inline constexpr unsigned wall_handoff_schema = 35, wall_handoff_physics = 42;
inline constexpr unsigned anatomical_handoff_schema = 36, anatomical_handoff_physics = 43;
inline constexpr unsigned familiar_return_schema = 37, familiar_return_physics = 44;
inline constexpr unsigned variable_nest_schema = 38, variable_nest_physics = 45;
inline constexpr unsigned provisioned_nest_schema = 39, provisioned_nest_physics = 46;
inline constexpr unsigned sustained_nest_schema = 40, sustained_nest_physics = 47;

inline constexpr unsigned protected_nest_schema = 41, protected_nest_physics = 48;
inline constexpr unsigned local_excavation_schema = 42, local_excavation_physics = 49;
inline constexpr unsigned callow_hydration_schema = 43, callow_hydration_physics = 50;
inline constexpr unsigned departure_schema = 50, departure_physics = 57;
inline constexpr unsigned rendezvous_schema = 51, rendezvous_physics = 58;
inline constexpr unsigned exit_attachment_schema = 66, exit_attachment_physics = 73;
inline constexpr unsigned founder_route_schema = 65, founder_route_physics = 72;
inline constexpr unsigned trip_load_schema = 64, trip_load_physics = 71;
inline constexpr unsigned appetite_schema = 63, appetite_physics = 70;
inline constexpr unsigned source_refill_schema = 62, source_refill_physics = 69;
inline constexpr unsigned solicitation_schema = 61, solicitation_physics = 68;
inline constexpr unsigned body_orientation_schema = 60, body_orientation_physics = 67;
inline constexpr unsigned chamber_handoff_schema = 59, chamber_handoff_physics = 66;
inline constexpr unsigned yielding_return_schema = 58, yielding_return_physics = 65;
inline constexpr unsigned sustained_contact_schema = 57, sustained_contact_physics = 64;
inline constexpr unsigned worked_exit_schema = 56, worked_exit_physics = 63;
inline constexpr unsigned local_crop_schema = 55, local_crop_physics = 62;
inline constexpr unsigned work_face_schema = 54, work_face_physics = 61;
inline constexpr unsigned responsive_meal_schema = 53, responsive_meal_physics = 60;
inline constexpr unsigned first_meal_schema = 52, first_meal_physics = 59;
inline constexpr unsigned checked_offer_schema = 49, checked_offer_physics = 56;
inline constexpr unsigned mouth_range_schema = 48, mouth_range_physics = 55;
inline constexpr unsigned chamber_return_schema = 47, chamber_return_physics = 54;
inline constexpr unsigned crop_exchange_schema = 46, crop_exchange_physics = 53;
inline constexpr unsigned social_crop_schema = 45, social_crop_physics = 52;
inline constexpr unsigned meal_search_schema = 44, meal_search_physics = 51;

inline bool micro_world_version(unsigned version) {
    return version==micro_world_physics || version==micro_world_no_hatch_physics ||
           version==portable_micro_world_physics || version==portable_micro_world_no_hatch_physics;
}

inline unsigned ecological_version(const EcologicalClosureConfig& c) {
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::LocalDeparture) return departure_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::MealRendezvous) return rendezvous_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ExitAttachment) return exit_attachment_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::FounderRoute) return founder_route_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::TripLoad) return trip_load_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::FounderAppetite) return appetite_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::SourceRefill) return source_refill_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::LocalSolicitation) return solicitation_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::BodyOrientation) return body_orientation_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ChamberHandoff) return chamber_handoff_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::YieldingReturn) return yielding_return_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::SustainedContact) return sustained_contact_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::WorkedExit) return worked_exit_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::LocalCropReturn) return local_crop_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::WorkFaceSearch) return work_face_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ResponsiveMeal) return responsive_meal_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::FirstMeal) return first_meal_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::CheckedLarvalOffer) return checked_offer_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::MouthRange) return mouth_range_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ChamberReturn) return chamber_return_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::CropExchange) return crop_exchange_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::SocialCrop) return social_crop_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::MealSearch) return meal_search_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::CallowHydration) return callow_hydration_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::LocalExcavation) return local_excavation_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ProtectedFounding) return protected_nest_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::SustainedSupply) return sustained_nest_physics;
    if (c.founding_habitat && c.founding_habitat->nutrition != FoundingNutrition::Original) return provisioned_nest_physics;
    if (c.founding_habitat && c.founding_habitat->variable_conditions) return variable_nest_physics;
    if (c.founding_habitat && c.founding_habitat->familiar_return) return familiar_return_physics;
    if (c.founding_habitat && c.founding_habitat->anatomical_handoff) return anatomical_handoff_physics;
    if (c.founding_habitat && c.founding_habitat->wall_handoff) return wall_handoff_physics;
    if (c.founding_habitat && c.founding_habitat->adult_offers) return adult_offer_physics;
    if (c.founding_habitat && c.founding_habitat->mouth_access) return mouth_access_physics;
    if (c.founding_habitat && c.founding_habitat->anatomical) return anatomical_physics;
    if (c.founding_habitat && c.founding_habitat->sealed_chamber) return sealed_chamber_physics;
    if (c.founding_habitat)
        return c.founding_habitat->alternate_berth ? reachable_berth_physics : founding_habitat_physics;
    if (c.yield_to_loaded || c.local_pantry_checks) return carrier_yield_physics;
    if (c.local_traffic) return local_traffic_physics;
    if (c.nest_dynamics) return nest_dynamics_physics;
    if (c.local_nest_activity) return nest_activity_physics;
    if (c.worker_activity_timing) return worker_timing_physics;
    if (c.portable_care_motion)
        return c.suppress_foundress_hatch_cue?portable_micro_world_no_hatch_physics:portable_micro_world_physics;
    if (c.brood_space) return c.suppress_foundress_hatch_cue?micro_world_no_hatch_physics:micro_world_physics;
    if (c.suppress_foundress_hatch_cue) return suppressed_hatch_physics;
    return c.portable_field?portable_ecological_physics:ecological_physics;
}
inline unsigned ecological_schema_version(const EcologicalClosureConfig& c) {
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::LocalDeparture) return departure_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::MealRendezvous) return rendezvous_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ExitAttachment) return exit_attachment_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::FounderRoute) return founder_route_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::TripLoad) return trip_load_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::FounderAppetite) return appetite_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::SourceRefill) return source_refill_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::LocalSolicitation) return solicitation_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::BodyOrientation) return body_orientation_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ChamberHandoff) return chamber_handoff_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::YieldingReturn) return yielding_return_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::SustainedContact) return sustained_contact_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::WorkedExit) return worked_exit_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::LocalCropReturn) return local_crop_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::WorkFaceSearch) return work_face_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ResponsiveMeal) return responsive_meal_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::FirstMeal) return first_meal_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::CheckedLarvalOffer) return checked_offer_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::MouthRange) return mouth_range_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ChamberReturn) return chamber_return_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::CropExchange) return crop_exchange_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::SocialCrop) return social_crop_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::MealSearch) return meal_search_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::CallowHydration) return callow_hydration_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::LocalExcavation) return local_excavation_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::ProtectedFounding) return protected_nest_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition == FoundingNutrition::SustainedSupply) return sustained_nest_schema;
    if (c.founding_habitat && c.founding_habitat->nutrition != FoundingNutrition::Original) return provisioned_nest_schema;
    if (c.founding_habitat && c.founding_habitat->variable_conditions) return variable_nest_schema;
    if (c.founding_habitat && c.founding_habitat->familiar_return) return familiar_return_schema;
    if (c.founding_habitat && c.founding_habitat->anatomical_handoff) return anatomical_handoff_schema;
    if (c.founding_habitat && c.founding_habitat->wall_handoff) return wall_handoff_schema;
    if (c.founding_habitat && c.founding_habitat->adult_offers) return adult_offer_schema;
    if (c.founding_habitat && c.founding_habitat->mouth_access) return mouth_access_schema;
    if (c.founding_habitat && c.founding_habitat->anatomical) return anatomical_schema;
    if (c.founding_habitat && c.founding_habitat->sealed_chamber) return sealed_chamber_schema;
    if (c.founding_habitat)
        return c.founding_habitat->alternate_berth ? reachable_berth_schema : founding_habitat_schema;
    if (c.yield_to_loaded || c.local_pantry_checks) return carrier_yield_schema;
    if (c.local_traffic) return local_traffic_schema;
    if (c.nest_dynamics) return nest_dynamics_schema;
    if (c.local_nest_activity) return nest_activity_schema;
    if (c.worker_activity_timing) return worker_timing_schema;
    return c.brood_space ? micro_world_schema : ecological_schema;
}

inline void write_ecological(Writer& w, const EcologicalClosureConfig& c) {
    w.put(c.distance_clock, 1); w.put(c.floor_space, 1);
    w.put(c.recruitment, 1); w.put(c.activity_cost, 1);
    w.real(c.unloaded_m_per_s); w.real(c.loaded_m_per_s);
    w.time(c.soil_handling); w.time(c.cue_lifetime);
    w.put(c.cue_minimum_carbs_ug); w.put(c.water_sip_ug);
    w.put(c.cue_response_ppm, 4); w.put(c.first_ration_ppm, 4);
    if (c.local_nest_activity) w.put(c.worker_activity_timing.has_value(),1);
    if (c.worker_activity_timing) {
        w.time(c.worker_activity_timing->check_interval);
        w.time(c.worker_activity_timing->minimum_program_time);
    }
    if (c.nest_dynamics) {
        w.put(c.nest_dynamics->worker_motor,1);
        w.put(static_cast<unsigned>(c.nest_dynamics->excavation),1);
    }
    if (c.yield_to_loaded || c.local_pantry_checks) {
        w.put(c.yield_to_loaded,1);
        w.put(c.local_pantry_checks,1);
    }
    if (c.founding_habitat) {
        w.position(c.founding_habitat->brood_site);
        w.put(c.founding_habitat->pantry_buffer_ug);
        if (const auto& exposure = c.founding_habitat->variable_conditions; exposure) {
            w.put(exposure->ventilated, 1);
            w.put(exposure->porous, 1);
        }
        if (c.founding_habitat->nutrition != FoundingNutrition::Original)
            w.put(static_cast<std::uint8_t>(c.founding_habitat->nutrition), 1);
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
    const bool habitat = version >= founding_habitat_physics;
    c.local_traffic = version == local_traffic_physics || version == carrier_yield_physics || habitat;
    c.local_nest_activity = version == nest_activity_physics || version == nest_dynamics_physics || c.local_traffic;
    c.brood_space = micro_world_version(version) || version == worker_timing_physics || c.local_nest_activity;
    c.portable_care_motion = version == portable_micro_world_physics ||
        version == portable_micro_world_no_hatch_physics || version == worker_timing_physics || c.local_nest_activity;
    if (version == worker_timing_physics || (c.local_nest_activity && r.flag()))
        c.worker_activity_timing = WorkerActivityTiming{r.time(), r.time()};
    if (version == nest_dynamics_physics || c.local_traffic)
        c.nest_dynamics = NestDynamics{r.flag(),static_cast<NestScoring>(r.get(1))};
    if (version == carrier_yield_physics || habitat) {
        c.yield_to_loaded = r.flag();
        c.local_pantry_checks = r.flag();
        ensure(c.yield_to_loaded || c.local_pantry_checks,"missing nursery work or traffic policy");
    }
    if (habitat) c.founding_habitat=FoundingHabitat{r.position(), r.get(), version >= reachable_berth_physics,
                                                  version >= sealed_chamber_physics,version >= anatomical_physics,
                                                  version >= mouth_access_physics,version >= adult_offer_physics,
                                                  version >= wall_handoff_physics,version >= anatomical_handoff_physics,
                                                  version == familiar_return_physics};
    if (version >= variable_nest_physics)
        c.founding_habitat->variable_conditions = TrailExposure{r.flag(), r.flag()};
    if (version >= provisioned_nest_physics) {
        c.founding_habitat->nutrition = static_cast<FoundingNutrition>(r.get(1));
        ensure(c.founding_habitat->nutrition != FoundingNutrition::Original &&
               ecological_version(c)==version, "invalid founding nutrition treatment");
    }
    validate_ecological_closure(c, world);
    return c;
}
} // namespace antworld::detail
