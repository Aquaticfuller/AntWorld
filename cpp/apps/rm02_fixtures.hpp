#pragma once

#include "rm02_observer.hpp"
#include "s6_3_1_fixture.hpp"

namespace antworld::rm02 {
inline RuntimeLimits contact_limits() {
    RuntimeLimits limits;
    limits.events_per_timestamp = 10000;
    limits.committed_events = 200000;
    limits.checkpoint_bytes = 64 * 1024 * 1024;
    return limits;
}

// Mirrors the frozen dense TD-01 workload. Performance identity is checked
// against its archived facts, state, queue and contact work, outside timing.
struct DenseFixture {
    WorldRuntime world;
    std::vector<EntityId> focal;
    DenseFixture(unsigned population, std::uint64_t seed) : world({6, 6}, seed, {}, contact_limits()) {
        world.configure_social({});
        const auto colony = world.seed_colony();
        std::vector<AntRef> workers;
        for (unsigned i = 0; i < population; ++i) {
            const auto actor = world.seed_ant(colony, {});
            world.enable_physiology(actor, {{100, 400, 400, 100}, 1000000000, 1000, 0});
            workers.push_back(actor);
            if (focal.size() < focal_limit)
                focal.push_back(actor.id);
        }
        for (const auto actor : workers)
            world.set_behavior(actor, IndividualBehavior::Nurse);
    }
};

inline s6_3_1_fixture::World ecology_fixture(std::uint64_t seed, unsigned workers, std::string_view arm) {
    if (arm != "depot" && arm != "ordinary" && arm != "scarce" && arm != "empty")
        throw std::invalid_argument("unknown RM-02 ecology arm");
    s6_3_1_fixture::Controls controls;
    controls.reserve_mode = 1;
    controls.positive = arm == "depot";
    const auto supply = arm == "depot" || arm == "ordinary" ? "balanced" : arm;
    return s6_3_1_fixture::World(seed, workers, supply, false, {}, 6, false, controls);
}

inline std::vector<EntityId> ecology_focal(const s6_3_1_fixture::World& fixture) {
    std::vector<EntityId> ids{fixture.queen.id};
    for (const auto worker : fixture.workers)
        ids.push_back(worker.id);
    return ids;
}
} // namespace antworld::rm02
