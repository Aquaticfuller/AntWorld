#include "care_internal.hpp"
#include "social_internal.hpp"
#include "worker_motion.hpp"
#include "anatomy.hpp"
#include "spatial_navigation.hpp"
#include <set>

namespace antworld {
using namespace detail;
namespace {
constexpr std::array<Cell,8> horizontal_steps{{{1,0},{1,1},{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1}}};

bool physically_overlaps(PositionM a,PositionM b,double width) {
    const auto limit=width-arithmetic_margin(position_scale(a,b),width);
    return std::abs(a.x-b.x)<limit && std::abs(a.y-b.y)<limit && std::abs(a.z-b.z)<limit;
}

bool sweeps_body(PositionM from,PositionM to,PositionM peer_from,PositionM peer_to,double width) {
    const std::array a{from.x,from.y,from.z}, b{to.x,to.y,to.z};
    const std::array c{peer_from.x,peer_from.y,peer_from.z}, d{peer_to.x,peer_to.y,peer_to.z};
    const auto extent = width-arithmetic_margin(std::max(position_scale(from,to),position_scale(peer_from,peer_to)),width);
    double enter=0, exit=1;
    for (std::size_t i=0;i<a.size();++i) {
        const auto low=std::min(c[i],d[i])-extent;
        const auto high=std::max(c[i],d[i])+extent;
        const auto delta=b[i]-a[i];
        if (delta==0) {
            if (a[i]<=low || a[i]>=high) return false;
            continue;
        }
        const double first=(low-a[i])/delta;
        const double last=(high-a[i])/delta;
        enter=std::max(enter,std::min(first,last));
        exit=std::min(exit,std::max(first,last));
        if (enter>=exit) return false;
    }
    return true;
}

} // namespace

bool detail::anatomical_sweep_hits(const BodyPose& mover,PositionM to,const BodyPose& peer) {
    auto destination=mover;
    destination.center_m=to;
    if (physical_overlap(destination,peer)) return true;
    const auto delta=displacement(to,mover.center_m);
    for (const auto& part:mover.segments) for (const auto& obstacle:peer.segments) {
        const auto a=lobe_center(mover,part), b=lobe_center(peer,obstacle);
        const auto bound=translated(lobe_extents(mover,part),lobe_extents(peer,obstacle));
        // Permit separation from an existing overlap, such as at eclosion.
        if (std::abs(a.x-b.x)<bound.x && std::abs(a.y-b.y)<bound.y && std::abs(a.z-b.z)<bound.z &&
            dot(delta,displacement(a,b))>=0) continue;
        const auto normalized=[&](PositionM p){return PositionM{p.x/bound.x,p.y/bound.y,p.z/bound.z};};
        if (sweeps_body(normalized(a),normalized(translated(a,delta)),normalized(b),normalized(b),1)) return true;
    }
    return false;
}

namespace {
bool leaving_overlap(PositionM from,PositionM to,PositionM stationary,double width) {
    return physically_overlaps(from,stationary,width) && !physically_overlaps(to,stationary,width) &&
           (to.x-from.x)*(from.x-stationary.x)>=0 && (to.y-from.y)*(from.y-stationary.y)>=0 &&
           (to.z-from.z)*(from.z-stationary.z)>=0;
}

bool supported_wall_segment(const GeometryView& view,PointQ from,PointQ to,int reach) {
    const std::array origin{from.x,from.y,from.z};
    const std::array delta{to.x-from.x,to.y-from.y,to.z-from.z};
    const auto steps=std::max({std::abs(delta[0]),std::abs(delta[1]),std::abs(delta[2])});
    if (!steps || steps>32) return false;
    for (std::size_t axis=0;axis<delta.size();++axis) {
        if (delta[axis]) continue; // The body must keep the same support face.
        for (const int face:{-reach-1,reach}) {
            if (axis==1 && face<0) continue; // Floor movement has its own rule.
            bool attached=true;
            for (int step=0;step<=steps && attached;++step) {
                auto p=origin;
                for (std::size_t i=0;i<p.size();++i) p[i]+=delta[i]*step/steps;
                p[axis]+=face;
                attached=material_at(view,{p[0],p[1],p[2]})!=Material::Void;
            }
            if (attached) return true;
        }
    }
    return false;
}
}

bool detail::center_sweep_clears(PositionM from, PositionM to, PositionM stationary, double width) {
    return leaving_overlap(from,to,stationary,width) ||
           !sweeps_body(from,to,stationary,stationary,width);
}

bool detail::anatomy_turn_clears(const BodyPose& sweep,std::uint8_t previous,std::uint8_t next,const BodyPose& other) {
    if (previous==next || previous>8 || next>8) return true;
    const int clockwise=(int(next)-previous+8)%8;
    const int increment=clockwise<=4 ? 1 : -1;
    auto stance=sweep;
    do {
        previous=static_cast<std::uint8_t>((int(previous)+increment+7)%8+1);
        stance.forward=tangent(body_heading(previous),stance.up);
        if (physical_overlap(stance,other)) return false;
    } while (previous!=next);
    return true;
}

std::uint8_t detail::body_travel_heading(const GeometryView& view,const AntState& ant,
                                        PositionM to,std::uint8_t previous,bool alignment,double alignment_m) {
    // ENGINEERING_FIXTURE. Tiny stance corrections can translate sideways
    // without a full body turn. The same swept pose is used at commit/replay.
    if (alignment && previous>=1 && previous<=8 && to.y==ant.position.y &&
        within_distance(ant.position,to,alignment_m,true) && anatomy_sweep(view,ant,to,previous,previous))
        return previous;
    const auto next=movement_facing(ant.position,to);
    // An ant beside a wall may take a short backward or lateral step before
    // there is enough space to turn its longitudinal body.
    if (anatomy_sweep(view,ant,to,previous,next)) return next;
    if (previous!=next && anatomy_sweep(view,ant,to,previous,previous)) return previous;
    if (to.y!=ant.position.y) {
        // Near the floor or ceiling a vertical body can run out of turning
        // room. Use a tangential body on the same wall before the next step.
        for (const auto tangent:std::array<std::uint8_t,4>{1,3,5,7})
            if (anatomy_sweep(view,ant,to,previous,tangent)) return tangent;
    }
    return next;
}

std::optional<BodyPose> WorldRuntime::query_body(AntRef ref) const {
    const auto& s=*state_;
    const auto ant=query_ant(ref);
    if (!anatomical_nest(s) || !s.geometry || !ant || !ant->alive()) return {};
    const auto facing=actor_facing(s,ant->id);
    return body_pose(*ant,facing,attachment(geometry_view(s,limits_),*ant,facing));
}

bool WorldRuntime::clear_body_motion(const AntState& ant,PositionM to,bool alignment_probe) const {
    const auto& s=*state_;
    const auto facing=actor_facing(s,ant.id);
    return !anatomical_nest(s) || (inside(to,s.config) &&
        anatomy_sweep(geometry_view(s,limits_),ant,to,facing,
                      to==ant.position?facing:segment_heading(s,ant.id,ant.position,to,alignment_probe)));
}

std::optional<std::uint8_t> WorldRuntime::emergence_heading(const AntState& pupa) const {
    const auto& s=*state_;
    if (s.care_locks.contains(pupa.id) && s.care.at(s.care_locks.at(pupa.id)).carrying_brood) return {};
    auto adult=pupa;
    adult.stage=LifeStage::Adult;
    const auto view=geometry_view(s,limits_);
    return emergence_pose(view,adult,sustained_supply(s) && s.autonomy.contains(adult.id),[&](const BodyPose& pose) {
        for (const auto ref:query_neighborhood({s.world,pupa.id},.008).ants) {
            if (query_ant(ref)->stage==LifeStage::Adult && physical_overlap(pose,*query_body(ref))) return true;
        }
        return false;
    });
}

std::optional<WorkerMotion> WorldRuntime::query_worker_motion(AntRef ref) const {
    const auto& s=*state_;
    if (!worker_motor(s)) return {};
    const auto ant=query_ant(ref);
    if (!ant || ant->stage!=LifeStage::Adult || !motile_caste(s,ant->caste) ||
        !s.autonomy.contains(ref.id)) return {};
    ScheduledId id;
    PositionM to;
    if (care_owned(s,ref.id)) {
        const auto& c=s.care.at(ref.id);
        if (!c.active || !care_motion(c.act) || c.act==CareAct::ArrangeBrood) return {};
        id=c.pending;
        to=c.destination;
    } else if (s.foragers.contains(ref.id) && s.foragers.at(ref.id).enabled) id=s.foragers.at(ref.id).action;
    else if (s.excavators.contains(ref.id) && s.excavators.at(ref.id).enabled) id=s.excavators.at(ref.id).action;
    if (!s.queue_index.contains(id)) return {};
    const auto& event=s.queue.at(s.queue_index.at(id));
    if (event.kind==ScheduledEvent::Kind::Move) to=event.destination;
    else if (event.kind!=ScheduledEvent::Kind::CareEnd) return {};
    if (to==ant->position) return {};
    if (local_traffic(s) && !spatially_clear(ant->position,to,body_half(ref.id))) return {};
    if (!clear_body_motion(*ant,to)) return {};
    const auto previous=actor_facing(s,ref.id);
    const auto heading=segment_heading(s,ref.id,ant->position,to);
    return WorkerMotion{id,ant->position,to,event.issued_at,after(event.issued_at,turn_ms(previous,heading)),
                        event.key.time,previous,heading};
}

void WorldRuntime::record_worker_move(Transaction& tx,WorldEvent& fact,PositionM from,SimTime began,bool autonomous) {
    auto& s=*state_;
    if (!worker_motor(s) || from==fact.position || !s.autonomy.contains(fact.actor) ||
        !motile_caste(s,s.ants.get(s.ants.index.at(fact.actor)).caste)) return;
    auto a=s.autonomy.at(fact.actor);
    const auto facing=segment_heading(s,fact.actor,from,fact.position);
    if (autonomous) {
        const auto elapsed=s.m.now.milliseconds-began.milliseconds;
        const auto turn=turn_ms(a.facing,facing);
        if (elapsed<=turn || elapsed>UINT32_MAX) throw std::logic_error("worker motor exceeded its segment clock");
        fact.random_value=motion_evidence(elapsed,turn,anatomical_nest(s)?facing:0);
    }
    a.facing=facing;
    tx.autonomy.set(fact.actor,a);
}

bool WorldRuntime::clear_worker_traffic(const AntState& ant,PositionM to,std::int32_t half,bool include_plans,bool alignment_probe) const {
    const auto& s=*state_;
    if (!local_traffic(s) || !s.geometry || ant.stage!=LifeStage::Adult) return true;
    if (!clear_body_motion(ant,to,alignment_probe)) return false;
    const auto quantum=s.geometry->config.quantum_m;
    const bool anatomical=anatomical_nest(s);
    const bool floor_precision=anatomical && uses_floor_body_clearance(s,ant,to,half);
    const auto reach=distance(ant.position,to)+(floor_precision?.009:ant.caste==Caste::Queen?.007:.0055);
    const auto previous=std::max<std::uint8_t>(1,actor_facing(s,ant.id));
    auto heading=previous;
    std::optional<BodyPose> mover;
    if (anatomical) {
        heading=to==ant.position?actor_facing(s,ant.id):segment_heading(s,ant.id,ant.position,to,alignment_probe);
        mover=body_pose(ant,heading,attachment(geometry_view(s,limits_),ant,heading));
    }
    for (const auto& row:s.ants.identities) {
        if (row.id==ant.id) continue;
        const auto other=s.ants.get(s.ants.index.at(row.id));
        if (other.stage!=LifeStage::Adult) continue;
        const bool anatomically_near=mover && distance(ant.position,other.position)<=reach;
        if (anatomically_near) {
            const auto obstacle=*query_body({s.world,other.id});
            if (anatomical_sweep_hits(*mover,to,obstacle) ||
                (floor_precision && heading && !anatomy_turn_clears(*mover,previous,heading,obstacle))) return false;
        }
        const auto other_half=body_half(other.id);
        const auto plan=include_plans?query_worker_motion({s.world,other.id}):std::nullopt;
        if (!plan && floor_precision && other.position.y==ant.position.y &&
            uses_floor_body_clearance(s,other,other.position,other_half)) continue;
        const auto width=(half+other_half)*quantum;
        if (!plan && leaving_overlap(ant.position,to,other.position,width)) continue;
        if (sweeps_body(ant.position,to,other.position,plan?plan->to:other.position,width)) return false;
    }
    return true;
}

std::optional<std::pair<PositionM,EntityId>> WorldRuntime::local_contact_step(const AntState& ant) const {
    const auto& s=*state_;
    if (!local_traffic(s) || !s.geometry || !integrated_care(s) ||
        (s.surface && ant.position.y>=s.surface->config.origin_m.y)) return {};
    const auto& g=s.geometry->config;
    // Quantize the search origin only. Check every proposed sweep from the
    // worker's actual micron-scale berth before committing any movement.
    const auto origin=mouth_access(s)?nearest_grid_point(ant.position,g,true):quantized(ant.position,g);
    if (!origin) return {};
    const auto reach=s.care_profile->perception_radius_m;
    const auto crop=s.physiology.at(ant.id).crop;
    std::optional<std::pair<PositionM,EntityId>> best;
    double best_score=0;
    const bool portable=mouth_access(s);
    const auto length_m=portable?portable_care_distance:distance;
    for (const auto ref:query_neighborhood({s.world,ant.id},reach).ants) {
        const auto target=*query_ant(ref);
        if (adult_offers(s) && target.stage==LifeStage::Adult) continue;
        if (!target.alive() || target.colony!=ant.colony || within_contact(ant.position,target.position,s.config)) continue;
        const auto receiver=query_physiology(ref);
        const bool donation=s.social->exchange_enabled && receiver && receiver->crop.total_ug()<receiver->config.crop_capacity_ug &&
            ingredient_min(crop,signaled_need(*receiver,target.stage,s.long_term!=nullptr)).total_ug();
        if (!brood(target.stage) && !donation) continue;
        const auto before=length_m(ant.position,target.position);
        for (int length=1;length<=3;++length) for (const auto direction:horizontal_steps) {
            const auto to=physical({origin->x+direction.x*length,origin->y,origin->z+direction.z*length},g);
            const auto progress=before-length_m(to,target.position);
            if (progress<=0.25*g.quantum_m || !spatially_clear(to,target.position)) continue;
            const auto travel=length_m(ant.position,to);
            const auto turn=turn_ms(actor_facing(s,ant.id),movement_facing(ant.position,to));
            const auto gain=progress-0.2*travel-static_cast<double>(turn)*g.quantum_m/1000;
            // Different libm implementations can split a symmetric contact
            // by one ulp. Rank below one micrometre by identity and position.
            const auto score=portable?static_cast<double>(std::llround(gain*1'000'000)):gain;
            const bool tied=portable && best && score==best_score &&
                std::tie(target.id,to.x,to.y,to.z)<std::tie(best->second,best->first.x,best->first.y,best->first.z);
            if ((score>best_score || tied) && clear_worker_site(ant,to)) {
                best_score=score;
                best=std::pair{to,target.id};
            }
        }
    }
    return best;
}

std::optional<std::pair<PositionM,EntityId>> WorldRuntime::carrier_yield_step(const AntState& ant) const {
    const auto& s=*state_;
    if (!s.geometry || !s.surface || !integrated_care(s) || ant.position.y>=s.surface->config.origin_m.y) return {};
    const auto& g=s.geometry->config;
    const auto origin=nearest_grid_point(ant.position,g);
    if (!origin) return {};
    const auto reach=s.care_profile->perception_radius_m;
    const auto half=body_half(ant.id);
    for (const auto ref:query_neighborhood({s.world,ant.id},reach).ants) {
        const auto other=*query_ant(ref);
        const auto link=s.connectors.find(other.id);
        const auto forage=s.foragers.find(other.id);
        const bool crop_load=worked_exit(s) && forage!=s.foragers.end() && forage->second.last_collected.value &&
            s.physiology.contains(other.id) && s.physiology.at(other.id).crop.carbs_ug;
        if (other.colony!=ant.colony || other.stage!=LifeStage::Adult || (!other.carried_food.total_ug() && !crop_load) ||
            link==s.connectors.end() || !link->second.returning || !link->second.cursor ||
            forage==s.foragers.end() || !forage->second.enabled || forage->second.mode!=BehaviorMode::Rest ||
            !spatially_clear(ant.position,other.position)) continue;
        const auto next=link->second.points[link->second.cursor-1];
        const auto width=(half+body_half(other.id))*g.quantum_m;
        const auto view=geometry_view(s,limits_);
        std::optional<BodyPose> carrier;
        if (sustained_supply(s)) {
            const auto facing=segment_heading(s,other.id,other.position,next);
            carrier=body_pose(other,facing,attachment(view,other,facing));
        }
        if (!sweeps_body(other.position,next,ant.position,ant.position,width) &&
            !(carrier && anatomical_sweep_hits(*carrier,next,*query_body({s.world,ant.id})))) continue;
        // The worker can vacate a nearby blocked path. Active work keeps its lease.
        const auto steps=carrier?g.reach_q:4;
        for (int length=1;length<=steps;++length) for (const auto direction:horizontal_steps) {
            const auto to=physical({origin->x+direction.x*length,origin->y,origin->z+direction.z*length},g);
            if (sweeps_body(other.position,next,to,to,width) || !clear_worker_site(ant,to)) continue;
            if (carrier) {
                auto repositioned=ant;
                repositioned.position=to;
                const auto facing=segment_heading(s,ant.id,ant.position,to);
                if (anatomical_sweep_hits(*carrier,next,body_pose(repositioned,facing,attachment(view,repositioned,facing))))
                    continue;
            }
            return std::pair{to,other.id};
        }
    }
    return {};
}

std::optional<PositionM> WorldRuntime::entrance_patrol_step(const AntState& ant) const {
    const auto& s=*state_;
    if (!s.care_profile || !s.geometry || !s.surface) return {};
    const auto& g=s.geometry->config;
    const auto q=nearest_grid_point(ant.position,g);
    const auto level=surface_level(s);
    const auto depot=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
    if (!q || !level || ant.position.y!=depot.y || !within_contact(ant.position,depot,s.config)) return {};
    const PositionM top{depot.x,physical({0,*level,0},g).y,depot.z};
    if (!within_distance(ant.position,top,s.care_profile->perception_radius_m,true) ||
        !spatially_clear(ant.position,top)) return {};
    const auto local=query_neighborhood({s.world,ant.id},s.care_profile->perception_radius_m);
    for (const auto peer:local.ants) {
        const auto other=*query_ant(peer);
        if (other.colony==ant.colony && inspecting_entrance(other)) return {};
    }
    const auto adult_peer=std::any_of(local.ants.begin(),local.ants.end(),[&](AntRef peer) {
        const auto other=*query_ant(peer);
        return other.colony==ant.colony && other.stage==LifeStage::Adult && other.caste==Caste::Worker;
    });
    if (!adult_peer) return {};
    const auto offset=s.autonomy.at(ant.id).decisions%horizontal_steps.size();
    const auto passage=(body_half(ant.id)+g.loaded_half_q)*g.quantum_m;
    for (int length=1;length<=g.reach_q;++length) for (std::size_t i=0;i<horizontal_steps.size();++i) {
        const auto d=horizontal_steps[(offset+i)%horizontal_steps.size()];
        const auto site=physical({q->x+length*d.x,q->y,q->z+length*d.z},g);
        if (within_contact(site,depot,s.config) && !physically_overlaps(site,depot,passage) &&
            clear_worker_site(ant,site)) return site;
    }
    return {};
}

bool WorldRuntime::inspecting_entrance(const AntState& ant) const {
    const auto& s=*state_;
    if (ant.stage!=LifeStage::Adult || ant.caste!=Caste::Worker) return false;
    const auto care=s.care.find(ant.id);
    return care!=s.care.end() && care->second.act==CareAct::EntrancePatrol && !care->second.enabled &&
        ant.position==care->second.destination && s.physiology.at(ant.id).behavior==IndividualBehavior::Rest &&
        s.m.now.milliseconds-care->second.began_at.milliseconds<s.ecological->worker_activity_timing->minimum_program_time.milliseconds;
}

void WorldRuntime::observe_entrance_contact(Transaction& tx,const WorldEvent& arrival) {
    auto& s=*state_;
    if (!s.ecological || !s.ecological->founding_habitat || arrival.kind!=FactKind::Moved ||
        arrival.payload!=connector_move_fact || s.connectors.at(arrival.actor).cursor) return;
    const auto local=query_neighborhood({s.world,arrival.actor},s.config.contact_distance_m);
    for (const auto peer:local.ants) {
        const auto actor=*query_ant(peer);
        if (actor.colony!=arrival.colony || !inspecting_entrance(actor)) continue;
        // An instantaneous antennation proxy within the committed contact range.
        observe(tx,actor.id,arrival.source,{ObservationPhase::Completed,CareAct::EntranceContact,
                arrival.actor,{},s.m.now,false,arrival.position});
        break;
    }
}

bool WorldRuntime::clear_worker_site(const AntState& ant,PositionM site,bool approach_depot) const {
    const auto& s=*state_;
    const auto& g=s.geometry->config;
    const auto depot=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
    const auto q=quantized(site,g);
    const auto half=body_half(ant.id);
    if ((!q && !mouth_access(s)) || ant.position==site || !clear_care_segment(ant.position,site,half) ||
        (s.surface && site.y>=s.surface->config.origin_m.y)) return false;
    if (anatomical_nest(s)) return (approach_depot || site!=depot) && clear_worker_traffic(ant,site,half);
    const auto view=geometry_view(s,limits_);
    const bool floor=material_at(view,{q->x,q->y-g.loaded_half_q-1,q->z})!=Material::Void;
    if (!floor || (sealed_chamber(s) && ant.position.y!=site.y)) {
        const auto from=sealed_chamber(s) && !approach_depot && half==g.body_half_q ? quantized(ant.position,g) : std::nullopt;
        if (!from || !supported_wall_segment(view,*from,*q,g.loaded_half_q)) return false;
    }
    if (local_traffic(s)) return (approach_depot || site!=depot) && clear_worker_traffic(ant,site,half);
    // A delivery/contact interface permits transient overlap. A resting berth
    // and the intermediate destination of a local walk reserve adult space.
    if (approach_depot && site==depot) return true;
    if (site==depot) return false;
    const auto reach=s.care_profile->perception_radius_m;
    const auto radius=reach+portable_care_distance(ant.position,site)+2*g.loaded_half_q*g.quantum_m;
    for (const auto ref:query_neighborhood({s.world,ant.id},radius).ants) {
        const auto other=*query_ant(ref);
        if (other.stage!=LifeStage::Adult) continue;
        const auto width=(half+body_half(ref.id))*g.quantum_m;
        if (physically_overlaps(site,other.position,width)) return false;
        if (const auto motion=query_worker_motion(ref); motion &&
            physically_overlaps(site,motion->to,width)) return false;
    }
    return true;
}

std::optional<PositionM> WorldRuntime::worker_depot_step(const AntState& ant,std::optional<PositionM> familiar_site) const {
    const auto& s=*state_;
    if (!s.geometry || !integrated_care(s)) return {};
    const auto& g=s.geometry->config;
    const bool habitat=s.ecological && s.ecological->founding_habitat;
    const auto link=s.connectors.find(ant.id);
    const bool rejoin=familiar_return(s) && link!=s.connectors.end() && !s.foragers.at(ant.id).enabled;
    const auto depot=familiar_site.value_or(habitat && link!=s.connectors.end() && !sustained_supply(s)
        ? link->second.points[rejoin?link->second.cursor:0]
        : s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position);
    const auto radius=s.care_profile->perception_radius_m;
    if (ant.position==depot) return {};
    if (familiar_site) {
        // A remembered location supplies a bearing, never the current position of
        // a recipient or food. Only locally checked paid steps can be executed.
        auto best=ant.position;
        auto gap=std::llround(portable_care_distance(ant.position,depot)*1e6);
        for (const double step:{.002,.001,.0005}) for (std::uint8_t dir=1;dir<=10;++dir) {
            const auto next=snap_micro(translated(ant.position,scale(body_heading(dir),step)));
            const auto remaining=std::llround(portable_care_distance(next,depot)*1e6);
            if (remaining<gap && clear_worker_site(ant,next,true)) { best=next; gap=remaining; }
        }
        if (best!=ant.position) return best;
        if (familiar_site_detour(s) && std::abs(ant.position.y-depot.y)<=2*g.quantum_m &&
            within_distance(ant.position,depot,radius,true) && spatially_clear(ant.position,depot)) {
            const auto target=snap_micro({depot.x,ant.position.y,depot.z});
            const std::array exact{target};
            const auto next=local_floor_route(ant,{},nullptr,exact);
            if (next!=ant.position) return next;
            if (const auto cell=nearest_grid_point(target,g,true)) {
                // A familiar place can have a different usable stance today.
                // The new stance still needs floor support and body clearance.
                std::array<PositionM,8> nearby;
                std::size_t count{};
                for (const auto direction:horizontal_steps) {
                    auto site=physical({cell->x+2*direction.x,cell->y,cell->z+2*direction.z},g);
                    site.y=ant.position.y;
                    if (site==ant.position || !within_distance(ant.position,site,radius,true) ||
                        !spatially_clear(ant.position,site) || !spatially_clear(site,site,body_half(ant.id))) continue;
                    nearby[count++]=site;
                }
                if (count) {
                    const auto alternative=local_floor_route(ant,{},nullptr,{nearby.data(),count});
                    if (alternative!=ant.position) return alternative;
                }
            }
        }
    }
    if (portable_care_distance(ant.position,depot)>radius) return {};
    if (clear_worker_site(ant,depot,true)) return depot;
    const bool alternate=habitat && s.ecological->founding_habitat->alternate_berth &&
        (link==s.connectors.end() || sustained_supply(s)) &&
        (!sealed_chamber(s) || !s.geometry_edits.empty());
    const auto berth=[&](PositionM site) {
        return within_contact(site,depot,s.config) && spatially_clear(site,depot) &&
            (!sustained_supply(s) || spatially_clear(site,site,g.loaded_half_q));
    };
    if (alternate && berth(ant.position)) return {};
    if (sustained_supply(s) && ant.position.y!=depot.y) {
        auto site=ant.position;
        site.y=depot.y;
        if ((berth(site) || !alternate) && clear_worker_site(ant,site,true)) return site;
    }
    const auto origin=habitat ? nearest_grid_point(ant.position,g,mouth_access(s)) : quantized(ant.position,g);
    // A remembered connector can start at a lawful subvoxel berth. Use
    // terrain cells to search, and the real endpoint for the final sweep.
    auto goal=mouth_access(s)?nearest_grid_point(depot,g,true):quantized(depot,g);
    if (!origin || !goal) return {};
    if (origin->y!=goal->y) {
        if (!sustained_supply(s)) return {};
        goal->y=origin->y;
    }
    struct Node { PointQ point, first; };
    const std::size_t budget=habitat ? 256 : 96;
    std::vector<Node> nodes(0);
    std::set<PointQ> examined{*origin};
    nodes.push_back({*origin,{}});
    const auto view=geometry_view(s,limits_);
    const auto half=body_half(ant.id);
    for (std::size_t i=0;i<nodes.size() && nodes.size()<budget;++i) {
        const auto node=nodes[i];
        for (const auto d:horizontal_steps) {
            const PointQ q{node.point.x+d.x,node.point.y,node.point.z+d.z};
            const auto target=physical(q,g);
            if (portable_care_distance(ant.position,target)>radius || !inside(target,s.config) ||
                material_at(view,{q.x,q.y-g.loaded_half_q-1,q.z})==Material::Void) continue;
            if (!spatially_clear(i==0 && habitat ? ant.position : physical(node.point,g),target,half)) continue;
            if (i==0 && !clear_worker_site(ant,target,true)) continue;
            if (i!=0 && habitat) {
                auto waypoint=ant;
                waypoint.position=physical(node.point,g);
                if (!clear_worker_traffic(waypoint,target,half)) continue;
            }
            if (!examined.insert(q).second) continue;
            const auto first=i==0?q:node.first;
            if (q==*goal || (alternate && berth(target)))
                return physical(first,g);
            if (nodes.size()==budget) break;
            nodes.push_back({q,first});
        }
    }
    return {};
}
} // namespace antworld
