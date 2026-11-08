#include "s2_1_fixture.hpp"
#include <bit>
#include <iostream>
#include <string_view>

using namespace antworld;
namespace {
// All scenario numbers are ENGINEERING_FIXTURE, never calibrated species values.
void require(bool yes, const char* message) { if (!yes) throw std::runtime_error(message); }
template <typename F> void rejects(F fn, const char* message) {
    bool failed = false; try { fn(); } catch (const std::exception&) { failed = true; } require(failed, message);
}
void roundtrip(const WorldRuntime& world) {
    const auto before = world.checkpoint(); WorldRuntime copy({8, 9}, 5); copy.restore(before);
    require(before == copy.checkpoint(), "S2.1 checkpoint differs");
}
struct Inputs {
    BehaviorConfig params;
    ForagerState ant;
    LocalObservation local;
    Inputs() {
        ant.path[0] = {2, 2}; ant.path_size = 1; ant.heading = Direction::North; local.current = {2, 2}; local.step_count = 4;
        local.steps = {{{{2, 3}, Direction::North, 0}, {{3, 2}, Direction::East, 0}, {{2, 1}, Direction::South, 0}, {{1, 2}, Direction::West, 0}}};
    }
    BehaviorDecision choose(std::uint64_t seed) const { return choose_behavior(seed, {7}, false, ant, local, params); }
};
void bias() {
    Inputs input; input.local.food_count = 2;
    input.local.food[0] = {{100}, {3, 2}, 1, Direction::East}; input.local.food[1] = {{200}, {1, 2}, 1, Direction::West};
    std::uint64_t east = 0;
    for (std::uint64_t seed = 1; seed <= 4096; ++seed) {
        const auto a = input.choose(seed); if (a.destination == Cell{3, 2}) ++east;
        auto renamed = input; std::swap(renamed.local.food[0].resource, renamed.local.food[1].resource);
        const auto b = renamed.choose(seed);
        require(a.destination == b.destination && a.resource != b.resource, "resource renaming changed physical food choice");
        std::swap(renamed.local.food[0], renamed.local.food[1]);
        require(renamed.choose(seed) == b, "local cue enumeration changed a decision");
        auto relocated = input;
        std::swap(relocated.local.food[0].cell, relocated.local.food[1].cell);
        std::swap(relocated.local.food[0].first_step, relocated.local.food[1].first_step);
        require(relocated.choose(seed).destination == a.destination && relocated.choose(seed).resource != a.resource,
            "moving equal food sources while retaining IDs biased the physical choice");
        auto rotated = input;
        rotated.local.food[0] = {{100}, {2, 3}, 1, Direction::North}; rotated.local.food[1] = {{200}, {2, 1}, 1, Direction::South};
        const auto north = rotated.choose(seed).destination == Cell{2, 3};
        require(north == (a.destination == Cell{3, 2}), "physical rotation introduced a food tie preference");
    }
    require(east > 1850 && east < 2250, "equal-food population retains a strong preference");
    input.local.food_count = 3; input.local.food[2] = {{300}, {2, 3}, 1, Direction::North}; std::array<unsigned, 3> choices{};
    for (std::uint64_t seed = 1; seed <= 6000; ++seed) {
        const auto selected = input.choose(seed);
        for (std::size_t i = 0; i < 3; ++i) if (selected.resource == input.local.food[i].resource) ++choices[i];
    }
    for (const auto n : choices) require(n > 1750 && n < 2250, "three-way tie is not distributed");
    input.local.food[2] = input.local.food[0];
    rejects([&] { (void)input.choose(1); }, "duplicate food cue gives an extra vote");
    std::cout << "equal_food_seeds=4096 east=" << east << " west=" << 4096-east << '\n';
}
void runtime_bias() {
    for (std::uint64_t seed = 1; seed <= 64; ++seed) {
        WorldRuntime a({1, 2}, seed), b({1, 2}, seed); BehaviorConfig p; p.trails_enabled = false;
        for (auto* world : {&a, &b}) world->configure_surface({{}, 3, 3, 0.01}, {}, p);
        const auto ca = a.seed_colony({0.01, 0, 0.01}), cb = b.seed_colony({0.01, 0, 0.01});
        const auto aa = a.seed_ant(ca, {{0.01, 0, 0.01}}), ab = b.seed_ant(cb, {{0.01, 0, 0.01}});
        a.seed_food({0.02, 0, 0.01}, {10000, 0, 0, 0}); a.seed_food({0, 0, 0.01}, {10000, 0, 0, 0});
        b.seed_food({0, 0, 0.01}, {10000, 0, 0, 0}); b.seed_food({0.02, 0, 0.01}, {10000, 0, 0, 0});
        a.start_foraging(aa); b.start_foraging(ab); a.advance_to({0}); b.advance_to({0});
        require(a.pending_events().front().destination == b.pending_events().front().destination, "creation order selected food");
        a.advance_to({1100}); b.advance_to({1100});
        require(a.query_ant(aa)->position == b.query_ant(ab)->position, "renaming source changed actual travel");
        const auto facts = a.committed_events();
        const auto chosen = std::find_if(facts.begin(), facts.end(), [](const auto& e) { return e.kind == FactKind::ForagingDecision; });
        require(chosen != facts.end() && chosen->resource.value && a.query_food({{1, 2}, chosen->resource})->position == a.query_ant(aa)->position,
            "approach fact recorded the wrong local food cue");
        roundtrip(a); roundtrip(b);
    }
}
void response() {
    Inputs absent, weak, fresh, blind, subcutoff;
    weak.local.steps[1].trail_units = 0.04; fresh.local.steps[1].trail_units = 1;
    blind.local.steps[1].trail_units = 1; blind.params.trail_weight = 0;
    subcutoff.local.steps[1].trail_units = 0.0001;
    std::uint64_t no_signal = 0, low_signal = 0, high_signal = 0;
    constexpr std::uint64_t trials = 131072;
    for (std::uint64_t seed = 1; seed <= trials; ++seed) {
        const auto a = absent.choose(seed), b = weak.choose(seed), c = fresh.choose(seed);
        if (a.destination == Cell{3, 2}) ++no_signal;
        if (b.destination == Cell{3, 2}) ++low_signal;
        if (c.destination == Cell{3, 2}) ++high_signal;
        if (seed <= 4096) {
            require(blind.choose(seed).destination == a.destination, "zero response control changed physical choice");
            require(subcutoff.choose(seed).destination == a.destination, "sub-cutoff signal affected choice");
        }
    }
    const auto rate = [](std::uint64_t n) { return static_cast<double>(n)/static_cast<double>(trials); };
    require(low_signal > no_signal && high_signal > low_signal, "positive fractional response lost");
    require(std::abs(rate(no_signal)-10.0/60.0) < 0.004 && std::abs(rate(low_signal)-10.45/60.45) < 0.004 &&
        std::abs(rate(high_signal)-21.25/71.25) < 0.004, "weighted local draws disagree with unchanged coefficients");
    std::cout << "response_trials=" << trials << " absent=" << no_signal << " weak=" << low_signal << " fresh=" << high_signal << '\n';
    fresh.ant.memory_size = 2; fresh.ant.memory[0] = {2, 2}; fresh.ant.memory[1] = {1, 2};
    require(fresh.choose(1).mode == BehaviorMode::FollowMemory && fresh.choose(1).destination == Cell{1, 2}, "trail overrode valid private memory");
    fresh.ant.memory_size = 0; fresh.ant.path[0] = {2, 1}; fresh.ant.path[1] = {2, 2}; fresh.ant.path_size = 2;
    const auto home = choose_behavior(1, {7}, true, fresh.ant, fresh.local, fresh.params);
    require(home.mode == BehaviorMode::Return && home.destination == Cell{2, 1}, "trail overrode loaded homing");
}
void continuity() {
    fixture::Recruitment r(1, false, "present"); require(r.train(), "scout fixture failed to deliver");
    const auto initial = r.world.surface_snapshot().trail_units; std::set<Cell> cells;
    for (const auto& t : r.world.trails()) cells.insert(t.cell);
    require(cells.size()+1 == r.experienced_route.size(), "return signal differs from experienced path");
    for (std::size_t i = 0; i+1 < r.experienced_route.size(); ++i) require(cells.contains(r.experienced_route[i]), "gap in real return deposits");
    require(!cells.contains(r.experienced_route.back()), "source cell has an uncommitted deposit");
    require(!r.world.sense(r.novice).food_count, "naive worker already sees food");
    const auto before = r.world.checkpoint(); const auto local = r.world.sense(r.novice);
    bool visible = false; for (std::uint32_t i = 0; i < local.step_count; ++i) if (local.steps[i].trail_units > 0) visible = true;
    require(visible && r.world.checkpoint() == before, "scout signal not locally observable or observer mutated state");
    r.world.advance_to({r.retired_at.milliseconds+60000});
    require(std::abs(r.world.surface_snapshot().trail_units-initial/2) < 1e-10, "real return trace did not decay by time");
    r.world.advance_to({r.retired_at.milliseconds+600000}); require(r.world.trails().empty(), "expired recruitment trace persisted");
    roundtrip(r.world);
}
void activation() {
    fixture::Recruitment r(3, false, "present"); require(r.train(), "late activation fixture did not train");
    r.world.advance_to({r.retired_at.milliseconds+180000}); const auto before = r.world.checkpoint();
    RuntimeLimits limits; limits.committed_events = static_cast<std::size_t>(r.world.summary().committed_events);
    WorldRuntime limited({8, 9}, 7, {}, limits); limited.restore(before);
    rejects([&] { limited.start_foraging(r.novice); }, "late activation fact budget ignored");
    require(limited.checkpoint() == before, "failed late activation leaked its wake or private state");
    r.world.start_foraging(r.novice); const auto state = *r.world.query_forager(r.novice);
    require(state.memory_size == 0 && state.decisions == 0 && state.path_size == 1, "activation fabricated experience");
    for (const auto& e : r.world.pending_events()) if (e.actor == r.novice.id)
        require(e.key.time > r.world.summary().now, "late first wake reopened a closed timestamp");
    const auto started = r.world.checkpoint();
    rejects([&] { r.world.start_foraging(r.novice); }, "duplicate activation reset private memory");
    require(started == r.world.checkpoint(), "rejected activation mutated state"); roundtrip(r.world);
    auto old = started; old[12] = 3; old[13] = old[14] = old[15] = 0;
    std::uint64_t hash = UINT64_C(14695981039346656037);
    for (std::size_t i = 0; i < old.size()-8; ++i) hash = (hash ^ old[i])*UINT64_C(1099511628211);
    for (unsigned i = 0; i < 8; ++i) old[old.size()-8+i] = static_cast<std::uint8_t>(hash >> (8*i));
    rejects([&] { r.world.restore(old); }, "previous physics version accepted");
    require(started == r.world.checkpoint(), "version rejection changed world");
}
void social() {
    std::uint64_t discovered = 0;
    for (std::uint64_t seed = 1; seed <= 8; ++seed) {
        fixture::Recruitment present(seed, false, "present"), absent(seed, false, "absent"), blind(seed, false, "blind");
        require(present.train() && absent.train() && blind.train(), "matched social training fixture failed");
        require(present.retired_at == absent.retired_at && present.retired_at == blind.retired_at &&
            present.experienced_route == absent.experienced_route && present.experienced_route == blind.experienced_route,
            "training history differs across treatments");
        for (auto* r : {&present, &absent, &blind}) r->world.start_foraging(r->novice);
        const auto first = present.world.checkpoint(); WorldRuntime restored({8, 9}, 9); restored.restore(first);
        const auto end = present.retired_at.milliseconds+180000;
        for (auto t = present.retired_at.milliseconds; t < end; t += 1101) {
            for (auto* r : {&present, &absent, &blind}) r->world.advance_to({t});
            require(absent.world.query_ant(absent.novice) == blind.world.query_ant(blind.novice), "blind field changed physical novice trajectory");
        }
        for (auto* r : {&present, &absent, &blind}) { r->world.advance_to({end}); fixture::check_ingredients(r->world); roundtrip(r->world); }
        restored.advance_to({end}); require(restored.checkpoint() == present.world.checkpoint(), "late-start resumed/chunked trajectory differs");
        for (const auto& e : present.world.committed_events()) if (e.actor == present.novice.id && e.kind == FactKind::ForagingDecision && e.resource.value) {
            ++discovered; break;
        }
    }
    require(discovered > 0, "social fixture produced no real novice discoveries");
    // Establish an operational experiment, not a forced recruitment gain.
}
}
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: antworld_s2_1_tests CASE");
        const std::string_view name(argv[1]);
        if (name == "BIAS") bias(); else if (name == "RUNTIME_BIAS") runtime_bias(); else if (name == "RESPONSE") response();
        else if (name == "CONTINUITY") continuity(); else if (name == "ACTIVATION") activation(); else if (name == "SOCIAL") social();
        else throw std::invalid_argument("unknown S2.1 test");
        std::cout << "PASS " << name << '\n'; return 0;
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
