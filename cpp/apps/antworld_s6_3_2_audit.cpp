#include "s6_3_fixture.hpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

using namespace antworld;
using s3_fixture::require;
using s6_3_fixture::day;
using s6_3_fixture::hour;

namespace {
// ENGINEERING_FIXTURE diagnostics frozen in document 49. No empirical fit.
PhysiologyConfig profile() {
  PhysiologyConfig p;
  p.absorption_period = {6 * hour};
  p.behavior_interval = {6 * hour};
  p.water_loss_period = {hour};
  p.egg_duration = {2 * day};
  p.larva_duration = {3 * day};
  p.pupa_duration = {2 * day};
  p.basal_nj_per_ms = 1;
  p.active_nj_per_ms = 1;
  return p;
}
void prepare(WorldRuntime &world) {
  world.configure_long_term({});
  world.configure_social({});
}
void facts(std::ofstream &out, const WorldRuntime &world,
           const std::string &name, std::uint64_t seed) {
  for (const auto &event : world.committed_events()) {
    out << name << ',' << seed << ',' << event.id.value << ','
        << event.time.milliseconds << ',' << static_cast<unsigned>(event.kind)
        << ',' << event.actor.value << ',';
    for (const auto byte : encode_event(event))
      out << std::hex << std::setfill('0') << std::setw(2)
          << static_cast<unsigned>(byte);
    out << std::dec << '\n';
  }
}
void observe(std::ofstream &out, const WorldRuntime &world, AntRef actor,
             const std::string &name, std::uint64_t seed) {
  const auto ant = world.query_ant(actor).value();
  const auto p = world.query_physiology(actor).value();
  const auto n = world.nutrition_snapshot();
  const auto r = world.query_reproduction(actor);
  const auto s = world.summary();
  s6_3_fixture::conserved(world);
  out << name << ',' << seed << ',' << s.now.milliseconds << ',' << ant.id.value
      << ',' << static_cast<unsigned>(ant.stage) << ',' << s.living_ants << ','
      << (r ? r->births : 0) << ',' << p.body_energy_nj << ',' << p.hydration_ug
      << ',' << p.crop.carbs_ug << ',' << p.crop.protein_ug << ','
      << p.crop.water_ug << ',' << p.tissue_protein_ug << ','
      << p.oxidized_carbs_ug << ',' << p.dissipated_energy_nj << ','
      << p.exported_energy_nj << ',' << n.energy_input_nj << ','
      << n.body_energy_nj << ',' << n.dissipated_energy_nj << ','
      << s.committed_events << '\n';
}
void trajectory(std::ofstream &series, std::ofstream &events,
                std::ofstream &checks, std::uint64_t seed,
                const std::string &name, Caste caste, LifeStage stage,
                const PhysiologySeed &initial, bool laying,
                std::int64_t duration, std::int64_t cadence) {
  WorldRuntime world({632, 1}, seed, {}, s6_3_fixture::limits());
  prepare(world);
  const auto colony = world.seed_colony();
  const auto actor = world.seed_ant(colony, {{}, stage, caste, 4000});
  auto p = profile();
  if (caste == Caste::Queen)
    p.adult_protein_target_ug = 20;
  world.enable_physiology(actor, initial, p);
  if (laying) {
    ReproductionConfig r;
    r.maintenance_horizon = {2 * day};
    world.enable_reproduction(actor, r);
  }
  const auto initial_bytes = world.checkpoint();
  WorldRuntime restored({632, 9}, 0, {}, s6_3_fixture::limits());
  observe(series, world, actor, name, seed);
  bool restored_at_midpoint = false;
  for (std::int64_t t = cadence; t <= duration; t += cadence) {
    world.advance_to({t});
    observe(series, world, actor, name, seed);
    if (t == duration / 2) {
      restored.restore(world.checkpoint());
      restored_at_midpoint = true;
    }
  }
  require(restored_at_midpoint, "missing frozen restore midpoint");
  restored.advance_to({duration});
  require(world.checkpoint() == restored.checkpoint(), "split restore mismatch");
  WorldRuntime accelerated({632, 8}, 0, {}, s6_3_fixture::limits());
  accelerated.restore(initial_bytes);
  accelerated.advance_to({duration});
  require(world.checkpoint() == accelerated.checkpoint(),
          "single advance differs from observation cadence");
  s6_3_fixture::conserved(restored);
  checks << name << ',' << seed << ",1,1,1," << world.snapshot().state_hash
         << ',' << world.snapshot().trace_hash << '\n';
  facts(events, world, name, seed);
}
void eligibility(std::ofstream &out, std::uint64_t seed, unsigned workers) {
  WorldRuntime world({632, 2}, seed, {}, s6_3_fixture::limits());
  prepare(world);
  const auto colony = world.seed_colony();
  const auto queen = world.seed_ant(colony, {{}, LifeStage::Adult, Caste::Queen});
  const PhysiologySeed initial{{200, 100, 200, 0}, 1500000000, 1600, 0};
  world.enable_physiology(queen, initial, profile());
  const auto larva = world.seed_ant(colony, {{}, LifeStage::Larva});
  world.enable_physiology(larva, initial, profile());
  AntRef worker;
  for (unsigned i = 0; i < workers; ++i) {
    worker = world.seed_ant(colony, {});
    world.enable_physiology(worker, initial, profile());
  }
  const auto before = world.checkpoint();
  bool nurse_rejected = false, autonomy_rejected = false;
  try {
    world.set_behavior(queen, IndividualBehavior::Nurse);
  } catch (const std::invalid_argument &) {
    nurse_rejected = true;
  }
  require(before == world.checkpoint(), "queen care rejection mutated world");
  try {
    world.set_autonomy(queen);
  } catch (const std::invalid_argument &) {
    autonomy_rejected = true;
  }
  require(before == world.checkpoint(), "queen autonomy rejection mutated world");
  require(nurse_rejected && autonomy_rejected,
          "queen model changed; revise frozen biological audit");
  if (workers) {
    world.set_behavior(worker, IndividualBehavior::Nurse);
    require(world.query_physiology(worker)->behavior == IndividualBehavior::Nurse,
            "worker care control failed");
  }
  out << seed << ',' << workers << ',' << nurse_rejected << ','
      << autonomy_rejected << ",1," << (workers ? "1" : "NOT_APPLICABLE") << '\n';
}
} // namespace

