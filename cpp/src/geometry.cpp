#include "state.hpp"
#include <queue>
#include <set>

namespace antworld {
using namespace detail;
void WorldRuntime::configure_geometry(const GeometryConfig &config, std::span<const BoxQ> voids,
                                      std::span<const BoxQ> rocks) {
    auto &s = *state_;
    if (s.geometry || s.m.now != SimTime{} || s.m.watermark || s.ants.size() || !s.foods.rows.empty() ||
        !s.colonies.rows.empty())
        throw std::invalid_argument("geometry must precede entity seeding in an unexecuted world");
    auto definition = std::make_shared<GeometryDefinition>();
    definition->config = config;
    definition->voids.assign(voids.begin(), voids.end());
    definition->rocks.assign(rocks.begin(), rocks.end());
    validate_geometry(*definition, s.config, limits_.geometry_partition_cells);
    Transaction tx(s, limits_);
    s.geometry = definition;
    s.m.soil.initial_q3 = material_volume(geometry_view(s, limits_), config.initial_solid, Material::Soil);
    s.m.soil.remaining_q3 = s.m.soil.initial_q3;
    WorldEvent f;
    f.kind = FactKind::GeometryConfigured;
    tx.fact(f);
    tx.commit();
}
GeometrySnapshot WorldRuntime::geometry_snapshot() const {
    const auto &s = *state_;
    return {s.world,
            static_cast<bool>(s.geometry),
            s.m.geometry_revision,
            s.parcels.size(),
            s.edit_index.size(),
            s.sdf_cache.size(),
            s.dirty_bricks.size(),
            s.geometry ? s.geometry->config : GeometryConfig{},
            s.m.soil};
}
Material WorldRuntime::query_material(PositionM p) const {
    const auto &s = *state_;
    if (!s.geometry)
        throw std::invalid_argument("geometry is not configured");
    const auto q = quantized(p, s.geometry->config);
    if (!q)
        throw std::invalid_argument("geometry query must lie on the configured coordinate quantum");
    return material_at(geometry_view(s, limits_), *q);
}
std::uint64_t WorldRuntime::query_material_volume(BoxQ b, Material m) const {
    const auto &s = *state_;
    if (!s.geometry || m > Material::Rock || !box_valid(b) || b.min.x < -1000000 || b.min.y < -1000000 ||
        b.min.z < -1000000 || b.max.x > 1000000 || b.max.y > 1000000 || b.max.z > 1000000)
        throw std::invalid_argument("invalid material query");
    return material_volume(geometry_view(s, limits_), b, m);
}
double WorldRuntime::query_signed_distance(PositionM p) const {
    const auto &s = *state_;
    if (!s.geometry)
        throw std::invalid_argument("geometry is not configured");
    const auto q = quantized(p, s.geometry->config);
    if (!q)
        throw std::invalid_argument("SDF query must lie on the configured coordinate quantum");
    return signed_distance(geometry_view(s, limits_), *q);
}
bool WorldRuntime::spatially_clear(PositionM a, PositionM b, std::int32_t half) const {
    profiling::Scope profile(profiling::Category::Spatial);
    const auto &s = *state_;
    if (!finite(a) || !finite(b))
        return false;
    return !s.geometry ||
           historical_clear(*s.geometry, s.geometry_edits, s.edit_index, a, b, half, limits_.geometry_partition_cells);
}
std::uint64_t WorldRuntime::carried_soil_ug(EntityId id) const {
    const auto &s = *state_;
    const auto it = s.carriers.find(id);
    if (it == s.carriers.end())
        return 0;
    const auto &c = s.geometry->config;
    return s.parcels.at(it->second).remaining_q3 * (c.dry_ug_per_q3 + c.water_ug_per_q3);
}
std::int32_t WorldRuntime::body_half(EntityId id) const {
    const auto &s = *state_;
    if (!s.geometry)
        return 0;
    const auto ant = s.ants.get(s.ants.index.at(id));
    return ant.carried_food.total_ug() || s.carriers.contains(id) ? s.geometry->config.loaded_half_q
                                                                  : s.geometry->config.body_half_q;
}
void WorldRuntime::index_position(Transaction &tx, EntityId id, PositionM from, PositionM to) {
    auto &s = *state_;
    index_contact(tx,id,to);
    if (!s.geometry)
        return;
    tx.spatial_index.erase({spatial_key(from), id.value});
    tx.spatial_index.set({spatial_key(to), id.value}, 1);
    const auto it = s.carriers.find(id);
    if (it != s.carriers.end()) {
        auto parcel = s.parcels.at(it->second);
        parcel.position = to;
        tx.parcels.set(parcel.id, parcel);
    }
}
Neighborhood WorldRuntime::query_neighborhood(AntRef ref, double radius) const {
    const auto &s = *state_;
    const auto ant = query_ant(ref);
    if (!ant || !std::isfinite(radius) || radius < 0)
        throw std::invalid_argument("invalid neighborhood query");
    Neighborhood result;
    auto candidate = [&](std::uint64_t id, std::uint8_t kind) {
        ++result.candidates_examined;
        const auto p = kind == 1 ? s.ants.get(s.ants.index.at(EntityId{id})).position
                                 : s.foods.rows[s.foods.index.at(ResourceId{id})].position;
        if (distance(ant->position, p) > radius || (p != ant->position && !spatially_clear(ant->position, p)))
            return;
        if (kind == 1 && id != ref.id.value)
            result.ants.push_back({s.world, {id}});
        if (kind == 2)
            result.food.push_back({s.world, {id}});
    };
    if (!s.geometry) {
        for (const auto &row : s.ants.identities)
            candidate(row.id.value, 1);
        for (const auto &row : s.foods.rows)
            candidate(row.id.value, 2);
    } else {
        const auto p = ant->position;
        const auto lo = spatial_key({p.x - radius, p.y - radius, p.z - radius}),
                   hi = spatial_key({p.x + radius, p.y + radius, p.z + radius});
        for (auto key : overlapping_bricks({lo, {hi.x + 1, hi.y + 1, hi.z + 1}}, 1, limits_.neighborhood_buckets)) {
            auto it = s.spatial_index.lower_bound({key, 0});
            while (it != s.spatial_index.end() && it->first.first == key) {
                candidate(it->first.second, it->second);
                ++it;
            }
        }
    }
    auto by_id = [](const auto &a, const auto &b) { return a.id < b.id; };
    std::sort(result.ants.begin(), result.ants.end(), by_id);
    std::sort(result.food.begin(), result.food.end(), by_id);
    return result;
}
Route3D WorldRuntime::query_route(AntRef ref, PositionM destination) const {
    const auto &s = *state_;
    const auto ant = query_ant(ref);
    if (!ant || !s.geometry)
        throw std::invalid_argument("route requires a geometry actor");
    const auto &c = s.geometry->config;
    const auto start = quantized(ant->position, c), goal = quantized(destination, c);
    Route3D route;
    route.world = s.world;
    route.geometry_revision = s.m.geometry_revision;
    route.half_extent_q = body_half(ref.id);
    if (!start || !goal || !inside(destination, s.config) ||
        !spatially_clear(destination, destination, route.half_extent_q))
        return route;
    using Node = std::pair<std::uint64_t, PointQ>;
    std::priority_queue<Node, std::vector<Node>, std::greater<Node>> open(std::greater<Node>{}, std::vector<Node>(0));
    std::map<PointQ, std::pair<PointQ, std::uint64_t>> parents;
    auto heuristic = [&](PointQ p) {
        return static_cast<std::uint64_t>(std::abs(p.x - goal->x) + std::abs(p.y - goal->y) + std::abs(p.z - goal->z));
    };
    open.emplace(heuristic(*start), *start);
    parents.emplace(*start, std::pair{*start, std::uint64_t{0}});
    std::set<PointQ> closed;
    while (!open.empty()) {
        const auto p = open.top().second;
        open.pop();
        if (closed.contains(p))
            continue;
        closed.insert(p);
        ++route.examined;
        if (p == *goal) {
            route.found = true;
            auto q = p;
            for (;;) {
                route.points.push_back(q);
                if (q == *start)
                    break;
                q = parents.at(q).first;
            }
            std::reverse(route.points.begin(), route.points.end());
            break;
        }
        for (auto q : portal_neighbors(geometry_view(s, limits_), p, route.half_extent_q, s.config)) {
            if (closed.contains(q))
                continue;
            const auto cost = parents.at(p).second + 1;
            auto it = parents.find(q);
            if (it != parents.end() && it->second.second <= cost)
                continue;
            if (it == parents.end() && parents.size() >= limits_.navigation_nodes) {
                route.budget_exhausted = true;
                return route;
            }
            parents[q] = {p, cost};
            open.emplace(cost + heuristic(q), q);
        }
    }
    return route;
}
std::vector<Portal3D> WorldRuntime::query_portals(AntRef ref) const {
    const auto &s = *state_;
    const auto ant = query_ant(ref);
    if (!ant || !s.geometry)
        throw std::invalid_argument("local portals require a geometry actor");
    const auto p = *quantized(ant->position, s.geometry->config);
    const auto half = body_half(ref.id);
    std::vector<Portal3D> result(0);
    for (auto q : portal_neighbors(geometry_view(s, limits_), p, half, s.config))
        result.push_back({s.world, s.m.geometry_revision, p, q, half});
    return result;
}
bool WorldRuntime::validate_route(AntRef ref, const Route3D &route) const {
    const auto &s = *state_;
    const auto ant = query_ant(ref);
    if (!ant || !s.geometry || route.world != s.world || !route.found || route.points.empty() ||
        route.half_extent_q != body_half(ref.id) ||
        quantized(ant->position, s.geometry->config) != route.points.front())
        return false;
    auto previous = route.points.front();
    for (auto point : route.points) {
        const auto length = std::abs(static_cast<std::int64_t>(point.x) - previous.x) +
                            std::abs(static_cast<std::int64_t>(point.y) - previous.y) +
                            std::abs(static_cast<std::int64_t>(point.z) - previous.z);
        if (length > 1 || !inside(physical(point, s.geometry->config), s.config) ||
            !clear_sweep(geometry_view(s, limits_), previous, point, route.half_extent_q))
            return false;
        previous = point;
    }
    return true;
}
std::vector<GeometryEdit> WorldRuntime::geometry_edits() const {
    std::vector<GeometryEdit> result(0);
    for (const auto &[id, e] : state_->geometry_edits) {
        (void)id;
        result.push_back(e);
    }
    return result;
}
std::vector<SoilParcel> WorldRuntime::soil_parcels() const {
    std::vector<SoilParcel> result(0);
    for (const auto &[id, p] : state_->parcels) {
        (void)id;
        result.push_back(p);
    }
    return result;
}
std::optional<SoilParcel> WorldRuntime::query_parcel(SoilParcelRef ref) const {
    const auto it = state_->parcels.find(ref.id);
    return ref.world != state_->world || it == state_->parcels.end() ? std::optional<SoilParcel>{} : it->second;
}
std::vector<PointQ> WorldRuntime::dirty_geometry_bricks() const {
    std::vector<PointQ> result(0);
    for (const auto &[key, version] : state_->dirty_bricks) {
        (void)version;
        result.push_back(key);
    }
    return result;
}
void WorldRuntime::rebuild_geometry_cache(std::span<const PointQ> keys) {
    auto &s = *state_;
    if (!s.geometry)
        throw std::invalid_argument("geometry is not configured");
    Transaction tx(s, limits_);
    const auto &c = s.geometry->config;
    for (auto key : keys) {
        if (std::abs(static_cast<std::int64_t>(key.x)) > 100000 ||
            std::abs(static_cast<std::int64_t>(key.y)) > 100000 || std::abs(static_cast<std::int64_t>(key.z)) > 100000)
            throw std::invalid_argument("cache coordinate limit");
        if (!s.sdf_cache.contains(key) && s.sdf_cache.size() >= limits_.sdf_bricks)
            throw std::length_error("SDF cache budget exceeded");
        SdfBrick brick;
        brick.key = key;
        brick.source_revision = s.m.geometry_revision;
        std::size_t n = 0;
        for (std::int32_t x = 0; x <= c.brick_q; x += c.sample_step_q)
            for (std::int32_t y = 0; y <= c.brick_q; y += c.sample_step_q)
                for (std::int32_t z = 0; z <= c.brick_q; z += c.sample_step_q)
                    brick.distance_m[n++] =
                        signed_distance(geometry_view(s, limits_),
                                        {key.x * c.brick_q + x, key.y * c.brick_q + y, key.z * c.brick_q + z});
        tx.sdf_cache.set(key, brick);
        tx.dirty_bricks.erase(key);
    }
    tx.commit(); // Disposable cache warmth is not an ecological fact or checkpoint field.
}
void WorldRuntime::discard_geometry_cache() {
    auto &s = *state_;
    Transaction tx(s, limits_);
    while (!s.sdf_cache.empty())
        tx.sdf_cache.erase(s.sdf_cache.begin()->first);
    while (!s.dirty_bricks.empty())
        tx.dirty_bricks.erase(s.dirty_bricks.begin()->first);
    tx.commit();
}
std::optional<SdfBrick> WorldRuntime::query_sdf_brick(PointQ key) const {
    const auto &s = *state_;
    const auto it = s.sdf_cache.find(key);
    return s.dirty_bricks.contains(key) || it == s.sdf_cache.end() ? std::optional<SdfBrick>{} : it->second;
}
std::optional<ExcavatorState> WorldRuntime::query_excavator(AntRef ref) const {
    const auto it = state_->excavators.find(ref.id);
    return ref.world != state_->world || it == state_->excavators.end() ? std::optional<ExcavatorState>{} : it->second;
}
} // namespace antworld
