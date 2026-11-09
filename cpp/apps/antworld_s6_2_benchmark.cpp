#include "antworld/core/profiling.hpp"
#include "s3_fixture.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <thread>
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
using s3_fixture::require;
namespace {
struct Stamp {
  std::chrono::steady_clock::time_point wall{std::chrono::steady_clock::now()};
  std::int64_t utc{std::chrono::duration_cast<std::chrono::nanoseconds>(
                       std::chrono::system_clock::now().time_since_epoch())
                       .count()};
  std::uint64_t cpu{}, cycles{};
  unsigned processor{};
  Stamp() {
#ifdef _WIN32
    FILETIME created{}, exited{}, kernel{}, user{};
    require(
        GetProcessTimes(GetCurrentProcess(), &created, &exited, &kernel, &user),
        "CPU time unavailable");
    auto value = [](FILETIME t) {
      return (static_cast<std::uint64_t>(t.dwHighDateTime) << 32) |
             t.dwLowDateTime;
    };
    cpu = (value(kernel) + value(user)) * 100;
    require(QueryProcessCycleTime(GetCurrentProcess(), &cycles),
            "CPU cycles unavailable");
    processor = GetCurrentProcessorNumber();
#else
    rusage usage{};
    require(getrusage(RUSAGE_SELF, &usage) == 0, "CPU time unavailable");
    cpu = static_cast<std::uint64_t>(usage.ru_utime.tv_sec +
                                     usage.ru_stime.tv_sec) *
              1000000000 +
          static_cast<std::uint64_t>(usage.ru_utime.tv_usec +
                                     usage.ru_stime.tv_usec) *
              1000;
#endif
  }
};
std::pair<std::uint64_t, std::uint64_t> memory() {
#ifdef _WIN32
  PROCESS_MEMORY_COUNTERS counters{};
  require(
      GetProcessMemoryInfo(GetCurrentProcess(), &counters, sizeof(counters)),
      "memory unavailable");
  return {counters.WorkingSetSize, counters.PeakWorkingSetSize};
#else
  rusage usage{};
  require(getrusage(RUSAGE_SELF, &usage) == 0, "memory unavailable");
  std::ifstream file("/proc/self/statm");
  std::uint64_t pages{}, resident{};
  file >> pages >> resident;
  require(static_cast<bool>(file), "resident memory unavailable");
  return {resident * static_cast<std::uint64_t>(sysconf(_SC_PAGESIZE)),
          static_cast<std::uint64_t>(usage.ru_maxrss) * 1024};
#endif
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc != 4)
      throw std::invalid_argument("usage: antworld_s6_2_benchmark OUTPUT_DIR "
                                  "SCHEDULE_CSV AFFINITY_MASK");
    const std::filesystem::path dir = argv[1];
    require(!std::filesystem::exists(dir / "contacts.csv"),
            "refusing to overwrite evidence");
    std::filesystem::create_directories(dir);
    const auto mask = std::stoull(argv[3]);
#ifdef _WIN32
    if (mask)
      require(SetProcessAffinityMask(GetCurrentProcess(), mask),
              "cannot set benchmark affinity");
#else
    require(
        !mask,
        "this portable runner requires external affinity on non-Windows hosts");
#endif
    std::ifstream input(argv[2]);
    require(static_cast<bool>(input), "schedule unavailable");
    std::string line;
    std::getline(input, line);
    if (!line.empty() && line.back() == '\r')
      line.pop_back();
    require(line == "sample,session,block,slot,warmup,population,layout,policy",
            "invalid schedule header");
    std::ofstream out(dir / "contacts.csv"), phases(dir / "phases.csv"),
        profiles(dir / "profile.csv");
    for (auto *f : {&out, &phases, &profiles}) {
      f->exceptions(std::ios::badbit | std::ios::failbit);
      *f << std::setprecision(17);
    }
    out << "sample,session,block,slot,warmup,population,layout,policy,seed,"
           "simulation_ms,setup_ms,advance_ms,encode_ms,restore_ms,checkpoint_"
           "bytes,resident_bytes,peak_resident_bytes,events,pending,decisions,"
           "candidates,bucket_queries,tree_visits,maximum_candidates,state_"
           "hash,trace_hash,continuation_equal,instrumented,affinity_mask\n";
    phases << "sample,phase,start_utc_ns,end_utc_ns,wall_ms,cpu_ms,cycles,"
              "start_processor,end_processor\n";
    profiles << "sample,phase,category,calls,inclusive_ns,exclusive_ns\n";
    unsigned expected{};
    while (std::getline(input, line)) {
      if (!line.empty() && line.back() == '\r')
        line.pop_back();
      if (line.empty())
        continue;
      std::stringstream row(line);
      std::vector<std::string> fields;
      std::string field;
      while (std::getline(row, field, ','))
        fields.push_back(field);
      require(fields.size() == 8 && std::stoul(fields[0]) == expected++,
              "invalid sample sequence");
      const auto count = std::stoul(fields[5]);
      require(count == 128 || count == 512 || count == 2048,
              "invalid population");
      require(fields[6] == "dense" || fields[6] == "dispersed",
              "invalid layout");
      require(fields[7] == "bounded" || fields[7] == "exhaustive",
              "invalid policy");
      const bool dispersed = fields[6] == "dispersed",
                 bounded = fields[7] == "bounded";
      auto finish = [&](const char *phase, const Stamp &before) {
        const Stamp after;
        const auto wall =
            std::chrono::duration<double, std::milli>(after.wall - before.wall)
                .count();
        phases << fields[0] << ',' << phase << ',' << before.utc << ','
               << after.utc << ',' << wall << ','
               << static_cast<double>(after.cpu - before.cpu) / 1000000 << ','
               << after.cycles - before.cycles << ',' << before.processor << ','
               << after.processor << '\n';
        const auto values = profiling::snapshot();
        for (std::size_t i = 0; i < values.size(); ++i)
          profiles << fields[0] << ',' << phase << ',' << profiling::names[i]
                   << ',' << values[i].calls << ',' << values[i].inclusive_ns
                   << ',' << values[i].exclusive_ns << '\n';
        profiling::reset();
        return wall;
      };
      profiling::reset();
      const Stamp setup_start;
      RuntimeLimits limits;
      limits.events_per_timestamp = 10000;
      limits.committed_events = 200000;
      limits.checkpoint_bytes = 64 * 1024 * 1024;
      WorldRuntime w({6, 6}, 42, {}, limits);
      SocialConfig config;
      config.bounded_contacts = bounded;
      w.configure_social(config);
      const auto colony = w.seed_colony();
      std::vector<AntRef> ants;
      for (unsigned i = 0; i < count; ++i) {
        const PositionM p =
            dispersed ? PositionM{static_cast<double>(i % 32) * .01, 0,
                                  static_cast<double>(i / 32) * .01}
                      : PositionM{};
        const auto ant = w.seed_ant(colony, {p});
        ants.push_back(ant);
        w.enable_physiology(ant, {{100, 400, 400, 100}, 1000000000, 1000, 0});
      }
      for (auto ant : ants)
        w.set_behavior(ant, IndividualBehavior::Nurse);
      const auto setup = finish("setup", setup_start);
      const Stamp advance_start;
      for (std::int64_t t = 1000; t <= 10000; t += 1000)
        w.advance_to({t});
      const auto advance = finish("advance", advance_start);
      s3_fixture::balanced(w);
      profiling::reset();
      const Stamp encode_start;
      const auto bytes = w.checkpoint();
      const auto encode = finish("encode", encode_start);
      WorldRuntime restored({9, 9}, 0, {}, limits);
      profiling::reset();
      const Stamp restore_start;
      restored.restore(bytes);
      const auto restore = finish("restore", restore_start);
      require(bytes == restored.checkpoint(), "checkpoint restore divergence");
      const auto work = w.contact_work();
      const auto state = w.snapshot();
      const auto [rss, peak] = memory();
      require(!bounded || work.maximum_candidates <= 16,
              "candidate budget violation");
      w.advance_to({11000});
      restored.advance_to({11000});
      require(w.checkpoint() == restored.checkpoint(),
              "restored continuation divergence");
      out << line << ",42,10000," << setup << ',' << advance << ',' << encode
          << ',' << restore << ',' << bytes.size() << ',' << rss << ',' << peak
          << ',' << state.committed_events << ',' << state.pending_events << ','
          << work.decisions << ',' << work.candidates_examined << ','
          << work.bucket_queries << ',' << work.tree_visits << ','
          << work.maximum_candidates << ',' << state.state_hash << ','
          << state.trace_hash << ",1," << profiling::enabled << ',' << mask
          << '\n';
      out.flush();
      phases.flush();
      profiles.flush();
      std::this_thread::sleep_for(std::chrono::milliseconds(250));
    }
    require(expected > 0, "empty schedule");
    std::cout << "PASS S6.2 measured " << expected
              << " complete samples; exact recovery and work retained\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
