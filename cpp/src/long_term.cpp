#include "long_term_internal.hpp"
#include "care_internal.hpp"
#include <set>

namespace antworld {
using namespace detail;
void WorldRuntime::configure_long_term(const LongTermConfig &config) {
  auto &s = *state_;
  if (s.m.now != SimTime{} || s.m.watermark || s.long_term ||
      !s.physiology.empty())
    throw std::invalid_argument(
        "long-term configuration precedes physiology and execution");
  validate_long_term(config);
  Transaction tx(s, limits_);
  s.long_term = std::make_shared<const LongTermConfig>(config);
  for (const auto &[key, e] : s.queue)
    if (e.actor.value && ((e.kind == ScheduledEvent::Kind::Lifecycle &&
                           e.stage != LifeStage::Dead) ||
                          key.phase == Phase::Resolution)) {
      auto counts = s.pending_conflicts.contains(e.actor)
                        ? s.pending_conflicts.at(e.actor)
                        : std::array<std::uint64_t, 2>{};
      bump(counts[key.phase == Phase::Resolution ? 1 : 0]);
      tx.pending_conflicts.set(e.actor, counts);
    }
  WorldEvent f;
  f.kind = FactKind::LongTermConfigured;
  f.payload = long_term_fingerprint(config);
  tx.fact(f);
  tx.commit();
}
std::optional<LongTermConfig> WorldRuntime::long_term_config() const {
  return state_->long_term ? std::optional<LongTermConfig>{*state_->long_term}
                           : std::nullopt;
}
void WorldRuntime::enable_reproduction(AntRef ref,
                                       const ReproductionConfig &config) {
  auto &s = *state_;
  const auto ant = query_ant(ref);
  if (!s.long_term || s.m.now != SimTime{} || s.m.watermark || !s.social ||
      !ant || ant->stage != LifeStage::Adult || ant->caste != Caste::Queen ||
      !s.physiology.contains(ref.id) || s.reproduction.contains(ref.id))
    throw std::invalid_argument(
        "reproduction requires a physiological adult queen at setup");
  validate_reproduction(config, s.physiology.at(ref.id).config);
  Transaction tx(s, limits_);
  ReproductionState r;
  r.config = config;
  ScheduledEvent e;
  e.kind = ScheduledEvent::Kind::Reproduction;
  e.actor = ref.id;
  e.key = {config.interval, Phase::Environment, 2, 0, 0};
  r.wake = tx.insert(e);
  tx.reproduction.set(ref.id, r);
  WorldEvent f;
  f.kind = FactKind::ReproductionEnabled;
  f.payload =
      static_cast<std::uint64_t>(config.maintenance_horizon.milliseconds);
  f.actor = ref.id;
  f.colony = ant->colony;
  f.stage = ant->stage;
  f.position = ant->position;
  tx.fact(f);
  tx.commit();
}
void WorldRuntime::stop_reproduction(Transaction &tx, EntityId id) {
  auto &s = *state_;
  if (!s.reproduction.contains(id))
    return;
  auto r = s.reproduction.at(id);
  if (r.wake.value && s.queue_index.contains(r.wake))
    tx.remove(s.queue_index.at(r.wake));
  r.wake = {};
  tx.reproduction.set(id, r);
}
void WorldRuntime::execute_reproduction(Transaction &tx,
                                        const ScheduledEvent &e) {
  auto &s = *state_;
  const auto mother = s.ants.get(s.ants.index.at(e.actor));
  auto r = s.reproduction.at(e.actor);
  if (r.wake != e.id || !mother.alive())
    throw std::logic_error("invalid reproduction ownership");
  synchronize_physiology(tx, e.actor);
  auto p = s.physiology.at(e.actor);
  const auto &c = r.config;
  // Only this individual's current body reserves and maintenance rates enter.
  // A deferred attempt spends nothing; unmet needs can still cause death.
  const bool funded =
      reproductive_resources(c, p) &&
      spatially_clear(mother.position, mother.position,
                      s.geometry ? s.geometry->config.body_half_q : 0);
  EntityId child;
  if (funded) {
    if (integrated_care(s) && care_owned(s,mother.id)) {
      interrupt_care(tx,mother.id,Outcome::InvalidTransition,true);
      p=s.physiology.at(e.actor);
    }
    tx.entity_budget();
    child = {take(s.m.next_entity)};
    p.crop.protein_ug -= c.egg_protein_ug;
    p.hydration_ug -= c.egg_water_ug;
    p.body_energy_nj -= add(c.egg_energy_nj, c.dissipated_energy_nj);
    p.exported_energy_nj = add(p.exported_energy_nj, c.egg_energy_nj);
    p.dissipated_energy_nj =
        add(p.dissipated_energy_nj, c.dissipated_energy_nj);
    tx.physiology.set(e.actor, p);
    schedule_physiology(tx, e.actor);
    s.ants.append({child,
                   mother.colony,
                   s.m.now,
                   LifeStage::Egg,
                   Caste::Worker,
                   mother.position,
                   0,
                   c.offspring_carrying_capacity_ug,
                   {}});
    if (s.geometry)
      tx.spatial_index.set({spatial_key(mother.position), child.value}, 1);
    index_contact(tx, child, mother.position);
    bump(s.m.living);
    PhysiologyState q;
    q.config = p.config;
    q.config.adult_protein_target_ug = 0;
    q.initial = {{}, c.egg_energy_nj, c.egg_water_ug, c.egg_protein_ug};
    q.body_energy_nj = c.egg_energy_nj;
    q.hydration_ug = c.egg_water_ug;
    q.tissue_protein_ug = c.egg_protein_ug;
    q.updated_at = s.m.now;
    q.next_absorption = after(s.m.now, q.config.absorption_period.milliseconds);
    q.mother = e.actor;
    tx.physiology.set(child, q);
    schedule_physiology(tx, child);
    bump(r.births);
  }
  bump(r.attempts);
  auto next = e;
  next.issued_at = s.m.now;
  next.key.time = after(s.m.now, c.interval.milliseconds);
  r.wake = tx.insert(next);
  tx.reproduction.set(e.actor, r);
  WorldEvent f;
  f.kind = FactKind::ReproductionAttempt;
  f.source = e.id;
  f.actor = e.actor;
  f.colony = mother.colony;
  f.stage = mother.stage;
  f.position = mother.position;
  f.payload = child.value;
  tx.fact(f);
  if (child.value) {
    f.kind = FactKind::AntBorn;
    f.actor = child;
    f.stage = LifeStage::Egg;
    f.payload = mother.id.value;
    f.transferred = {0, c.egg_protein_ug, c.egg_water_ug, 0};
    f.random_value = c.egg_energy_nj;
    tx.fact(f);
    change_autonomy(tx, {s.world, child}, true);
  }
}
std::optional<ReproductionState>
WorldRuntime::query_reproduction(AntRef ref) const {
  const auto &s = *state_;
  const auto i = s.reproduction.find(ref.id);
  return ref.world == s.world && i != s.reproduction.end()
             ? std::optional<ReproductionState>{i->second}
             : std::nullopt;
}
void WorldRuntime::configure_resource_cycle(FoodRef ref,
                                            const ResourceCycleConfig &config) {
  auto &s = *state_;
  if (!s.long_term || s.m.now != SimTime{} || s.m.watermark ||
      ref.world != s.world || !s.foods.index.contains(ref.id) ||
      s.resource_cycles.contains(ref.id))
    throw std::invalid_argument("invalid resource-cycle setup");
  validate_cycle(config);
  (void)multiply(config.release_limit.total_ug(), 1000);
  Transaction tx(s, limits_);
  ResourceCycleState r;
  r.config = config;
  r.remaining = config.reserve;
  ScheduledEvent e;
  e.kind = ScheduledEvent::Kind::ResourceRelease;
  e.resource = ref.id;
  e.key = {config.interval, Phase::Environment, 1, 0, 0};
  r.wake = tx.insert(e);
  tx.resource_cycles.set(ref.id, r);
  s.m.ledger.introduced = sum(s.m.ledger.introduced, config.reserve);
  (void)s.m.ledger.introduced.total_ug();
  validate_nutrition_capacity();
  WorldEvent f;
  f.kind = FactKind::ResourceCycleConfigured;
  f.resource = ref.id;
  f.position = s.foods.rows[s.foods.index.at(ref.id)].position;
  f.transferred = config.reserve;
  tx.fact(f);
  tx.commit();
}
void WorldRuntime::execute_resource_release(Transaction &tx,
                                            const ScheduledEvent &e) {
  auto &s = *state_;
  auto r = s.resource_cycles.at(e.resource);
  if (r.wake != e.id)
    throw std::logic_error("invalid resource pulse ownership");
  const auto amount = release_amount(r, s.m.now);
  r.remaining = subtract(r.remaining, amount);
  r.released = sum(r.released, amount);
  bump(r.pulses);
  const auto i = s.foods.index.at(e.resource);
  tx.touch_food(i);
  auto &food = s.foods.rows[i];
  food.remaining = sum(food.remaining, amount);
  s.m.ledger.available = sum(s.m.ledger.available, amount);
  auto next = e;
  next.issued_at = s.m.now;
  next.key.time = after(s.m.now, r.config.interval.milliseconds);
  r.wake = tx.insert(next);
  tx.resource_cycles.set(e.resource, r);
  WorldEvent f;
  f.kind = FactKind::ResourceReleased;
  f.source = e.id;
  f.resource = e.resource;
  f.position = food.position;
  f.transferred = amount;
  f.payload = productivity(r.config, s.m.now);
  tx.fact(f);
}
std::optional<ResourceCycleState>
WorldRuntime::query_resource_cycle(FoodRef ref) const {
  const auto &s = *state_;
  const auto i = s.resource_cycles.find(ref.id);
  return ref.world == s.world && i != s.resource_cycles.end()
             ? std::optional<ResourceCycleState>{i->second}
             : std::nullopt;
}
FoodMass WorldRuntime::resource_reserves() const {
  FoodMass result;
  for (const auto &[id, r] : state_->resource_cycles) {
    (void)id;
    result = sum(result, r.remaining);
  }
  return result;
}
void WorldRuntime::notify_return(Transaction &tx, EntityId id) {
  auto &s = *state_;
  if (!s.long_term || !s.autonomy.contains(id))
    return;
  auto a = s.autonomy.at(id);
  if (!a.enabled)
    return;
  if (a.wake.value && s.queue_index.contains(a.wake))
    tx.remove(s.queue_index.at(a.wake));
  ScheduledEvent e;
  e.kind = ScheduledEvent::Kind::AutonomyWake;
  e.actor = id;
  e.payload = 1;
  e.issued_at = s.m.now;
  e.key = {after(s.m.now, 1), Phase::Reschedule, 0, 0, 0};
  a.wake = tx.insert(e);
  tx.autonomy.set(id, a);
}
bool WorldRuntime::local_space_demand(AntRef ref, std::size_t contacts) const {
  const auto &s = *state_;
  if (!s.geometry || !s.long_term || contacts < 2)
    return false;
  const auto ant = query_ant(ref);
  const auto &g = s.geometry->config;
  const auto origin = *quantized(ant->position, g);
  constexpr std::array<PointQ, 6> directions{
      {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}}};
  // Bounded reachable free-space proxy, not packing volume or a nest blueprint.
  const auto required = contacts * s.long_term->empty_sites_per_contact;
  std::set<PointQ> visited{origin};
  std::vector<PointQ> frontier{origin};
  for (std::size_t i = 0; i < frontier.size() && frontier.size() < required;
       ++i)
    for (const auto d : directions) {
      const auto p = frontier[i];
      const PointQ q{p.x + d.x, p.y + d.y, p.z + d.z};
      if (std::abs(q.x - origin.x) + std::abs(q.y - origin.y) +
                  std::abs(q.z - origin.z) >
              g.reach_q ||
          visited.contains(q))
        continue;
      visited.insert(q);
      if (spatially_clear(physical(p, g), physical(q, g), body_half(ref.id)))
        frontier.push_back(q);
      if (frontier.size() >= required)
        return false;
    }
  return frontier.size() < required;
}
} // namespace antworld
