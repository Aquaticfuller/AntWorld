#include "s6_fixture.hpp"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>

using namespace antworld;
using s3_fixture::require;
namespace {
struct Output {
  std::ofstream summary, series, events, decisions, individuals, counts;
  explicit Output(const std::filesystem::path &dir)
      : summary(dir / "summary.csv"), series(dir / "time_series.csv"),
        events(dir / "events.csv"), decisions(dir / "decisions.csv"),
        individuals(dir / "individuals.csv"), counts(dir / "event_counts.csv") {
    for (auto *f :
         {&summary, &series, &events, &decisions, &individuals, &counts}) {
      f->exceptions(std::ios::badbit | std::ios::failbit);
      *f << std::setprecision(17);
    }
    const char *key = "suite,seed,policy,workers,source_protein_ug,budget,"
                      "minimum_ms,condition,mirror,";
    summary << key
            << "duration_ms,events,state_hash,trace_hash,living,emerged,"
               "unemerged_brood,unmet_protein_ug,"
               "unmet_integral_ug_s,accessible_demand_integral_ug_s,accessible_"
               "supply_integral_ug_s,adult_crop_protein_ug,"
               "dead_crop_protein_ug,gift_attempts,gift_success,gift_partial,"
               "gift_failed,given_protein_ug,nest_intakes,"
               "program_switches,nurse_exits_with_sampled_work,autonomy_"
               "decisions,blocked_travel_decisions,"
               "minimum_time_decisions,initial_worker_living_ms,initial_worker_"
               "active_ms,initial_worker_away_ms,"
               "moves,excavated_q3,carb_residual_ug,protein_residual_ug,water_"
               "residual_ug,other_residual_ug,energy_residual_nj,soil_residual_"
               "q3\n";
    series
        << key
        << "time_ms,living,larvae,unmet_protein_ug,adult_crop_protein_ug,dead_"
           "crop_protein_ug,"
           "accessible_sample,accessible_demand_ug,accessible_supply_ug,nest_"
           "protein_ug,emerged,gift_attempts,"
           "gift_success,gift_partial,gift_failed,given_protein_ug,program_"
           "switches,moves,excavated_q3,"
           "carb_introduced_ug,protein_introduced_ug,water_introduced_ug,other_"
           "introduced_ug,"
           "carb_accounted_ug,protein_accounted_ug,water_accounted_ug,other_"
           "accounted_ug,"
           "energy_input_nj,body_energy_nj,dissipated_energy_nj,soil_initial_"
           "q3,soil_remaining_q3,soil_carried_q3,soil_deposited_q3\n";
    events << key
           << "event_id,source_id,time_ms,kind,actor,payload,stage,outcome,x_m,"
              "y_m,z_m,carbs_ug,protein_ug,water_ug,other_ug\n";
    decisions
        << key
        << "event_id,time_ms,actor,program_before,program_after,program_age_ms,"
           "at_depot,"
           "can_switch,ready,actual_candidates,actual_contacts,needy_larvae,"
           "crop_compatible_work,"
           "crop_protein_ug,urgent,crowded,reachable_soil,nest_protein_ug\n";
    individuals << key
                << "entity_id,seed_stage,final_stage,adult_ms,death_ms,crop_"
                   "carbs_ug,crop_protein_ug,"
                   "crop_water_ug,crop_other_ug,tissue_protein_ug,body_energy_"
                   "nj,hydration_ug\n";
    counts << key << "kind,count\n";
  }
};
struct Person {
  LifeStage seeded{};
  std::int64_t adult{-1}, death{-1};
};
struct Observation {
  std::uint64_t living{}, larvae{}, unmet{}, adult_crop{}, dead_crop{},
      accessible_demand{}, accessible_supply{};
};
struct Monitor {
  WorldRuntime &w;
  Output &out;
  std::string prefix;
  unsigned workers;
  std::ofstream binary;
  EventId cursor;
  std::map<EntityId, Person> people;
  std::map<FactKind, std::uint64_t> counts;
  std::uint64_t emerged{}, attempts{}, success{}, partial{}, failed{}, given{},
      intakes{}, switches{}, exits{}, decisions{}, blocked{}, minimum{},
      living_ms{}, active_ms{}, away_ms{}, moves{};
  std::uint64_t unmet_integral{}, demand_integral{}, supply_integral{};
  Observation last;
  std::uint64_t audited_geometry_revision{UINT64_MAX};
  Monitor(WorldRuntime &world, Output &output, std::string key,
          unsigned population, const std::filesystem::path &path)
      : w(world), out(output), prefix(std::move(key)), workers(population),
        binary(path, std::ios::binary) {
    binary.exceptions(std::ios::badbit | std::ios::failbit);
    consume({});
    sample(0);
  }
  void consume(const std::map<ScheduledId, ScheduledEvent> &due) {
    for (const auto &e : w.events_after(cursor, 1000000)) {
      ++counts[e.kind];
      const auto bytes = encode_event(e);
      binary.write(reinterpret_cast<const char *>(bytes.data()),
                   static_cast<std::streamsize>(bytes.size()));
      cursor = e.id;
      if (e.kind == FactKind::AntSeeded)
        people[e.actor].seeded = e.stage;
      if (e.kind == FactKind::StageChanged && e.stage == LifeStage::Adult) {
        ++emerged;
        people.at(e.actor).adult = e.time.milliseconds;
      }
      if (e.kind == FactKind::AntDied)
        people.at(e.actor).death = e.time.milliseconds;
      if (e.kind == FactKind::BehaviorChanged)
        ++switches;
      if (e.kind == FactKind::Moved)
        ++moves;
      if (e.kind == FactKind::NestIngested)
        ++intakes;
      if (e.kind == FactKind::NutritionTransferred)
        given += e.transferred.protein_ug;
      if (due.contains(e.source) &&
          due.at(e.source).kind == ScheduledEvent::Kind::Trophallaxis) {
        ++attempts;
        if (e.kind != FactKind::NutritionTransferred)
          ++failed;
        else if (e.outcome == Outcome::Partial)
          ++partial;
        else {
          require(e.outcome == Outcome::Success, "invalid transfer outcome");
          ++success;
        }
      }
      if (e.kind == FactKind::FoodCollected ||
          e.kind == FactKind::FoodDelivered ||
          e.kind == FactKind::NestIngested ||
          e.kind == FactKind::NutritionTransferred ||
          e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied ||
          e.kind == FactKind::BehaviorChanged ||
          e.kind == FactKind::ActionRejected ||
          (e.kind >= FactKind::SoilExcavated && e.kind <= FactKind::SoilFilled))
        out.events << prefix << e.id.value << ',' << e.source.value << ','
                   << e.time.milliseconds << ','
                   << static_cast<unsigned>(e.kind) << ',' << e.actor.value
                   << ',' << e.payload << ',' << static_cast<unsigned>(e.stage)
                   << ',' << static_cast<unsigned>(e.outcome) << ','
                   << e.position.x << ',' << e.position.y << ',' << e.position.z
                   << ',' << e.transferred.carbs_ug << ','
                   << e.transferred.protein_ug << ',' << e.transferred.water_ug
                   << ',' << e.transferred.other_ug << '\n';
    }
  }
  void advance(SimTime target) {
    while (w.summary().now < target) {
      const auto pending = w.pending_events();
      const auto at =
          pending.empty() ? target : std::min(target, pending.front().key.time);
      std::map<ScheduledId, ScheduledEvent> due;
      std::map<EntityId, std::pair<IndividualBehavior, SimTime>> before;
      for (const auto &e : pending) {
        if (e.key.time != at)
          break;
        due.emplace(e.id, e);
        if (e.kind == ScheduledEvent::Kind::AutonomyWake)
          before[e.actor] = {
              w.query_physiology({w.summary().world, e.actor})->behavior,
              w.query_autonomy({w.summary().world, e.actor})
                  ->last_program_change};
      }
      const auto elapsed = at.milliseconds - w.summary().now.milliseconds;
      for (const auto &ant : w.ant_states()) {
        if (!ant.alive() || ant.id.value < 3 || ant.id.value >= 3 + workers)
          continue;
        living_ms += static_cast<std::uint64_t>(elapsed);
        const auto p = *w.query_physiology({w.summary().world, ant.id});
        if (p.behavior >= IndividualBehavior::Nurse)
          active_ms += static_cast<std::uint64_t>(elapsed);
        if (ant.position != PositionM{})
          away_ms += static_cast<std::uint64_t>(elapsed);
      }
      w.advance_to(at);
      for (const auto &e : w.events_after(cursor, 1000000)) {
        if (e.kind != FactKind::AutonomyDecision)
          continue;
        ++decisions;
        const AntRef ref{w.summary().world, e.actor};
        const auto ant = *w.query_ant(ref);
        const auto p = *w.query_physiology(ref);
        const auto old = before.at(e.actor);
        const auto social = *w.social_config();
        const auto age = at.milliseconds - old.second.milliseconds;
        const bool depot = ant.position == PositionM{};
        const bool stationary = old.first != IndividualBehavior::Forage &&
                                old.first != IndividualBehavior::Excavate;
        bool carrying_soil = false;
        for (const auto &parcel : w.soil_parcels())
          if (parcel.carrier == e.actor)
            carrying_soil = true;
        const bool can_switch = (depot || stationary) &&
                                !ant.carried_food.total_ug() && !carrying_soil;
        const bool ready = old.first == IndividualBehavior::Paused ||
                           age >= social.minimum_program_time.milliseconds;
        if (!can_switch)
          ++blocked;
        else if (!ready)
          ++minimum;
        ContactSample sample;
        if (e.random_value)
          sample = w.sample_contacts(ref, (e.payload - 1) ^
                                              UINT64_C(0x45434f4c4f4759));
        require(sample.candidates_examined == e.random_value,
                "observer sample disagrees with actual work");
        std::uint64_t needy = 0;
        bool compatible = false;
        for (const auto other : sample.ants) {
          const auto q = w.query_physiology(other);
          if (!q || q->crop.total_ug() >= q->config.crop_capacity_ug)
            continue;
          const auto stage = w.query_ant(other)->stage;
          const bool larva = stage == LifeStage::Larva &&
                             q->crop.protein_ug + q->tissue_protein_ug <
                                 q->config.larval_protein_requirement_ug;
          if (larva) {
            ++needy;
            if (p.crop.protein_ug)
              compatible = true;
          }
          const bool adult =
              stage == LifeStage::Adult &&
              (q->body_energy_nj < q->config.energy_capacity_nj / 4 ||
               q->hydration_ug < q->config.hydration_capacity_ug / 4);
          if (larva || adult) {
            if (p.crop.carbs_ug &&
                (q->config.energy_capacity_nj - q->body_energy_nj) /
                        q->config.carbohydrate_yield_nj_per_ug >
                    q->crop.carbs_ug)
              compatible = true;
            if (p.crop.water_ug &&
                q->config.hydration_capacity_ug - q->hydration_ug >
                    q->crop.water_ug)
              compatible = true;
          }
        }
        const bool urgent =
            p.body_energy_nj < p.config.energy_capacity_nj / 4 ||
            p.hydration_ug < p.config.hydration_capacity_ug / 4;
        if (old.first == IndividualBehavior::Nurse && p.behavior != old.first &&
            compatible)
          ++exits;
        bool soil = false;
        const auto g = w.geometry_snapshot().config;
        if (depot && sample.ants.size() >= 2) {
          const std::array<PositionM, 6> directions{{{1, 0, 0},
                                                     {-1, 0, 0},
                                                     {0, 1, 0},
                                                     {0, -1, 0},
                                                     {0, 0, 1},
                                                     {0, 0, -1}}};
          for (auto d : directions)
            for (std::int32_t step = 1; step <= g.reach_q; ++step) {
              const auto scale = static_cast<double>(step) * g.quantum_m;
              const auto material = w.query_material(
                  {ant.position.x + d.x * scale, ant.position.y + d.y * scale,
                   ant.position.z + d.z * scale});
              if (material == Material::Soil)
                soil = true;
              if (material != Material::Void)
                break;
            }
        }
        out.decisions << prefix << e.id.value << ',' << at.milliseconds << ','
                      << e.actor.value << ','
                      << static_cast<unsigned>(old.first) << ','
                      << static_cast<unsigned>(p.behavior) << ',' << age << ','
                      << depot << ',' << can_switch << ',' << ready << ','
                      << e.random_value << ',' << sample.ants.size() << ','
                      << needy << ',' << compatible << ',' << p.crop.protein_ug
                      << ',' << urgent << ',' << (sample.ants.size() >= 2)
                      << ',' << soil << ','
                      << w.colonies().front().nest_food.protein_ug << '\n';
      }
      consume(due);
    }
  }
  void sample(std::int64_t t) {
    const auto ants = w.ant_states();
    std::vector<PhysiologyState> p;
    for (const auto &ant : ants)
      p.push_back(*w.query_physiology({w.summary().world, ant.id}));
    Observation value;
    std::vector<std::uint64_t> need(ants.size());
    for (std::size_t i = 0; i < ants.size(); ++i) {
      if (!ants[i].alive()) {
        value.dead_crop += p[i].crop.protein_ug;
        continue;
      }
      ++value.living;
      if (ants[i].stage == LifeStage::Adult)
        value.adult_crop += p[i].crop.protein_ug;
      if (ants[i].stage == LifeStage::Larva) {
        ++value.larvae;
        const auto supplied = p[i].crop.protein_ug + p[i].tissue_protein_ug;
        need[i] = supplied < p[i].config.larval_protein_requirement_ug
                      ? p[i].config.larval_protein_requirement_ug - supplied
                      : 0;
        value.unmet += need[i];
      }
    }
    if (t)
      unmet_integral += last.unmet;
    const bool contact_sample = t % 10000 == 0;
    if (contact_sample) {
      if (t) {
        demand_integral += 10 * last.accessible_demand;
        supply_integral += 10 * last.accessible_supply;
      }
      std::set<std::size_t> recipients, donors;
      for (std::size_t i = 0; i < ants.size(); ++i) {
        if (!need[i] || p[i].crop.total_ug() >= p[i].config.crop_capacity_ug)
          continue;
        for (std::size_t j = 0; j < ants.size(); ++j) {
          if (!ants[j].alive() || ants[j].stage != LifeStage::Adult ||
              !p[j].crop.protein_ug)
            continue;
          const auto a = ants[i].position, b = ants[j].position;
          if (std::hypot(a.x - b.x, a.y - b.y, a.z - b.z) <=
                  w.config().contact_distance_m &&
              w.spatially_clear(a, b)) {
            recipients.insert(i);
            donors.insert(j);
          }
        }
      }
      for (auto i : recipients)
        value.accessible_demand += need[i];
      for (auto i : donors)
        value.accessible_supply += p[i].crop.protein_ug;
    } else {
      value.accessible_demand = last.accessible_demand;
      value.accessible_supply = last.accessible_supply;
    }
    last = value;
    // Recheck material authority when its revision changes; the same geometry
    // does not need another identical partition-volume calculation at each
    // observer tick. Every tick still checks all current conservation ledgers.
    const auto spatial = w.geometry_snapshot();
    if (spatial.geometry_revision != audited_geometry_revision) {
      s6_fixture::balanced(w);
      audited_geometry_revision = spatial.geometry_revision;
    }
    const auto n = w.nutrition_snapshot();
    const auto g = w.geometry_snapshot().ledger;
    require(n.introduced == n.accounted &&
                n.energy_input_nj == n.body_energy_nj + n.dissipated_energy_nj,
            "observed nutrition/energy imbalance");
    require(g.initial_q3 == g.remaining_q3 + g.carried_q3 + g.deposited_q3 &&
                g.initial_q3 + g.filled_q3 == g.remaining_q3 + g.excavated_q3,
            "observed material imbalance");
    out.series << prefix << t << ',' << value.living << ',' << value.larvae
               << ',' << value.unmet << ',' << value.adult_crop << ','
               << value.dead_crop << ',' << contact_sample << ','
               << value.accessible_demand << ',' << value.accessible_supply
               << ',' << w.colonies().front().nest_food.protein_ug << ','
               << emerged << ',' << attempts << ',' << success << ',' << partial
               << ',' << failed << ',' << given << ',' << switches << ','
               << moves << ',' << g.excavated_q3;
    for (auto v : n.introduced.components())
      out.series << ',' << v;
    for (auto v : n.accounted.components())
      out.series << ',' << v;
    out.series << ',' << n.energy_input_nj << ',' << n.body_energy_nj << ','
               << n.dissipated_energy_nj << ',' << g.initial_q3 << ','
               << g.remaining_q3 << ',' << g.carried_q3 << ',' << g.deposited_q3
               << '\n';
  }
  void finish(std::int64_t duration) {
    const auto meta = w.snapshot();
    const auto n = w.nutrition_snapshot();
    const auto g = w.geometry_snapshot().ledger;
    std::uint64_t unemerged = 0;
    for (const auto &ant : w.ant_states()) {
      const auto person = people.at(ant.id);
      const auto p = *w.query_physiology({meta.world, ant.id});
      if (person.seeded != LifeStage::Adult && person.adult < 0)
        ++unemerged;
      out.individuals << prefix << ant.id.value << ','
                      << static_cast<unsigned>(person.seeded) << ','
                      << static_cast<unsigned>(ant.stage) << ',' << person.adult
                      << ',' << person.death;
      for (auto v : p.crop.components())
        out.individuals << ',' << v;
      out.individuals << ',' << p.tissue_protein_ug << ',' << p.body_energy_nj
                      << ',' << p.hydration_ug << '\n';
    }
    for (auto [kind, count] : counts)
      out.counts << prefix << static_cast<unsigned>(kind) << ',' << count
                 << '\n';
    out.summary << prefix << duration << ',' << meta.committed_events << ','
                << meta.state_hash << ',' << meta.trace_hash << ','
                << last.living << ',' << emerged << ',' << unemerged << ','
                << last.unmet << ',' << unmet_integral << ',' << demand_integral
                << ',' << supply_integral << ',' << last.adult_crop << ','
                << last.dead_crop << ',' << attempts << ',' << success << ','
                << partial << ',' << failed << ',' << given << ',' << intakes
                << ',' << switches << ',' << exits << ',' << decisions << ','
                << blocked << ',' << minimum << ',' << living_ms << ','
                << active_ms << ',' << away_ms << ',' << moves << ','
                << g.excavated_q3;
    const auto input = n.introduced.components(),
               accounted = n.accounted.components();
    for (std::size_t i = 0; i < 4; ++i) {
      require(input[i] == accounted[i], "ingredient imbalance");
      out.summary << ",0";
    }
    require(n.energy_input_nj == n.body_energy_nj + n.dissipated_energy_nj,
            "energy imbalance");
    require(g.initial_q3 == g.remaining_q3 + g.carried_q3 + g.deposited_q3,
            "soil imbalance");
    out.summary << ",0,0\n";
    out.summary.flush();
  }
};
void run(Output &out, const std::filesystem::path &dir,
         const std::string &suite, std::uint64_t seed,
         const std::string &policy, unsigned workers, std::uint64_t protein,
         std::uint32_t budget, SimTime minimum, const std::string &condition,
         bool mirror) {
  auto options = s6_fixture::correction_options(policy);
  options.workers = workers;
  options.source_protein_ug = protein;
  options.minimum_program_time = minimum;
  s6_fixture::Integrated fixture(seed, condition, mirror, budget, options);
  auto &w = fixture.world;
  const auto prefix = suite + ',' + std::to_string(seed) + ',' + policy + ',' +
                      std::to_string(workers) + ',' + std::to_string(protein) +
                      ',' + std::to_string(budget) + ',' +
                      std::to_string(minimum.milliseconds) + ',' + condition +
                      ',' + (mirror ? "1," : "0,");
  auto filename = prefix;
  std::replace(filename.begin(), filename.end(), ',', '-');
  const auto path = dir / (filename + "facts.bin");
  require(!std::filesystem::exists(path), "existing fact archive");
  Monitor monitor(w, out, prefix, workers, path);
  WorldRuntime fast({9, 9}, 0, {}, s6_fixture::limits()),
      restored({9, 8}, 0, {}, s6_fixture::limits());
  fast.restore(w.checkpoint());
  restored.restore(w.checkpoint());
  const std::int64_t duration = suite == "integrated" ? 600000 : 180000;
  for (std::int64_t t = 1000; t <= duration; t += 1000) {
    monitor.advance({t});
    monitor.sample(t);
    if (t % 30000 == 0) {
      fast.advance_to({t});
      restored.advance_to({t});
      const auto bytes = w.checkpoint();
      require(bytes == fast.checkpoint() && bytes == restored.checkpoint(),
              "observer slicing changed continuation");
      restored.restore(bytes);
    }
  }
  monitor.finish(duration);
  std::cout << "PASS S6.1 case " << prefix << '\n' << std::flush;
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc < 2 || argc > 4)
      throw std::invalid_argument("usage: antworld_s6_1_experiment OUTPUT_DIR "
                                  "[SEEDS=16] [matrix|sensitivity|integrated]");
    const std::string suite = argc > 3 ? argv[3] : "matrix";
    if (suite != "matrix" && suite != "sensitivity" && suite != "integrated")
      throw std::invalid_argument("unknown suite");
    const auto seeds = argc > 2 ? std::stoul(argv[2]) : 16UL;
    require(seeds && seeds <= (suite == "integrated" ? 32UL : 16UL),
            "invalid complete seed prefix");
    const std::filesystem::path dir = argv[1];
    require(!std::filesystem::exists(dir / "summary.csv"),
            "refusing to overwrite results");
    std::filesystem::create_directories(dir);
    Output out(dir);
    std::ofstream config(dir / "configuration.json");
    config.exceptions(std::ios::badbit | std::ios::failbit);
    config << "{\"scope\":\"ENGINEERING_FIXTURE\",\"protocol\":\"document 37 "
              "at 03ae833\",\"suite\":\""
           << suite << "\",\"first_seed\":1,\"seeds\":" << seeds
           << ",\"schema\":" << WorldRuntime::schema_version
           << ",\"physics\":" << WorldRuntime::physics_version
           << ",\"samples_ms\":1000,\"exhaustive_observer_ms\":10000,"
              "\"normal\":\"event-boundary advance with 1 s "
              "observations\",\"comparison_ms\":30000,"
              "\"history\":\"complete canonical facts in per-case binary; "
              "selected CSV and all kind counts\"}\n";
    for (std::uint64_t seed = 1; seed <= seeds; ++seed) {
      if (suite == "integrated") {
        for (const auto policy : {"legacy", "combined"})
          for (bool mirror : {false, true})
            for (const auto condition :
                 {"supplied", "protein_absent", "food_absent", "sealed"})
              run(out, dir, suite, seed, policy, 32, 2000, 16, {10000},
                  condition, mirror);
      } else if (suite == "matrix") {
        for (const auto policy :
             {"legacy", "gift_first", "local_continuation", "combined"})
          for (unsigned workers : {8U, 32U, 128U})
            for (std::uint64_t protein : {0U, 500U, 2000U})
              run(out, dir, suite, seed, policy, workers, protein, 16, {10000},
                  "supplied", false);
      } else {
        for (const auto policy : {"legacy", "combined"})
          for (const auto& setting :
               std::array<std::pair<std::uint32_t, std::int64_t>, 4>{
                   {{8, 10000}, {16, 5000}, {16, 20000}, {32, 10000}}})
            run(out, dir, suite, seed, policy, 32, 2000, setting.first,
                {setting.second}, "supplied", false);
      }
    }
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
