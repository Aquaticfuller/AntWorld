#include "care_internal.hpp"
#include "social_internal.hpp"
#include "worker_motion.hpp"
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

bool leaving_overlap(PositionM from,PositionM to,PositionM stationary,double width) {
    return physically_overlaps(from,stationary,width) && !physically_overlaps(to,stationary,width) &&
           (to.x-from.x)*(from.x-stationary.x)>=0 && (to.y-from.y)*(from.y-stationary.y)>=0 &&
           (to.z-from.z)*(from.z-stationary.z)>=0;
}
}

std::optional<WorkerMotion> WorldRuntime::query_worker_motion(AntRef ref) const {
    const auto& s=*state_;
    if (!worker_motor(s)) return {};
    const auto ant=query_ant(ref);
    if (!ant || ant->stage!=LifeStage::Adult || ant->caste!=Caste::Worker ||
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
    const auto previous=actor_facing(s,ref.id);
    const auto heading=movement_facing(ant->position,to);
    return WorkerMotion{id,ant->position,to,event.issued_at,after(event.issued_at,turn_ms(previous,heading)),
                        event.key.time,previous,heading};
}

void WorldRuntime::record_worker_move(Transaction& tx,WorldEvent& fact,PositionM from,SimTime began,bool autonomous) {
    auto& s=*state_;
    if (!worker_motor(s) || from==fact.position || !s.autonomy.contains(fact.actor) ||
        s.ants.get(s.ants.index.at(fact.actor)).caste!=Caste::Worker) return;
    auto a=s.autonomy.at(fact.actor);
    const auto facing=movement_facing(from,fact.position);
    if (autonomous) {
        const auto elapsed=s.m.now.milliseconds-began.milliseconds;
        const auto turn=turn_ms(a.facing,facing);
        if (elapsed<=turn || elapsed>UINT32_MAX) throw std::logic_error("worker motor exceeded its segment clock");
        fact.random_value=motion_evidence(elapsed,turn);
    }
    a.facing=facing;
    tx.autonomy.set(fact.actor,a);
}

bool WorldRuntime::clear_worker_traffic(const AntState& ant,PositionM to,std::int32_t half) const {
    const auto& s=*state_;
    if (!local_traffic(s) || !s.geometry || ant.stage!=LifeStage::Adult) return true;
    const auto quantum=s.geometry->config.quantum_m;
    for (const auto& row:s.ants.identities) {
        if (row.id==ant.id) continue;
        const auto other=s.ants.get(s.ants.index.at(row.id));
        if (other.stage!=LifeStage::Adult) continue;
        const auto width=(half+body_half(other.id))*quantum;
        const auto plan=query_worker_motion({s.world,other.id});
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
    const auto origin=quantized(ant.position,g);
    if (!origin) return {};
    const auto reach=s.care_profile->perception_radius_m;
    const auto crop=s.physiology.at(ant.id).crop;
    std::optional<std::pair<PositionM,EntityId>> best;
    double best_score=0;
    for (const auto ref:query_neighborhood({s.world,ant.id},reach).ants) {
        const auto target=*query_ant(ref);
        if (!target.alive() || target.colony!=ant.colony || within_contact(ant.position,target.position,s.config)) continue;
        const auto receiver=query_physiology(ref);
        const bool donation=s.social->exchange_enabled && receiver && receiver->crop.total_ug()<receiver->config.crop_capacity_ug &&
            ingredient_min(crop,signaled_need(*receiver,target.stage,s.long_term!=nullptr)).total_ug();
        if (!brood(target.stage) && !donation) continue;
        const auto before=distance(ant.position,target.position);
        for (int length=1;length<=3;++length) for (const auto direction:horizontal_steps) {
            const auto to=physical({origin->x+direction.x*length,origin->y,origin->z+direction.z*length},g);
            const auto progress=before-distance(to,target.position);
            if (progress<=0.25*g.quantum_m || !spatially_clear(to,target.position)) continue;
            const auto travel=distance(ant.position,to);
            const auto turn=turn_ms(actor_facing(s,ant.id),movement_facing(ant.position,to));
            const auto score=progress-0.2*travel-static_cast<double>(turn)*g.quantum_m/1000;
            if (score>best_score && clear_worker_site(ant,to)) {
                best_score=score;
                best=std::pair{to,target.id};
            }
        }
    }
    return best;
}

bool WorldRuntime::clear_worker_site(const AntState& ant,PositionM site,bool approach_depot) const {
    const auto& s=*state_;
    const auto& g=s.geometry->config;
    const auto depot=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
    const auto q=quantized(site,g);
    const auto half=body_half(ant.id);
    if (!q || ant.position==site || !clear_care_segment(ant.position,site,half) ||
        (s.surface && site.y>=s.surface->config.origin_m.y) ||
        material_at(geometry_view(s,limits_),{q->x,q->y-g.loaded_half_q-1,q->z})==Material::Void) return false;
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

std::optional<PositionM> WorldRuntime::worker_depot_step(const AntState& ant) const {
    const auto& s=*state_;
    if (!s.geometry || !integrated_care(s)) return {};
    const auto& g=s.geometry->config;
    const auto depot=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
    const auto radius=s.care_profile->perception_radius_m;
    if (ant.position==depot || portable_care_distance(ant.position,depot)>radius) return {};
    if (clear_worker_site(ant,depot,true)) return depot;
    const auto origin=quantized(ant.position,g);
    const auto goal=quantized(depot,g);
    if (!origin || !goal || origin->y!=goal->y) return {};
    struct Node { PointQ point, first; };
    constexpr std::size_t budget=96;
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
            if (!spatially_clear(physical(node.point,g),target,half)) continue;
            if (i==0 && !clear_worker_site(ant,target,true)) continue;
            if (!examined.insert(q).second) continue;
            const auto first=i==0?q:node.first;
            if (q==*goal) return physical(first,g);
            if (nodes.size()==budget) break;
            nodes.push_back({q,first});
        }
    }
    return {};
}
} // namespace antworld
