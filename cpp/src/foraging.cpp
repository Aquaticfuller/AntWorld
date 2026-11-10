#include "state.hpp"
#include "behavior_rng.hpp"
#include "spatial_navigation.hpp"
#include <algorithm>

namespace antworld {
using namespace detail;
namespace {
SimTime later(SimTime now, SimTime delay) {
    if (delay.milliseconds <= 0 || now.milliseconds > INT64_MAX-delay.milliseconds)
        throw std::overflow_error("foraging schedule time exhausted");
    return {now.milliseconds+delay.milliseconds};
}
std::uint64_t next_count(std::uint64_t n) { bump(n); return n; }
}
namespace detail {
void validate_surface(const SurfaceConfig& c, const BehaviorConfig& p, const WorldConfig& world, const RuntimeLimits& limits) {
    const auto cells = std::uint64_t{c.width}*c.height;
    if (!c.width || !c.height || c.width >= static_cast<std::uint32_t>(INT32_MAX) || c.height >= static_cast<std::uint32_t>(INT32_MAX) ||
        cells > limits.surface_cells || !std::isfinite(c.cell_size_m) || c.cell_size_m <= 0 ||
        !inside(c.origin_m, world) || !inside({c.origin_m.x+(c.width-1)*c.cell_size_m, c.origin_m.y,
            c.origin_m.z+(c.height-1)*c.cell_size_m}, world)) throw std::invalid_argument("invalid surface fixture or host cell budget");
    if (p.sensing_radius_cells < 1 || p.sensing_radius_cells > 3 || p.route_capacity < 2 || p.route_capacity > route_storage_capacity ||
        p.max_trip_moves < p.route_capacity || p.max_trip_moves > 1000000 || p.step_duration.milliseconds <= 0 ||
        p.decision_delay.milliseconds <= 0 || p.field_interval.milliseconds <= 0 || p.memory_lifetime.milliseconds < 0 ||
        c.cell_size_m/(static_cast<double>(p.step_duration.milliseconds)/1000.0) > world.max_speed_m_per_s ||
        !std::isfinite(p.trail_half_life_s) || p.trail_half_life_s <= 0 ||
        !std::isfinite(p.deposit_units) || p.deposit_units <= 0 || !std::isfinite(p.trail_cap_units) || p.trail_cap_units <= 0 ||
        p.trail_cap_units > 1000000 || p.deposit_units > p.trail_cap_units || !std::isfinite(p.trail_cutoff_units) ||
        p.trail_cutoff_units <= 0 || p.trail_cutoff_units > p.trail_cap_units || !p.explore_weight ||
        p.explore_weight > 1000000 || p.persistence_weight > 1000000 || p.trail_weight > 1000000)
        throw std::invalid_argument("invalid ENGINEERING_FIXTURE behavior parameters");
}
}
void WorldRuntime::configure_surface(const SurfaceConfig& config, std::span<const Cell> blocked, const BehaviorConfig& behavior) {
    auto& s = *state_;
    if (s.surface || s.geometry || s.social || s.m.now != SimTime{} || s.m.watermark || !s.queue.empty() || !s.colonies.rows.empty() ||
        s.ants.size() || !s.foods.rows.empty()) throw std::invalid_argument("configure the surface before seeding entities or events");
    validate_surface(config, behavior, s.config, limits_);
    auto surface = std::make_shared<SurfaceDefinition>(); surface->config = config; surface->behavior = behavior;
    surface->walkable.resize(static_cast<std::size_t>(config.width)*config.height, 1);
    for (const auto cell : blocked) {
        if (!surface->contains(cell)) throw std::invalid_argument("blocked cell outside surface");
        surface->walkable[static_cast<std::size_t>(cell.z)*config.width+static_cast<std::size_t>(cell.x)] = 0;
    }
    if (std::none_of(surface->walkable.begin(), surface->walkable.end(), [](auto v) { return v != 0; }))
        throw std::invalid_argument("surface has no walkable cell");
    Transaction tx(s, limits_); s.surface = surface;
    WorldEvent fact; fact.kind = FactKind::SurfaceConfigured; fact.position = config.origin_m; tx.fact(fact);
    if (behavior.trails_enabled) {
        ScheduledEvent e; e.kind = ScheduledEvent::Kind::TrailMaintenance;
        e.key = {later(s.m.now, behavior.field_interval), Phase::Environment, 1, 0, 0}; e.issued_at = s.m.now;
        s.m.maintenance = tx.insert(e);
    }
    tx.commit();
}
void WorldRuntime::start_foraging(AntRef ref) {
    if (state_->physiology.contains(ref.id) && ref.world == state_->world) { set_behavior(ref, IndividualBehavior::Forage); return; }
    auto& s = *state_; const auto ant = query_ant(ref);
    if (!s.surface || !ant || s.foragers.contains(ref.id) ||
        ant->stage != LifeStage::Adult || ant->caste != Caste::Worker || ant->carried_food.total_ug() || !ant->carrying_capacity_ug)
        throw std::invalid_argument("invalid autonomous worker seed");
    for (const auto& [key, e] : s.queue) {
        (void)key;
        if (e.actor == ant->id && e.key.phase == Phase::Resolution)
            throw std::invalid_argument("cannot activate a worker with externally pending actions");
    }
    Transaction tx(s, limits_);
    ForagerState f;
    prepare_forager(tx,*ant,f);
    f.enabled=true;
    ScheduledEvent wake; wake.kind = ScheduledEvent::Kind::Wake; wake.actor = ant->id;
    // Initial setup retains its zero-time wake. A dormant individual's first
    // activation later in the run cannot reopen an already executed phase.
    const auto wake_time = s.m.now == SimTime{} && !s.m.watermark ? s.m.now : later(s.m.now, s.surface->behavior.decision_delay);
    wake.key = {wake_time, Phase::Perception, 0, 0, 0}; wake.issued_at = s.m.now;
    f.wake = tx.insert(wake); tx.foragers.set(ant->id, f);
    tx.fact(forager_started(*ant,f.path[0],mixed_navigation(s)));
    tx.commit();
}
LocalObservation WorldRuntime::sense(AntRef ref) const {
    const auto& s = *state_; const auto ant = query_ant(ref);
    if (!s.surface || !ant) throw std::invalid_argument("local sensing requires an existing surface ant");
    const auto at=navigation_cell(s,ant->position);
    if (!at) throw std::invalid_argument("ant is not at a walkable surface cell");
    const auto& p = s.surface->behavior;
    LocalObservation result; result.time = s.m.now; result.current = *at;
    if (s.config.continuous_spatial_motion) {
        const auto f=s.foragers.find(ref.id);
        if (f!=s.foragers.end() && f->second.path_size>1 && f->second.heading<Direction::None)
            result.previous_step=static_cast<Direction>((static_cast<unsigned>(f->second.heading)+2)%4);
    }
    for (unsigned d = 0; d < 4; ++d) {
        const auto dir = static_cast<Direction>(d); const auto c = neighbor(*at, dir);
        if (!s.surface->open(c) || !spatially_clear(ant->position,navigation_waypoint(s,ref.id,c),body_half(ant->id))) continue;
        double trail = 0;
        if (p.trails_enabled) {
            const auto found = s.trails.find({ant->colony, c});
            if (found != s.trails.end()) trail = trail_at(found->second, s.m.now, p);
        }
        result.steps[result.step_count++] = {c, dir, trail};
    }
    struct Sample { Cell cell; std::uint32_t distance; Direction first; };
    std::array<Sample, perception_storage_capacity> sampled{};
    sampled[0] = {*at, 0, Direction::None}; std::uint32_t size = 1;
    for (std::uint32_t i = 0; i < size; ++i) {
        const auto sample = sampled[i];
        const auto physical_sample=s.config.continuous_spatial_motion && !i?ant->position:
            navigation_waypoint(s,ref.id,sample.cell);
        // A bounded local index lookup, never a scan or nearest-neighbor query of all food.
        const auto found = s.food_cells.find(sample.cell);
        if (found!=s.food_cells.end()) {
            const auto& food=s.foods.rows[s.foods.index.at(found->second)];
            if (food.remaining.total_ug() && (!s.config.continuous_spatial_motion || spatially_clear(physical_sample,food.position)))
                result.food[result.food_count++]={found->second,sample.cell,sample.distance,sample.first};
        }
        if (sample.distance == p.sensing_radius_cells) continue;
        for (unsigned d = 0; d < 4; ++d) {
            const auto dir = static_cast<Direction>(d); const auto cell = neighbor(sample.cell, dir);
            if (!s.surface->open(cell) || !spatially_clear(physical_sample,navigation_waypoint(s,ref.id,cell),
                s.config.continuous_spatial_motion?body_half(ref.id):0)) continue;
            bool seen = false; for (std::uint32_t j = 0; j < size; ++j) if (sampled[j].cell == cell) seen = true;
            if (seen) continue;
            if (size == sampled.size()) throw std::logic_error("local perception capacity exceeded");
            sampled[size++] = {cell, sample.distance+1, sample.distance ? sample.first : dir};
        }
    }
    result.sampled_cells = size; return result;
}
void WorldRuntime::resolve_wakes(Transaction& tx, const std::vector<ScheduledEvent>& wakes) {
    auto& s = *state_; const auto& config = s.surface->behavior;
    struct Ready {
        ScheduledEvent event;
        LocalObservation local;
        BehaviorDecision decision;
        PositionM destination;
        bool connector_return{},connector_clock{};
    };
    std::vector<Ready> ready(0); ready.reserve(wakes.size());
    // Freeze all local observations before committing any decisions or proposals.
    for (const auto& e : wakes) {
        const auto& f = s.foragers.at(e.actor); const auto ant = s.ants.get(s.ants.index.at(e.actor));
        if (!f.enabled || !ant.alive() || f.wake != e.id) throw std::logic_error("stale autonomous wake");
        Ready r;
        r.event=e;
        const auto it=s.connectors.find(ant.id);
        const auto* link=it==s.connectors.end() || it->second.size==1?nullptr:&it->second;
        const bool loaded=ant.carried_food.total_ug()!=0;
        const auto connector=[&](bool returning) {
            r.connector_return=returning;
            r.connector_clock=true;
            if (returning && link->cursor==0) {
                r.decision.action=loaded?ActionKind::DeliverFood:ActionKind::Rest;
                r.decision.mode=loaded?BehaviorMode::Deliver:BehaviorMode::Rest;
                r.decision.reason=loaded?DecisionReason::NestContact:DecisionReason::NoLegalStep;
                return;
            }
            const auto at_entrance=link->cursor+1==link->size;
            r.destination=returning && at_entrance && ant.position!=link->entrance()?link->entrance():
                link->points[returning?link->cursor-1:link->cursor+1];
            if (spatially_clear(ant.position,r.destination,body_half(ant.id))) {
                r.decision.action=ActionKind::Move;
                r.decision.mode=returning?BehaviorMode::Return:BehaviorMode::Explore;
                r.decision.reason=returning?DecisionReason::HomeTrace:DecisionReason::Search;
            }
        };
        if (link && (link->returning || link->cursor+1<link->size)) connector(link->returning);
        else {
            r.local=sense({s.world,e.actor});
            r.decision=choose_behavior(s.seed,e.actor,loaded,f,r.local,config);
            if (link && r.decision.action==ActionKind::DeliverFood) connector(true);
            else if (r.decision.action==ActionKind::Move) r.destination=navigation_waypoint(s,ant.id,r.decision.destination);
            else if (s.config.continuous_spatial_motion && r.decision.action==ActionKind::CollectFood) {
                const auto& food=s.foods.rows[s.foods.index.at(r.decision.resource)];
                if (!within_contact(ant.position,food.position,s.config)) {
                    r.destination={food.position.x,ant.position.y,food.position.z};
                    const bool reach=within_contact(r.destination,food.position,s.config) &&
                        spatially_clear(ant.position,r.destination,body_half(ant.id)) &&
                        spatially_clear(r.destination,food.position);
                    r.decision.action=reach?ActionKind::Move:ActionKind::Rest;
                    r.decision.mode=reach?BehaviorMode::Explore:BehaviorMode::Rest;
                    r.decision.reason=reach?DecisionReason::LocalFood:DecisionReason::NoLegalStep;
                }
            } else if (s.config.continuous_spatial_motion && r.decision.action==ActionKind::DeliverFood) {
                const auto nest=s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position;
                if (!within_contact(ant.position,nest,s.config)) {
                    r.destination=nest;
                    r.decision.action=ActionKind::Move;
                    r.decision.mode=BehaviorMode::Return;
                    r.decision.reason=DecisionReason::HomeTrace;
                }
            }
        }
        ready.push_back(r);
    }
    std::sort(ready.begin(), ready.end(), [](const auto& a, const auto& b) { return a.event.actor < b.event.actor; });
    for (const auto& r : ready) {
        const auto ant = s.ants.get(s.ants.index.at(r.event.actor)); auto f = s.foragers.at(ant.id);
        f.wake = {}; f.mode = r.decision.mode; bump(f.decisions); bump(s.m.foraging.decisions);
        if (r.decision.forget_memory) { f.memory_size = 0; f.memory = {}; bump(s.m.foraging.memory_failures); }
        ScheduledEvent action; action.actor = ant.id; action.issued_at = s.m.now;
        action.observed_position_revision = ant.position_revision;
        auto duration=r.connector_clock?s.geometry->config.move_duration:config.step_duration;
        if (s.config.continuous_spatial_motion && r.decision.action==ActionKind::Move) {
            const auto travel_ms=std::ceil(1000*distance(ant.position,r.destination)/s.config.max_speed_m_per_s);
            if (!std::isfinite(travel_ms) || travel_ms>=static_cast<double>(INT64_MAX))
                throw std::overflow_error("spatial travel exceeds the simulation clock");
            duration.milliseconds=std::max(duration.milliseconds,static_cast<std::int64_t>(travel_ms));
        }
        action.key={later(s.m.now,duration),Phase::Resolution,0,0,0};
        switch (r.decision.action) {
        case ActionKind::Move: action.kind=ScheduledEvent::Kind::Move; action.destination=r.destination; break;
        case ActionKind::CollectFood:
            action.kind = ScheduledEvent::Kind::CollectFood; action.resource = r.decision.resource;
            action.requested_ug = ant.carrying_capacity_ug; bump(s.m.foraging.collection_attempts); break;
        case ActionKind::DeliverFood: action.kind = ScheduledEvent::Kind::DeliverFood; break;
        case ActionKind::Rest: action.kind = ScheduledEvent::Kind::Rest; break;
        }
        f.action = tx.insert(action); tx.foragers.set(ant.id, f);
        if (r.connector_return && !s.connectors.at(ant.id).returning) {
            auto link=s.connectors.at(ant.id);
            link.returning=true;
            tx.connectors.set(ant.id,link);
        }
        WorldEvent fact; fact.source = r.event.id; fact.kind = FactKind::ForagingDecision;
        fact.actor = ant.id; fact.colony = ant.colony; fact.position = ant.position; fact.stage = ant.stage;
        fact.mode = r.decision.mode; fact.reason = r.decision.reason; fact.payload = f.decisions;
        fact.forgot_memory = r.decision.forget_memory;
        // Count the explicitly recorded local food cue, never an unrecorded global discovery.
        fact.resource = r.decision.resource;
        if (s.care_profile) {
            const auto act=action.kind==ScheduledEvent::Kind::Move?CareAct::Walk:action.kind==ScheduledEvent::Kind::CollectFood?
                CareAct::CollectFood:action.kind==ScheduledEvent::Kind::DeliverFood?CareAct::DeliverFood:CareAct::Inactive;
            observe(tx,ant.id,r.event.id,{ObservationPhase::Selected,act,{},f.action,s.m.now,false});
        }
        if (!fact.resource.value && r.local.food_count) fact.resource = r.local.food[0].resource;
        if (fact.resource.value && !s.discoveries.contains(fact.resource)) tx.discoveries.set(fact.resource, {s.m.now, ant.id});
        tx.fact(fact);
    }
}
void WorldRuntime::after_action(Transaction& tx, const ScheduledEvent& e, WorldEvent& fact, const AntState& before) {
    auto& s = *state_; const auto it = s.foragers.find(e.actor);
    if (it == s.foragers.end() || !it->second.enabled) return;
    auto f = it->second;
    if (f.action != e.id) throw std::logic_error("autonomous action ownership mismatch");
    const auto ant = s.ants.get(s.ants.index.at(e.actor)); const auto& p = s.surface->behavior;
    fact.mode = f.mode; f.action = {};
    const auto connector=s.connectors.find(ant.id);
    const auto transit=connector!=s.connectors.end() && connector->second.size>1 &&
        (connector->second.cursor+1<connector->second.size ||
         (connector->second.returning && before.position==connector->second.entrance()));
    if (fact.kind==FactKind::Moved && transit) {
        auto link=connector->second;
        const auto cursor=link.returning?link.cursor-1:link.cursor+1;
        if (ant.position!=link.points[cursor]) throw std::logic_error("movement differs from the local connector");
        link.cursor=cursor;
        if (!cursor && !ant.carried_food.total_ug()) link.returning=false;
        tx.connectors.set(ant.id,link);
        fact.payload=connector_move_fact;
    } else if (fact.kind==FactKind::Moved && navigation_cell(s,before.position)!=navigation_cell(s,ant.position)) {
        const auto from=*navigation_cell(s,before.position),to=*navigation_cell(s,ant.position);
        f.heading = direction(from, to); bump(f.trip_moves); bump(s.m.foraging.moves);
        if (f.mode == BehaviorMode::Return) bump(s.m.foraging.return_moves);
        else if (f.mode == BehaviorMode::FollowMemory) bump(s.m.foraging.memory_moves);
        else if (f.mode == BehaviorMode::FollowTrail) bump(s.m.foraging.trail_moves);
        else bump(s.m.foraging.explore_moves);
        if (from == f.path[0] && !before.carried_food.total_ug()) { bump(s.m.foraging.trips_started); f.trip_moves = 1; }
        bool found = false;
        for (std::uint32_t i = 0; i < f.path_size; ++i) if (f.path[i] == to) {
            for (auto j = i+1; j < f.path_size; ++j) f.path[j] = {};
            f.path_size = i+1; found = true; break;
        }
        if (!found) {
            if (f.path_size >= p.route_capacity) throw std::logic_error("bounded return trace overflow");
            f.path[f.path_size++] = to;
        }
        if (to==f.path[0] && !ant.carried_food.total_ug()) {
            if (connector!=s.connectors.end() && connector->second.size>1 && f.mode==BehaviorMode::Return) {
                auto link=connector->second;
                link.returning=true;
                tx.connectors.set(ant.id,link);
            }
            f.mode=BehaviorMode::Explore; f.trip_moves=0;
        }
        tx.visits.set(to, next_count(s.visits.contains(to) ? s.visits.at(to) : 0));
        const EdgeKey edge{std::min(from, to), std::max(from, to)};
        tx.edges.set(edge, next_count(s.edges.contains(edge) ? s.edges.at(edge) : 0));
        if (p.trails_enabled && before.carried_food.total_ug()) {
            const TrailKey key{ant.colony, to}; const auto old = s.trails.find(key);
            if (old == s.trails.end() && s.trails.size() >= limits_.trail_cells) throw std::length_error("sparse trail host budget exceeded");
            const auto amount = old == s.trails.end() ? 0 : trail_at(old->second, s.m.now, p);
            const auto next = std::min(p.trail_cap_units, amount+p.deposit_units);
            fact.deposited_units = next-amount; s.m.foraging.deposited_units += fact.deposited_units;
            if (!std::isfinite(s.m.foraging.deposited_units)) throw std::overflow_error("trail accounting overflow");
            tx.trails.set(key, {next, s.m.now});
        }
    } else if (fact.kind == FactKind::FoodCollected) {
        bump(s.m.foraging.collections); bump(f.collections);
        s.m.foraging.collected_outbound_moves = add(s.m.foraging.collected_outbound_moves, f.trip_moves);
        if (f.last_collected == e.resource) bump(s.m.foraging.revisits);
        f.last_collected = e.resource; f.mode = BehaviorMode::Return;
        if (p.memory_enabled) { f.memory = f.path; f.memory_size = f.path_size; f.learned_at = s.m.now; }
    } else if (fact.kind == FactKind::FoodDelivered) {
        bump(s.m.foraging.deliveries); f.mode = BehaviorMode::Explore; f.trip_moves = 0;
        if (connector!=s.connectors.end() && connector->second.returning) {
            auto link=connector->second;
            link.returning=false;
            tx.connectors.set(ant.id,link);
        }
    } else if (fact.kind == FactKind::ActionRejected) bump(s.m.foraging.failed_actions);
    ScheduledEvent wake; wake.kind = ScheduledEvent::Kind::Wake; wake.actor = ant.id; wake.issued_at = s.m.now;
    wake.key = {later(s.m.now, p.decision_delay), Phase::Perception, 0, 0, 0};
    f.wake = tx.insert(wake); tx.foragers.set(ant.id, f);
}
void WorldRuntime::stop_dead_forager(Transaction& tx, EntityId actor) {
    auto& s = *state_; const auto it = s.foragers.find(actor); if (it == s.foragers.end()) return;
    auto f = it->second;
    for (const auto scheduled : {f.wake, f.action}) if (scheduled.value) {
        const auto found = s.queue_index.find(scheduled); if (found != s.queue_index.end()) tx.remove(found->second);
    }
    f.enabled = false; f.wake = {}; f.action = {}; tx.foragers.set(actor, f);
}
void WorldRuntime::maintain_trails(Transaction& tx, const ScheduledEvent& e) {
    auto& s = *state_; const auto& p = s.surface->behavior; std::uint64_t removed = 0;
    for (auto i = s.trails.begin(); i != s.trails.end();) {
        const auto key = i->first; const auto value = trail_at(i->second, s.m.now, p); ++i;
        if (value == 0) { tx.trails.erase(key); ++removed; }
        else tx.trails.set(key, {value, s.m.now});
    }
    auto next = e; next.key.time = later(s.m.now, p.field_interval); next.issued_at = s.m.now;
    s.m.maintenance = tx.insert(next);
    WorldEvent fact; fact.source = e.id; fact.kind = FactKind::TrailMaintenance; fact.payload = removed; tx.fact(fact);
}
std::optional<ForagerState> WorldRuntime::query_forager(AntRef ref) const {
    if (ref.world != state_->world) return {};
    const auto it = state_->foragers.find(ref.id); return it == state_->foragers.end() ? std::optional<ForagerState>{} : it->second;
}
std::vector<TrailSample> WorldRuntime::trails() const {
    std::vector<TrailSample> result(0); const auto& s = *state_; if (!s.surface) return result;
    result.reserve(s.trails.size());
    for (const auto& [key, value] : s.trails) {
        const auto amount = trail_at(value, s.m.now, s.surface->behavior);
        if (amount > 0) result.push_back({key.colony, key.cell, amount});
    }
    return result;
}
std::vector<CellVisit> WorldRuntime::visits() const {
    std::vector<CellVisit> result(0); result.reserve(state_->visits.size());
    for (const auto& [cell, n] : state_->visits) result.push_back({cell, n});
    return result;
}
SurfaceSnapshot WorldRuntime::surface_snapshot() const {
    const auto& s = *state_; SurfaceSnapshot result; if (!s.surface) return result;
    result.configured = true; result.surface = s.surface->config; result.behavior = s.surface->behavior;
    result.counters = s.m.foraging;
    for (const auto v : s.surface->walkable) if (v) ++result.walkable_cells;
    result.visited_cells = s.visits.size(); result.distinct_edges = s.edges.size();
    for (const auto& [key, n] : s.edges) { (void)key; result.edge_traversals = add(result.edge_traversals, n); }
    result.discovered_sources = s.discoveries.size();
    for (const auto& [id, d] : s.discoveries) {
        (void)id;
        if (result.first_discovery.milliseconds < 0 || d.time < result.first_discovery ||
            (d.time == result.first_discovery && d.actor < result.first_discoverer)) {
            result.first_discovery = d.time; result.first_discoverer = d.actor;
        }
    }
    for (const auto& [key, value] : s.trails) {
        (void)key; const auto amount = trail_at(value, s.m.now, s.surface->behavior);
        if (amount > 0) { ++result.active_trail_cells; result.trail_units += amount; }
    }
    result.evaporated_units = std::max(0.0, result.counters.deposited_units-result.trail_units); return result;
}
} // namespace antworld
