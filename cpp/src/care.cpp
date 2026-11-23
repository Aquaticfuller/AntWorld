#include "brood_space.hpp"
#include "physiology_internal.hpp"
#include "social_internal.hpp"
#include "behavior_rng.hpp"
#include "founding_internal.hpp"
#include "ecological_internal.hpp"
#include "worker_motion.hpp"
#include "anatomy.hpp"
#include <queue>
#include <set>
#include <tuple>

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
bool adult_overlap(PositionM a,PositionM b,double width) {
    const auto threshold=width-arithmetic_margin(position_scale(a,b),width);
    return std::abs(a.x-b.x)<threshold && std::abs(a.y-b.y)<threshold && std::abs(a.z-b.z)<threshold;
}
}
bool WorldRuntime::clear_care_segment(PositionM from,PositionM to,std::int32_t half) const {
    const auto& s=*state_;
    return inside(to,s.config) && inside_care_arena(s.care_environment,to) &&
           surface_care_clear(s,from,to) && spatially_clear(from,to,half);
}
bool WorldRuntime::brood_contact(const AntState& adult,const AntState& young) const {
    const auto& s=*state_;
    if (!anatomical_nest(s))
        return within_distance(adult.position,young.position,brood_handling_reach(s),s.config.continuous_spatial_motion);
    if (!brood(young.stage)) return false;
    const auto pose=query_body({s.world,adult.id});
    return pose && mouth_reaches(*pose,young.position,young.stage) &&
        spatially_clear(pose->mouth_m,young.position);
}

PositionM WorldRuntime::brood_approach(const CareState& care,const AntState& adult,const AntState& young) const {
    const auto& s=*state_;
    if (!anatomical_nest(s)) return care_destination(care,adult,young.position);
    return mouth_approach(adult,young.position,young.stage);
}

bool WorldRuntime::mouth_at_supply(const AntState& adult,PositionM target) const {
    const auto body=query_body({state_->world,adult.id});
    return body && supply_in_reach(*body,target) && spatially_clear(body->mouth_m,target);
}

PositionM WorldRuntime::depot_mouth_target(const AntState& adult, PositionM depot) const {
    if (!variable_conditions(*state_)) return depot;
    const auto pose = query_body({state_->world,adult.id});
    if (!pose) return depot;
    const auto target = feeding_patch_point(pose->mouth_m,depot);
    return spatially_clear(depot,target) ? target : depot;
}

PositionM WorldRuntime::nest_meal_step(const AntState& adult, PositionM depot) const {
    return local_founding_feeding(*state_) ? mouth_approach(adult,depot,{},nullptr,true) :
        mouth_approach(adult,depot_mouth_target(adult,depot),{});
}

FoodMass WorldRuntime::local_provisioning_shortfall(const AntState& adult, FoodMass available, bool include_queen) const {
    const auto& s=*state_;
    if (!local_founding_feeding(s) || adult.caste!=Caste::Worker || !local_founding_provisioning(s,adult.id) ||
        !s.social->exchange_enabled) return {};
    FoodMass demand;
    for (const auto ref:query_neighborhood({s.world,adult.id},s.care_profile->perception_radius_m).ants) {
        const auto recipient=*query_ant(ref);
        const bool queen=include_queen && founding_foundress(ref.id) && recipient.stage==LifeStage::Adult;
        if (recipient.colony!=adult.colony || (!queen && recipient.stage!=LifeStage::Larva) ||
            !surface_care_clear(s,adult.position,recipient.position)) continue;
        const auto p=query_physiology(ref);
        const auto reserve=query_founding(ref);
        if (!p || !reserve || p->crop.total_ug()==p->config.crop_capacity_ug) continue;
        const auto need=queen ? founding_resupply_shortfall(s.founding->profile,*p,*reserve,true,p->config.absorption_period) :
            founding_larval_demand(s.founding->profile,*p,*reserve,provision_callow_water(s));
        demand.carbs_ug=std::max(demand.carbs_ug,deficit(need.carbs_ug,available.carbs_ug));
        demand.protein_ug=std::max(demand.protein_ug,deficit(need.protein_ug,available.protein_ug));
        demand.water_ug=std::max(demand.water_ug,deficit(need.water_ug,available.water_ug));
    }
    return demand;
}

bool WorldRuntime::seeks_nest_meal(const AntState& adult,const PhysiologyState& p) const {
    const auto& s=*state_;
    if (!mouth_access(s) || !s.founding || !s.founding->profile.dietary ||
        !s.founding->profile.dietary->local_nest_intake || !s.founding_reserves.contains(adult.id) ||
        p.crop.total_ug()>=p.config.crop_capacity_ug) return false;
    const auto& colony=s.colonies.rows[s.colonies.index.at(adult.colony)];
    const auto mouth=query_body({s.world,adult.id})->mouth_m;
    const auto accessible=depot_mouth_target(adult,colony.nest_position);
    const bool visible=within_distance(mouth,accessible,s.care_profile->perception_radius_m,true) &&
                       spatially_clear(mouth,accessible);
    const auto& reserve=s.founding_reserves.at(adult.id);
    const bool founder=founding_foundress(adult.id);
    if (visible && founder) {
        if (sustained_supply(s) && has_founding_diet(p) && !care_owned(s,adult.id) &&
            !founding_resupply_shortfall(s.founding->profile,p,reserve,true,p.config.absorption_period).total_ug()) {
            // Finish a locally payable ration before topping up a healthy
            // foundress. Topping up each small deficit keeps her at the depot.
            for (const auto ref:query_neighborhood({s.world,adult.id},s.care_profile->perception_radius_m).ants) {
                const auto larva=*query_ant(ref);
                if (larva.stage==LifeStage::Larva && larva.colony==adult.colony &&
                    !s.care_locks.contains(larva.id) && surface_care_clear(s,adult.position,larva.position) &&
                    can_feed_founding(adult.id,larva.id)) return false;
            }
        }
        return foundress_nest_meal(s.founding->profile,p,reserve,colony.nest_food,local_founding_feeding(s)).total_ug()!=0;
    }
    if (founder && local_founding_feeding(s)) {
        // She knows the depot from setup. Check it before the maintenance
        // reserve is exhausted, without reading the stock beyond perception.
        const auto floor=maintenance_cost(s.founding->profile,reserve);
        return dietary_energy(s.founding->profile,p,reserve)<floor.energy ||
            add(p.hydration_ug,p.crop.water_ug)<floor.water;
    }
    if (visible && !founder && local_founding_feeding(s) &&
        ingredient_min(colony.nest_food,local_provisioning_shortfall(adult,founding_gift_supply(s.founding->profile,p),true)).total_ug())
        return true;
    const auto need=founding_resupply_shortfall(s.founding->profile,p,reserve,founder,p.config.absorption_period);
    // Remember the site, not its current inventory. Workers learn it only
    // through their own completed delivery or withdrawal.
    const bool familiar=founder || (s.autonomy.contains(adult.id) && s.autonomy.at(adult.id).knows_depot);
    return visible ? ingredient_min(need,colony.nest_food).total_ug()!=0 : familiar && need.total_ug()!=0;
}

