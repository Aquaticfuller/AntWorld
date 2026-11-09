#pragma once
#include "s3_fixture.hpp"
#include "s4_fixture.hpp"
#include <string>

namespace antworld::s6_fixture {
inline RuntimeLimits limits() {
  RuntimeLimits l;
  l.events_per_timestamp = 10000;
  l.committed_events = 1000000;
  l.checkpoint_bytes = 256 * 1024 * 1024;
  return l;
}
// ENGINEERING_FIXTURE: explicit frozen finite resources, never calibrated
// ecology.
struct IntegratedOptions {
  unsigned workers{32};
  std::uint64_t source_protein_ug{2000};
  bool gift_first{}, local_work_continuation{};
  SimTime minimum_program_time{10000};
};
inline IntegratedOptions correction_options(const std::string& policy) {
  IntegratedOptions result;
  if (policy != "legacy" && policy != "gift_first" &&
      policy != "local_continuation" && policy != "combined")
    throw std::invalid_argument("unknown nursing correction policy");
  result.gift_first = policy == "gift_first" || policy == "combined";
  result.local_work_continuation = policy == "local_continuation" || policy == "combined";
  return result;
}
struct Integrated {
  WorldRuntime world;
  ColonyRef colony;
  std::vector<AntRef> identities = std::vector<AntRef>(0);
  GeometryConfig geometry;
  Integrated(std::uint64_t seed, const std::string &condition = "supplied",
             bool mirror = false, std::uint32_t budget = 16,
             const IntegratedOptions& options = {})
      : world({6, 8}, seed, {}, limits()) {
    if (condition != "supplied" && condition != "protein_absent" &&
        condition != "food_absent" && condition != "sealed")
      throw std::invalid_argument("unknown integrated condition");
    if (!options.workers || options.workers > 128 || options.source_protein_ug > 2000)
      throw std::invalid_argument("invalid declared integrated fixture variation");
    world.configure_surface({{-.03, 0, -.03}, 7, 7, .01}, {});
    geometry.origin_m = {-.008, -.006, -.006};
    geometry.initial_solid = {{0, 0, 0}, {32, 24, 24}};
    const BoxQ chamber{{12, 8, 8}, {20, 16, 16}},
        passage{{0, 10, 10}, {32, 14, 14}};
    std::vector<BoxQ> voids{chamber}, rocks(0);
    if (condition == "sealed")
      rocks = {{{10, 6, 6}, {12, 18, 18}}, {{20, 6, 6}, {22, 18, 18}},
               {{12, 6, 6}, {20, 8, 18}},  {{12, 16, 6}, {20, 18, 18}},
               {{12, 8, 6}, {20, 16, 8}},  {{12, 8, 16}, {20, 16, 18}}};
    else
      voids.push_back(passage);
    world.configure_geometry(geometry, voids, rocks);
    SocialConfig social;
    social.encounter_budget = budget;
    social.gift_first = options.gift_first;
    social.local_work_continuation = options.local_work_continuation;
    social.minimum_program_time = options.minimum_program_time;
    world.configure_social(social);
    colony = world.seed_colony();
    auto seed_identity = [&](LifeStage stage, Caste caste) {
      const auto a = world.seed_ant(colony, {{}, stage, caste, 4000});
      identities.push_back(a);
      PhysiologySeed initial;
      if (stage == LifeStage::Pupa)
        initial.tissue_protein_ug = 100;
      world.enable_physiology(a, initial);
    };
    seed_identity(LifeStage::Adult, Caste::Queen);
    for (unsigned i = 0; i < options.workers; ++i)
      seed_identity(LifeStage::Adult, Caste::Worker);
    for (unsigned i = 0; i < 4; ++i)
      seed_identity(LifeStage::Egg, Caste::Worker);
    for (unsigned i = 0; i < 6; ++i)
      seed_identity(LifeStage::Larva, Caste::Worker);
    for (unsigned i = 0; i < 2; ++i)
      seed_identity(LifeStage::Pupa, Caste::Worker);
    if (condition != "food_absent") {
      world.seed_food({mirror ? -.02 : .02, 0, .01}, {1000, 0, 3000, 0});
      world.seed_food({mirror ? .02 : -.02, 0, -.01},
                      condition == "protein_absent"
                          ? FoodMass{0, 0, 2500, 2500}
                          : FoodMass{0, options.source_protein_ug, 2500, 2500-options.source_protein_ug});
    }
    for (std::size_t i = 1; i < identities.size(); ++i)
      world.set_autonomy(identities[i]);
  }
};
struct Surplus {
  WorldRuntime world;
  ColonyRef colony;
  AntRef donor;
  std::array<AntRef, 2> larvae;
  Surplus(std::uint64_t seed, const std::string &condition,
          bool emerged = false, std::uint32_t budget = 16, const std::string& policy = "legacy")
      : world({6, 9}, seed, {}, limits()) {
    if (condition != "contact" && condition != "wall" && condition != "range" &&
        condition != "no_response" && condition != "no_protein")
      throw std::invalid_argument("unknown surplus condition");
    GeometryConfig g;
    g.origin_m = {-.016, -.016, -.016};
    g.initial_solid = {{0, 0, 0}, {64, 64, 64}};
    std::vector<BoxQ> voids{{{4, 4, 4}, {60, 60, 60}}}, rocks(0);
    if (condition == "wall") {
      voids = {{{4, 4, 4}, {32, 60, 60}}, {{33, 4, 4}, {60, 60, 60}}};
      rocks = {{{32, 4, 4}, {33, 60, 60}}};
    }
    world.configure_geometry(g, voids, rocks);
    SocialConfig social;
    social.encounter_budget = budget;
    social.exchange_enabled = condition != "no_response";
    const auto corrections=correction_options(policy);
    social.gift_first=corrections.gift_first;
    social.local_work_continuation=corrections.local_work_continuation;
    world.configure_social(social);
    const auto p = s4_fixture::position({31, 32, 32}, g),
               q = s4_fixture::position(
                   {condition == "range" ? 48 : 34, 32, 32}, g);
    colony = world.seed_colony(p);
    donor = world.seed_ant(colony,
                           {p, emerged ? LifeStage::Pupa : LifeStage::Adult});
    const FoodMass crop = condition == "no_protein"
                              ? FoodMass{100, 0, 400, 500}
                              : FoodMass{100, 400, 400, 100};
    world.enable_physiology(donor,
                            {crop, 1000000000, 1000, emerged ? 100U : 0U});
    world.set_autonomy(donor);
    for (auto &a : larvae) {
      a = world.seed_ant(colony, {q, LifeStage::Larva});
      world.enable_physiology(a);
      world.set_autonomy(a);
    }
  }
};
inline void balanced(const WorldRuntime &world) {
  s3_fixture::balanced(world);
  s4_fixture::balanced(world);
}
} // namespace antworld::s6_fixture
