#include "rm01_egg_timing.hpp"
#include "rm02_fixtures.hpp"
#include "wp4_lineage.hpp"
#include "process_memory.hpp"
#include "antworld/storage/store.hpp"

#include <algorithm>
#include <chrono>
#include <iostream>
#include <limits>

namespace {
using namespace antworld;
using namespace antworld::rm01;
using namespace antworld::rm02;
using namespace antworld::wp4;
using Clock = std::chrono::steady_clock;
using Path = std::filesystem::path;
using Time = std::int64_t;

constexpr PhysiologySeed standard{{200, 100, 200, 0}, 1500000000, 1600, 0}; // ENGINEERING_FIXTURE.
constexpr std::array supply{"depot", "ordinary", "scarce", "empty"};

struct Case {
    std::string_view family, arm, profile;
    unsigned workers;
    std::uint64_t seed;

    bool colony() const { return family == "ecology" || family == "reserve"; }
    bool funded() const { return family == "clock" && arm == "funded"; }
    bool lays() const { return colony() || funded() || family == "brood"; }
    SimTime clock() const { return resolve_egg_duration(rm01::profile(profile)); }
    Time end() const {
        if (colony()) return (arm == "depot" ? 180 : 90) * day_ms;
        if (family == "clock") return (funded() ? 2 * day_ms : 0) + clock().milliseconds + 1;
        if (family == "pulse") return 12 * hour_ms + 1;
        return 11 * day_ms;
    }
};

template<class T, std::size_t N>
bool one_of(std::string_view value, const std::array<T, N>& allowed) {
    return std::ranges::find(allowed, value) != allowed.end();
}

void validate(const Case& c) {
    require(c.seed && (c.colony() || c.seed == 1), "invalid WP-4 seed");
    require(c.family == "clock" || c.profile == "legacy", "reference clock is confined to the technical assay");
    const auto legacy = c.clock() == legacy_duration;
    require((c.family == "ecology" && one_of(c.arm, supply) && (c.workers == 0 || c.workers == 8 || c.workers == 32)) ||
            (c.family == "reserve" && c.arm == "ordinary" && (c.workers == 0 || c.workers == 8)) ||
            (c.family == "clock" && c.workers == 0 &&
             (one_of(c.arm, std::array{"seed", "funded", "sentinel"}) ||
              (!legacy && c.arm == "energy-tie") || (legacy && one_of(c.arm, std::array{"water-tie", "interrupted"})))) ||
            (c.family == "pulse" && c.workers == 1 && one_of(c.arm, std::array{"none", "sham", "before", "on"})) ||
            (c.family == "brood" && c.workers == 3 && one_of(c.arm, std::array{"full", "low-protein", "none"})),
            "invalid WP-4 case");
}

ReproductionConfig reproduction() {
    ReproductionConfig config;
    config.maintenance_horizon = config.interval;
    return config;
}

struct EggAssay {
    PhysiologySeed budget = original_egg_budget();
    Time terminal;
    DeathCause cause{DeathCause::None};
};

EggAssay egg_assay(const Case& c) {
    const auto duration = c.clock().milliseconds;
    EggAssay assay{original_egg_budget(), duration};
    if (c.arm == "seed" || c.funded()) {
        if (static_cast<Time>(assay.budget.body_energy_nj) <= duration) {
            assay.terminal = static_cast<Time>(assay.budget.body_energy_nj);
            assay.cause = DeathCause::EnergyDepleted;
        }
        return assay;
    }
    // ENGINEERING_FIXTURE stock for boundary probes. The Core still executes depletion.
    assay.budget.body_energy_nj = static_cast<std::uint64_t>(duration + 4);
    assay.budget.hydration_ug = static_cast<std::uint64_t>((duration + 1) / hour_ms + 1);
    if (c.arm == "energy-tie") {
        assay.budget.body_energy_nj = static_cast<std::uint64_t>(duration);
        assay.cause = DeathCause::EnergyDepleted;
    } else if (c.arm == "water-tie") {
        assay.budget.hydration_ug = static_cast<std::uint64_t>(duration / hour_ms);
        assay.cause = DeathCause::Dehydrated;
    } else if (c.arm == "interrupted") {
        --assay.terminal;
        assay.cause = DeathCause::Fixture;
    }
    return assay;
}

struct Scene {
    WorldRuntime world;
    AntRef queen, egg;
    std::vector<AntRef> workers;
};

AntRef queen(WorldRuntime& world, ColonyRef colony, const PhysiologySeed& seed, SimTime clock, bool lays) {
    const auto ant = world.seed_ant(colony, {{}, LifeStage::Adult, Caste::Queen, 4000});
    auto p = physiology_config(clock);
    p.adult_protein_target_ug = 20;
    world.enable_physiology(ant, seed, p);
    if (lays) world.enable_reproduction(ant, reproduction());
    return ant;
}

Scene ecology(const Case& c) {
    if (c.family == "ecology" && c.workers) {
        auto frozen = ecology_fixture(c.seed, c.workers, c.arm);
        return {std::move(frozen.world), frozen.queen, {}, std::move(frozen.workers)};
    }
    // The accepted fixture excludes zero workers and hardcodes the maternal stock.
    // Reproduce its public setup for those two new arms.
    Scene s{WorldRuntime({63, 1}, c.seed, {}, s6_3_1_fixture::limits()), {}, {}, {}};
    auto& world = s.world;
    world.configure_long_term();
    BehaviorConfig behavior;
    behavior.trails_enabled = false;
    world.configure_surface({{-.03, 0, -.03}, 7, 7, .01}, {}, behavior);
    GeometryConfig geometry;
    geometry.origin_m = {-.008, -.006, -.006};
    geometry.initial_solid = {{0, 0, 0}, {32, 24, 24}};
    const std::array<BoxQ, 2> voids{{{{12, 8, 8}, {20, 16, 16}}, {{0, 10, 10}, {32, 14, 14}}}};
    world.configure_geometry(geometry, voids);
    SocialConfig social;
    social.gift_first = true;
    social.local_work_continuation = true;
    social.decision_interval = {6 * hour_ms};
    social.minimum_program_time = social.decision_interval;
    world.configure_social(social);
    const auto colony = world.seed_colony();
    auto maternal = standard;
    if (c.family == "reserve") {
        maternal.body_energy_nj /= 2;
        maternal.hydration_ug /= 2;
    }
    s.queen = queen(world, colony, maternal, legacy_duration, true);
    for (unsigned i = 0; i < c.workers; ++i) {
        const auto worker = world.seed_ant(colony, {});
        world.enable_physiology(worker, standard, physiology_config(legacy_duration));
        world.set_autonomy(worker);
        s.workers.push_back(worker);
    }
    const auto stock_scale = std::max(c.workers, 8U);
    if (c.arm == "depot") {
        world.seed_food({}, {200000ULL * stock_scale, 20000ULL * stock_scale, 100000ULL * stock_scale, 0});
    } else if (c.arm != "empty") {
        const auto food = world.seed_food({.02, 0, .01}, {4000, 500, 4000, 0});
        ResourceCycleConfig cycle;
        cycle.reserve = {20000ULL * stock_scale, (c.arm == "scarce" ? 50ULL : 2000ULL) * stock_scale,
                         5000ULL * stock_scale, 0};
        cycle.release_limit = {4000, 400, 2000, 0};
        world.configure_resource_cycle(food, cycle);
    }
    return s;
}

Scene setup(const Case& c) {
    if (c.colony()) return ecology(c);
    const WorldId id = c.family == "clock" ? WorldId{64, 1} : c.family == "pulse" ? WorldId{65, 1} : WorldId{65, 2};
    Scene s{WorldRuntime(id, c.seed, {}, s6_3_1_fixture::limits()), {}, {}, {}};
    auto& world = s.world;
    world.configure_long_term();
    const auto colony = world.seed_colony();
    if (c.family == "clock" && !c.funded()) {
        s.egg = world.seed_ant(colony, {{}, LifeStage::Egg, Caste::Worker, 4000});
        enable_seeded_egg(world, s.egg, egg_assay(c).budget, rm01::profile(c.profile));
        return s;
    }
    SocialConfig social;
    if (c.family != "clock") social.demand_sensitive = false;
    world.configure_social(social);
    const auto maternal = c.family == "pulse" ? PhysiologySeed{{}, 1000000000, 1200, 0} : standard;
    s.queen = queen(world, colony, maternal, c.clock(), c.lays());
    for (unsigned i = 0; i < c.workers; ++i) {
        const auto donor = world.seed_ant(colony, {});
        auto p = physiology_config(legacy_duration);
        p.absorption_period = {c.family == "pulse" ? day_ms : 7 * day_ms};
        FoodMass stock;
        if (c.family == "pulse") {
            if (c.arm != "sham") stock = {60, 20, 20, 0};
        } else if (i == 0) stock = {0, c.arm == "low-protein" ? 40U : 100U, 0, 0};
        else stock = {90, 0, 10, 0};
        world.enable_physiology(donor, {stock, 1500000000, 1600, 0}, p);
        s.workers.push_back(donor);
    }
    return s;
}

double elapsed(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

void write(std::ostream& out, std::span<const std::uint8_t> bytes) {
    out.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
}

void save(const Path& path, std::span<const std::uint8_t> bytes) {
    auto out = output(path);
    write(out, bytes);
    out.close();
}

AntRef first_child(const WorldRuntime& world, AntRef mother) {
    EventId cursor;
    while (cursor.value < world.summary().committed_events) {
        const auto page = world.events_after(cursor, fact_page);
        require(!page.empty(), "WP-4 birth lookup has a history gap");
        for (const auto& fact : page)
            if (fact.kind == FactKind::AntBorn && fact.payload == mother.id.value)
                return {fact.world, fact.actor};
        cursor = page.back().id;
    }
    throw std::runtime_error("WP-4 required committed fixture birth is absent");
}

std::vector<Time> boundaries(const Case& c, Time& middle) {
    if (c.family == "clock") {
        const auto entry = c.funded() ? 2 * day_ms : 0;
        const auto offset = egg_assay(c).terminal;
        const auto terminal = entry + offset;
        const auto clock_at = c.end() - 1;
        middle = entry + offset / 2 + 1;
        std::vector<Time> times{0, entry, middle, terminal - 1, terminal, terminal + 1, clock_at - 1, clock_at, c.end()};
        std::ranges::sort(times);
        times.erase(std::unique(times.begin(), times.end()), times.end());
        return times;
    }
    if (c.family == "pulse") {
        middle = 6 * hour_ms;
        return {0, middle - 2, middle - 1, middle, middle + 1, 12 * hour_ms - 1, 12 * hour_ms, c.end()};
    }
    middle = c.end() / 2;
    std::vector<Time> times;
    const auto interval = c.colony() ? day_ms : 6 * hour_ms;
    for (Time t = 0; t <= c.end(); t += interval) {
        times.push_back(t);
        if (c.family == "brood" && t == 2 * day_ms) times.push_back(t + 1);
        if (c.family == "brood" && t == 4 * day_ms) times.insert(times.end(), {t + 1, t + 2, t + 3});
    }
    return times;
}

template<class Advance, class Capture, class Input>
void drive(const Scene& scene, WorldRuntime& world, const Case& c, bool observed,
           Advance advance, Capture capture, Input input) {
    const auto submit = [&](AntRef actor, AntRef recipient, Time at, std::uint64_t dose) {
        const auto id = world.submit_nutrition({actor, {at}, NutritionAction::Trophallaxis, recipient, dose});
        input(world.summary().now.milliseconds, at, actor, recipient, "gift", dose, id);
    };
    if (c.family == "pulse" && c.arm != "none")
        submit(scene.workers.front(), scene.queen, 6 * hour_ms - (c.arm != "on"), 100);
    if (c.family == "clock" && c.arm == "interrupted") {
        const auto at = egg_assay(c).terminal;
        const auto id = world.schedule_lifecycle(scene.egg, {at}, LifeStage::Dead);
        input(0, at, scene.egg, AntRef{}, "fixture_interruption", 0, id);
    }

    Time middle;
    for (const auto t : boundaries(c, middle)) {
        const bool brood_input = c.family == "brood" && (t == 2 * day_ms || t == 4 * day_ms);
        if (!observed && !brood_input && t != c.end()) continue;
        if (t) advance(t);
        if (brood_input) {
            const auto child = first_child(world, scene.queen);
            if (t == 2 * day_ms) submit(scene.workers.front(), child, t + 1, 100);
            else if (c.arm != "none")
                for (unsigned i = 0; i < scene.workers.size(); ++i)
                    submit(scene.workers[i], child, t + 1 + i, 100);
        }
        if (observed) capture(t, t == middle);
    }
}

void canonical(const WorldRuntime& world, const WorldRuntime& reference, const Path& path) {
    auto out = output(path);
    EventId cursor;
    while (cursor.value < world.summary().committed_events) {
        const auto page = world.events_after(cursor, fact_page);
        const auto exact = reference.events_after(cursor, fact_page);
        require(!page.empty() && page.size() == exact.size(), "WP-4 canonical history gap");
        for (std::size_t i = 0; i < page.size(); ++i) {
            const auto bytes = encode_event(page[i]);
            require(page[i].id.value == cursor.value + 1 && bytes == encode_event(exact[i]),
                    "WP-4 canonical bytes changed with observer or segmentation");
            const auto n = static_cast<std::uint32_t>(bytes.size());
            const std::array<std::uint8_t, 4> length{static_cast<std::uint8_t>(n), static_cast<std::uint8_t>(n >> 8),
                static_cast<std::uint8_t>(n >> 16), static_cast<std::uint8_t>(n >> 24)};
            write(out, length);
            write(out, bytes);
            cursor = page[i].id;
        }
    }
    out.close();
}

void check_clock(const Scene& scene, const Case& c, Time t) {
    const auto entry = c.funded() ? 2 * day_ms : 0;
    if (t < entry) return;
    const auto egg = c.funded() ? first_child(scene.world, scene.queen) : scene.egg;
    const auto p = scene.world.query_physiology(egg).value();
    const auto a = scene.world.query_ant(egg).value();
    const auto assay = egg_assay(c);
    const auto terminal = t >= entry + assay.terminal;
    const auto expected = !terminal ? LifeStage::Egg : assay.cause == DeathCause::None ? LifeStage::Larva : LifeStage::Dead;
    require(a.born_at.milliseconds == entry && p.mother == scene.queen.id &&
            p.initial == assay.budget && p.config.egg_duration == c.clock() && a.stage == expected &&
            p.death_cause == (terminal ? assay.cause : DeathCause::None), "WP-4 frozen clock boundary changed");
}

void configuration(const Scene& scene, const Case& c, const Path& dir) {
    auto out = output(dir / "configuration.csv");
    const auto identity = scene.world.summary().world;
    const auto& p = rm01::profile(c.profile);
    const auto r = reproduction();
    out << "family,arm,workers,profile,seed,world_id,queen,seeded_egg,horizon_ms,egg_ms,clock_population,clock_source,"
           "reproduction_interval_ms,maintenance_ms,egg_export_nj,egg_export_protein_ug,egg_export_water_ug,egg_heat_nj,"
           "sidecar_scope,classification\n"
        << c.family << ',' << c.arm << ',' << c.workers << ',' << c.profile << ',' << c.seed << ',' << identity.str()
        << ',' << scene.queen.id.value << ',' << scene.egg.id.value << ',' << c.end() << ',' << c.clock().milliseconds
        << ',' << std::quoted(p.population) << ',' << p.source << ',';
    if (c.lays()) out << r.interval.milliseconds << ',' << r.maintenance_horizon.milliseconds << ',' << r.egg_energy_nj
                       << ',' << r.egg_protein_ug << ',' << r.egg_water_ug << ',' << r.dissipated_energy_nj << ',';
    else out << ",,,,,,";
    out << "RM02_NUTRITION,ENGINEERING_FIXTURE\n";
    out.close();
    auto resources = output(dir / "initial_food.csv");
    resources << "resource,x_m,y_m,z_m,carbs_ug,protein_ug,water_ug,other_ug\n";
    for (const auto& food : scene.world.food_sources())
        mass(resources << food.id.value << ',' << food.position.x << ',' << food.position.y << ',' << food.position.z,
             food.initial) << '\n';
    resources.close();
}

void run(const Path& dir, const Case& c) {
    auto scene = setup(c);
    auto& world = scene.world;
    const auto identity = world.summary().world;
    const auto initial = world.checkpoint();
    save(dir / "initial.chk", initial);
    configuration(scene, c, dir);
    Plan plan{"maternal-development", {}, {}, true};
    // Full care, movement and other facts are preserved once in canonical.bin.
    // The live sidecar supplies only the existing RM-02 budget projection.
    if (scene.queen.id.value) plan.focal.push_back(scene.queen.id);
    if (scene.egg.id.value) plan.focal.push_back(scene.egg.id);
    for (const auto worker : scene.workers) plan.focal.push_back(worker.id);
    const auto database = dir / "observer.sqlite";
    auto observer = std::make_unique<Observer>(database, world, plan);
    observer->start_background();
    Lineage lineage(dir);
    auto cuts = output(dir / "cuts.csv");
    cuts << "cut,cursor,sim_ms,examined,selected,records,dropped,payload_bytes,lineage_bytes,capture_ms,"
            "lineage_ms,submission_ms,nest_carbs_ug,nest_protein_ug,nest_water_ug,nest_other_ug,"
            "soil_initial_q3,soil_remaining_q3,soil_carried_q3,soil_deposited_q3\n";
    auto inputs = output(dir / "inputs.csv");
    inputs << "issued_ms,execute_ms,actor,recipient,kind,requested_ug,scheduled_id\n";
    std::size_t sequence{}, peak_queue{};
    double advance_ms{}, drain_ms{}, write_ms{}, midpoint_ms{};
    const auto drain = [&] {
        const auto begin = Clock::now();
        observer->flush();
        drain_ms += elapsed(begin);
        require(observer->committed_cuts() == sequence, "WP-4 unpublished cut");
        const auto stats = observer->background_stats();
        write_ms += stats.write_ms;
        peak_queue = std::max(peak_queue, stats.peak_payload_bytes);
    };
    const auto midpoint = dir / "midpoint.sqlite";
    const auto capture = [&](Time t, bool restore) {
        const auto start = Clock::now();
        auto cut = observer->capture();
        const auto capture_ms = elapsed(start);
        require(!cut.dropped && cut.end.time.milliseconds == t, "WP-4 sidecar has incomplete coverage");
        const auto payload = cut.payload.size();
        const auto view_start = Clock::now();
        const auto view_bytes = lineage.capture(world, ++sequence, cut.end.cursor, cut.end.time);
        const auto view_ms = elapsed(view_start);
        const auto submit_start = Clock::now();
        observer->submit(std::move(cut));
        const auto submit_ms = elapsed(submit_start);
        const auto soil = world.geometry_snapshot().ledger;
        require(soil.initial_q3 == soil.remaining_q3 + soil.carried_q3 + soil.deposited_q3, "WP-4 soil mismatch");
        const auto colonies = world.colonies();
        require(colonies.size() == 1, "WP-4 expected one colony");
        s6_3_1_fixture::conserved(world);
        cuts << sequence << ',' << cut.end.cursor << ',' << t << ',' << cut.examined << ',' << cut.selected << ','
             << cut.records << ',' << cut.dropped << ',' << payload << ',' << view_bytes << ',' << capture_ms << ','
             << view_ms << ',' << submit_ms;
        mass(cuts, colonies.front().nest_food) << ',' << soil.initial_q3 << ',' << soil.remaining_q3 << ','
             << soil.carried_q3 << ',' << soil.deposited_q3 << '\n';
        if (c.family == "clock") check_clock(scene, c, t);
        if (!restore) return;
        drain();
        const auto recovery_start = Clock::now();
        const auto checkpoint = world.checkpoint();
        save(dir / "midpoint.chk", checkpoint);
        observer->anchor(checkpoint);
        observer.reset();
        const auto limits = s6_3_1_fixture::limits();
        {
            storage::Store store(midpoint, limits, storage::StoreFormat::Segmented);
            store.save(world);
            store.checkpoint_wal();
        }
        storage::Store store(midpoint, limits);
        auto restored = store.load(identity).world.checkpoint();
        require(restored == checkpoint, "WP-4 SQLite checkpoint changed");
        world.restore(restored);
        observer = std::make_unique<Observer>(database, world, plan, restored);
        require(observer->publish(observer->capture()) == Publish::Duplicate, "WP-4 reopened cut was duplicated");
        observer->start_background();
        midpoint_ms = elapsed(recovery_start);
    };
    const auto started = Clock::now();
    drive(scene, world, c, true, [&](Time t) {
        const auto begin = Clock::now();
        world.advance_to({t});
        advance_ms += elapsed(begin);
    }, capture, [&](Time now, Time at, AntRef actor, AntRef target, std::string_view name, auto dose, ScheduledId id) {
        inputs << now << ',' << at << ',' << actor.id.value << ',' << target.id.value << ',' << name << ',' << dose
               << ',' << id.value << '\n';
    });
    drain();
    lineage.close();
    cuts.close();
    inputs.close();
    const auto final = world.checkpoint();
    save(dir / "final.chk", final);
    observer->anchor(final);
    observer.reset();
    const auto wall_ms = elapsed(started);
    const auto [rss, peak] = performance::memory();
    const auto replay_start = Clock::now();
    WorldRuntime reference({91, 4}, c.seed, {}, s6_3_1_fixture::limits());
    reference.restore(initial);
    drive(scene, reference, c, false, [&](Time t) { reference.advance_to({t}); },
          [](auto...) {}, [](auto...) {});
    const auto state = world.snapshot();
    require(reference.snapshot() == state && reference.checkpoint() == final && midpoint_ms > 0,
            "WP-4 observer-off or checkpoint replay diverged");
    canonical(world, reference, dir / "canonical.bin");
    auto result = output(dir / "summary.csv");
    result << "status,horizon_ms,events,cuts,state_hash,trace_hash,rng,exact_off,sqlite_midpoint_exact,"
              "advance_ms,wall_ms,midpoint_ms,drain_ms,writer_ms,replay_and_canonical_ms,peak_queue_bytes,"
              "rss_bytes,peak_rss_bytes,observer_bytes,midpoint_sqlite_bytes\n"
           << "PASS," << state.now.milliseconds << ',' << state.committed_events << ',' << sequence << ','
           << state.state_hash << ',' << state.trace_hash << ',' << state.rng_state << ",1,1," << advance_ms << ','
           << wall_ms << ',' << midpoint_ms << ',' << drain_ms << ',' << write_ms << ',' << elapsed(replay_start) << ','
           << peak_queue << ',' << rss << ',' << peak << ',' << std::filesystem::file_size(database) << ','
           << std::filesystem::file_size(midpoint) << '\n';
    result.close();
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 7, "usage: antworld_s6_4_wp4 OUTPUT FAMILY ARM WORKERS PROFILE SEED");
        const auto workers = unsigned_integer(argv[4]);
        require(workers <= 32, "invalid WP-4 worker count");
        const Case c{argv[2], argv[3], argv[5], static_cast<unsigned>(workers), unsigned_integer(argv[6])};
        validate(c);
        const Path dir = argv[1];
        require(std::filesystem::create_directories(dir), "WP-4 requires a new output directory");
        run(dir, c);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
