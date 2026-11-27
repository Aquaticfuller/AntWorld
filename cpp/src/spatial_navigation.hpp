#pragma once
#include "geometry_internal.hpp"
#include "surface_internal.hpp"
#include "ecological_internal.hpp"

namespace antworld::detail {
inline bool mixed_navigation(const auto& s) {
    return s.config.continuous_spatial_motion && s.surface && s.geometry;
}
inline std::optional<std::int32_t> surface_level(const auto& s) {
    const auto& g=s.geometry->config;
    const auto plane=std::ceil(grid_coordinate(s.surface->config.origin_m.y,g.origin_m.y,g.quantum_m))+g.loaded_half_q;
    if (!(plane>=-1000000 && plane<=1000000)) return {};
    return static_cast<std::int32_t>(plane);
}
inline double navigation_height(const auto& s) {
    if (!mixed_navigation(s)) return s.surface->config.origin_m.y;
    const auto level=surface_level(s);
    return level?physical({0,*level,0},s.geometry->config).y:std::numeric_limits<double>::infinity();
}
inline std::optional<Cell> navigation_cell(const auto& s,PositionM position) {
    if (!mixed_navigation(s)) return ground_cell(*s.surface,position,s.config.continuous_spatial_motion);
    const auto plane=navigation_height(s);
    if (!std::isfinite(plane) ||
        std::abs(position.y-plane)>arithmetic_margin(std::max(std::abs(plane),std::abs(position.y)),s.geometry->config.quantum_m))
        return {};
    return s.surface->tile(position);
}
inline PositionM navigation_waypoint(const auto& s,EntityId actor,Cell cell) {
    auto point=s.surface->center(cell);
    if (!mixed_navigation(s)) return point;
    point.y=navigation_height(s);
    const auto link=s.connectors.find(actor);
    if (link!=s.connectors.end() && s.surface->tile(link->second.entrance())==cell)
        return link->second.entrance();
    return point;
}
// A worker remembers its own paid excavation. The fixed path origin survives
// task changes. A handoff berth and this private sampling berth are distinct.
inline bool at_worked_site(const auto& s,EntityId id,PositionM site) {
    if (!worked_exit(s) || !s.geometry || !s.surface || site.y>=navigation_height(s)) return false;
    const auto dig=s.excavators.find(id);
    return dig!=s.excavators.end() && dig->second.digs && dig->second.deliveries &&
        dig->second.path_size && within_contact(site,physical(dig->second.path[0],s.geometry->config),s.config);
}

inline bool private_sampling_trip(const auto& s,const AntState& ant) {
    if (!worked_exit(s)) return false;
    const auto link=s.connectors.find(ant.id);
    const auto home=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
    return link!=s.connectors.end() && !within_contact(link->second.points[0],home,s.config) &&
        at_worked_site(s,ant.id,link->second.points[0]);
}

// The taste and origin of this worker's last trip survive a local feeding
// visit. The worker cannot sense the present stock of that distant source.
inline std::optional<PositionM> remembered_liquid_berth(const auto& s,const AntState& ant) {
    if (!source_refill(s) || !s.surface || !s.geometry || !s.care_profile ||
        ant.carried_food.total_ug() || s.carriers.contains(ant.id)) return {};
    const auto trip=s.foragers.find(ant.id);
    const auto route=s.connectors.find(ant.id);
    if (trip==s.foragers.end() || route==s.connectors.end() || trip->second.enabled ||
        trip->second.path_size!=1 || !trip->second.last_collected.value ||
        !trip->second.collections || ant.position.y>=navigation_height(s)) return {};
    const auto food=s.foods.index.find(trip->second.last_collected);
    if (food==s.foods.index.end() || !s.foods.rows[food->second].initial.carbs_ug) return {};
    return route->second.points[0];
}

inline bool familiar_liquid_exit(const auto& s,const AntState& ant) {
    const auto berth=remembered_liquid_berth(s,ant);
    return berth && within_distance(ant.position,*berth,s.care_profile->perception_radius_m,true);
}

inline WorldEvent forager_started(const AntState& ant,Cell home,bool mixed) {
    WorldEvent fact;
    fact.kind=FactKind::ForagingStarted; fact.actor=ant.id; fact.colony=ant.colony;
    fact.position=ant.position; fact.stage=ant.stage;
    if (mixed) fact.payload=connector_cell(home);
    return fact;
}
} // namespace antworld::detail
