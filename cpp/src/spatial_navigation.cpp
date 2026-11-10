#include "state.hpp"
#include "behavior_rng.hpp"
#include "spatial_navigation.hpp"
#include <queue>
#include <tuple>

namespace antworld {
using namespace detail;

SurfaceConnector WorldRuntime::discover_connector(PositionM depot) const {
    const auto& s=*state_;
    const auto& g=s.geometry->config;
    const auto level=surface_level(s);
    if (!level) return {};
    const auto nearest=[&](double value,double origin) {
        return std::round(grid_coordinate(value,origin,g.quantum_m));
    };
    const auto x=nearest(depot.x,g.origin_m.x),y=nearest(depot.y,g.origin_m.y),z=nearest(depot.z,g.origin_m.z);
    if (std::max({std::abs(x),std::abs(y),std::abs(z)})>1000000) return {};
    const PointQ start{static_cast<std::int32_t>(x),static_cast<std::int32_t>(y),static_cast<std::int32_t>(z)};
    const auto start_pos=physical(start,g);
    const auto half=g.loaded_half_q;
    if (!spatially_clear(depot,start_pos,half)) return {};
    const auto view=geometry_view(s,limits_);
    const auto capacity=s.surface->behavior.route_capacity;
    const auto attach=static_cast<std::uint32_t>(depot!=start_pos);
    if (!limits_.navigation_nodes) return {};
    const auto remaining=[&](PointQ p) { return static_cast<std::uint32_t>(std::abs(*level-p.y)); };
    using Node=std::tuple<std::uint32_t,std::uint32_t,PointQ>;
    std::priority_queue<Node,std::vector<Node>,std::greater<Node>> open(std::greater<Node>{},std::vector<Node>(0));
    struct Parent { PointQ point; std::uint32_t depth; };
    std::map<PointQ,Parent> visited;
    visited.emplace(start,Parent{start,attach});
    open.emplace(attach+remaining(start),remaining(start),start);
    while (!open.empty()) {
        const auto [cost,height,p]=open.top();
        open.pop();
        const auto depth=visited.at(p).depth;
        if (cost!=depth+height || cost>=capacity) continue;
        const auto pos=physical(p,g);
        if (p.y==*level) {
            if (const auto tile=s.surface->tile(pos)) {
                bool usable=false;
                for (unsigned d=0;d<4 && !usable;++d) {
                    const auto next=neighbor(*tile,static_cast<Direction>(d));
                    auto center=s.surface->center(next);
                    center.y=pos.y;
                    usable=s.surface->open(next) && spatially_clear(pos,center,half);
                }
                if (usable) {
                    SurfaceConnector path;
                    path.size=depth+1;
                    path.points[0]=depot;
                    auto current=p;
                    for (auto i=depth;;--i) {
                        path.points[i]=physical(current,g);
                        if (current==start) break;
                        current=visited.at(current).point;
                    }
                    return path;
                }
            }
        }
        for (const auto q:portal_neighbors(view,p,half,s.config)) {
            if (depth+1+remaining(q)>=capacity || !surface_allows(*s.surface,true,pos,physical(q,g))) continue;
            const auto old=visited.find(q);
            if (old!=visited.end() && old->second.depth<=depth+1) continue;
            if (old==visited.end() && visited.size()>=limits_.navigation_nodes) continue;
            visited.insert_or_assign(q,Parent{p,depth+1});
            open.emplace(depth+1+remaining(q),remaining(q),q);
        }
    }
    return {};
}

bool WorldRuntime::can_forage(const AntState& ant) const {
    const auto& s=*state_;
    if (!s.surface) return false;
    if (!mixed_navigation(s)) return navigation_cell(s,ant.position) && sense({s.world,ant.id}).step_count;
    const auto known=s.connectors.find(ant.id);
    if (known==s.connectors.end()) return discover_connector(ant.position).size!=0;
    const auto& path=known->second;
    if (path.cursor || path.points[0]!=ant.position) return false;
    for (std::uint32_t i=1;i<path.size;++i)
        if (!spatially_clear(path.points[i-1],path.points[i],s.geometry->config.loaded_half_q)) return false;
    return true;
}

void WorldRuntime::prepare_forager(Transaction& tx,const AntState& ant,ForagerState& f) {
    auto& s=*state_;
    if (!s.surface) throw std::invalid_argument("foraging requires a configured surface");
    const auto& nest=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
    if (f.path_size) {
        const auto it=s.connectors.find(ant.id);
        const auto in_connector=it!=s.connectors.end() && it->second.cursor+1<it->second.size;
        if (in_connector?ant.position!=it->second.points[it->second.cursor]:
            navigation_cell(s,ant.position)!=f.path[f.path_size-1])
            throw std::invalid_argument("foraging memory no longer ends at worker position");
        return;
    }
    if (ant.position!=nest || ant.carried_food.total_ug() || !ant.carrying_capacity_ug)
        throw std::invalid_argument("first foraging activation requires an unloaded worker at its nest");
    auto cell=navigation_cell(s,ant.position);
    if (mixed_navigation(s)) {
        const auto link=discover_connector(ant.position);
        if (!link.size) throw std::invalid_argument("no locally reachable loaded-clearance surface connector");
        cell=navigation_cell(s,link.entrance());
        tx.connectors.set(ant.id,link);
    }
    if (!cell) throw std::invalid_argument("foraging requires a walkable surface position");
    f.path[0]=*cell;
    f.path_size=1;
    f.heading=initial_heading(s.seed,ant.id);
    if (!s.visits.contains(*cell)) tx.visits.set(*cell,0);
}
} // namespace antworld
