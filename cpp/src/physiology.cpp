#include "physiology_internal.hpp"
#include "social_internal.hpp"
#include "behavior_rng.hpp"
#include "spatial_navigation.hpp"
#include "founding_internal.hpp"

namespace antworld {
using namespace detail;
void WorldRuntime::enable_physiology(AntRef ref, const PhysiologySeed& seed, const PhysiologyConfig& config) {
    auto& s = *state_; const auto ant = query_ant(ref);
    if (!ant || !ant->alive() || s.m.now != SimTime{} || s.m.watermark || s.physiology.contains(ref.id))
        throw std::invalid_argument("physiology fixture initialization requires an unexecuted living individual");
    validate_physiology(seed, config);
    if ((!s.long_term && (config.water_loss_period != SimTime{1000} || config.adult_protein_target_ug ||
         config.absorption_period.milliseconds > 60000 || config.behavior_interval.milliseconds > 60000)) ||
        (config.adult_protein_target_ug && ant->caste != Caste::Queen))
        throw std::invalid_argument("long-term physiology requires its explicit world contract");
    if (s.long_term && s.pending_conflicts.contains(ref.id) && s.pending_conflicts.at(ref.id)[0])
        throw std::invalid_argument("remove forced development before enabling physiology");
    if (!s.long_term && s.m.development_commands) for (const auto& [key, e] : s.queue) {
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
    s.m.physiology_inputs = sum(s.m.physiology_inputs, sum(seed.crop, {0, seed.tissue_protein_ug, seed.hydration_ug, 0}));
    s.m.initial_energy = add(s.m.initial_energy, seed.body_energy_nj);
    s.m.maximum_yield = std::max(s.m.maximum_yield, config.carbohydrate_yield_nj_per_ug);
    WorldEvent f; f.kind = FactKind::PhysiologyEnabled; f.actor = ref.id; f.colony = ant->colony; f.stage = ant->stage;
    f.position = ant->position; f.transferred = seed.crop; tx.fact(f);
    validate_nutrition_capacity();
    tx.commit();
}
void WorldRuntime::synchronize_physiology(Transaction& tx, EntityId id) {
    auto& s = *state_; if (!s.physiology.contains(id)) return;
    auto p = s.physiology.at(id);
    const auto stage = s.ants.get(s.ants.index.at(id)).stage;
    if (s.founding && s.founding_reserves.contains(id)) {
        auto reserve = s.founding_reserves.at(id);
        settle_founding(s.founding->profile, p, reserve, stage, founding_foundress(id), s.m.now);
        tx.set_founding(id, reserve);
    } else settle(p, stage, s.m.now);
    tx.physiology.set(id, p);
}
void WorldRuntime::schedule_physiology(Transaction& tx, EntityId id) {
    auto& s = *state_; auto p = s.physiology.at(id); const auto ant = s.ants.get(s.ants.index.at(id));
    if (p.physiology_event.value && s.queue_index.contains(p.physiology_event)) tx.remove(s.queue_index.at(p.physiology_event));
    p.physiology_event = {};
    if (ant.alive()) {
        ScheduledEvent e; e.actor = id; e.kind = ScheduledEvent::Kind::Physiology; e.issued_at = s.m.now;
        const auto next = s.founding && s.founding_reserves.contains(id)
            ? next_founding_physiology(s.founding->profile, p, s.founding_reserves.at(id), ant.stage, founding_foundress(id))
            : next_physiology(p, ant.stage);
        e.key = {next, Phase::Environment, 0, 0, 0}; p.physiology_event = tx.insert(e);
    }
    tx.physiology.set(id, p);
}
void WorldRuntime::stop_physiology(Transaction& tx, EntityId id, DeathCause cause) {
    interrupt_care(tx,id,Outcome::DeadActor,true);
    stop_reproduction(tx, id);
    auto& s = *state_; if (!s.physiology.contains(id)) return;
    auto p = s.physiology.at(id);
    // Lifecycle fixtures may interrupt before the next physiological boundary.
    const auto stage = s.ants.get(s.ants.index.at(id)).stage;
    if (stage != LifeStage::Dead) {
        if (s.founding && s.founding_reserves.contains(id)) {
            auto reserve = s.founding_reserves.at(id);
            settle_founding(s.founding->profile, p, reserve, stage, founding_foundress(id), s.m.now);
            tx.set_founding(id, reserve);
        } else settle(p, stage, s.m.now);
    }
    for (const auto event : {p.physiology_event, p.behavior_event})
        if (event.value && s.queue_index.contains(event)) tx.remove(s.queue_index.at(event));
    p.physiology_event = {}; p.behavior_event = {}; p.behavior = IndividualBehavior::Paused;
    p.death_cause = cause; tx.physiology.set(id, p);
}
void WorldRuntime::execute_physiology(Transaction& tx, const ScheduledEvent& e) {
    profiling::Scope profile(profiling::Category::Physiology);
    auto& s = *state_; const auto i = s.ants.index.at(e.actor); auto ant = s.ants.get(i); auto p = s.physiology.at(e.actor);
    if (!ant.alive() || p.physiology_event != e.id) throw std::logic_error("invalid physiology event ownership");
    std::optional<FoundingReserve> reserve;
    const bool queen = founding_foundress(e.actor);
    if (s.founding && s.founding_reserves.contains(e.actor)) {
        reserve = s.founding_reserves.at(e.actor);
        settle_founding(s.founding->profile, p, *reserve, ant.stage, queen, s.m.now);
        tx.set_founding(e.actor, *reserve);
    } else settle(p, ant.stage, s.m.now);
    p.physiology_event = {};
    bool mobilized=false;
    if (reserve && !p.body_energy_nj) {
        const auto amount = mobilize_founding_larval_lipid(s.founding->profile, p, *reserve, ant.stage);
        if (amount) {
            auto conversion = lipid_conversion(s.founding->profile, ant, e.id, amount);
            conversion.kind = FactKind::FoundingLipidMobilized;
            tx.set_founding(e.actor, *reserve);
            tx.fact(conversion);
            mobilized=true;
        }
    }
    WorldEvent f; f.source = e.id; f.actor = e.actor; f.colony = ant.colony; f.position = ant.position; f.stage = ant.stage;
    std::optional<FoundingUptakeClock> clock;
    if (reserve && founding_boundary_enabled(s.founding->profile,ant.stage)) {
        const auto it=s.founding_uptake_clocks.find(e.actor);
        clock=it==s.founding_uptake_clocks.end()?FoundingUptakeClock{}:it->second;
        const auto dose=founding_boundary_uptake(p,*clock);
        if (dose.total_ug()) {
            f.kind=FactKind::FoundingBoundaryUptake;
            f.transferred=dose;
            tx.set_founding_uptake(e.actor,*clock);
            tx.fact(f);
            f.transferred={};
        }
    }
    f.kind = FactKind::PhysiologyUpdated;
    if (!p.body_energy_nj || !p.hydration_ug) {
        p.death_cause = !p.body_energy_nj ? DeathCause::EnergyDepleted : DeathCause::Dehydrated;
        f.kind = FactKind::AntDied; f.stage = LifeStage::Dead; f.payload = static_cast<std::uint64_t>(p.death_cause);
        tx.touch_ant(i); ant.stage = LifeStage::Dead; s.ants.set(i, ant); --s.m.living;
        index_contact(tx,e.actor,{});
        tx.physiology.set(e.actor, p); stop_dead_forager(tx, e.actor); stop_excavator(tx,e.actor); stop_physiology(tx, e.actor, p.death_cause); stop_autonomy(tx,e.actor);
    } else {
        const bool emitted_pulse = reserve && s.m.now == p.next_absorption;
        if (emitted_pulse) {
            f.transferred = clock ? founding_pulse(p,*clock,ant.stage) : absorb(p,ant.stage);
            if (clock) tx.set_founding_uptake(e.actor,*clock);
            tx.fact(f);
            const auto amount = convert_founding_lipid(s.founding->profile, p, *reserve, ant.stage, queen);
            if (amount) tx.fact(lipid_conversion(s.founding->profile, ant, e.id, amount));
            tx.set_founding(e.actor, *reserve);
        }
        const bool advance_stage = reserve ? (!mobilized || emitted_pulse) && founding_develops(s.founding->profile, p, *reserve, ant.stage) :
            developing(p, ant.stage) && p.stage_progress == stage_duration(p.config, ant.stage);
        if (advance_stage) {
            interrupt_care(tx,e.actor,Outcome::InvalidStage);
            tx.touch_ant(i); ant.stage = static_cast<LifeStage>(static_cast<unsigned>(ant.stage)+1); s.ants.set(i, ant);
            p.stage_progress = {}; f.kind = FactKind::StageChanged; f.stage = ant.stage;
            f.transferred = {};
            if (ant.stage==LifeStage::Adult) {
                if (reserve && founding_boundary_enabled(s.founding->profile,ant.stage))
                    tx.set_founding_uptake(e.actor,{s.m.now,s.m.now});
                schedule_autonomy(tx,e.actor,local_founding_provisioning(s,e.actor)?SimTime{1}:SimTime{});
            }
        } else if (!reserve && s.m.now == p.next_absorption) f.transferred = absorb(p, ant.stage);
        tx.physiology.set(e.actor, p); schedule_physiology(tx, e.actor);
        if (emitted_pulse && !advance_stage) {
            if (queen && s.founding->profile.dietary && s.founding->profile.dietary->local_nest_intake) {
                const auto j=s.colonies.index.at(ant.colony);
                auto& colony=s.colonies.rows[j];
                if (within_contact(ant.position,colony.nest_position,s.config) && spatially_clear(ant.position,colony.nest_position)) {
                    const auto meal=foundress_nest_meal(s.founding->profile,p,*reserve,colony.nest_food);
                    if (meal.total_ug()) {
                        tx.touch_colony(j);
                        colony.nest_food=subtract(colony.nest_food,meal);
                        s.m.ledger.stored=subtract(s.m.ledger.stored,meal);
                        p=s.physiology.at(e.actor);
                        p.crop=sum(p.crop,meal);
                        tx.physiology.set(e.actor,p);
                        f.kind=FactKind::FoundressNestMeal;
                        f.transferred=meal;
                        tx.fact(f);
                    }
                }
            }
            return;
        }
    }
    tx.fact(f);
    if (f.kind == FactKind::StageChanged && f.stage == LifeStage::Larva && reserve &&
        s.founding->profile.early_access && s.founding->profile.early_access->local_hatch_cue)
        notify_local_hatch(tx, ant, e.id);
}
void WorldRuntime::set_behavior(AntRef ref, IndividualBehavior behavior) {
    if (state_->care.contains(ref.id) && state_->care.at(ref.id).enabled) throw std::invalid_argument("pause care before changing worker program");
    Transaction tx(*state_,limits_);
    change_behavior(tx,ref,behavior);
    if (state_->autonomy.contains(ref.id) && state_->autonomy.at(ref.id).enabled) change_autonomy(tx,ref,false);
    tx.commit();
}
void WorldRuntime::change_behavior(Transaction& tx, AntRef ref, IndividualBehavior behavior, ScheduledId source, bool care_motor) {
    auto& s = *state_; const auto ant = query_ant(ref);
    if (!ant || !ant->alive() || !s.physiology.contains(ref.id) || behavior > IndividualBehavior::Excavate ||
        (behavior != IndividualBehavior::Paused && (ant->stage != LifeStage::Adult || ant->caste != Caste::Worker)))
        throw std::invalid_argument("invalid individual behavior activation");
    if (behavior==IndividualBehavior::Forage && !s.surface) throw std::invalid_argument("foraging requires a surface");
    if (behavior == IndividualBehavior::Excavate && !s.geometry) throw std::invalid_argument("excavation requires geometry");
    // External pending actions must be explicitly resolved/cancelled, never silently commandeered.
    if (!source.value && s.long_term && s.external_resolution(ref.id))
        throw std::invalid_argument("individual has an external pending action");
    if (!source.value && !s.long_term && s.m.resolution_commands) for (const auto& [key, e] : s.queue) {
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
        const bool first=!f.path_size;
        prepare_forager(tx,*ant,f);
        if (first) tx.fact(forager_started(*ant,f.path[0],mixed_navigation(s)));
        f.enabled = true; ScheduledEvent e; e.actor = ref.id; e.kind = ScheduledEvent::Kind::Wake; e.issued_at = s.m.now;
        e.key = {after(s.m.now, s.surface->behavior.decision_delay.milliseconds), Phase::Perception, 0, 0, 0};
        f.wake = tx.insert(e); tx.foragers.set(ref.id, f);
    } else if (behavior == IndividualBehavior::Excavate) {
        activate_excavator(tx,ref.id);
    } else if (behavior != IndividualBehavior::Paused && !care_motor) {
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
    if (s.care.contains(proposal.actor.id) && s.care.at(proposal.actor.id).enabled) throw std::invalid_argument("pause care before external nutrition action");
    if (!ant || !s.physiology.contains(ant->id) || (s.autonomy.contains(ant->id) && s.autonomy.at(ant->id).enabled) || proposal.kind > NutritionAction::ReturnProtein || !proposal.requested_ug ||
        s.physiology.at(ant->id).behavior != IndividualBehavior::Paused ||
        (s.foragers.contains(ant->id) && s.foragers.at(ant->id).enabled)) throw std::invalid_argument("invalid nutrition proposal");
    if (proposal.kind == NutritionAction::Trophallaxis && (!query_ant(proposal.recipient) ||
        !s.physiology.contains(proposal.recipient.id) || proposal.recipient.id == ant->id))
        throw std::invalid_argument("invalid world-qualified nutrition recipient");
    ScheduledEvent e; e.actor = ant->id; e.issued_at = s.m.now; e.requested_ug = proposal.requested_ug;
    e.kind = static_cast<ScheduledEvent::Kind>(static_cast<unsigned>(ScheduledEvent::Kind::IngestCargo)+static_cast<unsigned>(proposal.kind));
    if (proposal.kind == NutritionAction::ReturnProtein) {
        if (!s.long_term || !s.long_term->protein_recycling) throw std::invalid_argument("protein recycling disabled");
        e.kind = ScheduledEvent::Kind::ReturnProtein;
    }
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
        room = receiver->config.crop_capacity_ug-receiver->crop.total_ug();
        supply = local_founding_provisioning(s,ant.id) ? founding_gift_supply(s.founding->profile,p) : p.crop;
        if (s.social && !s.social->exchange_enabled) { f.outcome = Outcome::EmptyInventory; return; }
        if (s.social && s.social->demand_sensitive)
            supply = ingredient_min(supply,nutrient_demand(*receiver,recipient.stage));
    } else if (e.kind == ScheduledEvent::Kind::IngestCargo) supply = ant.carried_food;
    else {
        const auto& colony = s.colonies.rows[s.colonies.index.at(ant.colony)];
        if (!within_contact(ant.position,colony.nest_position,s.config) ||
            (s.surface && !s.config.continuous_spatial_motion && !(s.social && s.geometry) &&
             s.surface->locate(ant.position)!=s.surface->locate(colony.nest_position)) ||
            !spatially_clear(ant.position,colony.nest_position)) { f.outcome=Outcome::NotAtNest; return; }
        supply = colony.nest_food;
        if (e.kind == ScheduledEvent::Kind::ReturnProtein) {
            const auto amount = std::min(p.crop.protein_ug, e.requested_ug);
            if (!amount) { f.outcome = Outcome::EmptyInventory; return; }
            if (!s.long_term || !s.long_term->protein_recycling) throw std::logic_error("unexpected recycling action");
            f.transferred.protein_ug = amount; f.kind = FactKind::ProteinRecycled;
            f.outcome = amount == e.requested_ug ? Outcome::Success : Outcome::Partial;
            const auto j = s.colonies.index.at(ant.colony); tx.touch_colony(j);
            s.colonies.rows[j].nest_food = sum(colony.nest_food, f.transferred);
            s.m.ledger.stored = sum(s.m.ledger.stored, f.transferred);
            p.crop = subtract(p.crop, f.transferred); tx.physiology.set(e.actor, p); return;
        }
        if (s.long_term) {
            auto demand = nutrient_demand(p, ant.stage);
            if (p.behavior == IndividualBehavior::Nurse) {
                const auto sample = sample_contacts({s.world, ant.id}, p.decisions);
                inspect_decision(e, sample, 2, static_cast<std::uint64_t>(e.kind));
                if (sample.candidates_examined) {
                    auto& work=s.m.contact_work; bump(work.decisions); f.random_value=sample.candidates_examined;
                    work.candidates_examined=add(work.candidates_examined,sample.candidates_examined);
                    work.bucket_queries=add(work.bucket_queries,sample.bucket_queries); work.tree_visits=add(work.tree_visits,sample.tree_visits);
                    work.maximum_candidates=std::max(work.maximum_candidates,sample.candidates_examined);
                }
                for (const auto ref : sample.ants) if (const auto q = query_physiology(ref)) {
                    const auto need = signaled_need(*q, s.ants.get(s.ants.index.at(ref.id)).stage,true);
                    demand.carbs_ug = std::max(demand.carbs_ug, need.carbs_ug);
                    demand.protein_ug = std::max(demand.protein_ug, need.protein_ug);
                    demand.water_ug = std::max(demand.water_ug, need.water_ug);
                }
            }
            supply = ingredient_min(supply, demand);
        }
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
        const bool gift_priority = s.social && s.social->gift_first;
        const bool urgent_self = gift_priority &&
            ((p.body_energy_nj < p.config.energy_capacity_nj/4 && !p.crop.carbs_ug) ||
             (p.hydration_ug < p.config.hydration_capacity_ug/4 && !p.crop.water_ug));
        auto choose_gift = [&] {
            if (p.behavior != IndividualBehavior::Nurse || !p.crop.total_ug() ||
                (gift_priority && !s.social->exchange_enabled)) return;
            const auto supply = local_founding_provisioning(s,ant.id) ? founding_gift_supply(s.founding->profile,p) : p.crop;
            if (!supply.total_ug()) return;
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
                const bool hungry_larva = other.stage == LifeStage::Larva && supply.protein_ug &&
                    add(q.tissue_protein_ug, q.crop.protein_ug) < q.config.larval_protein_requirement_ug;
                const bool hungry_adult = other.stage == LifeStage::Adult &&
                    (q.body_energy_nj < q.config.energy_capacity_nj/4 || q.hydration_ug < q.config.hydration_capacity_ug/4);
                const bool demand=s.social && s.social->demand_sensitive;
                if (demand ? (!ingredient_min(supply,signaled_need(q,other.stage,s.long_term!=nullptr)).total_ug() || q.crop.total_ug()>=q.config.crop_capacity_ug) :
                    ((!hungry_larva && !hungry_adult) || q.crop.total_ug() >= q.config.crop_capacity_ug/2)) continue;
                ++seen; if (bounded_draw(rng, seen) == 0) { action.kind = ScheduledEvent::Kind::Trophallaxis; action.payload = id.value; }
            }
        };
        if (gift_priority && !urgent_self) choose_gift();
        if (action.kind == ScheduledEvent::Kind::Rest) {
            if (s.long_term && s.long_term->protein_recycling && p.behavior == IndividualBehavior::Rest &&
                p.crop.protein_ug && within_contact(ant.position,colony.nest_position,s.config) &&
                spatially_clear(ant.position,colony.nest_position)) action.kind = ScheduledEvent::Kind::ReturnProtein;
        }
        if (action.kind == ScheduledEvent::Kind::Rest) {
            if (p.crop.total_ug() < p.config.crop_capacity_ug/2 && ant.carried_food.total_ug()) action.kind = ScheduledEvent::Kind::IngestCargo;
            else if (p.crop.total_ug() < p.config.crop_capacity_ug/2 && colony.nest_food.total_ug() &&
                within_contact(ant.position,colony.nest_position,s.config) &&
                (!s.surface || s.config.continuous_spatial_motion || (s.social && s.geometry) ||
                 s.surface->locate(ant.position)==s.surface->locate(colony.nest_position)) &&
                spatially_clear(ant.position,colony.nest_position)) action.kind=ScheduledEvent::Kind::WithdrawNest;
            else if (!gift_priority) choose_gift();
        }
        if (action.kind != ScheduledEvent::Kind::Rest) action.requested_ug = p.config.transfer_limit_ug;
        inspect_decision(wake, encounters[actions.size()], 0, static_cast<std::uint64_t>(action.kind),
                         action.kind == ScheduledEvent::Kind::Trophallaxis ? EntityId{action.payload} : EntityId{});
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
        if (s.care_profile) {
            for (auto ref:encounters[i].ants) observe(tx,ant.id,wakes[i].id,{ObservationPhase::Opportunity,
                query_ant(ref)->stage==LifeStage::Larva?CareAct::FeedBrood:CareAct::TransferNutrition,ref.id,{},s.m.now,false});
            const auto kind=actions[i].kind;
            const auto target=kind==ScheduledEvent::Kind::Trophallaxis?EntityId{actions[i].payload}:EntityId{};
            const auto act=kind==ScheduledEvent::Kind::Rest?CareAct::Inactive:target.value?
                (query_ant({s.world,target})->stage==LifeStage::Larva?CareAct::FeedBrood:CareAct::TransferNutrition):CareAct::IngestFood;
            observe(tx,ant.id,wakes[i].id,{ObservationPhase::Selected,act,target,p.behavior_event,s.m.now,false});
        }
    }
}
void WorldRuntime::continue_nutrition_behavior(Transaction& tx, const ScheduledEvent& action, const WorldEvent& fact) {
    auto& s = *state_; if (!s.physiology.contains(action.actor)) return;
    auto p = s.physiology.at(action.actor); if (p.behavior_event != action.id) return;
    ScheduledEvent e; e.actor = action.actor; e.kind = ScheduledEvent::Kind::NutritionWake; e.issued_at = s.m.now;
    const bool ongoing_contact=s.long_term && s.long_term->post_intake_contact &&
        p.behavior==IndividualBehavior::Nurse && fact.kind==FactKind::NestIngested;
    e.key = {after(s.m.now, ongoing_contact ? 1 : p.config.behavior_interval.milliseconds), Phase::Perception, 0, 0, 0};
    p.behavior_event = tx.insert(e); tx.physiology.set(e.actor, p);
}
std::optional<PhysiologyState> WorldRuntime::query_physiology(AntRef ref) const {
    profiling::Scope profile(profiling::Category::Physiology);
    const auto& s = *state_; const auto ant = query_ant(ref);
    if (!ant || !s.physiology.contains(ref.id)) return {};
    auto p = s.physiology.at(ref.id);
    if (s.founding && s.founding_reserves.contains(ref.id)) {
        auto reserve = s.founding_reserves.at(ref.id);
        settle_founding(s.founding->profile, p, reserve, ant->stage, founding_foundress(ref.id), s.m.now);
    } else settle(p, ant->stage, s.m.now);
    return p;
}
NutritionSnapshot WorldRuntime::nutrition_snapshot() const {
    const auto& s = *state_; NutritionSnapshot n;
    n.introduced = s.m.ledger.introduced; n.accounted = sum(sum(s.m.ledger.available, s.m.ledger.carried), s.m.ledger.stored);
    n.accounted = sum(n.accounted, resource_reserves());
    for (const auto& [id, unused] : s.physiology) {
        (void)unused; const auto p = *query_physiology({s.world, id}); ++n.individuals;
        if (!p.mother.value) n.introduced = sum(n.introduced, sum(p.initial.crop, {0, p.initial.tissue_protein_ug, p.initial.hydration_ug, 0}));
        n.crop = sum(n.crop, p.crop); n.hydration_ug = add(n.hydration_ug, p.hydration_ug);
        n.tissue_protein_ug = add(n.tissue_protein_ug, p.tissue_protein_ug); n.oxidized_carbs_ug = add(n.oxidized_carbs_ug, p.oxidized_carbs_ug);
        n.lost_water_ug = add(n.lost_water_ug, p.lost_water_ug);
        n.energy_input_nj = add(n.energy_input_nj, add(p.mother.value || founding_foundress(id) ? 0 : p.initial.body_energy_nj,
                                                    multiply(p.oxidized_carbs_ug, p.config.carbohydrate_yield_nj_per_ug)));
        n.body_energy_nj = add(n.body_energy_nj, p.body_energy_nj); n.dissipated_energy_nj = add(n.dissipated_energy_nj, p.dissipated_energy_nj);
    }
    n.accounted = sum(n.accounted, sum(n.crop, {n.oxidized_carbs_ug, n.tissue_protein_ug, add(n.hydration_ug, n.lost_water_ug), 0}));
    if (s.founding) {
        const auto budget = founding_budget();
        n.introduced.protein_ug = add(n.introduced.protein_ug, budget.introduced_protein_ug);
        n.accounted.protein_ug = add(n.accounted.protein_ug, budget.owned_mobile_protein_ug);
        n.energy_input_nj = add(n.energy_input_nj, multiply(budget.spent_lipid_ug, s.founding->profile.lipid_yield_nj_per_ug));
    }
    return n;
}
void WorldRuntime::validate_nutrition_capacity() const {
    const auto& s = *state_; if (s.physiology.empty()) return;
    const auto introduced = sum(s.m.ledger.introduced, s.m.physiology_inputs); (void)introduced.total_ug();
    // Bound even complete future carbohydrate oxidation, so queries never discover
    // an overflow that a previous mutation should have rejected.
    auto energy = add(s.m.initial_energy, multiply(introduced.carbs_ug, s.m.maximum_yield));
    if (s.founding) (void)add(energy, multiply(s.founding->profile.lipid_ug, s.founding->profile.lipid_yield_nj_per_ug));
}
} // namespace antworld
