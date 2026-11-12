#pragma once
#include "long_term_internal.hpp"
#include "checkpoint_codec.hpp"
#include "physiology_internal.hpp"
#include "social_internal.hpp"
#include "checkpoint_founding_replay.hpp"

namespace antworld::detail {
inline constexpr std::array physiology_config_times{
    &PhysiologyConfig::absorption_period, &PhysiologyConfig::egg_duration, &PhysiologyConfig::larva_duration,
    &PhysiologyConfig::pupa_duration, &PhysiologyConfig::behavior_interval};
inline constexpr std::array physiology_config_values{
    &PhysiologyConfig::crop_capacity_ug, &PhysiologyConfig::hydration_capacity_ug, &PhysiologyConfig::energy_capacity_nj,
    &PhysiologyConfig::carbohydrate_yield_nj_per_ug, &PhysiologyConfig::basal_nj_per_ms, &PhysiologyConfig::active_nj_per_ms,
    &PhysiologyConfig::water_loss_ug_per_period, &PhysiologyConfig::carb_absorption_ug_per_s, &PhysiologyConfig::water_absorption_ug_per_s,
    &PhysiologyConfig::protein_absorption_ug_per_s, &PhysiologyConfig::larval_protein_requirement_ug, &PhysiologyConfig::transfer_limit_ug};
inline constexpr std::array physiology_values{
    &PhysiologyState::body_energy_nj, &PhysiologyState::hydration_ug, &PhysiologyState::tissue_protein_ug,
    &PhysiologyState::oxidized_carbs_ug, &PhysiologyState::lost_water_ug, &PhysiologyState::dissipated_energy_nj,
    &PhysiologyState::water_loss_remainder, &PhysiologyState::carb_remainder, &PhysiologyState::water_remainder,
    &PhysiologyState::protein_remainder, &PhysiologyState::decisions};
template <typename S> void write_physiology(Writer& w, const S& s) {
    w.put(s.physiology.size());
    for (const auto& [id, p] : s.physiology) {
        w.put(id.value);
        for (const auto member : physiology_config_times) w.time(p.config.*member);
        for (const auto member : physiology_config_values) w.put(p.config.*member);
        if (s.long_term) { w.time(p.config.water_loss_period); w.put(p.config.adult_protein_target_ug); w.put(p.mother.value); w.put(p.exported_energy_nj); }
        w.mass(p.initial.crop); w.put(p.initial.body_energy_nj); w.put(p.initial.hydration_ug); w.put(p.initial.tissue_protein_ug);
        w.mass(p.crop); for (const auto member : physiology_values) w.put(p.*member);
        w.time(p.updated_at); w.time(p.next_absorption); w.time(p.stage_progress);
        w.put(p.physiology_event.value); w.put(p.behavior_event.value);
        w.put(static_cast<std::uint8_t>(p.behavior), 1); w.put(static_cast<std::uint8_t>(p.death_cause), 1);
    }
}
template <typename S> void read_physiology(Reader& r, S& s, const RuntimeLimits& limits) {
    const auto count = r.count(limits.entities, 362);
    for (std::size_t i = 0; i < count; ++i) {
        const EntityId id{r.get()}; PhysiologyState p;
        for (const auto member : physiology_config_times) p.config.*member = r.time();
        for (const auto member : physiology_config_values) p.config.*member = r.get();
        if (s.long_term) { p.config.water_loss_period=r.time(); p.config.adult_protein_target_ug=r.get(); p.mother={r.get()}; p.exported_energy_nj=r.get(); }
        p.initial = {r.mass(), r.get(), r.get(), r.get()}; p.crop = r.mass();
        for (const auto member : physiology_values) p.*member = r.get();
        p.updated_at = r.time(); p.next_absorption = r.time(); p.stage_progress = r.time();
        p.physiology_event = {r.get()}; p.behavior_event = {r.get()};
        p.behavior = static_cast<IndividualBehavior>(r.get(1)); p.death_cause = static_cast<DeathCause>(r.get(1));
        validate_physiology(p.initial, p.config);
        ensure(s.long_term || (p.config.absorption_period.milliseconds<=60000 && p.config.behavior_interval.milliseconds<=60000),"legacy physiology interval exceeds its contract");
        ensure(s.ants.index.contains(id) && p.crop.total_ug() <= p.config.crop_capacity_ug &&
            p.body_energy_nj <= p.config.energy_capacity_nj && p.hydration_ug <= p.config.hydration_capacity_ug &&
            p.tissue_protein_ug <= p.config.larval_protein_requirement_ug &&
            p.water_loss_remainder < static_cast<std::uint64_t>(p.config.water_loss_period.milliseconds) && p.carb_remainder < 1000 && p.water_remainder < 1000 && p.protein_remainder < 1000 &&
            p.updated_at <= s.m.now && p.behavior <= IndividualBehavior::Excavate && p.death_cause <= DeathCause::Fixture &&
            s.physiology.emplace(id, p).second, "invalid physiology state");
    }
}
inline bool nutrition_fact(FactKind k) {
    return k == FactKind::CargoIngested || k == FactKind::NestIngested || k == FactKind::NutritionTransferred;
}
template <typename S> void validate_physiology_evidence(const S& s, const RuntimeLimits& limits) {
    FoundingReplay<S> founding(s, limits);
    std::map<EntityId, PhysiologyState> audit;
    std::map<EntityId, LifeStage> stages;
    std::map<EntityId, PositionM> positions;
    std::set<EntityId> active_foragers;
    FoodMass introduced = s.m.ledger.introduced;
    std::uint64_t initial_energy = 0, max_yield = 0;
    FoodMass accounted = sum(sum(s.m.ledger.available, s.m.ledger.carried), s.m.ledger.stored);
    for (const auto& [id,r]:s.resource_cycles) { (void)id; accounted=sum(accounted,r.remaining); }
    for (const auto& e : s.journal) {
        const bool expected_founding_fact = founding.before(e);
        if (e.kind == FactKind::AntSeeded || e.kind==FactKind::AntBorn) { stages[e.actor] = e.stage; positions[e.actor] = e.position; }
        if (e.kind == FactKind::Moved || e.kind==FactKind::BroodMoved) positions[e.actor] = e.position;
        if (e.kind == FactKind::ForagingStarted) active_foragers.insert(e.actor);
        if (e.kind == FactKind::PhysiologyEnabled || e.kind==FactKind::AntBorn) {
            ensure(s.physiology.contains(e.actor) && !audit.contains(e.actor), "missing/duplicate physiology initialization");
            const auto& saved = s.physiology.at(e.actor); PhysiologyState p; p.config = saved.config; p.initial = saved.initial;
            p.crop = p.initial.crop; p.body_energy_nj = p.initial.body_energy_nj; p.hydration_ug = p.initial.hydration_ug;
            p.tissue_protein_ug = p.initial.tissue_protein_ug; p.next_absorption = after(e.time,p.config.absorption_period.milliseconds);
            p.updated_at=e.time; p.mother=saved.mother;
            if (active_foragers.contains(e.actor)) p.behavior = IndividualBehavior::Forage;
            if (founding.enrolled(e.actor)) {
                auto* mother = e.kind == FactKind::AntBorn ? &audit.at(EntityId{e.payload}) : nullptr;
                if (mother) {
                    const EntityId parent{e.payload};
                    ensure(stages.at(parent)==LifeStage::Adult && e.position==positions.at(parent), "F1 birth lacks living maternal placement");
                    founding.settle(parent,*mother,LifeStage::Adult,e.time);
                }
                founding.initialize(p, e, mother);
            } else if (e.kind==FactKind::AntBorn) {
                const EntityId parent{e.payload}; ensure(s.long_term && p.mother==parent && audit.contains(parent) && s.reproduction.contains(parent),"missing birth parent");
                auto& mother=audit.at(parent); const auto& c=s.reproduction.at(parent).config;
                settle(mother,stages.at(parent),e.time);
                ensure(stages.at(parent)==LifeStage::Adult && e.position==positions.at(parent) &&
                    p.initial==PhysiologySeed{{},c.egg_energy_nj,c.egg_water_ug,c.egg_protein_ug} &&
                    e.transferred==FoodMass{0,c.egg_protein_ug,c.egg_water_ug,0} && e.random_value==c.egg_energy_nj &&
                    mother.crop.protein_ug>=c.egg_protein_ug && mother.hydration_ug>c.egg_water_ug &&
                    mother.body_energy_nj>add(c.egg_energy_nj,c.dissipated_energy_nj),"unfunded birth evidence");
                auto expected_config=mother.config; expected_config.adult_protein_target_ug=0;
                ensure(p.config==expected_config,"offspring configuration lacks inheritance evidence");
                mother.crop.protein_ug-=c.egg_protein_ug; mother.hydration_ug-=c.egg_water_ug;
                mother.body_energy_nj-=add(c.egg_energy_nj,c.dissipated_energy_nj);
                mother.exported_energy_nj=add(mother.exported_energy_nj,c.egg_energy_nj);
                mother.dissipated_energy_nj=add(mother.dissipated_energy_nj,c.dissipated_energy_nj);
            } else ensure(e.time == SimTime{} && e.transferred == p.crop && !p.mother.value, "invalid physiology seed evidence");
            audit.emplace(e.actor, p);
        } else if (audit.contains(e.actor)) {
            auto& p = audit.at(e.actor); const auto prior_stage = stages.at(e.actor);
            const bool enrolled = founding.enrolled(e.actor);
            if (enrolled && !expected_founding_fact && (e.kind == FactKind::PhysiologyUpdated || e.kind == FactKind::StageChanged ||
                (e.kind == FactKind::AntDied && e.payload)))
                ensure(e.time == founding.next(e.actor, p, prior_stage), "F1 fact is outside its physiological boundary");
            if (e.kind == FactKind::PhysiologyUpdated || e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied ||
                e.kind == FactKind::BehaviorChanged || e.kind == FactKind::ReproductionAttempt || e.kind==FactKind::ProteinRecycled || e.kind == FactKind::SoilExcavated || nutrition_fact(e.kind) || e.kind == FactKind::FoundingRation || (e.kind == FactKind::ActionRejected && e.payload))
                founding.settle(e.actor, p, prior_stage, e.time);
            if (e.kind == FactKind::PhysiologyUpdated) {
                if (enrolled) founding.pulse(p, e, prior_stage);
                else ensure(p.body_energy_nj && p.hydration_ug && e.time == p.next_absorption && e.transferred == absorb(p, prior_stage),
                    "invalid absorption evidence");
            } else if (e.kind==FactKind::ReproductionAttempt) {
                ensure(s.reproduction.contains(e.actor),"attempt lacks reproduction configuration");
                const auto& c=s.reproduction.at(e.actor).config;
                const bool funded=founding.founder(e.actor) ? founding.funded(p, e) : reproductive_resources(c,p);
                ensure(funded==(e.payload!=0),"reproduction outcome differs from physiological funding");
            } else if (e.kind == FactKind::StageChanged) {
                const bool ready = enrolled ? founding_develops(founding.profile(), p, founding.reserves.at(e.actor), prior_stage) :
                    developing(p, prior_stage) && p.stage_progress == stage_duration(p.config, prior_stage);
                ensure(p.body_energy_nj && p.hydration_ug && ready &&
                    (!enrolled || e.time != p.next_absorption), "unearned development evidence"); p.stage_progress = {};
            } else if (e.kind == FactKind::AntDied) {
                p.death_cause = e.payload ? static_cast<DeathCause>(e.payload) : DeathCause::Fixture;
                ensure((p.death_cause == DeathCause::Fixture && e.payload == 0) ||
                    (p.death_cause == DeathCause::EnergyDepleted && !p.body_energy_nj) ||
                    (p.death_cause == DeathCause::Dehydrated && p.body_energy_nj && !p.hydration_ug), "invalid physiological death evidence");
                p.behavior = IndividualBehavior::Paused;
            } else if (e.kind == FactKind::BehaviorChanged) {
                ensure(e.payload <= static_cast<std::uint64_t>(IndividualBehavior::Excavate) && prior_stage != LifeStage::Dead,
                    "invalid behavior switch evidence"); p.behavior = static_cast<IndividualBehavior>(e.payload);
            } else if (e.kind == FactKind::SoilExcavated) {
                ensure(s.geometry && s.soil_requests.contains(e.source), "dig energy without geometry provenance");
                const auto cost=multiply(s.soil_requests.at(e.source).actual_q3,s.geometry->config.dig_energy_nj_per_q3);
                ensure(cost<p.body_energy_nj,"unfunded excavation energy");
                p.body_energy_nj-=cost; p.dissipated_energy_nj=add(p.dissipated_energy_nj,cost);
            } else if (e.kind == FactKind::NutritionDecision) {
                ensure(prior_stage == LifeStage::Adult && (p.behavior == IndividualBehavior::Nurse || p.behavior == IndividualBehavior::Rest),
                    "invalid local nutrition decision"); bump(p.decisions); ensure(e.payload == p.decisions, "nutrition decision counter mismatch");
            } else if (e.kind == FactKind::NutritionTransferred) {
                const EntityId target{e.payload}; ensure(audit.contains(target) && target != e.actor, "missing transfer recipient");
                auto& recipient = audit.at(target); const auto target_stage = stages.at(target);
                founding.settle(target, recipient, target_stage, e.time);
                auto a = s.ants.get(s.ants.index.at(e.actor)), b = s.ants.get(s.ants.index.at(target));
                a.position = positions.at(e.actor); b.position = positions.at(target);
                ensure(prior_stage == LifeStage::Adult && (a.caste == Caste::Worker || (s.care_profile && a.caste==Caste::Queen && s.care.contains(e.actor))) &&
                    (target_stage == LifeStage::Adult || target_stage == LifeStage::Larva) && contact(a, b, s.config, s.social && s.geometry ? nullptr : s.surface.get()),
                    "transfer has no living local contact evidence");
                if (s.social) {
                    ensure(s.social->exchange_enabled,"transfer in a no-response control");
                    if (s.social->demand_sensitive)
                        ensure(ingredient_min(e.transferred,nutrient_demand(recipient,target_stage))==e.transferred,
                            "transfer exceeds contacted recipient demand");
                }
                p.crop = subtract(p.crop, e.transferred); recipient.crop = sum(recipient.crop, e.transferred);
                ensure(recipient.crop.total_ug() <= recipient.config.crop_capacity_ug, "recipient overflow in history");
            } else if (e.kind == FactKind::FoundingRation) {
                const EntityId target{e.payload};
                auto& recipient = audit.at(target);
                const auto stage = stages.at(target);
                founding.settle(target, recipient, stage, e.time);
                founding.ration(p, recipient, e, positions.at(target), stage);
            } else if (e.kind == FactKind::ProteinRecycled) {
                ensure(s.long_term && s.long_term->protein_recycling && prior_stage==LifeStage::Adult &&
                    s.ants.get(s.ants.index.at(e.actor)).caste==Caste::Worker &&
                    e.transferred.protein_ug && e.transferred.total_ug()==e.transferred.protein_ug,"invalid crop recycling evidence");
                p.crop=subtract(p.crop,e.transferred);
            } else if (e.kind == FactKind::CargoIngested || e.kind == FactKind::NestIngested) p.crop = sum(p.crop, e.transferred);
            if (e.kind == FactKind::ActionRejected && e.payload && audit.contains(EntityId{e.payload}))
                founding.settle({e.payload}, audit.at(EntityId{e.payload}), stages.at(EntityId{e.payload}), e.time);
            ensure(p.crop.total_ug() <= p.config.crop_capacity_ug, "crop capacity exceeded in history");
        } else ensure(e.kind < FactKind::PhysiologyEnabled || e.kind >= FactKind::GeometryConfigured, "physiology fact without initialization");
        if (e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied) stages[e.actor] = e.stage;
    }
    founding.finish();
    ensure(audit.size() == s.physiology.size(), "missing physiology evidence");
    for (const auto& [id, saved] : s.physiology) {
        const auto ant = s.ants.get(s.ants.index.at(id)); auto expected = audit.at(id); auto actual = saved;
        const bool enrolled = founding.enrolled(id);
        if (enrolled) {
            auto left = founding.reserves.at(id), right = s.founding_reserves.at(id);
            settle_founding(founding.profile(), expected, left, ant.stage, founding.founder(id), s.m.now);
            settle_founding(founding.profile(), actual, right, ant.stage, founding.founder(id), s.m.now);
            ensure(left == right, "F1 reserve row disagrees with history");
        } else {
            settle(expected, ant.stage, s.m.now); settle(actual, ant.stage, s.m.now);
        }
        expected.physiology_event = actual.physiology_event; expected.behavior_event = actual.behavior_event;
        ensure(expected == actual, "physiology row disagrees with committed history");
        ensure(ant.alive() == (saved.death_cause == DeathCause::None), "life/death cause mismatch");
        if (ant.alive()) {
            ensure(saved.body_energy_nj && saved.hydration_ug && saved.next_absorption >= saved.updated_at &&
                s.queue_index.contains(saved.physiology_event), "missing living physiological schedule");
            const auto& e = s.queue.at(s.queue_index.at(saved.physiology_event));
            ensure(e.actor == id && e.kind == ScheduledEvent::Kind::Physiology &&
                e.key.time == founding.next(id, saved, ant.stage, enrolled ? &s.founding_reserves.at(id) : nullptr),
                "wrong physiology threshold schedule");
        } else ensure(!saved.physiology_event.value && !saved.behavior_event.value && saved.behavior == IndividualBehavior::Paused,
            "dead physiology still scheduled");
        const bool caring=s.care.contains(id) && s.care.at(id).enabled;
        const bool nursing = ant.alive() && (saved.behavior == IndividualBehavior::Nurse || saved.behavior == IndividualBehavior::Rest || caring);
        ensure(nursing == (saved.behavior_event.value != 0), "nutrition behavior schedule mismatch");
        if (nursing) {
            ensure(ant.stage == LifeStage::Adult && (ant.caste == Caste::Worker || caring) && s.queue_index.contains(saved.behavior_event), "missing behavior event");
            const auto& e = s.queue.at(s.queue_index.at(saved.behavior_event));
            ensure(e.actor == id && (e.kind == ScheduledEvent::Kind::NutritionWake || e.key.phase == Phase::Resolution || (caring && e.kind==ScheduledEvent::Kind::CareWake)), "foreign behavior ownership");
        }
        const auto f = s.foragers.find(id);
        ensure((saved.behavior == IndividualBehavior::Forage) == (f != s.foragers.end() && f->second.enabled), "foraging program mismatch");
        const auto excavator=s.excavators.find(id);
        ensure((saved.behavior==IndividualBehavior::Excavate)==(excavator!=s.excavators.end() && excavator->second.enabled),"excavation program mismatch");
        if (!saved.mother.value) {
            introduced = sum(introduced, sum(saved.initial.crop, {0, saved.initial.tissue_protein_ug, saved.initial.hydration_ug, 0}));
            if (founding.founder(id)) {
                introduced.protein_ug = add(introduced.protein_ug, founding.profile().protein_ug);
                accounted.protein_ug = add(accounted.protein_ug, s.founding_reserves.at(id).mobile_protein_ug);
                initial_energy = add(initial_energy, multiply(founding.profile().lipid_ug, founding.profile().lipid_yield_nj_per_ug));
            } else initial_energy = add(initial_energy, saved.initial.body_energy_nj);
        }
        max_yield = std::max(max_yield, saved.config.carbohydrate_yield_nj_per_ug);
        accounted = sum(accounted, sum(saved.crop, {saved.oxidized_carbs_ug, saved.tissue_protein_ug, add(saved.hydration_ug, saved.lost_water_ug), 0}));
        const auto seed_energy = enrolled ? multiply(s.founding_reserves.at(id).spent_lipid_ug, founding.profile().lipid_yield_nj_per_ug) :
            saved.initial.body_energy_nj;
        ensure(add(seed_energy, multiply(saved.oxidized_carbs_ug, saved.config.carbohydrate_yield_nj_per_ug)) ==
            add(add(saved.body_energy_nj, saved.dissipated_energy_nj),saved.exported_energy_nj), "energy ledger mismatch");
    }
    for (const auto& [id, f] : s.foragers) if (!s.physiology.contains(id))
        ensure(f.enabled == s.ants.get(s.ants.index.at(id)).alive(), "legacy forager activity mismatch");
    ensure(introduced == accounted, "nutrition ingredient ledger mismatch");
    (void)introduced.total_ug(); (void)add(initial_energy, multiply(introduced.carbs_ug, max_yield));
}
} // namespace antworld::detail
