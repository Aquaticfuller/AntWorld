#include "s3_fixture.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#ifdef _WIN32
#define NOMINMAX
// clang-format off
#include <windows.h>
#include <psapi.h>
// clang-format on
#else
#include <sys/resource.h>
#include <unistd.h>
#endif

using namespace antworld;
namespace {
using Clock = std::chrono::steady_clock;
double elapsed(Clock::time_point start) {
  return std::chrono::duration<double, std::milli>(Clock::now() - start)
      .count();
}
std::pair<std::uint64_t, std::uint64_t> memory() {
#ifdef _WIN32
  PROCESS_MEMORY_COUNTERS c{};
  if (!GetProcessMemoryInfo(GetCurrentProcess(), &c, sizeof(c)))
    throw std::runtime_error("memory query failed");
  return {c.WorkingSetSize, c.PeakWorkingSetSize};
#else
  rusage u{};
  if (getrusage(RUSAGE_SELF, &u))
    throw std::runtime_error("memory query failed");
  std::ifstream stat("/proc/self/statm");
  std::uint64_t pages = 0, resident = 0;
  stat >> pages >> resident;
  if (!stat)
    throw std::runtime_error("resident memory unavailable");
  return {resident * static_cast<std::uint64_t>(sysconf(_SC_PAGESIZE)),
          static_cast<std::uint64_t>(u.ru_maxrss) * 1024};
#endif
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc < 2 || argc > 4)
      throw std::invalid_argument(
          "usage: antworld_s6_contact_benchmark OUTPUT_DIR [REPETITIONS=10] "
          "[POPULATION=0(all)]");
    const std::filesystem::path dir = argv[1];
    std::filesystem::create_directories(dir);
    const auto repetitions = argc > 2 ? std::stoul(argv[2]) : 10UL;
    const auto only = argc > 3 ? std::stoul(argv[3]) : 0UL;
    if (!repetitions || repetitions > 100 ||
        (only && only != 128 && only != 512 && only != 2048))
      throw std::invalid_argument("invalid benchmark size");
    std::ofstream out(dir / "contacts.csv");
    out.exceptions(std::ios::badbit | std::ios::failbit);
    out << std::setprecision(17);
    out << "scope,population,layout,policy,seed,repetition,simulation_ms,setup_"
           "ms,advance_ms,encode_ms,restore_ms,checkpoint_bytes,resident_bytes,"
           "peak_resident_bytes,events,pending,decisions,candidates,bucket_"
           "queries,tree_visits,maximum_candidates\n";
    for (unsigned count : {128U, 512U, 2048U}) {
      if (only && only != count)
        continue;
      for (bool dispersed : {false, true})
        for (bool bounded : {false, true})
          for (unsigned rep = 0; rep < repetitions; ++rep) {
            const auto setup_start = Clock::now();
            RuntimeLimits limits;
            limits.events_per_timestamp = 10000;
            limits.committed_events = 200000;
            limits.checkpoint_bytes = 64 * 1024 * 1024;
            WorldRuntime w({6, 6}, 42, {}, limits);
            SocialConfig social;
            social.bounded_contacts = bounded;
            w.configure_social(social);
            const auto c = w.seed_colony();
            std::vector<AntRef> ants(0);
            for (unsigned i = 0; i < count; ++i) {
              const PositionM p =
                  dispersed ? PositionM{static_cast<double>(i % 32) * .01, 0,
                                        static_cast<double>(i / 32) * .01}
                            : PositionM{};
              const auto a = w.seed_ant(c, {p});
              ants.push_back(a);
              w.enable_physiology(a,
                                  {{100, 400, 400, 100}, 1000000000, 1000, 0});
            }
            for (auto a : ants)
              w.set_behavior(a, IndividualBehavior::Nurse);
            const auto setup = elapsed(setup_start);
            const auto start = Clock::now();
            for (std::int64_t t = 1000; t <= 10000; t += 1000)
              w.advance_to({t});
            const auto advance = elapsed(start);
            s3_fixture::balanced(w);
            const auto encode_start = Clock::now();
            const auto bytes = w.checkpoint();
            const auto encode = elapsed(encode_start);
            WorldRuntime restored({9, 9}, 0, {}, limits);
            const auto restore_start = Clock::now();
            restored.restore(bytes);
            const auto restore = elapsed(restore_start);
            s3_fixture::require(bytes == restored.checkpoint(),
                                "contact benchmark restore divergence");
            const auto work = w.contact_work();
            const auto q = w.summary();
            const auto [rss, peak] = memory();
            s3_fixture::require(!bounded || work.maximum_candidates <= 16,
                                "structural contact budget violated");
            out << "ENGINEERING_FIXTURE," << count << ','
                << (dispersed ? "dispersed" : "dense") << ','
                << (bounded ? "bounded" : "exhaustive") << ",42," << rep
                << ",10000," << setup << ',' << advance << ',' << encode << ','
                << restore << ',' << bytes.size() << ',' << rss << ',' << peak
                << ',' << q.committed_events << ',' << q.pending_events << ','
                << work.decisions << ',' << work.candidates_examined << ','
                << work.bucket_queries << ',' << work.tree_visits << ','
                << work.maximum_candidates << '\n';
            out.flush();
          }
    }
    std::cout << "PASS S6 contact benchmark; all samples retained\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
