#pragma once
#include "antworld/core/world_runtime.hpp"
#include "antworld/core/rng.hpp"
#include <array>
#include <stdexcept>

namespace antworld::s3_fixture {
// All populations, states, rates and timing are ENGINEERING_FIXTURE.
inline void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
inline void balanced(const WorldRuntime& world) {
    const auto n = world.nutrition_snapshot();
    require(n.introduced == n.accounted, "ingredient imbalance");
    require(n.energy_input_nj == n.body_energy_nj+n.dissipated_energy_nj, "energy imbalance");
}
inline void roundtrip(const WorldRuntime& world) {
    WorldRuntime copy({9,9}, 0); copy.restore(world.checkpoint());
    require(copy.checkpoint() == world.checkpoint(), "noncanonical physiology checkpoint");
    require(copy.nutrition_snapshot() == world.nutrition_snapshot(), "restored physiology query mismatch");
}
struct Brood {
    WorldRuntime world;
    ColonyRef colony;
    std::array<AntRef, 2> nurses;
    std::array<AntRef, 4> brood;
    Brood(std::uint64_t seed, bool protein, bool eggs, std::int64_t pulse = 1000)
        : world({3,3}, seed), colony(world.seed_colony()) {
        PhysiologyConfig config; config.absorption_period = {pulse}; Rng rng(seed);
        for (auto& a : nurses) {
            a = world.seed_ant(colony, {});
            PhysiologySeed initial; initial.crop = {100, protein ? 400U : 0U, 400, protein ? 100U : 500U};
            world.enable_physiology(a, initial, config);
        }
        for (auto& a : brood) {
            a = world.seed_ant(colony, {{}, eggs ? LifeStage::Egg : LifeStage::Larva, Caste::Worker, 4000});
            PhysiologySeed initial; initial.body_energy_nj = UINT64_C(500000000)+rng.next()%UINT64_C(500000001);
            world.enable_physiology(a, initial, config);
        }
        for (const auto a : nurses) world.set_behavior(a, IndividualBehavior::Nurse);
    }
};
struct Exchange {
    WorldRuntime world;
    ColonyRef colony;
    AntRef first, second, recipient;
    Exchange(std::uint64_t seed, std::uint64_t capacity, bool supply, bool reverse)
        : world({3,4}, seed), colony(world.seed_colony()), first(world.seed_ant(colony, {})),
          second(world.seed_ant(colony, {})), recipient(world.seed_ant(colony, {})) {
        PhysiologyConfig c; c.basal_nj_per_ms = 0; c.water_loss_ug_per_s = 0;
        PhysiologySeed p; if (supply) p.crop = {80,40,60,20};
        world.enable_physiology(first, p, c); world.enable_physiology(second, p, c);
        c.crop_capacity_ug = capacity; world.enable_physiology(recipient, {}, c);
        for (auto a : (reverse ? std::array{second,first} : std::array{first,second}))
            world.submit_nutrition({a, {500}, NutritionAction::Trophallaxis, recipient, 200});
    }
};
} // namespace antworld::s3_fixture
