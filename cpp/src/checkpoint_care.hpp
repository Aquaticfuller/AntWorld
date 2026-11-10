#pragma once
#include "care_internal.hpp"
#include "checkpoint_codec.hpp"

namespace antworld::detail {
inline constexpr std::array care_times{&SpeciesCareProfile::decision_interval,&SpeciesCareProfile::bout_duration,
    &SpeciesCareProfile::worker_contact_duration,&SpeciesCareProfile::social_memory_horizon};
inline constexpr std::array care_reals{&SpeciesCareProfile::care_probability,&SpeciesCareProfile::worker_contact_probability,
    &SpeciesCareProfile::maximum_inhibition,&SpeciesCareProfile::perception_radius_m,&SpeciesCareProfile::step_m,&SpeciesCareProfile::arrangement_m};
inline constexpr std::array motion_speeds{&CareMotionProfile::worker_unloaded_m_per_s,&CareMotionProfile::queen_unloaded_m_per_s,
    &CareMotionProfile::worker_loaded_m_per_s,&CareMotionProfile::queen_loaded_m_per_s};
inline constexpr std::array motion_times{&CareMotionProfile::pickup_duration,&CareMotionProfile::placement_duration,
    &CareMotionProfile::manipulation_duration,&CareMotionProfile::search_pause};
template<class S> void write_care(Writer& w,const S& s) {
    if (!s.care_profile) return;
    for (auto m:care_times) w.time(s.care_profile.get()->*m);
    for (auto m:care_reals) w.real(s.care_profile.get()->*m);
    w.real(s.care_environment.temperature_c); w.real(s.care_environment.relative_humidity);
    if (const auto& motion=s.care_profile->motion) {
        for (auto m:motion_speeds) w.real((*motion).*m);
        for (auto m:motion_times) w.time((*motion).*m);
        w.put(motion->search_steps,1); w.put(motion->integrate_autonomy,1);
        w.put(s.care_environment.neutral_displacement_assay,1); w.real(s.care_environment.arena_radius_m);
    }
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
        if (s.care_profile->motion) {
            w.put(c.carrying_brood,1); w.put(c.returning,1); w.put(c.search_remaining,1);
            if (s.config.continuous_spatial_motion && c.carrying_brood) w.position(c.grip_offset);
        }
    }
}
template<class S> void read_care(Reader& r,S& s,const RuntimeLimits& limits,bool retrieval,bool motion) {
    SpeciesCareProfile profile; for(auto m:care_times) profile.*m=r.time(); for(auto m:care_reals) profile.*m=r.real();
    profile.local_retrieval=retrieval;
    s.care_environment={r.real(),r.real()};
    if (motion) {
        CareMotionProfile m;
        for (auto member:motion_speeds) m.*member=r.real();
        for (auto member:motion_times) m.*member=r.time();
        m.search_steps=static_cast<std::uint8_t>(r.get(1)); m.integrate_autonomy=r.flag();
        s.care_environment.neutral_displacement_assay=r.flag(); s.care_environment.arena_radius_m=r.real();
        profile.motion=m;
    }
    validate_care_profile(profile,s.care_environment,s.config);
    s.care_profile=std::make_shared<const SpeciesCareProfile>(profile);
    const auto count=r.count(limits.entities,motion?144:retrieval?141:125);
    for(std::size_t i=0;i<count;++i) {
        const EntityId id{r.get()}; CareState c;
        c.profile.context=static_cast<CareContext>(r.get(1)); c.profile.age_at_enrollment=r.time(); c.familiar_shelter=r.position();
        c.enabled=r.flag(); c.active=r.flag(); c.has_worker_contact=r.flag(); c.enrolled_at=r.time(); c.began_at=r.time(); c.last_worker_contact=r.time();
        c.decisions=r.get(); c.act=static_cast<CareAct>(r.get(1)); c.target={r.get()}; c.destination=r.position(); c.pending={r.get()}; c.bout={r.get()};
        if (retrieval) {
            c.retrieval.target={r.get()}; c.retrieval.pickup_bout={r.get()};
            if (c.retrieval.pickup_bout.value) c.retrieval.pickup_site=r.position();
        }
        if (motion) {
            c.carrying_brood=r.flag(); c.returning=r.flag(); c.search_remaining=static_cast<std::uint8_t>(r.get(1));
            if (s.config.continuous_spatial_motion && c.carrying_brood) c.grip_offset=r.position();
        }
        ensure(s.ants.index.contains(id) && s.physiology.contains(id) && c.profile.context<=CareContext::Worker &&
            (c.act<=CareAct::CloseWorkerContact || (retrieval && c.act==CareAct::RevisitBroodSite) ||
             (motion && c.act>=CareAct::PickUpBrood && c.act<=CareAct::ReturnToCareShelter)) &&
            c.enrolled_at<=s.m.now && c.began_at<=s.m.now && c.last_worker_contact<=s.m.now &&
            inside(c.familiar_shelter,s.config) && finite(c.destination) && s.care.emplace(id,c).second,"invalid care state");
        const auto a=s.ants.get(s.ants.index.at(id));
        if (s.config.continuous_spatial_motion && c.carrying_brood) {
            ensure(finite(c.grip_offset) && s.ants.index.contains(c.retrieval.target),"invalid grip offset target");
            const auto b=s.ants.get(s.ants.index.at(c.retrieval.target));
            ensure(valid_grip(a.position,b.position,c.grip_offset,s.config),"held brood disagrees with acquisition offset");
        }
        ensure(a.caste!=Caste::Male && (a.caste==Caste::Worker)==(c.profile.context==CareContext::Worker) &&
            (a.stage==LifeStage::Adult || (!a.alive() && !c.enabled)) &&
            c.familiar_shelter==s.colonies.rows[s.colonies.index.at(a.colony)].nest_position &&
            c.enabled==(c.pending.value!=0) && (!c.active || c.enabled) &&
            (c.has_worker_contact || c.last_worker_contact==SimTime{}) && (!c.target.value || (s.ants.index.contains(c.target) && c.target!=id)),"care role/shelter mismatch");
        if (retrieval) {
            const auto& memory=c.retrieval;
            ensure((c.enabled || memory==RetrievalMemory{}) &&
                (!memory.target.value || (memory.target!=id && s.ants.index.contains(memory.target) &&
                    (s.ants.get(s.ants.index.at(memory.target)).colony==a.colony ||
                     foreign_assay_stage(s,s.ants.get(s.ants.index.at(memory.target)).stage)))) &&
                (!memory.pickup_bout.value || (memory.pickup_bout.value<s.m.next_scheduled && inside(memory.pickup_site,s.config))),
                "invalid retrieval memory");
            if (c.bout.value && c.act==CareAct::RevisitBroodSite)
                ensure(!c.target.value && !memory.target.value && memory.pickup_bout.value,"revisit without pickup memory");
            if (c.bout.value && memory.target.value)
                ensure(c.target==memory.target && (c.act==CareAct::ApproachBrood || c.act==CareAct::TransportBrood ||
                    (motion && (c.act==CareAct::PickUpBrood || c.act==CareAct::PlaceBrood))),"retrieval plan target mismatch");
        }
        if (motion) {
            ensure(c.search_remaining<=profile.motion->search_steps && (c.enabled || (!c.returning && !c.search_remaining)) &&
                   (!c.returning || (integrated_care(s) && !c.carrying_brood)) &&
                   (!integrated_care(s) || !c.enabled || (s.autonomy.contains(id) && s.autonomy.at(id).enabled)),
                   "invalid care motion ownership");
            if (c.carrying_brood) {
                ensure(c.enabled && c.retrieval.target.value && c.retrieval.pickup_bout.value &&
                       (!c.bout.value || c.act==CareAct::TransportBrood || c.act==CareAct::PlaceBrood) &&
                       s.care_locks.emplace(c.retrieval.target,id).second,"invalid persistent brood reservation");
            }
        }
        if (c.enabled) {
            ensure(s.queue_index.contains(c.pending) && s.physiology.at(id).behavior_event==c.pending,"missing care schedule");
            const auto e=s.queue.at(s.queue_index.at(c.pending));
            ensure(e.actor==id && (c.active?e.kind==ScheduledEvent::Kind::CareEnd:
                (e.kind==ScheduledEvent::Kind::CareWake || e.kind==ScheduledEvent::Kind::CareBegin)),"wrong care ownership");
            if (c.active) {
                ensure(c.bout.value && c.bout.value<s.m.next_scheduled,"invalid care bout identity");
                const bool handling=handles_brood(c.act) || c.act==CareAct::CloseWorkerContact;
                ensure(!handling || c.target.value,"care handling has no target");
                const auto from=c.act==CareAct::ArrangeBrood?s.ants.get(s.ants.index.at(c.target)).position:a.position;
                const auto duration=care_duration(profile,s.config,a.caste,c.act,from,c.destination);
                ensure(e.key.time==after(c.began_at,duration.milliseconds),"care bout duration differs from profile");
                if (handling && !c.carrying_brood)
                    ensure(s.care_locks.emplace(c.target,id).second,"duplicate care reservation");
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
        EntityId held;
        PositionM grip;
        std::optional<BehaviorObservation> selected,started;
    };
    std::map<EntityId,Audit> audit;
    std::size_t configured=0;
    std::map<ScheduledId,BehaviorObservation> starts;
    std::map<ScheduledId,EntityId> owners;
    std::map<EntityId,PositionM> positions;
    const auto spatial=s.config.continuous_spatial_motion;
    for (const auto& e:s.journal) {
        if (spatial && (e.kind==FactKind::AntSeeded || e.kind==FactKind::AntBorn ||
            e.kind==FactKind::Moved || e.kind==FactKind::BroodMoved)) positions[e.actor]=e.position;
        if (e.kind==FactKind::BiologyConfigured) { ++configured; ensure(e.time==SimTime{},"late biology configuration"); }
        if (e.kind==FactKind::CareProgramChanged) {
            ensure(s.care.contains(e.actor) && e.payload<=1,"unknown care enrollment");
            auto& a=audit[e.actor]; a.enabled=e.payload!=0;
            if (!a.enabled) { a.selected.reset(); a.started.reset(); a.held={}; a.grip={}; }
        }
        if (e.kind==FactKind::CareTick && e.payload==static_cast<std::uint64_t>(ScheduledEvent::Kind::CareWake)) {
            ensure(audit.contains(e.actor) && audit.at(e.actor).enabled,"care decision without enrollment"); ++audit.at(e.actor).decisions;
        }
        if (e.kind!=FactKind::BiologicalObservation) continue;
        const auto& o=e.observation;
        ensure(o.act<CareAct::Count && o.phase<=ObservationPhase::Interrupted && o.began_at<=e.time && finite(o.destination) &&
            (!o.target.value || (s.ants.index.contains(o.target) && o.target!=e.actor &&
             (s.ants.get(s.ants.index.at(o.target)).colony==e.colony ||
              (s.care_environment.neutral_displacement_assay && foreign_assay_act(o.act,o.phase))))),"invalid observation fields");
        ensure(o.act!=CareAct::RevisitBroodSite || (s.care_profile->local_retrieval && !o.target.value),"revisit observation outside retrieval contract");
        ensure(o.act<CareAct::PickUpBrood || s.care_profile->motion.has_value(),"motion observation outside its contract");
        if (o.phase==ObservationPhase::Selected && audit.contains(e.actor) && audit.at(e.actor).enabled) {
            auto& a=audit.at(e.actor);
            a.selected=o;
            if (s.care_profile->local_retrieval && o.target==s.care.at(e.actor).retrieval.target &&
                (o.act==CareAct::ApproachBrood || o.act==CareAct::TransportBrood ||
                 o.act==CareAct::PickUpBrood || o.act==CareAct::PlaceBrood)) a.focus_seen=true;
        }
        if (o.phase==ObservationPhase::Started && o.duration_known) {
            ensure(audit.contains(e.actor) && audit.at(e.actor).enabled && o.began_at==e.time && o.bout.value &&
                audit.at(e.actor).selected && audit.at(e.actor).selected->bout==o.bout &&
                audit.at(e.actor).selected->act==o.act && audit.at(e.actor).selected->target==o.target &&
                starts.emplace(o.bout,o).second,"start without selected care act");
            owners[o.bout]=e.actor; audit.at(e.actor).started=o; audit.at(e.actor).selected.reset();
            const auto pickup_act=s.care_profile->motion?CareAct::PickUpBrood:CareAct::TransportBrood;
            if (s.care_profile->local_retrieval && o.act==pickup_act) {
                const auto& memory=s.care.at(e.actor).retrieval;
                if (o.bout==memory.pickup_bout && e.position==memory.pickup_site &&
                    (!memory.target.value || o.target==memory.target)) audit.at(e.actor).pickup_started=true;
            }
        }
        if (o.phase==ObservationPhase::Completed || o.phase==ObservationPhase::Interrupted) {
            const auto pickup_act=s.care_profile->motion?CareAct::PickUpBrood:CareAct::TransportBrood;
            if (o.duration_known) {
                ensure(starts.contains(o.bout) && owners.at(o.bout)==e.actor && starts.at(o.bout).act==o.act &&
                    starts.at(o.bout).target==o.target && starts.at(o.bout).began_at==o.began_at,"end without matching start");
                starts.erase(o.bout); owners.erase(o.bout); audit.at(e.actor).started.reset();
                if (s.care_profile->local_retrieval && o.act==pickup_act && o.phase==ObservationPhase::Completed) {
                    auto& a=audit.at(e.actor);
                    const auto& memory=s.care.at(e.actor).retrieval;
                    if (a.pickup_started && o.bout==memory.pickup_bout &&
                        (s.care_profile->motion || e.position!=memory.pickup_site)) a.pickup_completed=true;
                }
            }
            if (s.care_profile->motion && audit.contains(e.actor)) {
                auto& a=audit.at(e.actor);
                if (o.act==CareAct::PickUpBrood && o.phase==ObservationPhase::Completed) {
                    ensure(!a.held.value && o.target.value && o.duration_known,"invalid observed brood pickup");
                    a.held=o.target;
                    if (spatial) {
                        ensure(e.position==positions.at(e.actor) && within_contact(e.position,positions.at(o.target),s.config),
                               "pickup outside physical contact");
                        a.grip=displacement(positions.at(o.target),e.position);
                    }
                } else if (spatial && o.act==CareAct::TransportBrood && o.phase==ObservationPhase::Completed) {
                    ensure(a.held==o.target && e.position==positions.at(e.actor) &&
                        valid_grip(e.position,positions.at(o.target),a.grip,s.config),"transport altered the acquired grip");
                } else if (o.act==CareAct::PlaceBrood || o.phase==ObservationPhase::Interrupted) {
                    if (o.act==CareAct::PlaceBrood && o.phase==ObservationPhase::Completed) {
                        ensure(a.held.value && a.held==o.target && o.duration_known,"placement without a real pickup");
                        if (spatial) ensure(valid_grip(e.position,positions.at(o.target),a.grip,s.config) &&
                            within_contact(positions.at(o.target),s.care.at(e.actor).familiar_shelter,s.config),
                            "placement lacks physical grip or shelter contact");
                    }
                    a.held={};
                    a.grip={};
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
        ensure(a.held==(c.carrying_brood?c.retrieval.target:EntityId{}),"held brood disagrees with observations");
        if (spatial) ensure(a.grip==c.grip_offset,"saved grip differs from the recorded acquisition");
        if (c.active || (c.enabled && s.queue.at(s.queue_index.at(c.pending)).kind==ScheduledEvent::Kind::CareBegin)) {
            ensure(c.active?a.started.has_value():a.selected.has_value(),"missing care plan evidence");
            const auto& o=c.active?*a.started:*a.selected;
            ensure(c.act==o.act && c.target==o.target && c.destination==o.destination && c.bout==o.bout &&
                (!c.active || c.began_at==o.began_at),"care plan differs from observation");
        }
    }
}
} // namespace antworld::detail
