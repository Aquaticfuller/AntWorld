#include "rm02_fixtures.hpp"
#include "s6_3_benchmark_clock.hpp"
#include "process_memory.hpp"
#include "history_digest.hpp"
#ifdef ANTWORLD_WP2_BENCHMARK
#include "s6_3_3_3_fixture.hpp"
#endif
#ifdef ANTWORLD_WP4_BENCHMARK
#include "wp4_lineage.hpp"
#endif
#ifdef ANTWORLD_WP5_BENCHMARK
#include "wp5_geometry_view.hpp"
#endif

#include <fstream>
#include <iomanip>
#include <iostream>

namespace {
using namespace antworld;
using namespace antworld::rm02;
using s6_3_benchmark::Stamp;
using Clock = std::chrono::steady_clock;
using s3_fixture::require;

double elapsed(Clock::time_point begin, Clock::time_point end = Clock::now()) {
    return std::chrono::duration<double, std::milli>(end - begin).count();
}

void run(const std::filesystem::path& folder, WorldRuntime& world, std::vector<EntityId> focal,
         RuntimeLimits limits, bool on, bool dense, Clock::time_point started, bool care = false) {
    const auto setup = elapsed(started);
    const auto step = dense || care ? 1000 : s6_3_1_fixture::day;
    const auto end = care ? 60000 : dense ? 10000 : 90 * s6_3_1_fixture::day;
    const auto database = folder / "observer.sqlite";
    const auto init_begin = Clock::now();
    std::unique_ptr<Observer> observer;
#ifdef ANTWORLD_WP5_BENCHMARK
    std::unique_ptr<std::ofstream> spatial;
    const AntRef geometry_focal{world.summary().world, focal.front()};
    const auto target = wp5::physical({18, 12, 12}, world.geometry_snapshot().config);
#endif
#ifdef ANTWORLD_WP4_BENCHMARK
    std::unique_ptr<wp4::Lineage> lineage;
#endif
    if (on) {
        Plan plan{"performance", std::move(focal), {}, !dense};
#if defined(ANTWORLD_WP2_BENCHMARK) || defined(ANTWORLD_WP4_BENCHMARK)
        plan.activity_care = true;
#endif
#ifdef ANTWORLD_WP3_BENCHMARK
        plan.foraging = true;
#endif
        observer = std::make_unique<Observer>(database, world, std::move(plan));
        observer->start_background();
#ifdef ANTWORLD_WP5_BENCHMARK
        if (!dense) spatial = std::make_unique<std::ofstream>(wp4::output(folder / "geometry.csv"));
#endif
#ifdef ANTWORLD_WP4_BENCHMARK
        if (!dense) lineage = std::make_unique<wp4::Lineage>(folder);
#endif
    }
    const auto init = elapsed(init_begin);
    struct Captured {
        double read_ms, write_ms;
        std::int64_t sim_ms;
        std::uint64_t cursor, examined, selected, records, dropped, payload;
#ifdef ANTWORLD_WP4_BENCHMARK
        std::size_t lineage_bytes;
#endif
#ifdef ANTWORLD_WP5_BENCHMARK
        std::size_t probe_bytes;
#endif
    };
    std::vector<Captured> cuts;
    cuts.reserve(dense ? 1 : 91);
    const auto observe = [&] {
        const auto begin = Clock::now();
        auto cut = observer->capture();
        const auto payload = cut.payload.size();
#ifdef ANTWORLD_WP4_BENCHMARK
        const auto lineage_bytes = lineage ? lineage->capture(world, cuts.size() + 1, cut.end.cursor, cut.end.time) : 0;
#endif
#ifdef ANTWORLD_WP5_BENCHMARK
        const auto probe_bytes = spatial ? wp5::probe(*spatial, world, geometry_focal, target) : 0;
#endif
        const auto middle = Clock::now();
        observer->submit(std::move(cut));
        const auto finish = Clock::now();
        cuts.push_back({elapsed(begin, middle), elapsed(middle, finish), cut.end.time.milliseconds,
                        cut.end.cursor, cut.examined, cut.selected, cut.records, cut.dropped, payload
#ifdef ANTWORLD_WP4_BENCHMARK
                        , lineage_bytes
#endif
#ifdef ANTWORLD_WP5_BENCHMARK
                        , probe_bytes
#endif
                        });
    };
    double advance{};
    const Stamp begin;
    if (on && !dense)
        observe();
    for (std::int64_t t = step; t <= end; t += step) {
        const auto start = Clock::now();
        world.advance_to({t});
        advance += elapsed(start);
        if (on && (care ? t % 10000 == 0 : !dense || t == end))
            observe();
    }
    const auto flush_begin = Clock::now();
    if (on) {
        observer->flush();
        require(observer->committed_cuts() == cuts.size(), "unpublished benchmark cut");
    }
#ifdef ANTWORLD_WP4_BENCHMARK
    if (lineage) lineage->close();
#endif
#ifdef ANTWORLD_WP5_BENCHMARK
    if (spatial) spatial->close();
#endif
    const auto flush_ms = elapsed(flush_begin);
    const Stamp finish;
    const auto background = on ? observer->background_stats() : BackgroundStats{};
    const auto [rss, peak] = performance::memory();
    const auto state = world.snapshot();
    const auto work = world.contact_work();
    const auto ledger = world.nutrition_snapshot();
    const bool conserved = ledger.introduced == ledger.accounted &&
                           ledger.energy_input_nj >= ledger.body_energy_nj &&
                           ledger.energy_input_nj - ledger.body_energy_nj == ledger.dissipated_energy_nj;
    const auto checkpoint_begin = Clock::now();
    const auto checkpoint = world.checkpoint();
    const auto checkpoint_ms = elapsed(checkpoint_begin);
    WorldRuntime restored({91, 3}, 1, {}, limits);
    const auto restore_begin = Clock::now();
    restored.restore(checkpoint);
    const auto restore_ms = elapsed(restore_begin);
    require(restored.checkpoint() == checkpoint, "benchmark restore diverged");
    restored.advance_to({end + step});
    world.advance_to({end + step});
    require(restored.checkpoint() == world.checkpoint(), "benchmark continuation diverged");
    require(conserved, "benchmark conservation failed");
    const auto wal_bytes = on ? std::filesystem::file_size(folder / "observer.sqlite-wal") : 0;
    observer.reset();
    const auto disk = on ? std::filesystem::file_size(database) : 0;
    auto open = [&](const char* name) {
        std::ofstream output(folder / name, std::ios::binary);
        output.exceptions(std::ios::badbit | std::ios::failbit);
        output << std::setprecision(17);
        return output;
    };
    auto summary = open("sample.csv");
    summary << "setup_ms,observer_init_ms,advance_ms,total_ms,start_utc_ns,end_utc_ns,cpu_ns,cycles,"
               "start_processor,end_processor,checkpoint_ms,restore_ms,rss_bytes,peak_rss_bytes,sqlite_bytes,wal_bytes_at_cut,"
               "flush_ms,background_write_ms,peak_queue_bytes,"
               "sim_ms,events,pending,decisions,candidates,bucket_queries,tree_visits,maximum_candidates,"
               "state_hash,trace_hash,checkpoint_bytes,checkpoint_sha256,exact_restore,conserved\n"
            << setup << ',' << init << ',' << advance << ',' << elapsed(begin.wall, finish.wall)
            << ',' << begin.utc << ',' << finish.utc << ',' << finish.cpu - begin.cpu
            << ',' << finish.cycles - begin.cycles << ',' << begin.processor << ',' << finish.processor
            << ',' << checkpoint_ms << ',' << restore_ms << ',' << rss << ',' << peak << ',' << disk
            << ',' << wal_bytes << ',' << flush_ms << ',' << background.write_ms << ',' << background.peak_payload_bytes << ','
            << end << ',' << state.committed_events << ',' << state.pending_events << ',' << work.decisions
            << ',' << work.candidates_examined << ',' << work.bucket_queries << ',' << work.tree_visits
            << ',' << work.maximum_candidates << ',' << state.state_hash << ',' << state.trace_hash
            << ',' << checkpoint.size() << ',' << std::hex << std::setfill('0');
    for (const auto byte : storage::detail::sha256(checkpoint))
        summary << std::setw(2) << static_cast<unsigned>(byte);
    summary << ",1,1\n";
    auto detail = open("captures.csv");
    detail << "sim_ms,capture_ms,publish_ms,cursor,examined,selected,records,dropped,payload_bytes";
#ifdef ANTWORLD_WP4_BENCHMARK
    detail << ",lineage_bytes";
#endif
#ifdef ANTWORLD_WP5_BENCHMARK
    detail << ",probe_bytes";
#endif
    detail << '\n';
    for (const auto& row : cuts) {
        detail << row.sim_ms << ',' << row.read_ms << ',' << row.write_ms << ',' << row.cursor << ','
               << row.examined << ',' << row.selected << ',' << row.records << ',' << row.dropped << ','
               << row.payload;
#ifdef ANTWORLD_WP4_BENCHMARK
        detail << ',' << row.lineage_bytes;
#endif
#ifdef ANTWORLD_WP5_BENCHMARK
        detail << ',' << row.probe_bytes;
#endif
        detail << '\n';
    }
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 5, "usage: antworld_s6_4_rm02_benchmark FOLDER CELL ARM AFFINITY_MASK");
        const std::filesystem::path folder = argv[1];
        const std::string_view cell = argv[2], arm = argv[3];
        require(arm == "on" || arm == "off", "invalid observer arm");
        const auto mask = std::stoull(argv[4]);
#ifdef _WIN32
        if (mask)
            require(SetProcessAffinityMask(GetCurrentProcess(), mask) != 0, "cannot set benchmark affinity");
#else
        require(mask == 0, "portable runs require external affinity");
#endif
        require(std::filesystem::create_directories(folder), "new performance sample folder required");
        const auto begin = Clock::now();
#ifdef ANTWORLD_WP2_BENCHMARK
        if (cell == "care8") {
            auto world = antworld::closure::density_world(8, true, false, true);
            std::vector<EntityId> focal;
            for (const auto& ant : world.ant_states())
                focal.push_back(ant.id);
            run(folder, world, std::move(focal), antworld::closure::limits(), arm == "on", false, begin, true);
            return 0;
        }
#endif
        if (cell == "depot32") {
            auto fixture = ecology_fixture(1, 32, "depot");
            run(folder, fixture.world, ecology_focal(fixture), s6_3_1_fixture::limits(), arm == "on", false, begin);
        } else {
            require(cell == "dense512" || cell == "dense2048", "invalid benchmark cell");
            DenseFixture fixture(cell == "dense512" ? 512 : 2048, 42);
            run(folder, fixture.world, std::move(fixture.focal), contact_limits(), arm == "on", true, begin);
        }
    } catch (const std::exception& error) {
        std::cerr << "RM-02 benchmark: " << error.what() << '\n';
        return 1;
    }
}
