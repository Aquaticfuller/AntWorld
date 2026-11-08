#pragma once
#include "checkpoint_codec.hpp"
#include "surface_internal.hpp"
#include "behavior_rng.hpp"
#include <algorithm>
#include <map>
#include <set>

namespace antworld::detail {
inline constexpr std::array counter_fields{
    &ForagingCounters::decisions, &ForagingCounters::moves, &ForagingCounters::explore_moves,
    &ForagingCounters::trail_moves, &ForagingCounters::memory_moves, &ForagingCounters::return_moves,
    &ForagingCounters::trips_started, &ForagingCounters::collections, &ForagingCounters::collection_attempts,
    &ForagingCounters::deliveries, &ForagingCounters::revisits, &ForagingCounters::failed_actions,
    &ForagingCounters::memory_failures, &ForagingCounters::collected_outbound_moves
};
template <typename S> void write_surface(Writer& w, const S& s) {
    w.put(s.surface != nullptr, 1); if (!s.surface) return;
    const auto& c = s.surface->config; const auto& p = s.surface->behavior;
    w.position(c.origin_m); w.put(c.width, 4); w.put(c.height, 4); w.real(c.cell_size_m);
    w.put(p.trails_enabled, 1); w.put(p.memory_enabled, 1);
    w.put(p.sensing_radius_cells, 4); w.put(p.route_capacity, 4); w.put(p.max_trip_moves, 4);
    w.time(p.step_duration); w.time(p.decision_delay); w.time(p.memory_lifetime); w.time(p.field_interval);
    w.real(p.trail_half_life_s); w.real(p.deposit_units); w.real(p.trail_cap_units); w.real(p.trail_cutoff_units);
    w.put(p.explore_weight, 4); w.put(p.persistence_weight, 4); w.put(p.trail_weight, 4);
    w.put(s.surface->walkable.size()); for (const auto b : s.surface->walkable) w.put(b, 1);
    for (const auto member : counter_fields) w.put(s.m.foraging.*member);
    w.real(s.m.foraging.deposited_units); w.put(s.m.maintenance.value);
    w.put(s.foragers.size());
    for (const auto& [id, f] : s.foragers) {
        w.put(id.value); w.put(f.enabled, 1); w.put(static_cast<std::uint8_t>(f.mode), 1); w.put(static_cast<std::uint8_t>(f.heading), 1);
        w.put(f.decisions); w.put(f.trip_moves); w.put(f.collections); w.put(f.path_size, 4); w.put(f.memory_size, 4);
        for (const auto cell : f.path) w.cell(cell);
        for (const auto cell : f.memory) w.cell(cell);
        w.time(f.learned_at); w.put(f.last_collected.value); w.put(f.wake.value); w.put(f.action.value);
    }
    w.put(s.trails.size());
    for (const auto& [k, t] : s.trails) { w.put(k.colony.value); w.cell(k.cell); w.real(t.units); w.time(t.updated); }
    w.put(s.visits.size()); for (const auto& [cell, n] : s.visits) { w.cell(cell); w.put(n); }
    w.put(s.edges.size()); for (const auto& [edge, n] : s.edges) { w.cell(edge.a); w.cell(edge.b); w.put(n); }
    w.put(s.discoveries.size()); for (const auto& [id, d] : s.discoveries) { w.put(id.value); w.time(d.time); w.put(d.actor.value); }
}
template <typename S> void read_surface(Reader& r, S& s, const RuntimeLimits& limits) {
    if (!r.flag()) return;
    auto surface = std::make_shared<SurfaceDefinition>(); auto& c = surface->config; auto& p = surface->behavior;
    c.origin_m = r.position(); c.width = static_cast<std::uint32_t>(r.get(4)); c.height = static_cast<std::uint32_t>(r.get(4)); c.cell_size_m = r.real();
    p.trails_enabled = r.flag(); p.memory_enabled = r.flag();
    p.sensing_radius_cells = static_cast<std::uint32_t>(r.get(4)); p.route_capacity = static_cast<std::uint32_t>(r.get(4));
    p.max_trip_moves = static_cast<std::uint32_t>(r.get(4));
    p.step_duration = r.time(); p.decision_delay = r.time(); p.memory_lifetime = r.time(); p.field_interval = r.time();
    p.trail_half_life_s = r.real(); p.deposit_units = r.real(); p.trail_cap_units = r.real(); p.trail_cutoff_units = r.real();
    p.explore_weight = static_cast<std::uint32_t>(r.get(4)); p.persistence_weight = static_cast<std::uint32_t>(r.get(4));
    p.trail_weight = static_cast<std::uint32_t>(r.get(4)); validate_surface(c, p, s.config, limits);
    const auto cells = r.count(limits.surface_cells, 1);
    ensure(cells == std::uint64_t{c.width}*c.height, "surface cell count mismatch"); surface->walkable.resize(cells);
    for (auto& value : surface->walkable) value = static_cast<std::uint8_t>(r.flag());
    ensure(std::any_of(surface->walkable.begin(), surface->walkable.end(), [](auto v) { return v != 0; }), "empty walkable surface");
    s.surface = surface;
    for (const auto member : counter_fields) s.m.foraging.*member = r.get();
    s.m.foraging.deposited_units = r.real(); s.m.maintenance = {r.get()};
    ensure(std::isfinite(s.m.foraging.deposited_units) && s.m.foraging.deposited_units >= 0, "invalid cumulative trail quantity");
    const auto agents = r.count(limits.entities, 1099);
    for (std::size_t i = 0; i < agents; ++i) {
        const EntityId id{r.get()}; ForagerState f;
        f.enabled = r.flag(); f.mode = static_cast<BehaviorMode>(r.get(1)); f.heading = static_cast<Direction>(r.get(1));
        f.decisions = r.get(); f.trip_moves = r.get(); f.collections = r.get();
        f.path_size = static_cast<std::uint32_t>(r.get(4)); f.memory_size = static_cast<std::uint32_t>(r.get(4));
        for (auto& cell : f.path) cell = r.cell();
        for (auto& cell : f.memory) cell = r.cell();
        f.learned_at = r.time(); f.last_collected = {r.get()}; f.wake = {r.get()}; f.action = {r.get()};
        ensure(s.ants.index.contains(id) && f.mode <= BehaviorMode::Rest && f.heading <= Direction::West && f.path_size &&
            f.path_size <= p.route_capacity && f.memory_size <= p.route_capacity && f.learned_at <= s.m.now &&
            (p.memory_enabled || f.memory_size == 0) && (!f.last_collected.value || s.foods.index.contains(f.last_collected)) &&
            s.foragers.emplace(id, f).second, "invalid forager state");
    }
    const auto trail_count = r.count(limits.trail_cells, 32);
    ensure(p.trails_enabled || trail_count == 0, "trail cells in disabled treatment");
    for (std::size_t i = 0; i < trail_count; ++i) {
        const TrailKey key{{r.get()}, r.cell()}; const Trail t{r.real(), r.time()};
        ensure(s.colonies.index.contains(key.colony) && surface->open(key.cell) && std::isfinite(t.units) &&
            t.units > 0 && t.units <= p.trail_cap_units && t.updated <= s.m.now && s.trails.emplace(key, t).second, "invalid sparse trail");
    }
    const auto visits = r.count(limits.surface_cells, 16);
    for (std::size_t i = 0; i < visits; ++i) {
        const auto cell = r.cell(); const auto n = r.get();
        ensure(surface->open(cell) && s.visits.emplace(cell, n).second, "invalid coverage cell");
    }
    const auto edges = r.count(cells*2, 24);
    for (std::size_t i = 0; i < edges; ++i) {
        const EdgeKey edge{r.cell(), r.cell()}; const auto n = r.get();
        ensure(surface->open(edge.a) && surface->open(edge.b) && edge.a < edge.b && adjacent(edge.a, edge.b) && n &&
            s.edges.emplace(edge, n).second, "invalid traversed edge");
    }
    const auto discoveries = r.count(limits.entities, 24);
    for (std::size_t i = 0; i < discoveries; ++i) {
        const ResourceId resource{r.get()}; const Discovery d{r.time(), {r.get()}};
        ensure(s.foods.index.contains(resource) && s.foragers.contains(d.actor) && d.time <= s.m.now &&
            s.discoveries.emplace(resource, d).second, "invalid discovery record");
    }
    for (const auto& colony : s.colonies.rows) ensure(surface->locate(colony.nest_position).has_value(), "nest outside walkable surface");
    for (std::size_t i = 0; i < s.ants.size(); ++i) ensure(surface->locate(s.ants.get(i).position).has_value(), "ant outside walkable surface");
    for (const auto& food : s.foods.rows) {
        const auto cell = surface->locate(food.position);
        ensure(cell && s.food_cells.emplace(*cell, food.id).second, "invalid surface food placement");
    }
    ensure(p.trails_enabled == (s.m.maintenance.value != 0), "field schedule flag mismatch");
    if (p.trails_enabled) {
        ensure(s.queue_index.contains(s.m.maintenance) && s.queue.at(s.queue_index.at(s.m.maintenance)).kind == ScheduledEvent::Kind::TrailMaintenance,
            "missing field maintenance event");
    }
    for (const auto& [id, f] : s.foragers) {
        const auto ant = s.ants.get(s.ants.index.at(id));
        const auto home = surface->locate(s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position);
        ensure(ant.caste == Caste::Worker && (ant.stage == LifeStage::Adult || ant.stage == LifeStage::Dead) &&
            (!f.enabled || ant.alive()) && f.path[0] == *home && f.path[f.path_size-1] == *surface->locate(ant.position), "invalid individual route endpoints");
        auto check_route = [&](const auto& route, std::uint32_t size) {
            for (std::size_t i = 0; i < route.size(); ++i) {
                if (i >= size) { ensure(route[i] == Cell{}, "noncanonical unused memory slot"); continue; }
                ensure(surface->open(route[i]) && (!i || adjacent(route[i-1], route[i])), "route crosses a blocked/nonlocal step");
                for (std::size_t j = 0; j < i; ++j) ensure(route[j] != route[i], "loop in erased route");
            }
        };
        check_route(f.path, f.path_size); check_route(f.memory, f.memory_size);
        if (f.memory_size) ensure(f.memory[0] == *home && f.last_collected.value &&
            f.memory[f.memory_size-1] == *surface->locate(s.foods.rows[s.foods.index.at(f.last_collected)].position), "memory has no experienced food endpoint");
        ensure(f.enabled ? ((f.wake.value != 0) != (f.action.value != 0)) : (!f.wake.value && !f.action.value), "invalid individual wake/action ownership");
        for (const auto pending : {f.wake, f.action}) if (pending.value) {
            ensure(s.queue_index.contains(pending), "missing individual pending event");
            const auto& e = s.queue.at(s.queue_index.at(pending));
            ensure(e.actor == id && ((pending == f.wake && e.kind == ScheduledEvent::Kind::Wake) ||
                (pending == f.action && e.key.phase == Phase::Resolution && e.observed_position_revision == ant.position_revision)), "foreign or stale individual event");
        }
    }
}
inline bool locally_reachable(const SurfaceDefinition& surface, Cell from, Cell to) {
    std::array<std::pair<Cell, std::uint32_t>, perception_storage_capacity> work{}; work[0] = {from, 0}; std::size_t size = 1;
    for (std::size_t i = 0; i < size; ++i) {
        if (work[i].first == to) return true;
        if (work[i].second == surface.behavior.sensing_radius_cells) continue;
        for (unsigned d = 0; d < 4; ++d) {
            const auto next = neighbor(work[i].first, static_cast<Direction>(d)); if (!surface.open(next)) continue;
            bool seen = false; for (std::size_t j = 0; j < size; ++j) if (work[j].first == next) seen = true;
            if (!seen) { ensure(size < work.size(), "perception audit overflow"); work[size++] = {next, work[i].second+1}; }
        }
    }
    return false;
}
template <typename S> void validate_surface_evidence(const S& s) {
    if (!s.surface) {
        for (const auto& e : s.journal) ensure(e.deposited_units == 0 && !e.forgot_memory, "surface evidence without configuration");
        return;
    }
    const auto& surface = *s.surface; const auto& p = surface.behavior;
    typename S::Foragers audit_agents; typename S::Trails audit_trails; typename S::Visits audit_visits;
    typename S::Edges audit_edges; typename S::Discoveries audit_discoveries;
    std::map<EntityId, PositionM> positions; std::map<EntityId, FoodMass> cargo;
    std::map<ResourceId, FoodMass> remaining;
    ForagingCounters counts; bool configured = false;
    for (const auto& e : s.journal) {
        if (e.kind == FactKind::SurfaceConfigured) {
            ensure(!configured && e.id == EventId{1} && e.position == surface.config.origin_m && !e.actor.value && !e.colony.value &&
                !e.resource.value, "invalid surface configuration evidence"); configured = true;
        }
        if (e.kind == FactKind::AntSeeded) positions[e.actor] = e.position;
        if (e.kind == FactKind::BehaviorChanged && audit_agents.contains(e.actor))
            audit_agents.at(e.actor).enabled = e.payload == static_cast<std::uint64_t>(IndividualBehavior::Forage);
        if (e.kind == FactKind::CargoIngested) cargo[e.actor] = subtract(cargo[e.actor], e.transferred);
        if (e.kind == FactKind::FoodSeeded) remaining[e.resource] = e.transferred;
        if (e.kind == FactKind::ForagingStarted) {
            ensure(configured && s.foragers.contains(e.actor) && !audit_agents.contains(e.actor) && e.position == positions[e.actor], "invalid autonomy activation evidence");
            auto& f = audit_agents[e.actor]; f.enabled = true; f.path[0] = *surface.locate(e.position); f.path_size = 1;
            f.heading = initial_heading(s.seed, e.actor); audit_visits.try_emplace(f.path[0], 0);
        }
        if (e.kind == FactKind::ForagingDecision) {
            ensure(audit_agents.contains(e.actor) && audit_agents.at(e.actor).enabled && e.position == positions[e.actor] &&
                e.reason != DecisionReason::None, "invalid individual decision evidence");
            auto& f = audit_agents.at(e.actor); ++f.decisions; ++counts.decisions; f.mode = e.mode;
            ensure(e.payload == f.decisions, "individual RNG/decision counter mismatch");
            if (e.forgot_memory) { f.memory = {}; f.memory_size = 0; ++counts.memory_failures; }
            if (e.mode == BehaviorMode::Collect) ++counts.collection_attempts;
            if (e.resource.value) {
                ensure(remaining.contains(e.resource) && remaining[e.resource].total_ug() &&
                    locally_reachable(surface, *surface.locate(e.position), *surface.locate(s.foods.rows[s.foods.index.at(e.resource)].position)),
                    "discovery has no local reachable food evidence");
                audit_discoveries.try_emplace(e.resource, Discovery{e.time, e.actor});
            }
        }
        if (e.kind == FactKind::Moved) {
            const auto old = surface.locate(positions[e.actor]), to = surface.locate(e.position);
            ensure(old && to && adjacent(*old, *to), "movement history crosses blocked/nonlocal surface");
            if (audit_agents.contains(e.actor)) {
                auto& f = audit_agents.at(e.actor); ensure(f.enabled && e.mode == f.mode, "movement behavior evidence mismatch");
                f.heading = direction(*old, *to); ++f.trip_moves; ++counts.moves;
                if (e.mode == BehaviorMode::Return) ++counts.return_moves;
                else if (e.mode == BehaviorMode::FollowMemory) ++counts.memory_moves;
                else if (e.mode == BehaviorMode::FollowTrail) ++counts.trail_moves;
                else ++counts.explore_moves;
                if (*old == f.path[0] && cargo[e.actor].total_ug() == 0) { ++counts.trips_started; f.trip_moves = 1; }
                auto found = std::find(f.path.begin(), f.path.begin()+f.path_size, *to);
                if (found != f.path.begin()+f.path_size) {
                    const auto n = static_cast<std::uint32_t>(found-f.path.begin()+1);
                    std::fill(f.path.begin()+n, f.path.end(), Cell{}); f.path_size = n;
                } else {
                    ensure(f.path_size < p.route_capacity, "historical return trace overflow"); f.path[f.path_size++] = *to;
                }
                if (*to == f.path[0] && !cargo[e.actor].total_ug()) { f.mode = BehaviorMode::Explore; f.trip_moves = 0; }
                ++audit_visits[*to]; ++audit_edges[{std::min(*old, *to), std::max(*old, *to)}];
                if (e.deposited_units > 0) {
                    // The exact saturated arithmetic below validates quantity; subtraction can
                    // round slightly above deposit_units even for a valid addition.
                    ensure(p.trails_enabled && cargo[e.actor].total_ug(), "deposit without carried food");
                    const TrailKey key{e.colony, *to}; const auto it = audit_trails.find(key);
                    const auto old_amount = it == audit_trails.end() ? 0 : trail_at(it->second, e.time, p);
                    const auto next = std::min(p.trail_cap_units, old_amount+p.deposit_units);
                    ensure(e.deposited_units == next-old_amount, "invalid saturated deposit evidence");
                    audit_trails[key] = {next, e.time}; counts.deposited_units += e.deposited_units;
                } else if (p.trails_enabled && cargo[e.actor].total_ug()) {
                    const TrailKey key{e.colony, *to}; const auto it = audit_trails.find(key);
                    ensure(it != audit_trails.end() && trail_at(it->second, e.time, p) == p.trail_cap_units, "missing deposit evidence");
                    audit_trails[key] = {p.trail_cap_units, e.time};
                }
            } else ensure(e.deposited_units == 0, "non-forager deposited a trail");
            positions[e.actor] = e.position;
        }
        if (e.kind == FactKind::FoodCollected) {
            remaining[e.resource] = subtract(remaining[e.resource], e.transferred);
            if (audit_agents.contains(e.actor)) {
                auto& f = audit_agents.at(e.actor); ensure(f.enabled, "dead forager collected");
                ++counts.collections; ++f.collections; counts.collected_outbound_moves = add(counts.collected_outbound_moves, f.trip_moves);
                if (f.last_collected == e.resource) ++counts.revisits;
                f.last_collected = e.resource; f.mode = BehaviorMode::Return;
                if (p.memory_enabled) { f.memory = f.path; f.memory_size = f.path_size; f.learned_at = e.time; }
            }
            cargo[e.actor] = sum(cargo[e.actor], e.transferred);
        }
        if (e.kind == FactKind::FoodDelivered) {
            ensure(surface.locate(e.position) == surface.locate(s.colonies.rows[s.colonies.index.at(e.colony)].nest_position), "delivery crosses surface cells");
            cargo[e.actor] = subtract(cargo[e.actor], e.transferred);
            if (audit_agents.contains(e.actor)) { auto& f = audit_agents.at(e.actor); ++counts.deliveries; f.mode = BehaviorMode::Explore; f.trip_moves = 0; }
        }
        if (e.kind == FactKind::ActionRejected && audit_agents.contains(e.actor) && audit_agents.at(e.actor).enabled) {
            // Lifecycle rejections are not autonomous action attempts.
            if (e.outcome != Outcome::InvalidTransition && e.outcome != Outcome::AlreadyDead && e.outcome != Outcome::DeadActor) ++counts.failed_actions;
        }
        if (e.kind == FactKind::AntDied && audit_agents.contains(e.actor)) audit_agents.at(e.actor).enabled = false;
        if (e.kind == FactKind::TrailMaintenance) {
            ensure(p.trails_enabled && !e.actor.value && !e.colony.value && !e.resource.value, "invalid field maintenance fact");
            std::uint64_t removed = 0;
            for (auto i = audit_trails.begin(); i != audit_trails.end();) {
                const auto value = trail_at(i->second, e.time, p);
                if (value == 0) { i = audit_trails.erase(i); ++removed; }
                else { i->second = {value, e.time}; ++i; }
            }
            ensure(e.payload == removed, "invalid sparse field cleanup count");
        }
        if (e.kind != FactKind::Moved) ensure(e.deposited_units == 0, "deposit outside a real movement fact");
        if (e.kind != FactKind::ForagingDecision) ensure(!e.forgot_memory && e.reason == DecisionReason::None, "decision metadata on non-decision fact");
    }
    ensure(configured && audit_agents.size() == s.foragers.size() && counts == s.m.foraging &&
        audit_trails == s.trails && audit_visits == s.visits && audit_edges == s.edges && audit_discoveries == s.discoveries,
        "surface counters/fields disagree with committed evidence");
    for (const auto& [id, f] : s.foragers) {
        auto expected = audit_agents.at(id); expected.wake = f.wake; expected.action = f.action;
        ensure(f == expected, "individual memory/path disagrees with experienced history");
    }
}
} // namespace antworld::detail
