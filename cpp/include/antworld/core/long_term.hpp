#pragma once
#include "antworld/core/physiology.hpp"

namespace antworld {
// All numerical biological assumptions are ENGINEERING_FIXTURE.
struct LongTermConfig {
  bool demand_feedback{true}, protein_recycling{true};
  std::uint32_t empty_sites_per_contact{4};
  bool complete_depot_visits{true}, post_intake_contact{true};
  bool operator==(const LongTermConfig &) const = default;
};
struct ReproductionConfig {
  SimTime interval{172800000};
  std::uint64_t egg_protein_ug{20}, egg_water_ug{200};
  std::uint64_t egg_energy_nj{500000000}, dissipated_energy_nj{10000000};
  std::uint64_t offspring_carrying_capacity_ug{4000};
  // ENGINEERING_FIXTURE local body-condition allocation horizon; zero preserves
  // S6.3.
  SimTime maintenance_horizon{};
  bool operator==(const ReproductionConfig &) const = default;
};
struct ReproductionState {
  ReproductionConfig config;
  ScheduledId wake;
  std::uint64_t attempts{}, births{};
  bool operator==(const ReproductionState &) const = default;
};
struct ResourceCycleConfig {
  FoodMass reserve, release_limit;
  SimTime interval{86400000}, productive_span{1296000000};
  bool cyclic{};
  std::uint32_t low_productivity_permille{};
  bool operator==(const ResourceCycleConfig &) const = default;
};
struct ResourceCycleState {
  ResourceCycleConfig config;
  FoodMass remaining, released;
  ScheduledId wake;
  std::uint64_t pulses{};
  bool operator==(const ResourceCycleState &) const = default;
};
} // namespace antworld
