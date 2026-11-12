#pragma once

#include "physiology_internal.hpp"

namespace antworld::detail {
inline constexpr std::uint64_t founding_day_ms = 86'400'000;
inline constexpr std::uint32_t founding_schema_version = 15, founding_physics_version = 17;
inline constexpr std::uint32_t founding_persistence_schema_version = 16, founding_persistence_physics_version = 18;
inline constexpr std::uint32_t founding_access_schema_version = 17, founding_access_physics_version = 19;
inline constexpr std::int64_t founding_hatch_cooldown_ms = 3'600'000; // ENGINEERING_FIXTURE
std::uint64_t founding_profile_hash(EntityId founder, const FoundingProfile&);

struct FoundingRates { std::uint64_t energy, water; };
struct FoundingRation {
    std::uint64_t lipid_ug{};
    FoodMass crop;
    bool operator==(const FoundingRation&) const = default;
};

inline std::uint64_t ceil_div(std::uint64_t n, std::uint64_t d) { return n/d + (n%d != 0); }

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
        const bool active = maximum || p.behavior == IndividualBehavior::Forage || p.behavior == IndividualBehavior::Nurse ||
                            p.behavior == IndividualBehavior::Excavate;
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

inline bool funds_founding_egg(const FoundingProfile& f, const PhysiologyState& p, const FoundingReserve& r) {
    const auto floor = maintenance_cost(f, r);
    return p.body_energy_nj > f.lay_overhead_nj && r.lipid_ug >= f.egg_lipid_ug && r.mobile_protein_ug >= f.egg_protein_ug &&
           p.hydration_ug > add(f.egg_water_ug, floor.water) &&
           founding_energy(f, p, r) > add(add(multiply(f.egg_lipid_ug, f.lipid_yield_nj_per_ug), f.lay_overhead_nj), floor.energy);
}

inline void debit_founding_egg(const FoundingProfile& f, PhysiologyState& p, FoundingReserve& r) {
    r.lipid_ug -= f.egg_lipid_ug;
    r.mobile_protein_ug -= f.egg_protein_ug;
    p.hydration_ug -= f.egg_water_ug;
    p.body_energy_nj -= f.lay_overhead_nj;
    p.dissipated_energy_nj = add(p.dissipated_energy_nj, f.lay_overhead_nj);
}

inline SimTime founding_lay_after(const FoundingProfile& f, SimTime at) {
    const auto end = after(f.first_lay, f.opening_width.milliseconds);
    if (at < f.first_lay) return f.first_lay;
    if (at >= end) return after(at, f.later_spacing.milliseconds);
    const auto next = after(at, f.opening_spacing.milliseconds);
    return next < end ? next : after(end, f.later_spacing.milliseconds);
}

inline ReproductionConfig founding_reproduction(const FoundingProfile& f) {
    return {f.later_spacing, f.egg_protein_ug, f.egg_water_ug, multiply(f.egg_lipid_ug, f.lipid_yield_nj_per_ug),
            f.lay_overhead_nj, ReproductionConfig{}.offspring_carrying_capacity_ug, f.maintenance_floor};
}

inline FoundingRation founding_ration(const FoundingProfile& f, const PhysiologyState& donor, const FoundingReserve& maternal,
                                      const PhysiologyState& receiver, const FoundingReserve& larva) {
    if (!donor.body_energy_nj || !donor.hydration_ug || !receiver.body_energy_nj || !receiver.hydration_ug) return {};
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
                                   PhysiologyState& receiver, FoundingReserve& larva) {
    maternal.lipid_ug -= amount.lipid_ug;
    maternal.mobile_protein_ug -= amount.crop.protein_ug;
    donor.hydration_ug -= amount.crop.water_ug;
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
