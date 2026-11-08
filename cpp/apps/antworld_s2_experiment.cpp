#include "s2_fixture.hpp"
#include <charconv>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <locale>

using namespace antworld;
namespace {
std::uint64_t number(std::string_view text) {
    std::uint64_t n = 0; const auto [end, error] = std::from_chars(text.data(), text.data()+text.size(), n);
    if (error != std::errc{} || end != text.data()+text.size() || !n) throw std::invalid_argument("expected positive integer");
    return n;
}
double ratio(std::uint64_t n, std::uint64_t d) { return d ? static_cast<double>(n)/static_cast<double>(d) : 0; }
void header(std::ostream& out) {
    out << "scope,layout,seed,treatment,trails_enabled,memory_enabled,workers,simulated_ms,walkable_cells,visited_cells,coverage,"
        "discovered_sources,first_discovery_ms,first_discoverer,trips_started,collections,collection_attempts,deliveries,"
        "delivery_per_started_trip,collection_success,revisits,mean_outbound_moves_per_collection,distinct_edges,edge_traversals,"
        "edge_reuse_fraction,decisions,moves,explore_moves,trail_moves,memory_moves,return_moves,failed_actions,memory_failures,"
        "available_ug,carried_ug,stored_ug,active_trail_cells,trail_units,deposited_units,evaporated_units\n";
}
void row(std::ostream& out, const fixture::Scene& scene, std::string_view layout, std::uint64_t seed, std::string_view treatment) {
    const auto s = scene.world.surface_snapshot(); const auto c = s.counters; const auto summary = scene.world.summary();
    const auto l = summary.food_ledger;
    for (std::size_t i = 0; i < 4; ++i) {
        const auto initial = l.introduced.components()[i], remaining = l.available.components()[i];
        const auto carried = l.carried.components()[i], stored = l.stored.components()[i];
        if (remaining > initial || carried > initial-remaining || stored != initial-remaining-carried)
            throw std::runtime_error("experiment ingredient conservation failed");
    }
    if ((!s.behavior.trails_enabled && (s.active_trail_cells || c.trail_moves || c.deposited_units != 0)) ||
        (!s.behavior.memory_enabled && c.memory_moves)) throw std::runtime_error("disabled feature leaked into experiment");
    out << "ENGINEERING_FIXTURE," << layout << ',' << seed << ',' << treatment << ',' << s.behavior.trails_enabled << ','
        << s.behavior.memory_enabled << ',' << scene.workers.size() << ',' << summary.now.milliseconds << ','
        << s.walkable_cells << ',' << s.visited_cells << ',' << ratio(s.visited_cells, s.walkable_cells) << ','
        << s.discovered_sources << ',' << s.first_discovery.milliseconds << ',' << s.first_discoverer.value << ','
        << c.trips_started << ',' << c.collections << ',' << c.collection_attempts << ',' << c.deliveries << ','
        << ratio(c.deliveries, c.trips_started) << ',' << ratio(c.collections, c.collection_attempts) << ',' << c.revisits << ','
        << ratio(c.collected_outbound_moves, c.collections) << ',' << s.distinct_edges << ',' << s.edge_traversals << ','
        << ratio(s.edge_traversals-s.distinct_edges, s.edge_traversals) << ',' << c.decisions << ',' << c.moves << ','
        << c.explore_moves << ',' << c.trail_moves << ',' << c.memory_moves << ',' << c.return_moves << ',' << c.failed_actions << ','
        << c.memory_failures << ',' << l.available.total_ug() << ',' << l.carried.total_ug() << ',' << l.stored.total_ug() << ','
        << s.active_trail_cells << ',' << s.trail_units << ',' << c.deposited_units << ',' << s.evaporated_units << '\n';
}
}
int main(int argc, char** argv) {
    try {
        if (argc < 2 || argc > 4) throw std::invalid_argument("usage: antworld_s2_experiment OUTPUT_DIR [SEEDS_1_TO_64] [DURATION_MS]");
        const auto seeds = argc > 2 ? number(argv[2]) : 16;
        const auto duration = argc > 3 ? number(argv[3]) : 1800000;
        if (seeds > 64 || duration > 3600000 || duration % 30000 != 0) throw std::invalid_argument("duration must be a multiple of 30000 ms, at most 3600000 ms");
        std::filesystem::create_directories(argv[1]); const std::filesystem::path root(argv[1]);
        std::ofstream summary(root/"summary.csv"), series(root/"timeseries.csv");
        summary.exceptions(std::ios::badbit | std::ios::failbit); series.exceptions(std::ios::badbit | std::ios::failbit);
        summary.imbue(std::locale::classic()); series.imbue(std::locale::classic());
        summary << std::setprecision(17); series << std::setprecision(17); header(summary); header(series);
        constexpr std::array treatments{"none", "trails", "memory", "both"};
        RuntimeLimits limits; limits.committed_events = 1000000; limits.checkpoint_bytes = 256*1024*1024;
        for (const std::string_view layout : {"open", "barrier"}) for (std::uint64_t seed = 1; seed <= seeds; ++seed) {
            for (std::size_t treatment = 0; treatment < treatments.size(); ++treatment) {
                fixture::Scene scene(seed, (treatment & 1) != 0, (treatment & 2) != 0, layout, 12, false, limits);
                for (std::uint64_t t = 0; t <= duration; t += 30000) {
                    scene.world.advance_to({static_cast<std::int64_t>(t)}); row(series, scene, layout, seed, treatments[treatment]);
                }
                const auto bytes = scene.world.checkpoint(); WorldRuntime restored({8, 9}, 0, {}, limits); restored.restore(bytes);
                if (restored.checkpoint() != bytes) throw std::runtime_error("experiment final checkpoint differs");
                row(summary, scene, layout, seed, treatments[treatment]);
            }
            std::cout << "completed layout=" << layout << " seed=" << seed << " treatments=4\n";
        }
        summary.close(); series.close(); return 0;
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
