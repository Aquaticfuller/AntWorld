#pragma once

#include "checkpoint_s3.hpp"
#include "founding_internal.hpp"

namespace antworld::detail {
inline constexpr auto founding_magic = UINT64_C(0x4654504b435741); // AWCKPTF
inline constexpr std::array founding_times{
    &FoundingProfile::first_lay, &FoundingProfile::opening_width, &FoundingProfile::opening_spacing,
    &FoundingProfile::later_spacing, &FoundingProfile::maintenance_floor};
inline constexpr std::array founding_values{
    &FoundingProfile::wet_mass_ug, &FoundingProfile::structural_minimum_ug, &FoundingProfile::lipid_ug,
    &FoundingProfile::protein_ug, &FoundingProfile::water_ug, &FoundingProfile::lipid_yield_nj_per_ug,
    &FoundingProfile::basal_nj_per_day, &FoundingProfile::active_nj_per_ms, &FoundingProfile::water_ug_per_day,
    &FoundingProfile::egg_lipid_ug, &FoundingProfile::egg_protein_ug, &FoundingProfile::egg_water_ug,
    &FoundingProfile::lay_overhead_nj, &FoundingProfile::larval_tissue_ug, &FoundingProfile::larval_lipid_capacity_ug,
    &FoundingProfile::ration_lipid_ug, &FoundingProfile::ration_protein_ug, &FoundingProfile::ration_water_ug};

inline void write_founding_profile(Writer& w, EntityId founder, const FoundingProfile& p) {
    w.put(FoundingProfile::version, 4);
    w.put(static_cast<std::uint8_t>(p.population), 1);
    w.put(founder.value);
    for (const auto& b : p.brood) { w.time(b.duration); w.put(b.basal_nj_per_day); w.put(b.water_ug_per_day); }
    for (const auto member : physiology_config_times) w.time(p.worker.*member);
    for (const auto member : physiology_config_values) w.put(p.worker.*member);
    w.time(p.worker.water_loss_period);
    w.put(p.worker.adult_protein_target_ug);
    for (const auto member : founding_times) w.time(p.*member);
    for (const auto member : founding_values) w.put(p.*member);
}

template<class S> void write_founding(Writer& w, const S& s, bool frame) {
    write_founding_profile(w, s.founding->founder, s.founding->profile);
    w.put(s.founding_reserves.size());
    for (const auto& [id, row] : s.founding_reserves) {
        w.put(id.value);
        w.put(row.lipid_ug); w.put(row.spent_lipid_ug); w.put(row.mobile_protein_ug);
        w.put(row.energy_remainder); w.put(row.water_remainder);
    }
    if (frame) w.put(s.m.founding_trace);
}

template<class S> void read_founding(Reader& r, S& s, const RuntimeLimits& limits, bool frame) {
    ensure(r.get(4) == FoundingProfile::version, "unsupported F1 profile version");
    typename S::FoundingSetup setup;
    auto& p = setup.profile;
    p.population = static_cast<FoundingPopulation>(r.get(1));
    setup.founder = {r.get()};
    for (auto& b : p.brood) b = {r.time(), r.get(), r.get()};
    for (const auto member : physiology_config_times) p.worker.*member = r.time();
    for (const auto member : physiology_config_values) p.worker.*member = r.get();
    p.worker.water_loss_period = r.time();
    p.worker.adult_protein_target_ug = r.get();
    for (const auto member : founding_times) p.*member = r.time();
    for (const auto member : founding_values) p.*member = r.get();
    validate_founding(p);
    ensure(s.long_term && s.social && s.care_profile && s.care_profile->motion && s.care_profile->motion->integrate_autonomy &&
           s.ants.index.contains(setup.founder) && s.reproduction.contains(setup.founder) &&
           s.reproduction.at(setup.founder).config == founding_reproduction(p) &&
           s.ants.get(s.ants.index.at(setup.founder)).caste == Caste::Queen, "invalid F1 founder ownership");
    for (const auto& [id, reproduction] : s.reproduction)
        if (id != setup.founder) validate_reproduction(reproduction.config, s.physiology.at(id).config);
    const auto count = r.count(limits.entities, 48);
    EntityId previous;
    std::uint64_t lipid = 0;
    for (std::size_t i = 0; i < count; ++i) {
        const EntityId id{r.get()};
        const FoundingReserve row{r.get(), r.get(), r.get(), r.get(), r.get()};
        ensure(id > previous && s.physiology.contains(id) && row.energy_remainder < founding_day_ms && row.water_remainder < founding_day_ms &&
               (id == setup.founder ? row.mobile_protein_ug <= p.protein_ug : !row.mobile_protein_ug && s.physiology.at(id).mother == setup.founder),
               "invalid F1 reserve row");
        const auto& physiology = s.physiology.at(id);
        const auto stage = s.ants.get(s.ants.index.at(id)).stage;
        ensure(physiology.config == founding_physiology(p, id==setup.founder) && !physiology.water_loss_remainder &&
               !physiology.exported_energy_nj && (stage==LifeStage::Dead || physiology.stage_progress <= stage_duration(physiology.config,stage)),
               "invalid F1 physiological bounds");
        lipid = add(lipid, add(row.lipid_ug, row.spent_lipid_ug));
        s.founding_reserves.emplace(id, row);
        previous = id;
    }
    ensure(s.founding_reserves.contains(setup.founder) && lipid == p.lipid_ug, "F1 ledger lacks seeded material");
    if (frame) ensure(r.get() == s.m.founding_trace, "F1 frame history digest mismatch");
    s.founding = std::make_shared<const typename S::FoundingSetup>(setup);
}
} // namespace antworld::detail
