#include "care_internal.hpp"
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

bool WorldRuntime::clear_worker_site(const AntState& ant,PositionM site,bool approach_depot) const {
    const auto& s=*state_;
    const auto& g=s.geometry->config;
    const auto depot=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
    const auto q=quantized(site,g);
    const auto half=body_half(ant.id);
    if (!q || ant.position==site || !clear_care_segment(ant.position,site,half) ||
        (s.surface && site.y>=s.surface->config.origin_m.y) ||
        material_at(geometry_view(s,limits_),{q->x,q->y-g.loaded_half_q-1,q->z})==Material::Void) return false;
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
