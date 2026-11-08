#pragma once
#include "s2_fixture.hpp"
#include <algorithm>
#include <cmath>
#include <map>
#include <set>

namespace antworld::fixture {
// ENGINEERING_FIXTURE: the observer measures the experienced route; no part of
// this observer state is passed to the scout or novice behavior model.
struct Recruitment {
    WorldRuntime world;
    SurfaceConfig grid{{-0.10, 0, -0.07}, 21, 15, 0.01};
    ColonyRef colony;
    AntRef scout, novice;
    FoodRef food;
    std::vector<Cell> experienced_route = std::vector<Cell>(0);
    SimTime delivered_at{-1}, retired_at{-1};
    Recruitment(std::uint64_t seed, bool reflected, std::string_view treatment)
        : world({0x533231, 1}, seed) {
        BehaviorConfig p; p.memory_enabled = false;
        if (treatment == "absent") p.trails_enabled = false;
        else if (treatment == "blind") p.trail_weight = 0;
        else if (treatment != "present") throw std::invalid_argument("unknown recruitment treatment");
        world.configure_surface(grid, {}, p); const auto nest = position(grid, {10, 7}); colony = world.seed_colony(nest);
        scout = world.seed_ant(colony, {nest, LifeStage::Adult, Caste::Worker, 1000});
        novice = world.seed_ant(colony, {nest, LifeStage::Adult, Caste::Worker, 1000});
        food = world.seed_food(position(grid, {reflected ? 2 : 18, 7}), {1000000, 1000000, 1000000, 1000000});
        world.start_foraging(scout);
    }
    bool train(SimTime cap = {1800000}) {
        EventId cursor{};
        while (world.summary().now < cap) {
            const auto pending = world.pending_events();
            if (pending.empty()) throw std::logic_error("training lost scout schedule");
            world.advance_to(std::min(pending.front().key.time, cap));
            for (const auto& e : world.events_after(cursor, 64)) {
                cursor = e.id;
                if (e.actor == scout.id && e.kind == FactKind::FoodCollected && experienced_route.empty()) {
                    const auto f = *world.query_forager(scout);
                    experienced_route.assign(f.path.begin(), f.path.begin()+f.path_size);
                }
                if (e.actor == scout.id && e.kind == FactKind::FoodDelivered) {
                    delivered_at = e.time; retired_at = {e.time.milliseconds+1};
                    world.schedule_lifecycle(scout, retired_at, LifeStage::Dead); world.advance_to(retired_at);
                    if (world.query_forager(novice) || world.query_ant(novice)->carried_food.total_ug())
                        throw std::logic_error("novice gained experience during training");
                    return true;
                }
            }
        }
        return false;
    }
    Cell locate(PositionM p) const {
        return {static_cast<std::int32_t>(std::llround((p.x-grid.origin_m.x)/grid.cell_size_m)),
                static_cast<std::int32_t>(std::llround((p.z-grid.origin_m.z)/grid.cell_size_m))};
    }
};
inline void check_ingredients(const WorldRuntime& world) {
    const auto l = world.summary().food_ledger;
    for (std::size_t i = 0; i < 4; ++i) {
        const auto initial = l.introduced.components()[i], available = l.available.components()[i];
        const auto carried = l.carried.components()[i], stored = l.stored.components()[i];
        if (available > initial || carried > initial-available || stored != initial-available-carried)
            throw std::logic_error("recruitment ingredient conservation failed");
    }
}
} // namespace antworld::fixture
