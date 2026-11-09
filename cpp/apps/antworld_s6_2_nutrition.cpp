#include "../src/behavior_rng.hpp"
#include "../src/social_internal.hpp"
#include "s6_fixture.hpp"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <tuple>
using namespace antworld;
using s3_fixture::require;
namespace {
struct Person {
  AntState ant;
  PhysiologyState p;
  LifeStage seeded;
  std::int64_t threshold{-1}, tissue_threshold{-1}, adult{-1}, death{-1};
  std::uint64_t received{}, given{};
};
using People = std::map<EntityId, Person>;
using Pair = std::pair<EntityId, EntityId>;
struct Output {
  std::ofstream summary, gifts, decisions, people;
  explicit Output(const std::filesystem::path &dir)
      : summary(dir / "summary.csv"), gifts(dir / "gifts.csv"),
        decisions(dir / "decisions.csv"), people(dir / "individuals.csv") {
    for (auto *f : {&summary, &gifts, &decisions, &people})
      f->exceptions(std::ios::badbit | std::ios::failbit);
    const char *key = "seed,workers,source_protein_ug,policy,";
    summary << key
            << "events,state_hash,trace_hash,gift_attempts,protein_given_ug,"
               "nutrition_decisions,actual_samples,missed_protein_contacts,"
               "canceled_choices,continuation_equal\n";
    gifts << key
          << "event_id,source_id,time_ms,donor,recipient,outcome,committed,"
             "protein_ug,donor_crop_protein_before_ug,recipient_protein_before_"
             "ug,recipient_stage,compatible_mass_before_ug,donor_crop_mass_"
             "before_ug,recipient_demand_mass_before_ug,recipient_capacity_"
             "before_ug,recipient_protein_after_ug\n";
    decisions
        << key
        << "event_id,source_id,time_ms,actor,program,crop_protein_ug,crop_mass_"
           "ug,urgent,actual_candidates,actual_contacts,reachable_eligible,"
           "reachable_protein_larvae,sampled_eligible,sampled_protein_larvae,"
           "chosen_recipient,action_kind,canceled_by_timestamp_end\n";
    people << key
           << "entity_id,seed_stage,stage,threshold_ms,tissue_threshold_ms,"
              "adult_ms,death_ms,received_"
              "protein_ug,given_protein_ug,crop_protein_ug,tissue_protein_ug\n";
  }
};
bool close_enough(const AntState &a, const AntState &b, double radius) {
  return a.colony == b.colony &&
         std::hypot(a.position.x - b.position.x, a.position.y - b.position.y,
                    a.position.z - b.position.z) <= radius;
}
std::vector<EntityId> sampled(const People &people, EntityId actor,
                              std::uint64_t seed, std::uint64_t decision,
                              double radius, const std::map<Pair, bool> &clear,
                              std::uint64_t &candidates) {
  std::map<PointQ, std::vector<EntityId>> buckets;
  for (const auto &[id, q] : people)
    if (q.ant.alive())
      buckets[detail::contact_key(q.ant.position, radius)].push_back(id);
  const auto key = detail::contact_key(people.at(actor).ant.position, radius);
  std::vector<EntityId> ordered;
  for (int x = -1; x <= 1; ++x)
    for (int y = -1; y <= 1; ++y)
      for (int z = -1; z <= 1; ++z) {
        const auto it = buckets.find({key.x + x, key.y + y, key.z + z});
        if (it != buckets.end())
          ordered.insert(ordered.end(), it->second.begin(), it->second.end());
      }
  candidates = std::min<std::size_t>(16, ordered.size());
  auto rng = detail::individual_rng(seed ^ UINT64_C(0x5336434f4e544143), actor,
                                    decision);
  std::set<std::uint64_t> ranks;
  for (std::uint64_t j = ordered.size() - candidates; j < ordered.size(); ++j) {
    const auto value = detail::bounded_draw(rng, j + 1);
    ranks.insert(ranks.contains(value) ? j : value);
  }
  std::vector<EntityId> result;
  for (auto rank : ranks) {
    const auto id = ordered[rank];
    if (id != actor &&
        close_enough(people.at(actor).ant, people.at(id).ant, radius) &&
        clear.at({actor, id}))
      result.push_back(id);
  }
  std::sort(result.begin(), result.end());
  return result;
}
void replay(Output &out, std::uint64_t seed, unsigned workers,
            std::uint64_t protein, const std::string &policy) {
  auto options = s6_fixture::correction_options(policy);
  options.workers = workers;
  options.source_protein_ug = protein;
  s6_fixture::Integrated fixture(seed, "supplied", false, 16, options);
  auto &w = fixture.world;
  const auto prefix = std::to_string(seed) + ',' + std::to_string(workers) +
                      ',' + std::to_string(protein) + ',' + policy + ',';
  People people;
  for (const auto &a : w.ant_states()) {
    const auto p = *w.query_physiology({w.summary().world, a.id});
    people.emplace(a.id,
                   Person{a, p, a.stage, p.tissue_protein_ug >= 100 ? 0 : -1,
                          p.tissue_protein_ug >= 100 ? 0 : -1});
  }
  WorldRuntime fast({9, 9}, 0, {}, s6_fixture::limits()),
      restored({9, 8}, 0, {}, s6_fixture::limits());
  fast.restore(w.checkpoint());
  restored.restore(w.checkpoint());
  EventId cursor{w.summary().committed_events};
  std::uint64_t attempts{}, given{}, decisions{}, samples{}, misses{},
      canceled{};
  auto nest = w.colonies().front().nest_food;
  for (std::int64_t boundary = 1000; boundary <= 180000; boundary += 1000) {
    while (w.summary().now.milliseconds < boundary) {
      const auto pending = w.pending_events();
      const auto at = std::min(SimTime{boundary}, pending.front().key.time);
      std::map<ScheduledId, ScheduledEvent> due;
      std::map<Pair, bool> clear;
      std::map<std::tuple<double, double, double, double, double, double>, bool>
          space_cache;
      for (const auto &e : pending) {
        if (e.key.time != at)
          break;
        due.emplace(e.id, e);
        if (e.kind != ScheduledEvent::Kind::NutritionWake)
          continue;
        const auto &a = people.at(e.actor).ant;
        for (const auto &[id, q] : people)
          if (id != e.actor && q.ant.alive() &&
              close_enough(a, q.ant, w.config().contact_distance_m)) {
            const auto p = a.position, b = q.ant.position;
            const auto key = std::tuple{p.x, p.y, p.z, b.x, b.y, b.z};
            if (!space_cache.contains(key))
              space_cache[key] = w.spatially_clear(p, b);
            clear[{e.actor, id}] = space_cache.at(key);
          }
      }
      // Only copied observer state is settled. Actual mass deltas below come
      // from ordered facts, including absorption before perception and gifts.
      for (auto &[id, q] : people) {
        (void)id;
        detail::settle(q.p, q.ant.stage, at);
      }
      w.advance_to(at);
      const auto after_queue = w.pending_events();
      const auto facts = w.events_after(cursor, 1000000);
      for (const auto &e : facts) {
        require(e.time == at, "observer crossed multiple fact timestamps");
        cursor = e.id;
        if (e.kind == FactKind::FoodDelivered)
          nest = detail::sum(nest, e.transferred);
        if (!e.actor.value || !people.contains(e.actor))
          continue;
        auto &a = people.at(e.actor);
        if (e.kind == FactKind::PhysiologyUpdated) {
          a.p.crop = detail::subtract(a.p.crop, e.transferred);
          a.p.tissue_protein_ug += e.transferred.protein_ug;
          if (a.tissue_threshold < 0 && a.p.tissue_protein_ug >= 100)
            a.tissue_threshold = at.milliseconds;
          a.p.body_energy_nj +=
              e.transferred.carbs_ug * a.p.config.carbohydrate_yield_nj_per_ug;
          a.p.hydration_ug += e.transferred.water_ug;
        }
        if (e.kind == FactKind::StageChanged) {
          a.ant.stage = e.stage;
          a.p.stage_progress = {};
          if (e.stage == LifeStage::Adult)
            a.adult = at.milliseconds;
        }
        if (e.kind == FactKind::AntDied) {
          a.ant.stage = LifeStage::Dead;
          a.p.behavior = IndividualBehavior::Paused;
          a.death = at.milliseconds;
        }
        if (e.kind == FactKind::BehaviorChanged)
          a.p.behavior = static_cast<IndividualBehavior>(e.payload);
        if (e.kind == FactKind::Moved)
          a.ant.position = e.position;
        if (e.kind == FactKind::SoilExcavated) {
          const auto edits = w.geometry_edits();
          const auto edit =
              std::find_if(edits.begin(), edits.end(),
                           [&](const auto &g) { return g.event == e.id; });
          require(edit != edits.end(), "missing dig energy evidence");
          a.p.body_energy_nj -=
              edit->volume_q3 * fixture.geometry.dig_energy_nj_per_q3;
        }
        if (e.kind == FactKind::FoodCollected)
          a.ant.carried_food = detail::sum(a.ant.carried_food, e.transferred);
        if (e.kind == FactKind::FoodDelivered)
          a.ant.carried_food =
              detail::subtract(a.ant.carried_food, e.transferred);
        if (e.kind == FactKind::CargoIngested ||
            e.kind == FactKind::NestIngested) {
          a.p.crop = detail::sum(a.p.crop, e.transferred);
          if (e.kind == FactKind::NestIngested)
            nest = detail::subtract(nest, e.transferred);
          else
            a.ant.carried_food =
                detail::subtract(a.ant.carried_food, e.transferred);
        }
        if (due.contains(e.source) &&
            due.at(e.source).kind == ScheduledEvent::Kind::Trophallaxis) {
          ++attempts;
          auto &q = people.at(EntityId{due.at(e.source).payload});
          const auto demand = detail::nutrient_demand(q.p, q.ant.stage);
          const auto compatible = detail::ingredient_min(a.p.crop, demand);
          const auto before = q.p.crop.protein_ug + q.p.tissue_protein_ug;
          out.gifts << prefix << e.id.value << ',' << e.source.value << ','
                    << at.milliseconds << ',' << e.actor.value << ','
                    << q.ant.id.value << ',' << static_cast<unsigned>(e.outcome)
                    << ',' << (e.kind == FactKind::NutritionTransferred) << ','
                    << e.transferred.protein_ug << ',' << a.p.crop.protein_ug
                    << ',' << before << ','
                    << static_cast<unsigned>(q.ant.stage) << ','
                    << compatible.total_ug() << ',' << a.p.crop.total_ug()
                    << ',' << demand.total_ug() << ','
                    << q.p.config.crop_capacity_ug - q.p.crop.total_ug() << ','
                    << before + e.transferred.protein_ug << '\n';
          if (e.kind == FactKind::NutritionTransferred) {
            a.p.crop = detail::subtract(a.p.crop, e.transferred);
            q.p.crop = detail::sum(q.p.crop, e.transferred);
            a.given += e.transferred.protein_ug;
            q.received += e.transferred.protein_ug;
            given += e.transferred.protein_ug;
            if (q.threshold < 0 && before + e.transferred.protein_ug >= 100)
              q.threshold = at.milliseconds;
          }
        }
        if (e.kind == FactKind::NutritionDecision) {
          ++decisions;
          std::uint64_t all_eligible{}, all_protein{}, sample_eligible{},
              sample_protein{}, candidate_count{};
          auto eligible = [&](EntityId id) {
            const auto &q = people.at(id);
            return q.p.crop.total_ug() < q.p.config.crop_capacity_ug &&
                   detail::ingredient_min(
                       a.p.crop, detail::signaled_need(q.p, q.ant.stage))
                       .total_ug();
          };
          auto protein_need = [&](EntityId id) {
            const auto &q = people.at(id);
            return a.p.crop.protein_ug && q.ant.stage == LifeStage::Larva &&
                   q.p.crop.protein_ug + q.p.tissue_protein_ug < 100 &&
                   q.p.crop.total_ug() < q.p.config.crop_capacity_ug;
          };
          for (const auto &[id, q] : people)
            if (id != e.actor && q.ant.alive() &&
                close_enough(a.ant, q.ant, w.config().contact_distance_m) &&
                clear.at({e.actor, id})) {
              all_eligible += eligible(id) != 0;
              all_protein += protein_need(id);
            }
          std::vector<EntityId> contacts;
          EntityId selected{};
          if (e.random_value) {
            ++samples;
            contacts =
                sampled(people, e.actor, seed, e.payload - 1,
                        w.config().contact_distance_m, clear, candidate_count);
            require(candidate_count == e.random_value,
                    "sample reconstruction work mismatch");
            auto rng = detail::individual_rng(seed ^ UINT64_C(0x53334e55525345),
                                              e.actor, e.payload - 1);
            for (auto id : contacts) {
              sample_protein += protein_need(id);
              if (eligible(id)) {
                ++sample_eligible;
                if (detail::bounded_draw(rng, sample_eligible) == 0)
                  selected = id;
              }
            }
            if (all_protein && !sample_protein)
              ++misses;
          }
          const auto action = std::find_if(
              after_queue.begin(), after_queue.end(), [&](const auto &q) {
                return q.actor == e.actor && q.issued_at == at &&
                       q.key.time == SimTime{at.milliseconds + 1} &&
                       q.key.phase == Phase::Resolution;
              });
          const bool canceled_choice = action == after_queue.end();
          canceled += canceled_choice;
          if (selected.value && !canceled_choice)
            require(action->kind == ScheduledEvent::Kind::Trophallaxis &&
                        action->payload == selected.value,
                    "chosen recipient reconstruction mismatch");
          const bool urgent =
              (a.p.body_energy_nj < a.p.config.energy_capacity_nj / 4 &&
               !a.p.crop.carbs_ug) ||
              (a.p.hydration_ug < a.p.config.hydration_capacity_ug / 4 &&
               !a.p.crop.water_ug);
          out.decisions << prefix << e.id.value << ',' << e.source.value << ','
                        << at.milliseconds << ',' << e.actor.value << ','
                        << static_cast<unsigned>(a.p.behavior) << ','
                        << a.p.crop.protein_ug << ',' << a.p.crop.total_ug()
                        << ',' << urgent << ',' << e.random_value << ','
                        << contacts.size() << ',' << all_eligible << ','
                        << all_protein << ',' << sample_eligible << ','
                        << sample_protein << ',' << selected.value << ','
                        << (canceled_choice ? -1
                                            : static_cast<int>(action->kind))
                        << ',' << canceled_choice << '\n';
        }
      }
      for (const auto &[id, q] : people) {
        const auto actual = *w.query_physiology({w.summary().world, id});
        if (!(q.p.crop == actual.crop &&
              q.p.tissue_protein_ug == actual.tissue_protein_ug &&
              q.p.body_energy_nj == actual.body_energy_nj &&
              q.p.hydration_ug == actual.hydration_ug)) {
          std::cerr << "observer mismatch time=" << at.milliseconds
                    << " id=" << id.value << " energy=" << q.p.body_energy_nj
                    << '/' << actual.body_energy_nj
                    << " water=" << q.p.hydration_ug << '/'
                    << actual.hydration_ug << " crop=" << q.p.crop.total_ug()
                    << '/' << actual.crop.total_ug()
                    << " tissue=" << q.p.tissue_protein_ug << '/'
                    << actual.tissue_protein_ug
                    << " program=" << static_cast<unsigned>(q.p.behavior) << '/'
                    << static_cast<unsigned>(actual.behavior)
                    << " updated=" << q.p.updated_at.milliseconds << '/'
                    << actual.updated_at.milliseconds << '\n';
          throw std::logic_error("ordered nutrient reconstruction mismatch");
        }
        require(q.ant.stage == w.query_ant({w.summary().world, id})->stage,
                "stage reconstruction mismatch");
        require(q.p.behavior == actual.behavior,
                "program reconstruction mismatch");
      }
      require(nest == w.colonies().front().nest_food,
              "nest reconstruction mismatch");
    }
    if (boundary % 30000 == 0) {
      fast.advance_to({boundary});
      restored.advance_to({boundary});
      require(w.checkpoint() == fast.checkpoint() &&
                  w.checkpoint() == restored.checkpoint(),
              "observer or partition divergence");
      restored.restore(restored.checkpoint());
      s6_fixture::balanced(w);
    }
  }
  for (const auto &[id, q] : people)
    out.people << prefix << id.value << ',' << static_cast<unsigned>(q.seeded)
               << ',' << static_cast<unsigned>(q.ant.stage) << ','
               << q.threshold << ',' << q.tissue_threshold << ',' << q.adult
               << ',' << q.death << ',' << q.received << ',' << q.given << ','
               << q.p.crop.protein_ug << ',' << q.p.tissue_protein_ug << '\n';
  const auto state = w.snapshot();
  out.summary << prefix << state.committed_events << ',' << state.state_hash
              << ',' << state.trace_hash << ',' << attempts << ',' << given
              << ',' << decisions << ',' << samples << ',' << misses << ','
              << canceled << ",1\n";
  out.summary.flush();
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc < 2 || argc > 4)
      throw std::invalid_argument("usage: antworld_s6_2_nutrition OUTPUT_DIR "
                                  "[SEEDS=16] [FIRST_SEED=1]");
    const std::filesystem::path dir = argv[1];
    require(!std::filesystem::exists(dir), "refusing existing output");
    std::filesystem::create_directories(dir);
    if (argc == 3 && std::string(argv[2]) == "smoke") {
      Output out(dir);
      for (const auto *policy : {"legacy", "combined"})
        replay(out, 1, 8, 500, policy);
      std::cout << "PASS S6.2 ordered scarcity observer smoke\n";
      return 0;
    }
    const auto seeds = argc > 2 ? std::stoul(argv[2]) : 16,
               first = argc > 3 ? std::stoul(argv[3]) : 1;
    require(seeds && first && first + seeds <= 17,
            "invalid frozen seed interval");
    Output out(dir);
    for (auto seed = first; seed < first + seeds; ++seed)
      for (unsigned workers : {8U, 32U, 128U})
        for (std::uint64_t protein : {500U, 2000U})
          for (const auto *policy : {"legacy", "combined"})
            replay(out, seed, workers, protein, policy);
    std::cout << "PASS S6.2 ordered nutrition reconstruction, choices and "
                 "continuation\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
