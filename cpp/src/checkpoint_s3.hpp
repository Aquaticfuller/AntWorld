#pragma once
#include "checkpoint_codec.hpp"
#include "physiology_internal.hpp"

namespace antworld::detail {
inline constexpr std::array physiology_config_times{
    &PhysiologyConfig::absorption_period, &PhysiologyConfig::egg_duration, &PhysiologyConfig::larva_duration,
    &PhysiologyConfig::pupa_duration, &PhysiologyConfig::behavior_interval};
inline constexpr std::array physiology_config_values{
    &PhysiologyConfig::crop_capacity_ug, &PhysiologyConfig::hydration_capacity_ug, &PhysiologyConfig::energy_capacity_nj,
    &PhysiologyConfig::carbohydrate_yield_nj_per_ug, &PhysiologyConfig::basal_nj_per_ms, &PhysiologyConfig::active_nj_per_ms,
    &PhysiologyConfig::water_loss_ug_per_s, &PhysiologyConfig::carb_absorption_ug_per_s, &PhysiologyConfig::water_absorption_ug_per_s,
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
        p.initial = {r.mass(), r.get(), r.get(), r.get()}; p.crop = r.mass();
        for (const auto member : physiology_values) p.*member = r.get();
        p.updated_at = r.time(); p.next_absorption = r.time(); p.stage_progress = r.time();
        p.physiology_event = {r.get()}; p.behavior_event = {r.get()};
        p.behavior = static_cast<IndividualBehavior>(r.get(1)); p.death_cause = static_cast<DeathCause>(r.get(1));
        validate_physiology(p.initial, p.config);
        ensure(s.ants.index.contains(id) && p.crop.total_ug() <= p.config.crop_capacity_ug &&
            p.body_energy_nj <= p.config.energy_capacity_nj && p.hydration_ug <= p.config.hydration_capacity_ug &&
            p.tissue_protein_ug <= p.config.larval_protein_requirement_ug &&
            p.water_loss_remainder < 1000 && p.carb_remainder < 1000 && p.water_remainder < 1000 && p.protein_remainder < 1000 &&
            p.updated_at <= s.m.now && p.behavior <= IndividualBehavior::Forage && p.death_cause <= DeathCause::Fixture &&
            s.physiology.emplace(id, p).second, "invalid physiology state");
    }
}
inline bool nutrition_fact(FactKind k) {
    return k == FactKind::CargoIngested || k == FactKind::NestIngested || k == FactKind::NutritionTransferred;
}
template <typename S> void validate_physiology_evidence(const S& s) {
    std::map<EntityId, PhysiologyState> audit;
    std::map<EntityId, LifeStage> stages;
    std::map<EntityId, PositionM> positions;
    std::set<EntityId> active_foragers;
    FoodMass introduced = s.m.ledger.introduced;
    std::uint64_t initial_energy = 0, max_yield = 0;
    FoodMass accounted = sum(sum(s.m.ledger.available, s.m.ledger.carried), s.m.ledger.stored);
    for (const auto& e : s.journal) {
        if (e.kind == FactKind::AntSeeded) { stages[e.actor] = e.stage; positions[e.actor] = e.position; }
        if (e.kind == FactKind::Moved) positions[e.actor] = e.position;
        if (e.kind == FactKind::ForagingStarted) active_foragers.insert(e.actor);
        if (e.kind == FactKind::PhysiologyEnabled) {
            ensure(s.physiology.contains(e.actor) && !audit.contains(e.actor), "missing/duplicate physiology initialization");
            const auto& saved = s.physiology.at(e.actor); PhysiologyState p; p.config = saved.config; p.initial = saved.initial;
            p.crop = p.initial.crop; p.body_energy_nj = p.initial.body_energy_nj; p.hydration_ug = p.initial.hydration_ug;
            p.tissue_protein_ug = p.initial.tissue_protein_ug; p.next_absorption = p.config.absorption_period;
            if (active_foragers.contains(e.actor)) p.behavior = IndividualBehavior::Forage;
            ensure(e.time == SimTime{} && e.transferred == p.crop, "invalid physiology seed evidence"); audit.emplace(e.actor, p);
        } else if (audit.contains(e.actor)) {
            auto& p = audit.at(e.actor); const auto prior_stage = stages.at(e.actor);
            if (e.kind == FactKind::PhysiologyUpdated || e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied ||
                e.kind == FactKind::BehaviorChanged || nutrition_fact(e.kind) || (e.kind == FactKind::ActionRejected && e.payload))
                settle(p, prior_stage, e.time);
            if (e.kind == FactKind::PhysiologyUpdated) {
                ensure(p.body_energy_nj && p.hydration_ug && e.time == p.next_absorption && e.transferred == absorb(p, prior_stage),
                    "invalid absorption evidence");
            } else if (e.kind == FactKind::StageChanged) {
                ensure(p.body_energy_nj && p.hydration_ug && developing(p, prior_stage) &&
                    p.stage_progress == stage_duration(p.config, prior_stage), "unearned development evidence"); p.stage_progress = {};
            } else if (e.kind == FactKind::AntDied) {
                p.death_cause = e.payload ? static_cast<DeathCause>(e.payload) : DeathCause::Fixture;
                ensure((p.death_cause == DeathCause::Fixture && e.payload == 0) ||
                    (p.death_cause == DeathCause::EnergyDepleted && !p.body_energy_nj) ||
                    (p.death_cause == DeathCause::Dehydrated && p.body_energy_nj && !p.hydration_ug), "invalid physiological death evidence");
                p.behavior = IndividualBehavior::Paused;
            } else if (e.kind == FactKind::BehaviorChanged) {
                ensure(e.payload <= static_cast<std::uint64_t>(IndividualBehavior::Forage) && prior_stage != LifeStage::Dead,
                    "invalid behavior switch evidence"); p.behavior = static_cast<IndividualBehavior>(e.payload);
            } else if (e.kind == FactKind::NutritionDecision) {
                ensure(prior_stage == LifeStage::Adult && (p.behavior == IndividualBehavior::Nurse || p.behavior == IndividualBehavior::Rest),
                    "invalid local nutrition decision"); bump(p.decisions); ensure(e.payload == p.decisions, "nutrition decision counter mismatch");
            } else if (e.kind == FactKind::NutritionTransferred) {
                const EntityId target{e.payload}; ensure(audit.contains(target) && target != e.actor, "missing transfer recipient");
                auto& recipient = audit.at(target); const auto target_stage = stages.at(target); settle(recipient, target_stage, e.time);
                auto a = s.ants.get(s.ants.index.at(e.actor)), b = s.ants.get(s.ants.index.at(target));
                a.position = positions.at(e.actor); b.position = positions.at(target);
                ensure(prior_stage == LifeStage::Adult && a.caste == Caste::Worker &&
                    (target_stage == LifeStage::Adult || target_stage == LifeStage::Larva) && contact(a, b, s.config, s.surface.get()),
                    "transfer has no living local contact evidence");
                p.crop = subtract(p.crop, e.transferred); recipient.crop = sum(recipient.crop, e.transferred);
                ensure(recipient.crop.total_ug() <= recipient.config.crop_capacity_ug, "recipient overflow in history");
            } else if (e.kind == FactKind::CargoIngested || e.kind == FactKind::NestIngested) p.crop = sum(p.crop, e.transferred);
            if (e.kind == FactKind::ActionRejected && e.payload && audit.contains(EntityId{e.payload}))
                settle(audit.at(EntityId{e.payload}), stages.at(EntityId{e.payload}), e.time);
            ensure(p.crop.total_ug() <= p.config.crop_capacity_ug, "crop capacity exceeded in history");
        } else ensure(e.kind < FactKind::PhysiologyEnabled, "physiology fact without initialization");
        if (e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied) stages[e.actor] = e.stage;
    }
    ensure(audit.size() == s.physiology.size(), "missing physiology evidence");
    for (const auto& [id, saved] : s.physiology) {
        const auto ant = s.ants.get(s.ants.index.at(id)); auto expected = audit.at(id); auto actual = saved;
        settle(expected, ant.stage, s.m.now); settle(actual, ant.stage, s.m.now);
        expected.physiology_event = actual.physiology_event; expected.behavior_event = actual.behavior_event;
        ensure(expected == actual, "physiology row disagrees with committed history");
        ensure(ant.alive() == (saved.death_cause == DeathCause::None), "life/death cause mismatch");
        if (ant.alive()) {
            ensure(saved.body_energy_nj && saved.hydration_ug && saved.next_absorption >= saved.updated_at &&
                s.queue_index.contains(saved.physiology_event), "missing living physiological schedule");
            const auto& e = s.queue.at(s.queue_index.at(saved.physiology_event));
            ensure(e.actor == id && e.kind == ScheduledEvent::Kind::Physiology && e.key.time == next_physiology(saved, ant.stage),
                "wrong physiology threshold schedule");
        } else ensure(!saved.physiology_event.value && !saved.behavior_event.value && saved.behavior == IndividualBehavior::Paused,
            "dead physiology still scheduled");
        const bool nursing = ant.alive() && (saved.behavior == IndividualBehavior::Nurse || saved.behavior == IndividualBehavior::Rest);
        ensure(nursing == (saved.behavior_event.value != 0), "nutrition behavior schedule mismatch");
        if (nursing) {
            ensure(ant.stage == LifeStage::Adult && ant.caste == Caste::Worker && s.queue_index.contains(saved.behavior_event), "missing behavior event");
            const auto& e = s.queue.at(s.queue_index.at(saved.behavior_event));
            ensure(e.actor == id && (e.kind == ScheduledEvent::Kind::NutritionWake || e.key.phase == Phase::Resolution), "foreign behavior ownership");
        }
        const auto f = s.foragers.find(id);
        ensure((saved.behavior == IndividualBehavior::Forage) == (f != s.foragers.end() && f->second.enabled), "foraging program mismatch");
        introduced = sum(introduced, sum(saved.initial.crop, {0, saved.initial.tissue_protein_ug, saved.initial.hydration_ug, 0}));
        initial_energy = add(initial_energy, saved.initial.body_energy_nj);
        max_yield = std::max(max_yield, saved.config.carbohydrate_yield_nj_per_ug);
        accounted = sum(accounted, sum(saved.crop, {saved.oxidized_carbs_ug, saved.tissue_protein_ug, add(saved.hydration_ug, saved.lost_water_ug), 0}));
        ensure(add(saved.initial.body_energy_nj, multiply(saved.oxidized_carbs_ug, saved.config.carbohydrate_yield_nj_per_ug)) ==
            add(saved.body_energy_nj, saved.dissipated_energy_nj), "energy ledger mismatch");
    }
    for (const auto& [id, f] : s.foragers) if (!s.physiology.contains(id))
        ensure(f.enabled == s.ants.get(s.ants.index.at(id)).alive(), "legacy forager activity mismatch");
    ensure(introduced == accounted, "nutrition ingredient ledger mismatch");
    (void)introduced.total_ug(); (void)add(initial_energy, multiply(introduced.carbs_ug, max_yield));
}
} // namespace antworld::detail
