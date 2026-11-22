#pragma once

#include "physiology_internal.hpp"
#include "social_internal.hpp"
#include "behavior_rng.hpp"
#include "ecological_internal.hpp"

namespace antworld::detail {
inline constexpr std::uint64_t founding_day_ms = 86'400'000;
inline constexpr std::uint32_t founding_schema_version = 15, founding_physics_version = 17;
inline constexpr std::uint32_t founding_persistence_schema_version = 16, founding_persistence_physics_version = 18;
inline constexpr std::uint32_t founding_access_schema_version = 17, founding_access_physics_version = 19;
inline constexpr std::uint32_t founding_provisioning_schema_version = 18, founding_provisioning_physics_version = 20;
inline constexpr std::uint32_t founding_dietary_schema_version = 19, founding_dietary_physics_version = 21;
inline constexpr std::uint32_t founding_uptake_schema_version = 20, founding_uptake_physics_version = 22;
inline constexpr std::uint32_t founding_resupply_schema_version = 21, founding_resupply_physics_version = 23;
inline constexpr std::int64_t founding_hatch_cooldown_ms = 3'600'000; // ENGINEERING_FIXTURE
std::uint64_t founding_profile_hash(EntityId founder, const FoundingProfile&);

struct FoundingRates { std::uint64_t energy, water; };
struct FoundingRation {
    std::uint64_t lipid_ug{};
    FoodMass crop;
    bool operator==(const FoundingRation&) const = default;
};
enum class FoundingEggFuel { None, Lipid, Body };

inline std::uint64_t ceil_div(std::uint64_t n, std::uint64_t d) { return n/d + (n%d != 0); }

inline bool local_founding_provisioning(const auto& world, EntityId id) {
    return world.founding && world.founding->profile.provisioning && world.founding->profile.provisioning->local_exchange &&
           world.founding_reserves.contains(id) && world.founding->founder!=id;
}

inline bool founding_boundary_enabled(const FoundingProfile& f, LifeStage stage) {
    return f.dietary && f.dietary->adult_boundary_uptake && stage==LifeStage::Adult;
}

// Split both factors at the fixed denominator to keep the sub-day product bounded.
inline std::uint64_t integrate_founding(std::uint64_t rate, std::uint64_t elapsed, std::uint64_t& carry) {
    const auto subday = elapsed % founding_day_ms;
    const auto fractional = (rate % founding_day_ms) * subday + carry;
    carry = fractional % founding_day_ms;
    return add(add(multiply(rate, elapsed / founding_day_ms), multiply(rate / founding_day_ms, subday)),
               fractional / founding_day_ms);
}

inline FoundingRates founding_rates(const FoundingProfile& f, const PhysiologyState& p,
                                    LifeStage stage, bool queen, bool maximum = false) {
    if (stage < LifeStage::Adult) {
        const auto& rates = f.brood[static_cast<std::size_t>(stage)];
        return {rates.basal_nj_per_day, rates.water_ug_per_day};
    }
    if (queen) {
        const bool active = maximum || active_expenditure(p);
        return {add(f.basal_nj_per_day, active ? multiply(f.active_nj_per_ms, founding_day_ms) : 0), f.water_ug_per_day};
    }
    const auto adult = maximum ? add(p.config.basal_nj_per_ms, p.config.active_nj_per_ms) : expenditure(p, stage);
    return {multiply(adult, founding_day_ms),
            multiply(p.config.water_loss_ug_per_period, founding_day_ms / static_cast<std::uint64_t>(p.config.water_loss_period.milliseconds))};
}

inline PhysiologyConfig founding_physiology(const FoundingProfile& f, bool queen) {
    auto c = f.worker;
    c.egg_duration = f.brood[0].duration;
    c.larva_duration = f.brood[1].duration;
    c.pupa_duration = f.brood[2].duration;
    c.larval_protein_requirement_ug = f.larval_tissue_ug;
    if (queen) {
        c.hydration_capacity_ug = std::max(c.hydration_capacity_ug, f.water_ug);
        c.active_nj_per_ms = f.active_nj_per_ms;
        c.adult_protein_target_ug = ReproductionConfig{}.egg_protein_ug;
    }
    return c;
}

inline std::uint64_t founding_buffer_target(const FoundingProfile& f, const PhysiologyState& p, LifeStage stage, bool queen) {
    const auto window = 2 * static_cast<std::uint64_t>(p.config.absorption_period.milliseconds);
    auto carry = founding_day_ms - 1;
    const auto rate = founding_rates(f, p, stage, queen, true).energy;
    return multiply(ceil_div(integrate_founding(rate, window, carry), f.lipid_yield_nj_per_ug), f.lipid_yield_nj_per_ug);
}

inline std::uint64_t convert_founding_lipid(const FoundingProfile& f, PhysiologyState& p, FoundingReserve& r,
                                            LifeStage stage, bool queen) {
    const auto target = founding_buffer_target(f, p, stage, queen);
    if (target <= p.body_energy_nj) return 0;
    const auto y = f.lipid_yield_nj_per_ug;
    const auto used = std::min({r.lipid_ug, ceil_div(target-p.body_energy_nj, y), (p.config.energy_capacity_nj-p.body_energy_nj)/y});
    r.lipid_ug -= used;
    r.spent_lipid_ug = add(r.spent_lipid_ug, used);
    p.body_energy_nj = add(p.body_energy_nj, multiply(used, y));
    return used;
}

inline std::uint64_t mobilize_founding_larval_lipid(const FoundingProfile& f, PhysiologyState& p, FoundingReserve& r,
                                                    LifeStage stage) {
    if (!f.early_access || !f.early_access->mobilize_larval_lipid || stage != LifeStage::Larva ||
        p.body_energy_nj || !p.hydration_ug || !r.lipid_ug) return 0;
    return convert_founding_lipid(f, p, r, stage, false);
}

inline PhysiologyState initial_founding_physiology(const FoundingProfile& f, bool queen, SimTime at, EntityId mother = {}) {
    PhysiologyState p;
    p.config = founding_physiology(f, queen);
    p.initial = {{}, 0, queen ? f.water_ug : f.egg_water_ug, queen ? 0 : f.egg_protein_ug};
    p.updated_at = at;
    p.next_absorption = after(at, p.config.absorption_period.milliseconds);
    p.hydration_ug = p.initial.hydration_ug;
    p.tissue_protein_ug = p.initial.tissue_protein_ug;
    p.mother = mother;
    return p;
}

inline void validate_founding(const FoundingProfile& f) {
    if (f.population != FoundingPopulation::Borisovka && f.population != FoundingPopulation::StPetersburg)
        throw std::invalid_argument("unknown F1 population context");
    const auto wet = add(add(f.lipid_ug, f.protein_ug), add(f.water_ug, f.structural_minimum_ug));
    if (!f.lipid_ug || !f.water_ug || !f.protein_ug || !f.structural_minimum_ug || wet > f.wet_mass_ug ||
        !f.lipid_yield_nj_per_ug || !f.basal_nj_per_day || !f.water_ug_per_day ||
        !f.egg_lipid_ug || !f.egg_protein_ug || !f.egg_water_ug || !f.lay_overhead_nj ||
        f.larval_tissue_ug <= f.egg_protein_ug || f.larval_lipid_capacity_ug < f.egg_lipid_ug ||
        f.worker.adult_protein_target_ug || !f.worker.basal_nj_per_ms || !f.worker.water_loss_ug_per_period ||
        !f.ration_lipid_ug || !f.ration_protein_ug || !f.ration_water_ug ||
        add(f.ration_lipid_ug, add(f.ration_protein_ug, f.ration_water_ug)) > f.worker.transfer_limit_ug ||
        f.brood[1].basal_nj_per_day < std::max(f.brood[0].basal_nj_per_day, f.brood[2].basal_nj_per_day))
        throw std::invalid_argument("invalid F1 material, capacity or rate ordering");
    auto duration = [](SimTime t) {
        if (t.milliseconds <= 0 || t.milliseconds > 365 * static_cast<std::int64_t>(founding_day_ms))
            throw std::invalid_argument("invalid F1 time interval");
        return static_cast<std::uint64_t>(t.milliseconds);
    };
    for (const auto t : {f.first_lay, f.opening_width, f.opening_spacing, f.later_spacing, f.maintenance_floor}) duration(t);
    if (f.opening_spacing > f.opening_width) throw std::invalid_argument("invalid F1 opening bout");
    if (const auto& repeat = f.feeding_persistence;
        repeat && (duration(repeat->window) > 3 * founding_day_ms || repeat->repeat_ppm > 875'000))
        throw std::invalid_argument("invalid F1-R1 feeding persistence");
    if (f.early_access && (!f.feeding_persistence ||
        !(f.early_access->mobilize_larval_lipid || f.early_access->local_hatch_cue)))
        throw std::invalid_argument("invalid F1-R2 early access profile");
    if (f.provisioning && (!f.early_access || !f.early_access->mobilize_larval_lipid || !f.early_access->local_hatch_cue ||
        f.worker.behavior_interval.milliseconds != (f.provisioning->local_exchange ? 3'600'000 : 21'600'000) ||
        (f.worker.carbohydrate_yield_nj_per_ug != 1'000'000 && f.worker.carbohydrate_yield_nj_per_ug != 4'000'000 &&
         f.worker.carbohydrate_yield_nj_per_ug != 8'000'000 && f.worker.carbohydrate_yield_nj_per_ug != 12'000'000) ||
        (!f.provisioning->local_exchange && f.worker.carbohydrate_yield_nj_per_ug == 1'000'000)))
        throw std::invalid_argument("invalid F1 provisioning and sugar profile");
    if (f.dietary && (!f.provisioning || !f.provisioning->local_exchange ||
        f.worker.carbohydrate_yield_nj_per_ug <= 1'000'000 ||
        !(f.dietary->local_nest_intake || f.dietary->dietary_eggs) ||
        (f.dietary->local_resupply && !f.dietary->adult_boundary_uptake) ||
        (f.dietary->adult_boundary_uptake && !(f.dietary->local_nest_intake && f.dietary->dietary_eggs)) ||
        (f.dietary->dietary_eggs && multiply(f.egg_lipid_ug,f.lipid_yield_nj_per_ug)>f.worker.energy_capacity_nj)))
        throw std::invalid_argument("invalid dietary founding profile");
    for (const auto& b : f.brood) {
        if (!b.basal_nj_per_day || !b.water_ug_per_day) throw std::invalid_argument("missing F1 stage cost");
        auto carry = founding_day_ms - 1;
        (void)integrate_founding(b.basal_nj_per_day, duration(b.duration), carry);
        (void)integrate_founding(b.water_ug_per_day, duration(b.duration), carry);
    }
    (void)multiply(f.lipid_ug, f.lipid_yield_nj_per_ug);
    (void)multiply(f.larval_lipid_capacity_ug, f.lipid_yield_nj_per_ug);
    for (const bool queen : {true, false}) {
        auto p = initial_founding_physiology(f, queen, {});
        p.initial.body_energy_nj = f.lipid_yield_nj_per_ug;
        validate_physiology(p.initial, p.config);
        if (founding_day_ms % static_cast<std::uint64_t>(p.config.water_loss_period.milliseconds))
            throw std::invalid_argument("F1 adult water period must divide a day");
        (void)multiply(p.config.energy_capacity_nj, founding_day_ms);
        (void)multiply(p.config.hydration_capacity_ug, founding_day_ms);
        for (const auto stage : {LifeStage::Egg, LifeStage::Larva, LifeStage::Pupa, LifeStage::Adult}) {
            if (queen && stage != LifeStage::Adult) continue;
            const auto bound = founding_buffer_target(f, p, stage, queen);
            if (add(bound, f.lipid_yield_nj_per_ug-1) > p.config.energy_capacity_nj ||
                f.lay_overhead_nj >= p.config.energy_capacity_nj)
                throw std::invalid_argument("F1 buffer cannot hold a refill quantum");
        }
    }
    auto carry = founding_day_ms - 1;
    (void)integrate_founding(f.basal_nj_per_day, duration(f.maintenance_floor), carry);
    (void)integrate_founding(f.water_ug_per_day, duration(f.maintenance_floor), carry);
}

inline void settle_founding(const FoundingProfile& f, PhysiologyState& p, FoundingReserve& r, LifeStage stage,
                            bool queen, SimTime at) {
    if (at < p.updated_at) throw std::logic_error("F1 physiology time reversal");
    if (stage == LifeStage::Dead) return;
    const auto dt = static_cast<std::uint64_t>(at.milliseconds-p.updated_at.milliseconds);
    const auto rates = founding_rates(f, p, stage, queen);
    const auto used = std::min(p.body_energy_nj, integrate_founding(rates.energy, dt, r.energy_remainder));
    const auto lost = std::min(p.hydration_ug, integrate_founding(rates.water, dt, r.water_remainder));
    p.body_energy_nj -= used;
    p.hydration_ug -= lost;
    p.dissipated_energy_nj = add(p.dissipated_energy_nj, used);
    p.lost_water_ug = add(p.lost_water_ug, lost);
    if (stage < LifeStage::Adult) {
        const auto remaining = stage_duration(p.config, stage).milliseconds - p.stage_progress.milliseconds;
        p.stage_progress.milliseconds += std::min(remaining, static_cast<std::int64_t>(dt));
    }
    p.updated_at = at;
}

inline SimTime next_founding_physiology(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r,
                                       LifeStage stage, bool queen) {
    auto dt = static_cast<std::uint64_t>(p.next_absorption.milliseconds-p.updated_at.milliseconds);
    const auto rates = founding_rates(f, p, stage, queen);
    dt = std::min({dt, ceil_div(multiply(p.body_energy_nj, founding_day_ms)-r.energy_remainder, rates.energy),
                      ceil_div(multiply(p.hydration_ug, founding_day_ms)-r.water_remainder, rates.water)});
    if (stage < LifeStage::Adult && p.stage_progress < stage_duration(p.config, stage))
        dt = std::min(dt, static_cast<std::uint64_t>(stage_duration(p.config, stage).milliseconds-p.stage_progress.milliseconds));
    return after(p.updated_at, static_cast<std::int64_t>(dt));
}

inline std::uint64_t founding_energy(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r) {
    return add(p.body_energy_nj, multiply(r.lipid_ug, f.lipid_yield_nj_per_ug));
}

inline std::uint64_t deficit(std::uint64_t required, std::uint64_t owned) {
    return required > owned ? required-owned : 0;
}

inline std::uint64_t dietary_energy(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r) {
    return add(founding_energy(f,p,r),multiply(p.crop.carbs_ug,p.config.carbohydrate_yield_nj_per_ug));
}

inline bool has_founding_diet(const PhysiologyState& p) {
    return p.crop.carbs_ug || p.crop.protein_ug || p.oxidized_carbs_ug;
}

inline FoundingRates remaining_brood_maintenance(const FoundingProfile& f, const PhysiologyState& p, LifeStage stage) {
    FoundingRates remaining{};
    auto energy_carry=founding_day_ms-1, water_carry=energy_carry;
    for (auto index=static_cast<std::size_t>(stage); index<f.brood.size(); ++index) {
        const auto& phase=f.brood[index];
        const auto progress=index==static_cast<std::size_t>(stage) ? p.stage_progress.milliseconds : 0;
        const auto time=static_cast<std::uint64_t>(phase.duration.milliseconds-progress);
        remaining.energy=add(remaining.energy,integrate_founding(phase.basal_nj_per_day,time,energy_carry));
        remaining.water=add(remaining.water,integrate_founding(phase.water_ug_per_day,time,water_carry));
    }
    return remaining;
}

// Carry through the first scheduled adult uptake, even if eclosion follows a
// recent pulse. These are accrued model costs, not additional resources.
inline FoundingRates needs_through_first_adult_pulse(const FoundingProfile& f, const PhysiologyState& p, LifeStage stage) {
    auto cost=remaining_brood_maintenance(f,p,stage);
    auto energy_carry=founding_day_ms-1, water_carry=energy_carry;
    const auto absorption=static_cast<std::uint64_t>(f.worker.absorption_period.milliseconds);
    const auto adult=founding_rates(f,p,LifeStage::Adult,false,true);
    cost.energy=add(cost.energy,integrate_founding(adult.energy,absorption,energy_carry));
    cost.water=add(cost.water,integrate_founding(adult.water,absorption,water_carry));
    return cost;
}

struct BroodRequirement { std::uint64_t energy_nj{}, protein_ug{}, water_ug{}; };

inline BroodRequirement unfunded_brood(const FoundingProfile& f, const PhysiologyState& p,
                                       const FoundingReserve& reserve, LifeStage stage) {
    const auto need=needs_through_first_adult_pulse(f,p,stage);
    return {deficit(add(need.energy,1),dietary_energy(f,p,reserve)),
            deficit(f.larval_tissue_ug,add(p.tissue_protein_ug,p.crop.protein_ug)),
            deficit(add(need.water,1),add(p.hydration_ug,p.crop.water_ug))};
}

inline FoodMass founding_larval_demand(const FoundingProfile& f, const PhysiologyState& p,
                                      const FoundingReserve& r) {
    const auto need=unfunded_brood(f,p,r,LifeStage::Larva);
    return {ceil_div(need.energy_nj,p.config.carbohydrate_yield_nj_per_ug),need.protein_ug,need.water_ug,0};
}

// A locally observed larva may miss the next uptake even when its mother
// holds enough reserves to lay. Count only energy and water already owned.
inline bool urgent_larval_upkeep(const FoundingProfile& f,const PhysiologyState& p,const FoundingReserve& r) {
    const auto span=static_cast<std::uint64_t>(p.config.absorption_period.milliseconds);
    const auto rate=founding_rates(f,p,LifeStage::Larva,false);
    auto e=r.energy_remainder,w=r.water_remainder;
    return dietary_energy(f,p,r)<=integrate_founding(rate.energy,span,e) ||
        add(p.hydration_ug,p.crop.water_ug)<=integrate_founding(rate.water,span,w);
}

inline void reserve_for_brood(BroodRequirement& total, const FoundingProfile& f, const PhysiologyState& p,
                              const FoundingReserve& reserve, LifeStage stage) {
    const auto need=unfunded_brood(f,p,reserve,stage);
    total.energy_nj=add(total.energy_nj,need.energy_nj);
    total.protein_ug=add(total.protein_ug,need.protein_ug);
    total.water_ug=add(total.water_ug,need.water_ug);
}

inline FoodMass founding_resupply_shortfall(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r,
                                           bool queen, SimTime decision_interval) {
    const auto rates=founding_rates(f,p,LifeStage::Adult,queen,true);
    auto ec=founding_day_ms-1, wc=ec;
    const auto span=2*static_cast<std::uint64_t>(decision_interval.milliseconds);
    const auto needed_energy=integrate_founding(rates.energy,span,ec);
    const auto needed_water=integrate_founding(rates.water,span,wc);
    const auto energy=founding_energy(f,p,r);
    const auto water=add(p.hydration_ug,p.crop.water_ug);
    const auto carb=needed_energy>energy?ceil_div(needed_energy-energy,p.config.carbohydrate_yield_nj_per_ug):0;
    return {carb>p.crop.carbs_ug?carb-p.crop.carbs_ug:0,0,needed_water>water?needed_water-water:0,0};
}

inline std::uint64_t wick_shortfall(const FoundingProfile& f, const PhysiologyState& p, bool queen) {
    // ENGINEERING_FIXTURE. Give the slower foundress a longer approach
    // window. The gap between seeking and refilling prevents tiny sips
    // from interrupting each bout.
    const auto day=founding_rates(f,p,LifeStage::Adult,queen).water;
    const auto held=add(p.hydration_ug,p.crop.water_ug);
    if (held>=std::min(p.config.hydration_capacity_ug,multiply(queen?2:1,day))) return 0;
    return deficit(std::min(p.config.hydration_capacity_ug,multiply(queen?3:2,day)),held);
}

inline std::uint64_t crop_for_sharing(const FoundingProfile& f, const PhysiologyState& p, bool queen) {
    // ENGINEERING_FIXTURE. The crop can hold food for the next local
    // exchange. Hold at most one permissible ration and only while the
    // body can already pay its own maintenance through the next pulse.
    const auto span=static_cast<std::uint64_t>(p.config.absorption_period.milliseconds);
    auto remainder=founding_day_ms-1;
    const auto upkeep=integrate_founding(founding_rates(f,p,LifeStage::Adult,queen,true).energy,span,remainder);
    if (p.body_energy_nj<=upkeep) return 0;
    const auto ration=multiply(f.ration_lipid_ug,f.lipid_yield_nj_per_ug);
    return std::min(p.crop.carbs_ug,ceil_div(ration,p.config.carbohydrate_yield_nj_per_ug));
}

inline FoodMass founding_pulse(PhysiologyState& p, FoundingUptakeClock& clock, LifeStage stage,
                              std::uint64_t crop_for_sharing_ug=0) {
    const auto now=p.updated_at;
    const SimTime carb{now.milliseconds-clock.carb.milliseconds};
    const SimTime water{now.milliseconds-clock.water.milliseconds};
    clock={now,now};
    p.crop.carbs_ug-=crop_for_sharing_ug;
    const auto dose=absorb(p,stage,carb,water);
    p.crop.carbs_ug=add(p.crop.carbs_ug,crop_for_sharing_ug);
    return dose;
}

inline FoodMass founding_boundary_uptake(PhysiologyState& p, FoundingUptakeClock& clock) {
    const bool energy=!p.body_energy_nj, water=!p.hydration_ug;
    if (!(energy || water)) return {};
    const auto now=p.updated_at;
    const auto& c=p.config;
    auto carb_remainder=p.carb_remainder, water_remainder=p.water_remainder;
    FoodMass dose;
    if (energy) dose.carbs_ug=std::min({p.crop.carbs_ug,c.energy_capacity_nj/c.carbohydrate_yield_nj_per_ug,
        pulse_allowance(c.carb_absorption_ug_per_s,{now.milliseconds-clock.carb.milliseconds},carb_remainder)});
    if (water) dose.water_ug=std::min({p.crop.water_ug,c.hydration_capacity_ug,
        pulse_allowance(c.water_absorption_ug_per_s,{now.milliseconds-clock.water.milliseconds},water_remainder)});
    if ((energy && !dose.carbs_ug) || (water && !dose.water_ug)) return {};
    p.crop=subtract(p.crop,dose);
    if (energy) {
        p.body_energy_nj=multiply(dose.carbs_ug,c.carbohydrate_yield_nj_per_ug);
        p.oxidized_carbs_ug=add(p.oxidized_carbs_ug,dose.carbs_ug);
        p.carb_remainder=carb_remainder;
        clock.carb=now;
    }
    if (water) {
        p.hydration_ug=dose.water_ug;
        p.water_remainder=water_remainder;
        clock.water=now;
    }
    return dose;
}

// Keep the part of owned crop needed for the next normal uptake cycle.
inline FoodMass founding_gift_supply(const FoundingProfile& f, const PhysiologyState& donor) {
    const auto rates = founding_rates(f, donor, LifeStage::Adult, false, true);
    const auto until_pulse = static_cast<std::uint64_t>(donor.next_absorption.milliseconds-donor.updated_at.milliseconds);
    const auto interval = static_cast<std::uint64_t>(donor.config.absorption_period.milliseconds);
    auto e = founding_day_ms - 1, w = e;
    const auto energy = integrate_founding(rates.energy, add(until_pulse, interval), e);
    const auto water = integrate_founding(rates.water, add(until_pulse, interval), w);
    auto result = donor.crop;
    const auto carbs = energy>donor.body_energy_nj ?
        ceil_div(energy-donor.body_energy_nj,donor.config.carbohydrate_yield_nj_per_ug) : 0;
    result.carbs_ug -= std::min(result.carbs_ug,carbs);
    result.water_ug -= std::min(result.water_ug,water>donor.hydration_ug ? water-donor.hydration_ug : 0);
    return result;
}

inline bool founding_develops(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r, LifeStage stage) {
    if (stage >= LifeStage::Adult || p.stage_progress != stage_duration(p.config, stage)) return false;
    if (stage != LifeStage::Larva) return true;
    const auto& closed = f.brood[2];
    auto e = r.energy_remainder, w = r.water_remainder;
    const auto duration = static_cast<std::uint64_t>(closed.duration.milliseconds);
    return p.tissue_protein_ug >= f.larval_tissue_ug &&
           founding_energy(f, p, r) > integrate_founding(closed.basal_nj_per_day, duration, e) &&
           p.hydration_ug > integrate_founding(closed.water_ug_per_day, duration, w);
}

inline FoundingRates maintenance_cost(const FoundingProfile& f, const FoundingReserve& r) {
    auto e = r.energy_remainder, w = r.water_remainder;
    const auto horizon = static_cast<std::uint64_t>(f.maintenance_floor.milliseconds);
    return {integrate_founding(f.basal_nj_per_day, horizon, e), integrate_founding(f.water_ug_per_day, horizon, w)};
}

inline FoundingRates dietary_maintenance(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r) {
    auto e=r.energy_remainder, w=r.water_remainder;
    const auto horizon=static_cast<std::uint64_t>(p.config.absorption_period.milliseconds)*2;
    const auto rates=founding_rates(f,p,LifeStage::Adult,true,true);
    return {integrate_founding(rates.energy,horizon,e),integrate_founding(rates.water,horizon,w)};
}

inline bool funds_brood_budget(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r,
                               const BroodRequirement& existing) {
    const auto floor=p.oxidized_carbs_ug ? dietary_maintenance(f,p,r) : maintenance_cost(f,r);
    const auto newborn=needs_through_first_adult_pulse(f,initial_founding_physiology(f,false,{}),LifeStage::Egg);
    const auto egg_energy=multiply(f.egg_lipid_ug,f.lipid_yield_nj_per_ug);
    const auto next_energy=add(std::max(egg_energy,newborn.energy),f.lay_overhead_nj);
    const auto next_water=std::max(f.egg_water_ug,newborn.water);
    return dietary_energy(f,p,r)>add(add(floor.energy,existing.energy_nj),next_energy) &&
        add(p.crop.protein_ug,r.mobile_protein_ug)>=add(existing.protein_ug,f.larval_tissue_ug) &&
        add(p.hydration_ug,p.crop.water_ug)>add(add(floor.water,existing.water_ug),next_water);
}

inline FoodMass foundress_nest_meal(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r,
                                  FoodMass stock, bool local_feeding=false) {
    if (!p.body_energy_nj || !p.hydration_ug) return {};
    const auto floor=dietary_maintenance(f,p,r);
    const auto y=p.config.carbohydrate_yield_nj_per_ug;
    const auto refill=f.dietary->dietary_eggs ? add(multiply(f.egg_lipid_ug,f.lipid_yield_nj_per_ug),f.lay_overhead_nj) : 0;
    const auto juvenile=local_feeding ?
        needs_through_first_adult_pulse(f,initial_founding_physiology(f,false,{}),LifeStage::Egg) : FoundingRates{};
    const auto own_energy=local_feeding ? multiply(floor.energy,2) : floor.energy;
    const auto energy_target=local_feeding ? add(own_energy,add(std::max(refill,juvenile.energy),f.lay_overhead_nj)) :
        std::min(p.config.energy_capacity_nj,add(floor.energy,refill));
    const auto body_carbs=energy_target>p.body_energy_nj ? ceil_div(energy_target-p.body_energy_nj,y) : 0;
    const auto own_water=local_feeding ? multiply(floor.water,2) : floor.water;
    const auto water_target=std::min(p.config.hydration_capacity_ug,add(own_water,std::max(f.egg_water_ug,juvenile.water)));
    const auto body_water=water_target>p.hydration_ug ? water_target-p.hydration_ug : 0;
    const auto protein_target=local_feeding ? f.larval_tissue_ug : f.egg_protein_ug;
    const FoodMass deficit{body_carbs>p.crop.carbs_ug ? body_carbs-p.crop.carbs_ug : 0,
        f.dietary->dietary_eggs && protein_target>p.crop.protein_ug ? protein_target-p.crop.protein_ug : 0,
        body_water>p.crop.water_ug ? body_water-p.crop.water_ug : 0,0};
    const auto supply=ingredient_min(stock,deficit);
    if (!supply.total_ug() || p.crop.total_ug()==p.config.crop_capacity_ug) return {};
    const auto room=p.config.crop_capacity_ug-p.crop.total_ug();
    // A self-fed meal is bounded by actual demand and crop room. The worker
    // handoff size remains the cap on one oral transfer between individuals.
    return portion(supply,std::min(supply.total_ug(),local_feeding ? room : std::min(room,p.config.transfer_limit_ug)));
}

inline FoundingEggFuel founding_egg_fuel(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r) {
    if (f.dietary && f.dietary->dietary_eggs && p.oxidized_carbs_ug) {
        const auto floor=dietary_maintenance(f,p,r);
        const auto egg=multiply(f.egg_lipid_ug,f.lipid_yield_nj_per_ug);
        const auto cost=add(egg,f.lay_overhead_nj);
        if (p.body_energy_nj>cost && p.hydration_ug>add(f.egg_water_ug,floor.water) &&
            add(p.crop.protein_ug,r.mobile_protein_ug)>=f.egg_protein_ug &&
            founding_energy(f,p,r)>add(cost,floor.energy)) return FoundingEggFuel::Body;
    }
    const auto floor = maintenance_cost(f, r);
    const bool funded=p.body_energy_nj > f.lay_overhead_nj && r.lipid_ug >= f.egg_lipid_ug && r.mobile_protein_ug >= f.egg_protein_ug &&
           p.hydration_ug > add(f.egg_water_ug, floor.water) &&
           founding_energy(f, p, r) > add(add(multiply(f.egg_lipid_ug, f.lipid_yield_nj_per_ug), f.lay_overhead_nj), floor.energy);
    return funded ? FoundingEggFuel::Lipid : FoundingEggFuel::None;
}

inline bool funds_founding_egg(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r) {
    return founding_egg_fuel(f,p,r)!=FoundingEggFuel::None;
}

inline void debit_founding_egg(const FoundingProfile& f, PhysiologyState& p, FoundingReserve& r) {
    r.lipid_ug -= f.egg_lipid_ug;
    r.mobile_protein_ug -= f.egg_protein_ug;
    p.hydration_ug -= f.egg_water_ug;
    p.body_energy_nj -= f.lay_overhead_nj;
    p.dissipated_energy_nj = add(p.dissipated_energy_nj, f.lay_overhead_nj);
}

inline std::uint64_t debit_dietary_egg(const FoundingProfile& f, PhysiologyState& p, FoundingReserve& r) {
    const auto from_crop=std::min(f.egg_protein_ug,p.crop.protein_ug);
    const auto egg=multiply(f.egg_lipid_ug,f.lipid_yield_nj_per_ug);
    p.crop.protein_ug-=from_crop;
    r.mobile_protein_ug-=f.egg_protein_ug-from_crop;
    p.hydration_ug-=f.egg_water_ug;
    p.body_energy_nj-=add(egg,f.lay_overhead_nj);
    p.exported_energy_nj=add(p.exported_energy_nj,egg);
    p.dissipated_energy_nj=add(p.dissipated_energy_nj,f.lay_overhead_nj);
    return from_crop;
}

inline SimTime founding_lay_after(const FoundingProfile& f, SimTime at) {
    const auto end = after(f.first_lay, f.opening_width.milliseconds);
    if (at < f.first_lay) return f.first_lay;
    if (at >= end) return after(at, f.later_spacing.milliseconds);
    const auto next = after(at, f.opening_spacing.milliseconds);
    return next < end ? next : after(end, f.later_spacing.milliseconds);
}

// ENGINEERING_FIXTURE. A bounded triangular distribution around the nominal
// interval; the mean is unchanged before rounding. Separate streams keep
// scheduling variation independent from food, movement and care decisions.
inline std::int64_t rhythm_delay(Rng& rng, SimTime nominal, std::uint32_t spread_permille) {
    const auto width = std::uint64_t{spread_permille} + 1;
    const auto scale = 1000 - spread_permille + bounded_draw(rng, width) + bounded_draw(rng, width);
    return std::max<std::int64_t>(1, nominal.milliseconds * static_cast<std::int64_t>(scale) / 1000);
}

inline std::int64_t autonomy_delay(const auto& s, EntityId id, Caste caste, std::uint64_t decisions) {
    const auto timing = worker_timing(s, caste);
    const bool founder_review=sustained_supply(s) && caste==Caste::Queen && s.founding;
    if (!timing && !founder_review) return s.social->decision_interval.milliseconds;
    const auto interval=timing ? timing->check_interval : s.founding->profile.worker.behavior_interval;
    if (!variable_conditions(s)) return interval.milliseconds;
    auto rng = individual_rng(s.seed ^ UINT64_C(0x574f524b5f57414b), id, decisions);
    return rhythm_delay(rng,interval,250);
}

inline SimTime next_founding_lay(const auto& s, EntityId queen, const FoundingProfile& f,
                                 SimTime at, std::uint64_t attempts) {
    if (!variable_conditions(s)) return founding_lay_after(f, at);

    auto individual = individual_rng(s.seed ^ UINT64_C(0x4c41595f51554545), queen, 0);
    const SimTime first{rhythm_delay(individual, f.first_lay, 60)};
    if (!attempts) return first;

    // Keep the bounded founding bout; only actual paid, placeable eggs count.
    const auto end = after(first, f.opening_width.milliseconds);
    const auto cadence = 900 + bounded_draw(individual, 201);
    auto spacing = individual_rng(s.seed ^ UINT64_C(0x4c41595f53504143), queen, attempts);
    const auto jitter = [&](SimTime interval) {
        return rhythm_delay(spacing, {interval.milliseconds * static_cast<std::int64_t>(cadence) / 1000}, 400);
    };
    if (at >= end) return after(at, jitter(f.later_spacing));
    const auto next = after(at, jitter(f.opening_spacing));
    return next < end ? next : after(end, jitter(f.later_spacing));
}

inline ReproductionConfig founding_reproduction(const FoundingProfile& f) {
    return {f.later_spacing, f.egg_protein_ug, f.egg_water_ug, multiply(f.egg_lipid_ug, f.lipid_yield_nj_per_ug),
            f.lay_overhead_nj, ReproductionConfig{}.offspring_carrying_capacity_ug, f.maintenance_floor};
}

inline FoundingRation dietary_ration(const FoundingProfile& f, const PhysiologyState& donor, const FoundingReserve& maternal,
                                    const PhysiologyState& receiver, const FoundingReserve& larva) {
    const auto floor=donor.oxidized_carbs_ug ? dietary_maintenance(f,donor,maternal) : maintenance_cost(f,maternal);
    const auto spare_energy=deficit(dietary_energy(f,donor,maternal),add(floor.energy,1));
    const auto spare_water=deficit(add(donor.hydration_ug,donor.crop.water_ug),add(floor.water,1));
    const auto need=unfunded_brood(f,receiver,larva,LifeStage::Larva);
    const auto energy_limit=std::min(spare_energy,multiply(f.ration_lipid_ug,f.lipid_yield_nj_per_ug));
    const auto yield=donor.config.carbohydrate_yield_nj_per_ug;
    const auto room=std::min(donor.config.transfer_limit_ug,receiver.config.crop_capacity_ug-receiver.crop.total_ug());
    const auto protein=std::min({room,f.ration_protein_ug,add(donor.crop.protein_ug,maternal.mobile_protein_ug),need.protein_ug});
    const auto water=std::min({room-protein,f.ration_water_ug,spare_water,need.water_ug});
    const auto carb_mass=std::min({room-protein-water,donor.crop.carbs_ug,ceil_div(need.energy_nj,yield),energy_limit/yield});
    const auto from_crop=multiply(carb_mass,yield);
    const auto lipid=std::min({maternal.lipid_ug,f.larval_lipid_capacity_ug-larva.lipid_ug,room-protein-water-carb_mass,
        ceil_div(deficit(need.energy_nj,from_crop),f.lipid_yield_nj_per_ug),(energy_limit-from_crop)/f.lipid_yield_nj_per_ug});
    return {lipid,{carb_mass,protein,water,0}};
}

inline FoundingRation founding_ration(const FoundingProfile& f, const PhysiologyState& donor, const FoundingReserve& maternal,
                                      const PhysiologyState& receiver, const FoundingReserve& larva, bool local_feeding=false) {
    if (!donor.body_energy_nj || !donor.hydration_ug || !receiver.body_energy_nj || !receiver.hydration_ug) return {};
    if (local_feeding && has_founding_diet(donor)) return dietary_ration(f,donor,maternal,receiver,larva);
    const auto floor = maintenance_cost(f, maternal);
    const auto energy = founding_energy(f, donor, maternal);
    if (energy <= floor.energy || donor.hydration_ug <= floor.water) return {};
    const auto lipid = std::min({f.ration_lipid_ug, maternal.lipid_ug, f.larval_lipid_capacity_ug-larva.lipid_ug,
                                 (energy-floor.energy-1)/f.lipid_yield_nj_per_ug});
    const auto room = receiver.config.crop_capacity_ug - receiver.crop.total_ug();
    const auto stored_protein = add(receiver.tissue_protein_ug, receiver.crop.protein_ug);
    const auto stored_water = add(receiver.hydration_ug, receiver.crop.water_ug);
    const auto protein = std::min({f.ration_protein_ug, maternal.mobile_protein_ug, room,
                                   f.larval_tissue_ug-std::min(stored_protein, f.larval_tissue_ug)});
    const auto water = std::min({f.ration_water_ug, room-protein, donor.hydration_ug-floor.water-1,
                                 receiver.config.hydration_capacity_ug-std::min(stored_water, receiver.config.hydration_capacity_ug)});
    return {lipid, {0, protein, water, 0}};
}

inline void apply_founding_ration(const FoundingRation& amount, PhysiologyState& donor, FoundingReserve& maternal,
                                   PhysiologyState& receiver, FoundingReserve& larva, bool local_feeding=false) {
    const FoodMass oral=local_feeding && has_founding_diet(donor) ? ingredient_min(donor.crop,amount.crop) : FoodMass{};
    maternal.lipid_ug -= amount.lipid_ug;
    maternal.mobile_protein_ug -= amount.crop.protein_ug-oral.protein_ug;
    donor.hydration_ug -= amount.crop.water_ug-oral.water_ug;
    donor.crop = subtract(donor.crop,oral);
    larva.lipid_ug = add(larva.lipid_ug, amount.lipid_ug);
    receiver.crop = sum(receiver.crop, amount.crop);
}

inline WorldEvent lipid_conversion(const FoundingProfile& f, const AntState& ant, ScheduledId source, std::uint64_t lipid) {
    WorldEvent event;
    event.kind = FactKind::FoundingLipidConverted;
    event.actor = ant.id;
    event.colony = ant.colony;
    event.stage = ant.stage;
    event.position = ant.position;
    event.source = source;
    event.payload = lipid;
    event.random_value = multiply(lipid, f.lipid_yield_nj_per_ug);
    return event;
}
} // namespace antworld::detail
