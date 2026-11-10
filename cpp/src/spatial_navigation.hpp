#pragma once
#include "geometry_internal.hpp"
#include "surface_internal.hpp"

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
inline WorldEvent forager_started(const AntState& ant,Cell home,bool mixed) {
    WorldEvent fact;
    fact.kind=FactKind::ForagingStarted; fact.actor=ant.id; fact.colony=ant.colony;
    fact.position=ant.position; fact.stage=ant.stage;
    if (mixed) fact.payload=connector_cell(home);
    return fact;
}
} // namespace antworld::detail
