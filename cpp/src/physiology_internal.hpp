#pragma once
#include "state.hpp"

namespace antworld::detail {
inline std::uint64_t bounded_draw(Rng& rng, std::uint64_t bound) {
    const auto threshold = (std::uint64_t{0}-bound)%bound;
    for (;;) { const auto value = rng.next(); if (value >= threshold) return value%bound; }
}
inline std::uint64_t multiply(std::uint64_t a, std::uint64_t b) {
    if (a && b > UINT64_MAX/a) throw std::overflow_error("physiology arithmetic overflow");
    return a*b;
}
inline SimTime after(SimTime at, std::int64_t delay) {
    if (delay < 0 || at.milliseconds > INT64_MAX-delay) throw std::overflow_error("physiology time exhausted");
    return {at.milliseconds+delay};
}
inline void validate_physiology(const PhysiologySeed& seed, const PhysiologyConfig& c) {
    if (c.absorption_period.milliseconds <= 0 || c.absorption_period.milliseconds > 604800000 ||
        c.behavior_interval.milliseconds <= 0 || c.behavior_interval.milliseconds > 604800000 ||
        c.water_loss_period.milliseconds < 1 || c.water_loss_period.milliseconds > 86400000 ||
        c.adult_protein_target_ug > c.crop_capacity_ug ||
        c.egg_duration.milliseconds <= 0 || c.larva_duration.milliseconds <= 0 || c.pupa_duration.milliseconds <= 0 ||
        !c.energy_capacity_nj || c.energy_capacity_nj > UINT64_C(1000000000000000) ||
        !seed.body_energy_nj || seed.body_energy_nj > c.energy_capacity_nj ||
        !seed.hydration_ug || seed.hydration_ug > c.hydration_capacity_ug || c.hydration_capacity_ug > 1000000000 ||
        c.crop_capacity_ug > 1000000000 || seed.crop.total_ug() > c.crop_capacity_ug ||
        !c.carbohydrate_yield_nj_per_ug || c.carbohydrate_yield_nj_per_ug > 1000000000 ||
        c.basal_nj_per_ms > 1000000000 || c.active_nj_per_ms > 1000000000 ||
        c.water_loss_ug_per_period > 1000000000 || c.carb_absorption_ug_per_s > 1000000000 ||
        c.water_absorption_ug_per_s > 1000000000 || c.protein_absorption_ug_per_s > 1000000000 ||
        !c.larval_protein_requirement_ug || c.larval_protein_requirement_ug > 1000000000 ||
        seed.tissue_protein_ug > c.larval_protein_requirement_ug || !c.transfer_limit_ug || c.transfer_limit_ug > 1000000000)
        throw std::invalid_argument("invalid ENGINEERING_FIXTURE physiology configuration");
}
inline SimTime stage_duration(const PhysiologyConfig& c, LifeStage stage) {
    if (stage == LifeStage::Egg) return c.egg_duration;
    if (stage == LifeStage::Larva) return c.larva_duration;
    if (stage == LifeStage::Pupa) return c.pupa_duration;
    return {};
}
inline bool developing(const PhysiologyState& p, LifeStage stage) {
    return stage < LifeStage::Adult && (stage != LifeStage::Larva || p.tissue_protein_ug >= p.config.larval_protein_requirement_ug);
}
inline std::uint64_t expenditure(const PhysiologyState& p, LifeStage stage) {
    const auto active = stage == LifeStage::Adult && (p.behavior == IndividualBehavior::Forage || p.behavior == IndividualBehavior::Nurse || p.behavior == IndividualBehavior::Excavate);
    return add(p.config.basal_nj_per_ms, active ? p.config.active_nj_per_ms : 0);
}
// Exact integration of the declared piecewise-constant model, independent of host calls.
inline void settle(PhysiologyState& p, LifeStage stage, SimTime at) {
    if (at < p.updated_at) throw std::logic_error("physiology time reversal");
    if (stage == LifeStage::Dead) return;
    const auto dt = static_cast<std::uint64_t>(at.milliseconds-p.updated_at.milliseconds);
    const auto used = std::min(p.body_energy_nj, multiply(expenditure(p, stage), dt));
    p.body_energy_nj -= used; p.dissipated_energy_nj = add(p.dissipated_energy_nj, used);
    const auto water = add(multiply(p.config.water_loss_ug_per_period, dt), p.water_loss_remainder);
    const auto period = static_cast<std::uint64_t>(p.config.water_loss_period.milliseconds);
    const auto lost = std::min(p.hydration_ug, water/period);
    p.hydration_ug -= lost; p.lost_water_ug = add(p.lost_water_ug, lost); p.water_loss_remainder = water%period;
    if (developing(p, stage)) p.stage_progress = after(p.stage_progress, static_cast<std::int64_t>(dt));
    p.updated_at = at;
}
inline std::uint64_t pulse_allowance(std::uint64_t rate, SimTime period, std::uint64_t& remainder) {
    const auto total = add(multiply(rate, static_cast<std::uint64_t>(period.milliseconds)), remainder);
    remainder = total%1000; return total/1000;
}
inline FoodMass absorb(PhysiologyState& p, LifeStage stage) {
    const auto& c = p.config; FoodMass used;
    if (stage == LifeStage::Adult || stage == LifeStage::Larva) {
        used.carbs_ug = std::min({p.crop.carbs_ug, (c.energy_capacity_nj-p.body_energy_nj)/c.carbohydrate_yield_nj_per_ug,
            pulse_allowance(c.carb_absorption_ug_per_s, c.absorption_period, p.carb_remainder)});
        used.water_ug = std::min({p.crop.water_ug, c.hydration_capacity_ug-p.hydration_ug,
            pulse_allowance(c.water_absorption_ug_per_s, c.absorption_period, p.water_remainder)});
        if (stage == LifeStage::Larva) used.protein_ug = std::min({p.crop.protein_ug,
            c.larval_protein_requirement_ug-p.tissue_protein_ug,
            pulse_allowance(c.protein_absorption_ug_per_s, c.absorption_period, p.protein_remainder)});
        p.crop = subtract(p.crop, used);
        p.body_energy_nj = add(p.body_energy_nj, multiply(used.carbs_ug, c.carbohydrate_yield_nj_per_ug));
        p.oxidized_carbs_ug = add(p.oxidized_carbs_ug, used.carbs_ug);
        p.hydration_ug = add(p.hydration_ug, used.water_ug); p.tissue_protein_ug = add(p.tissue_protein_ug, used.protein_ug);
    }
    p.next_absorption = after(p.next_absorption, c.absorption_period.milliseconds);
    return used;
}
inline SimTime next_physiology(const PhysiologyState& p, LifeStage stage) {
    auto dt = p.next_absorption.milliseconds-p.updated_at.milliseconds;
    auto shorten = [&](std::uint64_t amount, std::uint64_t rate) {
        if (rate) dt = std::min(dt, static_cast<std::int64_t>(amount/rate + (amount%rate != 0)));
    };
    shorten(p.body_energy_nj, expenditure(p, stage));
    shorten(multiply(p.hydration_ug, static_cast<std::uint64_t>(p.config.water_loss_period.milliseconds))-p.water_loss_remainder, p.config.water_loss_ug_per_period);
    if (developing(p, stage)) dt = std::min(dt, stage_duration(p.config, stage).milliseconds-p.stage_progress.milliseconds);
    return after(p.updated_at, dt);
}
inline bool contact(const AntState& a, const AntState& b, const WorldConfig& c, const SurfaceDefinition* surface) {
    return a.colony==b.colony && within_contact(a.position,b.position,c) &&
        (!surface || c.continuous_spatial_motion || surface->locate(a.position)==surface->locate(b.position));
}
} // namespace antworld::detail
