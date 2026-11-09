#include "behavior_rng.hpp"
#include "social_internal.hpp"

namespace antworld {
using namespace detail;
void WorldRuntime::set_autonomy(AntRef ref, bool enabled) {
  Transaction tx(*state_, limits_);
  change_autonomy(tx, ref, enabled);
  tx.commit();
}
void WorldRuntime::change_autonomy(Transaction &tx, AntRef ref, bool enabled) {
  auto &s = *state_;
  const auto ant = query_ant(ref);
  if (!s.social || !ant || !ant->alive() || ant->caste != Caste::Worker ||
      !s.physiology.contains(ref.id))
    throw std::invalid_argument(
        "autonomy requires a living physiological worker and social policy");
  if (enabled)
    for (const auto &[key, e] : s.queue) {
      if (e.actor == ref.id && key.phase == Phase::Resolution &&
          e.id != s.physiology.at(ref.id).behavior_event &&
          (!s.foragers.contains(ref.id) ||
           e.id != s.foragers.at(ref.id).action) &&
          (!s.excavators.contains(ref.id) ||
           e.id != s.excavators.at(ref.id).action))
        throw std::invalid_argument(
            "resolve external actions before enrolling autonomy");
    }
  auto a = s.autonomy.contains(ref.id)
               ? s.autonomy.at(ref.id)
               : AutonomyState{false, 0, s.m.now, s.m.now, {}};
  if (a.wake.value && s.queue_index.contains(a.wake))
    tx.remove(s.queue_index.at(a.wake));
  a.enabled = enabled;
  a.wake = {};
  tx.autonomy.set(ref.id, a);
  schedule_autonomy(tx, ref.id);
  WorldEvent f;
  f.kind = FactKind::AutonomyChanged;
  f.actor = ref.id;
  f.colony = ant->colony;
  f.stage = ant->stage;
  f.position = ant->position;
  f.payload = enabled ? 1 : 0;
  tx.fact(f);
}
std::optional<AutonomyState> WorldRuntime::query_autonomy(AntRef ref) const {
  const auto &s = *state_;
  if (!query_ant(ref) || !s.autonomy.contains(ref.id))
    return {};
  return s.autonomy.at(ref.id);
}
void WorldRuntime::schedule_autonomy(Transaction &tx, EntityId id) {
  auto &s = *state_;
  if (!s.autonomy.contains(id))
    return;
  auto a = s.autonomy.at(id);
  const auto ant = s.ants.get(s.ants.index.at(id));
  if (!a.enabled || ant.stage != LifeStage::Adult || a.wake.value)
    return;
  ScheduledEvent e;
  e.actor = id;
  e.kind = ScheduledEvent::Kind::AutonomyWake;
  e.issued_at = s.m.now;
  e.key = {after(s.m.now, s.social->decision_interval.milliseconds),
           Phase::Reschedule, 0, 0, 0};
  a.wake = tx.insert(e);
  tx.autonomy.set(id, a);
}
void WorldRuntime::stop_autonomy(Transaction &tx, EntityId id) {
  auto &s = *state_;
  if (!s.autonomy.contains(id))
    return;
  auto a = s.autonomy.at(id);
  if (a.wake.value && s.queue_index.contains(a.wake))
    tx.remove(s.queue_index.at(a.wake));
  a.enabled = false;
  a.wake = {};
  tx.autonomy.set(id, a);
}
void WorldRuntime::resolve_autonomy_wakes(
    Transaction &tx, const std::vector<ScheduledEvent> &wakes) {
  profiling::Scope profile(profiling::Category::Policy);
  auto &s = *state_;
  const auto &config = *s.social;
  // Keep the frozen decision record scalar: only work counters survive local
  // perception. Moving a nested debug-STL vector inside a noexcept aggregate
  // move can terminate under allocation-failure injection on MSVC.
  struct Choice {
    ScheduledEvent event;
    IndividualBehavior behavior;
    ContactWork sample;
  };
  std::vector<Choice> choices(0);
  choices.reserve(wakes.size());
  for (const auto &wake : wakes) {
    const auto ant = s.ants.get(s.ants.index.at(wake.actor));
    const auto a = s.autonomy.at(ant.id);
    const auto p = *query_physiology({s.world, ant.id});
    if (!a.enabled || a.wake != wake.id || ant.stage != LifeStage::Adult)
      throw std::logic_error("invalid autonomy ownership");
    Choice choice{wake, p.behavior, {}};
    const auto &colony = s.colonies.rows[s.colonies.index.at(ant.colony)];
    // Ongoing journeys and carried resources remain owned by that worker.
    // Stationary workers may nurse locally away from the depot; only a real
    // depot return permits switching out of foraging/excavation.
    const bool at_depot = ant.position == colony.nest_position;
    const bool stationary = p.behavior != IndividualBehavior::Forage &&
                            p.behavior != IndividualBehavior::Excavate;
    const bool can_switch = (at_depot || stationary) &&
                            !ant.carried_food.total_ug() &&
                            !s.carriers.contains(ant.id);
    const bool ready =
        p.behavior == IndividualBehavior::Paused ||
        s.m.now.milliseconds - a.last_program_change.milliseconds >=
            config.minimum_program_time.milliseconds;
    if (can_switch && ready) {
      const auto sample = sample_contacts(
          {s.world, ant.id}, a.decisions ^ UINT64_C(0x45434f4c4f4759));
      choice.sample = {0, sample.candidates_examined, sample.bucket_queries,
                       sample.tree_visits, 0};
      bool need = false, crop_work = false;
      const bool nest_contact =
          distance(ant.position, colony.nest_position) <=
              s.config.contact_distance_m &&
          (!s.surface || s.geometry ||
           s.surface->locate(ant.position) ==
               s.surface->locate(colony.nest_position)) &&
          spatially_clear(ant.position, colony.nest_position);
      const auto stock = nest_contact ? colony.nest_food : FoodMass{};
      const auto available = sum(p.crop, stock);
      for (const auto other : sample.ants) {
        const auto q = query_physiology(other);
        if (!q)
          continue;
        const auto stage = s.ants.get(s.ants.index.at(other.id)).stage;
        if (q->crop.total_ug() < q->config.crop_capacity_ug &&
            ingredient_min(available, signaled_need(*q, stage)).total_ug())
          need = true;
        if (q->crop.total_ug() < q->config.crop_capacity_ug &&
            ingredient_min(p.crop, signaled_need(*q, stage)).total_ug())
          crop_work = true;
      }
      const bool forage = at_depot && s.surface &&
                          s.surface->locate(ant.position) &&
                          sense({s.world, ant.id}).step_count;
      bool soil = false;
      if (at_depot && s.geometry && sample.ants.size() >= 2) {
        const auto &g = s.geometry->config;
        const auto origin = *quantized(ant.position, g);
        constexpr std::array<PointQ, 6> directions{{{1, 0, 0},
                                                    {-1, 0, 0},
                                                    {0, 1, 0},
                                                    {0, -1, 0},
                                                    {0, 0, 1},
                                                    {0, 0, -1}}};
        for (const auto d : directions)
          for (std::int32_t step = 1; step <= g.reach_q; ++step) {
            const auto material = query_material(
                physical({origin.x + d.x * step, origin.y + d.y * step,
                          origin.z + d.z * step},
                         g));
            if (material == Material::Soil)
              soil = true;
            if (material != Material::Void)
              break; // Rock occludes soil behind it.
          }
      }
      const bool urgent = p.body_energy_nj < p.config.energy_capacity_nj / 4 ||
                          p.hydration_ug < p.config.hydration_capacity_ug / 4;
      if (urgent &&
          ingredient_min(stock, nutrient_demand(p, ant.stage)).total_ug())
        choice.behavior = IndividualBehavior::Rest;
      else if (config.local_work_continuation && !urgent &&
               config.exchange_enabled && crop_work &&
               p.behavior == IndividualBehavior::Nurse)
        // Continue work witnessed in this local encounter. No stored request,
        // global deficit or promised transfer survives a later failed contact.
        choice.behavior = IndividualBehavior::Nurse;
      else {
        const std::array<std::pair<IndividualBehavior, std::uint64_t>, 4>
            options{
                {{IndividualBehavior::Rest, config.rest_weight},
                 {IndividualBehavior::Forage,
                  forage ? config.forage_weight : 0U},
                 {IndividualBehavior::Nurse,
                  need && config.exchange_enabled ? config.nurse_weight : 0U},
                 {IndividualBehavior::Excavate,
                  soil ? config.excavate_weight : 0U}}};
        std::uint64_t total = 0;
        for (const auto &option : options)
          total += option.second;
        auto rng = individual_rng(s.seed ^ UINT64_C(0x533645434f4c4f47), ant.id,
                                  a.decisions);
        auto draw = bounded_draw(rng, total);
        for (const auto &[program, weight] : options) {
          if (draw < weight) {
            choice.behavior = program;
            break;
          }
          draw -= weight;
        }
      }
    }
    choices.push_back(std::move(choice));
  }
  // Every choice uses the same committed boundary. Submission/enrollment order
  // does not determine an individual's program or its private random stream.
  std::sort(choices.begin(), choices.end(), [](const auto &a, const auto &b) {
    return a.event.actor < b.event.actor;
  });
  for (const auto &choice : choices) {
    const auto id = choice.event.actor;
    auto a = s.autonomy.at(id);
    a.wake = {};
    bump(a.decisions);
    tx.autonomy.set(id, a);
    if (choice.behavior != s.physiology.at(id).behavior)
      change_behavior(tx, {s.world, id}, choice.behavior, choice.event.id);
    const auto &sample = choice.sample;
    auto &work = s.m.contact_work;
    bump(work.decisions);
    work.candidates_examined =
        add(work.candidates_examined, sample.candidates_examined);
    work.bucket_queries = add(work.bucket_queries, sample.bucket_queries);
    work.tree_visits = add(work.tree_visits, sample.tree_visits);
    work.maximum_candidates =
        std::max(work.maximum_candidates, sample.candidates_examined);
    const auto ant = s.ants.get(s.ants.index.at(id));
    WorldEvent f;
    f.kind = FactKind::AutonomyDecision;
    f.source = choice.event.id;
    f.actor = id;
    f.colony = ant.colony;
    f.stage = ant.stage;
    f.position = ant.position;
    f.payload = a.decisions;
    f.random_value = sample.candidates_examined;
    tx.fact(f);
    schedule_autonomy(tx, id);
  }
}
} // namespace antworld
