#include "antworld/core/inspection.hpp"
#include "social_internal.hpp"
#include <algorithm>

namespace antworld {
void WorldRuntime::inspect_decision(const ScheduledEvent &e,
                                    const ContactSample &sample,
                                    std::uint64_t context, std::uint64_t choice,
                                    EntityId recipient) const {
  const auto &target = inspection::target;
  if (!target.output || target.world != state_->world)
    return;
  const auto &s = *state_;
  const auto queen = query_ant({s.world, target.queen});
  const auto q = query_physiology({s.world, target.queen});
  const auto actor = query_ant({s.world, e.actor});
  const auto p = query_physiology({s.world, e.actor});
  if (!queen || !q || !actor || !p)
    throw std::logic_error("invalid inspection target");
  const auto signal =
      detail::signaled_need(*q, queen->stage, s.long_term != nullptr);
  const auto &colony = s.colonies.rows[s.colonies.index.at(actor->colony)];
  inspection::Decision d;
  d.time_ms = static_cast<std::uint64_t>(s.m.now.milliseconds);
  d.source = e.id.value;
  d.actor = e.actor.value;
  d.context = context;
  d.behavior = static_cast<std::uint64_t>(p->behavior);
  d.choice = choice;
  d.recipient = recipient.value;
  d.candidates = sample.candidates_examined;
  d.sampled_queen =
      std::find(sample.ants.begin(), sample.ants.end(),
                AntRef{s.world, target.queen}) != sample.ants.end();
  d.reachable_queen =
      queen->alive() &&
      detail::contact(*actor, *queen, s.config,
                      s.social && s.geometry ? nullptr : s.surface.get()) &&
      spatially_clear(actor->position, queen->position);
  d.queen_alive = queen->alive();
  d.queen_energy_nj = q->body_energy_nj;
  d.queen_water_ug = q->hydration_ug;
  d.queen_crop_carbs_ug = q->crop.carbs_ug;
  d.queen_crop_protein_ug = q->crop.protein_ug;
  d.queen_crop_water_ug = q->crop.water_ug;
  d.signal_carbs_ug = signal.carbs_ug;
  d.signal_protein_ug = signal.protein_ug;
  d.signal_water_ug = signal.water_ug;
  d.donor_energy_nj = p->body_energy_nj;
  d.donor_water_ug = p->hydration_ug;
  d.donor_crop_carbs_ug = p->crop.carbs_ug;
  d.donor_crop_protein_ug = p->crop.protein_ug;
  d.donor_crop_water_ug = p->crop.water_ug;
  d.donor_urgent = (p->body_energy_nj < p->config.energy_capacity_nj / 4 &&
                    !p->crop.carbs_ug) ||
                   (p->hydration_ug < p->config.hydration_capacity_ug / 4 &&
                    !p->crop.water_ug);
  d.owns_journey = p->behavior == IndividualBehavior::Forage ||
                   p->behavior == IndividualBehavior::Excavate;
  d.at_depot = actor->position == colony.nest_position;
  if (s.autonomy.contains(actor->id))
    d.hold_elapsed_ms = static_cast<std::uint64_t>(
        s.m.now.milliseconds -
        s.autonomy.at(actor->id).last_program_change.milliseconds);
  target.output->push_back(d);
}
} // namespace antworld
