#include "antworld/storage/store.hpp"
#include "geometry_internal.hpp"
#include "s3_fixture.hpp"
#include "s4_fixture.hpp"
#include "s5_fixture.hpp"
#include "sqlite3.h"
#include <array>
#include <cstdlib>
#include <iostream>
#include <map>
#include <string>

using namespace antworld;
using namespace antworld::storage;
namespace {
void require(bool ok, const char *message) {
    if (!ok)
        throw std::runtime_error(message);
}
template <class F> void rejects(F fn) {
    bool caught = false;
    try {
        fn();
    } catch (const std::exception &) {
        caught = true;
    }
    require(caught, "operation should reject");
}
void clean(const std::filesystem::path &p) {
    for (const auto &suffix : {std::string{}, std::string{"-wal"}, std::string{"-shm"}}) {
        auto f = p;
        f += suffix;
        if (std::filesystem::is_regular_file(f))
            std::filesystem::remove(f);
    }
}
void sql(const std::filesystem::path &path, const char *command) {
    sqlite3 *db{};
    const auto p = path.u8string();
    require(sqlite3_open(reinterpret_cast<const char *>(p.c_str()), &db) == SQLITE_OK,
            "test database open failed");
    const auto result = sqlite3_exec(db, command, nullptr, nullptr, nullptr);
    const std::string error = sqlite3_errmsg(db);
    sqlite3_close(db);
    if (result != SQLITE_OK)
        throw std::runtime_error(error);
}
WorldRuntime world(std::uint64_t seed = 1) {
    WorldRuntime w({5, 1}, seed);
    const auto c = w.seed_colony();
    w.seed_ant(c, {});
    w.schedule({{1000}, Phase::Environment, 0, 0, 42, DiagnosticAction::DrawRandom});
    return w;
}
void atomic(const std::filesystem::path &path) {
    clean(path);
    Store store(path);
    auto w = world();
    const auto first = store.save(w);
    require(store.save(w, first) == first, "retry created a second generation");
    auto loaded = store.load(w.summary().world);
    require(loaded.world.checkpoint() == w.checkpoint(), "durable round trip differs");
    w.advance_to({1000});
    const auto next = w.checkpoint();
    for (auto stage : {SaveStage::BeforeTransaction, SaveStage::AfterCheckpoint, SaveStage::AfterHistory,
                       SaveStage::BeforeCommit}) {
        SaveOptions options;
        options.fault_hook = [&](SaveStage at) {
            if (at == stage)
                throw std::runtime_error("injected save failure");
        };
        rejects([&] { store.save(w, first, options); });
        require(w.checkpoint() == next, "save mutated simulation");
        require(store.latest(first.world) == first &&
                    store.load(first.world).world.checkpoint() == loaded.world.checkpoint(),
                "partial save survived");
    }
    const auto second = store.save(w, first);
    require(second.generation == 2, "generation skipped after rollback");
    loaded.world.advance_to({1000});
    require(store.load(first.world).world.checkpoint() == loaded.world.checkpoint(),
            "restored random/queue continuation differs");
}
void commands(const std::filesystem::path &path) {
    clean(path);
    auto w = world();
    Store store(path);
    auto saved = store.save(w);
    const PlaceFoodCommand command{w.summary().world, {UINT64_MAX, UINT64_MAX}, {}, {50, 20, 10, 0}};
    const auto original = w.checkpoint();
    SaveOptions fail;
    fail.fault_hook = [](SaveStage stage) {
        if (stage == SaveStage::BeforeCommit)
            throw std::runtime_error("failure");
    };
    rejects([&] { store.place_food(w, saved, command, fail); });
    require(w.checkpoint() == original, "failed durable command exposed candidate");
    const auto receipt = store.place_food(w, saved, command);
    const auto bytes = w.checkpoint();
    require(store.place_food(w, saved, command) == receipt && w.checkpoint() == bytes,
            "command retry duplicated food");
    auto changed = command;
    changed.mass.carbs_ug = 51;
    rejects([&] { store.place_food(w, saved, changed); });
    auto recovered = store.load(command.world);
    require(recovered.world.place_food(command) == receipt, "restored receipt missing");
    require(recovered.world.summary().food_ledger.introduced == command.mass,
            "command food counted more than once");
    w.advance_to({1000});
    changed.id = {1, 2};
    rejects([&] { w.place_food(changed); });
    w.advance_to({1001});
    const auto second = w.place_food(changed);
    require(second.event != receipt.event, "new command reused evidence");
    WorldRuntime copy({5, 2}, 0);
    copy.restore(w.checkpoint());
    require(copy.checkpoint() == w.checkpoint(), "new command codec fails");
    auto bad = w.checkpoint();
    bad[bad.size() - 16] ^= 1;
    s4_fixture::repair_checksum(bad);
    rejects([&] { copy.restore(bad); });
    WorldRuntime surface({5, 3}, 3);
    surface.configure_surface({{}, 5, 5, .001}, {}, {});
    const auto c = surface.seed_colony();
    surface.seed_ant(c, {});
    surface.advance_to({1});
    surface.place_food({{5, 3}, {1, 1}, {.001, 0, 0}, {2, 0, 0, 0}});
    copy.restore(surface.checkpoint());
}
void isolation(const std::filesystem::path &path) {
    clean(path);
    Store first(path), second(path);
    auto w = world();
    const auto initial = first.save(w);
    auto stale = second.load(initial.world);
    w.advance_to({1000});
    const auto current = first.save(w, initial);
    stale.world.advance_to({2000});
    rejects([&] { second.save(stale.world, stale.token); });
    require(first.latest(initial.world) == current, "stale writer changed latest");
    WorldRuntime other({5, 2}, 1);
    const auto c = other.seed_colony();
    const auto a = other.seed_ant(c, {});
    first.save(other);
    require(first.individual(a)->ant.world == other.summary().world, "individual world lost");
    require(first.load({5, 2}).world.checkpoint() == other.checkpoint(), "cross-world restore confusion");
    rejects([&] { first.load({5, 99}); });
    auto altered = world(99);
    rejects([&] { first.save(altered, current); });
    for (std::int64_t t = 2000; t <= 4000; t += 1000) {
        w.advance_to({t});
        first.save(w, first.latest(initial.world));
    }
    rejects([&] { first.load(initial.world, 1); });
    require(first.history({initial.world}).size() == 3, "checkpoint pruning removed history");
}
void metrics(const std::filesystem::path &path) {
    clean(path);
    Store store(path);
    WorldRuntime w({5, 1}, 3);
    const auto c = w.seed_colony();
    const auto a = w.seed_ant(c, {}), b = w.seed_ant(c, {{}, LifeStage::Pupa, Caste::Worker, 4000});
    const auto food = w.seed_food({}, {100, 50, 25, 0});
    w.enable_physiology(a);
    PhysiologyConfig config;
    config.pupa_duration = {100};
    w.enable_physiology(b, {}, config);
    auto token = store.save(w);
    w.submit({a, {100}, ActionKind::CollectFood, food, {}, 175});
    w.advance_to({100});
    token = store.save(w, token);
    require(store.flow_total(token.world, c.id, Metric::CollectedCarbs, {100}, {101}) == 100,
            "collection flow wrong");
    require(store.flow_total(token.world, c.id, Metric::CollectedCarbs, {0}, {100}) == 0,
            "half-open flow boundary wrong");
    require(store.flow_total(token.world, {}, Metric::Emerged, {0}, {101}) == 1, "emergence fact missing");
    w.submit_nutrition({a, {200}, NutritionAction::IngestCargo, {}, 175});
    w.advance_to({200});
    token = store.save(w, token);
    w.submit_nutrition({a, {300}, NutritionAction::Trophallaxis, b, 100});
    w.advance_to({300});
    token = store.save(w, token);
    require(store.flow_total(token.world, {}, Metric::Trophallaxis, {0}, {301}) == 100,
            "internal transfer wrong");
    require(store.flow_total(token.world, {}, Metric::CollectedCarbs, {0}, {301}) == 100,
            "internal transfer inflated intake");
    w.schedule_lifecycle(b, {400}, LifeStage::Dead);
    w.advance_to({400});
    token = store.save(w, token);
    w.schedule_lifecycle(b, {500}, LifeStage::Dead);
    w.advance_to({500});
    token = store.save(w, token);
    require(store.flow_total(token.world, {}, Metric::Deaths, {0}, {501}) == 1, "death duplicated");
    const auto person = store.individual(b);
    require(person && person->seeded && person->seeded_stage == LifeStage::Pupa &&
                person->current_stage == LifeStage::Dead && person->died_at == SimTime{400},
            "life record fabricated/replaced");
    const auto points = store.series(token.world, c.id, Metric::WorkerAlive, {0}, {501});
    require(points.back().value == 1, "population gauge differs");
    require(store.load(token.world).world.checkpoint() == w.checkpoint(), "metrics fail reconciliation");
    const auto before = w.checkpoint();
    for (int i = 0; i < 10; ++i) {
        (void)observe(w);
        (void)store.history({token.world});
    }
    require(before == w.checkpoint(), "analytics changes simulation");
}
void windows(const std::filesystem::path &path) {
    clean(path);
    Store store(path);
    auto w = world();
    auto token = store.save(w);
    for (auto t : {59999, 60000, 120000, 300000}) {
        w.advance_to({t});
        token = store.save(w, token);
    }
    const auto b = store.buckets(token.world, {}, Metric::Alive, {0}, {360000});
    require(b.size() == 4 && b[0].samples == 2 && b[0].sum == 2 && b[0].mean() == 1 &&
                b.back().begin == SimTime{300000},
            "sample bucket semantics wrong");
    require(store.series(token.world, {}, Metric::Alive, {180000}, {240000}).empty(),
            "missing observations turned into zeros");
    const auto p = store.series(token.world, {}, Metric::Alive, {0}, {400000}, 0, 2);
    const auto next = store.series(token.world, {}, Metric::Alive, {0}, {400000}, p.back().generation, 2);
    require(next.front().generation > p.back().generation, "series pagination overlaps");
    require(store.load(token.world).world.checkpoint() == w.checkpoint(), "bucket validation fails");
    require(store.coverage(token.world)->observed_through == SimTime{300000}, "history coverage missing");
    rejects([&] { store.flow_total(token.world, {}, Metric::Deaths, {0}, {400000}); });
    rejects([&] { store.flow_total({9, 9}, {}, Metric::Deaths, {0}, {1}); });
}
void corrupt(const std::filesystem::path &base) {
    const std::array commands{"UPDATE generations SET checkpoint=zeroblob(length(checkpoint))",
                              "DELETE FROM events WHERE id=(SELECT max(id) FROM events)",
                              "UPDATE events SET actor='0000000000000001' WHERE kind=0",
                              "UPDATE samples SET value='0000000000000009' WHERE metric=0",
                              "UPDATE buckets SET total='0000000000000009' WHERE metric=0",
                              "UPDATE individuals SET death_event='0000000000000001'",
                              "DELETE FROM generations",
                              "DELETE FROM flows WHERE metric=42"};
    for (std::size_t i = 0; i < commands.size(); ++i) {
        auto path = base;
        path += std::to_string(i);
        clean(path);
        Store store(path);
        auto w = world();
        w.advance_to({1000});
        store.save(w);
        sql(path, commands[i]);
        rejects([&] { store.load({5, 1}); });
    }
    auto path = base;
    path += "version";
    clean(path);
    {
        Store store(path);
    }
    sql(path, "PRAGMA user_version=99");
    rejects([&] { Store store(path); });
}
void exact(const std::filesystem::path &path) {
    clean(path);
    Store store(path);
    WorldRuntime w({UINT64_MAX, UINT64_MAX}, UINT64_MAX);
    w.seed_food({}, {UINT64_MAX, 0, 0, 0});
    const auto token = store.save(w);
    require(store.series(token.world, {}, Metric::AvailableCarbs, {0}, {1})[0].value == UINT64_MAX,
            "SQLite narrowed uint64 mass");
    require(store.load(token.world).world.checkpoint() == w.checkpoint(), "max uint64 continuation changed");
    RuntimeLimits small;
    small.checkpoint_bytes = 128;
    Store limited(path, small);
    rejects([&] { limited.load(token.world); });
}
void geometry(const std::filesystem::path &path) {
    clean(path);
    Store store(path);
    s4_fixture::Fixture f;
    auto token = store.save(f.world);
    for (int i = 0; i < 30; ++i) {
        const auto t = static_cast<std::int64_t>(i) * 200 + 100;
        f.dig({t});
        f.world.advance_to({t});
        const auto e = f.world.events_after({token.cursor}, 100).back();
        const SoilParcelRef p{token.world, {e.payload}};
        f.world.submit_soil({f.worker,
                             {t + 100},
                             SoilAction::Fill,
                             s4_fixture::patch,
                             p,
                             f.world.geometry_snapshot().geometry_revision});
        f.world.advance_to({t + 100});
    }
    token = store.save(f.world, token);
    require(f.world.geometry_edits().size() == 60 && f.world.geometry_snapshot().indexed_entries <= 4,
            "identical-box index did not compact");
    const auto raw = f.world.checkpoint();
    auto loaded = store.load(token.world);
    require(loaded.world.checkpoint() == raw, "geometry evidence changed");
    require(store.flow_total(token.world, {}, Metric::ExcavatedDry, {0}, {6001}) == 30 * 16 * 100,
            "excavated metric not based on actual edits");
    require(store.flow_total(token.world, {}, Metric::FilledDry, {0}, {6001}) == 30 * 16 * 100,
            "fill metric wrong");
    detail::GeometryDefinition def;
    def.config = f.geometry;
    def.voids.push_back(s4_fixture::room);
    detail::GeometryEdits edits;
    detail::EditIndex index;
    for (const auto &edit : f.world.geometry_edits()) {
        edits.emplace(edit.id, edit);
        for (auto key : detail::overlapping_bricks(edit.box, 8, 10000))
            index.emplace(std::pair{key, edit.id}, std::uint8_t{0});
    }
    const detail::GeometryView reference{def, edits, index, 200000};
    for (int x = 10; x <= 16; ++x)
        for (int y = 9; y <= 15; ++y)
            for (int z = 9; z <= 15; ++z) {
                PointQ p{x, y, z};
                require(f.world.query_material(s4_fixture::position(p, f.geometry)) ==
                            detail::material_at(reference, p),
                        "derived index changed authority");
            }
}
void equivalence(const std::filesystem::path &) {
    // Detached kernel fixture: this tests representation equivalence, not biological digging.
    detail::GeometryDefinition definition;
    definition.config = s4_fixture::config();
    definition.voids.push_back(s4_fixture::room);
    detail::GeometryEdits edits;
    detail::EditIndex all, filtered;
    Rng random(5505);
    for (std::uint64_t i = 1; i <= 256; ++i) {
        const auto y = static_cast<std::int32_t>(8 + random.next() % 6),
                   z = static_cast<std::int32_t>(8 + random.next() % 6);
        const BoxQ box = i % 3 ? s4_fixture::patch : BoxQ{{14, y, z}, {16, y + 3, z + 3}};
        GeometryEdit e;
        e.id = {i};
        e.box = box;
        e.kind = i % 2 ? SoilAction::Excavate : SoilAction::Fill;
        edits.emplace(e.id, e);
        for (auto key : detail::overlapping_bricks(box, 8, 10000))
            all.emplace(std::pair{key, e.id}, std::uint8_t{0});
        detail::rebuild_index_edit(edits, filtered, e, 8, 10000);
        if (i % 16)
            continue;
        const detail::GeometryView reference{definition, edits, all, 200000},
            optimized{definition, edits, filtered, 200000};
        require(detail::material_volume(reference, {{10, 8, 8}, {18, 18, 18}}, Material::Soil) ==
                    detail::material_volume(optimized, {{10, 8, 8}, {18, 18, 18}}, Material::Soil),
                "overlap volume differs after index reduction");
        for (int x = 12; x <= 17; ++x)
            for (int y2 = 9; y2 <= 16; ++y2) {
                const PointQ p{x, y2, 12};
                require(detail::material_at(reference, p) == detail::material_at(optimized, p),
                        "point classification differs");
                require(detail::signed_distance(reference, p) == detail::signed_distance(optimized, p),
                        "signed distance differs");
                require(detail::clear_sweep(reference, {12, 12, 12}, p, 1) ==
                            detail::clear_sweep(optimized, {12, 12, 12}, p, 1),
                        "clearance differs");
            }
    }
    require(edits.size() == 256 && filtered.size() < all.size(),
            "authority was discarded or index did not reduce");
}
void history(const std::filesystem::path &path) {
    clean(path);
    Store store(path);
    s3_fixture::Exchange exchange(12, 1000, true, false);
    auto &w = exchange.world;
    for (int t = 1; t < 500; ++t)
        w.schedule({{t}});
    w.advance_to({500});
    const auto token = store.save(w);
    HistoryFilter filter;
    filter.world = token.world;
    filter.individual = exchange.recipient.id;
    filter.limit = 1;
    std::vector<EventId> seen(0);
    for (;;) {
        auto page = store.history(filter);
        if (page.empty())
            break;
        require(page.size() == 1, "query exceeded page limit");
        seen.push_back(page[0].fact.id);
        filter.after = page[0].fact.id;
    }
    std::vector<EventId> expected(0);
    for (const auto &e : w.committed_events())
        if (e.actor == exchange.recipient.id ||
            (e.kind == FactKind::NutritionTransferred && e.payload == exchange.recipient.id.value))
            expected.push_back(e.id);
    require(seen == expected, "recipient history missed internal transfers or included unrelated events");
    filter.individual = {};
    filter.after = {};
    filter.kind = FactKind::Diagnostic;
    filter.limit = 10000;
    require(store.history(filter).size() == 499, "kind filter differs from facts");
    filter.limit = 0;
    rejects([&] { store.history(filter); });
    sql(path, "DELETE FROM participants WHERE event=(SELECT max(event) FROM participants)");
    rejects([&] { store.load(token.world); });
}
void behaviors(const std::filesystem::path &path) {
    clean(path);
    Store store(path);
    WorldRuntime w({5, 1}, 7);
    const auto c = w.seed_colony();
    const auto a = w.seed_ant(c, {});
    w.enable_physiology(a);
    auto token = store.save(w);
    const std::array programs{IndividualBehavior::Nurse, IndividualBehavior::Rest,
                              IndividualBehavior::Paused};
    for (auto program : programs) {
        w.set_behavior(a, program);
        token = store.save(w, token);
        const auto metric =
            static_cast<Metric>(static_cast<unsigned>(Metric::Paused) + static_cast<unsigned>(program));
        require(store.series(token.world, c.id, metric, {0}, {1}, token.generation - 1)[0].value == 1,
                "runtime behavior gauge incorrect");
    }
    require(store.flow_total(token.world, {}, Metric::BehaviorChanges, {0}, {1}) == 3,
            "behavior changes fabricated or dropped");
    w.schedule_lifecycle(a, {1}, LifeStage::Dead);
    w.advance_to({1});
    token = store.save(w, token);
    require(store.series(token.world, c.id, Metric::Paused, {1}, {2})[0].value == 0,
            "dead worker counted as active program");
    store.load(token.world);
}
void storage_limits(const std::filesystem::path &path) {
    clean(path);
    Store store(path);
    WorldRuntime w({5, 1}, 1);
    w.seed_food({}, {UINT64_MAX, 0, 0, 0});
    const auto token = store.save(w);
    w.advance_to({1});
    const auto bytes = w.checkpoint();
    rejects([&] { store.save(w, token); });
    require(store.latest(token.world) == token && w.checkpoint() == bytes,
            "metric overflow did not roll back atomically");
    require(store.load(token.world).world.summary().now == SimTime{}, "overflow advanced durable cursor");
    SaveOptions bad;
    bad.retained_generations = 0;
    rejects([&] { store.save(w, token, bad); });
    auto p = path;
    p += "history";
    clean(p);
    Store other(p);
    auto ordinary = world();
    auto t = other.save(ordinary);
    ordinary.advance_to({1000});
    t = other.save(ordinary, t);
    ordinary.advance_to({60000});
    other.save(ordinary, t);
    sql(p, "UPDATE samples SET value='0000000000000011' WHERE generation='0000000000000001' AND metric=0");
    rejects([&] { other.load({5, 1}); });
}
void crash_mode(const std::string &mode, const std::filesystem::path &path) {
    if (mode == "CRASH_SEED") {
        clean(path);
        Store store(path);
        auto w = world();
        store.save(w);
        return;
    }
    Store store(path);
    auto recovered = store.load({5, 1});
    auto expected = world();
    auto advance = [](WorldRuntime &w) {
        w.advance_to({1001});
        w.place_food({{5, 1}, {1, 2}, {}, {10, 20, 0, 0}});
        w.advance_to({2000});
    };
    if (mode == "CRASH_OLD" || mode == "CRASH_NEW") {
        if (mode == "CRASH_NEW")
            advance(expected);
        require(recovered.world.checkpoint() == expected.checkpoint(), "crash recovered a mixed generation");
        if (mode == "CRASH_NEW") {
            const auto before = recovered.world.checkpoint();
            recovered.world.place_food({{5, 1}, {1, 2}, {}, {10, 20, 0, 0}});
            require(before == recovered.world.checkpoint(), "crash retry duplicated command");
        }
        return;
    }
    const auto stage = static_cast<SaveStage>(std::stoi(mode.substr(6)));
    advance(recovered.world);
    SaveOptions options;
    options.fault_hook = [&](SaveStage at) {
        if (at == stage)
            std::_Exit(77);
    };
    store.save(recovered.world, recovered.token, options);
    throw std::runtime_error("crash hook did not fire");
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument("usage: antworld_s5_tests CASE DATABASE");
        const std::string test = argv[1];
        const std::filesystem::path path = argv[2];
        std::filesystem::create_directories(path.parent_path());
        if (test.starts_with("CRASH_"))
            crash_mode(test, path);
        else if (test == "ATOMIC")
            atomic(path);
        else if (test == "COMMANDS")
            commands(path);
        else if (test == "ISOLATION")
            isolation(path);
        else if (test == "METRICS")
            metrics(path);
        else if (test == "WINDOWS")
            windows(path);
        else if (test == "CORRUPTION")
            corrupt(path);
        else if (test == "UINT64")
            exact(path);
        else if (test == "GEOMETRY")
            geometry(path);
        else if (test == "EQUIVALENCE")
            equivalence(path);
        else if (test == "HISTORY")
            history(path);
        else if (test == "BEHAVIORS")
            behaviors(path);
        else if (test == "STORAGE_LIMITS")
            storage_limits(path);
        else
            throw std::invalid_argument("unknown test");
        std::cout << "PASS S5_" << test << '\n';
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL: " << e.what() << '\n';
        return 1;
    }
}
