#pragma once

#include "wp4_lineage.hpp"

namespace antworld::wp5 {
inline PositionM physical(PointQ point, const GeometryConfig& config) {
    const auto q = config.quantum_m;
    return {config.origin_m.x + point.x * q, config.origin_m.y + point.y * q, config.origin_m.z + point.z * q};
}

inline std::ostream& point(std::ostream& out, PointQ value) {
    return out << ',' << value.x << ',' << value.y << ',' << value.z;
}

inline std::ostream& position(std::ostream& out, PositionM value) {
    return out << ',' << value.x << ',' << value.y << ',' << value.z;
}

inline std::ostream& box(std::ostream& out, BoxQ value) {
    return point(point(out, value.min), value.max);
}

inline constexpr auto probe_columns = "actor,actor_x_m,actor_y_m,actor_z_m,target_x_m,target_y_m,target_z_m,"
    "found,budget_exhausted,half_extent_q,examined,portals,frontiers,points_q";

// This diagnostic query runs outside decision processing. It never submits the route.
inline std::size_t probe(std::ostream& out, const WorldRuntime& world, AntRef focal, PositionM target) {
    const auto ant = world.query_ant(focal);
    std::ostringstream line;
    line << std::setprecision(17);
    position(position(line << focal.id.value, ant.value().position), target);
    if (ant->alive()) {
        const auto route = world.query_route(focal, target);
        const auto portals = world.query_portals(focal);
        const auto frontiers = world.local_frontiers(focal);
        line << ',' << route.found << ',' << route.budget_exhausted << ',' << route.half_extent_q << ','
             << route.examined << ',' << portals.size() << ',' << frontiers.size() << ',';
        wp4::require(route.points.size() <= 4096, "WP-5 route view exceeds its point budget");
        for (const auto p : route.points) line << p.x << ':' << p.y << ':' << p.z << ';';
    } else {
        line << ",,,,,,,";
    }
    line << '\n';
    wp4::require(line.view().size() <= 64 * 1024, "WP-5 route view exceeds its byte budget");
    out << line.view();
    return line.view().size();
}
} // namespace antworld::wp5
