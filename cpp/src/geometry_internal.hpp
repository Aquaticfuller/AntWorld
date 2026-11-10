#pragma once
#include "antworld/core/geometry.hpp"
#include "motion_numeric.hpp"
#include <algorithm>
#include <cmath>
#include <map>
#include <memory>
#include <optional>
#include <span>
#include <stdexcept>

namespace antworld::detail {
struct GeometryDefinition {
    GeometryConfig config;
    std::vector<BoxQ> voids = std::vector<BoxQ>(0), rocks = std::vector<BoxQ>(0);
};
using GeometryEdits = std::map<GeometryEditId, GeometryEdit>;
using EditIndex = std::map<std::pair<PointQ, GeometryEditId>, std::uint8_t>;
using SpatialIndex = std::map<std::pair<PointQ, std::uint64_t>, std::uint8_t>;
struct GeometryView {
    const GeometryDefinition &definition;
    const GeometryEdits &edits;
    const EditIndex &index;
    std::size_t partition_budget;
};
inline bool box_valid(BoxQ b) { return b.min.x < b.max.x && b.min.y < b.max.y && b.min.z < b.max.z; }
inline bool contains(BoxQ b, PointQ p) {
    return p.x >= b.min.x && p.x < b.max.x && p.y >= b.min.y && p.y < b.max.y && p.z >= b.min.z && p.z < b.max.z;
}
inline bool encloses(BoxQ a, BoxQ b) {
    return a.min.x <= b.min.x && a.min.y <= b.min.y && a.min.z <= b.min.z && a.max.x >= b.max.x && a.max.y >= b.max.y &&
           a.max.z >= b.max.z;
}
inline BoxQ intersection(BoxQ a, BoxQ b) {
    return {{std::max(a.min.x, b.min.x), std::max(a.min.y, b.min.y), std::max(a.min.z, b.min.z)},
            {std::min(a.max.x, b.max.x), std::min(a.max.y, b.max.y), std::min(a.max.z, b.max.z)}};
}
inline std::int32_t floor_div(std::int32_t n, std::int32_t d) { return n / d - (n % d < 0); }
inline PointQ brick_key(PointQ p, std::int32_t side) {
    return {floor_div(p.x, side), floor_div(p.y, side), floor_div(p.z, side)};
}
inline BoxQ around(PointQ p, std::int32_t radius) {
    return {{p.x - radius, p.y - radius, p.z - radius}, {p.x + radius, p.y + radius, p.z + radius}};
}
inline BoxQ swept_box(PointQ a, PointQ b, std::int32_t radius) {
    return {{std::min(a.x, b.x) - radius, std::min(a.y, b.y) - radius, std::min(a.z, b.z) - radius},
            {std::max(a.x, b.x) + radius, std::max(a.y, b.y) + radius, std::max(a.z, b.z) + radius}};
}
inline PositionM physical(PointQ p, const GeometryConfig &c) {
    return {c.origin_m.x + p.x * c.quantum_m, c.origin_m.y + p.y * c.quantum_m, c.origin_m.z + p.z * c.quantum_m};
}
inline std::optional<PointQ> quantized(PositionM p, const GeometryConfig &c) {
    auto axis = [&](double value, double origin) -> std::optional<std::int32_t> {
        const auto q = (value - origin) / c.quantum_m, nearest = std::round(q);
        if (!std::isfinite(q) || std::abs(q - nearest) > 1e-7 || nearest < -1000000 || nearest > 1000000)
            return {};
        return static_cast<std::int32_t>(nearest);
    };
    const auto x = axis(p.x, c.origin_m.x), y = axis(p.y, c.origin_m.y), z = axis(p.z, c.origin_m.z);
    if (!x || !y || !z)
        return {};
    return PointQ{*x, *y, *z};
}
std::vector<PointQ> overlapping_bricks(BoxQ, std::int32_t side, std::size_t budget);
// Identical later boxes overwrite every classification affected by the older edit.
// Only the disposable index is reduced; the complete edit log is retained.
template<class Erase, class Insert>
void index_geometry_edit(const GeometryEdits& edits, EditIndex& index, const GeometryEdit& edit,
                         std::int32_t side, std::size_t budget, Erase erase, Insert insert) {
    for (auto key : overlapping_bricks(edit.box, side, budget)) {
        auto it = index.lower_bound({key, {0}});
        while (it != index.end() && it->first.first == key) {
            const auto old = it++->first;
            if (edits.at(old.second).box == edit.box) erase(old);
        }
        if (index.size() >= budget) throw std::length_error("geometry index host budget exceeded");
        insert(std::pair{key, edit.id});
    }
}
inline void rebuild_index_edit(const GeometryEdits& edits, EditIndex& index, const GeometryEdit& edit,
                               std::int32_t side, std::size_t budget) {
    index_geometry_edit(edits, index, edit, side, budget,
                        [&](const auto& key) { index.erase(key); },
                        [&](const auto& key) { index.emplace(key, std::uint8_t{0}); });
}
std::vector<GeometryEditId> relevant_edits(const GeometryView &, BoxQ);
Material material_at(const GeometryView &, PointQ);
std::uint64_t material_volume(const GeometryView &, BoxQ, Material);
double signed_distance(const GeometryView &, PointQ);
bool clear_sweep(const GeometryView &, PointQ from, PointQ to, std::int32_t half);
bool continuous_clear(const GeometryView &,PositionM from,PositionM to,std::int32_t half);
bool intersects_body(BoxQ,PositionM center,std::int32_t half,const GeometryConfig&);
PointQ spatial_key(PositionM);
inline GeometryView geometry_view(const auto &s, const RuntimeLimits &limits) {
    return {*s.geometry, s.geometry_edits, s.edit_index, limits.geometry_partition_cells};
}
// Version-limited views are used when auditing facts before a later wall fill.
bool historical_clear(const GeometryDefinition &, const GeometryEdits &, const EditIndex &, PositionM, PositionM,
                      std::int32_t half, std::size_t budget);
void validate_geometry(const GeometryDefinition &, const WorldConfig &, std::size_t budget);
bool local_patch(const GeometryView &, PointQ actor, BoxQ);
std::vector<PointQ> portal_neighbors(const GeometryView &, PointQ, std::int32_t half, const WorldConfig &);
} // namespace antworld::detail
