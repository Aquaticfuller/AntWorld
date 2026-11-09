#pragma once
#include "s6_3_fixture.hpp"

namespace antworld::s6_3_1_fixture {
using s6_3_fixture::day;
using s6_3_fixture::hour;
using s6_3_fixture::limits;
// All quantities and schedules are ENGINEERING_FIXTURE; protocol 44 fixes the
// arms.
struct Controls {
  bool laying{true}, exchange{true}, positive{};
  std::int64_t absorption_hours{6}, behavior_hours{6}, reproduction_days{2};
  std::uint64_t lineage_basal{1};
};
struct World {
  WorldRuntime world;
  ColonyRef colony;
  AntRef queen;
  std::vector<AntRef> workers = std::vector<AntRef>(0);
  World(std::uint64_t seed, unsigned population = 8,
        std::string_view supply = "balanced", bool cyclic = false,
        LongTermConfig policy = {}, std::int64_t pulse_hours = 6,
        bool compact = false, Controls controls = {})
      : world({63, 1}, seed, {}, limits()) {
    if ((supply != "balanced" && supply != "scarce" && supply != "empty") ||
        !population || population > 2048)
      throw std::invalid_argument("invalid frozen long-term fixture");
    world.configure_long_term(policy);
    BehaviorConfig behavior;
    behavior.trails_enabled = false;
    world.configure_surface({{-.03, 0, -.03}, 7, 7, .01}, {}, behavior);
    GeometryConfig g;
    g.origin_m = {-.008, -.006, -.006};
    g.initial_solid = {{0, 0, 0}, {32, 24, 24}};
    const std::array<BoxQ, 2> voids{{compact ? BoxQ{{14, 10, 10}, {18, 14, 14}}
                                             : BoxQ{{12, 8, 8}, {20, 16, 16}},
                                     {{0, 10, 10}, {32, 14, 14}}}};
    world.configure_geometry(g, voids);
    SocialConfig social;
    social.gift_first = true;
    social.local_work_continuation = true;
    social.decision_interval = {pulse_hours * hour};
    social.minimum_program_time = {pulse_hours * hour};
    social.exchange_enabled = controls.exchange;
    social.decision_interval = {controls.behavior_hours * hour};
    social.minimum_program_time = social.decision_interval;
    world.configure_social(social);
    colony = world.seed_colony();
    PhysiologyConfig p;
    p.absorption_period = {controls.absorption_hours * hour};
    p.behavior_interval = {controls.behavior_hours * hour};
    p.water_loss_period = {hour};
    p.egg_duration = {2 * day};
    p.larva_duration = {3 * day};
    p.pupa_duration = {2 * day};
    p.basal_nj_per_ms = controls.lineage_basal;
    p.active_nj_per_ms = 1;
    const PhysiologySeed initial{{200, 100, 200, 0}, 1500000000, 1600, 0};
    queen = world.seed_ant(colony, {{}, LifeStage::Adult, Caste::Queen, 4000});
    p.adult_protein_target_ug = 20;
    world.enable_physiology(queen, initial, p);
    ReproductionConfig reproduction;
    reproduction.interval = {controls.reproduction_days * day};
    if (controls.laying)
      world.enable_reproduction(queen, reproduction);
    p.basal_nj_per_ms = 1;
    p.adult_protein_target_ug = 0;
    for (unsigned i = 0; i < population; ++i) {
      const auto a =
          world.seed_ant(colony, {{}, LifeStage::Adult, Caste::Worker, 4000});
      world.enable_physiology(a, initial, p);
      world.set_autonomy(a);
      workers.push_back(a);
    }
    if (controls.positive) {
      world.seed_food({}, {200000ULL * population, 20000ULL * population,
                           100000ULL * population, 0});
    } else if (supply != "empty") {
      const auto food = world.seed_food({.02, 0, .01}, {4000, 500, 4000, 0});
      ResourceCycleConfig cycle;
      cycle.reserve = {20000ULL * population,
                       (supply == "scarce" ? 50ULL : 2000ULL) * population,
                       5000ULL * population, 0};
      cycle.release_limit = {4000, 400, 2000, 0};
      cycle.cyclic = cyclic;
      world.configure_resource_cycle(food, cycle);
    }
  }
};
using s6_3_fixture::conserved;
} // namespace antworld::s6_3_1_fixture
