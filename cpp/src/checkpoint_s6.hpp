#pragma once
#include "checkpoint_codec.hpp"
#include "social_internal.hpp"

namespace antworld::detail {
template<class S> void write_social(Writer& w, const S& s) {
    w.put(s.social != nullptr,1);
    if (s.social) {
        const auto& c = *s.social;
        w.put(c.demand_sensitive,1); w.put(c.bounded_contacts,1); w.put(c.exchange_enabled,1);
        w.put(c.encounter_budget,4); w.time(c.decision_interval); w.time(c.minimum_program_time);
        w.put(c.rest_weight,4); w.put(c.forage_weight,4); w.put(c.nurse_weight,4); w.put(c.excavate_weight,4);
        const auto& a=s.m.contact_work;
        w.put(a.decisions); w.put(a.candidates_examined); w.put(a.bucket_queries); w.put(a.tree_visits); w.put(a.maximum_candidates);
        w.put(s.autonomy.size());
        for (const auto& [id,p]:s.autonomy) {
            w.put(id.value); w.put(p.enabled,1); w.put(p.decisions); w.time(p.enrolled_at); w.time(p.last_program_change); w.put(p.wake.value);
        }
    }
}
template<class S> void read_social(Reader& r, S& s) {
    if (r.flag()) {
        auto c = std::make_shared<SocialConfig>();
        c->demand_sensitive=r.flag(); c->bounded_contacts=r.flag(); c->exchange_enabled=r.flag();
        c->encounter_budget=static_cast<std::uint32_t>(r.get(4));
        c->decision_interval=r.time(); c->minimum_program_time=r.time();
        c->rest_weight=static_cast<std::uint32_t>(r.get(4)); c->forage_weight=static_cast<std::uint32_t>(r.get(4));
        c->nurse_weight=static_cast<std::uint32_t>(r.get(4)); c->excavate_weight=static_cast<std::uint32_t>(r.get(4));
        validate_social(*c); s.social=std::move(c);
        s.m.contact_work={r.get(),r.get(),r.get(),r.get(),r.get()};
        const auto count=r.count(s.ants.size(),41);
        for (std::size_t i=0;i<count;++i) {
            const EntityId id{r.get()}; AutonomyState a{r.flag(),r.get(),r.time(),r.time(),{r.get()}};
            ensure(s.ants.index.contains(id) && s.physiology.contains(id) && s.ants.get(s.ants.index.at(id)).caste==Caste::Worker &&
                a.enrolled_at<=s.m.now && a.last_program_change>=a.enrolled_at && a.last_program_change<=s.m.now &&
                s.autonomy.emplace(id,a).second,"invalid autonomy identity/state");
        }
    }
    std::uint64_t configured=0;
    for (const auto& e:s.journal) if (e.kind==FactKind::SocialConfigured) {
        ensure(s.social && e.time==SimTime{} && !e.actor.value && !e.colony.value && !e.source.value &&
            e.payload==social_fingerprint(*s.social) && !e.random_value && e.position==PositionM{},"invalid social configuration evidence");
        ++configured;
    }
    ensure(configured==(s.social?1U:0U),"missing/duplicate social policy evidence");
    ContactWork audit; std::uint64_t sampled=0;
    for (const auto& e:s.journal) if (e.kind==FactKind::NutritionDecision || e.kind==FactKind::AutonomyDecision) {
        if (s.social) {
            bump(audit.decisions); audit.candidates_examined=add(audit.candidates_examined,e.random_value);
            audit.maximum_candidates=std::max(audit.maximum_candidates,e.random_value);
            if (e.random_value) ++sampled;
        } else ensure(!e.random_value,"unexpected legacy encounter count");
    }
    const auto& actual=s.m.contact_work;
    ensure(audit.decisions==actual.decisions && audit.candidates_examined==actual.candidates_examined &&
        audit.maximum_candidates==actual.maximum_candidates,"contact work disagrees with decisions");
    if (s.social && s.social->bounded_contacts)
        ensure(actual.maximum_candidates<=s.social->encounter_budget && actual.bucket_queries==multiply(sampled,27) &&
            actual.tree_visits>=actual.candidates_examined && actual.tree_visits<=multiply(actual.candidates_examined,s.ants.size()),
            "contact budget exceeded");
    rebuild_contacts(s);
}
template<class S> void validate_autonomy_evidence(const S& s) {
    typename S::Autonomy audit; std::map<EntityId,LifeStage> stages; std::map<EntityId,PositionM> positions;
    std::map<ScheduledId,WorldEvent> switches;
    for (const auto& e:s.journal) {
        if (e.kind==FactKind::AntSeeded) { stages[e.actor]=e.stage; positions[e.actor]=e.position; }
        if (e.kind==FactKind::Moved) positions[e.actor]=e.position;
        if (e.kind==FactKind::StageChanged || e.kind==FactKind::AntDied) stages[e.actor]=e.stage;
        if (e.kind==FactKind::AutonomyChanged) {
            ensure(s.social && s.autonomy.contains(e.actor) && e.payload<=1 && !e.source.value && !e.random_value &&
                stages.at(e.actor)!=LifeStage::Dead && e.stage==stages.at(e.actor) && e.position==positions.at(e.actor),"invalid autonomy control evidence");
            auto [it,inserted]=audit.try_emplace(e.actor,AutonomyState{false,0,e.time,e.time,{}}); (void)inserted;
            it->second.enabled=e.payload!=0;
        }
        if (e.kind==FactKind::BehaviorChanged) {
            if (audit.contains(e.actor)) audit.at(e.actor).last_program_change=e.time;
            if (e.source.value) ensure(audit.contains(e.actor) && audit.at(e.actor).enabled && switches.emplace(e.source,e).second,
                "automatic program change without unique active decision");
        }
        if (e.kind==FactKind::AutonomyDecision) {
            ensure(s.social && audit.contains(e.actor) && audit.at(e.actor).enabled && stages.at(e.actor)==LifeStage::Adult &&
                e.stage==LifeStage::Adult && e.position==positions.at(e.actor) && e.source.value,"invalid automatic decision evidence");
            auto& a=audit.at(e.actor); bump(a.decisions); ensure(a.decisions==e.payload,"automatic decision counter mismatch");
            if (switches.contains(e.source)) {
                const auto changed=switches.at(e.source);
                ensure(changed.actor==e.actor && changed.time==e.time && changed.position==e.position,
                    "program change has foreign decision source"); switches.erase(e.source);
            }
        }
        if (e.kind==FactKind::AntDied && audit.contains(e.actor)) audit.at(e.actor).enabled=false;
    }
    ensure(switches.empty() && audit.size()==s.autonomy.size(),"missing automatic decision/enrollment evidence");
    for (const auto& [id,a]:s.autonomy) {
        auto expected=audit.at(id); expected.wake=a.wake;
        ensure(expected==a,"autonomy state disagrees with history");
        const auto ant=s.ants.get(s.ants.index.at(id)); const bool scheduled=a.enabled && ant.stage==LifeStage::Adult;
        ensure(scheduled==(a.wake.value!=0) && (ant.alive() || !a.enabled),"autonomy lifecycle ownership mismatch");
        if (scheduled) {
            ensure(s.queue_index.contains(a.wake),"missing automatic wake");
            const auto& e=s.queue.at(s.queue_index.at(a.wake));
            ensure(e.actor==id && e.kind==ScheduledEvent::Kind::AutonomyWake && e.key.phase==Phase::Reschedule &&
                e.key.time==after(e.issued_at,s.social->decision_interval.milliseconds),"wrong automatic wake schedule");
        }
    }
}
} // namespace antworld::detail
