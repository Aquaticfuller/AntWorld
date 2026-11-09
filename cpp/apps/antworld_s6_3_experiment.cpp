#include "antworld/core/profiling.hpp"
#include "s6_3_fixture.hpp"
#ifdef ANTWORLD_S6_3_STORAGE
#include "antworld/storage/store.hpp"
#endif
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#ifdef _WIN32
#define NOMINMAX
// clang-format off
#include <windows.h>
#include <psapi.h>
// clang-format on
#endif
using namespace antworld;
using s3_fixture::require;
namespace {
using Clock = std::chrono::steady_clock;
double elapsed(Clock::time_point t) {
  return std::chrono::duration<double, std::milli>(Clock::now() - t).count();
}
std::uint64_t rss() {
#ifdef _WIN32
  PROCESS_MEMORY_COUNTERS_EX m{};
  m.cb = sizeof(m);
  return GetProcessMemoryInfo(GetCurrentProcess(),
                              reinterpret_cast<PROCESS_MEMORY_COUNTERS *>(&m),
                              sizeof(m))
             ? m.WorkingSetSize
             : 0;
#else
  return 0; // Host telemetry supplies platform memory; never fabricate a
            // measurement.
#endif
}
void mass(std::ostream &o, FoodMass m) {
  for (const auto n : m.components())
    o << ',' << n;
}
std::ofstream file(const std::filesystem::path &p) {
  std::ofstream o(p, std::ios::binary);
  o.exceptions(std::ios::badbit | std::ios::failbit);
  o << std::setprecision(17);
  return o;
}
struct Residence {
  LifeStage stage{};
  Caste caste{};
  unsigned behavior{};
  SimTime since;
};
struct Evidence {
  std::map<EntityId, Residence> people;
  std::array<std::uint64_t, 5> duration{};
  std::uint64_t births{}, emerged{}, deaths{}, transfers{}, protein{},
      recycled{}, switches{}, rejects{};
  EventId cursor;
  void integrate(EntityId id, SimTime at) {
    auto &p = people.at(id);
    if (p.stage == LifeStage::Adult && p.caste == Caste::Worker)
      duration.at(p.behavior) +=
          static_cast<std::uint64_t>(at.milliseconds - p.since.milliseconds);
    p.since = at;
  }
  void collect(const WorldRuntime &w, std::ostream &binary,
               std::ostream &life) {
    for (;;) {
      const auto batch = w.events_after(cursor, 4096);
      if (batch.empty())
        break;
      for (const auto &e : batch) {
        const auto encoded = encode_event(e);
        binary.write(reinterpret_cast<const char *>(encoded.data()),
                     static_cast<std::streamsize>(encoded.size()));
        if (e.kind == FactKind::AntSeeded || e.kind == FactKind::AntBorn)
          people.emplace(e.actor,
                         Residence{e.stage,
                                   w.query_ant({e.world, e.actor})->caste, 0,
                                   e.time});
        if (e.actor.value && people.contains(e.actor))
          integrate(e.actor, e.time);
        if (e.kind == FactKind::BehaviorChanged) {
          people.at(e.actor).behavior = static_cast<unsigned>(e.payload);
          ++switches;
        }
        if (e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied)
          people.at(e.actor).stage = e.stage;
        if (e.kind == FactKind::AntBorn)
          ++births;
        if (e.kind == FactKind::StageChanged && e.stage == LifeStage::Adult)
          ++emerged;
        if (e.kind == FactKind::AntDied)
          ++deaths;
        if (e.kind == FactKind::NutritionTransferred) {
          ++transfers;
          protein += e.transferred.protein_ug;
        }
        if (e.kind == FactKind::ProteinRecycled)
          recycled += e.transferred.protein_ug;
        if (e.kind == FactKind::ActionRejected)
          ++rejects;
        if (e.kind == FactKind::AntBorn || e.kind == FactKind::StageChanged ||
            e.kind == FactKind::AntDied ||
            e.kind == FactKind::NutritionTransferred ||
            e.kind == FactKind::ProteinRecycled ||
            e.kind == FactKind::ReproductionAttempt ||
            e.kind == FactKind::ResourceReleased ||
            e.kind == FactKind::NestIngested ||
            e.kind == FactKind::BehaviorChanged) {
          life << e.id.value << ',' << e.time.milliseconds << ','
               << static_cast<unsigned>(e.kind) << ',' << e.actor.value << ','
               << e.payload << ',' << e.random_value;
          mass(life, e.transferred);
          life << ',' << static_cast<unsigned>(e.stage) << ',' << e.source.value
               << '\n';
        }
        cursor = e.id;
      }
    }
    for (const auto &a : w.ant_states())
      integrate(a.id, w.summary().now);
  }
};
void run(const std::filesystem::path &root, std::ostream &summary,
         std::uint64_t seed, unsigned workers, std::string_view supply,
         bool cyclic, std::string_view arm, unsigned days,
         std::int64_t pulse = 6) {
  const auto name = std::to_string(seed) + "_" + std::to_string(workers) + "_" +
                    std::string(supply) + "_" +
                    (cyclic ? "cyclic" : "constant") + "_" + std::string(arm) +
                    "_" + std::to_string(pulse);
  const auto dir = root / name;
  require(!std::filesystem::exists(dir),
          "refusing to overwrite world evidence");
  std::filesystem::create_directories(dir);
  LongTermConfig policy;
  policy.protein_recycling = arm != "no_recycling";
  policy.demand_feedback = arm != "no_feedback";
  policy.post_intake_contact = arm != "return_only" && arm != "pre_correction";
  policy.complete_depot_visits =
      arm != "exchange_only" && arm != "pre_correction";
  const auto setup_start = Clock::now();
  s6_3_fixture::World fixture(seed, workers, supply, cyclic, policy, pulse,
                              arm == "compact");
  auto &w = fixture.world;
  const auto setup = elapsed(setup_start);
  auto series = file(dir / "daily.csv"),
       individuals = file(dir / "individuals.csv"),
       life = file(dir / "life_events.csv"), binary = file(dir / "events.bin"),
       performance = file(dir / "performance.csv");
  series << "day,time_ms,egg,larva,pupa,adult,dead,births,emerged,transfers,"
            "transferred_protein_ug,recycled_protein_ug,switches,rejected,"
            "unmet_larval_protein_ug,living_worker_crop_protein_ug";
  for (const auto label :
       {"input", "accounted", "reserve", "available", "cargo", "nest", "crop"})
    for (const auto ingredient : {"carbs", "protein", "water", "other"})
      series << ',' << label << '_' << ingredient << "_ug";
  series << ",body_water_ug,tissue_protein_ug,oxidized_carbs_ug,lost_water_ug,"
            "energy_input_nj,body_energy_nj,dissipated_energy_nj,soil_initial_"
            "q3,soil_remaining_q3,soil_carried_q3,soil_deposited_q3,geometry_"
            "edits,events,paused_ms,rest_ms,nurse_ms,forage_ms,excavate_ms,"
            "mass_balanced,energy_balanced\n";
  individuals << "day,id,mother,born_ms,stage,caste,x_m,y_m,z_m,behavior,carbs_"
                 "ug,protein_ug,water_ug,other_ug,body_energy_nj,hydration_ug,"
                 "tissue_protein_ug,stage_progress_ms,death_cause\n";
  life << "event,time_ms,kind,actor,payload,energy_or_candidates,carbs_ug,"
          "protein_ug,water_ug,other_ug,stage,source\n";
  performance
      << "day,advance_ms,checkpoint_ms,restore_ms,checkpoint_bytes,rss_bytes,"
         "events,pending,contact_candidates,contact_tree_visits\n";
  Evidence evidence;
  std::vector<std::uint8_t> middle;
  double advance_total = 0;
  std::string status = "complete", reason;
  unsigned completed = 0;
  for (unsigned d = 0; d <= days; ++d) {
    const auto start = Clock::now();
    try {
      w.advance_to({static_cast<std::int64_t>(d) * s6_3_fixture::day});
    } catch (const std::length_error &e) {
      status = "censored";
      reason = e.what();
      break;
    }
    const auto advance = elapsed(start);
    advance_total += advance;
    completed = d;
    s6_3_fixture::conserved(w);
    evidence.collect(w, binary, life);
    std::array<std::uint64_t, 5> stages{};
    std::uint64_t need = 0, surplus = 0;
    for (const auto &a : w.ant_states()) {
      ++stages.at(static_cast<unsigned>(a.stage));
      const auto p = *w.query_physiology({w.summary().world, a.id});
      if (a.stage == LifeStage::Larva &&
          p.tissue_protein_ug + p.crop.protein_ug <
              p.config.larval_protein_requirement_ug)
        need += p.config.larval_protein_requirement_ug - p.tissue_protein_ug -
                p.crop.protein_ug;
      if (a.stage == LifeStage::Adult && a.caste == Caste::Worker)
        surplus += p.crop.protein_ug;
      individuals << d << ',' << a.id.value << ',' << p.mother.value << ','
                  << a.born_at.milliseconds << ','
                  << static_cast<unsigned>(a.stage) << ','
                  << static_cast<unsigned>(a.caste) << ',' << a.position.x
                  << ',' << a.position.y << ',' << a.position.z << ','
                  << static_cast<unsigned>(p.behavior);
      mass(individuals, p.crop);
      individuals << ',' << p.body_energy_nj << ',' << p.hydration_ug << ','
                  << p.tissue_protein_ug << ',' << p.stage_progress.milliseconds
                  << ',' << static_cast<unsigned>(p.death_cause) << '\n';
    }
    const auto s = w.summary();
    const auto n = w.nutrition_snapshot();
    const auto g = w.geometry_snapshot();
    series << d << ',' << s.now.milliseconds;
    for (const auto count : stages)
      series << ',' << count;
    series << ',' << evidence.births << ',' << evidence.emerged << ','
           << evidence.transfers << ',' << evidence.protein << ','
           << evidence.recycled << ',' << evidence.switches << ','
           << evidence.rejects << ',' << need << ',' << surplus;
    for (const auto m : {n.introduced, n.accounted, w.resource_reserves(),
                         s.food_ledger.available, s.food_ledger.carried,
                         s.food_ledger.stored, n.crop})
      mass(series, m);
    series << ',' << n.hydration_ug << ',' << n.tissue_protein_ug << ','
           << n.oxidized_carbs_ug << ',' << n.lost_water_ug << ','
           << n.energy_input_nj << ',' << n.body_energy_nj << ','
           << n.dissipated_energy_nj << ',' << g.ledger.initial_q3 << ','
           << g.ledger.remaining_q3 << ',' << g.ledger.carried_q3 << ','
           << g.ledger.deposited_q3 << ',' << g.geometry_revision << ','
           << s.committed_events;
    for (const auto dt : evidence.duration)
      series << ',' << dt;
    series << ",1,1\n";
    double encode_ms = 0, restore_ms = 0;
    std::uint64_t bytes = 0;
    if (d == days / 2 || d == days) {
      auto t = Clock::now();
      const auto saved = w.checkpoint();
      encode_ms = elapsed(t);
      bytes = saved.size();
      WorldRuntime restored({7, 7}, 0, {}, s6_3_fixture::limits());
      t = Clock::now();
      restored.restore(saved);
      restore_ms = elapsed(t);
      require(restored.checkpoint() == saved, "checkpoint roundtrip mismatch");
      if (d == days / 2)
        middle = saved;
      if (d == days) {
        auto checkpoint = file(dir / "final.aw");
        checkpoint.write(reinterpret_cast<const char *>(saved.data()),
                         static_cast<std::streamsize>(saved.size()));
      }
    }
    const auto work = w.contact_work();
    performance << d << ',' << advance << ',' << encode_ms << ',' << restore_ms
                << ',' << bytes << ',' << rss() << ',' << s.committed_events
                << ',' << s.pending_events << ',' << work.candidates_examined
                << ',' << work.tree_visits << '\n';
  }
  bool exact = false, durable = false;
  if (!middle.empty() && status == "complete") {
    WorldRuntime replay({9, 9}, 0, {}, s6_3_fixture::limits());
    replay.restore(middle);
    while (replay.summary().now < w.summary().now)
      replay.advance_to({std::min(w.summary().now.milliseconds,
                                  replay.summary().now.milliseconds +
                                      7 * s6_3_fixture::day + 12345)});
    exact = replay.checkpoint() == w.checkpoint();
    require(exact, "irregular restored acceleration differs");
  }
#ifdef ANTWORLD_S6_3_STORAGE
  if (seed == 1 && workers == 8 && arm == "full" && pulse == 6) {
    storage::Store store(dir / "world.sqlite", s6_3_fixture::limits());
    const auto token = store.save(w);
    auto loaded = store.load(token.world);
    require(loaded.world.checkpoint() == w.checkpoint(),
            "SQLite long-term mismatch");
    require(store.flow_total(token.world, {}, storage::Metric::Born, {},
                             {w.summary().now.milliseconds + 1}) ==
                evidence.births,
            "durable birth count differs");
    for (const auto &a : w.ant_states())
      require(store.individual({token.world, a.id})->seeded ==
                  (a.born_at == SimTime{}),
              "seed and birth history conflated");
    durable = true;
  }
#endif
  const auto snapshot = w.snapshot();
  summary << "ENGINEERING_FIXTURE," << name << ',' << seed << ',' << workers
          << ',' << supply << ',' << cyclic << ',' << arm << ',' << pulse << ','
          << days << ',' << completed << ',' << status << ',' << reason << ','
          << snapshot.living_ants << ',' << evidence.births << ','
          << evidence.emerged << ',' << evidence.deaths << ','
          << evidence.protein << ',' << evidence.recycled << ','
          << snapshot.committed_events << ','
          << w.geometry_snapshot().geometry_revision << ',' << setup << ','
          << advance_total << ',' << exact << ',' << durable << ','
          << hex64(snapshot.state_hash) << ',' << hex64(snapshot.trace_hash)
          << '\n';
  summary.flush();
  std::cout << name << " days=" << completed << " births=" << evidence.births
            << " emerged=" << evidence.emerged
            << " alive=" << snapshot.living_ants
            << " events=" << snapshot.committed_events << '\n'
            << std::flush;
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc != 3)
      throw std::invalid_argument(
          "usage: antworld_s6_3_experiment OUTPUT_DIR "
          "smoke|primary|controls|sensitivity|factorial|spatial|review");
    const std::filesystem::path root = argv[1];
    const std::string mode = argv[2];
    require(!std::filesystem::exists(root / "summary.csv"),
            "refusing to overwrite experiment");
    std::filesystem::create_directories(root);
    auto summary = file(root / "summary.csv");
    summary << "scope,run,seed,workers,supply,cyclic,arm,pulse_hours,requested_"
               "days,completed_days,status,reason,alive,births,emerged,deaths,"
               "protein_transferred_ug,recycled_protein_ug,events,geometry_"
               "edits,setup_ms,advance_ms,exact_continuation,durable_checked,"
               "state_hash,trace_hash\n";
    if (mode == "smoke")
      run(root, summary, 1, 8, "balanced", false, "full", 7);
    else if (mode == "primary") {
      for (std::uint64_t seed = 1; seed <= 6; ++seed)
        for (const auto workers : {8U, 32U}) {
          for (const auto supply : {"balanced", "scarce", "empty"})
            run(root, summary, seed, workers, supply, false, "full", 90);
          run(root, summary, seed, workers, "balanced", true, "full", 90);
        }
    } else if (mode == "controls") {
      for (std::uint64_t seed = 1; seed <= 6; ++seed)
        for (const auto arm : {"full", "no_recycling", "no_feedback"})
          run(root, summary, seed, 32, "scarce", false, arm, 14);
    } else if (mode == "sensitivity") {
      for (std::uint64_t seed = 1; seed <= 3; ++seed)
        for (const auto pulse : {3, 12})
          run(root, summary, seed, 8, "balanced", false, "full", 14, pulse);
    } else if (mode == "factorial") {
      for (std::uint64_t seed = 1; seed <= 6; ++seed)
        for (const auto supply : {"balanced", "empty"})
          for (const auto arm : {"return_only", "exchange_only"})
            run(root, summary, seed, 8, supply, false, arm, 14);
    } else if (mode == "spatial") {
      for (std::uint64_t seed = 1; seed <= 6; ++seed)
        run(root, summary, seed, 32, "balanced", false, "compact", 90);
    } else if (mode == "review") {
      run(root, summary, 1, 8, "balanced", false, "full", 90);
      run(root, summary, 1, 32, "balanced", false, "compact", 90);
    } else
      throw std::invalid_argument("unknown frozen experiment matrix");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
