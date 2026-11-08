#include "antworld/core/world_runtime.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>

using namespace antworld;
namespace {
// All positions, speeds, masses, capacities and times here are ENGINEERING_FIXTURE.
constexpr WorldId id{1, 2};
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
template <typename Fn> void rejects(Fn fn, const char* message) {
    bool failed = false; try { fn(); } catch (const std::exception&) { failed = true; }
    require(failed, message);
}
ActionProposal collect(AntRef a, FoodRef f, std::int64_t at, std::uint64_t amount = 3000) {
    return {a, {at}, ActionKind::CollectFood, f, {}, amount};
}
ActionProposal move(AntRef a, PositionM to, std::int64_t at) {
    return {a, {at}, ActionKind::Move, {}, to, 0};
}
void conserved(const WorldRuntime& w) {
    const auto f = w.summary().food_ledger;
    const auto a = f.available.components(), c = f.carried.components(), i = f.introduced.components();
    for (std::size_t k = 0; k < 4; ++k) require(a[k] <= i[k] && c[k] == i[k]-a[k], "ingredient not conserved");
}
void roundtrip(const WorldRuntime& w) {
    WorldRuntime restored({3, 4}, 0); restored.restore(w.checkpoint());
    require(restored.checkpoint() == w.checkpoint(), "noncanonical round trip");
    require(restored.snapshot() == w.snapshot(), "snapshot round trip mismatch");
}
WorldEvent last(const WorldRuntime& w) { return w.committed_events().back(); }
struct Fixture {
    WorldRuntime w;
    ColonyRef c;
    AntRef a, b;
    FoodRef f;
    explicit Fixture(std::uint64_t seed = 1, RuntimeLimits limits = {}) : w(id, seed, {}, limits), c(w.seed_colony()),
        a(w.seed_ant(c, {})), b(w.seed_ant(c, {})), f(w.seed_food({}, {1000, 1000, 1000, 1000})) {}
};
void entities() {
    Fixture x;
    require(x.c.id.value < x.a.id.value && x.a.id.value < x.b.id.value && x.b.id.value < x.f.id.value, "global monotonic IDs");
    require(x.w.query_colony(x.c)->species == Species::LasiusNigerEngineeringFixture, "species provenance");
    require(x.w.summary().living_ants == 2 && x.w.summary().ant_count == 2 && x.w.summary().colony_count == 1 &&
        x.w.summary().food_source_count == 1, "entity counts");
    const auto before = x.w.checkpoint(); const auto snapshot = x.w.snapshot();
    const auto page = x.w.events_after({1}, 2);
    require(page.size() == 2 && page.front().id == EventId{2} && page.back().id == EventId{3}, "event cursor paging");
    require(x.w.events_after({UINT64_MAX}, 1).empty() && x.w.events_after({0}, 0).empty(), "event page overflow");
    for (int i = 0; i < 100; ++i) {
        auto detached = x.w.query_ant(x.a); detached->position.x = 99;
        auto food = x.w.query_food(x.f); food->remaining = {};
        (void)x.w.query_colony(x.c); (void)x.w.summary(); (void)x.w.pending_events();
        require(x.w.snapshot() == snapshot, "query changed state");
    }
    require(x.w.checkpoint() == before, "detached query mutation escaped");
    auto foreign = x.a; foreign.world = {3, 4};
    auto foreign_food = x.f; foreign_food.world = {3, 4};
    require(!x.w.query_ant(foreign) && !x.w.query_food(foreign_food), "foreign reference resolved");
    rejects([&] { x.w.submit(collect(foreign, x.f, 10)); }, "foreign actor accepted");
    rejects([&] { x.w.submit(collect(x.a, foreign_food, 10)); }, "foreign food accepted");
    rejects([&] { x.w.seed_ant({{9, 9}, x.c.id}, {}); }, "foreign colony accepted");
    require(x.w.checkpoint() == before, "foreign command allocated an ID");
    roundtrip(x.w);
    x.w.advance_to({1}); rejects([&] { x.w.seed_colony(); }, "late fixture seeding accepted");
}
void movement() {
    Fixture x;
    const auto original = *x.w.query_ant(x.a);
    x.w.submit(move(x.a, {0.005, 0, 0}, 1000));
    require(x.w.query_ant(x.a)->position == original.position, "proposal moved actor");
    x.w.advance_to({999}); require(x.w.query_ant(x.a)->position == original.position, "movement arrived early");
    x.w.advance_to({1000}); require(x.w.query_ant(x.a)->position == PositionM{0.005, 0, 0}, "valid movement failed");
    require(last(x.w).kind == FactKind::Moved, "missing movement fact");
    x.w.submit(move(x.a, {0.5, 0, 0}, 1001)); x.w.advance_to({1001});
    require(last(x.w).outcome == Outcome::TooFast && x.w.query_ant(x.a)->position.x == 0.005, "speed bound failed");
    x.w.submit(move(x.a, {2, 0, 0}, 1000000)); x.w.advance_to({1000000});
    require(last(x.w).outcome == Outcome::OutOfBounds, "bounds ignored");
    const auto saved = x.w.checkpoint();
    rejects([&] { x.w.submit(move(x.a, {std::numeric_limits<double>::quiet_NaN(), 0, 0}, 1000001)); }, "NaN accepted");
    require(saved == x.w.checkpoint(), "NaN mutated state");
    Fixture stale;
    stale.w.submit(move(stale.a, {0.001, 0, 0}, 1000)); stale.w.submit(move(stale.a, {0.002, 0, 0}, 2000));
    stale.w.advance_to({2000}); require(last(stale.w).outcome == Outcome::StalePosition, "stale move accepted");
    require(stale.w.query_ant(stale.a)->position.x == 0.001, "stale move teleported ant");
    rejects([&] { stale.w.submit(move(stale.a, {0.002, 0, 0}, 2000)); }, "closed movement boundary reopened");
}
void competition() {
    Fixture a(77), b(77), replay(77);
    const auto original = a.w.summary().food_ledger;
    a.w.submit(collect(a.a, a.f, 10)); a.w.submit(collect(a.b, a.f, 10));
    replay.w.submit(collect(replay.a, replay.f, 10)); replay.w.submit(collect(replay.b, replay.f, 10));
    b.w.submit(collect(b.b, b.f, 10)); b.w.submit(collect(b.a, b.f, 10));
    require(a.w.summary().food_ledger == original && a.w.committed_events().size() == 4, "proposal claimed success");
    a.w.advance_to({10}); b.w.advance_to({10}); replay.w.advance_to({10});
    require(a.w.checkpoint() == replay.w.checkpoint(), "fixed input not reproducible");
    const auto aa = *a.w.query_ant(a.a), ab = *a.w.query_ant(a.b);
    require(aa == *b.w.query_ant(b.a) && ab == *b.w.query_ant(b.b), "submission order biased allocation");
    auto amounts = std::array{aa.carried_food.total_ug(), ab.carried_food.total_ug()}; std::sort(amounts.begin(), amounts.end());
    require(amounts == std::array<std::uint64_t, 2>{1000, 3000}, "3000+3000 from 4000 violated");
    require(a.w.query_food(a.f)->remaining.total_ug() == 0, "food not depleted");
    const auto facts = a.w.committed_events();
    require(facts[4].kind == FactKind::FoodCollected && facts[5].outcome == Outcome::Partial, "missing partial transfer fact");
    conserved(a.w); roundtrip(a.w);
    a.w.submit(collect(a.a, a.f, 11)); a.w.advance_to({11});
    require(last(a.w).outcome == Outcome::Depleted, "empty resource transferred");
    conserved(a.w);
}
void failures() {
    WorldRuntime w(id, 1); const auto c = w.seed_colony();
    const auto a = w.seed_ant(c, {{}, LifeStage::Adult, Caste::Worker, 2});
    const auto far = w.seed_ant(c, {{0.1, 0, 0}});
    const auto brood = w.seed_ant(c, {{}, LifeStage::Egg});
    const auto queen = w.seed_ant(c, {{}, LifeStage::Adult, Caste::Queen});
    const auto f = w.seed_food({}, {10, 0, 0, 0});
    w.submit(collect(a, f, 1, 4)); w.advance_to({1});
    require(last(w).outcome == Outcome::Partial && w.query_ant(a)->carried_food.total_ug() == 2, "capacity overflow");
    w.submit(collect(a, f, 2, 1)); w.advance_to({2}); require(last(w).outcome == Outcome::Capacity, "full inventory accepted");
    w.submit(collect(far, f, 3, 1)); w.advance_to({3}); require(last(w).outcome == Outcome::OutOfReach, "remote collection accepted");
    w.submit(collect(brood, f, 4, 1)); w.advance_to({4}); require(last(w).outcome == Outcome::InvalidStage, "brood acted");
    w.submit(collect(queen, f, 5, 1)); w.advance_to({5}); require(last(w).outcome == Outcome::InvalidStage, "unsupported caste acted");
    conserved(w); roundtrip(w);
    Fixture x;
    x.w.submit(move(x.a, {0.001, 0, 0}, 1000)); x.w.submit(collect(x.a, x.f, 1000));
    x.w.advance_to({1000});
    require(x.w.query_ant(x.a)->carried_food.total_ug() == 0 && last(x.w).outcome == Outcome::DuplicateAction, "one actor executed twice");
    require(x.w.summary().food_ledger.available.total_ug() == 4000, "duplicate consumed food");
}
void fairness() {
    std::array<unsigned, 2> wins{};
    for (std::uint64_t seed = 0; seed < 256; ++seed) {
        Fixture x(seed); x.w.submit(collect(x.a, x.f, 100)); x.w.submit(collect(x.b, x.f, 100)); x.w.advance_to({100});
        ++wins[x.w.query_ant(x.a)->carried_food.total_ug() == 3000 ? 0u : 1u];
    }
    // Broad deterministic distribution guard, not a biological or statistical calibration.
    require(wins[0] > 70 && wins[1] > 70, "seed sweep permanently favored one ID");
    std::array<unsigned, 2> time_wins{};
    for (std::int64_t time = 1; time <= 256; ++time) {
        Fixture x(12345); x.w.submit(collect(x.b, x.f, time)); x.w.submit(collect(x.a, x.f, time)); x.w.advance_to({time});
        ++time_wins[x.w.query_ant(x.a)->carried_food.total_ug() == 3000 ? 0u : 1u];
    }
    require(time_wins[0] > 70 && time_wins[1] > 70, "time sweep permanently favored one ID");
    std::cout << "seed_wins=" << wins[0] << ',' << wins[1] << " time_wins=" << time_wins[0] << ',' << time_wins[1] << '\n';
}
void lifecycle() {
    WorldRuntime w(id, 1); const auto c = w.seed_colony(); const auto a = w.seed_ant(c, {{}, LifeStage::Egg});
    const auto f = w.seed_food({}, {10, 0, 0, 0}); const auto born = w.query_ant(a)->born_at;
    w.schedule_lifecycle(a, {1}, LifeStage::Adult); w.advance_to({1});
    require(last(w).outcome == Outcome::InvalidTransition, "stage skip accepted");
    w.schedule_lifecycle(a, {2}, LifeStage::Larva); w.schedule_lifecycle(a, {3}, LifeStage::Pupa);
    w.schedule_lifecycle(a, {4}, LifeStage::Adult); w.advance_to({4});
    require(w.query_ant(a)->id == a.id && w.query_ant(a)->born_at == born && w.summary().ant_count == 1, "identity changed during development");
    w.submit(collect(a, f, 5, 5)); w.advance_to({5});
    w.submit(collect(a, f, 6, 5)); w.schedule_lifecycle(a, {6}, LifeStage::Dead);
    w.schedule_lifecycle(a, {7}, LifeStage::Dead); w.schedule_lifecycle(a, {8}, LifeStage::Adult); w.advance_to({8});
    require(w.summary().living_ants == 0 && w.summary().ant_count == 1 && !w.query_ant(a)->alive(), "death identity/count failed");
    const auto facts = w.committed_events();
    require(std::count_if(facts.begin(), facts.end(), [](const auto& e) { return e.kind == FactKind::AntDied; }) == 1, "death emitted twice");
    require(w.query_ant(a)->carried_food.total_ug() == 5 && w.query_food(f)->remaining.total_ug() == 5, "dead ant acted or lost material");
    require(facts[facts.size()-3].outcome == Outcome::DeadActor && facts[facts.size()-2].outcome == Outcome::AlreadyDead, "death ordering/outcomes failed");
    conserved(w); roundtrip(w); require(w.allocate_entity_id().value > f.id.value, "dead ID reused");
}
void phases() {
    WorldRuntime w(id, 1);
    w.schedule({{10}, Phase::Publish, 3, 5}); w.advance_to({10});
    const auto saved = w.checkpoint();
    for (auto phase : {Phase::Input, Phase::Environment, Phase::Perception, Phase::Proposals, Phase::Resolution, Phase::Commit})
        rejects([&] { w.schedule({{10}, phase}); }, "cross-call earlier phase accepted");
    rejects([&] { w.schedule({{10}, Phase::Publish, 2, 9}); }, "earlier priority accepted");
    rejects([&] { w.schedule({{10}, Phase::Publish, 3, 4}); }, "earlier tie accepted");
    require(saved == w.checkpoint(), "invalid late scheduling mutated state");
    WorldRuntime restored({3, 4}, 0); restored.restore(saved);
    rejects([&] { restored.schedule({{10}, Phase::Environment}); }, "restored phase reopened");
    w.schedule({{10}, Phase::Publish, 3, 5}); w.advance_to({10});
    require(w.summary().events_at_current_time == 2, "same-time execution count reset");
    w.advance_to({11}); w.schedule({{11}, Phase::Input}); w.advance_to({11});
    require(w.summary().events_at_current_time == 1, "next timestamp did not reset cursor");
    Fixture x; x.w.submit(collect(x.a, x.f, 1)); x.w.advance_to({1});
    const auto closed = x.w.checkpoint();
    rejects([&] { x.w.submit(collect(x.b, x.f, 1)); }, "late same-time contender entered completed batch");
    rejects([&] { x.w.schedule_lifecycle(x.a, {1}, LifeStage::Dead); }, "late death rewrote earlier action");
    require(closed == x.w.checkpoint(), "late action changed closed boundary");
    x.w.schedule({{1}, Phase::Commit}); x.w.advance_to({1}); roundtrip(x.w);
    RuntimeLimits limits; limits.events_per_timestamp = 2; WorldRuntime bounded(id, 1, {}, limits);
    for (int i = 0; i < 2; ++i) { bounded.schedule({{0}}); bounded.advance_to({0}); }
    bounded.schedule({{0}}); const auto full = bounded.checkpoint();
    rejects([&] { bounded.advance_to({0}); }, "cross-call same-time budget bypassed");
    require(full == bounded.checkpoint(), "budget failure did not roll back");
    WorldRuntime loaded(id, 1, {}, limits); loaded.restore(full);
    rejects([&] { loaded.advance_to({0}); }, "restore reset same-time guard");
}
void rollback() {
    RuntimeLimits limits; limits.committed_events = 6; Fixture x(9, limits);
    x.w.schedule({{1}, Phase::Environment, 0, 0, 0, DiagnosticAction::DrawRandom});
    x.w.submit(collect(x.a, x.f, 2)); x.w.submit(collect(x.b, x.f, 2));
    const auto before = x.w.checkpoint();
    rejects([&] { x.w.advance_to({20}); }, "late journal failure did not occur");
    require(before == x.w.checkpoint(), "late failure leaked queue, RNG, rows, ledger or time");
    conserved(x.w);
    RuntimeLimits tiny; tiny.committed_events = 1; WorldRuntime create(id, 1, {}, tiny); const auto colony = create.seed_colony();
    const auto seed = create.checkpoint();
    rejects([&] { create.seed_ant(colony, {}); }, "seed journal budget ignored");
    rejects([&] { create.seed_food({}, {1, 0, 0, 0}); }, "food journal budget ignored");
    require(create.checkpoint() == seed, "failed creation left a row or ID");
    Fixture loop; loop.w.submit(collect(loop.a, loop.f, 1));
    loop.w.schedule({{2}, Phase::Environment, 0, 0, 0, DiagnosticAction::RepeatSameTime});
    const auto loop_start = loop.w.checkpoint();
    rejects([&] { loop.w.advance_to({2}); }, "runaway diagnostic did not fail");
    require(loop_start == loop.w.checkpoint(), "runaway rollback lost earlier successful transfer");
}
void put(std::vector<std::uint8_t>& bytes, std::size_t at, std::uint64_t v, unsigned width = 8) {
    for (unsigned i = 0; i < width; ++i) { bytes.at(at+i) = static_cast<std::uint8_t>(v & 255); v >>= 8; }
}
void checksum(std::vector<std::uint8_t>& bytes) {
    std::uint64_t h = 14695981039346656037ULL;
    for (std::size_t i = 0; i < bytes.size()-8; ++i) h = (h ^ bytes[i])*1099511628211ULL;
    put(bytes, bytes.size()-8, h);
}
void persistence() {
    Fixture x; x.w.submit(collect(x.a, x.f, 10)); x.w.submit(collect(x.b, x.f, 10));
    x.w.schedule_lifecycle(x.a, {20}, LifeStage::Dead); x.w.advance_to({5});
    WorldRuntime restored({9, 10}, 42); restored.restore(x.w.checkpoint());
    x.w.advance_to({30}); restored.advance_to({10}); restored.advance_to({20}); restored.advance_to({30});
    require(x.w.checkpoint() == restored.checkpoint(), "loaded/chunked action continuation differs"); roundtrip(x.w);
    const auto good = x.w.checkpoint();
    for (std::size_t i = 0; i < good.size(); ++i) {
        auto bad = good; bad[i] ^= 128;
        rejects([&] { restored.restore(bad); }, "corrupt checkpoint accepted");
    }
    auto bad = good; put(bad, bad.size()-16, 1); checksum(bad); // Last remaining ingredient disagrees with seed/history.
    rejects([&] { restored.restore(bad); }, "forged material ledger accepted");
    bad = good; put(bad, 8, 1, 4); checksum(bad);
    rejects([&] { restored.restore(bad); }, "S0 schema silently reinterpreted");
    auto pending = Fixture{}; pending.w.submit(collect(pending.a, pending.f, 10)); bad = pending.w.checkpoint();
    put(bad, 158, 999); checksum(bad); // Scheduled actor follows the diagnostic prefix and kind.
    rejects([&] { restored.restore(bad); }, "missing scheduled actor accepted");
    require(restored.checkpoint() == good, "invalid restoration replaced live state");
}
void arithmetic() {
    // Independent bounded-product reference for mixed ingredients and remainder ties.
    for (std::uint64_t seed = 1; seed <= 256; ++seed) {
        const std::array<std::uint64_t, 4> ingredients{
            seed*7919 % 1000003, seed*104729 % 1000003, seed*15485863 % 1000003, seed*32452843 % 1000003};
        const FoodMass stock{ingredients[0], ingredients[1], ingredients[2], ingredients[3]};
        const auto total = stock.total_ug(); const auto amount = seed*49999 % total + 1;
        std::array<std::uint64_t, 4> expected{}, remainder{}; std::array<std::size_t, 4> order{0, 1, 2, 3};
        std::uint64_t assigned = 0;
        for (std::size_t i = 0; i < 4; ++i) {
            expected[i] = ingredients[i]*amount/total; remainder[i] = ingredients[i]*amount%total; assigned += expected[i];
        }
        std::sort(order.begin(), order.end(), [&](auto a, auto b) {
            return remainder[a] != remainder[b] ? remainder[a] > remainder[b] : a < b;
        });
        for (std::uint64_t i = 0; i < amount-assigned; ++i) ++expected[order[static_cast<std::size_t>(i)]];
        WorldRuntime reference(id, seed); const auto colony = reference.seed_colony();
        const auto actor = reference.seed_ant(colony, {{}, LifeStage::Adult, Caste::Worker, total});
        const auto source = reference.seed_food({}, stock);
        reference.submit(collect(actor, source, 1, amount)); reference.advance_to({1});
        require(reference.query_ant(actor)->carried_food.components() == expected, "integer apportionment differs from independent reference");
        conserved(reference);
    }
    WorldRuntime w(id, 1); const auto c = w.seed_colony();
    const auto a = w.seed_ant(c, {{}, LifeStage::Adult, Caste::Worker, UINT64_MAX});
    const auto f = w.seed_food({}, {UINT64_MAX/2, UINT64_MAX-UINT64_MAX/2, 0, 0});
    w.submit(collect(a, f, 1, UINT64_MAX-1)); w.advance_to({1});
    require(w.query_ant(a)->carried_food.total_ug() == UINT64_MAX-1 && w.query_food(f)->remaining.total_ug() == 1, "wide integer division overflow");
    conserved(w); w.submit(collect(a, f, 2, 1)); w.advance_to({2}); conserved(w); roundtrip(w);
    WorldRuntime over(id, 1); over.seed_food({}, {UINT64_MAX, 0, 0, 0}); const auto saved = over.checkpoint();
    rejects([&] { over.seed_food({}, {0, 1, 0, 0}); }, "world mass overflow accepted");
    require(saved == over.checkpoint(), "overflow seed allocated entity");
    rejects([] { (void)FoodMass{UINT64_MAX, 1, 0, 0}.total_ug(); }, "component sum wrapped");
    WorldRuntime tiny(id, 1); const auto tc = tiny.seed_colony(); const auto ta = tiny.seed_ant(tc, {});
    const auto tf = tiny.seed_food({}, {1, 1, 1, 1}); tiny.submit(collect(ta, tf, 1, 3)); tiny.advance_to({1});
    require(tiny.query_ant(ta)->carried_food == FoodMass{1, 1, 1, 0}, "largest-remainder tie rule changed");
    conserved(tiny);
}
void budgets() {
    // Explicitly exceed BOTH old S0 defaults to prove these are configurable host policy.
    RuntimeLimits large; large.pending_events = 150000; large.checkpoint_bytes = 32*1024*1024;
    WorldRuntime w(id, 1, {}, large);
    ScheduledId middle;
    for (std::int64_t i = 1; i <= 150000; ++i) { const auto s = w.schedule({{i}}); if (i == 75000) middle = s; }
    const auto bytes = w.checkpoint(); require(bytes.size() > 16*1024*1024, "large save fixture too small");
    WorldRuntime small(id, 1); const auto before = small.checkpoint();
    rejects([&] { small.restore(bytes); }, "default host budget ignored"); require(before == small.checkpoint(), "budget restore changed state");
    WorldRuntime restored(id, 1, {}, large); restored.restore(bytes);
    require(restored.checkpoint() == bytes && restored.cancel(middle), "raised host policy did not round-trip/cancel");
    std::cout << "pending_records=150000 checkpoint_bytes=" << bytes.size() << '\n';
}
} // namespace
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("usage: antworld_s1_tests CASE");
        const std::string_view name = argv[1];
        if (name == "ENTITIES") entities();
        else if (name == "MOVEMENT") movement();
        else if (name == "COMPETITION") competition();
        else if (name == "FAILURES") failures();
        else if (name == "FAIRNESS") fairness();
        else if (name == "LIFECYCLE") lifecycle();
        else if (name == "PHASES") phases();
        else if (name == "ROLLBACK") rollback();
        else if (name == "PERSISTENCE") persistence();
        else if (name == "ARITHMETIC") arithmetic();
        else if (name == "BUDGETS") budgets();
        else throw std::runtime_error("unknown S1 case");
        std::cout << "PASS " << name << '\n'; return 0;
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