int main(int argc, char **argv) {
  try {
    require(argc == 2 || argc == 3,
            "usage: antworld_s6_3_2_audit OUTPUT_DIR [SEED_COUNT]");
    const unsigned seeds = argc == 3 ? static_cast<unsigned>(std::stoul(argv[2])) : 6;
    require(seeds >= 1 && seeds <= 6, "frozen seeds are 1 through 6");
    const std::filesystem::path out = argv[1];
    std::filesystem::create_directories(out);
    std::ofstream care(out / "eligibility.csv"), series(out / "time_series.csv"),
        events(out / "events.csv"), checks(out / "checks.csv");
    for (auto *stream : {&care, &series, &events, &checks})
      stream->exceptions(std::ios::badbit | std::ios::failbit);
    care << "seed,workers,queen_nurse_rejected,queen_autonomy_rejected,exact_rollback,worker_nurse_accepted\n";
    series << "probe,seed,time_ms,actor,stage,living,births,body_energy_nj,hydration_ug,crop_carbs_ug,crop_protein_ug,crop_water_ug,tissue_protein_ug,oxidized_carbs_ug,actor_dissipated_nj,exported_nj,total_energy_input_nj,total_body_energy_nj,total_dissipated_nj,events\n";
    events << "probe,seed,event_id,time_ms,kind,actor,canonical_event_hex\n";
    checks << "probe,seed,exact_restore,exact_single_advance,conserved,state_hash,trace_hash\n";
    for (unsigned seed = 1; seed <= seeds; ++seed) {
      for (const auto workers : {0U, 1U, 5U})
        eligibility(care, seed, workers);
      const PhysiologySeed empty{{}, 1500000000, 1600, 0};
      trajectory(series, events, checks, seed, "rest_queen", Caste::Queen,
                 LifeStage::Adult, empty, false, day, 12 * hour);
      trajectory(series, events, checks, seed, "rest_worker", Caste::Worker,
                 LifeStage::Adult, empty, false, day, 12 * hour);
      const PhysiologySeed supplied{{}, 1500000000, 1600, 100};
      trajectory(series, events, checks, seed, "supplied_tissue_clock", Caste::Worker,
                 LifeStage::Egg, supplied, false, 8 * day, day);
      const PhysiologySeed initial{{200, 100, 200, 0}, 1500000000, 1600, 0};
      for (const bool laying : {false, true})
        trajectory(series, events, checks, seed,
                   laying ? "sealed_queen_laying" : "sealed_queen_suppressed",
                   Caste::Queen, LifeStage::Adult, initial, laying, 90 * day, day);
    }
    std::cout << "Audit diagnostics complete; biological limitations retained\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
