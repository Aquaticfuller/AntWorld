#pragma once
#include "s3_fixture.hpp"

namespace antworld::s6_fixture {
// ENGINEERING_FIXTURE, frozen SD-04 comparison. No post-initialization nutrient
// injection.
struct Nutrition {
  WorldRuntime world;
  ColonyRef colony;
  std::array<AntRef, 2> nurses;
  std::array<AntRef, 4> brood;
  Nutrition(std::uint64_t seed, std::uint64_t protein, bool eggs, bool demand)
      : world({6, 1}, seed), colony(world.seed_colony()) {
    if (demand) {
      SocialConfig c;
      c.bounded_contacts = false;
      world.configure_social(c);
    }
    for (auto &a : nurses) {
      a = world.seed_ant(colony, {});
      world.enable_physiology(
          a, {{100, protein, 400, 500 - protein}, 1000000000, 1000, 0});
    }
    Rng rng(seed);
    for (auto &a : brood) {
      a = world.seed_ant(
          colony,
          {{}, eggs ? LifeStage::Egg : LifeStage::Larva, Caste::Worker, 4000});
      world.enable_physiology(
          a, {{},
              UINT64_C(500000000) + rng.next() % UINT64_C(500000001),
              1000,
              0});
    }
    for (auto a : nurses)
      world.set_behavior(a, IndividualBehavior::Nurse);
  }
};
} // namespace antworld::s6_fixture
