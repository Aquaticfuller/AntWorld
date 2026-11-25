#include "founding_internal.hpp"
#include "state.hpp"
#include "ecological_internal.hpp"
#include "behavior_rng.hpp"
#include "spatial_navigation.hpp"
#include "anatomy.hpp"
#include <queue>
#include <tuple>

namespace antworld {
using namespace detail;

SurfaceConnector WorldRuntime::discover_connector(const AntState& ant) const {
    const auto& s=*state_;
    const auto depot=ant.position;
    if (sealed_chamber(s) && s.geometry_edits.empty()) return {};
    const auto& g=s.geometry->config;
    const auto level=surface_level(s);
    if (!level) return {};
    const auto nearest=[&](double value,double origin) {
        return std::round(grid_coordinate(value,origin,g.quantum_m));
    };
    const auto x=nearest(depot.x,g.origin_m.x),y=nearest(depot.y,g.origin_m.y),z=nearest(depot.z,g.origin_m.z);
    if (std::max({std::abs(x),std::abs(y),std::abs(z)})>1000000) return {};
    const PointQ start{static_cast<std::int32_t>(x),static_cast<std::int32_t>(y),static_cast<std::int32_t>(z)};
    auto route=connector_from_grid(ant,start,*level);
    if (route.size || founding_nutrition(s)!=FoundingNutrition::ExitAttachment ||
        !familiar_liquid_exit(s,ant)) return route;
    // A worker at a remembered berth can reach the navigation grid from
    // beside another body. Each candidate still pays its actual first leg.
    constexpr std::array<std::pair<int,int>,8> neighbors{{
        {-1,0},{1,0},{0,-1},{0,1},{-1,-1},{-1,1},{1,-1},{1,1}
    }};
    for (const auto& [dx,dz]:neighbors) {
        const PointQ cell{start.x+dx,start.y,start.z+dz};
        const auto reach=std::min(g.quantum_m,s.care_profile->perception_radius_m);
        if (!within_distance(depot,physical(cell,g),reach,true)) continue;
        route=connector_from_grid(ant,cell,*level);
        if (route.size) return route;
    }
    return {};
}

SurfaceConnector WorldRuntime::connector_from_grid(const AntState& ant,PointQ start,std::int32_t level) const {
    const auto& s=*state_;
    const auto depot=ant.position;
    const auto& g=s.geometry->config;
    const auto start_pos=physical(start,g);
    const auto half=g.loaded_half_q;
    if (!spatially_clear(depot,start_pos,half)) return {};
    const auto view=geometry_view(s,limits_);
    const auto capacity=s.surface->behavior.route_capacity;
    const auto attach=static_cast<std::uint32_t>(depot!=start_pos);
    // Route selection uses the current occupancy. The motion transaction
    // checks reserved sweeps again before each segment actually executes.
    if (sustained_supply(s) && attach && !clear_worker_traffic(ant,start_pos,body_half(ant.id),false)) return {};
    if (!limits_.navigation_nodes) return {};
    const auto remaining=[&](PointQ p) { return static_cast<std::uint32_t>(std::abs(level-p.y)); };
    using Node=std::tuple<std::uint32_t,std::uint32_t,PointQ>;
    std::priority_queue<Node,std::vector<Node>,std::greater<Node>> open(std::greater<Node>{},std::vector<Node>(0));
    const bool anatomy=anatomical_nest(s);
    std::vector<BodyPose> local_adults;
    if (protected_founding(s)) {
        for (const auto ref:query_neighborhood({s.world,ant.id},s.care_profile->perception_radius_m).ants) {
            const auto peer=query_ant(ref);
            if (ref.id!=ant.id && peer && peer->stage==LifeStage::Adult && spatially_clear(depot,peer->position))
                local_adults.push_back(*query_body(ref));
        }
    }
    const auto budget=anatomy?std::min(limits_.navigation_nodes,std::size_t{1024}):limits_.navigation_nodes;
    auto facing=std::max<std::uint8_t>(1,actor_facing(s,ant.id));
    if (anatomy && attach) {
        const auto next=body_travel_heading(view,ant,start_pos,facing);
        if (!anatomy_sweep(view,ant,start_pos,facing,next)) return {};
        facing=next;
    }
    struct Parent { PointQ point; std::uint32_t depth; std::uint8_t facing; };
    std::map<PointQ,Parent> visited;
    visited.emplace(start,Parent{start,attach,facing});
    open.emplace(attach+remaining(start),remaining(start),start);
    while (!open.empty()) {
        const auto [cost,height,p]=open.top();
        open.pop();
        const auto current=visited.at(p);
        const auto depth=current.depth;
        if (cost!=depth+height || cost>=capacity) continue;
        const auto pos=physical(p,g);
        if (p.y==level) {
            if (const auto tile=s.surface->tile(pos)) {
                bool usable=false;
                for (unsigned d=0;d<4 && !usable;++d) {
                    const auto next=neighbor(*tile,static_cast<Direction>(d));
                    auto center=s.surface->center(next);
                    center.y=pos.y;
                    usable=s.surface->open(next) && spatially_clear(pos,center,half);
                    if (usable && anatomy) {
                        auto actor=ant; actor.position=pos;
                        const auto heading=body_travel_heading(view,actor,center,current.facing);
                        usable=anatomy_sweep(view,actor,center,current.facing,heading);
                    }
                }
                if (usable) {
                    SurfaceConnector path;
                    path.size=depth+1;
                    path.points[0]=depot;
                    auto route_point=p;
                    for (auto i=depth;;--i) {
                        path.points[i]=physical(route_point,g);
                        if (route_point==start) break;
                        route_point=visited.at(route_point).point;
                    }
                    return path;
                }
            }
        }
        for (const auto q:portal_neighbors(view,p,half,s.config)) {
            const auto to=physical(q,g);
            if (attach && to==depot) continue;
            if (depth+1+remaining(q)>=capacity || !surface_allows(*s.surface,true,pos,to) ||
                (anatomy && s.care_profile && !within_distance(depot,to,s.care_profile->perception_radius_m,true))) continue;
            if (sustained_supply(s) && !depth && !clear_worker_traffic(ant,to,body_half(ant.id),false)) continue;
            const auto old=visited.find(q);
            if (old!=visited.end() && old->second.depth<=depth+1) continue;
            if (old==visited.end() && visited.size()>=budget) continue;
            auto heading=current.facing;
            if (anatomy) {
                auto actor=ant; actor.position=pos;
                heading=body_travel_heading(view,actor,to,current.facing);
                if (!anatomy_sweep(view,actor,to,current.facing,heading)) continue;
                if (protected_founding(s)) {
                    // Route through the space currently visible from the
                    // departure site. Recheck occupancy at execution time.
                    const auto body=body_pose(actor,heading,attachment(view,actor,heading));
                    bool blocked=false;
                    for (const auto& peer:local_adults) {
                        if (anatomical_sweep_hits(body,to,peer)) { blocked=true; break; }
                    }
                    if (blocked) continue;
                }
            }
            visited.insert_or_assign(q,Parent{p,depth+1,heading});
            open.emplace(depth+1+remaining(q),remaining(q),q);
        }
    }
    return {};
}

bool WorldRuntime::departure_replan(const AntState& ant,const SurfaceConnector& path) const {
    return path.points[path.cursor]!=ant.position || path.cursor ||
        (path.size>1 && !clear_worker_traffic(ant,path.points[1],body_half(ant.id),false));
}

bool WorldRuntime::at_foraging_home(const AntState& ant) const {
    const auto& s=*state_;
    const auto depot=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
    if (!s.ecological || !s.ecological->founding_habitat) return ant.position==depot;
    if (sealed_chamber(s) && s.geometry_edits.empty()) return ant.position==depot;
    const auto route=s.connectors.find(ant.id);
    // A pantry on the shaft wall accepts dry freight. A forager returning
    // with a payable crop still owns the route to its chamber berth.
    if (chamber_handoff(s) && route!=s.connectors.end() && route->second.returning &&
        route->second.cursor && s.foragers.at(ant.id).enabled && local_founding_provisioning(s,ant.id) &&
        founding_gift_supply(s.founding->profile,*query_physiology({s.world,ant.id})).carbs_ug)
        return false;
    if (worked_exit(s) && !ant.carried_food.total_ug() && at_worked_site(s,ant.id,ant.position) &&
        spatially_clear(ant.position,physical(s.excavators.at(ant.id).path[0],s.geometry->config)) &&
        (route==s.connectors.end() || !s.foragers.at(ant.id).enabled ||
         (!route->second.cursor && ant.position==route->second.points[0]))) return true;
    if (sustained_supply(s) && route!=s.connectors.end() && !ant.carried_food.total_ug()) {
        if (!s.foragers.at(ant.id).enabled)
            return within_contact(ant.position,depot,s.config) && spatially_clear(ant.position,depot);
        if (route->second.cursor && route->second.cursor+1<route->second.size &&
            ant.position==route->second.points[route->second.cursor] &&
            s.autonomy.contains(ant.id) && s.autonomy.at(ant.id).knows_depot &&
            mouth_at_supply(ant,depot_mouth_target(ant,depot)))
            return true;
    }
    if (familiar_return(s) && route!=s.connectors.end() && route->second.cursor &&
        route->second.cursor+1<route->second.size && ant.position==route->second.points[route->second.cursor] &&
        (route->second.returning || !s.foragers.at(ant.id).enabled) && !ant.carried_food.total_ug() &&
        s.autonomy.contains(ant.id) && s.autonomy.at(ant.id).knows_depot)
        return mouth_at_supply(ant,depot) && spatially_clear(ant.position,depot);
    if (!within_contact(ant.position,depot,s.config) || !spatially_clear(ant.position,depot)) return false;
    return route==s.connectors.end() || (!route->second.cursor && ant.position==route->second.points[0]);
}

bool WorldRuntime::can_forage(const AntState& ant) const {
    const auto& s=*state_;
    if (!s.surface) return false;
    if (!mixed_navigation(s)) return navigation_cell(s,ant.position) && sense({s.world,ant.id}).step_count;
    const auto known=s.connectors.find(ant.id);
    if (known==s.connectors.end()) return discover_connector(ant).size!=0;
    const auto& path=known->second;
    if (sustained_supply(s) && !s.foragers.at(ant.id).enabled &&
        (!at_foraging_home(ant) || s.foragers.at(ant.id).path_size!=1)) return false;
    if (sustained_supply(s) && !s.foragers.at(ant.id).enabled && departure_replan(ant,path))
        return discover_connector(ant).size!=0;
    if (path.points[path.cursor]!=ant.position || (path.cursor && !(familiar_return(s) && at_foraging_home(ant)))) return false;
    for (std::uint32_t i=path.cursor+1;i<path.size;++i)
        if (!spatially_clear(path.points[i-1],path.points[i],s.geometry->config.loaded_half_q)) return false;
    return true;
}

void WorldRuntime::prepare_forager(Transaction& tx,const AntState& ant,ForagerState& f) {
    auto& s=*state_;
    if (!s.surface) throw std::invalid_argument("foraging requires a configured surface");
    if (f.path_size) {
        const auto it=s.connectors.find(ant.id);
        if (sustained_supply(s) && it!=s.connectors.end() && !f.enabled && departure_replan(ant,it->second)) {
            if (!at_foraging_home(ant) || f.path_size!=1)
                throw std::invalid_argument("an interrupted trip still owns its return trace");
            const auto replacement=discover_connector(ant);
            if (!replacement.size) throw std::invalid_argument("no locally reachable connector from the new berth");
            const auto home=*navigation_cell(s,replacement.entrance());
            if (home!=f.path[0]) {
                f.path[0]=home;
                f.memory={};
                f.memory_size=0;
            }
            f.trip_moves=0;
            tx.connectors.set(ant.id,replacement);
            if (!s.visits.contains(home)) tx.visits.set(home,0);
            auto fact=forager_started(ant,home,true);
            fact.random_value=1;
            tx.fact(fact);
            return;
        }
        const auto in_connector=it!=s.connectors.end() && it->second.cursor+1<it->second.size;
        if (in_connector?ant.position!=it->second.points[it->second.cursor]:
            navigation_cell(s,ant.position)!=f.path[f.path_size-1])
            throw std::invalid_argument("foraging memory no longer ends at worker position");
        return;
    }
    if (!at_foraging_home(ant) || ant.carried_food.total_ug() || !ant.carrying_capacity_ug)
        throw std::invalid_argument("first foraging activation requires an unloaded worker at its nest");
    auto cell=navigation_cell(s,ant.position);
    if (mixed_navigation(s)) {
        const auto link=discover_connector(ant);
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
