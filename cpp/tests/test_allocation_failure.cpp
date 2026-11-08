#include "antworld/core/world_runtime.hpp"
#include <cstdlib>
#include <cstdio>
#include <exception>
#include <iostream>
#include <new>
#include <stdexcept>

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
} // namespace
int main() {
    // Turn an unexpected noexcept failure into a useful CI failure, not a CRT dialog.
    std::set_terminate([] {
        remaining = -1;
        std::fprintf(stderr, "Unexpected terminate: scenario=%s allocation=%ld\n", current_scenario, current_fault);
        std::_Exit(86);
    });
    try {
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
