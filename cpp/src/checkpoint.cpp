#include "state.hpp"
#include "checkpoint_codec.hpp"
#include "checkpoint_s2.hpp"
#include "checkpoint_s3.hpp"
#include "checkpoint_s4.hpp"
#include "checkpoint_s5.hpp"
#include <bit>
#include <set>

namespace antworld {
namespace {
using namespace detail;
void write_fact(Writer& w, const WorldEvent& e) {
    w.put(e.id.value); w.put(e.world.high); w.put(e.world.low); w.time(e.time); w.put(e.source.value);
    w.put(static_cast<std::uint8_t>(e.action), 1); w.put(e.revision); w.put(e.payload); w.put(e.random_value);
    w.put(static_cast<std::uint8_t>(e.kind), 1); w.put(e.actor.value); w.put(e.colony.value); w.put(e.resource.value);
    w.position(e.position); w.mass(e.transferred); w.put(static_cast<std::uint8_t>(e.stage), 1);
    w.put(static_cast<std::uint8_t>(e.outcome), 1);
    w.put(static_cast<std::uint8_t>(e.mode), 1); w.put(static_cast<std::uint8_t>(e.reason), 1);
    w.real(e.deposited_units); w.put(e.forgot_memory, 1);
}
WorldEvent read_fact(Reader& r) {
    WorldEvent e;
    e.id = {r.get()}; e.world = {r.get(), r.get()}; e.time = r.time(); e.source = {r.get()};
    e.action = static_cast<DiagnosticAction>(r.get(1)); e.revision = r.get(); e.payload = r.get(); e.random_value = r.get();
    e.kind = static_cast<FactKind>(r.get(1)); e.actor = {r.get()}; e.colony = {r.get()}; e.resource = {r.get()};
    e.position = r.position(); e.transferred = r.mass(); e.stage = static_cast<LifeStage>(r.get(1));
    e.outcome = static_cast<Outcome>(r.get(1)); e.mode = static_cast<BehaviorMode>(r.get(1));
    e.reason = static_cast<DecisionReason>(r.get(1)); e.deposited_units = r.real(); e.forgot_memory = r.flag(); return e;
}
} // namespace
std::vector<std::uint8_t> encode_event(const WorldEvent& event) {
    Writer writer; write_fact(writer, event); return writer.bytes;
}
WorldEvent decode_event(std::span<const std::uint8_t> bytes) {
    Reader reader{bytes}; auto event = read_fact(reader);
    ensure(reader.cursor == bytes.size(), "trailing fact payload bytes"); return event;
}
namespace detail {
std::uint64_t hash_bytes(std::span<const std::uint8_t> bytes) {
    std::uint64_t result = UINT64_C(14695981039346656037);
    for (auto b : bytes) result = (result ^ b) * UINT64_C(1099511628211);
    return result;
}
std::uint64_t trace_hash(const std::vector<WorldEvent>& events) {
    Writer w; for (const auto& e : events) write_fact(w, e); return hash_bytes(w.bytes);
}
} // namespace detail

std::vector<std::uint8_t> WorldRuntime::encode(const State& s, std::size_t byte_limit) {
    Writer w(byte_limit); const auto& m = s.m;
    w.put(UINT64_C(0x3654504b435741)); // AWCKPT6, then zero.
    w.put(schema_version, 4); w.put(physics_version, 4); w.put(1, 4); // SplitMix64 v1.
    w.put(s.world.high); w.put(s.world.low); w.put(s.seed); w.time(m.now); w.put(m.revision);
    w.put(m.next_entity); w.put(m.next_scheduled); w.put(m.next_event); w.put(m.next_sequence); w.put(m.rng.state());
    w.put(s.queue.size());
    for (const auto& [key, e] : s.queue) {
        w.put(e.id.value); w.key(key); w.put(static_cast<std::uint8_t>(e.action), 1); w.put(e.payload);
        w.put(static_cast<std::uint8_t>(e.kind), 1); w.put(e.actor.value); w.put(e.resource.value);
        w.position(e.destination); w.put(e.requested_ug); w.time(e.issued_at); w.put(e.observed_position_revision);
        w.put(static_cast<std::uint8_t>(e.stage), 1);
    }
    w.put(s.journal.size()); for (const auto& e : s.journal) write_fact(w, e);
    w.position(s.config.min_m); w.position(s.config.max_m); w.real(s.config.max_speed_m_per_s); w.real(s.config.contact_distance_m);
    w.put(m.watermark.has_value(), 1); if (m.watermark) w.key(*m.watermark);
    w.put(m.executed); w.put(m.living); w.mass(m.ledger.introduced); w.mass(m.ledger.available); w.mass(m.ledger.carried); w.mass(m.ledger.stored);
    w.put(s.colonies.rows.size());
    for (const auto& c : s.colonies.rows) {
        w.put(c.id.value); w.put(static_cast<std::uint8_t>(c.species), 1); w.time(c.founded_at); w.position(c.nest_position); w.mass(c.nest_food);
    }
    w.put(s.ants.size());
    for (std::size_t i = 0; i < s.ants.size(); ++i) {
        const auto a = s.ants.get(i); w.put(a.id.value); w.put(a.colony.value); w.time(a.born_at);
        w.put(static_cast<std::uint8_t>(a.stage), 1); w.put(static_cast<std::uint8_t>(a.caste), 1);
        w.position(a.position); w.put(a.position_revision); w.put(a.carrying_capacity_ug); w.mass(a.carried_food);
    }
    w.put(s.foods.rows.size());
    for (const auto& f : s.foods.rows) { w.put(f.id.value); w.position(f.position); w.mass(f.initial); w.mass(f.remaining); }
    write_surface(w, s);
    write_physiology(w, s);
    write_geometry(w,s);
    write_commands(w,s);
    w.put(hash_bytes(w.bytes)); return w.bytes;
}
std::unique_ptr<WorldRuntime::State> WorldRuntime::decode(std::span<const std::uint8_t> bytes, const RuntimeLimits& limits) {
    ensure(bytes.size() >= 124 && bytes.size() <= limits.checkpoint_bytes, "invalid checkpoint size or host budget");
    Reader checksum{bytes.last(8)};
    ensure(hash_bytes(bytes.first(bytes.size()-8)) == checksum.get(), "checkpoint checksum mismatch");
    Reader r{bytes.first(bytes.size()-8)};
    ensure(r.get() == UINT64_C(0x3654504b435741), "unsupported checkpoint magic; previous-stage migration is not implemented");
    ensure(r.get(4) == schema_version && r.get(4) == physics_version && r.get(4) == 1, "unsupported schema, physics or RNG version");
    const WorldId world{r.get(), r.get()}; ensure(world != WorldId{}, "nil checkpoint world");
    auto s = std::make_unique<State>(world, r.get()); auto& m = s->m;
    m.now = r.time(); m.revision = r.get(); m.next_entity = r.get(); m.next_scheduled = r.get();
    m.next_event = r.get(); m.next_sequence = r.get(); m.rng = Rng(r.get());
    ensure(m.next_entity && m.next_scheduled && m.next_event && m.next_sequence, "zero ID allocator");
    std::set<std::uint64_t> scheduled_ids, sequences, entity_ids;
    const auto count = r.count(limits.pending_events, 115);
    for (std::size_t i = 0; i < count; ++i) {
        ScheduledEvent e; e.id = {r.get()}; e.key = r.key(); e.action = static_cast<DiagnosticAction>(r.get(1)); e.payload = r.get();
        e.kind = static_cast<ScheduledEvent::Kind>(r.get(1)); e.actor = {r.get()}; e.resource = {r.get()};
        e.destination = r.position(); e.requested_ug = r.get(); e.issued_at = r.time(); e.observed_position_revision = r.get();
        e.stage = static_cast<LifeStage>(r.get(1));
        ensure(e.id.value && e.id.value < m.next_scheduled && e.key.sequence && e.key.sequence < m.next_sequence &&
            e.key.time >= m.now && valid(e.key.phase) && valid(e.action) && valid(e.stage) &&
            e.kind <= ScheduledEvent::Kind::ExcavationWake && finite(e.destination) && e.issued_at <= m.now &&
            scheduled_ids.insert(e.id.value).second && sequences.insert(e.key.sequence).second &&
            (s->queue.empty() || s->queue.rbegin()->first < e.key), "invalid future event");
        s->queue.emplace(e.key, e); s->queue_index.emplace(e.id, e.key);
    }
    const auto facts = r.count(limits.committed_events, 159);
    std::uint64_t previous_revision = 0; SimTime previous_time{};
    for (std::size_t i = 0; i < facts; ++i) {
        const auto e = read_fact(r);
        const auto seeded = e.kind == FactKind::ColonySeeded || e.kind == FactKind::AntSeeded || e.kind == FactKind::FoodSeeded ||
            e.kind == FactKind::SurfaceConfigured || e.kind == FactKind::ForagingStarted ||
            e.kind == FactKind::PhysiologyEnabled || e.kind == FactKind::BehaviorChanged || e.kind==FactKind::GeometryConfigured;
        ensure(e.id.value == i+1 && e.world == world && e.time >= previous_time && e.time <= m.now &&
            valid(e.action) && e.kind <= FactKind::FoodPlaced && valid(e.stage) && e.outcome <= Outcome::InsufficientEnergy &&
            e.mode <= BehaviorMode::Rest && e.reason <= DecisionReason::NoLegalStep && std::isfinite(e.deposited_units) && e.deposited_units >= 0 &&
            e.revision > previous_revision && e.revision <= m.revision && finite(e.position) &&
            (e.action == DiagnosticAction::DrawRandom || e.random_value == 0) &&
            (seeded ? e.source.value == 0 && (e.time == SimTime{} || e.kind == FactKind::ForagingStarted || e.kind == FactKind::BehaviorChanged) : e.source.value && e.source.value < m.next_scheduled &&
                scheduled_ids.insert(e.source.value).second), "invalid committed event");
        previous_revision = e.revision; previous_time = e.time; s->journal.push_back(e);
    }
    s->config = {r.position(), r.position(), r.real(), r.real()}; validate_config(s->config);
    const auto has_watermark = r.get(1); ensure(has_watermark <= 1, "invalid watermark flag");
    if (has_watermark) m.watermark = r.key();
    m.executed = r.get(); m.living = r.get(); m.ledger = {r.mass(), r.mass(), r.mass(), r.mass()};
    ensure(m.executed <= limits.events_per_timestamp && (m.watermark.has_value() == (m.executed != 0)), "invalid execution count");
    if (m.watermark) ensure(m.watermark->time == m.now && valid(m.watermark->phase) &&
        m.watermark->sequence < m.next_sequence && !s->journal.empty() && previous_time == m.now, "invalid execution watermark");
    auto entity = [&](std::uint64_t id) { ensure(id && id < m.next_entity && entity_ids.insert(id).second, "invalid or duplicate entity ID"); };
    const auto colonies = r.count(limits.entities, 73); FoodMass stored;
    for (std::size_t i = 0; i < colonies; ++i) {
        Colony c{{r.get()}, static_cast<Species>(r.get(1)), r.time(), r.position(), r.mass()}; entity(c.id.value);
        ensure(c.species == Species::LasiusNigerEngineeringFixture && c.founded_at == SimTime{} && inside(c.nest_position, s->config), "invalid colony");
        s->colonies.append(c); stored = sum(stored, c.nest_food);
    }
    const auto ants = r.count(limits.entities - colonies, 98); FoodMass carried; std::uint64_t living = 0;
    for (std::size_t i = 0; i < ants; ++i) {
        AntState a; a.id = {r.get()}; a.colony = {r.get()}; a.born_at = r.time();
        a.stage = static_cast<LifeStage>(r.get(1)); a.caste = static_cast<Caste>(r.get(1));
        a.position = r.position(); a.position_revision = r.get(); a.carrying_capacity_ug = r.get(); a.carried_food = r.mass(); entity(a.id.value);
        ensure(s->colonies.index.contains(a.colony) && a.born_at == SimTime{} && valid(a.stage) && a.caste <= Caste::Male &&
            inside(a.position, s->config) && a.carried_food.total_ug() <= a.carrying_capacity_ug, "invalid ant");
        s->ants.append(a); carried = sum(carried, a.carried_food); if (a.alive()) ++living;
    }
    const auto foods = r.count(limits.entities-colonies-ants, 96); FoodMass introduced, available;
    for (std::size_t i = 0; i < foods; ++i) {
        FoodSource f{{r.get()}, r.position(), r.mass(), r.mass()}; entity(f.id.value);
        ensure(inside(f.position, s->config) && f.initial.total_ug() > 0, "invalid food source");
        (void)subtract(f.initial, f.remaining); s->foods.append(f);
        introduced = sum(introduced, f.initial); available = sum(available, f.remaining);
    }
    read_surface(r, *s, limits);
    read_physiology(r, *s, limits);
    read_geometry(r,*s,limits,entity_ids);
    read_commands(r,*s,limits);
    ensure(m.living == living && m.ledger == FoodLedger{introduced, available, carried, stored}, "food ledger or living count mismatch");
    (void)introduced.total_ug();
    for (const auto& [key, e] : s->queue) {
        ensure(!m.watermark || key > *m.watermark, "future queue precedes execution watermark");
        if (e.kind == ScheduledEvent::Kind::Diagnostic) {
            ensure(!e.actor.value && !e.resource.value && !e.requested_ug && !e.observed_position_revision &&
                e.destination == PositionM{} && e.stage == LifeStage::Egg && e.issued_at == SimTime{}, "invalid diagnostic fields");
        } else if (e.kind == ScheduledEvent::Kind::TrailMaintenance) {
            ensure(s->surface && s->surface->behavior.trails_enabled && e.id == m.maintenance && key.phase == Phase::Environment &&
                key.priority == 1 && !key.tie && !e.actor.value && !e.resource.value && !e.requested_ug && !e.observed_position_revision &&
                e.destination == PositionM{} && e.action == DiagnosticAction::Record && !e.payload && e.stage == LifeStage::Egg, "invalid field event");
        } else if (e.kind >= ScheduledEvent::Kind::SoilAction) {
            ensure(s->geometry && s->ants.index.contains(e.actor) && e.action==DiagnosticAction::Record && !e.payload && !e.resource.value &&
                !e.requested_ug && !key.priority && !key.tie && e.destination==PositionM{} && e.stage==LifeStage::Egg,"invalid geometry event fields");
            if (e.kind==ScheduledEvent::Kind::SoilAction) {
                ensure(key.phase==Phase::Resolution && s->soil_requests.contains(e.id) && s->soil_requests.at(e.id).actor==e.actor &&
                    !s->soil_requests.at(e.id).actual_q3 && e.observed_position_revision<=s->ants.get(s->ants.index.at(e.actor)).position_revision,"invalid pending soil request");
            } else ensure(key.phase==Phase::Perception && s->excavators.contains(e.actor) && s->excavators.at(e.actor).wake==e.id &&
                !e.observed_position_revision,"invalid excavation wake");
        } else if (e.kind >= ScheduledEvent::Kind::Physiology) {
            ensure(s->physiology.contains(e.actor) && e.action == DiagnosticAction::Record && !e.resource.value &&
                e.key.priority == 0 && e.key.tie == 0 && e.destination == PositionM{} && e.stage == LifeStage::Egg,
                "invalid physiological event actor/fields");
            const auto& p = s->physiology.at(e.actor);
            if (e.kind == ScheduledEvent::Kind::Physiology || e.kind == ScheduledEvent::Kind::NutritionWake) {
                const bool physiological = e.kind == ScheduledEvent::Kind::Physiology;
                ensure(e.id == (physiological ? p.physiology_event : p.behavior_event) &&
                    e.key.phase == (physiological ? Phase::Environment : Phase::Perception) &&
                    !e.payload && !e.requested_ug && !e.observed_position_revision, "invalid physiology wake ownership");
            } else {
                ensure(e.key.phase == Phase::Resolution && e.requested_ug &&
                    e.observed_position_revision <= s->ants.get(s->ants.index.at(e.actor)).position_revision,
                    "invalid nutrition action phase");
                ensure(e.kind == ScheduledEvent::Kind::Trophallaxis ?
                    (e.payload != e.actor.value && s->physiology.contains(EntityId{e.payload})) : e.payload == 0,
                    "invalid nutrition recipient");
            }
        } else {
            ensure(s->ants.index.contains(e.actor) && e.action == DiagnosticAction::Record && !e.payload &&
                e.key.priority == 0 && e.key.tie == 0, "invalid scheduled actor");
            const auto a = s->ants.get(s->ants.index.at(e.actor));
            ensure(e.observed_position_revision <= a.position_revision, "invalid observed position version");
            if (e.kind == ScheduledEvent::Kind::Lifecycle)
                ensure(key.phase == Phase::Environment && !e.resource.value && !e.requested_ug && e.destination == PositionM{}, "invalid lifecycle event");
            else if (e.kind == ScheduledEvent::Kind::Wake) {
                ensure(s->surface && s->foragers.contains(e.actor) && s->foragers.at(e.actor).wake == e.id &&
                    key.phase == Phase::Perception && !e.resource.value && !e.requested_ug && e.destination == PositionM{} &&
                    !e.observed_position_revision && e.stage == LifeStage::Egg, "invalid autonomous wake");
            } else {
                ensure(key.phase == Phase::Resolution && e.stage == LifeStage::Egg, "invalid action phase");
                if (e.kind == ScheduledEvent::Kind::CollectFood)
                    ensure(s->foods.index.contains(e.resource) && e.requested_ug && e.destination == PositionM{}, "invalid food proposal");
                else ensure(!e.resource.value && !e.requested_ug, "invalid movement proposal");
            }
        }
    }
    // Check recorded facts against retained rows; no invented births, transfers or deaths.
    std::set<ColonyId> seeded_colonies; std::set<EntityId> seeded_ants; std::set<ResourceId> seeded_food;
    std::map<EntityId, LifeStage> stages; std::map<EntityId, PositionM> positions;
    std::map<EntityId, std::uint64_t> moves; std::map<EntityId, FoodMass> cargo;
    std::map<ResourceId, FoodMass> transferred;
    std::map<ColonyId, FoodMass> delivered;
    std::uint64_t executed_now = 0;
    for (const auto& e : s->journal) {
        if (e.source.value && e.time == m.now) ++executed_now;
        ensure((!e.actor.value || s->ants.index.contains(e.actor)) && (!e.colony.value || s->colonies.index.contains(e.colony)) &&
            (!e.resource.value || s->foods.index.contains(e.resource)), "fact has missing entity");
        if (e.actor.value) ensure(e.colony == s->ants.get(s->ants.index.at(e.actor)).colony, "fact colony mismatch");
        switch (e.kind) {
        case FactKind::Diagnostic:
            ensure(!e.actor.value && !e.colony.value && !e.resource.value && e.transferred == FoodMass{}, "invalid diagnostic fact"); break;
        case FactKind::ColonySeeded:
            ensure(e.colony.value && !e.actor.value && !e.resource.value && seeded_colonies.insert(e.colony).second &&
                e.position == s->colonies.rows[s->colonies.index.at(e.colony)].nest_position, "duplicate or invalid colony seed"); break;
        case FactKind::AntSeeded:
            ensure(e.actor.value && seeded_colonies.contains(e.colony) && seeded_ants.insert(e.actor).second &&
                e.stage != LifeStage::Dead && inside(e.position, s->config), "invalid ant seed fact");
            stages[e.actor] = e.stage; positions[e.actor] = e.position; break;
        case FactKind::FoodPlaced:
        case FactKind::FoodSeeded: {
            ensure(e.resource.value && !e.actor.value && seeded_food.insert(e.resource).second, "invalid food seed fact");
            const auto& f = s->foods.rows[s->foods.index.at(e.resource)];
            ensure(e.transferred == f.initial && e.position == f.position, "food seed fact mismatch"); break;
        }
        case FactKind::Moved:
            ensure(seeded_ants.contains(e.actor) && stages[e.actor] == LifeStage::Adult && e.stage == LifeStage::Adult &&
                inside(e.position, s->config) && !e.resource.value, "invalid movement fact");
            positions[e.actor] = e.position; ++moves[e.actor]; break;
        case FactKind::FoodCollected:
            ensure(seeded_ants.contains(e.actor) && seeded_food.contains(e.resource) && stages[e.actor] == LifeStage::Adult &&
                e.transferred.total_ug() > 0 && (e.outcome == Outcome::Success || e.outcome == Outcome::Partial), "invalid collection fact");
            cargo[e.actor] = sum(cargo[e.actor], e.transferred); transferred[e.resource] = sum(transferred[e.resource], e.transferred); break;
        case FactKind::StageChanged:
            ensure(seeded_ants.contains(e.actor) && e.stage != LifeStage::Dead &&
                static_cast<unsigned>(e.stage) == static_cast<unsigned>(stages[e.actor])+1, "invalid stage fact");
            stages[e.actor] = e.stage; break;
        case FactKind::AntDied:
            ensure(seeded_ants.contains(e.actor) && stages[e.actor] != LifeStage::Dead && e.stage == LifeStage::Dead, "duplicate or invalid death");
            stages[e.actor] = LifeStage::Dead; break;
        case FactKind::ActionRejected:
            ensure(seeded_ants.contains(e.actor) && e.outcome > Outcome::Partial && e.transferred == FoodMass{}, "invalid rejected action fact"); break;
        case FactKind::FoodDelivered:
            ensure(seeded_ants.contains(e.actor) && stages[e.actor] == LifeStage::Adult && e.transferred.total_ug() &&
                distance(e.position, s->colonies.rows[s->colonies.index.at(e.colony)].nest_position) <= s->config.contact_distance_m,
                "invalid physical delivery fact");
            cargo[e.actor] = subtract(cargo[e.actor], e.transferred); delivered[e.colony] = sum(delivered[e.colony], e.transferred); break;
        case FactKind::Rested:
            ensure(seeded_ants.contains(e.actor) && stages[e.actor] == LifeStage::Adult, "invalid rest fact"); break;
        case FactKind::CargoIngested:
            cargo[e.actor] = subtract(cargo[e.actor], e.transferred); break;
        case FactKind::NestIngested:
            ensure(distance(e.position, s->colonies.rows[s->colonies.index.at(e.colony)].nest_position) <= s->config.contact_distance_m,
                "nest ingestion has no physical contact");
            delivered[e.colony] = subtract(delivered[e.colony], e.transferred); break;
        case FactKind::PhysiologyEnabled:
        case FactKind::PhysiologyUpdated:
        case FactKind::BehaviorChanged:
        case FactKind::NutritionDecision:
        case FactKind::NutritionTransferred: break;
        case FactKind::GeometryConfigured:
        case FactKind::SoilExcavated:
        case FactKind::SoilDropped:
        case FactKind::SoilPickedUp:
        case FactKind::SoilFilled:
        case FactKind::ExcavationDecision: ensure(s->geometry != nullptr,"geometry fact without geometry"); break;
        case FactKind::SurfaceConfigured:
        case FactKind::ForagingStarted:
        case FactKind::ForagingDecision:
        case FactKind::TrailMaintenance: ensure(s->surface != nullptr, "surface fact without surface"); break;
        }
        if (nutrition_fact(e.kind)) ensure(e.transferred.total_ug() && e.outcome <= Outcome::Partial, "invalid nutrition transfer fact");
        if (e.kind != FactKind::FoodCollected && e.kind != FactKind::FoodSeeded && e.kind != FactKind::FoodPlaced && e.kind != FactKind::FoodDelivered &&
            !nutrition_fact(e.kind) && e.kind != FactKind::PhysiologyEnabled && e.kind != FactKind::PhysiologyUpdated)
            ensure(e.transferred == FoodMass{}, "unexpected transfer in fact");
        if (e.kind != FactKind::ActionRejected && e.kind != FactKind::FoodCollected && !nutrition_fact(e.kind))
            ensure(e.outcome == Outcome::Success, "unexpected fact outcome");
    }
    ensure(seeded_colonies.size() == colonies && seeded_ants.size() == ants && seeded_food.size() == foods &&
        executed_now == m.executed, "missing seed evidence or execution count mismatch");
    for (std::size_t i = 0; i < ants; ++i) {
        const auto a = s->ants.get(i);
        ensure(stages[a.id] == a.stage && positions[a.id] == a.position && moves[a.id] == a.position_revision &&
            cargo[a.id] == a.carried_food, "ant row disagrees with committed facts");
    }
    for (const auto& f : s->foods.rows) ensure(sum(f.remaining, transferred[f.id]) == f.initial, "source disagrees with transfer facts");
    for (const auto& c : s->colonies.rows) ensure(delivered[c.id] == c.nest_food, "nest inventory disagrees with delivery facts");
    validate_surface_evidence(*s);
    validate_geometry_evidence(*s,limits);
    validate_physiology_evidence(*s);
    ensure(m.next_event == facts+1 && r.cursor == r.bytes.size(), "invalid event allocator or trailing checkpoint bytes");
    return s;
}
std::vector<std::uint8_t> WorldRuntime::checkpoint() const { return encode(*state_, limits_.checkpoint_bytes); }
void WorldRuntime::restore(std::span<const std::uint8_t> bytes) {
    auto restored = decode(bytes, limits_); state_.swap(restored);
}
} // namespace antworld
