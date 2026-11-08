#pragma once
#include "physiology_internal.hpp"

namespace antworld::detail {
inline void validate_social(const SocialConfig& c) {
    if (!c.encounter_budget || c.encounter_budget > 128 || c.decision_interval.milliseconds < 1 ||
        c.decision_interval.milliseconds > 60000 || c.minimum_program_time.milliseconds < 0 ||
        c.minimum_program_time.milliseconds > 3600000 || !c.rest_weight || !c.forage_weight ||
        !c.nurse_weight || !c.excavate_weight || c.rest_weight > 1000000 || c.forage_weight > 1000000 ||
        c.nurse_weight > 1000000 || c.excavate_weight > 1000000)
        throw std::invalid_argument("invalid ENGINEERING_FIXTURE social configuration");
}
inline FoodMass ingredient_min(FoodMass a, FoodMass b) {
    return {std::min(a.carbs_ug,b.carbs_ug),std::min(a.protein_ug,b.protein_ug),
        std::min(a.water_ug,b.water_ug),std::min(a.other_ug,b.other_ug)};
}
// A local engineering proxy for a contacted recipient's demand, not a colony aggregate.
inline FoodMass nutrient_demand(const PhysiologyState& p, LifeStage stage) {
    if (stage != LifeStage::Adult && stage != LifeStage::Larva) return {};
    auto remaining = [](std::uint64_t target, std::uint64_t supplied) {
        return target > supplied ? target-supplied : 0;
    };
    return {remaining((p.config.energy_capacity_nj-p.body_energy_nj)/p.config.carbohydrate_yield_nj_per_ug,p.crop.carbs_ug),
        stage == LifeStage::Larva ? remaining(p.config.larval_protein_requirement_ug,add(p.tissue_protein_ug,p.crop.protein_ug)) : 0,
        remaining(p.config.hydration_capacity_ug-p.hydration_ug,p.crop.water_ug),0};
}
} // namespace antworld::detail
