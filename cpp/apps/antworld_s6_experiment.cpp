#include "antworld/storage/store.hpp"
#include "s6_fixture.hpp"
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>

using namespace antworld;
using namespace antworld::storage;
using s3_fixture::require;
namespace {
using Clock = std::chrono::steady_clock;
using Values =
    std::array<std::uint64_t, static_cast<std::size_t>(Metric::Count)>;
double ms(Clock::time_point start) {
  return std::chrono::duration<double, std::milli>(Clock::now() - start)
      .count();
}
void configuration(const std::filesystem::path &dir, const std::string &suite,
                   unsigned long seeds, const std::string &policy,
                   unsigned long first) {
  std::ofstream f(dir / "configuration.json");
  f.exceptions(std::ios::badbit | std::ios::failbit);
  f << std::setprecision(17);
  const PhysiologyConfig p;
  const SocialConfig s;
  const BehaviorConfig b;
  const GeometryConfig g;
  const auto l = s6_fixture::limits();
  f << "{\n  \"scope\":\"ENGINEERING_FIXTURE\",\"suite\":\"" << suite
    << "\",\"seeds\":" << seeds << ",\"first_seed\":" << first << ",\n"
    << "  \"schema_version\":" << WorldRuntime::schema_version
    << ",\"physics_version\":" << WorldRuntime::physics_version << ",\n"
    << "  \"nursing_correction_policy\":\"" << policy << "\",\n"
    << "  "
       "\"world\":{\"id\":[6,8],\"bounds_m\":[[-1,-1,-1],[1,1,1]],\"speed_m_"
       "s\":0.01,\"contact_m\":0.002},\n"
    << "  "
       "\"population\":{\"queen\":1,\"workers\":32,\"eggs\":4,\"larvae\":6,"
       "\"pupae\":2,\"initial_position_m\":[0,0,0],\"carrying_ug\":4000,\"body_"
       "energy_nj_each\":1000000000,\"hydration_ug_each\":1000,\"crop_each\":["
       "0,0,0,0],\"pupal_tissue_protein_ug_each\":100},\n"
    << "  "
       "\"food_ingredients_ug_order\":[\"carbs\",\"protein\",\"water\","
       "\"other\"],\"food\":[{\"position_m\":[0.02,0,0.01],\"mass\":[1000,0,"
       "3000,0]},{\"position_m\":[-0.02,0,-0.01],\"mass\":[0,2000,2500,500]}],"
       "\n"
    << "  \"controls\":{\"mirror\":\"negate food "
       "X\",\"protein_absent_source_2\":[0,0,2500,2500],\"food_absent\":\"omit "
       "both sources\",\"sealed\":\"same food; omit passage and add rock "
       "shell\"},\n"
    << "  \"physiology\":{\"absorption_ms\":"
    << p.absorption_period.milliseconds
    << ",\"egg_ms\":" << p.egg_duration.milliseconds
    << ",\"larva_ms\":" << p.larva_duration.milliseconds
    << ",\"pupa_ms\":" << p.pupa_duration.milliseconds
    << ",\"behavior_ms\":" << p.behavior_interval.milliseconds
    << ",\"crop_capacity_ug\":" << p.crop_capacity_ug
    << ",\"hydration_capacity_ug\":" << p.hydration_capacity_ug
    << ",\"energy_capacity_nj\":" << p.energy_capacity_nj
    << ",\"carb_yield_nj_ug\":" << p.carbohydrate_yield_nj_per_ug
    << ",\"basal_nj_ms\":" << p.basal_nj_per_ms
    << ",\"active_nj_ms\":" << p.active_nj_per_ms
    << ",\"water_loss_ug_s\":" << p.water_loss_ug_per_period
    << ",\"carb_absorption_ug_s\":" << p.carb_absorption_ug_per_s
    << ",\"water_absorption_ug_s\":" << p.water_absorption_ug_per_s
    << ",\"protein_absorption_ug_s\":" << p.protein_absorption_ug_per_s
    << ",\"larval_protein_ug\":" << p.larval_protein_requirement_ug
    << ",\"gift_ug\":" << p.transfer_limit_ug << "},\n"
    << "  \"social\":{\"decision_ms\":" << s.decision_interval.milliseconds
    << ",\"minimum_program_ms\":" << s.minimum_program_time.milliseconds
    << ",\"weights_rest_forage_nurse_excavate\":[" << s.rest_weight << ','
    << s.forage_weight << ',' << s.nurse_weight << ',' << s.excavate_weight
    << "],\"budgets\":" << (suite == "sensitivity" ? "[8,16,32]" : "[16]")
    << ",\"adult_urgent_fraction\":0.25,\"crowding_others\":2},\n"
    << "  "
       "\"surface\":{\"origin_m\":[-0.03,0,-0.03],\"width\":7,\"height\":7,"
       "\"cell_m\":0.01,\"blocked\":[],\"trails\":true,\"memory\":true,"
       "\"sensing_radius_cells\":"
    << b.sensing_radius_cells << ",\"route_capacity\":" << b.route_capacity
    << ",\"max_trip_moves\":" << b.max_trip_moves
    << ",\"step_ms\":" << b.step_duration.milliseconds
    << ",\"decision_ms\":" << b.decision_delay.milliseconds
    << ",\"memory_ms\":" << b.memory_lifetime.milliseconds
    << ",\"field_ms\":" << b.field_interval.milliseconds
    << ",\"half_life_s\":" << b.trail_half_life_s
    << ",\"deposit_units\":" << b.deposit_units
    << ",\"cap_units\":" << b.trail_cap_units
    << ",\"cutoff_units\":" << b.trail_cutoff_units
    << ",\"weights_explore_persistence_trail\":[" << b.explore_weight << ','
    << b.persistence_weight << ',' << b.trail_weight << "]},\n"
    << "  \"geometry\":{\"quantum_m\":" << g.quantum_m
    << ",\"origin_m\":[-0.008,-0.006,-0.006],\"initial_solid_q\":[[0,0,0],[32,"
       "24,24]],\"chamber_q\":[[12,8,8],[20,16,16]],\"passage_q\":[[0,10,10],["
       "32,14,14]],\n"
    << "    "
       "\"sealed_rocks_q\":[[[10,6,6],[12,18,18]],[[20,6,6],[22,18,18]],[[12,6,"
       "6],[20,8,18]],[[12,16,6],[20,18,18]],[[12,8,6],[20,16,8]],[[12,8,16],["
       "20,16,18]]],\n"
    << "    \"dry_ug_q3\":" << g.dry_ug_per_q3
    << ",\"water_ug_q3\":" << g.water_ug_per_q3
    << ",\"body_half_q\":" << g.body_half_q
    << ",\"loaded_half_q\":" << g.loaded_half_q << ",\"reach_q\":" << g.reach_q
    << ",\"max_patch_q\":" << g.max_patch_extent_q
    << ",\"brick_q\":" << g.brick_q << ",\"sample_step_q\":" << g.sample_step_q
    << ",\"sdf_band_q\":" << g.sdf_band_q
    << ",\"work_ms\":" << g.work_duration.milliseconds
    << ",\"move_ms\":" << g.move_duration.milliseconds
    << ",\"decision_ms\":" << g.decision_delay.milliseconds
    << ",\"dig_nj_q3\":" << g.dig_energy_nj_per_q3 << "},\n"
    << "  \"host\":{\"committed_events\":" << l.committed_events
    << ",\"events_per_timestamp\":" << l.events_per_timestamp
    << ",\"checkpoint_bytes\":" << l.checkpoint_bytes << "},\n"
    << "  "
       "\"observation\":{\"normal_step_ms\":1000,\"time_series_ms\":10000,"
       "\"accelerated_step_ms\":60000,\"save_interval_ms\":60000,\"retained_"
       "checkpoints\":2,\"history_policy\":\"retain all committed "
       "facts\"}\n}\n";
}
struct Evidence {
  EventId cursor;
  Values flows{};
  std::map<EventId, GeometryEdit> edits;
  void update(const WorldRuntime &w) {
    const auto geometry = w.geometry_snapshot();
    for (const auto &edit : w.geometry_edits())
      edits.insert_or_assign(edit.event, edit);
    for (const auto &event : w.events_after(cursor, 1000000)) {
      for (const auto &value : contributions(
               event, geometry,
               edits.contains(event.id) ? &edits.at(event.id) : nullptr))
        if (!value.owner.value)
          flows[static_cast<std::size_t>(value.metric)] = checked_add(
              flows[static_cast<std::size_t>(value.metric)], value.value);
      cursor = event.id;
    }
  }
  Values values(const WorldRuntime &w) const {
    auto result = flows;
    for (const auto &value : observe(w).values)
      if (!value.owner.value)
        result[static_cast<std::size_t>(value.metric)] = value.value;
    return result;
  }
};
struct Output {
  std::ofstream summary, series, individuals, events, geometry, foods, counts;
  explicit Output(const std::filesystem::path &dir)
      : summary(dir / "summary.csv"), series(dir / "time_series.csv"),
        individuals(dir / "individuals.csv"), events(dir / "events.csv"),
        geometry(dir / "geometry.csv"), foods(dir / "foods.csv"),
        counts(dir / "event_counts.csv") {
    for (auto *f : {&summary, &series, &individuals, &events, &geometry, &foods,
                    &counts}) {
      f->exceptions(std::ios::badbit | std::ios::failbit);
      *f << std::setprecision(17);
    }
    summary
        << "scope,suite,seed,condition,mirror,encounter_budget,mode,simulation_"
           "ms,schema_version,physics_version,exact_continuation,state_hash,"
           "trace_hash,events,pending_events,rng_state,checkpoint_bytes,"
           "database_bytes,setup_ms,advance_ms,save_ms,load_ms,contact_"
           "decisions,contact_candidates,maximum_candidates,explored_cells,"
           "discovered_sources,food_collections,food_deliveries,excavated_q3,"
           "filled_q3,soil_initial_q3,soil_remaining_q3,soil_carried_q3,soil_"
           "deposited_q3,carbs_introduced_ug,protein_introduced_ug,water_"
           "introduced_ug,other_introduced_ug,energy_input_nj,carb_residual_ug,"
           "protein_residual_ug,water_residual_ug,other_residual_ug,energy_"
           "residual_nj,soil_residual_q3";
    series
        << "suite,seed,condition,mirror,encounter_budget,time_ms,event_cursor";
    for (const auto &d : metric_definitions()) {
      summary << ',' << d.name;
      series << ',' << d.name;
    }
    summary << '\n';
    series << '\n';
    const char *prefix = "suite,seed,condition,mirror,encounter_budget,";
    individuals << prefix
                << "entity_id,caste,seed_stage,final_stage,larva_ms,pupa_ms,"
                   "adult_ms,death_ms,death_cause,crop_carbs_ug,crop_protein_"
                   "ug,crop_water_ug,crop_other_ug,body_energy_nj,hydration_ug,"
                   "tissue_protein_ug,received_protein_ug,given_protein_ug,"
                   "path_m,paused_ms,rest_ms,nurse_ms,forage_ms,excavate_ms,"
                   "autonomy_decisions,final_x_m,final_y_m,final_z_m\n";
    events << prefix
           << "event_id,source_id,time_ms,kind,actor_id,colony_id,resource_id,"
              "payload,x_m,y_m,z_m,carbs_ug,protein_ug,water_ug,other_ug,stage,"
              "outcome\n";
    geometry << prefix
             << "edit_id,event_id,source_id,actor_id,parcel_id,time_ms,kind,"
                "min_x_q,min_y_q,min_z_q,max_x_q,max_y_q,max_z_q,volume_q3\n";
    foods << prefix
          << "resource_id,x_m,y_m,z_m,initial_carbs_ug,initial_protein_ug,"
             "initial_water_ug,initial_other_ug,remaining_carbs_ug,remaining_"
             "protein_ug,remaining_water_ug,remaining_other_ug\n";
    counts << prefix << "kind,events\n";
  }
};
void reconcile(Store &store, const WorldRuntime &w, const Evidence &evidence) {
  const auto meta = w.summary();
  const auto values = evidence.values(w);
  for (const auto &value : observe(w).values) {
    const auto rows = store.series(meta.world, value.owner, value.metric,
                                   meta.now, {meta.now.milliseconds + 1});
    require(!rows.empty() && rows.back().value == value.value &&
                rows.back().cursor.value == meta.committed_events,
            "stored gauge does not match actual state");
  }
  for (const auto &definition : metric_definitions())
    if (definition.kind == MetricKind::Flow)
      require(store.flow_total(meta.world, {}, definition.id, {0},
                               {meta.now.milliseconds + 1}) ==
                  values[static_cast<std::size_t>(definition.id)],
              "stored flow does not match actual events");
  const auto facts = w.committed_events();
  std::size_t index = 0;
  EventId cursor;
  for (;;) {
    const auto page =
        store.history({meta.world, cursor, {0}, {INT64_MAX}, {}, {}, 4096});
    if (page.empty())
      break;
    for (const auto &row : page) {
      require(index < facts.size() && row.fact == facts[index],
              "durable history differs from committed event");
      require(row.related ==
                  EntityId{row.fact.kind == FactKind::NutritionTransferred
                               ? row.fact.payload
                               : 0},
              "wrong recipient evidence link");
      if (evidence.edits.contains(row.fact.id))
        require(row.geometry_edit == evidence.edits.at(row.fact.id).id,
                "wrong geometry evidence link");
      ++index;
      cursor = row.fact.id;
    }
  }
  require(index == facts.size(), "durable history omitted facts");
  for (const auto &ant : w.ant_states()) {
    const auto identity = store.individual({meta.world, ant.id});
    require(identity && identity->current_stage == ant.stage &&
                identity->colony == ant.colony &&
                identity->caste == ant.caste &&
                identity->created_at == ant.born_at && identity->seeded,
            "durable identity discontinuity");
    require((ant.stage == LifeStage::Dead) == identity->died_at.has_value(),
            "durable death evidence mismatch");
  }
}
void write_history(Output &out, const std::string &prefix,
                   const WorldRuntime &w) {
  struct Person {
    LifeStage seeded{};
    std::array<std::int64_t, 4> transition{{-1, -1, -1, -1}};
    std::uint64_t cause{}, received{}, given{};
    PositionM position;
    double path{};
    IndividualBehavior program{IndividualBehavior::Paused};
    SimTime changed;
    std::array<std::int64_t, 5> residence{};
  };
  std::map<EntityId, Person> people;
  std::map<FactKind, std::uint64_t> counts;
  for (const auto &e : w.committed_events()) {
    ++counts[e.kind];
    if (e.kind == FactKind::AntSeeded) {
      auto &a = people[e.actor];
      a.seeded = e.stage;
      a.position = e.position;
    }
    if (e.kind == FactKind::Moved) {
      auto &a = people.at(e.actor);
      a.path +=
          std::hypot(e.position.x - a.position.x, e.position.y - a.position.y,
                     e.position.z - a.position.z);
      a.position = e.position;
    }
    if (e.kind == FactKind::StageChanged)
      people.at(e.actor).transition[static_cast<unsigned>(e.stage) - 1] =
          e.time.milliseconds;
    if (e.kind == FactKind::AntDied) {
      auto &a = people.at(e.actor);
      a.transition[3] = e.time.milliseconds;
      a.cause = e.payload;
    }
    if (e.kind == FactKind::NutritionTransferred) {
      people.at(e.actor).given += e.transferred.protein_ug;
      people.at(EntityId{e.payload}).received += e.transferred.protein_ug;
    }
    if (e.kind == FactKind::BehaviorChanged || e.kind == FactKind::AntDied) {
      auto &a = people.at(e.actor);
      a.residence[static_cast<unsigned>(a.program)] +=
          e.time.milliseconds - a.changed.milliseconds;
      a.changed = e.time;
      a.program = e.kind == FactKind::AntDied
                      ? IndividualBehavior::Paused
                      : static_cast<IndividualBehavior>(e.payload);
    }
    const bool selected =
        e.kind == FactKind::FoodCollected ||
        e.kind == FactKind::FoodDelivered ||
        e.kind == FactKind::CargoIngested || e.kind == FactKind::NestIngested ||
        e.kind == FactKind::NutritionTransferred ||
        e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied ||
        e.kind == FactKind::BehaviorChanged ||
        (e.kind >= FactKind::SoilExcavated && e.kind <= FactKind::SoilFilled);
    if (selected)
      out.events << prefix << e.id.value << ',' << e.source.value << ','
                 << e.time.milliseconds << ',' << static_cast<unsigned>(e.kind)
                 << ',' << e.actor.value << ',' << e.colony.value << ','
                 << e.resource.value << ',' << e.payload << ',' << e.position.x
                 << ',' << e.position.y << ',' << e.position.z << ','
                 << e.transferred.carbs_ug << ',' << e.transferred.protein_ug
                 << ',' << e.transferred.water_ug << ','
                 << e.transferred.other_ug << ','
                 << static_cast<unsigned>(e.stage) << ','
                 << static_cast<unsigned>(e.outcome) << '\n';
  }
  for (const auto &ant : w.ant_states()) {
    auto a = people.at(ant.id);
    const auto p = *w.query_physiology({w.summary().world, ant.id});
    if (ant.alive())
      a.residence[static_cast<unsigned>(a.program)] +=
          w.summary().now.milliseconds - a.changed.milliseconds;
    out.individuals << prefix << ant.id.value << ','
                    << static_cast<unsigned>(ant.caste) << ','
                    << static_cast<unsigned>(a.seeded) << ','
                    << static_cast<unsigned>(ant.stage);
    for (auto t : a.transition)
      out.individuals << ',' << t;
    out.individuals << ',' << a.cause << ',' << p.crop.carbs_ug << ','
                    << p.crop.protein_ug << ',' << p.crop.water_ug << ','
                    << p.crop.other_ug << ',' << p.body_energy_nj << ','
                    << p.hydration_ug << ',' << p.tissue_protein_ug << ','
                    << a.received << ',' << a.given << ',' << a.path;
    for (auto duration : a.residence)
      out.individuals << ',' << duration;
    const auto automatic = w.query_autonomy({w.summary().world, ant.id});
    out.individuals << ',' << (automatic ? automatic->decisions : 0) << ','
                    << ant.position.x << ',' << ant.position.y << ','
                    << ant.position.z << '\n';
  }
  for (const auto &e : w.geometry_edits())
    out.geometry << prefix << e.id.value << ',' << e.event.value << ','
                 << e.source.value << ',' << e.actor.value << ','
                 << e.parcel.value << ',' << e.time.milliseconds << ','
                 << static_cast<unsigned>(e.kind) << ',' << e.box.min.x << ','
                 << e.box.min.y << ',' << e.box.min.z << ',' << e.box.max.x
                 << ',' << e.box.max.y << ',' << e.box.max.z << ','
                 << e.volume_q3 << '\n';
  for (const auto &food : w.food_sources()) {
    out.foods << prefix << food.id.value << ',' << food.position.x << ','
              << food.position.y << ',' << food.position.z;
    for (auto v : food.initial.components())
      out.foods << ',' << v;
    for (auto v : food.remaining.components())
      out.foods << ',' << v;
    out.foods << '\n';
  }
  for (const auto &[kind, count] : counts)
    out.counts << prefix << static_cast<unsigned>(kind) << ',' << count << '\n';
}
void run(Output &out, const std::filesystem::path &dir,
         const std::string &suite, std::uint64_t seed,
         const std::string &condition, bool mirror, std::uint32_t budget,
         const std::string &policy) {
  const auto start = Clock::now();
  s6_fixture::Integrated fixture(seed, condition, mirror, budget,
                                 s6_fixture::correction_options(policy));
  auto &normal = fixture.world;
  WorldRuntime fast({9, 9}, 0, {}, s6_fixture::limits());
  fast.restore(normal.checkpoint());
  const auto prefix = suite + ',' + std::to_string(seed) + ',' + condition +
                      ',' + (mirror ? "1," : "0,") + std::to_string(budget) +
                      ',';
  const auto path = dir / (std::to_string(seed) + "-" + condition + "-" +
                           (mirror ? "mirror-" : "original-") +
                           std::to_string(budget) + ".sqlite");
  require(!std::filesystem::exists(path),
          "refusing to overwrite a retained experiment database");
  Store store(path, s6_fixture::limits());
  auto token = store.save(normal);
  auto recovered = store.load(token.world);
  const auto setup = ms(start);
  std::array<double, 3> advance{};
  double save_time = 0, load_time = 0;
  const std::int64_t end = suite == "long"    ? 1800000
                           : suite == "smoke" ? 60000
                                              : 600000;
  Evidence evidence;
  auto sample = [&] {
    s6_fixture::balanced(normal);
    evidence.update(normal);
    out.series << prefix << normal.summary().now.milliseconds << ','
               << evidence.cursor.value;
    for (auto v : evidence.values(normal))
      out.series << ',' << v;
    out.series << '\n';
  };
  sample();
  for (std::int64_t t = 60000; t <= end; t += 60000) {
    for (std::int64_t at = t - 59000; at <= t; at += 1000) {
      const auto begin = Clock::now();
      normal.advance_to({at});
      advance[0] += ms(begin);
      if (at % 10000 == 0)
        sample();
    }
    auto begin = Clock::now();
    fast.advance_to({t});
    advance[1] += ms(begin);
    begin = Clock::now();
    recovered.world.advance_to({t});
    advance[2] += ms(begin);
    const auto bytes = normal.checkpoint();
    require(bytes == fast.checkpoint() && bytes == recovered.world.checkpoint(),
            "host slicing changed canonical ecology");
    begin = Clock::now();
    token = store.save(recovered.world, token);
    save_time += ms(begin);
    begin = Clock::now();
    recovered = store.load(token.world);
    load_time += ms(begin);
    require(bytes == recovered.world.checkpoint(),
            "durable recovery changed ecology");
  }
  reconcile(store, normal, evidence);
  write_history(out, prefix, normal);
  store.checkpoint_wal();
  const auto metadata = normal.snapshot();
  const auto n = normal.nutrition_snapshot();
  const auto g = normal.geometry_snapshot().ledger;
  const auto surface = normal.surface_snapshot();
  const auto contacts = normal.contact_work();
  const auto bytes = normal.checkpoint().size();
  std::size_t mode = 0;
  for (const auto label : {"normal", "accelerated", "recovered"}) {
    out.summary
        << "ENGINEERING_FIXTURE," << prefix << label << ',' << end << ','
        << WorldRuntime::schema_version << ',' << WorldRuntime::physics_version
        << ",1," << metadata.state_hash << ',' << metadata.trace_hash << ','
        << metadata.committed_events << ',' << metadata.pending_events << ','
        << metadata.rng_state << ',' << bytes << ',' << store.database_bytes()
        << ',' << setup << ',' << advance[mode++] << ',' << save_time << ','
        << load_time << ',' << contacts.decisions << ','
        << contacts.candidates_examined << ',' << contacts.maximum_candidates
        << ',' << normal.visits().size() << ',' << surface.discovered_sources
        << ',' << surface.counters.collections << ','
        << surface.counters.deliveries << ',' << g.excavated_q3 << ','
        << g.filled_q3 << ',' << g.initial_q3 << ',' << g.remaining_q3 << ','
        << g.carried_q3 << ',' << g.deposited_q3 << ',' << n.introduced.carbs_ug
        << ',' << n.introduced.protein_ug << ',' << n.introduced.water_ug << ','
        << n.introduced.other_ug << ',' << n.energy_input_nj << ','
        << n.introduced.carbs_ug - n.accounted.carbs_ug << ','
        << n.introduced.protein_ug - n.accounted.protein_ug << ','
        << n.introduced.water_ug - n.accounted.water_ug << ','
        << n.introduced.other_ug - n.accounted.other_ug << ','
        << n.energy_input_nj - n.body_energy_nj - n.dissipated_energy_nj << ','
        << g.initial_q3 - g.remaining_q3 - g.carried_q3 - g.deposited_q3;
    for (auto v : evidence.values(normal))
      out.summary << ',' << v;
    out.summary << '\n';
  }
  out.summary.flush();
  std::cout << "PASS case " << prefix << end << " ms\n" << std::flush;
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc < 2 || argc > 6)
      throw std::invalid_argument(
          "usage: antworld_s6_experiment OUTPUT_DIR [SEEDS=32] "
          "[primary|sensitivity|long|smoke] "
          "[legacy|gift_first|local_continuation|combined] [FIRST_SEED=1]");
    const std::string suite = argc > 3 ? argv[3] : "primary";
    const std::string policy = argc > 4 ? argv[4] : "legacy";
    (void)s6_fixture::correction_options(policy);
    if (suite != "primary" && suite != "sensitivity" && suite != "long" &&
        suite != "smoke")
      throw std::invalid_argument("unknown suite");
    const auto maximum = suite == "primary"       ? 32UL
                         : suite == "sensitivity" ? 16UL
                         : suite == "long"        ? 8UL
                                                  : 1UL;
    const auto seeds = argc > 2 ? std::stoul(argv[2]) : maximum;
    const auto first = argc > 5 ? std::stoul(argv[5]) : 1UL;
    if (!first || first > maximum || !seeds || seeds > maximum - first + 1)
      throw std::invalid_argument("invalid frozen seed range");
    std::filesystem::path dir = argv[1];
    if (suite == "smoke")
      dir /= ("run-" + std::to_string(Clock::now().time_since_epoch().count()));
    require(!std::filesystem::exists(dir / "summary.csv"),
            "refusing to overwrite raw experimental results");
    std::filesystem::create_directories(dir);
    configuration(dir, suite, seeds, policy, first);
    Output out(dir);
    for (std::uint64_t seed = first; seed < first + seeds; ++seed)
      for (bool mirror : {false, true})
        for (const auto condition :
             {"supplied", "protein_absent", "food_absent", "sealed"}) {
          if (suite == "long" &&
              (mirror || (std::string(condition) != "supplied" &&
                          std::string(condition) != "food_absent")))
            continue;
          if ((suite == "sensitivity" || suite == "smoke") &&
              (mirror || std::string(condition) != "supplied"))
            continue;
          const std::vector<std::uint32_t> budgets =
              suite == "sensitivity" ? std::vector<std::uint32_t>{8, 16, 32}
                                     : std::vector<std::uint32_t>{16};
          for (auto budget : budgets)
            run(out, dir, suite, seed, condition, mirror, budget, policy);
        }
    std::cout << "PASS S6 integrated ecological evidence: " << suite << '\n';
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
