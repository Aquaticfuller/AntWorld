#pragma once
#include "antworld/core/behavior.hpp"
#include <cmath>
#include <optional>
#include <vector>

namespace antworld::detail {
inline Cell neighbor(Cell c, Direction d) {
    switch (d) {
    case Direction::North: ++c.z; break;
    case Direction::East: ++c.x; break;
    case Direction::South: --c.z; break;
    case Direction::West: --c.x; break;
    case Direction::None: break;
    }
    return c;
}
inline bool adjacent(Cell a, Cell b) {
    return std::abs(std::int64_t{a.x}-b.x)+std::abs(std::int64_t{a.z}-b.z) == 1;
}
inline Direction direction(Cell a, Cell b) {
    for (unsigned i = 0; i < 4; ++i) if (neighbor(a, static_cast<Direction>(i)) == b) return static_cast<Direction>(i);
    return Direction::None;
}
struct SurfaceDefinition {
    SurfaceConfig config;
    BehaviorConfig behavior;
    std::vector<std::uint8_t> walkable = std::vector<std::uint8_t>(0);
    bool contains(Cell c) const {
        return c.x >= 0 && c.z >= 0 && static_cast<std::uint32_t>(c.x) < config.width && static_cast<std::uint32_t>(c.z) < config.height;
    }
    bool open(Cell c) const {
        return contains(c) && walkable[static_cast<std::size_t>(c.z)*config.width + static_cast<std::size_t>(c.x)] != 0;
    }
    PositionM center(Cell c) const {
        return {config.origin_m.x + c.x*config.cell_size_m, config.origin_m.y, config.origin_m.z + c.z*config.cell_size_m};
    }
    std::optional<Cell> locate(PositionM p) const {
        if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) return {};
        const auto x = (p.x-config.origin_m.x)/config.cell_size_m, z = (p.z-config.origin_m.z)/config.cell_size_m;
        if (!std::isfinite(x) || !std::isfinite(z) || x < -0.5 || z < -0.5 ||
            x > static_cast<double>(config.width)-0.5 || z > static_cast<double>(config.height)-0.5) return {};
        const Cell cell{static_cast<std::int32_t>(std::round(x)), static_cast<std::int32_t>(std::round(z))};
        if (!open(cell)) return {};
        const auto expected = center(cell);
        // Numerical coordinate tolerance in meters, not a sensing/body-size parameter.
        if (std::abs(p.x-expected.x) > 1e-9 || std::abs(p.y-expected.y) > 1e-9 || std::abs(p.z-expected.z) > 1e-9) return {};
        return cell;
    }
};
struct TrailKey { ColonyId colony; Cell cell; auto operator<=>(const TrailKey&) const = default; };
struct Trail { double units{}; SimTime updated; bool operator==(const Trail&) const = default; };
struct EdgeKey { Cell a, b; auto operator<=>(const EdgeKey&) const = default; };
struct Discovery { SimTime time; EntityId actor; bool operator==(const Discovery&) const = default; };
inline double trail_at(const Trail& t, SimTime now, const BehaviorConfig& p) {
    const auto seconds = static_cast<double>(now.milliseconds-t.updated.milliseconds)/1000.0;
    const auto amount = t.units*std::exp(-std::log(2.0)*seconds/p.trail_half_life_s);
    return amount < p.trail_cutoff_units ? 0 : amount;
}
void validate_surface(const SurfaceConfig&, const BehaviorConfig&, const WorldConfig&, const RuntimeLimits&);
} // namespace antworld::detail
