#include "antworld/storage/store.hpp"
#include "s5_fixture.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>
#ifdef _WIN32
#define NOMINMAX
// clang-format off: Windows definitions must precede PSAPI declarations.
#include <windows.h>
#include <psapi.h>
// clang-format on
#else
#include <sys/resource.h>
#include <unistd.h>
#endif

using namespace antworld;
using namespace antworld::storage;
using Clock = std::chrono::steady_clock;
namespace {
std::pair<std::uint64_t, std::uint64_t> memory() {
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS counters{};
    if (!GetProcessMemoryInfo(GetCurrentProcess(), &counters, sizeof(counters)))
        throw std::runtime_error("process memory query failed");
    return {counters.WorkingSetSize, counters.PeakWorkingSetSize};
#else
    rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage))
        throw std::runtime_error("process peak memory unavailable");
    std::ifstream stat("/proc/self/statm");
    std::uint64_t pages{}, resident{};
    stat >> pages >> resident;
    if (!stat)
        throw std::runtime_error("resident process memory unavailable");
    return {resident * static_cast<std::uint64_t>(sysconf(_SC_PAGESIZE)),
            static_cast<std::uint64_t>(usage.ru_maxrss) * 1024};
#endif
}
template <class F> double measured(F fn) {
    const auto begin = Clock::now();
    fn();
    return std::chrono::duration<double, std::micro>(Clock::now() - begin).count();
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc < 4 || argc > 5)
            throw std::invalid_argument(
                "usage: antworld_s5_benchmark OUTPUT_DIR EDITS repeated|interleaved [ITERATIONS]");
        const std::filesystem::path dir = argv[1];
        std::filesystem::create_directories(dir);
        const auto edits = static_cast<unsigned>(std::stoul(argv[2]));
        const std::string condition = argv[3];
        if (condition != "repeated" && condition != "interleaved")
            throw std::invalid_argument("unknown geometry condition");
        const unsigned iterations = argc == 5 ? static_cast<unsigned>(std::stoul(argv[4])) : 10;
        if (!iterations || iterations > 100 || edits > 10000)
            throw std::invalid_argument("benchmark bound exceeded");
        s5_fixture::History fixture;
        const auto setup = measured([&] { fixture.append(edits, condition == "interleaved"); });
        auto &w = fixture.world;
        s4_fixture::balanced(w);
        const auto bytes = w.checkpoint();
        const auto material = w.geometry_snapshot();
        const auto original_route =
            w.query_route(fixture.first, s4_fixture::position({6, 6, 6}, fixture.geometry));
        std::ofstream out(dir / (condition + "-" + std::to_string(edits) + ".csv"));
        out.exceptions(std::ios::badbit | std::ios::failbit);
        out << std::setprecision(17);
        out << "scope,condition,edits,iteration,operation,elapsed_us,checkpoint_bytes,database_bytes,sqlite_"
               "memory_bytes,resident_bytes,peak_resident_bytes,index_entries,events,setup_us\n";
        auto row = [&](unsigned iteration, const char *operation, double elapsed, std::uint64_t database = 0,
                       std::uint64_t sqlite = 0) {
            const auto [rss, peak] = memory();
            out << "ENGINEERING_FIXTURE," << condition << ',' << edits << ',' << iteration << ',' << operation
                << ',' << elapsed << ',' << bytes.size() << ',' << database << ',' << sqlite << ',' << rss
                << ',' << peak << ',' << material.indexed_entries << ',' << w.summary().committed_events
                << ',' << setup << '\n';
        };
        for (unsigned iteration = 0; iteration < iterations; ++iteration) {
            std::vector<std::uint8_t> encoded(0);
            const auto encode_time = measured([&] { encoded = w.checkpoint(); });
            row(iteration, "checkpoint_encode", encode_time);
            WorldRuntime decoded({5, 51}, 0);
            const auto restore_time = measured([&] { decoded.restore(bytes); });
            row(iteration, "checkpoint_restore", restore_time);
            s4_fixture::require(decoded.checkpoint() == bytes, "core restore changed authority");
            const auto path =
                dir / (condition + "-" + std::to_string(edits) + "-" + std::to_string(iteration) + ".sqlite");
            s5_fixture::clean_database(path);
            {
                Store store(path);
                SaveToken token;
                const auto write = measured([&] { token = store.save(w); });
                row(iteration, "durable_save", write, store.database_bytes(), store.sqlite_memory_bytes());
                const auto load = measured([&] {
                    auto recovered = store.load(token.world);
                    s4_fixture::require(recovered.world.checkpoint() == bytes,
                                        "durable restore changed authority");
                    s4_fixture::require(
                        recovered.world
                                .query_route(fixture.first, s4_fixture::position({6, 6, 6}, fixture.geometry))
                                .points == original_route.points,
                        "connectivity changed on durable restore");
                });
                row(iteration, "durable_load_validate", load, store.database_bytes(),
                    store.sqlite_memory_bytes());
                const auto query = measured([&] {
                    HistoryFilter filter;
                    filter.world = token.world;
                    filter.individual = fixture.second.id;
                    filter.limit = 25;
                    (void)store.history(filter);
                    const auto dry =
                        store.flow_total(token.world, {}, Metric::ExcavatedDry, {0}, {fixture.time + 1});
                    s4_fixture::require(dry == material.ledger.excavated_q3 * material.config.dry_ug_per_q3,
                                        "flow metric differs from soil ledger");
                });
                row(iteration, "indexed_history_and_flow_query", query, store.database_bytes(),
                    store.sqlite_memory_bytes());
                store.checkpoint_wal();
                row(iteration, "post_wal_checkpoint_size", 0, store.database_bytes(),
                    store.sqlite_memory_bytes());
            }
            s5_fixture::clean_database(path);
        }
        std::cout << "PASS S5 performance " << condition << ' ' << edits << " edits; SQLite "
                  << Store::sqlite_version() << '\n';
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL: " << e.what() << '\n';
        return 1;
    }
}