bool WorldRuntime::oral_contact(const AntState& a,const AntState& b) const {
    const auto& s=*state_;
    if (a.stage!=LifeStage::Adult || b.stage!=LifeStage::Adult || a.id==b.id || a.colony!=b.colony) return false;
    const auto donor=*query_body({s.world,a.id}), receiver=*query_body({s.world,b.id});
    return mouths_meet(donor,receiver) && spatially_clear(donor.mouth_m,receiver.mouth_m);
}

std::optional<std::pair<PositionM,EntityId>> WorldRuntime::local_food_offer(const AntState& ant,bool urgent_foundress) const {
    const auto& s=*state_;
    if (!adult_offers(s) || !s.social->exchange_enabled || !s.founding ||
        !s.founding_reserves.contains(ant.id)) return {};
    const auto physiology=*query_physiology({s.world,ant.id});
    const auto supply=founding_gift_supply(s.founding->profile,physiology);
    if (!supply.total_ug()) return {};
    const auto donor=*query_body({s.world,ant.id});
    const auto radius=s.care_profile->perception_radius_m;
    std::optional<std::pair<std::int64_t,EntityId>> nearest;
    std::vector<std::pair<std::int64_t,EntityId>> alternatives;
    for (const auto ref:query_neighborhood({s.world,ant.id},radius).ants) {
        if (urgent_foundress && !founding_foundress(ref.id)) continue;
        const auto peer=*query_ant(ref);
        if (peer.id==ant.id || peer.colony!=ant.colony || peer.stage!=LifeStage::Adult ||
            query_worker_motion(ref)) continue;
        const auto mouth=query_body(ref)->mouth_m;
        if (!within_distance(donor.mouth_m,mouth,radius,true) || !spatially_clear(donor.mouth_m,mouth)) continue;
        const bool touching=oral_contact(ant,peer);
        if (touching || variable_conditions(s)) {
            const auto p=query_physiology(ref);
            if (!p || p->crop.total_ug()>=p->config.crop_capacity_ug ||
                !ingredient_min(contact_offer(s,supply,physiology,*p,peer.stage),signaled_need(*p,peer.stage,true)).total_ug()) continue;
            if (urgent_foundress && !ingredient_min(supply,founding_resupply_shortfall(s.founding->profile,*p,
                *query_founding(ref),true,p->config.absorption_period)).total_ug()) continue;
            if (touching) return std::pair{ant.position,peer.id};
        }
        const auto rank=std::pair{std::int64_t(std::llround(portable_care_distance(donor.mouth_m,mouth)*1'000'000)),peer.id};
        if (crop_exchange(s)) alternatives.push_back(rank);
        else if (!nearest || rank<*nearest) nearest=rank;
    }
    if (nearest) alternatives.push_back(*nearest);
    else std::sort(alternatives.begin(),alternatives.end());
    for (const auto& candidate : alternatives) {
        const auto other=*query_body({s.world,candidate.second});
        const auto next=mouth_approach(ant,other.mouth_m,{},&other);
        if (next!=ant.position) return std::pair{next,candidate.second};
    }
    return {};
}

