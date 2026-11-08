#pragma once
#include "antworld/core/world_runtime.hpp"
#include <string_view>
#include <stdexcept>

namespace antworld::fixture {
// ENGINEERING_FIXTURE: same geometry, workers, food and seeds in every treatment.
inline PositionM position(const SurfaceConfig& c, Cell cell) {
    return {c.origin_m.x+cell.x*c.cell_size_m, c.origin_m.y, c.origin_m.z+cell.z*c.cell_size_m};
}
struct Scene {
    WorldRuntime world;
    SurfaceConfig surface;
    ColonyRef colony;
    std::vector<AntRef> workers = std::vector<AntRef>(0);
    std::vector<FoodRef> food = std::vector<FoodRef>(0);
    Scene(std::uint64_t seed, bool trails, bool memory, std::string_view layout, std::size_t population = 12,
        bool reverse_activation = false, RuntimeLimits limits = {}) : world({0x53320001, 1}, seed, {}, limits) {
        surface = {{-0.15, 0, -0.10}, 31, 21, 0.01};
        BehaviorConfig behavior; behavior.trails_enabled = trails; behavior.memory_enabled = memory;
        std::vector<Cell> blocked(0);
        if (layout == "barrier") {
            for (std::int32_t z = 0; z < 21; ++z) if (z != 4 && z != 16) blocked.push_back({15, z});
        } else if (layout != "open") throw std::invalid_argument("unknown S2 fixture layout");
        world.configure_surface(surface, blocked, behavior);
        const auto nest = position(surface, {3, 10}); colony = world.seed_colony(nest);
        for (std::size_t i = 0; i < population; ++i) workers.push_back(world.seed_ant(colony, {nest, LifeStage::Adult, Caste::Worker, 1000}));
        for (const Cell cell : {Cell{25, 5}, Cell{25, 15}})
            food.push_back(world.seed_food(position(surface, cell), {1000000, 1000000, 1000000, 1000000}));
        if (reverse_activation) for (auto i = workers.rbegin(); i != workers.rend(); ++i) world.start_foraging(*i);
        else for (const auto ant : workers) world.start_foraging(ant);
    }
};
} // namespace antworld::fixture
