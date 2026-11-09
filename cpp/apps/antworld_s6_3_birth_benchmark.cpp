#include "antworld/core/profiling.hpp"
#include "s6_3_benchmark_clock.hpp"
#include "s6_3_fixture.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
using namespace antworld;
using s3_fixture::require;
namespace {
std::pair<std::uint64_t, std::uint64_t> memory() {
#ifdef _WIN32
  PROCESS_MEMORY_COUNTERS m{};
  m.cb = sizeof(m);
  require(GetProcessMemoryInfo(GetCurrentProcess(), &m, sizeof(m)) != 0,
          "memory unavailable");
  return {m.WorkingSetSize, m.PeakWorkingSetSize};
#else
  return {}; // Host-specific telemetry remains separate.
#endif
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc != 4)
      throw std::invalid_argument("usage: antworld_s6_3_birth_benchmark "
                                  "OUTPUT_DIR SCHEDULE_CSV AFFINITY_MASK");
    const std::filesystem::path out = argv[1];
    require(!std::filesystem::exists(out / "births.csv"),
            "refusing to overwrite birth evidence");
    std::filesystem::create_directories(out);
    const auto mask = std::stoull(argv[3]);
#ifdef _WIN32
    if (mask)
      require(SetProcessAffinityMask(GetCurrentProcess(), mask) != 0,
              "cannot set benchmark affinity");
#else
    require(mask == 0, "use external affinity on this host");
#endif
    std::ifstream schedule(argv[2]);
    require(static_cast<bool>(schedule), "missing birth schedule");
    std::string line;
    std::getline(schedule, line);
    std::ofstream data(out / "births.csv"), profile(out / "profile.csv"),
        phases(out / "phases.csv");
    data.exceptions(std::ios::badbit | std::ios::failbit);
    profile.exceptions(std::ios::badbit | std::ios::failbit);
    phases.exceptions(std::ios::badbit | std::ios::failbit);
    phases << std::setprecision(17)
           << "sample,phase,start_utc_ns,end_utc_ns,wall_ms,cpu_ms,cycles,"
              "start_processor,end_processor\n";
    data << std::setprecision(17)
         << "sample,session,block,slot,warmup,population,layout,policy,setup_"
            "ms,birth_advance_ms,encode_ms,restore_ms,births,events,pending,"
            "checkpoint_bytes,rss_bytes,process_peak_bytes,exact_restore,mass_"
            "balanced,energy_balanced,state_hash,trace_hash\n";
    profile << "sample,phase,category,calls,inclusive_ns,exclusive_ns\n";
    while (std::getline(schedule, line)) {
      if (!line.empty() && line.back() == '\r')
        line.pop_back();
      std::stringstream parse(line);
      std::vector<std::string> fields;
      for (std::string part; std::getline(parse, part, ',');)
        fields.push_back(part);
      require(fields.size() == 8, "invalid birth schedule row");
      const auto n = std::stoul(fields[5]);
      require(n == 128 || n == 512 || n == 2048, "unfrozen population");
      auto emit = [&](std::string_view phase) {
        for (std::size_t i = 0; i < profiling::names.size(); ++i) {
          const auto c = profiling::snapshot()[i];
          profile << fields[0] << ',' << phase << ',' << profiling::names[i]
                  << ',' << c.calls << ',' << c.inclusive_ns << ','
                  << c.exclusive_ns << '\n';
        }
      };
      auto finish = [&](std::string_view phase,
                        const s6_3_benchmark::Stamp &start) {
        const s6_3_benchmark::Stamp end;
        const auto ms =
            std::chrono::duration<double, std::milli>(end.wall - start.wall)
                .count();
        phases << fields[0] << ',' << phase << ',' << start.utc << ','
               << end.utc << ',' << ms << ','
               << static_cast<double>(end.cpu - start.cpu) / 1000000 << ','
               << end.cycles - start.cycles << ',' << start.processor << ','
               << end.processor << '\n';
        emit(phase);
        return ms;
      };
      profiling::reset();
      auto t = s6_3_benchmark::Stamp{};
      WorldRuntime w({63, 8}, 42, {}, s6_3_fixture::limits());
      w.configure_long_term();
      w.configure_social({});
      const auto colony = w.seed_colony();
      PhysiologyConfig p;
      p.adult_protein_target_ug = 20;
      p.basal_nj_per_ms = 0;
      p.water_loss_ug_per_period = 0;
      ReproductionConfig r;
      r.interval = {10};
      r.egg_water_ug = 1;
      r.egg_energy_nj = 1000000;
      for (unsigned long i = 0; i < n; ++i) {
        const auto queen =
            w.seed_ant(colony, {{}, LifeStage::Adult, Caste::Queen});
        w.enable_physiology(queen, {{0, 100, 0, 0}, 1500000000, 1600, 0}, p);
        w.enable_reproduction(queen, r);
        // ENGINEERING_FIXTURE: unrelated pending worker moves expose a
        // registration conflict check that scans the entire queue.
        const auto worker = w.seed_ant(colony, {});
        w.submit({worker, {100}, ActionKind::Move, {}, {}, 0});
      }
      const auto setup = finish("setup", t);
      profiling::reset();
      t = s6_3_benchmark::Stamp{};
      w.advance_to({10});
      const auto advance = finish("birth_advance", t);
      profiling::reset();
      t = s6_3_benchmark::Stamp{};
      const auto bytes = w.checkpoint();
      const auto encode = finish("checkpoint", t);
      WorldRuntime restored({9, 9}, 0, {}, s6_3_fixture::limits());
      profiling::reset();
      t = s6_3_benchmark::Stamp{};
      restored.restore(bytes);
      const auto restore = finish("restore", t);
      require(restored.checkpoint() == bytes, "birth restore mismatch");
      s6_3_fixture::conserved(w);
      require(w.summary().ant_count == 3 * n,
              "missing dynamically registered offspring");
      const auto m = memory();
      const auto s = w.snapshot();
      data << line << ',' << setup << ',' << advance << ',' << encode << ','
           << restore << ',' << n << ',' << s.committed_events << ','
           << s.pending_events << ',' << bytes.size() << ',' << m.first << ','
           << m.second << ",1,1,1," << hex64(s.state_hash) << ','
           << hex64(s.trace_hash) << '\n';
      data.flush();
    }
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
