#include "rm01_egg_timing.hpp"

#include "antworld/storage/live_history.hpp"
#include "process_memory.hpp"
#include "s6_3_1_fixture.hpp"

#include <algorithm>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <utility>

namespace {
using namespace antworld;
using namespace antworld::storage;
using namespace antworld::rm01;
using Clock = std::chrono::steady_clock;
constexpr std::size_t page_size = 512;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

double elapsed(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

std::ofstream output(const std::filesystem::path& path) {
    std::ofstream stream(path, std::ios::binary);
    stream.exceptions(std::ios::failbit | std::ios::badbit);
    stream << std::setprecision(17);
    return stream;
}

void write_bytes(const std::filesystem::path& path, const std::vector<std::uint8_t>& bytes) {
    auto stream = output(path);
    stream.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
}

template<class Read>
void read_facts(const WorldRuntime& world, EventId& cursor, Read read) {
    while (cursor.value < world.summary().committed_events) {
        const auto page = world.events_after(cursor, page_size);
        require(!page.empty(), "committed event page missing");
        for (const auto& fact : page) {
            require(fact.id.value == cursor.value + 1, "noncontiguous committed event cursor");
            read(fact);
            cursor = fact.id;
        }
    }
}

void exact(const WorldRuntime& expected, const WorldRuntime& restored) {
    require(expected.snapshot() == restored.snapshot(), "state or trace hash changed");
    require(expected.pending_events() == restored.pending_events(), "queued event state changed");
    require(expected.checkpoint_frame() == restored.checkpoint_frame(), "checkpoint frame changed");
    EventId cursor;
    while (cursor.value < expected.summary().committed_events) {
        const auto a = expected.events_after(cursor, page_size);
        const auto b = restored.events_after(cursor, page_size);
        require(!a.empty() && a.size() == b.size(), "event page length changed");
        for (std::size_t i = 0; i < a.size(); ++i)
            require(encode_event(a[i]) == encode_event(b[i]), "canonical fact bytes changed");
        cursor = a.back().id;
    }
}

struct Egg {
    EntityId mother;
    EventId entry_id;
    SimTime entered;
    std::optional<WorldEvent> terminal;
};

struct EggObserver {
    EventId cursor;
    std::map<EntityId, Egg> eggs;
    double ms{};

    void observe(const WorldRuntime& world) {
        const auto start = Clock::now();
        read_facts(world, cursor, [&](const WorldEvent& fact) {
            if (fact.stage == LifeStage::Egg && (fact.kind == FactKind::AntBorn || fact.kind == FactKind::AntSeeded)) {
                const EntityId mother{fact.kind == FactKind::AntBorn ? fact.payload : 0};
                require(eggs.emplace(fact.actor, Egg{mother, fact.id, fact.time, {}}).second,
                        "duplicate egg entry fact");
            }
            const bool hatch = fact.kind == FactKind::StageChanged && fact.stage == LifeStage::Larva;
            if (hatch || fact.kind == FactKind::AntDied) {
                const auto it = eggs.find(fact.actor);
                if (it != eggs.end() && !it->second.terminal) it->second.terminal = fact;
            }
        });
        ms += elapsed(start);
    }

    void write(const WorldRuntime& world, const std::filesystem::path& path) const {
        auto stream = output(path);
        const auto state = world.summary();
        stream << "world_id,egg_id,mother_id,entry_event_id,entry_ms,clock_ms,outcome,outcome_event_id,outcome_or_censor_ms,"
                  "initial_energy_nj,initial_water_ug,initial_tissue_protein_ug,basal_nj_per_ms,water_ug_per_period,"
                  "water_loss_period_ms,observed_stage,observed_updated_ms,observed_stage_progress_ms,"
                  "observed_energy_nj,observed_water_ug,observed_death_cause_code\n";
        for (const auto& [id, egg] : eggs) {
            const auto physiology = world.query_physiology({state.world, id});
            const auto ant = world.query_ant({state.world, id});
            require(physiology && ant && ant->born_at == egg.entered && physiology->mother == egg.mother,
                    "egg entry and committed identity disagree");
            const auto outcome = egg.terminal ? (egg.terminal->kind == FactKind::AntDied ? "death" : "hatch") : "censored";
            stream << state.world.str() << ',' << id.value << ',' << egg.mother.value << ',' << egg.entry_id.value << ','
                   << egg.entered.milliseconds << ',' << physiology->config.egg_duration.milliseconds << ',' << outcome
                   << ',' << (egg.terminal ? egg.terminal->id.value : 0) << ','
                   << (egg.terminal ? egg.terminal->time : state.now).milliseconds << ','
                   << physiology->initial.body_energy_nj << ',' << physiology->initial.hydration_ug << ','
                   << physiology->initial.tissue_protein_ug << ',' << physiology->config.basal_nj_per_ms << ','
                   << physiology->config.water_loss_ug_per_period << ',' << physiology->config.water_loss_period.milliseconds
                   << ',' << static_cast<unsigned>(ant->stage) << ',' << physiology->updated_at.milliseconds << ','
                   << physiology->stage_progress.milliseconds << ',' << physiology->body_energy_nj << ','
                   << physiology->hydration_ug << ',' << static_cast<unsigned>(physiology->death_cause) << '\n';
        }
    }
};

void write_facts(const WorldRuntime& world, const std::filesystem::path& path) {
    auto stream = output(path);
    stream << "event_id,time_ms,source_id,actor_id,kind_code,stage_code,payload,canonical_hex\n";
    constexpr std::string_view digits = "0123456789abcdef";
    EventId cursor;
    read_facts(world, cursor, [&](const WorldEvent& f) {
        stream << f.id.value << ',' << f.time.milliseconds << ',' << f.source.value << ',' << f.actor.value << ','
               << static_cast<unsigned>(f.kind) << ',' << static_cast<unsigned>(f.stage) << ',' << f.payload << ',';
        for (const auto byte : encode_event(f)) stream << digits[byte >> 4] << digits[byte & 15U];
        stream << '\n';
    });
}

struct Publications {
    Store store;
    LiveHistoryWriter writer;
    std::ofstream cuts;
    std::optional<SaveToken> previous;
    double query_ms{}, scoped_query_ms{};

    explicit Publications(const std::filesystem::path& root)
        : store(root / "world.sqlite", s6_3_1_fixture::limits(), StoreFormat::Segmented),
          writer(root / "world.sqlite", s6_3_1_fixture::limits()), cuts(output(root / "cuts.csv")) {
        cuts << "time_ms,generation,cursor,frame_bytes,capture_bytes,checkpoint_ms,capture_ms,foreground_ms,"
                "background_ms,finish_ms,wal_flush_ms,restore_ms,database_bytes,current_rss_bytes,peak_rss_bytes\n";
    }

    void publish(WorldRuntime& world, bool restore, bool full_check = false) {
        auto start = Clock::now();
        require(writer.try_submit(world, previous), "history submission rejected");
        const auto foreground = elapsed(start);
        start = Clock::now();
        const auto publication = writer.finish(world);
        const auto finish = elapsed(start);
        previous = publication.token;
        require(!world.unpublished_history(), "committed cut did not acknowledge history");
        start = Clock::now();
        store.checkpoint_wal();
        const auto flush = elapsed(start);
        double restore_ms = -1;
        if (restore) {
            start = Clock::now();
            auto saved = store.load(previous->world);
            restore_ms = elapsed(start);
            require(saved.token == *previous && saved.world.checkpoint_frame() == world.checkpoint_frame(),
                    "published cut did not restore its exact frame");
            if (full_check) exact(world, saved.world);
            world = std::move(saved.world);
            writer.bind(world);
        }
        const auto [rss, peak] = performance::memory();
        cuts << world.summary().now.milliseconds << ',' << previous->generation << ',' << previous->cursor << ','
             << publication.frame_bytes << ',' << publication.captured_bytes << ',' << publication.checkpoint_ms << ','
             << publication.capture_ms << ',' << foreground << ',' << publication.background_ms << ',' << finish << ','
             << flush << ',' << restore_ms << ',' << store.database_bytes() << ',' << rss << ',' << peak << '\n';
    }

    void query(const WorldRuntime& world) {
        const auto summary = world.summary();
        const auto start_id = summary.committed_events > 256 ? summary.committed_events - 256 : 0;
        const auto start = Clock::now();
        const auto records = store.history({summary.world, {start_id}, {}, {INT64_MAX}, {}, {}, 256});
        query_ms = elapsed(start);
        require(records.size() == summary.committed_events - start_id, "published history query is incomplete");
        const SimTime begin{summary.now.milliseconds / 2};
        const auto scope_start = Clock::now();
        const auto births = store.history({summary.world, {}, begin, {INT64_MAX}, {}, FactKind::AntBorn, 256});
        scoped_query_ms = elapsed(scope_start);
        for (const auto& birth : births)
            require(birth.fact.kind == FactKind::AntBorn && birth.fact.time >= begin, "scoped history contains unrelated facts");
    }
};

void write_config(const std::filesystem::path& dir, const Profile& profile_row, SimTime duration,
                  std::string_view mode, std::uint64_t seed, bool observer) {
    auto stream = output(dir / "configuration.csv");
    stream << "scope,profile,mode,seed,species,population,condition,source,source_days,source_unit,"
              "clock_ms,observer_enabled,biological_status\n"
           << "ENGINEERING_FIXTURE," << profile_row.id << ',' << mode << ',' << seed << ",Lasius niger,"
           << std::quoted(profile_row.population) << ',' << std::quoted(profile_row.condition) << ','
           << std::quoted(profile_row.source) << ',' << profile_row.days << ',' << profile_row.unit << ','
           << duration.milliseconds << ',' << observer << ",BIOLOGICAL_NOT_VALIDATED\n";
}

void write_summary(const std::filesystem::path& dir, const WorldRuntime& world, const Publications& saves,
                   double advance_ms, double observer_ms, AntRef queen, std::uint64_t online_peak) {
    s6_3_1_fixture::conserved(world);
    const auto state = world.snapshot();
    const auto n = world.nutrition_snapshot();
    const auto soil = world.geometry_snapshot().ledger;
    const auto q = queen.id.value ? world.query_ant(queen) : std::nullopt;
    const auto [rss, peak] = performance::memory();
    auto stream = output(dir / "summary.csv");
    stream << "world_id,now_ms,facts,pending,state_hash,trace_hash,living,queen_id,queen_alive,advance_ms,observer_ms,"
              "query_ms,scoped_query_ms,rss_bytes,online_peak_rss_bytes,process_peak_rss_bytes,database_bytes,"
              "carb_in_ug,carb_accounted_ug,protein_in_ug,"
              "protein_accounted_ug,water_in_ug,water_accounted_ug,energy_input_nj,body_energy_nj,"
              "dissipated_energy_nj,soil_initial_q3,soil_remaining_q3,soil_carried_q3,soil_deposited_q3,replay\n"
           << state.world.str() << ',' << state.now.milliseconds << ',' << state.committed_events << ','
           << state.pending_events << ',' << hex64(state.state_hash) << ',' << hex64(state.trace_hash) << ','
           << state.living_ants << ',' << queen.id.value << ',' << (q && q->alive()) << ',' << advance_ms << ','
           << observer_ms << ',' << saves.query_ms << ',' << saves.scoped_query_ms << ',' << rss << ','
           << online_peak << ',' << peak << ',' << saves.store.database_bytes()
           << ',' << n.introduced.carbs_ug << ',' << n.accounted.carbs_ug << ',' << n.introduced.protein_ug << ','
           << n.accounted.protein_ug << ',' << n.introduced.water_ug << ',' << n.accounted.water_ug << ','
           << n.energy_input_nj << ',' << n.body_energy_nj << ',' << n.dissipated_energy_nj << ','
           << soil.initial_q3 << ',' << soil.remaining_q3 << ',' << soil.carried_q3 << ',' << soil.deposited_q3
           << ",exact\n";
    write_bytes(dir / "final.frame", world.checkpoint_frame());
}

struct ShortPlan {
    bool funded{};
    PhysiologySeed budget = original_egg_budget();
    std::int64_t outcome_offset{};
    DeathCause death{DeathCause::None};
};

ShortPlan short_plan(std::string_view mode, SimTime duration) {
    ShortPlan plan;
    const auto d = duration.milliseconds;
    plan.outcome_offset = d;
    if (mode == "seed" || mode == "funded") {
        plan.funded = mode == "funded";
        const auto depletion = static_cast<std::int64_t>(plan.budget.body_energy_nj);
        if (depletion <= d) {
            plan.outcome_offset = depletion;
            plan.death = DeathCause::EnergyDepleted;
        }
        return plan;
    }
    // ENGINEERING_FIXTURE reserves for exact boundary observations.
    plan.budget.body_energy_nj = static_cast<std::uint64_t>(d + 4);
    plan.budget.hydration_ug = static_cast<std::uint64_t>((d + 1) / hour_ms + 1);
    if (mode == "energy-tie" && duration != legacy_duration) {
        plan.budget.body_energy_nj = static_cast<std::uint64_t>(d);
        plan.death = DeathCause::EnergyDepleted;
    } else if (mode == "water-tie" && duration == legacy_duration) {
        plan.budget.hydration_ug = static_cast<std::uint64_t>(d / hour_ms);
        plan.death = DeathCause::Dehydrated;
    } else if (mode == "interrupted" && duration == legacy_duration) {
        plan.outcome_offset = d - 1;
        plan.death = DeathCause::Fixture;
    } else if (mode != "sentinel") {
        throw std::invalid_argument("unsupported short arm and profile combination");
    }
    return plan;
}

struct FocalWorld {
    WorldRuntime world;
    AntRef egg, queen;
};

constexpr PhysiologySeed queen_budget{{200, 100, 200, 0}, 1500000000, 1600, 0};

ReproductionConfig reserve_mode_one() {
    ReproductionConfig reproduction;
    reproduction.maintenance_horizon = reproduction.interval;
    return reproduction;
}

FocalWorld setup_short(const Profile& profile_row, const ShortPlan& plan, std::uint64_t seed) {
    WorldRuntime world({64, 1}, seed, {}, s6_3_1_fixture::limits());
    world.configure_long_term();
    const auto colony = world.seed_colony();
    if (!plan.funded) {
        const auto egg = world.seed_ant(colony, {{}, LifeStage::Egg, Caste::Worker, 4000});
        enable_seeded_egg(world, egg, plan.budget, profile_row);
        if (plan.death == DeathCause::Fixture)
            world.schedule_lifecycle(egg, {plan.outcome_offset}, LifeStage::Dead);
        return {std::move(world), egg, {}};
    }
    world.configure_social();
    const auto queen = world.seed_ant(colony, {{}, LifeStage::Adult, Caste::Queen, 4000});
    auto config = physiology_config(resolve_egg_duration(profile_row));
    config.adult_protein_target_ug = 20;
    world.enable_physiology(queen, queen_budget, config);
    const auto reproduction = reserve_mode_one();
    world.enable_reproduction(queen, reproduction);
    world.advance_to(reproduction.interval);
    const auto facts = world.committed_events();
    const auto entry = std::find_if(facts.begin(), facts.end(), [](const auto& f) { return f.kind == FactKind::AntBorn; });
    require(entry != facts.end() && entry->time == reproduction.interval && entry->payload == queen.id.value,
            "first funded egg was not committed at the known entry time");
    return {std::move(world), {entry->world, entry->actor}, queen};
}

void observe_focal(std::ostream& out, const WorldRuntime& world, AntRef egg, SimTime duration,
                   const ShortPlan& plan, SimTime terminal, SimTime tick) {
    const auto p = world.query_physiology(egg);
    const auto a = world.query_ant(egg);
    require(p && a && p->config == physiology_config(duration) && p->initial == plan.budget,
            "focal clock, initial budget or identity changed");
    const auto expected = tick < terminal ? LifeStage::Egg
        : (plan.death == DeathCause::None ? LifeStage::Larva : LifeStage::Dead);
    require(a->stage == expected && p->death_cause == (tick < terminal ? DeathCause::None : plan.death),
            "unexpected stage or death cause at boundary");
    if (tick == terminal) {
        const auto spent = static_cast<std::uint64_t>(plan.outcome_offset);
        require(p->updated_at == tick && p->body_energy_nj == plan.budget.body_energy_nj - spent &&
                    p->hydration_ug == plan.budget.hydration_ug - spent / static_cast<std::uint64_t>(hour_ms) &&
                    p->crop == FoodMass{},
                "recorded terminal stores disagree with original rates and fixture reserves");
    }
    const auto state = world.snapshot();
    out << tick.milliseconds << ',' << egg.id.value << ',' << a->born_at.milliseconds << ','
        << p->updated_at.milliseconds << ',' << p->stage_progress.milliseconds << ','
        << p->body_energy_nj << ',' << p->hydration_ug << ',' << static_cast<unsigned>(a->stage) << ','
        << static_cast<unsigned>(p->death_cause) << ',' << p->physiology_event.value << ','
        << state.pending_events << ',' << state.committed_events << ',' << hex64(state.state_hash) << ','
        << hex64(state.trace_hash) << '\n';
}

void run_short(const std::filesystem::path& dir, const Profile& profile_row, SimTime duration,
               const ShortPlan& plan, std::uint64_t seed) {
    auto focal = setup_short(profile_row, plan, seed);
    auto& sliced = focal.world;
    const auto entry = sliced.query_ant(focal.egg)->born_at.milliseconds;
    const SimTime terminal{entry + plan.outcome_offset};
    const auto clock_at = entry + duration.milliseconds;
    const auto end = clock_at + 1;
    const auto middle = entry + plan.outcome_offset / 2 + 1;
    auto reference = setup_short(profile_row, plan, seed);
    reference.world.advance_to({end});
    Publications saves(dir);
    saves.writer.bind(sliced);
    auto states = output(dir / "observations.csv");
    states << "time_ms,egg_id,entry_ms,queried_updated_ms,queried_progress_ms,energy_nj,water_ug,stage_code,death_cause_code,"
              "scheduled_physiology_id,pending,facts,state_hash,trace_hash\n";
    observe_focal(states, sliced, focal.egg, duration, plan, terminal, {entry});

    std::array ticks{middle, terminal.milliseconds - 1, terminal.milliseconds,
                     terminal.milliseconds + 1, clock_at - 1, clock_at, end};
    std::sort(ticks.begin(), ticks.end());
    const auto distinct_end = std::unique(ticks.begin(), ticks.end());
    double advance_ms{};
    for (auto tick = ticks.begin(); tick != distinct_end; ++tick) {
        const auto time = *tick;
        const auto start = Clock::now();
        sliced.advance_to({time});
        advance_ms += elapsed(start);
        observe_focal(states, sliced, focal.egg, duration, plan, terminal, {time});
        if (time == middle) {
            WorldRuntime resumed({64, 1}, seed, {}, s6_3_1_fixture::limits());
            const auto checkpoint = sliced.checkpoint();
            write_bytes(dir / "mid.checkpoint", checkpoint);
            resumed.restore(checkpoint);
            require(resumed.checkpoint() == checkpoint, "mid-egg checkpoint bytes changed");
            exact(sliced, resumed);
            sliced = std::move(resumed);
        }
        if (time == middle || time == terminal.milliseconds) saves.publish(sliced, true, true);
    }

    exact(reference.world, sliced);
    require(reference.world.checkpoint() == sliced.checkpoint(), "short full checkpoint differs");
    const auto saved_terminal = saves.store.recover(focal.egg.world, 1, 2);
    require(saved_terminal.token == saves.previous && saved_terminal.world.summary().now == terminal,
            "terminal published cut is not independently recoverable");
    exact(saves.store.load(focal.egg.world, 2).world, saved_terminal.world);

    EggObserver observer;
    observer.observe(sliced);
    const auto& first = observer.eggs.at(focal.egg.id);
    require(first.terminal && first.terminal->time == terminal &&
                first.terminal->kind == (plan.death == DeathCause::None ? FactKind::StageChanged : FactKind::AntDied),
            "incorrect first committed egg outcome");
    std::size_t hatches{};
    EventId cursor;
    read_facts(sliced, cursor, [&](const WorldEvent& event) {
        if (event.actor != focal.egg.id) return;
        if (event.kind == FactKind::StageChanged && event.stage == LifeStage::Larva) ++hatches;
        if (event.kind == FactKind::PhysiologyUpdated && event.stage == LifeStage::Egg)
            require(event.transferred == FoodMass{}, "egg recorded an absorption transfer");
    });
    require(hatches == (plan.death == DeathCause::None ? 1U : 0U), "egg hatched on a death boundary or more than once");
    observer.write(sliced, dir / "eggs.csv");
    write_facts(sliced, dir / "facts.csv");
    saves.query(saved_terminal.world);
    write_summary(dir, sliced, saves, advance_ms, observer.ms, focal.queen, performance::memory().second);
}

struct Ecology {
    std::string_view id, supply;
    unsigned workers;
    bool depot;
};
constexpr std::array ecology_cases{
    Ecology{"ordinary-8", "balanced", 8, false}, Ecology{"scarce-8", "scarce", 8, false},
    Ecology{"depot-8", "balanced", 8, true}, Ecology{"ordinary-32", "balanced", 32, false},
    Ecology{"scarce-32", "scarce", 32, false}, Ecology{"depot-32", "balanced", 32, true},
};

struct ColonyWorld {
    WorldRuntime world;
    AntRef queen;
};

// Use the public setup sequence of the frozen fixture. It has no application clock input.
ColonyWorld setup_ecology(const Ecology& row, SimTime duration, std::uint64_t seed) {
    WorldRuntime world({63, 1}, seed, {}, s6_3_1_fixture::limits());
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
    const auto queen = world.seed_ant(colony, {{}, LifeStage::Adult, Caste::Queen, 4000});
    auto config = physiology_config(duration);
    config.adult_protein_target_ug = 20;
    world.enable_physiology(queen, queen_budget, config);
    world.enable_reproduction(queen, reserve_mode_one());
    const auto workers = physiology_config(legacy_duration);
    for (unsigned i = 0; i < row.workers; ++i) {
        const auto worker = world.seed_ant(colony, {{}, LifeStage::Adult, Caste::Worker, 4000});
        world.enable_physiology(worker, queen_budget, workers);
        world.set_autonomy(worker);
    }
    if (row.depot) {
        world.seed_food({}, {200000ULL * row.workers, 20000ULL * row.workers, 100000ULL * row.workers, 0});
    } else {
        const auto food = world.seed_food({.02, 0, .01}, {4000, 500, 4000, 0});
        ResourceCycleConfig cycle;
        cycle.reserve = {20000ULL * row.workers, (row.supply == "scarce" ? 50ULL : 2000ULL) * row.workers,
                         5000ULL * row.workers, 0};
        cycle.release_limit = {4000, 400, 2000, 0};
        world.configure_resource_cycle(food, cycle);
    }
    return {std::move(world), queen};
}

void check_frozen_ecology(const Ecology& row, std::uint64_t seed) {
    s6_3_1_fixture::Controls controls;
    controls.positive = row.depot;
    controls.reserve_mode = 1;
    const s6_3_1_fixture::World baseline(seed, row.workers, row.supply, false, {}, 6, false, controls);
    const auto local = setup_ecology(row, legacy_duration, seed);
    require(baseline.world.checkpoint() == local.world.checkpoint() && baseline.queen == local.queen,
            "legacy initialization does not match the frozen S6.3.1 fixture");
}

void run_ecology(const std::filesystem::path& dir, const Ecology& row, SimTime duration,
                 std::uint64_t seed, bool observe) {
    check_frozen_ecology(row, seed);
    auto fixture = setup_ecology(row, duration, seed);
    auto& world = fixture.world;
    const auto end = (row.depot ? 180 : 90) * day_ms;
    Publications saves(dir);
    saves.writer.bind(world);
    EggObserver observer;
    double advance_ms{};
    for (auto t = day_ms; t <= end; t += day_ms) {
        const auto start = Clock::now();
        world.advance_to({t});
        advance_ms += elapsed(start);
        if (t % (10 * day_ms) == 0) {
            if (observe) observer.observe(world);
            saves.publish(world, t == (row.depot ? 90 : 40) * day_ms || t == end);
        }
    }
    saves.query(world);
    const auto online_peak = performance::memory().second;
    auto reference = setup_ecology(row, duration, seed);
    reference.world.advance_to({end});
    exact(reference.world, world);
    if (observe) {
        const auto r = world.query_reproduction(fixture.queen);
        require(r && observer.eggs.size() == r->births, "observer did not account for every committed birth");
        observer.write(world, dir / "eggs.csv");
    }
    write_summary(dir, world, saves, advance_ms, observer.ms, fixture.queen, online_peak);
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 5 || argc > 6)
            throw std::invalid_argument("usage: antworld_s6_4_egg_timing NEW_OUTPUT PROFILE ARM SEED [quiet]");
        const auto& profile_row = profile(argv[2]);
        const auto duration = resolve_egg_duration(profile_row);
        const std::string_view arm = argv[3];
        const auto seed = unsigned_integer(argv[4]);
        const bool observe = argc == 5;
        if (!observe && std::string_view(argv[5]) != "quiet") throw std::invalid_argument("unknown observation mode");
        const auto ecology = std::find_if(ecology_cases.begin(), ecology_cases.end(),
                                          [arm](const auto& row) { return row.id == arm; });
        std::optional<ShortPlan> short_case;
        if (ecology == ecology_cases.end()) {
            if (!observe) throw std::invalid_argument("short arms require observation");
            short_case = short_plan(arm, duration);
        }
        const std::filesystem::path dir = argv[1];
        require(std::filesystem::create_directories(dir), "refusing to overwrite run evidence");
        write_config(dir, profile_row, duration, arm, seed, observe);
        if (short_case)
            run_short(dir, profile_row, duration, *short_case, seed);
        else
            run_ecology(dir, *ecology, duration, seed, observe);
        std::cout << "ENGINEERING_PASS BIOLOGICAL_NOT_VALIDATED\n";
    } catch (const std::exception& error) {
        std::cerr << "ENGINEERING_FAIL " << error.what() << '\n';
        return 1;
    }
}
