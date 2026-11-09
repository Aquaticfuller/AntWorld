#include "antworld/core/inspection.hpp"
#include "s6_3_1_fixture.hpp"
#include <algorithm>
#include <iostream>
using namespace antworld;
using s3_fixture::require;
namespace {
struct Tiny {
  WorldRuntime w{{631, 1}, 7};
  ColonyRef colony;
  AntRef queen;
  PhysiologyConfig p;
  Tiny(std::uint64_t energy = 1000, std::uint64_t water = 100,
       SimTime horizon = {10}, bool wall = false) {
    w.configure_long_term();
    if (wall) {
      GeometryConfig g;
      g.origin_m = {-.01, -.01, -.01};
      g.initial_solid = {{0, 0, 0}, {40, 40, 40}};
      const std::array<BoxQ, 2> voids{
          {{{18, 18, 18}, {22, 22, 22}}, {{24, 18, 18}, {28, 22, 22}}}};
      w.configure_geometry(g, voids);
    }
    w.configure_social();
    colony = w.seed_colony();
    queen = w.seed_ant(colony, {{}, LifeStage::Adult, Caste::Queen});
    p.absorption_period = {10};
    p.behavior_interval = {10};
    p.water_loss_period = {10};
    p.energy_capacity_nj = 2000;
    p.basal_nj_per_ms = 1;
    p.active_nj_per_ms = 0;
    p.hydration_capacity_ug = 200;
    p.carbohydrate_yield_nj_per_ug = 1;
    p.carb_absorption_ug_per_s = 100000;
    p.water_absorption_ug_per_s = 100000;
    p.adult_protein_target_ug = 20;
    w.enable_physiology(queen, {{0, 100, 0, 0}, energy, water, 0}, p);
    ReproductionConfig r;
    r.interval = {10};
    r.egg_energy_nj = 100;
    r.dissipated_energy_nj = 10;
    r.egg_water_ug = 10;
    r.maintenance_horizon = horizon;
    w.enable_reproduction(queen, r);
  }
  AntRef donor(PositionM position = {}) {
    auto a = w.seed_ant(colony, {position});
    auto config = p;
    config.adult_protein_target_ug = 0;
    config.absorption_period = {1000};
    w.enable_physiology(a, {{100, 0, 0, 0}, 1000, 100, 0}, config);
    return a;
  }
};
void roundtrip(WorldRuntime &w, SimTime end) {
  auto bytes = w.checkpoint();
  WorldRuntime replay({9, 9}, 0, {}, s6_3_fixture::limits());
  replay.restore(bytes);
  require(bytes == replay.checkpoint(),
          "new allocation checkpoint changed on restore");
  w.advance_to(end);
  replay.advance_to({end.milliseconds - 1});
  replay.advance_to(end);
  require(w.checkpoint() == replay.checkpoint(),
          "allocation continuation differs");
  s6_3_fixture::conserved(w);
}
void funding() {
  Tiny equality(130), sufficient(131), water_equal(1000, 12),
      water_sufficient(1000, 13);
  for (auto *f : {&equality, &sufficient, &water_equal, &water_sufficient})
    f->w.advance_to({10});
  require(equality.w.query_reproduction(equality.queen)->births == 0,
          "strict energy reserve boundary failed");
  auto p = *equality.w.query_physiology(equality.queen);
  require(p.body_energy_nj == 120 && p.crop.protein_ug == 100 &&
              !p.exported_energy_nj,
          "deferred attempt spent resources");
  require(sufficient.w.query_reproduction(sufficient.queen)->births == 1,
          "funded birth incorrectly blocked");
  require(sufficient.w.query_physiology(sufficient.queen)->body_energy_nj == 11,
          "funded maternal balance differs");
  require(water_equal.w.query_reproduction(water_equal.queen)->births == 0,
          "strict water reserve boundary failed");
  require(
      water_sufficient.w.query_reproduction(water_sufficient.queen)->births ==
          1,
      "funded water incorrectly blocked");
  for (auto *f : {&equality, &sufficient, &water_equal, &water_sufficient})
    s6_3_fixture::conserved(f->w);
}
void pulse() {
  Tiny legacy(125, 100, {}), guarded(125);
  for (auto *f : {&legacy, &guarded}) {
    auto donor = f->donor();
    f->w.submit_nutrition(
        {donor, {11}, NutritionAction::Trophallaxis, f->queen, 100});
    f->w.advance_to({15});
  }
  require(!legacy.w.query_ant(legacy.queen)->alive(),
          "legacy pre-absorption death changed");
  require(legacy.w.query_physiology(legacy.queen)->crop.carbs_ug == 100,
          "crop/body energy conflated");
  require(guarded.w.query_ant(guarded.queen)->alive(),
          "deferred egg did not retain actual body reserve");
  guarded.w.advance_to({20});
  require(guarded.w.query_reproduction(guarded.queen)->births == 1,
          "real absorption failed to resume reproduction");
  roundtrip(guarded.w, {50});
  Tiny empty(125);
  empty.w.advance_to({126});
  require(!empty.w.query_ant(empty.queen)->alive(),
          "reserve rule guaranteed survival without input");
  require(empty.w.query_reproduction(empty.queen)->births == 0,
          "insufficient queen laid eggs");
}
void barrier() {
  Tiny f(125, 100, {10}, true);
  auto donor = f.donor({.003, 0, 0});
  require(!f.w.spatially_clear({}, {.003, 0, 0}), "fixture barrier is open");
  f.w.submit_nutrition(
      {donor, {11}, NutritionAction::Trophallaxis, f.queen, 100});
  f.w.advance_to({20});
  require(!f.w.query_physiology(f.queen)->crop.carbs_ug &&
              !f.w.query_reproduction(f.queen)->births,
          "queen gift crossed solid barrier");
  bool rejected = false;
  for (const auto &e : f.w.committed_events())
    if (e.kind == FactKind::ActionRejected && e.outcome == Outcome::OutOfReach)
      rejected = true;
  require(rejected, "blocked contact missing evidence");
  s6_3_fixture::conserved(f.w);
}
void rehash(std::vector<std::uint8_t> &bytes) {
  std::uint64_t h = UINT64_C(14695981039346656037);
  for (std::size_t i = 0; i < bytes.size() - 8; ++i)
    h = (h ^ bytes[i]) * UINT64_C(1099511628211);
  for (unsigned i = 0; i < 8; ++i)
    bytes[bytes.size() - 8 + i] = static_cast<std::uint8_t>(h >> (8 * i));
}
void corruption() {
  Tiny f;
  f.w.advance_to({10});
  const auto before = f.w.checkpoint();
  require(before[6] == 'A', "allocation reused legacy checkpoint schema");
  for (auto fact : f.w.committed_events())
    if (fact.kind == FactKind::ReproductionEnabled) {
      auto original = encode_event(fact);
      ++fact.payload;
      auto forged = encode_event(fact);
      auto bytes = before;
      auto at = std::search(bytes.begin(), bytes.end(), original.begin(),
                            original.end());
      require(at != bytes.end(), "enrollment evidence missing");
      std::copy(forged.begin(), forged.end(), at);
      rehash(bytes);
      bool caught = false;
      try {
        f.w.restore(bytes);
      } catch (const std::exception &) {
        caught = true;
      }
      require(caught && f.w.checkpoint() == before,
              "rechecksummed allocation forgery replaced authority");
    }
  roundtrip(f.w, {20});
}
void controls() {
  s6_3_1_fixture::Controls config;
  config.reserve_mode = 1;
  s6_3_1_fixture::World guarded(1, 8, "balanced", false, {}, 6, false, config),
      legacy(1);
  guarded.world.advance_to({30 * s6_3_fixture::day});
  bool provisioned = false;
  for (const auto &e : guarded.world.committed_events())
    if (e.kind == FactKind::NutritionTransferred &&
        e.payload == guarded.queen.id.value)
      provisioned = true;
  require(provisioned, "autonomous workers never supplied the local queen");
  roundtrip(guarded.world, {31 * s6_3_fixture::day});
  config.laying = false;
  s6_3_1_fixture::World suppressed(1, 8, "balanced", false, {}, 6, false,
                                   config);
  config.reserve_mode = 0;
  s6_3_1_fixture::World reference(1, 8, "balanced", false, {}, 6, false,
                                  config);
  suppressed.world.advance_to({7 * s6_3_fixture::day});
  reference.world.advance_to({7 * s6_3_fixture::day});
  require(suppressed.world.checkpoint() == reference.world.checkpoint(),
          "allocation changed suppressed control");
  require(legacy.world.checkpoint()[6] == '9', "legacy schema migrated");
}
void validation() {
  WorldRuntime w({631, 9}, 1);
  w.configure_long_term();
  w.configure_social();
  auto colony = w.seed_colony();
  auto queen = w.seed_ant(colony, {{}, LifeStage::Adult, Caste::Queen});
  PhysiologyConfig p;
  p.adult_protein_target_ug = 20;
  p.basal_nj_per_ms = 1000000000;
  w.enable_physiology(queen, {}, p);
  auto before = w.checkpoint();
  for (auto horizon :
       {INT64_C(-1), INT64_C(31536000001), INT64_C(31536000000)}) {
    ReproductionConfig c;
    c.maintenance_horizon = {horizon};
    bool failed = false;
    try {
      w.enable_reproduction(queen, c);
    } catch (const std::exception &) {
      failed = true;
    }
    require(failed && w.checkpoint() == before,
            "invalid/overflowed reserve changed world");
  }
}
void observe() {
  s6_3_1_fixture::World a(1), b(1);
  std::vector<inspection::Decision> observations;
  {
    inspection::Scope scope(a.queen.world, a.queen.id, observations);
    a.world.advance_to({7 * s6_3_fixture::day});
  }
  b.world.advance_to({s6_3_fixture::day});
  b.world.advance_to({7 * s6_3_fixture::day});
  require(!observations.empty(), "observer recorded no decisions");
  require(a.world.checkpoint() == b.world.checkpoint(),
          "observer or partition changed authority");
  require(!inspection::target.output, "observer scope leaked");
  for (const auto &o : observations) {
    require(o.actor != a.queen.id.value, "queen entered worker policy");
    require(o.candidates <= a.world.social_config()->encounter_budget,
            "observer exceeded encounter bound");
  }
  s6_3_1_fixture::World failed(2);
  const auto before = failed.world.checkpoint();
  bool caught = false;
  try {
    inspection::Scope invalid(failed.queen.world, EntityId{99999},
                              observations);
    failed.world.advance_to({s6_3_fixture::day});
  } catch (const std::logic_error &) {
    caught = true;
    observations.clear();
  }
  require(caught && failed.world.checkpoint() == before,
          "observer failure escaped rollback");
  s6_3_fixture::conserved(a.world);
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      throw std::invalid_argument("one S6.3.1 case required");
    const std::string_view mode = argv[1];
    if (mode == "OBSERVER")
      observe();
    else if (mode == "FUNDING")
      funding();
    else if (mode == "PULSE")
      pulse();
    else if (mode == "BARRIER")
      barrier();
    else if (mode == "CORRUPTION")
      corruption();
    else if (mode == "CONTROLS")
      controls();
    else if (mode == "VALIDATION")
      validation();
    else
      throw std::invalid_argument("unknown S6.3.1 test");
    std::cout << "PASS " << argv[1] << '\n';
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
