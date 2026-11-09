#pragma once
#include "care_internal.hpp"
#include "checkpoint_codec.hpp"

namespace antworld::detail {
inline constexpr std::array care_times{&SpeciesCareProfile::decision_interval,&SpeciesCareProfile::bout_duration,
    &SpeciesCareProfile::worker_contact_duration,&SpeciesCareProfile::social_memory_horizon};
inline constexpr std::array care_reals{&SpeciesCareProfile::care_probability,&SpeciesCareProfile::worker_contact_probability,
    &SpeciesCareProfile::maximum_inhibition,&SpeciesCareProfile::perception_radius_m,&SpeciesCareProfile::step_m,&SpeciesCareProfile::arrangement_m};
template<class S> void write_care(Writer& w,const S& s) {
    if (!s.care_profile) return;
    for (auto m:care_times) w.time(s.care_profile.get()->*m);
    for (auto m:care_reals) w.real(s.care_profile.get()->*m);
    w.real(s.care_environment.temperature_c); w.real(s.care_environment.relative_humidity);
    w.put(s.care.size());
    for (const auto& [id,c]:s.care) {
        w.put(id.value); w.put(static_cast<std::uint8_t>(c.profile.context),1); w.time(c.profile.age_at_enrollment);
        w.position(c.familiar_shelter); w.put(c.enabled,1); w.put(c.active,1); w.put(c.has_worker_contact,1);
        w.time(c.enrolled_at); w.time(c.began_at); w.time(c.last_worker_contact); w.put(c.decisions);
        w.put(static_cast<std::uint8_t>(c.act),1); w.put(c.target.value); w.position(c.destination);
        w.put(c.pending.value); w.put(c.bout.value);
        if (s.care_profile->local_retrieval) {
            w.put(c.retrieval.target.value); w.put(c.retrieval.pickup_bout.value);
            if (c.retrieval.pickup_bout.value) w.position(c.retrieval.pickup_site);
        }
    }
}
template<class S> void read_care(Reader& r,S& s,const RuntimeLimits& limits,bool retrieval) {
    SpeciesCareProfile profile; for(auto m:care_times) profile.*m=r.time(); for(auto m:care_reals) profile.*m=r.real();
    profile.local_retrieval=retrieval;
    s.care_environment={r.real(),r.real()}; validate_care_profile(profile,s.care_environment,s.config);
    s.care_profile=std::make_shared<const SpeciesCareProfile>(profile);
    const auto count=r.count(limits.entities,retrieval?141:125);
    for(std::size_t i=0;i<count;++i) {
        const EntityId id{r.get()}; CareState c;
        c.profile.context=static_cast<CareContext>(r.get(1)); c.profile.age_at_enrollment=r.time(); c.familiar_shelter=r.position();
        c.enabled=r.flag(); c.active=r.flag(); c.has_worker_contact=r.flag(); c.enrolled_at=r.time(); c.began_at=r.time(); c.last_worker_contact=r.time();
        c.decisions=r.get(); c.act=static_cast<CareAct>(r.get(1)); c.target={r.get()}; c.destination=r.position(); c.pending={r.get()}; c.bout={r.get()};
        if (retrieval) {
            c.retrieval.target={r.get()}; c.retrieval.pickup_bout={r.get()};
            if (c.retrieval.pickup_bout.value) c.retrieval.pickup_site=r.position();
        }
        ensure(s.ants.index.contains(id) && s.physiology.contains(id) && c.profile.context<=CareContext::Worker &&
            (c.act<=CareAct::CloseWorkerContact || (retrieval && c.act==CareAct::RevisitBroodSite)) &&
            c.enrolled_at<=s.m.now && c.began_at<=s.m.now && c.last_worker_contact<=s.m.now &&
            inside(c.familiar_shelter,s.config) && finite(c.destination) && s.care.emplace(id,c).second,"invalid care state");
        const auto a=s.ants.get(s.ants.index.at(id));
        ensure(a.caste!=Caste::Male && (a.caste==Caste::Worker)==(c.profile.context==CareContext::Worker) &&
            (a.stage==LifeStage::Adult || (!a.alive() && !c.enabled)) &&
            c.familiar_shelter==s.colonies.rows[s.colonies.index.at(a.colony)].nest_position &&
            c.enabled==(c.pending.value!=0) && (!c.active || c.enabled) &&
            (c.has_worker_contact || c.last_worker_contact==SimTime{}) && (!c.target.value || (s.ants.index.contains(c.target) && c.target!=id)),"care role/shelter mismatch");
        if (retrieval) {
            const auto& memory=c.retrieval;
            ensure((c.enabled || memory==RetrievalMemory{}) &&
                (!memory.target.value || (memory.target!=id && s.ants.index.contains(memory.target) &&
                    s.ants.get(s.ants.index.at(memory.target)).colony==a.colony)) &&
                (!memory.pickup_bout.value || (memory.pickup_bout.value<s.m.next_scheduled && inside(memory.pickup_site,s.config))),
                "invalid retrieval memory");
            if (c.bout.value && c.act==CareAct::RevisitBroodSite)
                ensure(!c.target.value && !memory.target.value && memory.pickup_bout.value,"revisit without pickup memory");
            if (c.bout.value && memory.target.value)
                ensure(c.target==memory.target && (c.act==CareAct::ApproachBrood || c.act==CareAct::TransportBrood),"retrieval plan target mismatch");
        }
        if (c.enabled) {
            ensure(s.queue_index.contains(c.pending) && s.physiology.at(id).behavior_event==c.pending,"missing care schedule");
            const auto e=s.queue.at(s.queue_index.at(c.pending));
            ensure(e.actor==id && (c.active?e.kind==ScheduledEvent::Kind::CareEnd:
                (e.kind==ScheduledEvent::Kind::CareWake || e.kind==ScheduledEvent::Kind::CareBegin)),"wrong care ownership");
            if (c.active) {
                ensure(c.bout.value && c.bout.value<s.m.next_scheduled,"invalid care bout identity");
                const auto duration=c.act==CareAct::Inactive?profile.decision_interval:c.act==CareAct::CloseWorkerContact?profile.worker_contact_duration:profile.bout_duration;
                ensure(e.key.time==after(c.began_at,duration.milliseconds),"care bout duration differs from profile");
                if (handles_brood(c.act) || c.act==CareAct::CloseWorkerContact)
                    ensure(c.target.value && s.care_locks.emplace(c.target,id).second,"duplicate care reservation");
            }
        } else ensure(!c.active && !c.bout.value && !c.target.value,"disabled care retains work");
    }
}
template<class S> void validate_care_evidence(const S& s) {
    if (!s.care_profile) return;
    struct Audit {
        bool enabled{}, contact{}, focus_seen{}, pickup_started{}, pickup_completed{};
        SimTime last;
        std::uint64_t decisions{};
        std::optional<BehaviorObservation> selected,started;
    };
    std::map<EntityId,Audit> audit;
    std::size_t configured=0;
    std::map<ScheduledId,BehaviorObservation> starts;
    std::map<ScheduledId,EntityId> owners;
    for (const auto& e:s.journal) {
        if (e.kind==FactKind::BiologyConfigured) { ++configured; ensure(e.time==SimTime{},"late biology configuration"); }
        if (e.kind==FactKind::CareProgramChanged) {
            ensure(s.care.contains(e.actor) && e.payload<=1,"unknown care enrollment");
            auto& a=audit[e.actor]; a.enabled=e.payload!=0;
            if (!a.enabled) { a.selected.reset(); a.started.reset(); }
        }
        if (e.kind==FactKind::CareTick && e.payload==static_cast<std::uint64_t>(ScheduledEvent::Kind::CareWake)) {
            ensure(audit.contains(e.actor) && audit.at(e.actor).enabled,"care decision without enrollment"); ++audit.at(e.actor).decisions;
        }
        if (e.kind!=FactKind::BiologicalObservation) continue;
        const auto& o=e.observation;
        ensure(o.act<CareAct::Count && o.phase<=ObservationPhase::Interrupted && o.began_at<=e.time && finite(o.destination) &&
            (!o.target.value || (s.ants.index.contains(o.target) && o.target!=e.actor && s.ants.get(s.ants.index.at(o.target)).colony==e.colony)),"invalid observation fields");
        ensure(o.act!=CareAct::RevisitBroodSite || (s.care_profile->local_retrieval && !o.target.value),"revisit observation outside retrieval contract");
        if (o.phase==ObservationPhase::Selected && audit.contains(e.actor) && audit.at(e.actor).enabled) {
            auto& a=audit.at(e.actor);
            a.selected=o;
            if (s.care_profile->local_retrieval && o.target==s.care.at(e.actor).retrieval.target &&
                (o.act==CareAct::ApproachBrood || o.act==CareAct::TransportBrood)) a.focus_seen=true;
        }
        if (o.phase==ObservationPhase::Started && o.duration_known) {
            ensure(audit.contains(e.actor) && audit.at(e.actor).enabled && o.began_at==e.time && o.bout.value &&
                audit.at(e.actor).selected && audit.at(e.actor).selected->bout==o.bout &&
                audit.at(e.actor).selected->act==o.act && audit.at(e.actor).selected->target==o.target &&
                starts.emplace(o.bout,o).second,"start without selected care act");
            owners[o.bout]=e.actor; audit.at(e.actor).started=o; audit.at(e.actor).selected.reset();
            if (s.care_profile->local_retrieval && o.act==CareAct::TransportBrood) {
                const auto& memory=s.care.at(e.actor).retrieval;
                if (o.bout==memory.pickup_bout && e.position==memory.pickup_site &&
                    (!memory.target.value || o.target==memory.target)) audit.at(e.actor).pickup_started=true;
            }
        }
        if (o.phase==ObservationPhase::Completed || o.phase==ObservationPhase::Interrupted) {
            if (o.duration_known) {
                ensure(starts.contains(o.bout) && owners.at(o.bout)==e.actor && starts.at(o.bout).act==o.act &&
                    starts.at(o.bout).target==o.target && starts.at(o.bout).began_at==o.began_at,"end without matching start");
                starts.erase(o.bout); owners.erase(o.bout); audit.at(e.actor).started.reset();
                if (s.care_profile->local_retrieval && o.act==CareAct::TransportBrood && o.phase==ObservationPhase::Completed) {
                    auto& a=audit.at(e.actor);
                    const auto& memory=s.care.at(e.actor).retrieval;
                    if (a.pickup_started && o.bout==memory.pickup_bout && e.position!=memory.pickup_site) a.pickup_completed=true;
                }
            }
            if (audit.contains(e.actor)) audit.at(e.actor).selected.reset();
            if (o.phase==ObservationPhase::Completed && o.act==CareAct::CloseWorkerContact && o.duration_known) {
                audit.at(e.actor).contact=true; audit.at(e.actor).last=e.time;
            }
            ensure(o.phase!=ObservationPhase::Completed || e.outcome<=Outcome::Partial,"rejection presented as completed act");
        }
    }
    ensure(configured==1 && audit.size()==s.care.size(),"care configuration/enrollment evidence missing");
    for (const auto& [id,c]:s.care) {
        const auto& a=audit.at(id);
        ensure(c.enabled==a.enabled && c.decisions==a.decisions && c.has_worker_contact==a.contact && c.last_worker_contact==a.last &&
            c.active==a.started.has_value(),"care state disagrees with committed evidence");
        ensure((!c.retrieval.target.value || a.focus_seen) && (!c.retrieval.pickup_bout.value || a.pickup_completed),
            "retrieval memory lacks committed evidence");
        if (c.active || (c.enabled && s.queue.at(s.queue_index.at(c.pending)).kind==ScheduledEvent::Kind::CareBegin)) {
            ensure(c.active?a.started.has_value():a.selected.has_value(),"missing care plan evidence");
            const auto& o=c.active?*a.started:*a.selected;
            ensure(c.act==o.act && c.target==o.target && c.destination==o.destination && c.bout==o.bout &&
                (!c.active || c.began_at==o.began_at),"care plan differs from observation");
        }
    }
}
} // namespace antworld::detail