PositionM WorldRuntime::mouth_approach(const AntState& adult,PositionM target,std::optional<LifeStage> stage,
                                     const BodyPose* partner,bool patch) const {
    const auto& s=*state_;
    const auto pose=*query_body({s.world,adult.id});
    const auto reach=portable_care_distance(adult.position,pose.mouth_m);
    const auto view=geometry_view(s,limits_);
    const auto radius=s.care_profile->perception_radius_m;
    if (!stage && portable_care_distance(adult.position,target)>radius) {
        // Approach a familiar place using only this body's next visible step.
        // Its current stock and any obstacles at the remote site are unknown.
        auto best=adult.position;
        auto remaining=std::llround(portable_care_distance(best,target)*1'000'000);
        const auto examine=[&](double step) {
            for (std::uint8_t dir=1;dir<=8;++dir) {
                auto next=snap_micro(translated(adult.position,scale(body_heading(dir),step)));
                next.y=adult.position.y;
                const auto gap=std::llround(portable_care_distance(next,target)*1'000'000);
                if (gap<remaining && clear_care_segment(adult.position,next,body_half(adult.id)) &&
                    clear_worker_traffic(adult,next,body_half(adult.id))) {
                    remaining=gap;
                    best=next;
                }
            }
        };
        examine(.001);
        if (patch && best==adult.position) examine(.0005);
        return best;
    }
    std::vector<BodyPose> nearby;
    if (!stage) {
        for (const auto ref:query_neighborhood({s.world,adult.id},radius).ants) {
            const auto peer=*query_ant(ref);
            if (ref.id!=adult.id && peer.stage==LifeStage::Adult && spatially_clear(pose.mouth_m,peer.position))
                nearby.push_back(*query_body(ref));
        }
    }
    const auto occupied=[&](const BodyPose& candidate) {
        return std::any_of(nearby.begin(),nearby.end(),[&](const auto& peer){return physical_overlap(candidate,peer);});
    };
    const auto contact_point=[&](const BodyPose& body) {
        if (!patch) return target;
        const auto edge=feeding_patch_point(body.mouth_m,target);
        return continuous_clear(view,target,edge,0) ? edge : target;
    };
    const auto reaches=[&](const BodyPose& body) {
        const auto contact=contact_point(body);
        return (stage ? mouth_reaches(body,contact,*stage) : supply_in_reach(body,contact) &&
            (!partner || supply_in_reach(*partner,body.mouth_m))) && continuous_clear(view,body.mouth_m,contact,0);
    };
    const bool change_level=chamber_return(s) && adult.caste==Caste::Worker &&
        std::abs(adult.position.y-target.y)>.00065;
    std::array<std::pair<std::uint8_t,PositionM>,2*8*9> candidates;
    std::size_t count=0;
    for (std::uint8_t dir=1;dir<=8;++dir) {
        const auto bearing=body_heading(dir);
        const auto examine_stance=[&](PositionM contact) {
            auto stance=snap_micro(translated(contact,scale(bearing,-reach-.00024)));
            for (unsigned level=0;level<(change_level?2u:1u);++level) {
                stance.y=level ? target.y+(stage?.0005:0) : adult.position.y;
                auto candidate=adult;
                candidate.position=stance;
                const auto final=body_pose(candidate,dir,stage?floor_normal:attachment(view,candidate,dir));
                if (reaches(final) && substrate_clear(view,final,stance) && !occupied(final))
                    candidates[count++]={dir,stance};
            }
        };
        examine_stance(target);
        if (patch) {
            // Search both sides of the same funded patch. Project each
            // potential mouth onto it before applying real reach and clearance.
            for (std::uint8_t edge=1;edge<=8;++edge)
                examine_stance(translated(target,scale(body_heading(edge),feeding_patch_radius_m)));
        }
    }
    if (!count) return adult.position;
    const std::span stances(candidates.data(),count);
    struct Node {
        PositionM site, first;
        std::int64_t travelled_um, estimate_um;
        std::uint8_t facing;
        bool initial;
    };
    const bool portable=mouth_access(s);
    const auto closer=[portable](const Node& a,const Node& b) {
        const auto priority=[](const Node& n) {
            return std::tuple{n.estimate_um,n.travelled_um,n.site.x,n.site.z,n.facing,n.site.y};
        };
        const auto left=priority(a),right=priority(b);
        if (left!=right || !portable) return left>right;
        // Two equal-cost paths can reach the same pose via different first
        // movements. A library heap does not preserve their insertion order.
        return std::tie(a.first.x,a.first.z,a.first.y)>std::tie(b.first.x,b.first.z,b.first.y);
    };
    const auto path_length=[](PositionM from,PositionM to) {
        // Rank near-ties below the motion lattice precision in integer micrometres.
        return std::llround(portable_care_distance(from,to)*1'000'000);
    };
    std::priority_queue<Node,std::vector<Node>,decltype(closer)> open(closer,std::vector<Node>(0));
    std::set<std::tuple<double,double,double,std::uint8_t>> seen;
    open.push({adult.position,adult.position,0,0,std::max<std::uint8_t>(1,actor_facing(s,adult.id)),true});
    for (unsigned iteration=0;!open.empty() && iteration<160;++iteration) {
        const auto current=open.top(); open.pop();
        if (!seen.emplace(current.site.x,current.site.y,current.site.z,current.facing).second) continue;
        auto actor=adult;
        actor.position=current.site;
        const auto legal=[&](PositionM to,std::uint8_t heading) {
            if (!nearby.empty()) {
                auto candidate=adult;
                candidate.position=to;
                if (occupied(body_pose(candidate,heading,attachment(view,candidate,heading)))) return false;
            }
            return to!=current.site && portable_care_distance(adult.position,to)<=radius &&
                clear_care_segment(current.site,to,body_half(adult.id)) &&
                anatomy_sweep(view,actor,to,current.facing,heading) &&
                (!current.initial || clear_worker_traffic(adult,to,body_half(adult.id)));
        };
        const auto head=body_pose(actor,current.facing,stage?floor_normal:attachment(view,actor,current.facing));
        if (!current.initial && reaches(head)) return current.first;
        for (const auto& [dir,site]:stances) {
            if (portable_care_distance(current.site,site)<=.002 &&
                movement_facing(current.site,site)==dir && legal(site,dir))
                return current.initial?site:current.first;
        }
        const auto examine_steps=[&](double length) {
            for (std::uint8_t dir=1;dir<=(change_level?10:8);++dir) {
                auto to=snap_micro(translated(current.site,scale(body_heading(dir),length)));
                if (dir<=8) to.y=current.site.y;
                const auto heading=body_travel_heading(view,actor,to,current.facing);
                if (seen.contains({to.x,to.y,to.z,heading}) || !legal(to,heading)) continue;
                const auto spent=current.travelled_um+path_length(current.site,to);
                auto remaining=std::llround(radius*1'000'000);
                for (const auto& stance:stances) remaining=std::min(remaining,path_length(to,stance.second));
                open.push({to,current.initial?to:current.first,spent,spent+remaining,heading,false});
            }
        };
        examine_steps(.001);
        if (patch && current.initial) examine_steps(.0005);
    }
    return adult.position;
}

