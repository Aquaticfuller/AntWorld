#pragma once
#include "social_internal.hpp"

namespace antworld::detail {
inline void validate_long_term(const LongTermConfig &c) {
  if (!c.empty_sites_per_contact || c.empty_sites_per_contact > 128)
    throw std::invalid_argument("invalid local space ENGINEERING_FIXTURE");
}
inline std::uint64_t long_term_fingerprint(const LongTermConfig &c) {
  return UINT64_C(0x5336330000000000) |
         (std::uint64_t{c.empty_sites_per_contact} << 4) |
         (c.demand_feedback ? 1U : 0U) | (c.protein_recycling ? 2U : 0U) |
         (c.complete_depot_visits ? 4U : 0U) |
         (c.post_intake_contact ? 8U : 0U);
}
inline void validate_reproduction(const ReproductionConfig &c,
                                  const PhysiologyConfig &p) {
  if (c.interval.milliseconds < 1 ||
      c.interval.milliseconds > INT64_C(31536000000) || !c.egg_protein_ug ||
      c.egg_protein_ug > p.larval_protein_requirement_ug || !c.egg_water_ug ||
      c.egg_water_ug >= p.hydration_capacity_ug || !c.egg_energy_nj ||
      add(c.egg_energy_nj, c.dissipated_energy_nj) >= p.energy_capacity_nj ||
      p.adult_protein_target_ug != c.egg_protein_ug ||
      !c.offspring_carrying_capacity_ug ||
      c.offspring_carrying_capacity_ug > 1000000000)
    throw std::invalid_argument(
        "invalid funded reproduction ENGINEERING_FIXTURE");
}
inline void validate_cycle(const ResourceCycleConfig &c) {
  if (!c.reserve.total_ug() || !c.release_limit.total_ug() ||
      c.interval.milliseconds < 1 ||
      c.interval.milliseconds > INT64_C(31536000000) ||
      c.productive_span.milliseconds < c.interval.milliseconds ||
      c.productive_span.milliseconds > INT64_C(31536000000) ||
      c.low_productivity_permille > 1000)
    throw std::invalid_argument("invalid finite resource ENGINEERING_FIXTURE");
}
inline std::uint32_t productivity(const ResourceCycleConfig &c, SimTime at) {
  return c.cyclic && (at.milliseconds / c.productive_span.milliseconds) % 2
             ? c.low_productivity_permille
             : 1000U;
}
inline FoodMass release_amount(const ResourceCycleState &r, SimTime at) {
  const auto scale = productivity(r.config, at);
  auto scaled = [&](std::uint64_t v) { return multiply(v, scale) / 1000; };
  const auto &l = r.config.release_limit;
  return ingredient_min(r.remaining, {scaled(l.carbs_ug), scaled(l.protein_ug),
                                      scaled(l.water_ug), scaled(l.other_ug)});
}
} // namespace antworld::detail
