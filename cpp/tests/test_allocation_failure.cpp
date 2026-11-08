#include "antworld/core/world_runtime.hpp"
#include <cstdlib>
#include <cstdio>
#include <exception>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string_view>

// Single-threaded fault injection. Only the operation under test has injection
// enabled. Verification and rollback comparisons run after it is disabled.
namespace {
long remaining = -1;
const char* current_scenario = "setup";
long current_fault = -1;
void* allocate(std::size_t bytes) {
    if (remaining == 0) throw std::bad_alloc{};
    if (remaining > 0) --remaining;
    if (auto* p = std::malloc(bytes == 0 ? 1 : bytes)) return p;
    throw std::bad_alloc{};
}
}
void* operator new(std::size_t bytes) { return allocate(bytes); }
void* operator new[](std::size_t bytes) { return allocate(bytes); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }

using namespace antworld;
namespace {
template <typename Fn> void sweep(const char* name, WorldRuntime& world, Fn action) {
    current_scenario = name;
    const auto before = world.checkpoint();
    for (long fault = 0; fault < 2000; ++fault) {
        world.restore(before); current_fault = fault; remaining = fault;
        bool failed = false;
        try { action(); } catch (const std::bad_alloc&) { failed = true; }
        catch (...) { remaining = -1; throw; }
        remaining = -1;
        if (!failed) {
            if (fault == 0) throw std::runtime_error("fault sweep exercised no allocation");
            std::cout << name << " rollback_points=" << fault << '\n';
            world.restore(before); return;
        }
        if (world.checkpoint() != before) throw std::runtime_error("allocation failure left partial world state");
    }
    throw std::runtime_error("fault sweep never completed");
}
void s2_sweeps() {
    // ENGINEERING_FIXTURE: a three-cell corridor isolates each commit boundary.
    WorldRuntime world({1, 2}, 12345); SurfaceConfig grid{{0, 0, 0}, 3, 1, 0.01};
    BehaviorConfig params; params.trail_half_life_s = 1; params.trail_cutoff_units = 0.5;
    sweep("surface_configure", world, [&] { world.configure_surface(grid, {}, params); });
    world.configure_surface(grid, {}, params); const auto colony = world.seed_colony();
    const auto ant = world.seed_ant(colony, {{}, LifeStage::Adult, Caste::Worker, 1000});
    sweep("local_food_index", world, [&] { world.seed_food({0.02, 0, 0}, {1000, 0, 0, 0}); });
    world.seed_food({0.02, 0, 0}, {1000, 0, 0, 0});
    sweep("activate_forager", world, [&] { world.start_foraging(ant); }); world.start_foraging(ant);
    sweep("local_decision_discovery", world, [&] { world.advance_to({0}); });
    world.advance_to({1099}); sweep("local_move", world, [&] { world.advance_to({1100}); });
    world.advance_to({3301}); sweep("collect_learned_route", world, [&] { world.advance_to({3302}); });
    world.advance_to({4402}); sweep("return_deposit", world, [&] { world.advance_to({4403}); });
    world.advance_to({4999}); sweep("field_decay_prune", world, [&] { world.advance_to({5000}); });
    world.advance_to({6604}); sweep("physical_delivery", world, [&] { world.advance_to({6605}); });
    world.advance_to({6605}); const auto bytes = world.checkpoint();
    sweep("restore_surface_history", world, [&] { world.restore(bytes); });
    world.schedule_lifecycle(ant, {6606}, LifeStage::Dead);
    sweep("cancel_dead_forager", world, [&] { world.advance_to({6606}); });
    world.advance_to({9999}); sweep("erase_decayed_trails", world, [&] { world.advance_to({10000}); });
    std::cout << "PASS S2_ALLOCATION_FAILURE\n";
}
void s2_1_sweeps() {
    WorldRuntime world({1, 2}, 12345);
    world.configure_surface({{}, 3, 1, 0.01}, {}); const auto colony = world.seed_colony();
    const auto ant = world.seed_ant(colony, {}); world.seed_food({0.02, 0, 0}, {1000, 0, 0, 0});
    world.advance_to({6000});
    sweep("late_first_activation", world, [&] { world.start_foraging(ant); });
    world.start_foraging(ant); const auto bytes = world.checkpoint();
    sweep("restore_late_activation", world, [&] { world.restore(bytes); });
    sweep("late_first_decision", world, [&] { world.advance_to({6001}); });
    std::cout << "PASS S2_1_ALLOCATION_FAILURE\n";
}
} // namespace
int main(int argc, char** argv) {
    // Turn an unexpected noexcept failure into a useful CI failure, not a CRT dialog.
    std::set_terminate([] {
        remaining = -1;
        std::fprintf(stderr, "Unexpected terminate: scenario=%s allocation=%ld\n", current_scenario, current_fault);
        std::_Exit(86);
    });
    try {
        if (argc == 2 && std::string_view(argv[1]) == "S2.1") { s2_1_sweeps(); return 0; }
        if (argc == 2 && std::string_view(argv[1]) == "S2") { s2_sweeps(); return 0; }
        if (argc != 1) throw std::invalid_argument("usage: antworld_allocation_tests [S2]");
        // ENGINEERING_FIXTURE: no biological parameter is inferred here.
        WorldRuntime world({1, 2}, 12345); const auto colony = world.seed_colony();
        const auto a = world.seed_ant(colony, {}); const auto b = world.seed_ant(colony, {});
        const auto food = world.seed_food({}, {1000, 1000, 1000, 1000});
        sweep("seed_ant", world, [&] { world.seed_ant(colony, {}); });
        sweep("seed_colony", world, [&] { world.seed_colony(); });
        sweep("seed_food", world, [&] { world.seed_food({}, {1, 2, 3, 4}); });
        for (int i = 0; i < 6; ++i) world.seed_ant(colony, {});
        sweep("grow_ant_columns", world, [&] { world.seed_ant(colony, {}); });
        sweep("schedule", world, [&] { world.schedule({{5}}); });
        sweep("submit", world, [&] { world.submit({a, {10}, ActionKind::CollectFood, food, {}, 3000}); });
        const auto diagnostic = world.schedule({{1}, Phase::Environment, 0, 0, 0, DiagnosticAction::DrawRandom});
        sweep("cancel", world, [&] { world.cancel(diagnostic); });
        world.submit({a, {2}, ActionKind::CollectFood, food, {}, 3000});
        world.submit({b, {2}, ActionKind::CollectFood, food, {}, 3000});
        world.submit({a, {1000}, ActionKind::Move, {}, {0.001, 0, 0}, 0});
        world.schedule_lifecycle(b, {1001}, LifeStage::Dead);
        sweep("advance", world, [&] { world.advance_to({2000}); });
        const auto loaded = world.checkpoint();
        sweep("restore", world, [&] { world.restore(loaded); });
        std::cout << "PASS S1_ALLOCATION_FAILURE\n"; return 0;
    } catch (const std::exception& e) { remaining = -1; std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