PositionM WorldRuntime::care_destination(const CareState& care,const AntState& actor,PositionM goal,
                                        std::optional<PositionM> load) const {
    const auto& s=*state_;
    const auto step=s.care_profile->step_m;
    const auto direct=care_toward(s,actor.position,goal,step);
    if (!s.config.continuous_spatial_motion || !s.care_profile->motion || direct==actor.position) return direct;
    const auto half=care_extent(s,body_half(actor.id),care.act);
    const auto clear=[&](PositionM next) {
        const auto held=translated(next,care.grip_offset);
        return clear_care_segment(actor.position,next,half) &&
            (!sealed_chamber(s) || clear_worker_traffic(actor,next,half)) &&
            (!load || (clear_care_segment(*load,held,anatomical_nest(s)?0:half) &&
                       clear_brood_space(care.retrieval.target,*load,held) &&
                       (!anatomical_nest(s) ||
                        clear_brood_space(care.retrieval.target,held,{held.x,next.y-.0005,held.z}))));
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
    if (local_nest_activity(s) && actor.caste==Caste::Worker && care.act==CareAct::ApproachBrood) {
        // Try short diagonal probes in the current local floor plane. Progress
        // to the observed brood must be strict at each accepted segment.
        constexpr double diagonal=0.7071067811865476;
        for (const auto x : {-1,1}) for (const auto z : {-1,1}) {
            const PositionM next{actor.position.x+x*step*diagonal,actor.position.y,
                                 actor.position.z+z*step*diagonal};
            const auto d=portable_care_distance(next,goal);
            if (d<remaining && clear(next)) { best=next; remaining=d; }
        }
    }
    return best;
}
bool WorldRuntime::clear_resting_site(const AntState& ant,PositionM site) const {
    const auto& s=*state_;
    if (worker_motor(s)) return clear_worker_site(ant,site);
    const auto& g=s.geometry->config;
    const auto nest=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
    const auto half=body_half(ant.id);
    const auto q=quantized(site,g);
    if (!q || site==ant.position || !within_contact(nest,site,s.config) || !spatially_clear(site,nest) ||
        !clear_care_segment(ant.position,site,half) ||
        material_at(geometry_view(s,limits_),{q->x,q->y-g.loaded_half_q-1,q->z})==Material::Void) return false;
    const auto width=2*half*g.quantum_m;
    const auto radius=portable_care_distance(ant.position,site)+2*width;
    for (const auto other:query_neighborhood({s.world,ant.id},radius).ants) {
        const auto neighbor=*query_ant(other);
        if (neighbor.stage==LifeStage::Adult && adult_overlap(site,neighbor.position,width)) return false;
    }
    return true;
}
std::optional<PositionM> WorldRuntime::local_resting_site(const AntState& ant) const {
    const auto& s=*state_;
    if (!local_nest_activity(s) || !s.geometry || !integrated_care(s)) return {};
    const auto& g=s.geometry->config;
    const auto origin=mouth_access(s)?nearest_grid_point(ant.position,g,true):quantized(ant.position,g);
    if (!origin || (s.surface && ant.position.y>=s.surface->config.origin_m.y)) return {};
    const auto span=2*body_half(ant.id);
    const auto width=span*g.quantum_m;
    const auto local=query_neighborhood({s.world,ant.id},2*width);
    const auto crowded=std::any_of(local.ants.begin(),local.ants.end(),[&](AntRef ref) {
        const auto other=*query_ant(ref);
        return other.stage==LifeStage::Adult && adult_overlap(ant.position,other.position,width);
    });
    if (!crowded) return {};
    if (worker_motor(s)) {
        const auto reach=s.care_profile->perception_radius_m;
        const auto pitch=std::max(span,1);
        const auto count=std::min(12,static_cast<int>(reach/(pitch*g.quantum_m)));
        std::vector<PositionM> sites(0);
        for (int dx=-count;dx<=count;++dx) for (int dz=-count;dz<=count;++dz) {
            if (!dx && !dz) continue;
            const auto site=physical({origin->x+pitch*dx,origin->y,origin->z+pitch*dz},g);
            if (portable_care_distance(ant.position,site)<=reach) sites.push_back(site);
        }
        auto rank=[&](PositionM site) {
            const auto facing=movement_facing(ant.position,site);
            return std::tuple{portable_care_distance(ant.position,site),turn_ms(actor_facing(s,ant.id),facing),
                              (ant.id.value+facing)%8,site.x,site.z};
        };
        std::sort(sites.begin(),sites.end(),[&](auto a,auto b) { return rank(a)<rank(b); });
        for (const auto site:sites)
            if (clear_worker_site(ant,site)) return site;
        if (sealed_chamber(s))
            for (const auto lift:{pitch,-pitch}) {
                const auto site=physical({origin->x,origin->y+lift,origin->z},g);
                if (clear_worker_site(ant,site)) return site;
            }
        return {};
    }
    constexpr std::array<Cell,8> bearings{{{1,0},{0,1},{-1,0},{0,-1},{1,1},{-1,1},{-1,-1},{1,-1}}};
    // Individual tie breaks keep the same preferred bearings across a save.
    for (std::size_t i=0;i<bearings.size();++i) {
        const auto d=bearings[(i+ant.id.value)%bearings.size()];
        const auto next=physical({origin->x+span*d.x,origin->y,origin->z+span*d.z},g);
        if (clear_resting_site(ant,next)) return next;
    }
    return {};
}
void WorldRuntime::start_resting_move(Transaction& tx,const AntState& ant,PositionM site,ScheduledId source,CareAct act,
                                     EntityId target,std::uint8_t remaining) {
    auto& s=*state_;
    const AntRef ref{s.world,ant.id};
    if (ant.caste==Caste::Worker) change_behavior(tx,ref,IndividualBehavior::Rest,source,true);
    CareState care;
    if (s.care.contains(ant.id)) care=s.care.at(ant.id);
    else {
        care.profile={ant.caste==Caste::Queen?CareContext::FoundingQueen:CareContext::Worker,
                      {s.m.now.milliseconds-ant.born_at.milliseconds}};
        care.familiar_shelter=familiar_brood_site(s,s.colonies.rows[s.colonies.index.at(ant.colony)]);
        care.enrolled_at=s.m.now;
    }
    care.enabled=true; care.act=act; care.destination=site; care.target=target;
    if ((mouth_access(s) && act==CareAct::DepotApproach) ||
        (crop_exchange(s) && act==CareAct::ApproachNestmate)) care.search_remaining=remaining;
    ScheduledEvent e; e.actor=ant.id; e.kind=ScheduledEvent::Kind::CareBegin; e.issued_at=s.m.now;
    e.key={after(s.m.now,1),Phase::Resolution,0,0,0}; care.pending=tx.insert(e); care.bout=care.pending;
    tx.care.set(ant.id,care);
    auto p=s.physiology.at(ant.id); p.behavior_event=care.pending; tx.physiology.set(ant.id,p);
    WorldEvent fact; fact.kind=FactKind::CareProgramChanged; fact.actor=ant.id; fact.colony=ant.colony;
    fact.stage=ant.stage; fact.position=ant.position; fact.payload=1; tx.fact(fact);
    observe(tx,ant.id,source,{ObservationPhase::Selected,care.act,target,care.bout,s.m.now,false,site});
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
std::optional<EnvironmentCareProfile> WorldRuntime::care_environment() const {
    return state_->care_profile ? std::optional{state_->care_environment} : std::nullopt;
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
    const auto nest=familiar_brood_site(s,s.colonies.rows[s.colonies.index.at(a.colony)]);
    if (a.position!=nest && (!worker_motor(s) || !motile_caste(s,a.caste))) {
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
        care.familiar_shelter=familiar_brood_site(s,s.colonies.rows[s.colonies.index.at(a.colony)]);
        care.enrolled_at=s.m.now;
        care.profile={a.caste==Caste::Queen?CareContext::FoundingQueen:CareContext::Worker,
                      {s.m.now.milliseconds-a.born_at.milliseconds}};
    }
    if (a.caste==Caste::Worker) change_behavior(tx,ref,IndividualBehavior::Nurse,source,true);
    care.enabled=true;
    care.returning=a.position!=care.familiar_shelter && (!worker_motor(s) || !motile_caste(s,a.caste));
    if (anatomical_nest(s)) care.search_remaining=s.care_profile->motion->search_steps;
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
    const auto shelter=familiar_brood_site(s,s.colonies.rows[s.colonies.index.at(queen.colony)]);
    if (!queen.alive() || queen.colony!=larva.colony ||
        (!sealed_chamber(s) && (queen.position!=shelter || !within_contact(queen.position,larva.position,s.config))) ||
        s.physiology.at(larva.id).mother!=founder ||
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
    // A relocation invalidates the target's old reservations. Remove this
    // ownership first so lowering the brood cannot interrupt us recursively.
    release_brood_on_floor(tx,c,id,c.pending);
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
void WorldRuntime::commit_brood_position(Transaction& tx,EntityId brood_id,EntityId carrier,
                                          ScheduledId source,PositionM destination) {
    auto& s=*state_;
    const auto i=s.ants.index.at(brood_id);
    auto ant=s.ants.get(i);
    if (ant.position==destination) return;
    index_position(tx,brood_id,ant.position,destination);
    tx.touch_ant(i); ant.position=destination; bump(ant.position_revision); s.ants.set(i,ant);
    WorldEvent f; f.kind=FactKind::BroodMoved; f.actor=brood_id; f.source=source;
    f.colony=ant.colony; f.stage=ant.stage; f.position=destination; f.payload=carrier.value;
    tx.fact(f);
}

void WorldRuntime::release_brood_on_floor(Transaction& tx,const CareState& care,EntityId carrier,ScheduledId source) {
    const auto& s=*state_;
    if (!anatomical_nest(s) || !care.carrying_brood || !s.ants.index.contains(care.retrieval.target)) return;
    const auto b=s.ants.get(s.ants.index.at(care.retrieval.target));
    if (!brood(b.stage)) return;
    const auto a=s.ants.get(s.ants.index.at(carrier));
    const PositionM floor{b.position.x,a.position.y-.0005,b.position.z};
    const auto beneath=translated(floor,{0,-.00065,0});
    if (!spatially_clear(beneath,beneath) && clear_brood_space(b.id,b.position,floor))
        commit_brood_position(tx,b.id,carrier,source,floor);
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
        const auto last_approach=anatomical_nest(s) && c.act==CareAct::ApproachBrood?c.retrieval.target:EntityId{};
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
            if (brood(other.stage) ? brood_contact(a,other) :
                                     within_contact(a.position,other.position,s.config)) {
                if (brood(other.stage) || (other.stage==LifeStage::Adult && other.caste==Caste::Worker))
                    opportunities[n].push_back(ref);
                if (other.stage==LifeStage::Adult && other.caste==Caste::Worker) workers.push_back(ref);
            }
        }
        const auto p=*query_physiology({s.world,a.id});
        // Keep the pre-supply care policy. Once food has arrived, assess
        // affordability over the actual care interval using the ant's reserves.
        const auto reserve=local_founding_feeding(s) && has_founding_diet(p) ?
            query_founding({s.world,a.id}) : std::nullopt;
        const bool capable=reserve ? p.body_energy_nj && p.hydration_ug &&
            !founding_resupply_shortfall(s.founding->profile,p,*reserve,founding_foundress(a.id),cfg.bout_duration).total_ug() :
            p.body_energy_nj>=p.config.energy_capacity_nj/4 && p.hydration_ug>=p.config.hydration_capacity_ug/4;
        bool continuing=false;
        bool revisiting=false;
        const auto can_feed_here=[&](const AntState& brood_ant) {
            if (!sealed_chamber(s) || brood_ant.stage!=LifeStage::Larva || s.care_locks.contains(brood_ant.id)) return false;
            if (founding_foundress(a.id)) return s.founding_reserves.contains(brood_ant.id) && can_feed_founding(a.id,brood_ant.id);
            if (!reserve || !s.social->exchange_enabled || a.colony!=brood_ant.colony) return false;
            const auto receiver=query_physiology({s.world,brood_ant.id});
            const auto brood_reserve=query_founding({s.world,brood_ant.id});
            return receiver && brood_reserve && receiver->crop.total_ug()<receiver->config.crop_capacity_ug &&
                ingredient_min(founding_gift_supply(s.founding->profile,p),
                    founding_larval_demand(s.founding->profile,*receiver,*brood_reserve,provision_callow_water(s))).total_ug();
        };
        if (cfg.local_retrieval && capable && !c.carrying_brood && !c.returning) {
            const auto displaced=[&](AntRef ref) {
                const auto other=s.ants.get(s.ants.index.at(ref.id));
                return ref.id==last_approach || !within_contact(other.position,c.familiar_shelter,s.config);
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
            const bool hungry=sealed_chamber(s) && std::any_of(brood_candidates.begin(),brood_candidates.end(),
                [&](AntRef ref) { return can_feed_here(*query_ant(ref)); });
            if (hungry && !last_approach.value) {
                std::erase_if(brood_candidates,[&](AntRef ref) { return !can_feed_here(*query_ant(ref)); });
                c.retrieval={}; continuing=false;
            } else if (outside) std::erase_if(brood_candidates,[&](AntRef ref) { return !displaced(ref); });
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
        if (cfg.motion && !brood_candidates.empty() && !anatomical_nest(s)) c.search_remaining=0;
        const bool hatch_cue=wake.payload!=0;
        if (hatch_cue) {
            const EntityId target{wake.payload};
            std::erase_if(brood_candidates,[&](AntRef other) {
                return other.id!=target || (!sealed_chamber(s) &&
                       std::find(opportunities[n].begin(),opportunities[n].end(),other)==opportunities[n].end()) ||
                       query_ant(other)->stage!=LifeStage::Larva || s.care_locks.contains(other.id);
            });
            remembered={}; // The single hatch cue is independent of last-meal preference.
        }
        if (c.carrying_brood) {
            c.target=c.retrieval.target;
            const auto b=*query_ant({s.world,c.target});
            if (within_contact(b.position,c.familiar_shelter,s.config) && (!anatomical_nest(s) ||
                clear_brood_space(b.id,b.position,{b.position.x,a.position.y-.0005,b.position.z})))
                c.act=CareAct::PlaceBrood;
            else {
                c.act=CareAct::TransportBrood;
                const PositionM center{a.position.x+(c.familiar_shelter.x-b.position.x),
                    a.position.y+(c.familiar_shelter.y-b.position.y),a.position.z+(c.familiar_shelter.z-b.position.z)};
                const auto berth=sealed_chamber(s)?local_brood_berth(a,b,c.familiar_shelter):std::optional{center};
                if (berth) c.destination=care_destination(c,a,*berth,b.position);
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
            if (reserve && a.caste==Caste::Worker && !continuing) {
                auto feeding=brood_candidates;
                std::erase_if(feeding,[&](AntRef ref) { return !can_feed_here(*query_ant(ref)); });
                if (!feeding.empty()) brood_candidates=std::move(feeding);
            }
            double memory=0;
            if (c.has_worker_contact) memory=std::max(0.0,1.0-static_cast<double>(s.m.now.milliseconds-c.last_worker_contact.milliseconds)/static_cast<double>(cfg.social_memory_horizon.milliseconds));
            const auto probability=cfg.care_probability*(a.caste==Caste::Queen ? 1-cfg.maximum_inhibition*memory : 1);
            if (continuing || draw(probability)) {
                if (protected_founding(s) && !continuing) {
                    auto urgent=brood_candidates;
                    std::erase_if(urgent,[&](AntRef ref) {
                        const auto other=*query_ant(ref);
                        if (!can_feed_here(other)) return true;
                        return !urgent_larval_upkeep(s.founding->profile,*query_physiology(ref),*query_founding(ref));
                    });
                    if (!urgent.empty()) brood_candidates=std::move(urgent);
                }
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
                                !(anatomical_nest(s)?brood_contact(a,larva):within_contact(a.position,larva.position,s.config)) ||
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
                const bool hungry=can_feed_here(b);
                const bool displaced=!hungry && !within_contact(b.position,c.familiar_shelter,s.config);
                if (cfg.local_retrieval && displaced && c.retrieval.target!=c.target) {
                    c.retrieval={};
                    c.retrieval.target=c.target;
                }
                if (!brood_contact(a,b)) {
                    c.act=CareAct::ApproachBrood; c.destination=brood_approach(c,a,b);
                    if (anatomical_nest(s)) c.retrieval.target=b.id;
                } else if (displaced) {
                    if (anatomical_nest(s)) {
                        auto lifted=b;
                        lifted.position.y=a.position.y+.00038;
                        if (clear_brood_space(b.id,b.position,lifted.position) &&
                            local_brood_berth(a,lifted,c.familiar_shelter)) c.act=CareAct::PickUpBrood;
                        else c.act=CareAct::CleanBrood;
                    } else if (cfg.motion) c.act=CareAct::PickUpBrood;
                    else { c.act=CareAct::TransportBrood; c.destination=toward(a.position,c.familiar_shelter,cfg.step_m); }
                } else if (repeat || first_meal || hungry) {
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
                    if (c.act==CareAct::ArrangeBrood && anatomical_nest(s)) c.act=CareAct::InspectBrood;
                    if (c.act==CareAct::ArrangeBrood) {
                        if (bounded_brood_space(s)) {
                            if (const auto site=arrange_brood_site(b,c.familiar_shelter)) c.destination=*site;
                            else c.act=CareAct::InspectBrood;
                        } else c.destination=toward(b.position,a.position,cfg.arrangement_m);
                    }
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
        if (anatomical_nest(s) && (c.act==CareAct::ApproachBrood || c.act==CareAct::TransportBrood ||
                                  c.act==CareAct::ReturnToCareShelter)) {
            if (c.search_remaining) --c.search_remaining;
            else {
                c.act=CareAct::Inactive;
                c.destination=a.position;
                c.target={};
            }
        }
        if (anatomical_nest(s) && !c.carrying_brood && c.act!=CareAct::ApproachBrood &&
            c.act!=CareAct::PickUpBrood && c.act!=CareAct::RevisitBroodSite) c.retrieval={};
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
                 !(handles_brood(c.act)?(c.carrying_brood && anatomical_nest(s) ?
                    valid_grip(a.position,b.position,c.grip_offset,s.config,true):brood_contact(a,b)):
                    within_distance(a.position,b.position,(c.act==CareAct::ApproachBrood || c.act==CareAct::ApproachNestmate ||
                                  c.act==CareAct::YieldToCarrier)?cfg.perception_radius_m:
                                  s.config.contact_distance_m,s.config.continuous_spatial_motion))) outcome=Outcome::OutOfReach;
        else if (handling && s.care_locks.contains(c.target) && s.care_locks.at(c.target)!=a.id) outcome=Outcome::DuplicateAction;
        else if (s.config.continuous_spatial_motion && c.carrying_brood &&
                 (!s.care_locks.contains(b.id) || s.care_locks.at(b.id)!=a.id ||
                  !valid_grip(a.position,b.position,c.grip_offset,s.config,anatomical_nest(s)))) outcome=Outcome::OutOfReach;
        else if (c.act==CareAct::PlaceBrood && (!c.carrying_brood ||
                 !within_contact(b.position,c.familiar_shelter,s.config))) outcome=Outcome::InvalidTransition;
        else if (c.act==CareAct::PickUpBrood || c.act==CareAct::PlaceBrood) {
            if (!clear_care_segment(a.position,a.position,half) || !clear_care_segment(b.position,b.position,anatomical_nest(s)?0:half))
                outcome=Outcome::Blocked;
            if (anatomical_nest(s)) {
                const auto y=c.act==CareAct::PickUpBrood?a.position.y+.00038:a.position.y-.0005;
                if (!clear_brood_space(b.id,b.position,{b.position.x,y,b.position.z})) outcome=Outcome::Blocked;
            }
        } else if (timed && c.act==CareAct::TransportBrood) {
            const auto target=carried_position(b.position,a.position,c.destination,c,true,s.config.continuous_spatial_motion);
            if (target==b.position || !clear_care_segment(b.position,target,anatomical_nest(s)?0:half) ||
                !clear_brood_space(b.id,b.position,target)) outcome=Outcome::Blocked;
        }
    }
    if (outcome==Outcome::Success && care_motion(c.act)) {
        if (!clear_care_segment(from,c.destination,half) ||
            (motile_caste(s,a.caste) && c.act!=CareAct::ArrangeBrood && !clear_worker_traffic(a,c.destination,half)) ||
            ((c.act==CareAct::NestReposition || c.act==CareAct::EntrancePatrol) && !clear_resting_site(a,c.destination)) ||
            (c.act==CareAct::DepotApproach && !(mouth_access(s) && c.search_remaining) &&
             !clear_worker_site(a,c.destination,true)) ||
            (c.act==CareAct::ArrangeBrood && !clear_brood_space(c.target,from,c.destination)) ||
            ((timed || (cfg.local_retrieval && c.act==CareAct::TransportBrood)) && c.destination==from))
            outcome=Outcome::Blocked;
    }
    if (event.kind==ScheduledEvent::Kind::CareBegin && outcome==Outcome::Success) {
        if (handling) tx.care_locks.set(c.target,a.id);
        c.active=true; c.began_at=s.m.now;
        auto duration=care_duration(cfg,s.config,a.caste,c.act,from,c.destination,portable_care(s));
        if (motile_caste(s,a.caste) && care_motion(c.act) && c.act!=CareAct::ArrangeBrood)
            duration=with_worker_turn(s,a.id,from,c.destination,duration);
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
    const auto move=[&](EntityId id,PositionM destination,bool carried) {
        if (carried) { commit_brood_position(tx,id,a.id,event.id,destination); return; }
        const auto i=s.ants.index.at(id); auto ant=s.ants.get(i);
        if (ant.position==destination) return;
        index_position(tx,id,ant.position,destination); tx.touch_ant(i);
        ant.position=destination; bump(ant.position_revision); s.ants.set(i,ant);
        WorldEvent f; f.kind=FactKind::Moved; f.actor=id; f.source=event.id;
        f.colony=ant.colony; f.stage=ant.stage; f.position=destination;
        record_worker_move(tx,f,a.position,c.began_at,true);
        tx.fact(f);
    };
    if (event.kind==ScheduledEvent::Kind::CareEnd && outcome==Outcome::Success) {
        if (care_motion(c.act) && c.act!=CareAct::ArrangeBrood) {
            if (c.act==CareAct::TransportBrood) {
                const auto b=*query_ant({s.world,c.target});
                const auto target=carried_position(b.position,a.position,c.destination,c,timed,s.config.continuous_spatial_motion);
                if (!clear_care_segment(b.position,target,anatomical_nest(s)?0:half) ||
                    (anatomical_nest(s) && !clear_brood_space(b.id,b.position,target))) outcome=Outcome::Blocked;
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
            if (anatomical_nest(s)) {
                const auto b=*query_ant({s.world,c.target});
                move(b.id,{b.position.x,a.position.y+.00038,b.position.z},true);
            }
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
            ended.returning=!anatomical_nest(s); ended.retrieval={};
        }
        if (ended.carrying_brood) tx.care_locks.set(ended.retrieval.target,a.id);
    }
    if (ended.retrieval!=c.retrieval || ended.carrying_brood!=c.carrying_brood || ended.grip_offset!=c.grip_offset ||
        ended.returning!=c.returning || ended.search_remaining!=c.search_remaining) tx.care.set(a.id,ended);
    observe(tx,a.id,event.id,{event.kind==ScheduledEvent::Kind::CareEnd && outcome<=Outcome::Partial?ObservationPhase::Completed:ObservationPhase::Interrupted,
        c.act,c.target,c.bout,c.active?c.began_at:s.m.now,c.active},amount,outcome);
    if (failed) release_brood_on_floor(tx,c,a.id,event.id);
    if (anatomical_nest(s) && c.act==CareAct::PlaceBrood && event.kind==ScheduledEvent::Kind::CareEnd && outcome==Outcome::Success) {
        const auto b=*query_ant({s.world,c.target});
        move(b.id,{b.position.x,a.position.y-.0005,b.position.z},true);
    }
    const bool local_work=worker_motor(s) && integrated && a.caste==Caste::Worker && !ended.carrying_brood &&
        (failed || c.act==CareAct::PlaceBrood || c.act==CareAct::InspectBrood ||
         c.act==CareAct::ArrangeBrood || c.act==CareAct::CleanBrood || c.act==CareAct::FeedBrood);
    if (anatomical_nest(s) && a.caste==Caste::Queen && !ended.carrying_brood &&
        (failed || c.act==CareAct::PlaceBrood || c.act==CareAct::InspectBrood ||
         c.act==CareAct::CleanBrood || c.act==CareAct::FeedBrood)) {
        interrupt_care(tx,a.id,outcome,true);
        return;
    }
    if (c.act==CareAct::DepotApproach) {
        interrupt_care(tx,a.id,outcome,true);
        if (!failed && c.search_remaining && mouth_access(s)) {
            const auto arrived=*query_ant({s.world,a.id});
            if (sustained_supply(s)) {
                const auto p=*query_physiology({s.world,arrived.id});
                if (const auto wick=local_wick_contact(arrived,p)) {
                    if (mouth_at_supply(arrived,depot_mouth_target(arrived,*wick))) {
                        draw_founding_water(tx,event,arrived);
                        return;
                    }
                    if (c.search_remaining>1) {
                        const auto next=mouth_approach(arrived,*wick,{},nullptr,true);
                        if (next!=arrived.position) {
                            start_resting_move(tx,arrived,next,event.id,c.act,{},c.search_remaining-1);
                            return;
                        }
                    }
                }
            }
            const auto depot=s.colonies.rows[s.colonies.index.at(a.colony)].nest_position;
            if (seeks_nest_meal(arrived,*query_physiology({s.world,a.id}))) {
                if (mouth_at_supply(arrived,depot_mouth_target(arrived,depot))) {
                    if (a.caste==Caste::Worker) change_behavior(tx,{s.world,a.id},IndividualBehavior::Rest,event.id);
                    else if (local_founding_feeding(s) && founding_foundress(a.id)) draw_foundress_meal(tx,arrived,event.id);
                } else if (c.search_remaining>1) {
                    const auto next=nest_meal_step(arrived,depot);
                    if (next!=arrived.position)
                        start_resting_move(tx,arrived,next,event.id,c.act,{},c.search_remaining-1);
                }
            }
            return;
        }
        // Reassess upon contact. A failed trip waits for the regular decision.
        if (!failed && a.caste==Caste::Worker && s.autonomy.at(a.id).enabled) {
            auto autonomy=s.autonomy.at(a.id);
            if (s.queue_index.contains(autonomy.wake)) tx.remove(s.queue_index.at(autonomy.wake));
            autonomy.wake={};
            tx.autonomy.set(a.id,autonomy);
            const auto& arrived=s.ants.get(s.ants.index.at(a.id));
            const bool still_approaching=s.ecological && s.ecological->founding_habitat && !at_foraging_home(arrived);
            schedule_autonomy(tx,a.id,{still_approaching?0:1});
        }
        return;
    }
    if (c.act==CareAct::ApproachNestmate) {
        interrupt_care(tx,a.id,outcome,true);
        const AntRef self{s.world,a.id}, other{s.world,c.target};
        const auto target=query_ant(other);
        const auto worker=*query_ant(self);
        const bool oral=adult_offers(s) && target && target->stage==LifeStage::Adult;
        const bool reached=!failed && target && target->alive() && target->colony==a.colony &&
            (oral ? oral_contact(worker,*target) && !query_worker_motion(other) :
            within_contact(worker.position,target->position,s.config) && spatially_clear(worker.position,target->position));
        if (crop_exchange(s) && !failed && !reached && oral && target->alive() && c.search_remaining &&
            !query_worker_motion(other)) {
            const auto next=local_food_offer(worker);
            if (next && next->second==c.target && next->first!=worker.position) {
                start_resting_move(tx,worker,next->first,event.id,CareAct::ApproachNestmate,c.target,
                                   static_cast<std::uint8_t>(c.search_remaining-1));
                return;
            }
        }
        if (reached && brood(target->stage) && local_care_available(self)) start_autonomous_care(tx,self,event.id);
        else {
            const auto receiver=reached?query_physiology(other):std::nullopt;
            const auto& p=s.physiology.at(a.id);
            const auto available=oral?founding_gift_supply(s.founding->profile,p):p.crop;
            const bool offer=s.social->exchange_enabled && receiver &&
                receiver->crop.total_ug()<receiver->config.crop_capacity_ug &&
                ingredient_min(contact_offer(s,available,p,*receiver,target->stage),
                               signaled_need(*receiver,target->stage,s.long_term!=nullptr)).total_ug();
            change_behavior(tx,self,offer?IndividualBehavior::Nurse:IndividualBehavior::Rest,event.id,false,
                            offer && oral ? other.id : EntityId{});
        }
        return;
    }
    if (c.act==CareAct::NestReposition || c.act==CareAct::YieldToCarrier || c.act==CareAct::EntrancePatrol || local_work) {
        interrupt_care(tx,a.id,outcome,true);
        if (a.caste==Caste::Worker) change_behavior(tx,{s.world,a.id},IndividualBehavior::Rest,event.id);
        return;
    }
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
