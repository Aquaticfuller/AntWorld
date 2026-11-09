#include "s6_fixture.hpp"
#include <algorithm>
#include <iostream>
#include <string_view>

using namespace antworld;
using s3_fixture::require;
namespace {
struct Intake {
  WorldRuntime w{{61, 1}, 7};
  ColonyRef colony;
  AntRef donor, larva, carrier;
  Intake(bool corrected, bool urgent = false, bool response = true) {
    SocialConfig c;
    c.gift_first = corrected;
    c.local_work_continuation = corrected;
    c.exchange_enabled = response;
    w.configure_social(c);
    colony = w.seed_colony();
    donor = w.seed_ant(colony, {});
    larva = w.seed_ant(colony, {{}, LifeStage::Larva});
    carrier = w.seed_ant(colony, {});
    const auto food = w.seed_food({}, {200, 200, 600, 0});
    w.enable_physiology(donor,
                        {{0, 100, 0, 0},
                         urgent ? UINT64_C(400000000) : UINT64_C(1000000000),
                         1000,
                         0});
    w.enable_physiology(larva, {{}, 2000000000, 2000, 0});
    w.submit({carrier, {1}, ActionKind::CollectFood, food, {}, 1000});
    w.advance_to({1});
    w.submit({carrier, {2}, ActionKind::DeliverFood, {}, {}, 0});
    w.advance_to({2});
    w.set_behavior(donor, IndividualBehavior::Nurse);
  }
  FactKind first_action() {
    w.advance_to({1003});
    for (const auto &e : w.committed_events())
      if (e.actor == donor.id && (e.kind == FactKind::NestIngested ||
                                  e.kind == FactKind::NutritionTransferred))
        return e.kind;
    throw std::runtime_error("no actual nursing action");
  }
};
void priority() {
  Intake before(false), after(true);
  require(before.first_action() == FactKind::NestIngested,
          "lost S6 refill control");
  require(after.first_action() == FactKind::NutritionTransferred,
          "existing compatible crop did not precede refill");
  require(after.w.query_physiology(after.larva)->crop.protein_ug == 100,
          "actual protein gift missing");
  require(after.w.query_colony(after.colony)->nest_food.total_ug() == 1000,
          "gift fabricated a nest withdrawal");
  s3_fixture::balanced(after.w);
  s3_fixture::roundtrip(after.w);
}
void self_maintenance() {
  Intake urgent(true, true);
  require(urgent.first_action() == FactKind::NestIngested,
          "urgent own energy did not retain intake priority");
  require(urgent.w.query_physiology(urgent.larva)->crop.protein_ug == 0,
          "urgent actor gave a fabricated priority gift");
  s3_fixture::balanced(urgent.w);
  s3_fixture::roundtrip(urgent.w);
}
void continuation() {
  s6_fixture::Integrated old(7),
      fixed(7, "supplied", false, 16,
            s6_fixture::correction_options("local_continuation"));
  old.world.advance_to({25000});
  fixed.world.advance_to({25000});
  for (std::uint64_t id : {19U, 20U}) {
    const AntRef a{{6, 8}, {id}};
    require(old.world.query_physiology(a)->behavior ==
                IndividualBehavior::Forage,
            "lost seed-7 original premature exit");
    require(fixed.world.query_physiology(a)->behavior ==
                IndividualBehavior::Nurse,
            "sampled compatible work did not retain nursing");
  }
  s6_fixture::balanced(fixed.world);
  s3_fixture::roundtrip(fixed.world);
}
void release_cue() {
  WorldRuntime w({61, 2}, 7);
  SocialConfig c;
  c.gift_first = true;
  c.local_work_continuation = true;
  w.configure_social(c);
  const auto colony = w.seed_colony();
  const auto donor = w.seed_ant(colony, {}),
             larva = w.seed_ant(colony, {{}, LifeStage::Larva});
  w.enable_physiology(donor, {{0, 400, 0, 0}, 1000000000, 1000, 0});
  w.enable_physiology(larva, {{}, 2000000000, 2000, 0});
  w.set_behavior(donor, IndividualBehavior::Nurse);
  w.set_autonomy(donor);
  w.advance_to({10000});
  require(w.query_physiology(larva)->tissue_protein_ug +
                  w.query_physiology(larva)->crop.protein_ug ==
              100,
          "local requirement unfilled");
  require(w.query_physiology(donor)->behavior == IndividualBehavior::Rest,
          "cue-free worker remained locked in Nurse");
  w.set_behavior(donor, IndividualBehavior::Paused);
  require(!w.query_autonomy(donor)->enabled,
          "manual pause did not revoke autonomy");
  w.schedule_lifecycle(donor, {10001}, LifeStage::Dead);
  w.advance_to({10001});
  for (const auto &e : w.pending_events())
    require(e.actor != donor.id, "dead corrected actor retained work");
  s3_fixture::balanced(w);
  s3_fixture::roundtrip(w);
}
void controls() {
  for (bool emerged : {false, true})
    for (const auto condition :
         {"contact", "wall", "range", "no_response", "no_protein"}) {
      s6_fixture::Surplus f(7, condition, emerged, 16, "combined");
      f.world.advance_to({180000});
      std::uint64_t protein = 0;
      for (const auto &e : f.world.committed_events())
        if (e.kind == FactKind::NutritionTransferred)
          protein += e.transferred.protein_ug;
      require(std::string_view(condition) == "contact" ? protein == 200
                                                       : protein == 0,
              "corrected local control violated actual access/supply");
      require(f.world.query_ant(f.donor)->id == f.donor.id,
              "correction replaced an emerged identity");
      s6_fixture::balanced(f.world);
      s3_fixture::roundtrip(f.world);
    }
}
void partition() {
  for (const auto policy :
       {"legacy", "gift_first", "local_continuation", "combined"}) {
    s6_fixture::Integrated f(7, "supplied", false, 16,
                             s6_fixture::correction_options(policy));
    WorldRuntime copy({9, 9}, 0, {}, s6_fixture::limits());
    copy.restore(f.world.checkpoint());
    f.world.advance_to({90000});
    for (std::int64_t t = 1000; t <= 90000; t += 1000) {
      copy.advance_to({t});
      if (t % 10000 == 0)
        copy.restore(copy.checkpoint());
    }
    require(f.world.checkpoint() == copy.checkpoint(),
            "corrected slicing/restore changed complete state");
    s6_fixture::balanced(f.world);
  }
}
void locality() {
  auto build = [](bool distant, bool reverse) {
    WorldRuntime w({61, 3}, 5);
    SocialConfig c;
    c.gift_first = true;
    c.local_work_continuation = true;
    w.configure_social(c);
    const auto colony = w.seed_colony();
    const auto a = w.seed_ant(colony, {}), b = w.seed_ant(colony, {}),
               larva = w.seed_ant(colony, {{}, LifeStage::Larva});
    for (auto id : {a, b})
      w.enable_physiology(id, {{0, 400, 0, 0}, 1000000000, 1000, 0});
    w.enable_physiology(larva);
    if (distant) {
      w.seed_food({.8, 0, 0}, {0, 100000, 0, 0});
      for (unsigned i = 0; i < 32; ++i)
        w.seed_ant(colony, {{.5, 0, 0}});
    }
    for (auto id : reverse ? std::array{b, a} : std::array{a, b})
      w.set_autonomy(id);
    w.advance_to({60000});
    return w;
  };
  auto a = build(false, false), b = build(true, true);
  for (std::uint64_t id : {2U, 3U, 4U}) {
    const AntRef ref{{61, 3}, {id}};
    auto p = *a.query_physiology(ref), q = *b.query_physiology(ref);
    // Schedule IDs reflect external enrollment order; the individual's
    // actual physiology, decisions and program must not depend on it.
    p.physiology_event = {};
    p.behavior_event = {};
    q.physiology_event = {};
    q.behavior_event = {};
    require(p == q,
            "remote information or enrollment order changed local physiology");
  }
  const auto bytes = a.checkpoint();
  for (unsigned i = 0; i < 50; ++i)
    (void)a.sample_contacts({{61, 3}, {2}}, i);
  require(a.checkpoint() == bytes, "observer consumed state/RNG");
}
void corruption() {
  s6_fixture::Surplus f(7, "contact", false, 16, "combined");
  const auto bytes = f.world.checkpoint();
  const auto flag = bytes.size() - 8 - 3 * 41 - 8 - 40 - 2;
  for (auto offset : {flag, flag + 1}) {
    auto bad = bytes;
    bad[offset] = 2;
    std::uint64_t hash = UINT64_C(14695981039346656037);
    for (std::size_t i = 0; i < bad.size() - 8; ++i)
      hash = (hash ^ bad[i]) * UINT64_C(1099511628211);
    for (unsigned i = 0; i < 8; ++i)
      bad[bad.size() - 8 + i] = static_cast<std::uint8_t>(hash >> (8 * i));
    bool rejected = false;
    try {
      f.world.restore(bad);
    } catch (const std::invalid_argument &) {
      rejected = true;
    }
    require(rejected && f.world.checkpoint() == bytes,
            "invalid correction flag mutated authority");
  }
  WorldRuntime invalid({61, 4}, 1);
  SocialConfig c;
  c.gift_first = true;
  c.demand_sensitive = false;
  const auto prior = invalid.checkpoint();
  bool rejected = false;
  try {
    invalid.configure_social(c);
  } catch (const std::invalid_argument &) {
    rejected = true;
  }
  require(rejected && invalid.checkpoint() == prior,
          "uncapped correction configuration accepted");
}
void contact_links() {
  WorldRuntime w({61, 5}, 42);
  w.configure_social();
  const auto c = w.seed_colony();
  std::vector<AntRef> ants(0);
  for (unsigned i = 0; i < 200; ++i)
    ants.push_back(w.seed_ant(c, {}));
  for (unsigned round = 0; round < 3; ++round) {
    const SimTime at{static_cast<std::int64_t>(round + 1) * 1000};
    for (std::size_t i = 0; i < ants.size(); ++i) {
      if (!w.query_ant(ants[i])->alive())
        continue;
      if (i % 7 == round)
        w.schedule_lifecycle(ants[i], at, LifeStage::Dead);
      else
        w.submit({ants[i],
                  at,
                  ActionKind::Move,
                  {},
                  (i + round) % 3 ? PositionM{} : PositionM{.01, 0, 0},
                  0});
    }
    w.advance_to(at);
    WorldRuntime copy({9, 9}, 0);
    copy.restore(w.checkpoint());
    for (auto actor : ants)
      if (w.query_ant(actor)->alive())
        for (std::uint64_t decision = 0; decision < 10; ++decision)
          require(w.sample_contacts(actor, decision) ==
                      copy.sample_contacts(actor, decision),
                  "cached child references differ from canonical rebuild");
  }
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      throw std::invalid_argument("one test name required");
    const std::string_view t = argv[1];
    if (t == "GIFT_PRIORITY")
      priority();
    else if (t == "SELF_MAINTENANCE")
      self_maintenance();
    else if (t == "LOCAL_CONTINUATION")
      continuation();
    else if (t == "RELEASE_CUE")
      release_cue();
    else if (t == "CONTROLS")
      controls();
    else if (t == "PARTITION")
      partition();
    else if (t == "LOCALITY")
      locality();
    else if (t == "CORRUPTION")
      corruption();
    else if (t == "CONTACT_LINKS")
      contact_links();
    else
      throw std::invalid_argument("unknown S6.1 test");
    std::cout << "PASS S6_1_" << t << '\n';
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
