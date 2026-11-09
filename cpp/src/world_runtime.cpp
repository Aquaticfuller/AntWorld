#include "state.hpp"
#include <tuple>

namespace antworld {
using namespace detail;
std::array<std::uint64_t, 4> FoodMass::components() const { return {carbs_ug, protein_ug, water_ug, other_ug}; }
std::uint64_t FoodMass::total_ug() const { return add(add(carbs_ug, protein_ug), add(water_ug, other_ug)); }
namespace {
void require_seed_time(SimTime now, bool executed) {
    if (now != SimTime{} || executed) throw std::invalid_argument("fixture seeding requires an unexecuted time-zero world");
}
// Exact a*b/d without nonportable 128-bit integers. a,b <= d guarantees a uint64 quotient.
std::pair<std::uint64_t, std::uint64_t> muldiv(std::uint64_t a, std::uint64_t b, std::uint64_t d) {
    std::uint64_t q = 0, r = 0;
    for (unsigned i = 64; i-- > 0;) {
        q *= 2;
        if (r >= d-r) { r -= d-r; ++q; } else r += r;
        if ((b >> i) & 1) { if (r >= d-a) { r -= d-a; ++q; } else r += a; }
    }
    return {q, r};
}
} // namespace
FoodMass detail::portion(FoodMass mass, std::uint64_t amount) {
    if (!amount) return {};
    const auto total = mass.total_ug(); const auto values = mass.components();
    std::array<std::uint64_t, 4> parts{}, remainders{};
    std::array<std::size_t, 4> order{0, 1, 2, 3}; std::uint64_t assigned = 0;
    for (std::size_t i = 0; i < 4; ++i) {
        const auto [q, r] = muldiv(values[i], amount, total);
        parts[i] = q; remainders[i] = r; assigned += q;
    }
    std::sort(order.begin(), order.end(), [&](auto a, auto b) {
        return remainders[a] != remainders[b] ? remainders[a] > remainders[b] : a < b;
    });
    for (std::uint64_t i = 0; i < amount-assigned; ++i) ++parts[order[static_cast<std::size_t>(i)]];
    return {parts[0], parts[1], parts[2], parts[3]};
}
namespace {
std::uint64_t rank(std::uint64_t seed, SimTime time, ResourceId resource, EntityId actor) {
    // Stateless arbitration stream v1; it never consumes the world's diagnostic RNG.
    Rng a(seed ^ static_cast<std::uint64_t>(time.milliseconds));
    Rng b(a.next() ^ resource.value); Rng c(b.next() ^ actor.value); return c.next();
}
} // namespace
WorldRuntime::WorldRuntime(WorldId world, std::uint64_t seed, WorldConfig config, RuntimeLimits limits)
    : state_(std::make_unique<State>(world, seed, config)), limits_(limits) {
    if (world == WorldId{}) throw std::invalid_argument("world_id must not be nil");
    validate_config(config);
}
WorldRuntime::~WorldRuntime() = default;
WorldRuntime::WorldRuntime(WorldRuntime&&) noexcept = default;
WorldRuntime& WorldRuntime::operator=(WorldRuntime&&) noexcept = default;
EntityId WorldRuntime::allocate_entity_id() {
    Transaction tx(*state_, limits_); const EntityId id{take(state_->m.next_entity)};
    bump(state_->m.revision); tx.commit(); return id;
}
ScheduledId WorldRuntime::schedule(const EventRequest& request) {
    if (!valid(request.phase) || !valid(request.action)) throw std::invalid_argument("invalid phase or diagnostic action");
    ScheduledEvent e; e.key = {request.time, request.phase, request.priority, request.tie, 0};
    e.action = request.action; e.payload = request.payload;
    Transaction tx(*state_, limits_); const auto id = tx.insert(e); tx.commit(); return id;
}
bool WorldRuntime::cancel(ScheduledId id) {
    auto& s = *state_; const auto found = s.queue_index.find(id);
    if (found == s.queue_index.end()) return false;
    const auto& event = s.queue.at(found->second);
    if (event.kind == ScheduledEvent::Kind::Wake || event.kind == ScheduledEvent::Kind::TrailMaintenance ||
        event.kind==ScheduledEvent::Kind::Reproduction || event.kind==ScheduledEvent::Kind::ResourceRelease ||
        event.kind == ScheduledEvent::Kind::Physiology || event.kind == ScheduledEvent::Kind::NutritionWake || event.kind == ScheduledEvent::Kind::ExcavationWake || event.kind==ScheduledEvent::Kind::AutonomyWake ||
        (s.excavators.contains(event.actor) && s.excavators.at(event.actor).action == id) ||
        (s.physiology.contains(event.actor) && s.physiology.at(event.actor).behavior_event == id) ||
        (s.foragers.contains(event.actor) && s.foragers.at(event.actor).action == id))
        throw std::invalid_argument("autonomous events are owned by their individual/field scheduler");
    Transaction tx(s, limits_); tx.remove(found->second); bump(s.m.revision); tx.commit(); return true;
}
ColonyRef WorldRuntime::seed_colony(PositionM nest) {
    auto& s = *state_; require_seed_time(s.m.now, s.m.watermark.has_value());
    if (!inside(nest, s.config) || (s.surface && !s.surface->locate(nest)) || !spatially_clear(nest,nest)) throw std::invalid_argument("invalid physical nest position");
    Transaction tx(s, limits_); tx.entity_budget(); const ColonyId id{take(s.m.next_entity)};
    s.colonies.append({id, Species::LasiusNigerEngineeringFixture, s.m.now, nest, {}});
    WorldEvent e; e.kind = FactKind::ColonySeeded; e.colony = id; e.position = nest; tx.fact(e);
    tx.commit(); return {s.world, id};
}
AntRef WorldRuntime::seed_ant(ColonyRef colony, const AntSeed& seed) {
    auto& s = *state_; require_seed_time(s.m.now, s.m.watermark.has_value());
    if (colony.world != s.world || !s.colonies.index.contains(colony.id) ||
        !valid(seed.stage) || seed.stage == LifeStage::Dead || seed.caste > Caste::Male ||
        !inside(seed.position, s.config) || (s.surface && !(s.social && s.geometry) && !s.surface->locate(seed.position)) ||
        !spatially_clear(seed.position,seed.position,s.geometry ? s.geometry->config.body_half_q : 0))
        throw std::invalid_argument("invalid ant seed or colony reference");
    Transaction tx(s, limits_); tx.entity_budget(); const EntityId id{take(s.m.next_entity)};
    s.ants.append({id, colony.id, s.m.now, seed.stage, seed.caste, seed.position, 0, seed.carrying_capacity_ug, {}});
    if (s.geometry) tx.spatial_index.set({spatial_key(seed.position),id.value},1);
    index_contact(tx,id,seed.position);
    bump(s.m.living);
    WorldEvent e; e.kind = FactKind::AntSeeded; e.actor = id; e.colony = colony.id;
    e.position = seed.position; e.stage = seed.stage; tx.fact(e); tx.commit(); return {s.world, id};
}
FoodRef WorldRuntime::seed_food(PositionM position, FoodMass mass) {
    auto& s = *state_; require_seed_time(s.m.now, s.m.watermark.has_value());
    if (!inside(position, s.config) || mass.total_ug() == 0 || !spatially_clear(position,position)) throw std::invalid_argument("invalid food seed");
    std::optional<Cell> cell;
    if (s.surface) {
        cell = s.surface->locate(position);
        if (!cell || s.food_cells.contains(*cell)) throw std::invalid_argument("surface food requires a unique walkable cell");
    }
    Transaction tx(s, limits_); tx.entity_budget(); const ResourceId id{take(s.m.next_entity)};
    s.foods.append({id, position, mass, mass});
    if (s.geometry) tx.spatial_index.set({spatial_key(position),id.value},2);
    if (cell) tx.food_cells.set(*cell, id);
    s.m.ledger.introduced = sum(s.m.ledger.introduced, mass); (void)s.m.ledger.introduced.total_ug();
    s.m.ledger.available = sum(s.m.ledger.available, mass);
    WorldEvent e; e.kind = FactKind::FoodSeeded; e.resource = id; e.position = position; e.transferred = mass;
    tx.fact(e); validate_nutrition_capacity(); tx.commit(); return {s.world, id};
}
ScheduledId WorldRuntime::submit(const ActionProposal& p) {
    auto& s = *state_; const auto ant = query_ant(p.actor);
    if (!ant || p.kind > ActionKind::Rest || s.foragers.contains(p.actor.id) || (s.autonomy.contains(p.actor.id) && s.autonomy.at(p.actor.id).enabled) ||
        (s.physiology.contains(p.actor.id) && s.physiology.at(p.actor.id).behavior != IndividualBehavior::Paused) ||
        (p.kind == ActionKind::CollectFood && (!query_food(p.food) || p.requested_ug == 0)) ||
        (p.kind == ActionKind::Move && !finite(p.destination)))
        throw std::invalid_argument("invalid action proposal or world reference");
    ScheduledEvent e; e.key = {p.execute_at, Phase::Resolution, 0, 0, 0};
    switch (p.kind) {
    case ActionKind::Move: e.kind = ScheduledEvent::Kind::Move; break;
    case ActionKind::CollectFood: e.kind = ScheduledEvent::Kind::CollectFood; break;
    case ActionKind::DeliverFood: e.kind = ScheduledEvent::Kind::DeliverFood; break;
    case ActionKind::Rest: e.kind = ScheduledEvent::Kind::Rest; break;
    }
    e.actor = p.actor.id; e.resource = p.kind == ActionKind::CollectFood ? p.food.id : ResourceId{};
    e.destination = p.kind == ActionKind::Move ? p.destination : PositionM{};
    e.requested_ug = p.kind == ActionKind::CollectFood ? p.requested_ug : 0;
    e.issued_at = s.m.now; e.observed_position_revision = ant->position_revision;
    Transaction tx(s, limits_); const auto id = tx.insert(e); tx.commit(); return id;
}
ScheduledId WorldRuntime::schedule_lifecycle(AntRef actor, SimTime at, LifeStage stage) {
    if (!query_ant(actor) || !valid(stage)) throw std::invalid_argument("invalid lifecycle fixture");
    if (state_->physiology.contains(actor.id) && stage != LifeStage::Dead)
        throw std::invalid_argument("physiological development cannot be forced by a fixture event");
    ScheduledEvent e; e.key = {at, Phase::Environment, 0, 0, 0};
    e.kind = ScheduledEvent::Kind::Lifecycle; e.actor = actor.id; e.stage = stage; e.issued_at = state_->m.now;
    Transaction tx(*state_, limits_); const auto id = tx.insert(e); tx.commit(); return id;
}
void WorldRuntime::execute(Transaction& tx, const ScheduledEvent& e) {
    auto& s = *state_; WorldEvent fact; fact.source = e.id; fact.actor = e.actor;
    if (e.kind == ScheduledEvent::Kind::Physiology) { execute_physiology(tx, e); return; }
    if (e.kind == ScheduledEvent::Kind::Reproduction) { execute_reproduction(tx,e); return; }
    if (e.kind == ScheduledEvent::Kind::ResourceRelease) { execute_resource_release(tx,e); return; }
    if (e.kind == ScheduledEvent::Kind::TrailMaintenance) { maintain_trails(tx, e); return; }
    if (e.kind == ScheduledEvent::Kind::Diagnostic) {
        fact.action = e.action; fact.payload = e.payload;
        fact.random_value = e.action == DiagnosticAction::DrawRandom ? s.m.rng.next() : 0;
        tx.fact(fact);
        if (e.action == DiagnosticAction::RepeatSameTime) tx.insert(e);
        return;
    }
    const auto i = s.ants.index.at(e.actor); auto ant = s.ants.get(i);
    fact.colony = ant.colony; fact.stage = e.stage; fact.kind = FactKind::ActionRejected;
    if (!ant.alive()) fact.outcome = e.stage == LifeStage::Dead ? Outcome::AlreadyDead : Outcome::DeadActor;
    else if (e.stage != LifeStage::Dead && static_cast<unsigned>(e.stage) != static_cast<unsigned>(ant.stage)+1)
        fact.outcome = Outcome::InvalidTransition;
    else {
        synchronize_physiology(tx, e.actor);
        tx.touch_ant(i); ant.stage = e.stage; s.ants.set(i, ant);
        fact.kind = e.stage == LifeStage::Dead ? FactKind::AntDied : FactKind::StageChanged;
        if (e.stage == LifeStage::Dead) { --s.m.living; index_contact(tx,e.actor,{}); stop_dead_forager(tx, e.actor); stop_excavator(tx,e.actor); stop_physiology(tx, e.actor, DeathCause::Fixture); stop_autonomy(tx,e.actor); }
    }
    tx.fact(fact);
}
void WorldRuntime::resolve_actions(Transaction& tx, const std::vector<ScheduledEvent>& actions) {
    auto& s = *state_; std::vector<ScheduledEvent> ordered = actions;
    // One actor gets one proposal per boundary. Earliest submission wins for that actor.
    std::map<EntityId, std::uint64_t> first;
    for (const auto& e : ordered) {
        auto [it, inserted] = first.emplace(e.actor, e.key.sequence);
        if (!inserted) it->second = std::min(it->second, e.key.sequence);
    }
    std::sort(ordered.begin(), ordered.end(), [&](const auto& a, const auto& b) {
        return std::tuple{a.resource.value, rank(s.seed, s.m.now, a.resource, a.actor), a.actor.value, a.key.sequence} <
            std::tuple{b.resource.value, rank(s.seed, s.m.now, b.resource, b.actor), b.actor.value, b.key.sequence};
    });
    for (const auto& e : ordered) {
        const auto i = s.ants.index.at(e.actor); auto ant = s.ants.get(i);
        const auto before = ant;
        WorldEvent f; f.source = e.id; f.actor = e.actor; f.colony = ant.colony; f.resource = e.resource;
        f.kind = FactKind::ActionRejected; f.position = ant.position; f.stage = ant.stage;
        if (e.key.sequence != first.at(e.actor)) f.outcome = Outcome::DuplicateAction;
        else if (!ant.alive()) f.outcome = Outcome::DeadActor;
        else if (ant.stage != LifeStage::Adult || ant.caste != Caste::Worker) f.outcome = Outcome::InvalidStage;
        else if (e.observed_position_revision != ant.position_revision) f.outcome = Outcome::StalePosition;
        else if (e.kind == ScheduledEvent::Kind::SoilAction) {
            resolve_soil_action(tx,e,f);
        } else if ((e.kind >= ScheduledEvent::Kind::IngestCargo && e.kind <= ScheduledEvent::Kind::Trophallaxis) || e.kind==ScheduledEvent::Kind::ReturnProtein) {
            resolve_nutrition_action(tx, e, f);
        } else if (e.kind == ScheduledEvent::Kind::Move) {
            const bool planar=s.surface && (!(s.social && s.geometry) || (s.foragers.contains(e.actor) && s.foragers.at(e.actor).enabled));
            const auto seconds = static_cast<double>(e.key.time.milliseconds - e.issued_at.milliseconds) / 1000.0;
            const auto length = distance(ant.position, e.destination);
            if (!inside(e.destination, s.config)) f.outcome = Outcome::OutOfBounds;
            else if (!spatially_clear(ant.position,e.destination,body_half(e.actor))) f.outcome = Outcome::Blocked;
            else if (planar && (!s.surface->locate(ant.position) || !s.surface->locate(e.destination))) f.outcome = Outcome::Blocked;
            else if (planar && !adjacent(*s.surface->locate(ant.position), *s.surface->locate(e.destination))) f.outcome = Outcome::NonLocalMove;
            else if (!std::isfinite(length) || (length > 0 && (seconds <= 0 || length / seconds > s.config.max_speed_m_per_s)))
                f.outcome = Outcome::TooFast;
            else {
                index_position(tx,ant.id,ant.position,e.destination);
                tx.touch_ant(i); ant.position = e.destination; bump(ant.position_revision); s.ants.set(i, ant);
                f.kind = FactKind::Moved; f.position = ant.position;
            }
        } else if (e.kind == ScheduledEvent::Kind::CollectFood) {
            const auto j = s.foods.index.at(e.resource); auto& food = s.foods.rows[j];
            const auto available = food.remaining.total_ug();
            const auto room = ant.carrying_capacity_ug - ant.carried_food.total_ug() - carried_soil_ug(ant.id);
            if (distance(ant.position, food.position) > s.config.contact_distance_m ||
                (s.surface && s.surface->locate(ant.position) != s.surface->locate(food.position)) || !spatially_clear(ant.position,food.position)) f.outcome = Outcome::OutOfReach;
            else if (available == 0) f.outcome = Outcome::Depleted;
            else if (room == 0) f.outcome = Outcome::Capacity;
            else if (s.geometry && !spatially_clear(ant.position,ant.position,s.geometry->config.loaded_half_q)) f.outcome = Outcome::Blocked;
            else {
                const auto amount = std::min({e.requested_ug, available, room}); f.transferred = portion(food.remaining, amount);
                tx.touch_ant(i); tx.touch_food(j);
                ant.carried_food = sum(ant.carried_food, f.transferred); s.ants.set(i, ant);
                food.remaining = subtract(food.remaining, f.transferred);
                s.m.ledger.available = subtract(s.m.ledger.available, f.transferred);
                s.m.ledger.carried = sum(s.m.ledger.carried, f.transferred);
                f.kind = FactKind::FoodCollected; f.outcome = amount == e.requested_ug ? Outcome::Success : Outcome::Partial;
            }
        } else if (e.kind == ScheduledEvent::Kind::DeliverFood) {
            const auto j = s.colonies.index.at(ant.colony); auto& colony = s.colonies.rows[j];
            if (distance(ant.position, colony.nest_position) > s.config.contact_distance_m ||
                (s.surface && s.surface->locate(ant.position) != s.surface->locate(colony.nest_position)) || !spatially_clear(ant.position,colony.nest_position)) f.outcome = Outcome::NotAtNest;
            else if (ant.carried_food.total_ug() == 0) f.outcome = Outcome::EmptyInventory;
            else {
                tx.touch_ant(i); tx.touch_colony(j); f.transferred = ant.carried_food;
                colony.nest_food = sum(colony.nest_food, f.transferred); ant.carried_food = {}; s.ants.set(i, ant);
                s.m.ledger.carried = subtract(s.m.ledger.carried, f.transferred);
                s.m.ledger.stored = sum(s.m.ledger.stored, f.transferred); f.kind = FactKind::FoodDelivered;
            }
        } else if (e.kind == ScheduledEvent::Kind::Rest) {
            f.kind = FactKind::Rested;
        } else {
            throw std::logic_error("invalid action event kind");
        }
        after_action(tx, e, f, before);
        continue_nutrition_behavior(tx, e);
        after_excavation_action(tx,e,f,before);
        if (s.long_term && ant.position==s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position &&
            !ant.carried_food.total_ug() && !s.carriers.contains(ant.id) &&
            (f.kind==FactKind::FoodDelivered || f.kind==FactKind::SoilDropped ||
             (f.kind==FactKind::Moved && s.foragers.contains(ant.id) && s.foragers.at(ant.id).mode==BehaviorMode::Return)))
            notify_return(tx,ant.id);
        tx.fact(f);
    }
}
void WorldRuntime::advance_to(SimTime target) {
    profiling::Scope profile(profiling::Category::Advance);
    auto& s = *state_;
    if (target < s.m.now) throw std::invalid_argument("simulation time cannot move backwards");
    Transaction tx(s, limits_);
    while (!s.queue.empty() && s.queue.begin()->first.time <= target) {
        const auto key = s.queue.begin()->first;
        if (key.phase == Phase::Perception) {
            std::vector<ScheduledEvent> wakes(0);
            while (!s.queue.empty() && s.queue.begin()->first.time == key.time && s.queue.begin()->first.phase == Phase::Perception) {
                const auto e = tx.remove(s.queue.begin()->first); tx.executing(e);
                if (e.kind == ScheduledEvent::Kind::Wake || e.kind == ScheduledEvent::Kind::NutritionWake || e.kind == ScheduledEvent::Kind::ExcavationWake) wakes.push_back(e); else execute(tx, e);
            }
            std::vector<ScheduledEvent> foragers(0), nurses(0), excavators(0);
            for (const auto& e : wakes) (e.kind == ScheduledEvent::Kind::Wake ? foragers : e.kind == ScheduledEvent::Kind::NutritionWake ? nurses : excavators).push_back(e);
            if (!foragers.empty()) resolve_wakes(tx, foragers);
            if (!nurses.empty()) resolve_nutrition_wakes(tx, nurses);
            if (!excavators.empty()) resolve_excavation_wakes(tx,excavators);
        } else if (key.phase == Phase::Resolution) {
            std::vector<ScheduledEvent> actions(0);
            while (!s.queue.empty() && s.queue.begin()->first.time == key.time && s.queue.begin()->first.phase == Phase::Resolution) {
                const auto e = tx.remove(s.queue.begin()->first); tx.executing(e);
                if (e.kind == ScheduledEvent::Kind::Diagnostic) execute(tx, e); else actions.push_back(e);
            }
            if (!actions.empty()) {
                resolve_actions(tx, actions);
                s.m.watermark = EventKey{key.time, Phase::Commit, 0, 0, 0};
            }
        } else if (key.phase==Phase::Reschedule) {
            std::vector<ScheduledEvent> wakes(0);
            while (!s.queue.empty() && s.queue.begin()->first.time==key.time && s.queue.begin()->first.phase==Phase::Reschedule) {
                const auto e=tx.remove(s.queue.begin()->first); tx.executing(e);
                if (e.kind==ScheduledEvent::Kind::AutonomyWake) wakes.push_back(e); else execute(tx,e);
            }
            if (!wakes.empty()) resolve_autonomy_wakes(tx,wakes);
        } else { const auto e = tx.remove(key); tx.executing(e); execute(tx, e); }
    }
    tx.time(target); tx.commit();
}
std::optional<AntState> WorldRuntime::query_ant(AntRef ref) const {
    if (ref.world != state_->world) return {};
    const auto it = state_->ants.index.find(ref.id);
    return it == state_->ants.index.end() ? std::optional<AntState>{} : state_->ants.get(it->second);
}
std::optional<Colony> WorldRuntime::query_colony(ColonyRef ref) const {
    if (ref.world != state_->world) return {};
    const auto it = state_->colonies.index.find(ref.id);
    return it == state_->colonies.index.end() ? std::optional<Colony>{} : state_->colonies.rows[it->second];
}
std::optional<FoodSource> WorldRuntime::query_food(FoodRef ref) const {
    if (ref.world != state_->world) return {};
    const auto it = state_->foods.index.find(ref.id);
    return it == state_->foods.index.end() ? std::optional<FoodSource>{} : state_->foods.rows[it->second];
}
WorldConfig WorldRuntime::config() const { return state_->config; }
WorldSnapshot WorldRuntime::summary() const {
    const auto& s = *state_; const auto& m = s.m;
    return {s.world, m.now, s.seed, m.revision, s.queue.size(), s.journal.size(), m.next_entity,
        m.next_scheduled, m.next_event, m.next_sequence, m.rng.state(), 0, 0,
        s.ants.size(), s.colonies.rows.size(), s.foods.rows.size(), m.living, m.ledger, m.watermark, m.executed};
}
WorldSnapshot WorldRuntime::snapshot() const {
    auto result = summary(); const auto bytes = checkpoint();
    result.state_hash = hash_bytes(std::span{bytes}.first(bytes.size()-8)); result.trace_hash = trace_hash(state_->journal);
    return result;
}
std::vector<WorldEvent> WorldRuntime::committed_events() const { return state_->journal; }
std::vector<WorldEvent> WorldRuntime::events_after(EventId cursor, std::size_t limit) const {
    const auto& journal = state_->journal;
    if (cursor.value >= journal.size()) return std::vector<WorldEvent>(0);
    const auto first = static_cast<std::size_t>(cursor.value);
    const auto count = std::min(limit, journal.size()-first);
    return {journal.begin()+static_cast<std::ptrdiff_t>(first), journal.begin()+static_cast<std::ptrdiff_t>(first+count)};
}
std::vector<ScheduledEvent> WorldRuntime::pending_events() const {
    std::vector<ScheduledEvent> result(0); result.reserve(state_->queue.size());
    for (const auto& [key, e] : state_->queue) { (void)key; result.push_back(e); }
    return result;
}
} // namespace antworld
