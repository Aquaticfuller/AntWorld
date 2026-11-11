#include "rm02_fixtures.hpp"
#include "s6_3_3_fixture.hpp"
#include "s6_3_3_3_fixture.hpp"
#include "process_memory.hpp"

#include <charconv>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>

namespace {
using namespace antworld;
using namespace antworld::rm02;
using Clock = std::chrono::steady_clock;
using s3_fixture::require;
constexpr auto hour = s6_3_1_fixture::hour;
constexpr auto day = s6_3_1_fixture::day;
constexpr std::int64_t second = 1000;

struct Case {
    std::string_view mode, arm, layout, origin;
    unsigned workers, brood;
    std::uint64_t seed;
};

struct Timeline {
    std::int64_t end, step, cut, restart, input_at{};
};

std::ofstream output(const std::filesystem::path& path) {
    std::ofstream stream(path, std::ios::binary);
    stream.exceptions(std::ios::failbit | std::ios::badbit);
    stream << std::setprecision(17);
    return stream;
}

void checkpoint_file(const std::filesystem::path& path, std::span<const std::uint8_t> bytes) {
    auto stream = output(path);
    stream.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    stream.close();
}

double ms(Clock::time_point since) {
    return std::chrono::duration<double, std::milli>(Clock::now() - since).count();
}

std::uint64_t number(std::string_view text) {
    std::uint64_t result{};
    const auto parsed = std::from_chars(text.data(), text.data() + text.size(), result);
    require(parsed.ec == std::errc{} && parsed.ptr == text.data() + text.size(), "invalid integer");
    return result;
}

void no_input(WorldRuntime&) {}

template <class Input, class Advance, class Capture>
void drive(WorldRuntime& world, Timeline timeline, Input input, Advance advance, Capture capture) {
    if (timeline.input_at == 0)
        input(world);
    capture(0);
    for (auto time = timeline.step; time <= timeline.end; time += timeline.step) {
        advance(time);
        if (time == timeline.input_at)
            input(world);
        if (time % timeline.cut == 0)
            capture(time);
    }
}

template <class Input>
void assay(const std::filesystem::path& dir, const Case& c, WorldRuntime& world, RuntimeLimits limits,
           Timeline timeline, Input input) {
    const auto initial = world.checkpoint();
    checkpoint_file(dir / "initial.chk", initial);
    auto config = output(dir / "configuration.csv");
    config << "mode,arm,workers,seed,layout,brood,origin,world_id,horizon_ms,step_ms,cut_ms,midpoint_ms,input_ms,classification\n"
           << c.mode << ',' << c.arm << ',' << c.workers << ',' << c.seed << ',' << c.layout << ','
           << c.brood << ',' << c.origin << ',' << world.summary().world.str() << ',' << timeline.end
           << ',' << timeline.step << ',' << timeline.cut << ',' << timeline.restart << ',' << timeline.input_at
           << ",ENGINEERING_FIXTURE\n";
    config.close();
    auto start_state = output(dir / "initial_ants.csv");
    start_state << "entity,colony,stage,caste,x_m,y_m,z_m,physiology,basal_nj_per_ms,active_nj_per_ms,"
                   "water_loss_ug_per_period,water_loss_period_ms,absorption_period_ms\n";
    Plan plan{"activity-care", {}, {}, true};
    plan.activity_care = true;
    const auto world_id = world.summary().world;
    for (const auto& ant : world.ant_states()) {
        plan.focal.push_back(ant.id);
        const auto p = world.query_physiology({world_id, ant.id});
        start_state << ant.id.value << ',' << ant.colony.value << ',' << static_cast<unsigned>(ant.stage)
                    << ',' << static_cast<unsigned>(ant.caste) << ',' << ant.position.x << ','
                    << ant.position.y << ',' << ant.position.z << ',' << static_cast<bool>(p) << ',';
        if (p)
            start_state << p->config.basal_nj_per_ms << ',' << p->config.active_nj_per_ms << ','
                        << p->config.water_loss_ug_per_period << ',' << p->config.water_loss_period.milliseconds
                        << ',' << p->config.absorption_period.milliseconds;
        else
            start_state << ",,,,";
        start_state << '\n';
    }
    start_state.close();
    const auto database = dir / "observer.sqlite";
    auto reader = std::make_unique<Observer>(database, world, plan);
    reader->start_background();
    auto cuts = output(dir / "cuts.csv");
    cuts << "sim_ms,cursor,examined,selected,records,dropped,payload_bytes,capture_ms,submission_ms,"
            "soil_initial_q3,soil_remaining_q3,soil_carried_q3,soil_deposited_q3\n";
    std::size_t captured{};
    double advance_ms{}, flush_ms{}, writer_ms{}, midpoint_ms{};
    std::size_t peak_queued{};
    auto drain = [&] {
        const auto begin = Clock::now();
        reader->flush();
        require(reader->committed_cuts() == captured, "unpublished WP-2 cut");
        flush_ms += ms(begin);
        const auto stats = reader->background_stats();
        writer_ms += stats.write_ms;
        peak_queued = std::max(peak_queued, stats.peak_payload_bytes);
    };
    auto advance = [&](std::int64_t time) {
        const auto begin = Clock::now();
        world.advance_to({time});
        advance_ms += ms(begin);
    };
    auto capture = [&](std::int64_t time) {
        const auto begin = Clock::now();
        auto cut = reader->capture();
        const auto capture_ms = ms(begin);
        const auto size = cut.payload.size();
        require(!cut.dropped && cut.end.time.milliseconds == time, "incomplete WP-2 capture");
        const auto submit = Clock::now();
        reader->submit(std::move(cut));
        const auto submission_ms = ms(submit);
        ++captured;
        const auto soil = world.geometry_snapshot().ledger;
        require(soil.initial_q3 == soil.remaining_q3 + soil.carried_q3 + soil.deposited_q3, "soil ledger mismatch");
        cuts << time << ',' << cut.end.cursor << ',' << cut.examined << ',' << cut.selected << ','
             << cut.records << ',' << cut.dropped << ',' << size << ',' << capture_ms << ',' << submission_ms
             << ',' << soil.initial_q3 << ',' << soil.remaining_q3 << ',' << soil.carried_q3 << ',' << soil.deposited_q3 << '\n';
        if (time == timeline.restart) {
            drain();
            const auto begin_restore = Clock::now();
            const auto checkpoint = world.checkpoint();
            checkpoint_file(dir / "midpoint.chk", checkpoint);
            reader->anchor(checkpoint);
            reader.reset();
            world.restore(checkpoint);
            require(world.checkpoint() == checkpoint, "WP-2 checkpoint failed midpoint round trip");
            reader = std::make_unique<Observer>(database, world, plan, checkpoint);
            require(reader->publish(reader->capture()) == Publish::Duplicate, "WP-2 midpoint repeated a cut");
            reader->start_background();
            midpoint_ms = ms(begin_restore);
        }
    };
    const auto begin = Clock::now();
    drive(world, timeline, input, advance, capture);
    drain();
    const auto timed_wall = ms(begin);
    const auto [rss, peak] = performance::memory();
    cuts.close();
    const auto final = world.checkpoint();
    checkpoint_file(dir / "final.chk", final);
    reader->anchor(final);
    const auto wal = std::filesystem::file_size(database.string() + "-wal");
    reader.reset();
    const auto disk = std::filesystem::file_size(database);

    WorldRuntime off({642, 0}, c.seed, {}, limits);
    off.restore(initial);
    drive(off, timeline, input, [&](auto time) { off.advance_to({time}); }, [](auto) {});
    require(off.checkpoint() == final, "WP-2 observed/restored and matched observer-off checkpoint differ");
    const auto state = world.snapshot();
    auto result = output(dir / "summary.csv");
    result << "status,events,cuts,living,individuals,state_hash,trace_hash,rng,observer_off_equal,midpoint_rejoined,"
              "advance_ms,wall_including_midpoint_ms,midpoint_ms,terminal_and_mid_drain_ms,writer_ms,peak_queued_bytes,"
              "rss_bytes,peak_rss_bytes,closed_database_bytes,wal_at_end_bytes\n"
           << "PASS," << state.committed_events << ',' << captured << ',' << state.living_ants << ',' << state.ant_count
           << ',' << state.state_hash << ',' << state.trace_hash << ',' << state.rng_state << ",1,1,"
           << advance_ms << ',' << timed_wall << ',' << midpoint_ms << ',' << flush_ms << ',' << writer_ms
           << ',' << peak_queued << ',' << rss << ',' << peak << ',' << disk << ',' << wal << '\n';
    result.close();
}

void social_care(const std::filesystem::path& dir, const Case& c) {
    const bool barrier = c.arm == "barrier";
    auto profile = closure::timed_care(false);
    s6_3_3_fixture::Fixture f(c.seed, profile, c.brood, c.workers, barrier, CareContext::FoundingQueen,
                            {(barrier ? 52 : 55) * day}, true, c.arm == "added");
    const auto input = [&](WorldRuntime& w) {
        if (c.arm == "added" || c.arm == "removed" || c.arm == "sham")
            for (auto worker : f.workers)
                w.submit({worker, {3 * day + 10 * second}, ActionKind::Move, {},
                          c.arm == "removed" ? PositionM{.02, 0, .02} : PositionM{0, 0, -.00025}, 0});
    };
    const auto half_hour = hour / 2;
    const Timeline time = barrier ? Timeline{25 * hour, half_hour, half_hour, 12 * hour}
                                  : Timeline{121 * hour, half_hour, half_hour, 60 * hour, 3 * day};
    assay(dir, c, f.w, s6_3_3_fixture::limits(), time, input);
}

void retrieval(const std::filesystem::path& dir, const Case& c) {
    const auto profile = closure::timed_care(false);
    const EnvironmentCareProfile environment{21, .8, true, .025};
    s6_3_3_fixture::Fixture f(c.seed, profile, 0, c.workers, c.layout == "wall", CareContext::FoundingQueen,
                            {4752000000LL}, true, false, environment, .08, {}, false);
    const auto foreign = f.w.seed_colony({.02, 0, 0});
    f.w.pause_brood_care(f.queen);
    const auto p = s6_3_3_fixture::physiology();
    for (auto worker : f.workers)
        f.w.enable_physiology(worker, {{0, 100, 0, 0}, p.energy_capacity_nj, p.hydration_capacity_ug, 0}, p);
    for (unsigned i = 0; i < c.brood; ++i) {
        PositionM location{(c.layout == "far" ? .009 : .005) + static_cast<double>(i) * .002, 0, 0};
        if (c.layout == "split" && i >= 3)
            location = {0, 0, -(.005 + static_cast<double>(i - 3) * .002)};
        f.w.seed_ant(c.origin == "foreign" ? foreign : f.colony,
                     {location, i % 2 ? LifeStage::Pupa : LifeStage::Larva});
    }
    const auto input = [&](WorldRuntime& w) {
        if (f.workers.empty())
            w.enable_brood_care(f.queen, {CareContext::FoundingQueen, {4752000000LL}});
        else
            for (const auto worker : f.workers)
                w.enable_brood_care(worker, {CareContext::Worker, {30 * day}});
    };
    assay(dir, c, f.w, s6_3_3_fixture::limits(), {780 * second, 30 * second, 30 * second, 480 * second, 180 * second}, input);
}

void dispatch(const std::filesystem::path& dir, const Case& c) {
    if (c.mode == "activity") {
        require((c.workers == 8 || c.workers == 32) && !c.brood && c.layout == c.arm &&
                c.origin == (c.arm == "depot" || c.arm == "ordinary" ? "balanced" : c.arm), "invalid activity assay");
        auto fixture = ecology_fixture(c.seed, c.workers, c.arm);
        assay(dir, c, fixture.world, s6_3_1_fixture::limits(), {90 * day, day, day, 45 * day}, no_input);
    } else if (c.mode == "integrated") {
        require((c.workers == 4 || c.workers == 16) && c.brood == 4 && c.layout == "underground" &&
                (c.arm == "care" || c.arm == "control") && (c.origin == "balanced" || c.origin == "empty"),
                "invalid integrated assay");
        WorldRuntime world({6333, c.seed}, c.seed, {{-.04, -.02, -.02}, {.04, .02, .02}, .08, .002, true}, closure::limits());
        closure::prepare_ecology(world, c.workers, "underground", c.origin == "balanced", c.arm == "care");
        assay(dir, c, world, closure::limits(), {21 * day, 6 * hour, day, 10 * day}, no_input);
    } else if (c.mode == "b01") {
        const bool with_workers = c.arm == "added" || c.arm == "removed" || c.arm == "sham";
        require(c.origin == "own" && ((c.arm == "barrier" && c.workers == 3 && c.brood == 5 && c.layout == "wall") ||
                (c.layout == "plain" && ((with_workers && c.workers == 5 && c.brood == 5) ||
                  (c.arm == "absent" && !c.workers && c.brood == 5) ||
                  (c.arm == "no_brood" && !c.workers && !c.brood)))), "invalid B01 assay");
        social_care(dir, c);
    } else if (c.mode == "b02") {
        require(((c.arm == "queen" && !c.workers) || (c.arm == "trio" && c.workers == 3)) &&
                ((c.brood == 6 && (c.layout == "line" || c.layout == "split" || c.layout == "far" || c.layout == "wall") &&
                  (c.origin == "own" || c.origin == "foreign")) ||
                 ((c.brood == 0 || c.brood == 1) && c.layout == "line" && c.origin == "own")), "invalid B02 assay");
        retrieval(dir, c);
    } else
        throw std::invalid_argument("unknown WP-2 assay");
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 9, "usage: antworld_s6_4_wp2 OUTPUT MODE ARM WORKERS SEED LAYOUT BROOD ORIGIN");
        const auto workers = number(argv[4]), brood = number(argv[7]);
        require(workers <= 32 && brood <= 6, "WP-2 fixture size is out of range");
        const auto seed = number(argv[5]);
        require(seed != 0, "expected positive fixture seed");
        const Case c{argv[2], argv[3], argv[6], argv[8], static_cast<unsigned>(workers),
                     static_cast<unsigned>(brood), seed};
        const std::filesystem::path dir = argv[1];
        require(std::filesystem::create_directories(dir), "WP-2 output must be new");
        dispatch(dir, c);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "WP-2 assay: " << error.what() << '\n';
        return 1;
    }
}
