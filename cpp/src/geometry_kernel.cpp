#include "geometry_internal.hpp"
#include <array>
#include <set>

namespace antworld::detail {
namespace {
std::uint64_t volume(BoxQ b) {
    if (!box_valid(b))
        return 0;
    return static_cast<std::uint64_t>(b.max.x - b.min.x) * static_cast<std::uint64_t>(b.max.y - b.min.y) *
           static_cast<std::uint64_t>(b.max.z - b.min.z);
}
Material classify(const GeometryView &v, PointQ p, const std::vector<GeometryEditId> &ids) {
    if (!contains(v.definition.config.initial_solid, p))
        return Material::Void;
    for (auto b : v.definition.rocks)
        if (contains(b, p))
            return Material::Rock;
    for (auto it = ids.rbegin(); it != ids.rend(); ++it) {
        const auto &e = v.edits.at(*it);
        if (contains(e.box, p))
            return e.kind == SoilAction::Excavate ? Material::Void : Material::Soil;
    }
    for (auto b : v.definition.voids)
        if (contains(b, p))
            return Material::Void;
    return Material::Soil;
}
template <class F> void partition(const GeometryView &v, BoxQ query, F visit) {
    if (!box_valid(query))
        throw std::invalid_argument("empty geometry query box");
    const auto ids = relevant_edits(v, query);
    std::array<std::vector<std::int32_t>, 3> axes{std::vector<std::int32_t>(0), std::vector<std::int32_t>(0),
                                                  std::vector<std::int32_t>(0)};
    axes[0] = {query.min.x, query.max.x};
    axes[1] = {query.min.y, query.max.y};
    axes[2] = {query.min.z, query.max.z};
    auto split = [&](BoxQ b) {
        b = intersection(b, query);
        if (!box_valid(b))
            return;
        axes[0].push_back(b.min.x);
        axes[0].push_back(b.max.x);
        axes[1].push_back(b.min.y);
        axes[1].push_back(b.max.y);
        axes[2].push_back(b.min.z);
        axes[2].push_back(b.max.z);
    };
    split(v.definition.config.initial_solid);
    for (auto b : v.definition.voids)
        split(b);
    for (auto b : v.definition.rocks)
        split(b);
    for (auto id : ids)
        split(v.edits.at(id).box);
    std::size_t cells = 1;
    for (auto &axis : axes) {
        std::sort(axis.begin(), axis.end());
        axis.erase(std::unique(axis.begin(), axis.end()), axis.end());
        if (axis.size() - 1 > v.partition_budget / cells)
            throw std::length_error("exact geometry partition budget exceeded");
        cells *= axis.size() - 1;
    }
    for (std::size_t x = 1; x < axes[0].size(); ++x)
        for (std::size_t y = 1; y < axes[1].size(); ++y)
            for (std::size_t z = 1; z < axes[2].size(); ++z) {
                const BoxQ b{{axes[0][x - 1], axes[1][y - 1], axes[2][z - 1]}, {axes[0][x], axes[1][y], axes[2][z]}};
                visit(b, classify(v, b.min, ids));
            }
}
} // namespace
std::vector<PointQ> overlapping_bricks(BoxQ b, std::int32_t side, std::size_t budget) {
    if (!box_valid(b) || side <= 0)
        throw std::invalid_argument("invalid brick extent");
    const auto lo = brick_key(b.min, side), hi = brick_key({b.max.x - 1, b.max.y - 1, b.max.z - 1}, side);
    if (volume({lo, {hi.x + 1, hi.y + 1, hi.z + 1}}) > budget)
        throw std::length_error("geometry brick budget exceeded");
    std::vector<PointQ> result(0);
    for (auto x = lo.x; x <= hi.x; ++x)
        for (auto y = lo.y; y <= hi.y; ++y)
            for (auto z = lo.z; z <= hi.z; ++z)
                result.push_back({x, y, z});
    return result;
}
std::vector<GeometryEditId> relevant_edits(const GeometryView &v, BoxQ b) {
    const auto side = v.definition.config.brick_q;
    const auto lo = brick_key(b.min, side), hi = brick_key({b.max.x - 1, b.max.y - 1, b.max.z - 1}, side);
    std::set<GeometryEditId> ids;
    // Large administrative queries may scan the compact index; local queries only visit buckets.
    const BoxQ keys{lo, {hi.x + 1, hi.y + 1, hi.z + 1}};
    if (volume(keys) > v.index.size()) {
        for (const auto &[key, unused] : v.index) {
            (void)unused;
            if (contains(keys, key.first) && box_valid(intersection(v.edits.at(key.second).box, b)))
                ids.insert(key.second);
        }
    } else {
        for (auto key : overlapping_bricks(b, side, v.partition_budget)) {
            auto it = v.index.lower_bound({key, {0}});
            while (it != v.index.end() && it->first.first == key) {
                if (box_valid(intersection(v.edits.at(it->first.second).box, b)))
                    ids.insert(it->first.second);
                ++it;
            }
        }
    }
    return {ids.begin(), ids.end()};
}
Material material_at(const GeometryView &v, PointQ p) {
    return classify(v, p, relevant_edits(v, {p, {p.x + 1, p.y + 1, p.z + 1}}));
}
std::uint64_t material_volume(const GeometryView &v, BoxQ b, Material wanted) {
    std::uint64_t total = 0;
    partition(v, b, [&](BoxQ cell, Material m) {
        if (m == wanted)
            total += volume(cell);
    });
    return total;
}
double signed_distance(const GeometryView &v, PointQ p) {
    const auto band = v.definition.config.sdf_band_q;
    const bool solid = material_at(v, p) != Material::Void;
    double nearest = static_cast<double>(band);
    partition(v, around(p, band + 1), [&](BoxQ cell, Material m) {
        if ((m != Material::Void) == solid)
            return;
        const auto dx = std::max({cell.min.x - p.x, 0, p.x - cell.max.x});
        const auto dy = std::max({cell.min.y - p.y, 0, p.y - cell.max.y});
        const auto dz = std::max({cell.min.z - p.z, 0, p.z - cell.max.z});
        nearest =
            std::min(nearest, std::hypot(static_cast<double>(dx), static_cast<double>(dy), static_cast<double>(dz)));
    });
    return (solid ? -nearest : nearest) * v.definition.config.quantum_m;
}
bool clear_sweep(const GeometryView &v, PointQ a, PointQ b, std::int32_t half) {
    if (half < 0 || half > 64)
        return false;
    const auto box = swept_box(a, b, std::max(1, half));
    return material_volume(v, box, Material::Void) == volume(box);
}
PointQ spatial_key(PositionM p) {
    // ENGINEERING_FIXTURE: 4 mm buckets. Distance and solid barriers still decide eligibility.
    auto axis = [](double value) {
        const auto n = std::floor(value / 0.004);
        if (!std::isfinite(n) || n < -1000000 || n > 1000000)
            throw std::invalid_argument("spatial index coordinate limit");
        return static_cast<std::int32_t>(n);
    };
    return {axis(p.x), axis(p.y), axis(p.z)};
}
std::vector<PointQ> portal_neighbors(const GeometryView &view, PointQ p, std::int32_t half, const WorldConfig &world) {
    constexpr std::array<PointQ, 6> steps{{{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}}};
    std::vector<PointQ> result(0);
    for (auto delta : steps) {
        const PointQ q{p.x + delta.x, p.y + delta.y, p.z + delta.z};
        const auto a = physical(q, view.definition.config);
        if (a.x < world.min_m.x || a.x > world.max_m.x || a.y < world.min_m.y || a.y > world.max_m.y ||
            a.z < world.min_m.z || a.z > world.max_m.z)
            continue;
        if (clear_sweep(view, p, q, half))
            result.push_back(q);
    }
    return result;
}
bool historical_clear(const GeometryDefinition &d, const GeometryEdits &edits, const EditIndex &index, PositionM a,
                      PositionM b, std::int32_t half, std::size_t budget) {
    const auto qa = quantized(a, d.config), qb = quantized(b, d.config);
    return qa && qb && clear_sweep({d, edits, index, budget}, *qa, *qb, half);
}
void validate_geometry(const GeometryDefinition &d, const WorldConfig &world, std::size_t budget) {
    const auto &c = d.config;
    auto bounded = [](BoxQ b) {
        return box_valid(b) && b.min.x >= -100000 && b.min.y >= -100000 && b.min.z >= -100000 && b.max.x <= 100000 &&
               b.max.y <= 100000 && b.max.z <= 100000 && b.max.x - b.min.x <= 4096 && b.max.y - b.min.y <= 4096 &&
               b.max.z - b.min.z <= 4096;
    };
    auto physical_inside = [&](PointQ p) {
        const auto a = physical(p, c);
        return a.x >= world.min_m.x && a.x <= world.max_m.x && a.y >= world.min_m.y && a.y <= world.max_m.y &&
               a.z >= world.min_m.z && a.z <= world.max_m.z;
    };
    if (!std::isfinite(c.quantum_m) || c.quantum_m < 1e-6 || c.quantum_m > 0.01 || !bounded(c.initial_solid) ||
        !physical_inside(c.initial_solid.min) || !physical_inside(c.initial_solid.max) || c.body_half_q < 1 ||
        c.loaded_half_q < c.body_half_q || c.loaded_half_q > 8 || c.reach_q < c.loaded_half_q || c.reach_q > 32 ||
        c.max_patch_extent_q < 1 || c.max_patch_extent_q > 32 || c.brick_q != 8 || c.sample_step_q != 2 ||
        c.sdf_band_q < 1 || c.sdf_band_q > 32 || !c.dry_ug_per_q3 || c.dry_ug_per_q3 > 1000000 ||
        c.water_ug_per_q3 > 1000000 || c.work_duration.milliseconds < 1 || c.move_duration.milliseconds < 1 ||
        c.decision_delay.milliseconds < 1 || c.work_duration.milliseconds > 86400000 ||
        c.move_duration.milliseconds > 86400000 || c.decision_delay.milliseconds > 86400000 ||
        c.dig_energy_nj_per_q3 > 1000000000 || d.voids.size() > 256 || d.rocks.size() > 256)
        throw std::invalid_argument("invalid ENGINEERING_FIXTURE geometry configuration");
    for (auto b : d.voids)
        if (!bounded(b) || !encloses(c.initial_solid, b))
            throw std::invalid_argument("invalid seed void");
    for (auto b : d.rocks) {
        if (!bounded(b) || !encloses(c.initial_solid, b))
            throw std::invalid_argument("invalid immutable rock");
        for (auto a : d.voids)
            if (box_valid(intersection(a, b)))
                throw std::invalid_argument("seed void intersects immutable rock");
    }
    const GeometryEdits edits;
    const EditIndex index;
    (void)material_volume({d, edits, index, budget}, c.initial_solid, Material::Soil);
}
} // namespace antworld::detail
