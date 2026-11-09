#include "s6_3_fixture.hpp"
#include <algorithm>
#include <iostream>
#include <string_view>
using namespace antworld;
using s3_fixture::require;
namespace {
struct Tiny {
  WorldRuntime w;
  ColonyRef colony;
  AntRef queen;
  Tiny(std::uint64_t protein = 10, RuntimeLimits limits = {})
      : w({63, 2}, 7, {}, limits) {
    w.configure_long_term();
    SocialConfig s;
    s.decision_interval = {100};
    w.configure_social(s);
    colony = w.seed_colony();
    queen = w.seed_ant(colony, {{}, LifeStage::Adult, Caste::Queen});
    PhysiologyConfig p;
    p.absorption_period = {10};
    p.egg_duration = {10};
    p.larva_duration = {20};
    p.pupa_duration = {10};
    p.water_loss_period = {3600000};
    p.basal_nj_per_ms = 0;
    p.active_nj_per_ms = 0;
    p.water_loss_ug_per_period = 0;
    p.larval_protein_requirement_ug = 1;
    p.adult_protein_target_ug = 1;
    w.enable_physiology(queen, {{0, protein, 0, 0}, 1000000000, 1000, 0}, p);
    ReproductionConfig r;
    r.interval = {50};
    r.egg_protein_ug = 1;
    r.egg_water_ug = 10;
    r.egg_energy_nj = 1000000;
    r.dissipated_energy_nj = 1000;
    w.enable_reproduction(queen, r);
  }
};
void roundtrip(WorldRuntime &w, SimTime next) {
  s6_3_fixture::conserved(w);
  const auto bytes = w.checkpoint();
  WorldRuntime restored({9, 9}, 0, {}, s6_3_fixture::limits());
  restored.restore(bytes);
  require(restored.checkpoint() == bytes, "long-term byte restore mismatch");
  w.advance_to(next);
  restored.advance_to(next);
  require(w.checkpoint() == restored.checkpoint(),
          "long-term continuation mismatch");
  s6_3_fixture::conserved(w);
}
void run(std::string_view name) {
  if (name == "BIRTH") {
    Tiny f;
    const auto n = f.w.nutrition_snapshot();
    f.w.advance_to({90});
    require(f.w.ant_states().size() == 2, "missing endogenous egg");
    const auto a = f.w.ant_states()[1];
    require(a.born_at == SimTime{50} && a.stage == LifeStage::Adult,
            "continuous birth development failed");
    const auto p = *f.w.query_physiology({f.w.summary().world, a.id});
    require(p.mother == f.queen.id, "maternal identity missing");
    require(n.introduced == f.w.nutrition_snapshot().introduced,
            "birth created external nutrients");
    roundtrip(f.w, {160});
  } else if (name == "SHORTFALL") {
    Tiny f(0);
    f.w.advance_to({200});
    require(f.w.ant_states().size() == 1, "unfunded egg appeared");
    roundtrip(f.w, {250});
  } else if (name == "QUEEN_DEATH") {
    Tiny f;
    f.w.schedule_lifecycle(f.queen, {50}, LifeStage::Dead);
    f.w.advance_to({200});
    require(f.w.ant_states().size() == 1 &&
                !f.w.query_reproduction(f.queen)->wake.value,
            "dead queen reproduced");
    roundtrip(f.w, {250});
  } else if (name == "RESERVE") {
    Tiny f;
    const auto food = f.w.seed_food({}, {1, 1, 1, 1});
    ResourceCycleConfig c;
    c.reserve = {5, 7, 9, 2};
    c.release_limit = {3, 4, 5, 1};
    c.interval = {10};
    c.productive_span = {20};
    c.cyclic = true;
    f.w.configure_resource_cycle(food, c);
    f.w.advance_to({30});
    require(f.w.query_resource_cycle(food)->released == FoodMass{3, 4, 5, 1},
            "dry interval released food");
    roundtrip(f.w, {100});
    require(f.w.resource_reserves() == FoodMass{},
            "finite reserve did not exhaust");
  } else if (name == "REMAINDER") {
    Tiny f;
    const auto ant = f.w.seed_ant(f.colony, {});
    PhysiologyConfig p;
    p.water_loss_period = {3600000};
    p.absorption_period = {3600000};
    p.basal_nj_per_ms = 0;
    f.w.schedule_lifecycle(f.queen, {0}, LifeStage::Dead);
    f.w.enable_physiology(ant, {}, p);
    f.w.advance_to({1800000});
    require(f.w.query_physiology(ant)->hydration_ug == 1000 &&
                f.w.query_physiology(ant)->water_loss_remainder == 1800000,
            "fractional water loss rounded away");
    roundtrip(f.w, {3600000});
    require(f.w.query_physiology(ant)->hydration_ug == 999,
            "water period integration mismatch");
  } else if (name == "RECYCLE") {
    Tiny f;
    const auto ant = f.w.seed_ant(f.colony, {});
    f.w.enable_physiology(ant, {{0, 40, 0, 0}, 1000000000, 1000, 0});
    f.w.submit_nutrition({ant, {1}, NutritionAction::ReturnProtein, {}, 30});
    f.w.advance_to({1});
    require(f.w.colonies()[0].nest_food.protein_ug == 30 &&
                f.w.query_physiology(ant)->crop.protein_ug == 10,
            "protein return is not a real transfer");
    roundtrip(f.w, {20});
  } else if (name == "ROLLBACK") {
    RuntimeLimits l;
    l.entities = 2;
    Tiny f(10, l);
    const auto before = f.w.checkpoint();
    bool failed = false;
    try {
      f.w.advance_to({50});
    } catch (const std::length_error &) {
      failed = true;
    }
    require(failed && f.w.checkpoint() == before,
            "birth capacity failure partially committed");
  } else if (name == "MONTH") {
    s6_3_fixture::World f(1);
    f.world.advance_to({s6_3_fixture::day});
    roundtrip(f.world, {2 * s6_3_fixture::day});
    auto bytes = f.world.checkpoint();
    WorldRuntime other({8, 8}, 0, {}, s6_3_fixture::limits());
    other.restore(bytes);
    for (int d = 3; d <= 30; ++d)
      f.world.advance_to({d * s6_3_fixture::day});
    other.advance_to({30 * s6_3_fixture::day});
    require(other.checkpoint() == f.world.checkpoint(),
            "month acceleration changed facts");
    roundtrip(f.world, {31 * s6_3_fixture::day});
  } else if (name == "RETURN_VISIT") {
    s6_3_fixture::World f(1, 8, "empty");
    f.world.advance_to({8 * s6_3_fixture::day});
    require(f.world.summary().committed_events < 100000,
            "empty trips bypassed local recovery");
    bool returned = false;
    for (const auto &e : f.world.committed_events())
      if (e.kind == FactKind::Moved && e.position == PositionM{} &&
          e.mode != BehaviorMode::Return)
        returned = true;
    require(returned, "test did not exercise an ordinary depot revisit");
    roundtrip(f.world, {9 * s6_3_fixture::day});
  } else if (name == "CONTACT_SEQUENCE" || name == "NO_RECIPIENT") {
    WorldRuntime w({63, 3}, 7);
    w.configure_long_term();
    SocialConfig social;
    social.gift_first = true;
    w.configure_social(social);
    const auto c = w.seed_colony();
    const auto nurse = w.seed_ant(c, {});
    const auto carrier = w.seed_ant(c, {});
    PhysiologyConfig p;
    p.basal_nj_per_ms = 0;
    p.water_loss_ug_per_period = 0;
    p.absorption_period = {100};
    p.behavior_interval = {100};
    w.enable_physiology(nurse, {{}, 2000000000, 2000, 0}, p);
    const auto larva = w.seed_ant(
        c, {{name == "NO_RECIPIENT" ? .01 : 0, 0, 0}, LifeStage::Larva});
    w.enable_physiology(larva, {{}, 100000000, 100, 0}, p);
    const auto food = w.seed_food({}, {100, 100, 100, 0});
    w.submit({carrier, {1}, ActionKind::CollectFood, food, {}, 300});
    w.advance_to({1});
    w.submit({carrier, {2}, ActionKind::DeliverFood, {}, {}, 0});
    w.advance_to({2});
    w.set_behavior(nurse, IndividualBehavior::Nurse);
    w.advance_to(
        {103}); // Actual local intake has committed; the follow-up has not.
    roundtrip(w, {110});
    const auto recipient = *w.query_physiology(larva);
    if (name == "CONTACT_SEQUENCE")
      require(recipient.crop.carbs_ug && recipient.crop.protein_ug &&
                  recipient.crop.water_ug,
              "local exchange lost the transferable meal to the donor's next "
              "absorption pulse");
    else
      require(recipient.crop == FoodMass{},
              "follow-up invented a distant recipient");
  } else if (name == "SPACE_RESPONSE") {
    s6_3_fixture::World ample(1, 32),
        compact(1, 32, "balanced", false, {}, 6, true);
    ample.world.advance_to({2 * s6_3_fixture::day});
    compact.world.advance_to({2 * s6_3_fixture::day});
    require(ample.world.geometry_snapshot().geometry_revision == 0,
            "ample local space failed to inhibit work");
    require(compact.world.geometry_snapshot().geometry_revision > 0,
            "compact local space elicited no physical excavation");
    roundtrip(compact.world, {3 * s6_3_fixture::day});
  } else if (name == "PENDING_INDEX") {
    WorldRuntime w({63, 4}, 1);
    const auto c = w.seed_colony();
    const auto egg = w.seed_ant(c, {{}, LifeStage::Egg});
    const auto forced = w.schedule_lifecycle(egg, {5}, LifeStage::Larva);
    w.configure_long_term();
    w.configure_social({});
    bool refused = false;
    try {
      w.enable_physiology(egg);
    } catch (const std::invalid_argument &) {
      refused = true;
    }
    require(refused,
            "preexisting development command was absent from derived index");
    require(w.cancel(forced), "forced command cancellation failed");
    w.enable_physiology(egg);
    const auto worker = w.seed_ant(c, {});
    w.enable_physiology(worker);
    const auto move = w.submit({worker, {5}, ActionKind::Move, {}, {}, 0});
    const auto before = w.checkpoint();
    refused = false;
    try {
      w.set_autonomy(worker);
    } catch (const std::invalid_argument &) {
      refused = true;
    }
    require(refused && w.checkpoint() == before,
            "external resolution ownership was lost");
    WorldRuntime restored({9, 9}, 0);
    restored.restore(before);
    refused = false;
    try {
      restored.set_behavior(worker, IndividualBehavior::Nurse);
    } catch (const std::invalid_argument &) {
      refused = true;
    }
    require(refused, "restored actor index lost external work");
    require(w.cancel(move), "external action cancellation failed");
    w.set_autonomy(worker);
    roundtrip(w, {10});
  } else if (name == "CORRUPTION") {
    Tiny f;
    f.w.advance_to({60});
    const auto before = f.w.checkpoint();
    auto corrupt = before;
    corrupt.back() ^= 1;
    bool failed = false;
    try {
      f.w.restore(corrupt);
    } catch (const std::exception &) {
      failed = true;
    }
    require(failed && f.w.checkpoint() == before,
            "corrupt extended save replaced state");
    require(before[6] == '9', "extended checkpoint reused legacy version");
    for (auto fact : f.w.committed_events())
      if (fact.kind == FactKind::AntBorn) {
        const auto original = encode_event(fact);
        ++fact.transferred.protein_ug;
        const auto forged = encode_event(fact);
        corrupt = before;
        const auto at = std::search(corrupt.begin(), corrupt.end(),
                                    original.begin(), original.end());
        require(at != corrupt.end(), "birth evidence not found in checkpoint");
        std::copy(forged.begin(), forged.end(), at);
        std::uint64_t hash = UINT64_C(14695981039346656037);
        for (std::size_t i = 0; i < corrupt.size() - 8; ++i)
          hash = (hash ^ corrupt[i]) * UINT64_C(1099511628211);
        for (unsigned i = 0; i < 8; ++i)
          corrupt[corrupt.size() - 8 + i] =
              static_cast<std::uint8_t>(hash >> (8 * i));
        failed = false;
        try {
          f.w.restore(corrupt);
        } catch (const std::exception &) {
          failed = true;
        }
        require(failed && f.w.checkpoint() == before,
                "rechecksummed unfunded birth was accepted");
      }
  } else
    throw std::invalid_argument("unknown S6.3 test");
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      throw std::invalid_argument("one S6.3 case required");
    run(argv[1]);
    std::cout << "PASS " << argv[1] << '\n';
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
