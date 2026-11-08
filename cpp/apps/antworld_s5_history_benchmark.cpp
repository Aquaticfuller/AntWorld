#include "antworld/storage/store.hpp"
#include "process_memory.hpp"
#include "s5_fixture.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>

using namespace antworld;
using namespace antworld::storage;
namespace {
using Clock = std::chrono::steady_clock;
template <class F> double measured(F f) {
    const auto at = Clock::now();
    f();
    return std::chrono::duration<double, std::micro>(Clock::now() - at).count();
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc < 2 || argc > 4)
            throw std::invalid_argument(
                "usage: antworld_s5_history_benchmark OUTPUT_DIR [DAYS=365] [EVENTS_PER_DAY=100]");
        const std::filesystem::path dir = argv[1];
        std::filesystem::create_directories(dir);
        const auto days = argc > 2 ? std::stoul(argv[2]) : 365,
                   per_day = argc > 3 ? std::stoul(argv[3]) : 100;
        if (!days || days > 365 || !per_day || per_day > 100)
            throw std::invalid_argument("storage-clock fixture bounds exceeded");
        const auto path = dir / "long-history.sqlite";
        s5_fixture::clean_database(path);
        Store store(path);
        // ENGINEERING_FIXTURE: a storage clock with diagnostic events, not a year of biological ecology.
        WorldRuntime world({5, 365}, 1);
        const auto c = world.seed_colony();
        world.seed_ant(c, {});
        auto token = store.save(world);
        std::ofstream out(dir / "long-history.csv");
        out.exceptions(std::ios::badbit | std::ios::failbit);
        out << std::setprecision(17);
        out << "scope,day,simulation_ms,events,generation,checkpoint_bytes,database_bytes,save_us,load_"
               "validate_us,query_us,resident_bytes,peak_resident_bytes,sqlite_memory_bytes\n";
        for (unsigned long day = 1; day <= days; ++day) {
            const auto start = static_cast<std::int64_t>(day - 1) * 86400000;
            for (unsigned long i = 1; i <= per_day; ++i)
                world.schedule({{start + static_cast<std::int64_t>(i)},
                                Phase::Environment,
                                0,
                                0,
                                i,
                                DiagnosticAction::DrawRandom});
            world.advance_to({static_cast<std::int64_t>(day) * 86400000});
            const auto save = measured([&] { token = store.save(world, token); });
            double restore = -1;
            if (day % 30 == 0 || day == days)
                restore = measured([&] {
                    auto loaded = store.load(token.world);
                    s4_fixture::require(loaded.world.checkpoint() == world.checkpoint(),
                                        "long history restore drift");
                    world = std::move(loaded.world);
                });
            const auto query = measured([&] {
                HistoryFilter filter;
                filter.world = token.world;
                filter.begin = {start};
                filter.end = world.summary().now;
                filter.kind = FactKind::Diagnostic;
                filter.limit = 100;
                s4_fixture::require(store.history(filter).size() == per_day,
                                    "daily factual history query mismatch");
                s4_fixture::require(
                    store.flow_total(token.world, {}, Metric::Deaths, {0}, world.summary().now) == 0,
                    "diagnostic history invented biological deaths");
            });
            const auto [rss, peak] = performance::memory();
            out << "ENGINEERING_STORAGE_CLOCK," << day << ',' << world.summary().now.milliseconds << ','
                << world.summary().committed_events << ',' << token.generation << ','
                << world.checkpoint().size() << ',' << store.database_bytes() << ',' << save << ',' << restore
                << ',' << query << ',' << rss << ',' << peak << ',' << store.sqlite_memory_bytes() << '\n';
        }
        store.checkpoint_wal();
        std::cout << "PASS S5 storage clock " << days << " days, " << world.summary().committed_events
                  << " facts; no ecological year claim\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL: " << e.what() << '\n';
        return 1;
    }
}
