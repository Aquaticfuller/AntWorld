#include "care_internal.hpp"
#include "physiology_internal.hpp"
#include "social_internal.hpp"
#include "behavior_rng.hpp"

namespace antworld {
using namespace detail;
void WorldRuntime::configure_biology(const SpeciesCareProfile& profile, const EnvironmentCareProfile& environment) {
    auto& s=*state_;
    if (s.care_profile || !s.long_term || !s.social || s.m.now!=SimTime{} || s.m.watermark)
        throw std::invalid_argument("biology contract requires an unexecuted long-term social world");
    validate_care_profile(profile,environment,s.config);
    auto prepared=std::make_shared<const SpeciesCareProfile>(profile);
    Transaction tx(s,limits_); s.care_profile=prepared; s.care_environment=environment;
    WorldEvent f; f.kind=FactKind::BiologyConfigured; tx.fact(f); tx.commit();
}
std::optional<SpeciesCareProfile> WorldRuntime::care_profile() const {
    return state_->care_profile ? std::optional<SpeciesCareProfile>{*state_->care_profile} : std::nullopt;
}
std::optional<CareState> WorldRuntime::query_care(AntRef ref) const {
    if (!query_ant(ref) || !state_->care.contains(ref.id)) return {};
    return state_->care.at(ref.id);
}
void WorldRuntime::observe(Transaction& tx, EntityId actor, ScheduledId source,
                           const BehaviorObservation& observation, FoodMass amount, Outcome outcome) {
    if (!state_->care_profile) return;
    const auto a=state_->ants.get(state_->ants.index.at(actor));
    WorldEvent f; f.kind=FactKind::BiologicalObservation; f.source=source; f.actor=actor;
    f.colony=a.colony; f.stage=a.stage; f.position=a.position; f.observation=observation;
    f.transferred=amount; f.outcome=outcome; tx.fact(f);
}
void WorldRuntime::schedule_care(Transaction& tx, EntityId id, SimTime when) {
    auto& s=*state_; auto c=s.care.at(id); if (!c.enabled) return;
    ScheduledEvent e; e.actor=id; e.kind=ScheduledEvent::Kind::CareWake; e.issued_at=s.m.now;
    e.key={when,Phase::Perception,0,0,0}; c.pending=tx.insert(e); tx.care.set(id,c);
    auto p=s.physiology.at(id); p.behavior_event=c.pending; tx.physiology.set(id,p);
}
void WorldRuntime::enable_brood_care(AntRef ref, const IndividualCareProfile& profile) {
    auto& s=*state_; const auto a=query_ant(ref);
    if (!s.care_profile || !a || a->stage!=LifeStage::Adult || a->caste==Caste::Male ||
        !s.physiology.contains(ref.id) || profile.context>CareContext::Worker || profile.age_at_enrollment.milliseconds<0 ||
        (a->caste==Caste::Worker)!=(profile.context==CareContext::Worker) ||
        s.physiology.at(ref.id).behavior!=IndividualBehavior::Paused ||
        (s.autonomy.contains(ref.id) && s.autonomy.at(ref.id).enabled) || s.external_resolution(ref.id) ||
        (s.care.contains(ref.id) && s.care.at(ref.id).enabled))
        throw std::invalid_argument("invalid caste-specific care enrollment");
    const auto nest=s.colonies.rows[s.colonies.index.at(a->colony)].nest_position;
    if (!s.care.contains(ref.id) && (distance(a->position,nest)>s.config.contact_distance_m || !spatially_clear(a->position,nest)))
        throw std::invalid_argument("first enrollment requires locally experienced shelter");
    Transaction tx(s,limits_); synchronize_physiology(tx,ref.id);
    CareState c; if (s.care.contains(ref.id)) c=s.care.at(ref.id);
    else { c.profile=profile; c.familiar_shelter=nest; c.enrolled_at=s.m.now; }
    if (c.profile!=profile) throw std::invalid_argument("care identity context cannot be rewritten");
    c.enabled=true; tx.care.set(ref.id,c);
    if (a->caste==Caste::Worker) {
        auto p=s.physiology.at(ref.id); p.behavior=IndividualBehavior::Nurse; tx.physiology.set(ref.id,p);
        WorldEvent f; f.kind=FactKind::BehaviorChanged; f.actor=ref.id; f.colony=a->colony;
        f.stage=a->stage; f.position=a->position; f.payload=static_cast<std::uint64_t>(p.behavior); tx.fact(f);
    }
    schedule_care(tx,ref.id,after(s.m.now,1)); schedule_physiology(tx,ref.id);
    WorldEvent f; f.kind=FactKind::CareProgramChanged; f.actor=ref.id; f.colony=a->colony;
    f.stage=a->stage; f.position=a->position; f.payload=1; tx.fact(f); tx.commit();
}
void WorldRuntime::pause_brood_care(AntRef ref) {
    if (!query_ant(ref) || !state_->care.contains(ref.id)) throw std::invalid_argument("unknown care actor");
    Transaction tx(*state_,limits_); interrupt_care(tx,ref.id,Outcome::InvalidTransition,true); tx.commit();
}
void WorldRuntime::interrupt_care(Transaction& tx, EntityId id, Outcome reason, bool disable) {
    auto& s=*state_; if (!s.care_profile) return;
    if (s.care_locks.contains(id)) {
        const auto owner=s.care_locks.at(id);
        if (owner!=id) interrupt_care(tx,owner,reason);
    }
    if (!s.care.contains(id) || !s.care.at(id).enabled) return;
    auto c=s.care.at(id);
    if (!disable && !c.active && !c.pending.value) return;
    if (c.active || c.bout.value) observe(tx,id,c.bout,{ObservationPhase::Interrupted,c.act,c.target,c.bout,c.active?c.began_at:s.m.now,c.active},{},reason);
    if (c.target.value && s.care_locks.contains(c.target) && s.care_locks.at(c.target)==id) tx.care_locks.erase(c.target);
    if (s.queue_index.contains(c.pending)) tx.remove(s.queue_index.at(c.pending));
    c.active=false; c.pending={}; c.bout={}; c.target={}; c.enabled=!disable;
    c.retrieval={};
    tx.care.set(id,c); auto p=s.physiology.at(id); p.behavior_event={}; tx.physiology.set(id,p);
    if (disable) {
        synchronize_physiology(tx,id); p=s.physiology.at(id); p.behavior=IndividualBehavior::Paused; tx.physiology.set(id,p);
        const auto a=s.ants.get(s.ants.index.at(id));
        WorldEvent f; f.kind=FactKind::CareProgramChanged; f.actor=id; f.colony=a.colony;
        f.stage=a.stage; f.position=a.position; tx.fact(f);
        if (a.alive()) {
            f.kind=FactKind::BehaviorChanged; f.payload=0; tx.fact(f); schedule_physiology(tx,id);
        }
    } else schedule_care(tx,id,after(s.m.now,1));
}
void WorldRuntime::validate_active_care(Transaction& tx) {
    auto& s=*state_; if (!s.care_profile) return;
    std::vector<EntityId> blocked(0);
    for (const auto& [id,c]:s.care) if (c.enabled && c.active) {
        const auto a=s.ants.get(s.ants.index.at(id));
        const auto half=care_extent(s,body_half(id),c.act);
        const auto from=c.act==CareAct::ArrangeBrood?query_ant({s.world,c.target})->position:a.position;
        bool clear=spatially_clear(from,c.destination,half);
        if (c.target.value) {
            const auto b=s.ants.get(s.ants.index.at(c.target));
            const PositionM target{b.position.x+c.destination.x-a.position.x,b.position.y+c.destination.y-a.position.y,b.position.z+c.destination.z-a.position.z};
            clear=clear && spatially_clear(a.position,b.position) &&
                (c.act!=CareAct::TransportBrood || spatially_clear(b.position,target,half));
        }
        if (!clear) blocked.push_back(id);
    }
    for (auto id:blocked) interrupt_care(tx,id,Outcome::Blocked);
}
void WorldRuntime::resolve_care_wakes(Transaction& tx, const std::vector<ScheduledEvent>& wakes) {
    auto& s=*state_; const auto& cfg=*s.care_profile;
    // Throwing count constructors preserve rollback when MSVC Debug allocates iterator proxies.
    std::vector<CareState> choices(0); choices.reserve(wakes.size());
    std::vector<std::vector<AntRef>> opportunities(0); opportunities.reserve(wakes.size());
    for (std::size_t n=0;n<wakes.size();++n) opportunities.emplace_back(0);
    for (std::size_t n=0;n<wakes.size();++n) {
        const auto& wake=wakes[n]; auto c=s.care.at(wake.actor); const auto a=*query_ant({s.world,wake.actor});
        if (!c.enabled || c.active || c.pending!=wake.id || !a.alive()) throw std::logic_error("care wake ownership");
        auto rng=individual_rng(s.seed ^ UINT64_C(0x51434152454d4f44),a.id,c.decisions);
        auto draw=[&](double probability) { return static_cast<double>(bounded_draw(rng,1000000))/1000000<probability; };
        c.act=CareAct::Inactive; c.target={}; c.destination=a.position; c.bout={};
        const auto local=care_neighborhood({s.world,a.id},cfg.perception_radius_m);
        std::vector<AntRef> brood_candidates(0),workers(0);
        for (auto ref:local.ants) {
            const auto other=*query_ant(ref);
            if (other.colony!=a.colony || !other.alive()) continue;
            if (brood(other.stage)) brood_candidates.push_back(ref);
            if (distance(a.position,other.position)<=s.config.contact_distance_m) {
                if (brood(other.stage) || (other.stage==LifeStage::Adult && other.caste==Caste::Worker))
                    opportunities[n].push_back(ref);
                if (other.stage==LifeStage::Adult && other.caste==Caste::Worker) workers.push_back(ref);
            }
        }
        const auto p=*query_physiology({s.world,a.id});
        // Retain the existing quarter-capacity individual urgency proxy; do not change metabolism.
        const bool capable=p.body_energy_nj>=p.config.energy_capacity_nj/4 && p.hydration_ug>=p.config.hydration_capacity_ug/4;
        bool continuing=false;
        bool revisiting=false;
        if (cfg.local_retrieval && capable) {
            const auto displaced=[&](AntRef ref) {
                const auto other=s.ants.get(s.ants.index.at(ref.id));
                return distance(other.position,c.familiar_shelter)>s.config.contact_distance_m;
            };
            // Eligibility uses only locally seen brood. The opportunity records above are unchanged.
            std::erase_if(brood_candidates,[&](AntRef ref) {
                return displaced(ref) && s.care_locks.contains(ref.id) && s.care_locks.at(ref.id)!=a.id;
            });
            if (c.retrieval.target.value && !std::any_of(brood_candidates.begin(),brood_candidates.end(),[&](AntRef ref) {
                return ref.id==c.retrieval.target && displaced(ref);
            })) c.retrieval={};
            if (!c.retrieval.target.value && c.retrieval.pickup_bout.value && a.position==c.retrieval.pickup_site)
                c.retrieval={};
            continuing=c.retrieval.target.value || c.retrieval.pickup_bout.value;
            const bool outside=std::any_of(brood_candidates.begin(),brood_candidates.end(),displaced);
            if (outside) std::erase_if(brood_candidates,[&](AntRef ref) { return !displaced(ref); });
            revisiting=continuing && !outside;
        } else if (cfg.local_retrieval) {
            c.retrieval={};
        }
        if (revisiting) {
            c.act=CareAct::RevisitBroodSite;
            c.destination=toward(a.position,c.retrieval.pickup_site,cfg.step_m);
        } else if (capable && !continuing && a.caste==Caste::Queen && !workers.empty() && draw(cfg.worker_contact_probability)) {
            c.act=CareAct::CloseWorkerContact; c.target=workers[static_cast<std::size_t>(bounded_draw(rng,workers.size()))].id;
        } else if (capable && !brood_candidates.empty()) {
            double memory=0;
            if (c.has_worker_contact) memory=std::max(0.0,1.0-static_cast<double>(s.m.now.milliseconds-c.last_worker_contact.milliseconds)/static_cast<double>(cfg.social_memory_horizon.milliseconds));
            const auto probability=cfg.care_probability*(a.caste==Caste::Queen ? 1-cfg.maximum_inhibition*memory : 1);
            if (continuing || draw(probability)) {
                c.target=c.retrieval.target.value?c.retrieval.target:
                    brood_candidates[static_cast<std::size_t>(bounded_draw(rng,brood_candidates.size()))].id;
                const auto b=*query_ant({s.world,c.target});
                const bool displaced=distance(b.position,c.familiar_shelter)>s.config.contact_distance_m;
                if (cfg.local_retrieval && displaced && c.retrieval.target!=c.target) {
                    c.retrieval={};
                    c.retrieval.target=c.target;
                }
                if (distance(a.position,b.position)>s.config.contact_distance_m) {
                    c.act=CareAct::ApproachBrood; c.destination=toward(a.position,b.position,cfg.step_m);
                } else if (displaced) {
                    c.act=CareAct::TransportBrood; c.destination=toward(a.position,c.familiar_shelter,cfg.step_m);
                } else {
                    std::vector<CareAct> acts{CareAct::InspectBrood,CareAct::ArrangeBrood,CareAct::CleanBrood};
                    const auto receiver=query_physiology({s.world,b.id});
                    if (b.stage==LifeStage::Larva && receiver && ingredient_min(p.crop,nutrient_demand(*receiver,b.stage)).total_ug()) acts.push_back(CareAct::FeedBrood);
                    c.act=acts[static_cast<std::size_t>(bounded_draw(rng,acts.size()))];
                    if (c.act==CareAct::ArrangeBrood) c.destination=toward(b.position,a.position,cfg.arrangement_m);
                }
            }
        } else if (capable && brood_candidates.empty()) {
            // Local exploratory steps, not a hidden brood-location query.
            const auto direction=bounded_draw(rng,4);
            c.act=CareAct::Walk;
            if (direction<2) c.destination.x+=(direction==0?1:-1)*cfg.step_m;
            else c.destination.z+=(direction==2?1:-1)*cfg.step_m;
        }
        if (care_motion(c.act)) {
            const auto from=c.act==CareAct::ArrangeBrood?query_ant({s.world,c.target})->position:a.position;
            if (!inside(c.destination,s.config) || !spatially_clear(from,c.destination,care_extent(s,body_half(a.id),c.act))) {
                c.act=CareAct::Inactive; c.target={}; c.destination=a.position;
                c.retrieval={};
            }
        }
        choices.push_back(c);
    }
    for (std::size_t n=0;n<wakes.size();++n) {
        const auto& wake=wakes[n]; auto c=choices[n]; ++c.decisions;
        WorldEvent tick; tick.kind=FactKind::CareTick; tick.actor=wake.actor;
        const auto a=*query_ant({s.world,wake.actor}); tick.colony=a.colony; tick.stage=a.stage; tick.position=a.position;
        tick.source=wake.id; tick.payload=static_cast<std::uint64_t>(wake.kind); tx.fact(tick);
        {
            profiling::Scope profile(profiling::Category::CareOpportunities);
            for (auto other:opportunities[n]) observe(tx,wake.actor,wake.id,{ObservationPhase::Opportunity,
                brood(query_ant(other)->stage)?CareAct::InspectBrood:CareAct::CloseWorkerContact,other.id,{},s.m.now,false});
            profiling::record_work(profiling::Category::CareOpportunities,opportunities[n].size());
        }
        ScheduledEvent e; e.actor=wake.actor; e.kind=ScheduledEvent::Kind::CareBegin; e.issued_at=s.m.now;
        e.key={after(s.m.now,1),Phase::Resolution,0,0,0};
        c.pending=tx.insert(e); c.bout=c.pending; tx.care.set(wake.actor,c);
        auto p=s.physiology.at(wake.actor); p.behavior_event=c.pending; tx.physiology.set(wake.actor,p);
        observe(tx,wake.actor,wake.id,{ObservationPhase::Selected,c.act,c.target,c.bout,s.m.now,false,c.destination});
    }
}
void WorldRuntime::execute_care_action(Transaction& tx, const ScheduledEvent& event) {
    auto& s=*state_; auto c=s.care.at(event.actor); auto a=*query_ant({s.world,event.actor});
    if (!c.enabled || c.pending!=event.id || !a.alive()) throw std::logic_error("care action ownership");
    WorldEvent tick; tick.kind=FactKind::CareTick; tick.source=event.id; tick.actor=a.id;
    tick.colony=a.colony; tick.stage=a.stage; tick.position=a.position; tick.payload=static_cast<std::uint64_t>(event.kind); tx.fact(tick);
    Outcome outcome=Outcome::Success;
    const bool handling=handles_brood(c.act) || c.act==CareAct::CloseWorkerContact;
    if (c.target.value) {
        const auto b=*query_ant({s.world,c.target});
        if (!b.alive()) outcome=Outcome::DeadActor;
        else if ((handles_brood(c.act) || c.act==CareAct::ApproachBrood) && !brood(b.stage)) outcome=Outcome::InvalidStage;
        else if (c.act==CareAct::CloseWorkerContact && (b.stage!=LifeStage::Adult || b.caste!=Caste::Worker)) outcome=Outcome::InvalidStage;
        else if (b.colony!=a.colony || !spatially_clear(a.position,b.position) ||
                 distance(a.position,b.position)>(c.act==CareAct::ApproachBrood?s.care_profile->perception_radius_m:s.config.contact_distance_m)) outcome=Outcome::OutOfReach;
        else if (handling && s.care_locks.contains(c.target) && s.care_locks.at(c.target)!=a.id) outcome=Outcome::DuplicateAction;
    }
    if (outcome==Outcome::Success && care_motion(c.act)) {
        const auto from=c.act==CareAct::ArrangeBrood?query_ant({s.world,c.target})->position:a.position;
        if (!inside(c.destination,s.config) || !spatially_clear(from,c.destination,care_extent(s,body_half(a.id),c.act)) ||
            (s.care_profile->local_retrieval && c.act==CareAct::TransportBrood && c.destination==a.position)) outcome=Outcome::Blocked;
    }
    if (event.kind==ScheduledEvent::Kind::CareBegin && outcome==Outcome::Success) {
        if (handling) tx.care_locks.set(c.target,a.id);
        c.active=true; c.began_at=s.m.now;
        const auto duration=c.act==CareAct::Inactive?s.care_profile->decision_interval:
            c.act==CareAct::CloseWorkerContact?s.care_profile->worker_contact_duration:s.care_profile->bout_duration;
        ScheduledEvent e; e.actor=a.id; e.kind=ScheduledEvent::Kind::CareEnd; e.issued_at=s.m.now;
        e.key={after(s.m.now,duration.milliseconds),Phase::Resolution,0,0,0}; c.pending=tx.insert(e);
        tx.care.set(a.id,c); auto p=s.physiology.at(a.id); p.behavior_event=c.pending; tx.physiology.set(a.id,p);
        observe(tx,a.id,event.id,{ObservationPhase::Started,c.act,c.target,c.bout,c.began_at,true,c.destination}); return;
    }
    // Release ownership before applying this act's movements; external movement invalidates other acts.
    if (c.target.value && s.care_locks.contains(c.target) && s.care_locks.at(c.target)==a.id) tx.care_locks.erase(c.target);
    auto ended=c; ended.active=false; ended.pending={}; ended.target={}; ended.bout={}; tx.care.set(a.id,ended);
    FoodMass amount;
    if (event.kind==ScheduledEvent::Kind::CareEnd && outcome==Outcome::Success) {
        auto move=[&](EntityId id,PositionM destination,bool carried) {
            const auto i=s.ants.index.at(id); auto ant=s.ants.get(i);
            if (ant.position==destination) return;
            index_position(tx,id,ant.position,destination); tx.touch_ant(i);
            ant.position=destination; bump(ant.position_revision); s.ants.set(i,ant);
            WorldEvent f; f.kind=carried?FactKind::BroodMoved:FactKind::Moved; f.actor=id; f.source=event.id;
            f.colony=ant.colony; f.stage=ant.stage; f.position=destination; f.payload=carried?a.id.value:0; tx.fact(f);
        };
        if (care_motion(c.act) && c.act!=CareAct::ArrangeBrood) {
            if (c.act==CareAct::TransportBrood) {
                const auto b=*query_ant({s.world,c.target});
                const PositionM target{b.position.x+c.destination.x-a.position.x,b.position.y+c.destination.y-a.position.y,b.position.z+c.destination.z-a.position.z};
                if (!inside(target,s.config) || !spatially_clear(b.position,target,care_extent(s,body_half(a.id),c.act))) outcome=Outcome::Blocked;
                else {
                    move(c.target,target,true);
                    if (s.care_profile->local_retrieval) {
                        if (!ended.retrieval.pickup_bout.value) {
                            ended.retrieval.pickup_bout=c.bout;
                            ended.retrieval.pickup_site=a.position;
                        }
                        if (distance(target,c.familiar_shelter)<=s.config.contact_distance_m) ended.retrieval.target={};
                    }
                }
            }
            if (outcome==Outcome::Success) move(a.id,c.destination,false);
        } else if (c.act==CareAct::ArrangeBrood) move(c.target,c.destination,true);
        else if (c.act==CareAct::FeedBrood) {
            ScheduledEvent gift=event; gift.kind=ScheduledEvent::Kind::Trophallaxis; gift.payload=c.target.value;
            gift.requested_ug=s.physiology.at(a.id).config.transfer_limit_ug;
            WorldEvent f; f.kind=FactKind::ActionRejected; f.source=event.id; f.actor=a.id; f.colony=a.colony; f.stage=a.stage; f.position=a.position;
            resolve_nutrition_action(tx,gift,f); outcome=f.outcome; amount=f.transferred; tx.fact(f);
        } else if (c.act==CareAct::CloseWorkerContact) {
            ended.has_worker_contact=true; ended.last_worker_contact=s.m.now; tx.care.set(a.id,ended);
        }
    }
    if (outcome>Outcome::Partial || (c.act==CareAct::RevisitBroodSite && c.destination==c.retrieval.pickup_site))
        ended.retrieval={};
    if (ended.retrieval!=c.retrieval) tx.care.set(a.id,ended);
    observe(tx,a.id,event.id,{event.kind==ScheduledEvent::Kind::CareEnd && outcome<=Outcome::Partial?ObservationPhase::Completed:ObservationPhase::Interrupted,
        c.act,c.target,c.bout,c.active?c.began_at:s.m.now,c.active},amount,outcome);
    schedule_care(tx,a.id,after(s.m.now,1));
}
void WorldRuntime::observe_legacy_action(Transaction& tx,const ScheduledEvent& e,const WorldEvent& f) {
    if (!state_->care_profile) return;
    CareAct act=CareAct::Inactive;
    switch(e.kind) {
    case ScheduledEvent::Kind::Move: act=CareAct::Walk; break;
    case ScheduledEvent::Kind::CollectFood: act=CareAct::CollectFood; break;
    case ScheduledEvent::Kind::DeliverFood: act=CareAct::DeliverFood; break;
    case ScheduledEvent::Kind::IngestCargo: case ScheduledEvent::Kind::WithdrawNest: act=CareAct::IngestFood; break;
    case ScheduledEvent::Kind::Trophallaxis: act=query_ant({state_->world,{e.payload}})->stage==LifeStage::Larva?CareAct::FeedBrood:CareAct::TransferNutrition; break;
    case ScheduledEvent::Kind::SoilAction: act=f.kind==FactKind::SoilExcavated?CareAct::Excavate:CareAct::HandleSoil; break;
    default: break;
    }
    const EntityId target=e.kind==ScheduledEvent::Kind::Trophallaxis?EntityId{e.payload}:EntityId{};
    if (f.outcome<=Outcome::Partial) observe(tx,e.actor,e.id,{ObservationPhase::Started,act,target,e.id,state_->m.now,false});
    observe(tx,e.actor,e.id,{f.outcome<=Outcome::Partial?ObservationPhase::Completed:ObservationPhase::Interrupted,act,target,e.id,state_->m.now,false},f.transferred,f.outcome);
}
} // namespace antworld
