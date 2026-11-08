#include "antworld/core/world_runtime.hpp"
#include "s2_fixture.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <iostream>
#include <map>
#include <limits>
#include <set>
#include <stdexcept>
#include <string_view>

using namespace antworld;
namespace {
// Every numeric value in these mechanism scenarios is ENGINEERING_FIXTURE.
constexpr WorldId id{0x53320001, 1};
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
template <typename F> void rejects(F action, const char* message) {
    bool failed = false; try { action(); } catch (const std::exception&) { failed = true; } require(failed, message);
}
void conserved(const WorldRuntime& w) {
    const auto l = w.summary().food_ledger;
    const auto initial = l.introduced.components(), remaining = l.available.components();
    const auto carried = l.carried.components(), stored = l.stored.components();
    for (std::size_t i = 0; i < 4; ++i) require(remaining[i] <= initial[i] && carried[i] <= initial[i]-remaining[i] &&
        stored[i] == initial[i]-remaining[i]-carried[i], "S2 ingredient conservation failed");
}
void roundtrip(const WorldRuntime& w, RuntimeLimits limits = {}) {
    WorldRuntime copy({3, 4}, 9, {}, limits); const auto bytes = w.checkpoint(); copy.restore(bytes);
    require(copy.checkpoint() == bytes && copy.surface_snapshot() == w.surface_snapshot(), "S2 checkpoint round trip differs");
}
struct Corridor {
    WorldRuntime w;
    SurfaceConfig grid;
    ColonyRef colony;
    std::vector<AntRef> ants = std::vector<AntRef>(0);
    FoodRef food;
    Corridor(std::uint32_t length = 7, std::size_t workers = 2, BehaviorConfig behavior = {},
        FoodMass stock = {100000, 100000, 100000, 100000}, RuntimeLimits limits = {}, bool activate = true)
        : w(id, 12345, {}, limits), grid{{0, 0, 0}, length, 1, 0.01} {
        w.configure_surface(grid, {}, behavior); colony = w.seed_colony({0, 0, 0});
        for (std::size_t i = 0; i < workers; ++i) ants.push_back(w.seed_ant(colony, {{0, 0, 0}, LifeStage::Adult, Caste::Worker, 1000}));
        food = w.seed_food(fixture::position(grid, {static_cast<std::int32_t>(length)-1, 0}), stock);
        if (activate) for (const auto a : ants) w.start_foraging(a);
    }
};
void surface() {
    WorldRuntime w(id, 1); SurfaceConfig grid{{0, 0, 0}, 5, 3, 0.01};
    const std::array blocked{Cell{1, 0}, Cell{1, 1}};
    w.configure_surface(grid, blocked); const auto colony = w.seed_colony(); const auto a = w.seed_ant(colony, {});
    w.submit({a, {1100}, ActionKind::Move, {}, {0.01, 0, 0}, 0}); w.advance_to({1100});
    require(w.committed_events().back().outcome == Outcome::Blocked, "walked into wall");
    w.submit({a, {10000}, ActionKind::Move, {}, {0.02, 0, 0}, 0}); w.advance_to({10000});
    require(w.committed_events().back().outcome == Outcome::NonLocalMove, "jumped through wall");
    w.submit({a, {11100}, ActionKind::Move, {}, {0, 0, 0.01}, 0}); w.advance_to({11100});
    require(w.query_ant(a)->position == PositionM{0, 0, 0.01}, "legal local step failed"); roundtrip(w);
    WorldRuntime bad(id, 1); const auto before = bad.checkpoint();
    auto invalid = grid; invalid.cell_size_m = 0;
    rejects([&] { bad.configure_surface(invalid, {}); }, "zero cell size accepted");
    BehaviorConfig speed; speed.step_duration = {1};
    rejects([&] { bad.configure_surface(grid, {}, speed); }, "too-fast behavior parameters accepted");
    require(before == bad.checkpoint(), "invalid configuration mutated world");
}
void locality() {
    BehaviorConfig params; params.trails_enabled = false; params.sensing_radius_cells = 2;
    SurfaceConfig grid{{0, 0, 0}, 15, 3, 0.01}; std::array<Cell, 3> wall{{{1, 0}, {1, 1}, {1, 2}}};
    WorldRuntime blocked(id, 1); blocked.configure_surface(grid, wall, params);
    const auto colony = blocked.seed_colony(); const auto ant = blocked.seed_ant(colony, {});
    blocked.seed_food({0.02, 0, 0}, {1000, 0, 0, 0});
    require(blocked.sense(ant).food_count == 0, "food perceived through disconnected wall");
    WorldRuntime left(id, 17), right(id, 17);
    left.configure_surface(grid, {}, params); right.configure_surface(grid, {}, params);
    const auto lc = left.seed_colony(), rc = right.seed_colony(); const auto la = left.seed_ant(lc, {}), ra = right.seed_ant(rc, {});
    left.seed_food({0.13, 0, 0}, {1000, 0, 0, 0}); right.seed_food({0.14, 0, 0.02}, {1000, 0, 0, 0});
    left.start_foraging(la); right.start_foraging(ra);
    for (std::int64_t t = 0; t <= 5000; t += 500) {
        require(left.sense(la) == right.sense(ra), "hidden food changed local observation");
        left.advance_to({t}); right.advance_to({t});
        require(left.query_ant(la) == right.query_ant(ra) && left.query_forager(la) == right.query_forager(ra), "hidden food changed individual choice");
        require(left.surface_snapshot().discovered_sources == 0 && right.surface_snapshot().discovered_sources == 0, "fabricated remote discovery");
    }
    const auto before = left.checkpoint();
    for (int i = 0; i < 100; ++i) { (void)left.sense(la); (void)left.trails(); (void)left.visits(); (void)left.surface_snapshot(); }
    require(before == left.checkpoint(), "observer consumed RNG/time or materialized decay");
    rejects([&] { (void)left.sense({{9, 9}, la.id}); }, "foreign observer reference accepted");
    require(left.sense(la).sampled_cells <= 13, "radius-two perception exceeded local budget");
}
void loop() {
    Corridor c; c.w.advance_to({60000}); const auto stats = c.w.surface_snapshot();
    require(stats.discovered_sources == 1 && stats.first_discovery.milliseconds > 0 && stats.first_discoverer.value,
        "missing encountered food discovery");
    require(stats.counters.collections > 0 && stats.counters.deliveries > 0 && c.w.query_colony(c.colony)->nest_food.total_ug() > 0,
        "autonomous collection/physical return/delivery loop failed");
    require(stats.counters.failed_actions == 0 && stats.counters.trips_started >= stats.counters.deliveries, "invalid foraging outcomes");
    std::map<EntityId, bool> discovered;
    for (const auto& e : c.w.committed_events()) {
        if (e.kind == FactKind::ForagingDecision && e.resource.value) discovered[e.actor] = true;
        if (e.kind == FactKind::FoodCollected) require(discovered[e.actor], "collected without local discovery");
        if (e.kind == FactKind::FoodDelivered) require(e.position == PositionM{} && e.transferred.total_ug(), "delivery without physical nest contact");
    }
    conserved(c.w); roundtrip(c.w);
}
void order() {
    fixture::Scene forward(92, true, true, "open", 8), reverse(92, true, true, "open", 8, true);
    for (std::int64_t t = 0; t <= 180000; t += 3000) {
        forward.world.advance_to({t}); reverse.world.advance_to({t});
        for (std::size_t i = 0; i < forward.workers.size(); ++i) {
            require(forward.world.query_ant(forward.workers[i]) == reverse.world.query_ant(reverse.workers[i]), "activation order biased behavior");
            require(forward.world.query_forager(forward.workers[i]) == reverse.world.query_forager(reverse.workers[i]), "activation order biased private memory/RNG");
        }
        require(forward.world.surface_snapshot() == reverse.world.surface_snapshot() && forward.world.trails() == reverse.world.trails(),
            "iteration order changed collective outcome");
    }
    const auto before = forward.world.checkpoint();
    rejects([&] { forward.world.submit({forward.workers[0], {181000}, ActionKind::Rest, {}, {}, 0}); }, "external action overrode individual model");
    require(before == forward.world.checkpoint(), "rejected external action mutated state");
}
void memory() {
    BehaviorConfig off; off.memory_enabled = false; Corridor learned(7, 1), disabled(7, 1, off);
    learned.w.advance_to({45000}); disabled.w.advance_to({45000});
    require(learned.w.surface_snapshot().counters.memory_moves > 0, "learned route never used");
    require(disabled.w.query_forager(disabled.ants[0])->memory_size == 0 && disabled.w.surface_snapshot().counters.memory_moves == 0,
        "memory-off treatment retained learned route");
    auto expired = off; expired.memory_enabled = true; expired.memory_lifetime = {0}; Corridor forget(7, 1, expired);
    forget.w.advance_to({45000}); require(forget.w.surface_snapshot().counters.memory_failures > 0 &&
        forget.w.surface_snapshot().counters.memory_moves == 0, "expired route used");
    Corridor empty(7, 1, {}, {1000, 0, 0, 0}); empty.w.advance_to({60000});
    require(empty.w.surface_snapshot().counters.memory_failures > 0 && empty.w.surface_snapshot().counters.collections == 1,
        "depleted learned endpoint was treated as known food");
    const auto f = learned.w.query_forager(learned.ants[0]);
    require(f->path_size <= 48 && f->memory_size <= 48, "bounded memory exceeded");
    roundtrip(learned.w); roundtrip(disabled.w); roundtrip(forget.w); roundtrip(empty.w);
}
void trails() {
    BehaviorConfig p; p.trail_cap_units = 1; p.deposit_units = 1; p.trail_half_life_s = 10;
    Corridor active(7, 2, p); auto off = p; off.trails_enabled = false; Corridor disabled(7, 2, off);
    active.w.advance_to({30000}); disabled.w.advance_to({30000});
    require(active.w.surface_snapshot().counters.deposited_units > 0 && active.w.surface_snapshot().active_trail_cells > 0,
        "loaded return failed to deposit trail");
    for (const auto& sample : active.w.trails()) require(sample.units > 0 && sample.units <= 1, "trail saturation failed");
    require(disabled.w.trails().empty() && disabled.w.surface_snapshot().counters.deposited_units == 0 &&
        disabled.w.surface_snapshot().counters.trail_moves == 0, "disabled trail treatment leaked signal");
    for (const auto a : active.ants) active.w.schedule_lifecycle(a, {30001}, LifeStage::Dead);
    active.w.advance_to({30001}); const auto initial = active.w.surface_snapshot().trail_units;
    active.w.advance_to({40001}); const auto half = active.w.surface_snapshot().trail_units;
    require(half > 0 && std::abs(half-initial/2) < 1e-10, "time-based half-life failed");
    active.w.advance_to({600000}); require(active.w.trails().empty(), "sparse dead trail never pruned");
    conserved(active.w); roundtrip(active.w); roundtrip(disabled.w);
}
void replay() {
    fixture::Scene one(19, true, true, "barrier", 6), split(19, true, true, "barrier", 6);
    one.world.advance_to({180000});
    for (std::int64_t t = 0; t < 180000; t += 467) {
        split.world.advance_to({t});
        if (t == 467*100) { const auto bytes = split.world.checkpoint(); split.world.restore(bytes); }
    }
    split.world.advance_to({180000});
    require(one.world.checkpoint() == split.world.checkpoint(), "chunked/resumed autonomous trajectory changed");
    WorldRuntime restored({5, 6}, 3); restored.restore(one.world.checkpoint());
    one.world.advance_to({240000}); restored.advance_to({240000});
    require(one.world.checkpoint() == restored.checkpoint(), "surface continuation missing state");
    roundtrip(one.world); conserved(one.world);
}
void rollback() {
    Corridor reference; reference.w.advance_to({60000});
    auto facts = reference.w.committed_events();
    const auto delivery = std::find_if(facts.begin(), facts.end(), [](const auto& e) { return e.kind == FactKind::FoodDelivered; });
    require(delivery != facts.end(), "delivery rollback fixture failed");
    Corridor before; before.w.advance_to({delivery->time.milliseconds-1});
    RuntimeLimits limits; limits.committed_events = static_cast<std::size_t>(before.w.summary().committed_events);
    WorldRuntime bounded(id, 1, {}, limits); bounded.restore(before.w.checkpoint()); const auto save = bounded.checkpoint();
    rejects([&] { bounded.advance_to(delivery->time); }, "late delivery fact failure missing");
    require(bounded.checkpoint() == save, "failed delivery leaked inventory, schedule, map or counters");
    limits = {}; limits.trail_cells = 0; Corridor no_trail_space(7, 1, {}, {10000, 0, 0, 0}, limits);
    const auto seed = no_trail_space.w.checkpoint();
    rejects([&] { no_trail_space.w.advance_to({30000}); }, "trail budget ignored");
    require(seed == no_trail_space.w.checkpoint(), "failed return deposit lost earlier discovery/collection");
}
void scheduling() {
    Corridor c; c.w.advance_to({0}); const auto before = c.w.checkpoint();
    const auto state = c.w.query_forager(c.ants[0]);
    rejects([&] { c.w.cancel(state->action); }, "external cancellation orphaned behavior");
    rejects([&] { c.w.start_foraging(c.ants[0]); }, "duplicate/late activation accepted");
    require(before == c.w.checkpoint(), "invalid managed event operation changed state");
    c.w.schedule_lifecycle(c.ants[0], {1100}, LifeStage::Dead); c.w.advance_to({20000});
    require(!c.w.query_forager(c.ants[0])->enabled, "dead forager stayed active");
    for (const auto& e : c.w.pending_events()) require(e.actor != c.ants[0].id, "dead forager retained pending actions");
    for (const auto& e : c.w.committed_events()) if (e.actor == c.ants[0].id && e.time >= SimTime{1100})
        require(e.kind == FactKind::AntDied, "dead worker acted at or after death");
    roundtrip(c.w);
}
void multiseed() {
    std::uint64_t total_delivered = 0, trail_moves = 0, memory_moves = 0;
    std::set<std::array<std::uint64_t, 4>> signatures;
    for (std::uint64_t seed = 1; seed <= 8; ++seed) {
        fixture::Scene a(seed, true, true, "open", 6), b(seed, false, false, "open", 6);
        a.world.advance_to({900000}); b.world.advance_to({900000});
        conserved(a.world); conserved(b.world); roundtrip(a.world); roundtrip(b.world);
        const auto s = a.world.surface_snapshot();
        signatures.insert({s.visited_cells, s.counters.deliveries, s.counters.trail_moves, s.counters.memory_moves});
        total_delivered += s.counters.deliveries; trail_moves += s.counters.trail_moves; memory_moves += s.counters.memory_moves;
        require(b.world.trails().empty() && b.world.surface_snapshot().counters.memory_moves == 0, "ablation feature leaked");
    }
    std::cout << "seeds=8 deliveries=" << total_delivered << " trail_moves=" << trail_moves << " memory_moves=" << memory_moves << '\n';
    require(signatures.size() == 8 && total_delivered > 0 && trail_moves > 0 && memory_moves > 0, "multi-seed behavioral mechanisms inactive");
}
void model() {
    BehaviorConfig p; ForagerState f; f.enabled = true; f.path_size = 1; f.path[0] = {2, 2};
    LocalObservation local; local.current = {2, 2}; local.step_count = 2;
    local.steps[0] = {{2, 3}, Direction::North, 0}; local.steps[1] = {{3, 2}, Direction::East, 0};
    const auto first = choose_behavior(17, {2}, false, f, local, p);
    for (int i = 0; i < 50; ++i) require(choose_behavior(17, {2}, false, f, local, p) == first, "pure model consumed hidden RNG");
    bool different = false;
    for (std::uint64_t decision = 0; decision < 32; ++decision) {
        f.decisions = decision;
        if (choose_behavior(2, {3}, false, f, local, p) != choose_behavior(3, {2}, false, f, local, p)) different = true;
    }
    require(different, "seed and actor merely permuted random streams");
    auto invalid = p; invalid.explore_weight = 0;
    rejects([&] { (void)choose_behavior(17, {2}, false, f, local, invalid); }, "zero random weight accepted");
    invalid = p; invalid.trail_cap_units = 0;
    rejects([&] { (void)choose_behavior(17, {2}, false, f, local, invalid); }, "invalid trail divisor accepted");
    auto cue = local; cue.steps[0].trail_units = std::numeric_limits<double>::quiet_NaN();
    rejects([&] { (void)choose_behavior(17, {2}, false, f, cue, p); }, "nonfinite trail cue accepted");
    cue = local; cue.steps[1] = cue.steps[0];
    rejects([&] { (void)choose_behavior(17, {2}, false, f, cue, p); }, "duplicate legal step accepted");
    // A finite return trace makes a dead end reversible without a global nest route.
    p.route_capacity = 2; p.max_trip_moves = 2; p.trails_enabled = false;
    Corridor bounded(7, 1, p); bounded.w.advance_to({60000});
    require(bounded.w.surface_snapshot().counters.return_moves > 0 && bounded.w.surface_snapshot().discovered_sources == 0,
        "bounded excursion used remote food or failed to return"); roundtrip(bounded.w);
    WorldRuntime trapped(id, 7); trapped.configure_surface({{}, 1, 1, 0.01}, {}, p);
    const auto colony = trapped.seed_colony(); const auto ant = trapped.seed_ant(colony, {}); trapped.start_foraging(ant);
    trapped.advance_to({5000}); require(trapped.surface_snapshot().counters.moves == 0 && trapped.query_forager(ant)->decisions > 1,
        "isolated ant failed to wait locally"); roundtrip(trapped);
}
void colonies() {
    Corridor c(7, 1, {}, {100000, 0, 0, 0}, {}, false);
    const auto second = c.w.seed_colony(); const auto observer = c.w.seed_ant(second, {});
    c.w.start_foraging(c.ants[0]); c.w.advance_to({30000});
    require(!c.w.trails().empty(), "colony isolation fixture has no trail");
    const auto observed = c.w.sense(observer);
    for (std::uint32_t i = 0; i < observed.step_count; ++i) require(observed.steps[i].trail_units == 0, "foreign colony trail leaked into perception");
    require(c.w.query_colony(second)->nest_food.total_ug() == 0 && c.w.query_colony(c.colony)->nest_food.total_ug() > 0,
        "delivery entered the wrong colony");
    roundtrip(c.w); conserved(c.w);
}
std::uint64_t read_u64(const std::vector<std::uint8_t>& bytes, std::size_t offset) {
    std::uint64_t n = 0; for (unsigned i = 0; i < 8; ++i) n |= std::uint64_t{bytes.at(offset+i)} << (i*8); return n;
}
void put(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint64_t n, unsigned width = 8) {
    for (unsigned i = 0; i < width; ++i) { bytes.at(offset+i) = static_cast<std::uint8_t>(n & 255); n >>= 8; }
}
void resign(std::vector<std::uint8_t>& bytes) {
    std::uint64_t hash = UINT64_C(14695981039346656037);
    for (std::size_t i = 0; i < bytes.size()-8; ++i) hash = (hash ^ bytes[i])*UINT64_C(1099511628211);
    put(bytes, bytes.size()-8, hash);
}
void corruption() {
    Corridor c; c.w.advance_to({30000}); const auto before = c.w.checkpoint();
    // Schema 3 structural offsets: deliberately repair the checksum so semantic
    // validation, rather than the transport checksum, must reject each forgery.
    std::size_t cursor = 108+static_cast<std::size_t>(read_u64(before, 100))*115;
    const auto facts = static_cast<std::size_t>(read_u64(before, cursor)); const auto first_fact = cursor+8;
    cursor += 8+facts*159+64;
    const auto watermark = before.at(cursor++); if (watermark) cursor += 32;
    cursor += 16+128;
    for (const std::size_t record : {73u, 98u, 96u}) { const auto n = read_u64(before, cursor); cursor += 8+static_cast<std::size_t>(n)*record; }
    require(before.at(cursor) == 1, "schema fixture surface offset failed"); const auto surface_start = cursor++;
    cursor += 130; const auto cells = read_u64(before, cursor); cursor += 8+static_cast<std::size_t>(cells);
    const auto counters = cursor; cursor += 128;
    const auto foragers = read_u64(before, cursor); const auto first_forager = cursor+8;
    cursor += 8+static_cast<std::size_t>(foragers)*1099;
    require(read_u64(before, cursor) > 0, "corruption fixture lacks trail"); const auto first_trail = cursor+8;
    auto reject_edit = [&](std::size_t at, std::uint64_t value, unsigned width = 8) {
        auto bad = before; put(bad, at, value, width); resign(bad);
        rejects([&] { c.w.restore(bad); }, "forged S2 checkpoint accepted");
        require(c.w.checkpoint() == before, "failed S2 restore changed live state");
    };
    reject_edit(surface_start+1+40, 0, 1); // Disable trails while retaining field evidence.
    reject_edit(counters, read_u64(before, counters)+1); // Fabricated observer aggregate.
    reject_edit(counters+120, 0); // Orphan field maintenance.
    reject_edit(first_forager+35, 65, 4); // Unbounded private return route.
    reject_edit(first_forager+43, 99, 4); // Invented nest landmark.
    reject_edit(first_forager+1083, UINT64_MAX); // Foreign wake ownership.
    reject_edit(first_trail+16, std::bit_cast<std::uint64_t>(0.75)); // Plausible quantity, unsupported by deposits.
    const auto events = c.w.committed_events();
    for (std::size_t i = 0; i < events.size(); ++i) if (events[i].deposited_units > 0) {
        reject_edit(first_fact+i*159+150, std::bit_cast<std::uint64_t>(0.25)); break;
    }
    RuntimeLimits small; small.surface_cells = 6; WorldRuntime limited(id, 0, {}, small);
    const auto empty = limited.checkpoint(); rejects([&] { limited.restore(before); }, "surface restore ignored host budget");
    require(limited.checkpoint() == empty, "host budget failure mutated world");
}
} // namespace
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: antworld_s2_tests CASE"); const std::string_view name = argv[1];
        if (name == "SURFACE") surface(); else if (name == "LOCALITY") locality(); else if (name == "LOOP") loop();
        else if (name == "ORDER") order(); else if (name == "MEMORY") memory(); else if (name == "TRAILS") trails();
        else if (name == "REPLAY") replay(); else if (name == "ROLLBACK") rollback(); else if (name == "SCHEDULING") scheduling();
        else if (name == "MULTISEED") multiseed(); else if (name == "MODEL") model(); else if (name == "COLONIES") colonies();
        else if (name == "CORRUPTION") corruption(); else throw std::invalid_argument("unknown S2 case");
        std::cout << "PASS " << name << '\n'; return 0;
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
