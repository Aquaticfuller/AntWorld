#include "physiology_internal.hpp"
#include "social_internal.hpp"
#include "behavior_rng.hpp"

namespace antworld {
using namespace detail;
void WorldRuntime::enable_physiology(AntRef ref, const PhysiologySeed& seed, const PhysiologyConfig& config) {
    auto& s = *state_; const auto ant = query_ant(ref);
    if (!ant || !ant->alive() || s.m.now != SimTime{} || s.m.watermark || s.physiology.contains(ref.id))
        throw std::invalid_argument("physiology fixture initialization requires an unexecuted living individual");
    validate_physiology(seed, config);
    for (const auto& [key, e] : s.queue) {
        (void)key;
        if (e.actor == ref.id && e.kind == ScheduledEvent::Kind::Lifecycle && e.stage != LifeStage::Dead)
            throw std::invalid_argument("remove forced development before enabling physiology");
    }
    Transaction tx(s, limits_); PhysiologyState p;
    p.config = config; p.initial = seed; p.crop = seed.crop; p.body_energy_nj = seed.body_energy_nj;
    p.hydration_ug = seed.hydration_ug; p.tissue_protein_ug = seed.tissue_protein_ug;
    p.next_absorption = config.absorption_period;
    if (s.foragers.contains(ref.id) && s.foragers.at(ref.id).enabled) p.behavior = IndividualBehavior::Forage;
    tx.physiology.set(ref.id, p); schedule_physiology(tx, ref.id);
    WorldEvent f; f.kind = FactKind::PhysiologyEnabled; f.actor = ref.id; f.colony = ant->colony; f.stage = ant->stage;
    f.position = ant->position; f.transferred = seed.crop; tx.fact(f);
    validate_nutrition_capacity();
    tx.commit();
}
void WorldRuntime::synchronize_physiology(Transaction& tx, EntityId id) {
    auto& s = *state_; if (!s.physiology.contains(id)) return;
    auto p = s.physiology.at(id); settle(p, s.ants.get(s.ants.index.at(id)).stage, s.m.now); tx.physiology.set(id, p);
}
void WorldRuntime::schedule_physiology(Transaction& tx, EntityId id) {
    auto& s = *state_; auto p = s.physiology.at(id); const auto ant = s.ants.get(s.ants.index.at(id));
    if (p.physiology_event.value && s.queue_index.contains(p.physiology_event)) tx.remove(s.queue_index.at(p.physiology_event));
    p.physiology_event = {};
    if (ant.alive()) {
        ScheduledEvent e; e.actor = id; e.kind = ScheduledEvent::Kind::Physiology; e.issued_at = s.m.now;
        e.key = {next_physiology(p, ant.stage), Phase::Environment, 0, 0, 0}; p.physiology_event = tx.insert(e);
    }
    tx.physiology.set(id, p);
}
void WorldRuntime::stop_physiology(Transaction& tx, EntityId id, DeathCause cause) {
    auto& s = *state_; if (!s.physiology.contains(id)) return;
    auto p = s.physiology.at(id);
    // Lifecycle fixtures may interrupt before the next physiological boundary.
    const auto stage = s.ants.get(s.ants.index.at(id)).stage;
    if (stage != LifeStage::Dead) settle(p, stage, s.m.now);
    for (const auto event : {p.physiology_event, p.behavior_event})
        if (event.value && s.queue_index.contains(event)) tx.remove(s.queue_index.at(event));
    p.physiology_event = {}; p.behavior_event = {}; p.behavior = IndividualBehavior::Paused;
    p.death_cause = cause; tx.physiology.set(id, p);
}
void WorldRuntime::execute_physiology(Transaction& tx, const ScheduledEvent& e) {
    profiling::Scope profile(profiling::Category::Physiology);
    auto& s = *state_; const auto i = s.ants.index.at(e.actor); auto ant = s.ants.get(i); auto p = s.physiology.at(e.actor);
    if (!ant.alive() || p.physiology_event != e.id) throw std::logic_error("invalid physiology event ownership");
    settle(p, ant.stage, s.m.now); p.physiology_event = {};
    WorldEvent f; f.source = e.id; f.actor = e.actor; f.colony = ant.colony; f.position = ant.position; f.stage = ant.stage;
    f.kind = FactKind::PhysiologyUpdated;
    if (!p.body_energy_nj || !p.hydration_ug) {
        p.death_cause = !p.body_energy_nj ? DeathCause::EnergyDepleted : DeathCause::Dehydrated;
        f.kind = FactKind::AntDied; f.stage = LifeStage::Dead; f.payload = static_cast<std::uint64_t>(p.death_cause);
        tx.touch_ant(i); ant.stage = LifeStage::Dead; s.ants.set(i, ant); --s.m.living;
        index_contact(tx,e.actor,{});
        tx.physiology.set(e.actor, p); stop_dead_forager(tx, e.actor); stop_excavator(tx,e.actor); stop_physiology(tx, e.actor, p.death_cause); stop_autonomy(tx,e.actor);
    } else {
        if (developing(p, ant.stage) && p.stage_progress == stage_duration(p.config, ant.stage)) {
            tx.touch_ant(i); ant.stage = static_cast<LifeStage>(static_cast<unsigned>(ant.stage)+1); s.ants.set(i, ant);
            p.stage_progress = {}; f.kind = FactKind::StageChanged; f.stage = ant.stage;
            if (ant.stage==LifeStage::Adult) schedule_autonomy(tx,e.actor);
        } else if (s.m.now == p.next_absorption) f.transferred = absorb(p, ant.stage);
        tx.physiology.set(e.actor, p); schedule_physiology(tx, e.actor);
    }
    tx.fact(f);
}
void WorldRuntime::set_behavior(AntRef ref, IndividualBehavior behavior) {
    Transaction tx(*state_,limits_);
    change_behavior(tx,ref,behavior);
    if (state_->autonomy.contains(ref.id) && state_->autonomy.at(ref.id).enabled) change_autonomy(tx,ref,false);
    tx.commit();
}
void WorldRuntime::change_behavior(Transaction& tx, AntRef ref, IndividualBehavior behavior, ScheduledId source) {
    auto& s = *state_; const auto ant = query_ant(ref);
    if (!ant || !ant->alive() || !s.physiology.contains(ref.id) || behavior > IndividualBehavior::Excavate ||
        (behavior != IndividualBehavior::Paused && (ant->stage != LifeStage::Adult || ant->caste != Caste::Worker)))
        throw std::invalid_argument("invalid individual behavior activation");
    if (behavior == IndividualBehavior::Forage && (!s.surface || !s.surface->locate(ant->position))) throw std::invalid_argument("foraging requires a surface position");
    if (behavior == IndividualBehavior::Excavate && !s.geometry) throw std::invalid_argument("excavation requires geometry");
    // External pending actions must be explicitly resolved/cancelled, never silently commandeered.
    if (!source.value) for (const auto& [key, e] : s.queue) {
        (void)key;
        if (e.actor == ref.id && e.key.phase == Phase::Resolution && e.id != s.physiology.at(ref.id).behavior_event &&
            (!s.foragers.contains(ref.id) || e.id != s.foragers.at(ref.id).action) &&
            (!s.excavators.contains(ref.id) || e.id != s.excavators.at(ref.id).action))
            throw std::invalid_argument("individual has an external pending action");
    }
    synchronize_physiology(tx, ref.id); auto p = s.physiology.at(ref.id);
    if (p.behavior_event.value && s.queue_index.contains(p.behavior_event)) tx.remove(s.queue_index.at(p.behavior_event));
    p.behavior_event = {};
    stop_dead_forager(tx, ref.id); // This helper cancels behavior work and preserves acquired memory.
    stop_excavator(tx,ref.id);
    p.behavior = behavior; tx.physiology.set(ref.id, p);
    if (behavior == IndividualBehavior::Forage) {
        ForagerState f;
        if (s.foragers.contains(ref.id)) f = s.foragers.at(ref.id);
        else {
            const auto& nest = s.colonies.rows[s.colonies.index.at(ant->colony)].nest_position;
            if (ant->position != nest || ant->carried_food.total_ug() || !ant->carrying_capacity_ug)
                throw std::invalid_argument("first foraging activation requires an unloaded worker at its nest");
            f.path[0] = *s.surface->locate(ant->position); f.path_size = 1; f.heading = initial_heading(s.seed, ref.id);
            if (!s.visits.contains(f.path[0])) tx.visits.set(f.path[0], 0);
            WorldEvent initial; initial.kind = FactKind::ForagingStarted; initial.actor = ref.id; initial.colony = ant->colony;
            initial.position = ant->position; initial.stage = ant->stage; tx.fact(initial);
        }
        if (f.path[f.path_size-1]!=*s.surface->locate(ant->position))
            throw std::invalid_argument("foraging memory no longer ends at worker position");
        f.enabled = true; ScheduledEvent e; e.actor = ref.id; e.kind = ScheduledEvent::Kind::Wake; e.issued_at = s.m.now;
        e.key = {after(s.m.now, s.surface->behavior.decision_delay.milliseconds), Phase::Perception, 0, 0, 0};
        f.wake = tx.insert(e); tx.foragers.set(ref.id, f);
    } else if (behavior == IndividualBehavior::Excavate) {
        activate_excavator(tx,ref.id);
    } else if (behavior != IndividualBehavior::Paused) {
        ScheduledEvent e; e.actor = ref.id; e.kind = ScheduledEvent::Kind::NutritionWake; e.issued_at = s.m.now;
        e.key = {after(s.m.now, p.config.behavior_interval.milliseconds), Phase::Perception, 0, 0, 0};
        p.behavior_event = tx.insert(e); tx.physiology.set(ref.id, p);
    }
    schedule_physiology(tx, ref.id);
    WorldEvent f; f.kind = FactKind::BehaviorChanged; f.actor = ref.id; f.colony = ant->colony; f.stage = ant->stage;
    f.source=source; f.position = ant->position; f.payload = static_cast<std::uint64_t>(behavior); tx.fact(f);
    if (s.autonomy.contains(ref.id)) { auto a=s.autonomy.at(ref.id); a.last_program_change=s.m.now; tx.autonomy.set(ref.id,a); }
}
ScheduledId WorldRuntime::submit_nutrition(const NutritionProposal& proposal) {
    auto& s = *state_; const auto ant = query_ant(proposal.actor);
    if (!ant || !s.physiology.contains(ant->id) || (s.autonomy.contains(ant->id) && s.autonomy.at(ant->id).enabled) || proposal.kind > NutritionAction::Trophallaxis || !proposal.requested_ug ||
        s.physiology.at(ant->id).behavior != IndividualBehavior::Paused ||
        (s.foragers.contains(ant->id) && s.foragers.at(ant->id).enabled)) throw std::invalid_argument("invalid nutrition proposal");
    if (proposal.kind == NutritionAction::Trophallaxis && (!query_ant(proposal.recipient) ||
        !s.physiology.contains(proposal.recipient.id) || proposal.recipient.id == ant->id))
        throw std::invalid_argument("invalid world-qualified nutrition recipient");
    ScheduledEvent e; e.actor = ant->id; e.issued_at = s.m.now; e.requested_ug = proposal.requested_ug;
    e.kind = static_cast<ScheduledEvent::Kind>(static_cast<unsigned>(ScheduledEvent::Kind::IngestCargo)+static_cast<unsigned>(proposal.kind));
    e.payload = proposal.kind == NutritionAction::Trophallaxis ? proposal.recipient.id.value : 0;
    e.observed_position_revision = ant->position_revision; e.key = {proposal.execute_at, Phase::Resolution, 0, 0, 0};
    Transaction tx(s, limits_); const auto id = tx.insert(e); tx.commit(); return id;
}
void WorldRuntime::resolve_nutrition_action(Transaction& tx, const ScheduledEvent& e, WorldEvent& f) {
    auto& s = *state_; const auto i = s.ants.index.at(e.actor); auto ant = s.ants.get(i);
    synchronize_physiology(tx, e.actor); auto p = s.physiology.at(e.actor); f.payload = e.payload;
    FoodMass supply; std::uint64_t room = p.config.crop_capacity_ug-p.crop.total_ug();
    std::optional<PhysiologyState> receiver;
    if (e.kind == ScheduledEvent::Kind::Trophallaxis) {
        const auto recipient = s.ants.get(s.ants.index.at(EntityId{e.payload}));
        if (!recipient.alive()) { f.outcome = Outcome::DeadActor; return; }
        if (recipient.stage != LifeStage::Adult && recipient.stage != LifeStage::Larva) { f.outcome = Outcome::InvalidStage; return; }
        if (!contact(ant, recipient, s.config, s.social && s.geometry ? nullptr : s.surface.get()) || !spatially_clear(ant.position,recipient.position)) { f.outcome = Outcome::OutOfReach; return; }
        synchronize_physiology(tx, recipient.id); receiver = s.physiology.at(recipient.id);
        room = receiver->config.crop_capacity_ug-receiver->crop.total_ug(); supply = p.crop;
        if (s.social && !s.social->exchange_enabled) { f.outcome = Outcome::EmptyInventory; return; }
        if (s.social && s.social->demand_sensitive)
            supply = ingredient_min(supply,nutrient_demand(*receiver,recipient.stage));
    } else if (e.kind == ScheduledEvent::Kind::IngestCargo) supply = ant.carried_food;
    else {
        const auto& colony = s.colonies.rows[s.colonies.index.at(ant.colony)];
        if (distance(ant.position, colony.nest_position) > s.config.contact_distance_m ||
            (s.surface && !(s.social && s.geometry) && s.surface->locate(ant.position) != s.surface->locate(colony.nest_position)) || !spatially_clear(ant.position,colony.nest_position)) { f.outcome = Outcome::NotAtNest; return; }
        supply = colony.nest_food;
    }
    if (!room) { f.outcome = Outcome::Capacity; return; }
    if (!supply.total_ug()) { f.outcome = Outcome::EmptyInventory; return; }
    const auto amount = std::min({e.requested_ug, room, supply.total_ug()}); f.transferred = portion(supply, amount);
    f.outcome = amount == e.requested_ug ? Outcome::Success : Outcome::Partial;
    if (receiver) {
        p.crop = subtract(p.crop, f.transferred); receiver->crop = sum(receiver->crop, f.transferred);
        tx.physiology.set(EntityId{e.payload}, *receiver); f.kind = FactKind::NutritionTransferred;
    } else {
        p.crop = sum(p.crop, f.transferred);
        if (e.kind == ScheduledEvent::Kind::IngestCargo) {
            tx.touch_ant(i); ant.carried_food = subtract(ant.carried_food, f.transferred); s.ants.set(i, ant);
            s.m.ledger.carried = subtract(s.m.ledger.carried, f.transferred); f.kind = FactKind::CargoIngested;
        } else {
            const auto j = s.colonies.index.at(ant.colony); tx.touch_colony(j);
            s.colonies.rows[j].nest_food = subtract(s.colonies.rows[j].nest_food, f.transferred);
            s.m.ledger.stored = subtract(s.m.ledger.stored, f.transferred); f.kind = FactKind::NestIngested;
        }
    }
    tx.physiology.set(e.actor, p);
}
void WorldRuntime::resolve_nutrition_wakes(Transaction& tx, const std::vector<ScheduledEvent>& wakes) {
    profiling::Scope profile(profiling::Category::Policy);
    auto& s = *state_; std::vector<ScheduledEvent> actions(0); actions.reserve(wakes.size());
    std::vector<ContactSample> encounters(wakes.size());
    for (const auto& wake : wakes) {
        const auto ant = s.ants.get(s.ants.index.at(wake.actor)); const auto p = *query_physiology({s.world, ant.id});
        if (p.behavior_event != wake.id || !ant.alive()) throw std::logic_error("invalid nutrition wake ownership");
        ScheduledEvent action; action.actor = ant.id; action.issued_at = s.m.now; action.kind = ScheduledEvent::Kind::Rest;
        action.key = {after(s.m.now, 1), Phase::Resolution, 0, 0, 0}; action.observed_position_revision = ant.position_revision;
        const auto& colony = s.colonies.rows[s.colonies.index.at(ant.colony)];
        if (p.crop.total_ug() < p.config.crop_capacity_ug/2 && ant.carried_food.total_ug()) action.kind = ScheduledEvent::Kind::IngestCargo;
        else if (p.crop.total_ug() < p.config.crop_capacity_ug/2 && colony.nest_food.total_ug() &&
            distance(ant.position, colony.nest_position) <= s.config.contact_distance_m &&
            (!s.surface || (s.social && s.geometry) || s.surface->locate(ant.position) == s.surface->locate(colony.nest_position)) && spatially_clear(ant.position,colony.nest_position)) action.kind = ScheduledEvent::Kind::WithdrawNest;
        else if (p.behavior == IndividualBehavior::Nurse && p.crop.total_ug()) {
            auto rng = individual_rng(s.seed ^ UINT64_C(0x53334e55525345), ant.id, p.decisions);
            std::uint64_t seen = 0;
            // Geometry worlds use a spatial index; legacy worlds retain their canonical candidate order.
            std::vector<EntityId> candidates(0);
            if (s.social) {
                encounters[actions.size()]=sample_contacts({s.world,ant.id},p.decisions);
                for (const auto neighbor:encounters[actions.size()].ants)
                    if (s.physiology.contains(neighbor.id)) candidates.push_back(neighbor.id);
            } else if (s.geometry) {
                for (const auto& neighbor:query_neighborhood({s.world,ant.id},s.config.contact_distance_m).ants)
                    if (s.physiology.contains(neighbor.id)) candidates.push_back(neighbor.id);
            } else {
                for (const auto& [id,unused]:s.physiology) { (void)unused; candidates.push_back(id); }
            }
            for (const auto id : candidates) {
                const auto other = s.ants.get(s.ants.index.at(id));
                if (id == ant.id || !other.alive() || !contact(ant, other, s.config, s.social && s.geometry ? nullptr : s.surface.get())) continue;
                const auto q = *query_physiology({s.world, id});
                const bool hungry_larva = other.stage == LifeStage::Larva && p.crop.protein_ug &&
                    add(q.tissue_protein_ug, q.crop.protein_ug) < q.config.larval_protein_requirement_ug;
                const bool hungry_adult = other.stage == LifeStage::Adult &&
                    (q.body_energy_nj < q.config.energy_capacity_nj/4 || q.hydration_ug < q.config.hydration_capacity_ug/4);
                const bool demand=s.social && s.social->demand_sensitive;
                if (demand ? (!ingredient_min(p.crop,signaled_need(q,other.stage)).total_ug() || q.crop.total_ug()>=q.config.crop_capacity_ug) :
                    ((!hungry_larva && !hungry_adult) || q.crop.total_ug() >= q.config.crop_capacity_ug/2)) continue;
                ++seen; if (bounded_draw(rng, seen) == 0) { action.kind = ScheduledEvent::Kind::Trophallaxis; action.payload = id.value; }
            }
        }
        if (action.kind != ScheduledEvent::Kind::Rest) action.requested_ug = p.config.transfer_limit_ug;
        actions.push_back(action);
    }
    // All choices above observe the same committed boundary, never earlier submissions.
    for (std::size_t i = 0; i < actions.size(); ++i) {
        auto p = s.physiology.at(actions[i].actor); bump(p.decisions); p.behavior_event = tx.insert(actions[i]);
        tx.physiology.set(actions[i].actor, p);
        const auto ant = s.ants.get(s.ants.index.at(actions[i].actor));
        WorldEvent f; f.source = wakes[i].id; f.actor = ant.id; f.colony = ant.colony; f.position = ant.position; f.stage = ant.stage;
        if (s.social) {
            const auto& sample=encounters[i]; auto& work=s.m.contact_work;
            bump(work.decisions); work.candidates_examined=add(work.candidates_examined,sample.candidates_examined);
            work.bucket_queries=add(work.bucket_queries,sample.bucket_queries); work.tree_visits=add(work.tree_visits,sample.tree_visits);
            work.maximum_candidates=std::max(work.maximum_candidates,sample.candidates_examined);
            f.random_value=sample.candidates_examined;
        }
        f.kind = FactKind::NutritionDecision; f.payload = p.decisions; tx.fact(f);
    }
}
void WorldRuntime::continue_nutrition_behavior(Transaction& tx, const ScheduledEvent& action) {
    auto& s = *state_; if (!s.physiology.contains(action.actor)) return;
    auto p = s.physiology.at(action.actor); if (p.behavior_event != action.id) return;
    ScheduledEvent e; e.actor = action.actor; e.kind = ScheduledEvent::Kind::NutritionWake; e.issued_at = s.m.now;
    e.key = {after(s.m.now, p.config.behavior_interval.milliseconds), Phase::Perception, 0, 0, 0};
    p.behavior_event = tx.insert(e); tx.physiology.set(e.actor, p);
}
std::optional<PhysiologyState> WorldRuntime::query_physiology(AntRef ref) const {
    profiling::Scope profile(profiling::Category::Physiology);
    const auto& s = *state_; const auto ant = query_ant(ref);
    if (!ant || !s.physiology.contains(ref.id)) return {};
    auto p = s.physiology.at(ref.id); settle(p, ant->stage, s.m.now); return p;
}
NutritionSnapshot WorldRuntime::nutrition_snapshot() const {
    const auto& s = *state_; NutritionSnapshot n;
    n.introduced = s.m.ledger.introduced; n.accounted = sum(sum(s.m.ledger.available, s.m.ledger.carried), s.m.ledger.stored);
    for (const auto& [id, unused] : s.physiology) {
        (void)unused; const auto p = *query_physiology({s.world, id}); ++n.individuals;
        n.introduced = sum(n.introduced, sum(p.initial.crop, {0, p.initial.tissue_protein_ug, p.initial.hydration_ug, 0}));
        n.crop = sum(n.crop, p.crop); n.hydration_ug = add(n.hydration_ug, p.hydration_ug);
        n.tissue_protein_ug = add(n.tissue_protein_ug, p.tissue_protein_ug); n.oxidized_carbs_ug = add(n.oxidized_carbs_ug, p.oxidized_carbs_ug);
        n.lost_water_ug = add(n.lost_water_ug, p.lost_water_ug);
        n.energy_input_nj = add(n.energy_input_nj, add(p.initial.body_energy_nj, multiply(p.oxidized_carbs_ug, p.config.carbohydrate_yield_nj_per_ug)));
        n.body_energy_nj = add(n.body_energy_nj, p.body_energy_nj); n.dissipated_energy_nj = add(n.dissipated_energy_nj, p.dissipated_energy_nj);
    }
    n.accounted = sum(n.accounted, sum(n.crop, {n.oxidized_carbs_ug, n.tissue_protein_ug, add(n.hydration_ug, n.lost_water_ug), 0}));
    return n;
}
void WorldRuntime::validate_nutrition_capacity() const {
    const auto& s = *state_; if (s.physiology.empty()) return;
    const auto n = nutrition_snapshot(); (void)n.introduced.total_ug();
    std::uint64_t initial_energy = 0, max_yield = 0;
    for (const auto& [id, p] : s.physiology) {
        (void)id; initial_energy = add(initial_energy, p.initial.body_energy_nj);
        max_yield = std::max(max_yield, p.config.carbohydrate_yield_nj_per_ug);
    }
    // Bound even complete future carbohydrate oxidation, so queries never discover
    // an overflow that a previous mutation should have rejected.
    (void)add(initial_energy, multiply(n.introduced.carbs_ug, max_yield));
}
} // namespace antworld
