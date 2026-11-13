#include "care_internal.hpp"
#include "physiology_internal.hpp"
#include "social_internal.hpp"
#include "behavior_rng.hpp"
#include "founding_internal.hpp"
#include "ecological_internal.hpp"

namespace antworld {
using namespace detail;
namespace {
PositionM carried_position(PositionM brood_position,PositionM from,PositionM to,const CareState& care,
                           bool timed,bool continuous) {
    if (timed && continuous) return translated(to,care.grip_offset);
    if (timed)
        return {brood_position.x+(to.x-from.x),brood_position.y+(to.y-from.y),brood_position.z+(to.z-from.z)};
    return {brood_position.x+to.x-from.x,brood_position.y+to.y-from.y,brood_position.z+to.z-from.z};
}
}
bool WorldRuntime::clear_care_segment(PositionM from,PositionM to,std::int32_t half) const {
    const auto& s=*state_;
    return inside(to,s.config) && inside_care_arena(s.care_environment,to) &&
           surface_care_clear(s,from,to) && spatially_clear(from,to,half);
}
PositionM WorldRuntime::care_destination(const CareState& care,const AntState& actor,PositionM goal,
                                        std::optional<PositionM> load) const {
    const auto& s=*state_;
    const auto step=s.care_profile->step_m;
    const auto direct=care_toward(s,actor.position,goal,step);
    if (!s.config.continuous_spatial_motion || !s.care_profile->motion || direct==actor.position) return direct;
    const auto half=care_extent(s,body_half(actor.id),care.act);
    const auto clear=[&](PositionM next) {
        return clear_care_segment(actor.position,next,half) &&
            (!load || clear_care_segment(*load,translated(next,care.grip_offset),half));
    };
    if (clear(direct)) return direct;
    // Try a local, distance-reducing axis segment when a diagonal clips a
    // corner. This is a clearance fallback with no remote topology or brood cue.
    auto best=direct;
    auto remaining=distance(actor.position,goal);
    for (auto axis:{&PositionM::x,&PositionM::y,&PositionM::z}) {
        auto next=actor.position;
        next.*axis+=std::clamp(goal.*axis-next.*axis,-step,step);
        const auto d=distance(next,goal);
        if (d<remaining && clear(next)) { best=next; remaining=d; }
    }
    return best;
}
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
void WorldRuntime::schedule_care(Transaction& tx, EntityId id, SimTime when, EntityId hatch_target) {
    auto& s=*state_; auto c=s.care.at(id); if (!c.enabled) return;
    ScheduledEvent e; e.actor=id; e.kind=ScheduledEvent::Kind::CareWake; e.issued_at=s.m.now;
    e.key={when,Phase::Perception,0,0,0}; e.payload=hatch_target.value; c.pending=tx.insert(e); tx.care.set(id,c);
    auto p=s.physiology.at(id); p.behavior_event=c.pending; tx.physiology.set(id,p);
}
void WorldRuntime::enable_brood_care(AntRef ref, const IndividualCareProfile& profile) {
    auto& s=*state_; const auto a=query_ant(ref);
    if (!s.care_profile || integrated_care(s) || !a || a->stage!=LifeStage::Adult || a->caste==Caste::Male ||
        !s.physiology.contains(ref.id) || profile.context>CareContext::Worker || profile.age_at_enrollment.milliseconds<0 ||
        (a->caste==Caste::Worker)!=(profile.context==CareContext::Worker) ||
        s.physiology.at(ref.id).behavior!=IndividualBehavior::Paused ||
        (s.autonomy.contains(ref.id) && s.autonomy.at(ref.id).enabled) || s.external_resolution(ref.id) ||
        (s.care.contains(ref.id) && s.care.at(ref.id).enabled))
        throw std::invalid_argument("invalid caste-specific care enrollment");
    const auto nest=s.colonies.rows[s.colonies.index.at(a->colony)].nest_position;
    if (!s.care.contains(ref.id) && (!within_contact(a->position,nest,s.config) || !spatially_clear(a->position,nest)))
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
bool WorldRuntime::local_care_available(AntRef ref) const {
    const auto& s=*state_;
    if (!integrated_care(s) || care_owned(s,ref.id)) return false;
    const auto a=*query_ant(ref);
    const auto nest=s.colonies.rows[s.colonies.index.at(a.colony)].nest_position;
    if (a.position!=nest) {
        // Only a remembered shelter can resume a failed return, one valid step at a time.
        if (!s.care.contains(a.id)) return false;
        const auto shelter=s.care.at(a.id).familiar_shelter;
        auto care=s.care.at(a.id); care.act=CareAct::ReturnToCareShelter;
        const auto next=care_destination(care,a,shelter);
        return next!=a.position && clear_care_segment(a.position,next,body_half(a.id));
    }
    std::vector<AntRef> local(0);
    collect_care_neighbors(ref,s.care_profile->perception_radius_m,local);
    return std::any_of(local.begin(),local.end(),[&](AntRef neighbor) {
        const auto b=*query_ant(neighbor);
        return b.alive() && b.colony==a.colony && surface_care_clear(s,a.position,b.position) &&
            ((brood(b.stage) && !s.care_locks.contains(b.id)) ||
             (a.caste==Caste::Queen && b.caste==Caste::Worker && b.stage==LifeStage::Adult &&
              within_contact(a.position,b.position,s.config)));
    });
}
void WorldRuntime::start_autonomous_care(Transaction& tx,AntRef ref,ScheduledId source,EntityId hatch_target) {
    auto& s=*state_;
    const auto a=*query_ant(ref);
    CareState care;
    if (s.care.contains(a.id)) care=s.care.at(a.id);
    else {
        care.familiar_shelter=s.colonies.rows[s.colonies.index.at(a.colony)].nest_position;
        care.enrolled_at=s.m.now;
        care.profile={a.caste==Caste::Queen?CareContext::FoundingQueen:CareContext::Worker,
                      {s.m.now.milliseconds-a.born_at.milliseconds}};
    }
    if (a.caste==Caste::Worker) change_behavior(tx,ref,IndividualBehavior::Nurse,source,true);
    care.enabled=true;
    care.returning=a.position!=care.familiar_shelter;
    tx.care.set(a.id,care);
    schedule_care(tx,a.id,after(s.m.now,1),hatch_target);
    WorldEvent f; f.kind=FactKind::CareProgramChanged; f.actor=a.id; f.colony=a.colony;
    f.stage=a.stage; f.position=a.position; f.payload=1; tx.fact(f);
}
void WorldRuntime::notify_local_hatch(Transaction& tx, const AntState& larva, ScheduledId source) {
    auto& s=*state_;
    const auto founder=s.founding->founder;
    const auto last=s.m.last_founding_hatch_cue;
    if ((last!=SimTime{} && s.m.now.milliseconds-last.milliseconds<founding_hatch_cooldown_ms) ||
        !s.autonomy.contains(founder) || !s.autonomy.at(founder).enabled || care_owned(s,founder) ||
        s.external_resolution(founder)) return;
    const AntRef ref{s.world,founder};
    const auto queen=*query_ant(ref);
    const auto shelter=s.colonies.rows[s.colonies.index.at(queen.colony)].nest_position;
    if (!queen.alive() || queen.colony!=larva.colony || queen.position!=shelter ||
        s.physiology.at(larva.id).mother!=founder || !within_contact(queen.position,larva.position,s.config) ||
        !within_distance(queen.position,larva.position,s.care_profile->perception_radius_m,s.config.continuous_spatial_motion) ||
        !surface_care_clear(s,queen.position,larva.position) || !spatially_clear(queen.position,larva.position) ||
        s.care_locks.contains(larva.id)) return;
    const auto p=*query_physiology(ref);
    if (p.behavior!=IndividualBehavior::Paused || p.body_energy_nj<p.config.energy_capacity_nj/4 ||
        p.hydration_ug<p.config.hydration_capacity_ug/4) return;
    start_autonomous_care(tx,ref,source,larva.id);
    s.m.last_founding_hatch_cue=s.m.now;
    WorldEvent f; f.kind=FactKind::FoundingHatchCue; f.actor=founder; f.colony=queen.colony;
    f.stage=queen.stage; f.position=queen.position; f.source=source;
    f.payload=larva.id.value; f.random_value=s.care.at(founder).pending.value;
    tx.fact(f);
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
    if (c.active && c.act!=CareAct::Inactive) set_activity_work(tx,id,{});
    if (c.active || c.bout.value) observe(tx,id,c.bout,{ObservationPhase::Interrupted,c.act,c.target,c.bout,c.active?c.began_at:s.m.now,c.active},{},reason);
    else if (c.carrying_brood) observe(tx,id,c.pending,{ObservationPhase::Interrupted,CareAct::PlaceBrood,
        c.retrieval.target,c.retrieval.pickup_bout,s.m.now,false},{},reason);
    const auto locked=c.carrying_brood?c.retrieval.target:c.target;
    if (locked.value && s.care_locks.contains(locked) && s.care_locks.at(locked)==id) tx.care_locks.erase(locked);
    if (s.queue_index.contains(c.pending)) tx.remove(s.queue_index.at(c.pending));
    c.active=false; c.pending={}; c.bout={}; c.target={}; c.enabled=!disable;
    c.retrieval={};
    c.carrying_brood=false; c.grip_offset={}; c.search_remaining=0; c.returning=!disable && integrated_care(s);
    tx.care.set(id,c); auto p=s.physiology.at(id); p.behavior_event={}; tx.physiology.set(id,p);
    if (disable) {
        synchronize_physiology(tx,id); p=s.physiology.at(id); p.behavior=IndividualBehavior::Paused; tx.physiology.set(id,p);
        const auto a=s.ants.get(s.ants.index.at(id));
        WorldEvent f; f.kind=FactKind::CareProgramChanged; f.actor=id; f.colony=a.colony;
        f.stage=a.stage; f.position=a.position; tx.fact(f);
        if (a.alive()) {
            f.kind=FactKind::BehaviorChanged; f.payload=0; tx.fact(f); schedule_physiology(tx,id);
            if (integrated_care(s) && s.autonomy.contains(id)) {
                auto autonomy=s.autonomy.at(id); autonomy.last_program_change=s.m.now; tx.autonomy.set(id,autonomy);
            }
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
        bool clear=clear_care_segment(from,c.destination,half);
        if (c.target.value) {
            const auto b=s.ants.get(s.ants.index.at(c.target));
            const auto target=carried_position(b.position,a.position,c.destination,c,s.care_profile->motion.has_value(),
                                               s.config.continuous_spatial_motion);
            clear=clear && spatially_clear(a.position,b.position) &&
                (c.act!=CareAct::TransportBrood || clear_care_segment(b.position,target,half));
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
    const auto* persistence = s.founding && s.founding->profile.feeding_persistence
        ? &*s.founding->profile.feeding_persistence : nullptr;
    std::vector<FoundingCareWake> annotations(0);
    if (persistence && persistence->repeat_ppm) annotations.resize(wakes.size());
    for (std::size_t n=0;n<wakes.size();++n) {
        const auto& wake=wakes[n]; auto c=s.care.at(wake.actor); const auto a=*query_ant({s.world,wake.actor});
        if (!c.enabled || c.active || c.pending!=wake.id || !a.alive()) throw std::logic_error("care wake ownership");
        auto rng=individual_rng(s.seed ^ UINT64_C(0x51434152454d4f44),a.id,c.decisions);
        auto draw=[&](double probability) { return static_cast<double>(bounded_draw(rng,1000000))/1000000<probability; };
        c.act=CareAct::Inactive; c.target={}; c.destination=a.position; c.bout={};
        // MSVC Debug iterator proxies can allocate even during a noexcept vector move.
        std::vector<AntRef> local(0);
        collect_care_neighbors({s.world,a.id},cfg.perception_radius_m,local);
        std::vector<AntRef> brood_candidates(0),workers(0);
        for (auto ref:local) {
            const auto other=*query_ant(ref);
            if (!other.alive() || !surface_care_clear(s,a.position,other.position)) continue;
            const bool foreign=other.colony!=a.colony;
            if (foreign && (!foreign_assay_stage(s,other.stage) ||
                (within_contact(other.position,c.familiar_shelter,s.config) &&
                 !(c.carrying_brood && c.retrieval.target==ref.id)))) continue;
            if (brood(other.stage)) brood_candidates.push_back(ref);
            if (within_contact(a.position,other.position,s.config)) {
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
        if (cfg.local_retrieval && capable && !c.carrying_brood && !c.returning) {
            const auto displaced=[&](AntRef ref) {
                const auto other=s.ants.get(s.ants.index.at(ref.id));
                return !within_contact(other.position,c.familiar_shelter,s.config);
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
        } else if (cfg.local_retrieval && !c.carrying_brood) {
            c.retrieval={};
        }
        EntityId remembered;
        if (!annotations.empty() && founding_foundress(a.id) && s.m.founding_meal.target.value) {
            const auto& memory=s.m.founding_meal;
            const AntRef ref{s.world,memory.target};
            if (s.m.now.milliseconds-memory.fed_at.milliseconds >= persistence->window.milliseconds)
                annotations[n]=FoundingCareWake::Expired;
            else if (std::find(opportunities[n].begin(),opportunities[n].end(),ref)==opportunities[n].end())
                annotations[n]=FoundingCareWake::Unavailable;
            else {
                const auto b=*query_ant(ref);
                if (b.stage==LifeStage::Larva && b.colony==a.colony && within_contact(b.position,c.familiar_shelter,s.config) &&
                    (!s.care_locks.contains(b.id) || s.care_locks.at(b.id)==a.id) && can_feed_founding(a.id,b.id,true))
                    remembered=b.id;
                else annotations[n]=FoundingCareWake::Unavailable;
            }
        }
        if (cfg.motion && !brood_candidates.empty()) c.search_remaining=0;
        const bool hatch_cue=wake.payload!=0;
        if (hatch_cue) {
            const EntityId target{wake.payload};
            std::erase_if(brood_candidates,[&](AntRef other) {
                return other.id!=target || std::find(opportunities[n].begin(),opportunities[n].end(),other)==opportunities[n].end() ||
                       query_ant(other)->stage!=LifeStage::Larva || s.care_locks.contains(other.id);
            });
            remembered={}; // The single hatch cue is independent of last-meal preference.
        }
        if (c.carrying_brood) {
            c.target=c.retrieval.target;
            const auto b=*query_ant({s.world,c.target});
            if (within_contact(b.position,c.familiar_shelter,s.config)) c.act=CareAct::PlaceBrood;
            else {
                c.act=CareAct::TransportBrood;
                const PositionM goal{a.position.x+(c.familiar_shelter.x-b.position.x),
                    a.position.y+(c.familiar_shelter.y-b.position.y),a.position.z+(c.familiar_shelter.z-b.position.z)};
                c.destination=care_destination(c,a,goal,b.position);
            }
        } else if (c.returning) {
            if (a.position!=c.familiar_shelter) {
                c.act=CareAct::ReturnToCareShelter;
                c.destination=care_destination(c,a,c.familiar_shelter);
            }
        } else if (revisiting) {
            c.act=CareAct::RevisitBroodSite;
            c.destination=care_destination(c,a,c.retrieval.pickup_site);
        } else if (!hatch_cue && capable && !continuing && a.caste==Caste::Queen && !workers.empty() && draw(cfg.worker_contact_probability)) {
            c.act=CareAct::CloseWorkerContact; c.target=workers[static_cast<std::size_t>(bounded_draw(rng,workers.size()))].id;
        } else if (capable && !brood_candidates.empty()) {
            double memory=0;
            if (c.has_worker_contact) memory=std::max(0.0,1.0-static_cast<double>(s.m.now.milliseconds-c.last_worker_contact.milliseconds)/static_cast<double>(cfg.social_memory_horizon.milliseconds));
            const auto probability=cfg.care_probability*(a.caste==Caste::Queen ? 1-cfg.maximum_inhibition*memory : 1);
            if (continuing || draw(probability)) {
                bool repeat=false;
                if (remembered.value && !continuing && std::any_of(brood_candidates.begin(),brood_candidates.end(),
                        [&](AntRef ref) { return ref.id==remembered; })) {
                    auto repeat_rng=individual_rng(s.seed ^ UINT64_C(0x4631523146454544),a.id,c.decisions);
                    repeat=bounded_draw(repeat_rng,1'000'000)<persistence->repeat_ppm;
                }
                c.target=repeat?remembered:c.retrieval.target.value?c.retrieval.target:
                    brood_candidates[static_cast<std::size_t>(bounded_draw(rng,brood_candidates.size()))].id;
                bool first_meal = false;
                if (s.ecological && s.ecological->first_ration_ppm && founding_foundress(a.id) && !continuing && !repeat) {
                    auto preference=individual_rng(s.seed ^ UINT64_C(0x4649525354524154),a.id,c.decisions);
                    if (bounded_draw(preference,1000000)<s.ecological->first_ration_ppm) {
                        std::uint64_t eligible=0;
                        for (const auto ref : brood_candidates) {
                            const auto larva=*query_ant(ref);
                            if (larva.stage!=LifeStage::Larva || larva.colony!=a.colony ||
                                !within_contact(a.position,larva.position,s.config) ||
                                !within_contact(larva.position,c.familiar_shelter,s.config) ||
                                s.care_locks.contains(ref.id) || !can_feed_founding(a.id,ref.id,true)) continue;
                            const auto receiver=*query_physiology(ref);
                            if (receiver.crop.protein_ug || receiver.tissue_protein_ug!=receiver.initial.tissue_protein_ug) continue;
                            if (!eligible || bounded_draw(preference,eligible+1)==0) c.target=ref.id;
                            ++eligible;
                        }
                        first_meal = eligible!=0;
                    }
                }
                const auto b=*query_ant({s.world,c.target});
                const bool displaced=!within_contact(b.position,c.familiar_shelter,s.config);
                if (cfg.local_retrieval && displaced && c.retrieval.target!=c.target) {
                    c.retrieval={};
                    c.retrieval.target=c.target;
                }
                if (!within_contact(a.position,b.position,s.config)) {
                    c.act=CareAct::ApproachBrood; c.destination=care_destination(c,a,b.position);
                } else if (displaced) {
                    if (cfg.motion) c.act=CareAct::PickUpBrood;
                    else { c.act=CareAct::TransportBrood; c.destination=toward(a.position,c.familiar_shelter,cfg.step_m); }
                } else if (repeat || first_meal) {
                    c.act=CareAct::FeedBrood;
                    if (repeat) annotations[n]=FoundingCareWake::Repeat;
                } else {
                    std::vector<CareAct> acts{CareAct::InspectBrood,CareAct::ArrangeBrood,CareAct::CleanBrood};
                    const auto receiver=query_physiology({s.world,b.id});
                    if (b.stage==LifeStage::Larva && receiver) {
                        const bool available = founding_foundress(a.id) && s.founding_reserves.contains(b.id)
                            ? can_feed_founding(a.id, b.id) : ingredient_min(p.crop,nutrient_demand(*receiver,b.stage)).total_ug() != 0;
                        if (available) acts.push_back(CareAct::FeedBrood);
                    }
                    c.act=acts[static_cast<std::size_t>(bounded_draw(rng,acts.size()))];
                    if (c.act==CareAct::ArrangeBrood) c.destination=toward(b.position,a.position,cfg.arrangement_m);
                }
            }
        } else if (capable && brood_candidates.empty() && !integrated_care(s)) {
            // Local exploratory steps, not a hidden brood-location query.
            const auto direction=bounded_draw(rng,4);
            c.act=CareAct::Walk;
            if (direction<2) c.destination.x+=(direction==0?1:-1)*cfg.step_m;
            else c.destination.z+=(direction==2?1:-1)*cfg.step_m;
            if (cfg.motion) {
                if (!c.search_remaining) c.search_remaining=cfg.motion->search_steps;
                --c.search_remaining;
            }
        }
        if (!cfg.motion && care_motion(c.act)) {
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
        tick.source=wake.id; tick.payload=static_cast<std::uint64_t>(wake.kind);
        if (!annotations.empty()) tick.random_value=static_cast<std::uint64_t>(annotations[n]);
        tx.fact(tick);
        {
            profiling::Scope profile(profiling::Category::CareOpportunities);
            for (auto other:opportunities[n]) observe(tx,wake.actor,wake.id,{ObservationPhase::Opportunity,
                brood(query_ant(other)->stage)?CareAct::InspectBrood:CareAct::CloseWorkerContact,other.id,{},s.m.now,false});
            profiling::record_work(profiling::Category::CareOpportunities,opportunities[n].size());
        }
        if (integrated_care(s) && c.act==CareAct::Inactive) {
            tx.care.set(wake.actor,c);
            interrupt_care(tx,wake.actor,Outcome::InvalidTransition,true);
            continue;
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
    const auto& cfg=*s.care_profile;
    const bool timed=cfg.motion.has_value();
    if (!c.enabled || c.pending!=event.id || !a.alive()) throw std::logic_error("care action ownership");
    WorldEvent tick; tick.kind=FactKind::CareTick; tick.source=event.id; tick.actor=a.id;
    tick.colony=a.colony; tick.stage=a.stage; tick.position=a.position; tick.payload=static_cast<std::uint64_t>(event.kind); tx.fact(tick);
    Outcome outcome=Outcome::Success;
    const bool handling=handles_brood(c.act) || c.act==CareAct::CloseWorkerContact;
    const auto half=care_extent(s,body_half(a.id),c.act);
    const auto from=c.act==CareAct::ArrangeBrood?query_ant({s.world,c.target})->position:a.position;
    if (c.target.value) {
        const auto b=*query_ant({s.world,c.target});
        if (!b.alive()) outcome=Outcome::DeadActor;
        else if ((handles_brood(c.act) || c.act==CareAct::ApproachBrood) && !brood(b.stage)) outcome=Outcome::InvalidStage;
        else if (c.act==CareAct::CloseWorkerContact && (b.stage!=LifeStage::Adult || b.caste!=Caste::Worker)) outcome=Outcome::InvalidStage;
        else if ((b.colony!=a.colony && (!foreign_assay_stage(s,b.stage) || !foreign_assay_act(c.act))) ||
                 !spatially_clear(a.position,b.position) || !surface_care_clear(s,a.position,b.position) ||
                 !within_distance(a.position,b.position,c.act==CareAct::ApproachBrood?cfg.perception_radius_m:s.config.contact_distance_m,
                                  s.config.continuous_spatial_motion)) outcome=Outcome::OutOfReach;
        else if (handling && s.care_locks.contains(c.target) && s.care_locks.at(c.target)!=a.id) outcome=Outcome::DuplicateAction;
        else if (s.config.continuous_spatial_motion && c.carrying_brood &&
                 (!s.care_locks.contains(b.id) || s.care_locks.at(b.id)!=a.id ||
                  !valid_grip(a.position,b.position,c.grip_offset,s.config))) outcome=Outcome::OutOfReach;
        else if (c.act==CareAct::PlaceBrood && (!c.carrying_brood ||
                 !within_contact(b.position,c.familiar_shelter,s.config))) outcome=Outcome::InvalidTransition;
        else if (c.act==CareAct::PickUpBrood || c.act==CareAct::PlaceBrood) {
            if (!clear_care_segment(a.position,a.position,half) || !clear_care_segment(b.position,b.position,half))
                outcome=Outcome::Blocked;
        } else if (timed && c.act==CareAct::TransportBrood) {
            const auto target=carried_position(b.position,a.position,c.destination,c,true,s.config.continuous_spatial_motion);
            if (target==b.position || !clear_care_segment(b.position,target,half)) outcome=Outcome::Blocked;
        }
    }
    if (outcome==Outcome::Success && care_motion(c.act)) {
        if (!clear_care_segment(from,c.destination,half) ||
            ((timed || (cfg.local_retrieval && c.act==CareAct::TransportBrood)) && c.destination==from))
            outcome=Outcome::Blocked;
    }
    if (event.kind==ScheduledEvent::Kind::CareBegin && outcome==Outcome::Success) {
        if (handling) tx.care_locks.set(c.target,a.id);
        c.active=true; c.began_at=s.m.now;
        const auto duration=care_duration(cfg,s.config,a.caste,c.act,from,c.destination);
        ScheduledEvent e; e.actor=a.id; e.kind=ScheduledEvent::Kind::CareEnd; e.issued_at=s.m.now;
        e.key={after(s.m.now,duration.milliseconds),Phase::Resolution,0,0,0}; c.pending=tx.insert(e);
        tx.care.set(a.id,c); auto p=s.physiology.at(a.id); p.behavior_event=c.pending; tx.physiology.set(a.id,p);
        observe(tx,a.id,event.id,{ObservationPhase::Started,c.act,c.target,c.bout,c.began_at,true,c.destination});
        if (c.act!=CareAct::Inactive) set_activity_work(tx,a.id,c.pending);
        return;
    }
    if (c.active && c.act!=CareAct::Inactive) set_activity_work(tx,a.id,{});
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
                const auto target=carried_position(b.position,a.position,c.destination,c,timed,s.config.continuous_spatial_motion);
                if (!clear_care_segment(b.position,target,half)) outcome=Outcome::Blocked;
                else {
                    move(c.target,target,true);
                    if (cfg.local_retrieval && !timed) {
                        if (!ended.retrieval.pickup_bout.value) {
                            ended.retrieval.pickup_bout=c.bout;
                            ended.retrieval.pickup_site=a.position;
                        }
                        if (distance(target,c.familiar_shelter)<=s.config.contact_distance_m) ended.retrieval.target={};
                    }
                }
            }
            if (outcome==Outcome::Success) move(a.id,c.destination,false);
        } else if (c.act==CareAct::PickUpBrood) {
            ended.carrying_brood=true;
            if (s.config.continuous_spatial_motion)
                ended.grip_offset=displacement(query_ant({s.world,c.target})->position,a.position);
            ended.retrieval.pickup_bout=c.bout;
            ended.retrieval.pickup_site=a.position;
        } else if (c.act==CareAct::PlaceBrood) {
            ended.carrying_brood=false;
            ended.grip_offset={};
            ended.retrieval.target={};
        } else if (c.act==CareAct::ArrangeBrood) move(c.target,c.destination,true);
        else if (c.act==CareAct::FeedBrood) {
            ScheduledEvent gift=event; gift.kind=ScheduledEvent::Kind::Trophallaxis; gift.payload=c.target.value;
            gift.requested_ug=s.physiology.at(a.id).config.transfer_limit_ug;
            WorldEvent f; f.kind=FactKind::ActionRejected; f.source=event.id; f.actor=a.id; f.colony=a.colony; f.stage=a.stage; f.position=a.position;
            if (founding_foundress(a.id) && s.founding_reserves.contains(c.target)) resolve_founding_feed(tx,gift,f);
            else resolve_nutrition_action(tx,gift,f);
            outcome=f.outcome; amount=f.transferred; tx.fact(f);
        } else if (c.act==CareAct::CloseWorkerContact) {
            ended.has_worker_contact=true; ended.last_worker_contact=s.m.now; tx.care.set(a.id,ended);
        }
    }
    const bool failed=outcome>Outcome::Partial;
    if (failed || (c.act==CareAct::RevisitBroodSite && c.destination==c.retrieval.pickup_site))
        ended.retrieval={};
    const bool integrated=integrated_care(s);
    if (timed) {
        if (failed) { ended.carrying_brood=false; ended.grip_offset={}; ended.search_remaining=0; }
        if (integrated && (failed || c.act==CareAct::PlaceBrood || c.act==CareAct::InspectBrood ||
            c.act==CareAct::ArrangeBrood || c.act==CareAct::CleanBrood || c.act==CareAct::FeedBrood ||
            c.act==CareAct::CloseWorkerContact)) {
            ended.returning=true; ended.retrieval={};
        }
        if (ended.carrying_brood) tx.care_locks.set(ended.retrieval.target,a.id);
    }
    if (ended.retrieval!=c.retrieval || ended.carrying_brood!=c.carrying_brood || ended.grip_offset!=c.grip_offset ||
        ended.returning!=c.returning || ended.search_remaining!=c.search_remaining) tx.care.set(a.id,ended);
    observe(tx,a.id,event.id,{event.kind==ScheduledEvent::Kind::CareEnd && outcome<=Outcome::Partial?ObservationPhase::Completed:ObservationPhase::Interrupted,
        c.act,c.target,c.bout,c.active?c.began_at:s.m.now,c.active},amount,outcome);
    if (integrated && c.act==CareAct::ReturnToCareShelter && failed) {
        interrupt_care(tx,a.id,Outcome::Blocked,true);
        return;
    }
    auto delay=std::int64_t{1};
    if (timed && !integrated) {
        if (c.act==CareAct::PlaceBrood && !failed) delay=cfg.motion->search_pause.milliseconds;
        else if (c.act!=CareAct::Inactive && !ended.carrying_brood && !ended.retrieval.target.value &&
                 !ended.retrieval.pickup_bout.value && !ended.search_remaining) delay=cfg.decision_interval.milliseconds;
    }
    schedule_care(tx,a.id,after(s.m.now,delay));
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
