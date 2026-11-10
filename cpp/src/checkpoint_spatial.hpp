#pragma once
#include "checkpoint_codec.hpp"
#include "spatial_navigation.hpp"

namespace antworld::detail {
template<class S> void write_connectors(Writer& w,const S& s) {
    if (!s.config.continuous_spatial_motion) return;
    w.put(s.connectors.size());
    for (const auto& [id,path]:s.connectors) {
        w.put(id.value);
        w.put(path.size,4); w.put(path.cursor,4); w.put(path.returning,1);
        for (std::uint32_t i=0;i<path.size;++i) w.position(path.points[i]);
    }
}
template<class S> void read_connectors(Reader& r,S& s,const RuntimeLimits& limits) {
    if (!s.config.continuous_spatial_motion) return;
    const auto count=r.count(limits.entities,41);
    ensure(count==(mixed_navigation(s)?s.foragers.size():0),"missing or unexpected surface connectors");
    for (std::size_t n=0;n<count;++n) {
        const EntityId id{r.get()};
        SurfaceConnector path;
        path.size=static_cast<std::uint32_t>(r.get(4));
        path.cursor=static_cast<std::uint32_t>(r.get(4)); path.returning=r.flag();
        ensure(s.foragers.contains(id) && path.size && path.size<=s.surface->behavior.route_capacity &&
            path.cursor<path.size && (path.size>1 || !path.returning),"invalid connector record");
        const auto& g=s.geometry->config;
        for (std::uint32_t i=0;i<path.size;++i) {
            auto& p=path.points[i];
            p=r.position();
            ensure(inside(p,s.config) && (!i || quantized(p,g).has_value()),"invalid connector waypoint");
            if (!i) continue;
            const auto a=quantized(path.points[i-1],g);
            const auto b=*quantized(p,g);
            if (a && *a!=b) ensure(std::abs(a->x-b.x)+std::abs(a->y-b.y)+std::abs(a->z-b.z)==1,
                                   "connector skips a geometry waypoint");
            else ensure(i==1 && p!=path.points[0] && within_distance(p,path.points[0],g.quantum_m,true),
                        "invalid local connector attachment");
            for (std::uint32_t j=0;j<i;++j) ensure(path.points[j]!=p,"connector loops");
        }
        const auto& f=s.foragers.at(id);
        const auto a=s.ants.get(s.ants.index.at(id));
        const auto home=s.colonies.rows[s.colonies.index.at(a.colony)].nest_position;
        const auto in_transit=path.cursor+1<path.size;
        ensure(path.points[0]==home && navigation_cell(s,path.entrance())==f.path[0] &&
            (!in_transit || f.path_size==1) && (!f.enabled || !in_transit || a.position==path.points[path.cursor]) &&
            (!path.returning || path.cursor || a.carried_food.total_ug()) &&
            s.connectors.emplace(id,path).second,"connector owner or physical endpoint mismatch");
        if (f.action.value && (in_transit || path.returning)) {
            const auto& event=s.queue.at(s.queue_index.at(f.action));
            if (event.kind==ScheduledEvent::Kind::Move) {
                ensure(!path.returning || path.cursor,"inbound connector move below depot");
                const auto target=path.returning && !in_transit && a.position!=path.entrance()?path.entrance():
                    path.points[path.returning?path.cursor-1:path.cursor+1];
                ensure(event.destination==target,"pending connector movement has no local waypoint");
            } else ensure(event.kind==ScheduledEvent::Kind::Rest ||
                (event.kind==ScheduledEvent::Kind::DeliverFood && path.returning && !path.cursor),
                "action incompatible with connector transit");
        }
    }
}
} // namespace antworld::detail
