#pragma once
#include "antworld/core/behavior.hpp"
#include "motion_numeric.hpp"
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
    std::array<double,2> coordinates(PositionM p) const {
        const auto size=config.cell_size_m;
        return {grid_coordinate(p.x,config.origin_m.x-size/2,size),
                grid_coordinate(p.z,config.origin_m.z-size/2,size)};
    }
    // Cells index terrain and observations. They do not quantize a body position.
    std::optional<Cell> tile(PositionM p) const {
        const auto [x,z]=coordinates(p);
        if (!(x>=0 && z>=0 && x<config.width && z<config.height)) return {};
        const Cell cell{static_cast<std::int32_t>(x),static_cast<std::int32_t>(z)};
        return open(cell)?std::optional{cell}:std::nullopt;
    }
    bool clear_segment(PositionM from,PositionM to) const {
        const auto start=tile(from),end=tile(to);
        if (!start || !end) return false;
        const auto [x,z]=coordinates(from);
        const auto [end_x,end_z]=coordinates(to);
        const auto dx=end_x-x,dz=end_z-z;
        const auto border_x=dx==0 && x==std::floor(x);
        const auto border_z=dz==0 && z==std::floor(z);
        const auto pass=[&](Cell p) {
            return open(p) && (!border_x || open({p.x-1,p.z})) &&
                (!border_z || open({p.x,p.z-1})) && (!(border_x && border_z) || open({p.x-1,p.z-1}));
        };
        const auto endpoint_clear=[&](Cell cell,double px,double pz) {
            const bool bx=px==std::floor(px),bz=pz==std::floor(pz);
            return open(cell) && (!bx || open({cell.x-1,cell.z})) &&
                (!bz || open({cell.x,cell.z-1})) && (!(bx && bz) || open({cell.x-1,cell.z-1}));
        };
        if (!endpoint_clear(*start,x,z) || !endpoint_clear(*end,end_x,end_z)) return false;
        auto at=*start;
        const auto sx=dx<0?-1:1,sz=dz<0?-1:1;
        while (at!=*end) {
            const auto tx=at.x==end->x?2.0:(at.x+(sx>0)-x)/dx;
            const auto tz=at.z==end->z?2.0:(at.z+(sz>0)-z)/dz;
            if (std::abs(tx-tz)<=8*std::numeric_limits<double>::epsilon()) {
                if (!pass({at.x+sx,at.z}) || !pass({at.x,at.z+sz})) return false;
                at={at.x+sx,at.z+sz};
            } else if (tx<tz) at.x+=sx;
            else at.z+=sz;
            if (!pass(at)) return false;
        }
        return true;
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
inline bool surface_allows(const SurfaceDefinition& surface,bool mixed,PositionM a,PositionM b) {
    const auto y=surface.config.origin_m.y;
    const auto on_plane=[&](PositionM p) {
        return std::abs(p.y-y)<=arithmetic_margin(std::max(std::abs(p.y),std::abs(y)),surface.config.cell_size_m);
    };
    if (on_plane(a)) a.y=y;
    if (on_plane(b)) b.y=y;
    if (!mixed) return a.y==y && b.y==y && surface.clear_segment(a,b);
    if (a.y<y && b.y<y) return true;
    if (b.y<a.y) std::swap(a,b);
    if (a.y<y) {
        const auto t=(y-a.y)/(b.y-a.y);
        a={std::lerp(a.x,b.x,t),y,std::lerp(a.z,b.z,t)};
    }
    return surface.clear_segment(a,b);
}
inline std::optional<Cell> ground_cell(const SurfaceDefinition& surface,PositionM p,bool continuous) {
    if (!continuous) return surface.locate(p);
    const auto y=surface.config.origin_m.y;
    if (std::abs(p.y-y)>arithmetic_margin(std::max(std::abs(p.y),std::abs(y)),surface.config.cell_size_m)) return {};
    return surface.tile(p);
}
struct TrailKey { ColonyId colony; Cell cell; auto operator<=>(const TrailKey&) const = default; };
struct Trail { double units{}; SimTime updated; bool operator==(const Trail&) const = default; };
struct EdgeKey { Cell a, b; auto operator<=>(const EdgeKey&) const = default; };
struct Discovery { SimTime time; EntityId actor; bool operator==(const Discovery&) const = default; };
struct SurfaceConnector {
    std::array<PositionM,route_storage_capacity> points{};
    std::uint32_t size{},cursor{};
    bool returning{};
    [[nodiscard]] PositionM entrance() const { return points[size-1]; }
};
inline std::uint64_t connector_cell(Cell cell) {
    return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(cell.x))<<32)|static_cast<std::uint32_t>(cell.z);
}
inline Cell connector_cell(std::uint64_t encoded) {
    return {static_cast<std::int32_t>(encoded>>32),static_cast<std::int32_t>(encoded&UINT32_MAX)};
}
inline constexpr std::uint64_t connector_move_fact=1;
inline double portable_trail_exponential(double halves) {
    // Whole half-lives are exact binary scaling. Explicitly fused steps
    // approximate exp(-ln(2)*fraction) at binary64 precision.
    if (halves>=1075) return 0;
    const auto whole=static_cast<int>(halves);
    const auto fraction=halves-whole;
    constexpr auto log_two=0x1.62e42fefa39efp-1;
    double series=1;
    for (int n=18;n>=1;--n)
        series=std::fma(series,-log_two*fraction/static_cast<double>(n),1.);
    return std::ldexp(series,-whole);
}
inline double trail_at(const Trail& t, SimTime now, const BehaviorConfig& p, bool portable=false) {
    const auto seconds = static_cast<double>(now.milliseconds-t.updated.milliseconds)/1000.0;
    const auto amount = t.units*(portable ? portable_trail_exponential(seconds/p.trail_half_life_s) :
        std::exp(-std::log(2.0)*seconds/p.trail_half_life_s));
    return amount < p.trail_cutoff_units ? 0 : amount;
}
inline double next_trail(const BehaviorConfig& p,double current,bool portable) {
    const auto next=std::min(p.trail_cap_units,current+p.deposit_units);
    // Snap stored concentrations to a 2^-36-unit lattice. Keep sublattice
    // values and an off-lattice configured cap so all legal inputs retain a signal.
    if (!portable || next<=0x1p-36 || next==p.trail_cap_units) return next;
    return std::clamp(std::ldexp(std::round(std::ldexp(next,36)),-36),current,p.trail_cap_units);
}
void validate_surface(const SurfaceConfig&, const BehaviorConfig&, const WorldConfig&, const RuntimeLimits&);
} // namespace antworld::detail
