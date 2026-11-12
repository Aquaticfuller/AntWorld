#pragma once
#include "checkpoint_codec.hpp"
#include "long_term_internal.hpp"
#include "founding_internal.hpp"

namespace antworld::detail {
inline constexpr std::array reproduction_values{
    &ReproductionConfig::egg_protein_ug, &ReproductionConfig::egg_water_ug,
    &ReproductionConfig::egg_energy_nj,
    &ReproductionConfig::dissipated_energy_nj,
    &ReproductionConfig::offspring_carrying_capacity_ug};
template <class S> void write_long_term(Writer &w, const S &s, bool guarded) {
  if (!s.long_term)
    return;
  w.put(s.long_term->demand_feedback, 1);
  w.put(s.long_term->protein_recycling, 1);
  w.put(s.long_term->empty_sites_per_contact, 4);
  w.put(s.long_term->complete_depot_visits, 1);
  w.put(s.long_term->post_intake_contact, 1);
  w.put(s.reproduction.size());
  for (const auto &[id, r] : s.reproduction) {
    w.put(id.value);
    w.time(r.config.interval);
    for (const auto m : reproduction_values)
      w.put(r.config.*m);
    if (guarded)
      w.time(r.config.maintenance_horizon);
    w.put(r.wake.value);
    w.put(r.attempts);
    w.put(r.births);
  }
  w.put(s.resource_cycles.size());
  for (const auto &[id, r] : s.resource_cycles) {
    w.put(id.value);
    w.mass(r.config.reserve);
    w.mass(r.config.release_limit);
    w.time(r.config.interval);
    w.time(r.config.productive_span);
    w.put(r.config.cyclic, 1);
    w.put(r.config.low_productivity_permille, 4);
    w.mass(r.remaining);
    w.mass(r.released);
    w.put(r.wake.value);
    w.put(r.pulses);
  }
}
template <class S> void read_long_term(Reader &r, S &s, bool guarded, bool founding) {
  if (!s.long_term)
    return;
  LongTermConfig c{r.flag(), r.flag(), static_cast<std::uint32_t>(r.get(4)),
                   r.flag(), r.flag()};
  validate_long_term(c);
  s.long_term = std::make_shared<const LongTermConfig>(c);
  auto count = r.count(s.ants.size(), 80);
  for (std::size_t i = 0; i < count; ++i) {
    const EntityId id{r.get()};
    ReproductionState q;
    q.config.interval = r.time();
    for (const auto m : reproduction_values)
      q.config.*m = r.get();
    if (guarded)
      q.config.maintenance_horizon = r.time();
    q.wake = {r.get()};
    q.attempts = r.get();
    q.births = r.get();
    ensure(s.physiology.contains(id) &&
               s.ants.get(s.ants.index.at(id)).caste == Caste::Queen &&
               q.births <= q.attempts && s.reproduction.emplace(id, q).second,
           "invalid queen record");
    if (!founding) validate_reproduction(q.config, s.physiology.at(id).config);
  }
  count = r.count(s.foods.rows.size(), 173);
  for (std::size_t i = 0; i < count; ++i) {
    const ResourceId id{r.get()};
    ResourceCycleState q;
    q.config.reserve = r.mass();
    q.config.release_limit = r.mass();
    q.config.interval = r.time();
    q.config.productive_span = r.time();
    q.config.cyclic = r.flag();
    q.config.low_productivity_permille = static_cast<std::uint32_t>(r.get(4));
    q.remaining = r.mass();
    q.released = r.mass();
    q.wake = {r.get()};
    q.pulses = r.get();
    validate_cycle(q.config);
    ensure(s.foods.index.contains(id) &&
               sum(q.remaining, q.released) == q.config.reserve &&
               s.resource_cycles.emplace(id, q).second,
           "invalid finite reserve");
  }
}
template <class S> void validate_long_term_evidence(const S &s) {
  std::uint64_t configured = 0;
  typename S::Reproduction queens;
  typename S::ResourceCycles cycles;
  std::map<EntityId, LifeStage> stages;
  std::map<ScheduledId, std::pair<EntityId, EntityId>> births;
  SimTime next_founding_lay = s.founding ? s.founding->profile.first_lay : SimTime{};
  for (const auto &e : s.journal) {
    if (e.kind == FactKind::AntSeeded || e.kind == FactKind::AntBorn ||
        e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied)
      stages[e.actor] = e.stage;
    if (e.kind == FactKind::LongTermConfigured) {
      ensure(s.long_term && e.time == SimTime{} &&
                 e.payload == long_term_fingerprint(*s.long_term) &&
                 !e.actor.value && !e.resource.value && !e.colony.value,
             "invalid long-term policy evidence");
      ++configured;
    } else if (e.kind == FactKind::ReproductionEnabled) {
      ensure(s.long_term && s.reproduction.contains(e.actor) &&
                 e.time == SimTime{} && !queens.contains(e.actor) &&
                 stages[e.actor] == LifeStage::Adult,
             "invalid reproduction enrollment");
      ReproductionState q;
      q.config = s.reproduction.at(e.actor).config;
      ensure(e.payload == static_cast<std::uint64_t>(
                              q.config.maintenance_horizon.milliseconds),
             "maternal allocation contract differs from enrollment evidence");
      queens.emplace(e.actor, q);
    } else if (e.kind == FactKind::ReproductionAttempt) {
      ensure(queens.contains(e.actor) && stages[e.actor] == LifeStage::Adult,
             "attempt by inactive queen");
      auto &q = queens.at(e.actor);
      bump(q.attempts);
      if (s.founding && e.actor == s.founding->founder) {
        ensure(e.time == next_founding_lay, "unexpected F1 reproduction timing");
        next_founding_lay = founding_lay_after(s.founding->profile, e.time);
      } else ensure(e.time.milliseconds ==
                 static_cast<std::int64_t>(
                     multiply(q.attempts, static_cast<std::uint64_t>(
                                              q.config.interval.milliseconds))),
             "unexpected reproduction timing");
      if (e.payload) {
        bump(q.births);
        ensure(births.emplace(e.source, std::pair{e.actor, EntityId{e.payload}})
                   .second,
               "duplicate birth attempt");
      }
    } else if (e.kind == FactKind::AntBorn) {
      ensure(s.long_term && births.contains(e.source) &&
                 births.at(e.source) ==
                     std::pair{EntityId{e.payload}, e.actor} &&
                 s.ants.get(s.ants.index.at(e.actor)).born_at == e.time,
             "birth lacks successful maternal attempt");
      births.erase(e.source);
      const auto &c = s.reproduction.at(EntityId{e.payload}).config;
      const auto child = s.ants.get(s.ants.index.at(e.actor)),
                 mother = s.ants.get(s.ants.index.at(EntityId{e.payload}));
      ensure(child.colony == mother.colony &&
                 child.carrying_capacity_ug == c.offspring_carrying_capacity_ug,
             "offspring identity differs from maternal contract");
    } else if (e.kind == FactKind::ResourceCycleConfigured) {
      ensure(s.long_term && s.resource_cycles.contains(e.resource) &&
                 !cycles.contains(e.resource) && e.time == SimTime{},
             "invalid reserve setup evidence");
      ResourceCycleState q;
      q.config = s.resource_cycles.at(e.resource).config;
      q.remaining = q.config.reserve;
      ensure(e.transferred == q.remaining, "reserve input mismatch");
      cycles.emplace(e.resource, q);
    } else if (e.kind == FactKind::ResourceReleased) {
      ensure(cycles.contains(e.resource), "release without finite source");
      auto &q = cycles.at(e.resource);
      bump(q.pulses);
      ensure(e.time.milliseconds ==
                     static_cast<std::int64_t>(multiply(
                         q.pulses, static_cast<std::uint64_t>(
                                       q.config.interval.milliseconds))) &&
                 e.payload == productivity(q.config, e.time) &&
                 e.transferred == release_amount(q, e.time),
             "invalid environment release evidence");
      q.remaining = subtract(q.remaining, e.transferred);
      q.released = sum(q.released, e.transferred);
    }
    if (e.kind == FactKind::ResourceCycleConfigured ||
        e.kind == FactKind::ResourceReleased)
      ensure(!e.actor.value && !e.colony.value &&
                 e.position ==
                     s.foods.rows[s.foods.index.at(e.resource)].position,
             "resource evidence has foreign spatial identity");
  }
  ensure(configured == (s.long_term ? 1U : 0U) && births.empty() &&
             queens.size() == s.reproduction.size() &&
             cycles.size() == s.resource_cycles.size(),
         "missing long-term evidence");
  for (const auto &[id, q] : s.reproduction) {
    auto expected = queens.at(id);
    expected.wake = q.wake;
    ensure(expected == q, "reproduction counts differ from history");
    const bool alive = s.ants.get(s.ants.index.at(id)).alive();
    ensure(alive == (q.wake.value != 0),
           "reproduction death ownership mismatch");
    if (alive) {
      ensure(s.queue_index.contains(q.wake), "missing queen wake");
      const auto &e = s.queue.at(s.queue_index.at(q.wake));
      ensure(e.actor == id && e.kind == ScheduledEvent::Kind::Reproduction &&
                 e.key.time == (s.founding && id == s.founding->founder ? next_founding_lay :
                     after(e.issued_at, q.config.interval.milliseconds)),
             "invalid next reproduction time");
    }
  }
  for (const auto &[id, q] : s.resource_cycles) {
    auto expected = cycles.at(id);
    expected.wake = q.wake;
    ensure(expected == q && s.queue_index.contains(q.wake),
           "reserve state differs from evidence");
    const auto &e = s.queue.at(s.queue_index.at(q.wake));
    ensure(e.resource == id &&
               e.kind == ScheduledEvent::Kind::ResourceRelease &&
               e.key.time == after(e.issued_at, q.config.interval.milliseconds),
           "invalid next resource pulse");
  }
}
template <class S> void rebuild_nutrition_budget(S &s) {
  for (const auto &[id, p] : s.physiology) {
    const auto ant = s.ants.get(s.ants.index.at(id));
    ensure(!p.config.adult_protein_target_ug ||
               (s.long_term && ant.caste == Caste::Queen),
           "worker has reproductive nutrition target");
    if (!p.mother.value) {
      s.m.physiology_inputs =
          sum(s.m.physiology_inputs,
              sum(p.initial.crop,
                  {0, p.initial.tissue_protein_ug, p.initial.hydration_ug, 0}));
      if (s.founding && id == s.founding->founder)
        s.m.physiology_inputs.protein_ug = add(s.m.physiology_inputs.protein_ug, s.founding->profile.protein_ug);
      else s.m.initial_energy = add(s.m.initial_energy, p.initial.body_energy_nj);
    }
    s.m.maximum_yield =
        std::max(s.m.maximum_yield, p.config.carbohydrate_yield_nj_per_ug);
  }
  for (const auto &[key, e] : s.queue) {
    if (e.kind == ScheduledEvent::Kind::Lifecycle && e.stage != LifeStage::Dead)
      bump(s.m.development_commands);
    if (key.phase == Phase::Resolution)
      bump(s.m.resolution_commands);
    if (s.long_term && e.actor.value &&
        ((e.kind == ScheduledEvent::Kind::Lifecycle &&
          e.stage != LifeStage::Dead) ||
         key.phase == Phase::Resolution))
      bump(
          s.pending_conflicts[e.actor][key.phase == Phase::Resolution ? 1 : 0]);
  }
}
} // namespace antworld::detail
