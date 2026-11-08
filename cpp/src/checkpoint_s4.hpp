#pragma once
#include "checkpoint_codec.hpp"
#include "state.hpp"
#include <bit>
#include <set>

namespace antworld::detail {
inline void write_point(Writer &w, PointQ p) {
    for (auto v : {p.x, p.y, p.z})
        w.put(static_cast<std::uint32_t>(v), 4);
}
inline PointQ read_point(Reader &r) {
    const auto x = std::bit_cast<std::int32_t>(static_cast<std::uint32_t>(r.get(4)));
    const auto y = std::bit_cast<std::int32_t>(static_cast<std::uint32_t>(r.get(4)));
    const auto z = std::bit_cast<std::int32_t>(static_cast<std::uint32_t>(r.get(4)));
    ensure(x >= -1000000 && x <= 1000000 && y >= -1000000 && y <= 1000000 && z >= -1000000 && z <= 1000000,
           "geometry coordinate range");
    return {x, y, z};
}
inline void write_box(Writer &w, BoxQ b) {
    write_point(w, b.min);
    write_point(w, b.max);
}
inline BoxQ read_box(Reader &r) { return {read_point(r), read_point(r)}; }
inline constexpr std::array geometry_ints{&GeometryConfig::body_half_q, &GeometryConfig::loaded_half_q,
                                          &GeometryConfig::reach_q,     &GeometryConfig::max_patch_extent_q,
                                          &GeometryConfig::brick_q,     &GeometryConfig::sample_step_q,
                                          &GeometryConfig::sdf_band_q};
inline constexpr std::array soil_values{&SoilLedger::initial_q3,   &SoilLedger::remaining_q3, &SoilLedger::carried_q3,
                                        &SoilLedger::deposited_q3, &SoilLedger::excavated_q3, &SoilLedger::filled_q3};
template <class S> void write_geometry(Writer &w, const S &s) {
    w.put(static_cast<bool>(s.geometry), 1);
    if (!s.geometry)
        return;
    const auto &c = s.geometry->config;
    w.position(c.origin_m);
    w.real(c.quantum_m);
    write_box(w, c.initial_solid);
    w.put(c.dry_ug_per_q3);
    w.put(c.water_ug_per_q3);
    for (auto member : geometry_ints)
        w.put(static_cast<std::uint32_t>(c.*member), 4);
    w.time(c.work_duration);
    w.time(c.move_duration);
    w.time(c.decision_delay);
    w.put(c.dig_energy_nj_per_q3);
    for (const auto *boxes : {&s.geometry->voids, &s.geometry->rocks}) {
        w.put(boxes->size());
        for (auto box : *boxes)
            write_box(w, box);
    }
    w.put(s.m.geometry_revision);
    for (auto member : soil_values)
        w.put(s.m.soil.*member);
    w.put(s.geometry_edits.size());
    for (const auto &[id, e] : s.geometry_edits) {
        w.put(id.value);
        w.put(e.source.value);
        w.put(e.event.value);
        w.put(e.actor.value);
        w.put(e.parcel.value);
        w.put(static_cast<std::uint8_t>(e.kind), 1);
        w.time(e.time);
        write_box(w, e.box);
        w.put(e.volume_q3);
    }
    w.put(s.parcels.size());
    for (const auto &[id, p] : s.parcels) {
        w.put(id.value);
        w.put(p.origin_edit.value);
        w.put(p.initial_q3);
        w.put(p.remaining_q3);
        w.put(p.carrier.value);
        w.position(p.position);
        w.put(static_cast<std::uint8_t>(p.state), 1);
    }
    w.put(s.soil_requests.size());
    for (const auto &[id, p] : s.soil_requests) {
        w.put(id.value);
        w.put(p.actor.value);
        w.put(static_cast<std::uint8_t>(p.kind), 1);
        write_box(w, p.box);
        w.put(p.parcel.value);
        w.put(p.observed_revision);
        w.put(p.actual_q3);
        w.put(p.edit.value);
    }
    w.put(s.excavators.size());
    for (const auto &[id, p] : s.excavators) {
        w.put(id.value);
        w.put(p.enabled, 1);
        w.put(p.decisions);
        w.put(p.digs);
        w.put(p.carrying_moves);
        w.put(p.deliveries);
        w.put(p.path_size, 4);
        for (std::uint32_t i = 0; i < p.path_size; ++i)
            write_point(w, p.path[i]);
        w.put(p.wake.value);
        w.put(p.action.value);
    }
}
template <class S>
void read_geometry(Reader &r, S &s, const RuntimeLimits &limits, std::set<std::uint64_t> &entity_ids) {
    if (!r.flag())
        return;
    auto d = std::make_shared<GeometryDefinition>();
    auto &c = d->config;
    c.origin_m = r.position();
    c.quantum_m = r.real();
    c.initial_solid = read_box(r);
    c.dry_ug_per_q3 = r.get();
    c.water_ug_per_q3 = r.get();
    for (auto member : geometry_ints) {
        const auto v = r.get(4);
        ensure(v <= INT32_MAX, "invalid geometry integer");
        c.*member = static_cast<std::int32_t>(v);
    }
    c.work_duration = r.time();
    c.move_duration = r.time();
    c.decision_delay = r.time();
    c.dig_energy_nj_per_q3 = r.get();
    for (auto *boxes : {&d->voids, &d->rocks}) {
        const auto n = r.count(256, 24);
        for (std::size_t i = 0; i < n; ++i)
            boxes->push_back(read_box(r));
    }
    validate_geometry(*d, s.config, limits.geometry_partition_cells);
    s.geometry = d;
    s.m.geometry_revision = r.get();
    for (auto member : soil_values)
        s.m.soil.*member = r.get();
    auto count = r.count(limits.geometry_edits, 81);
    for (std::size_t i = 0; i < count; ++i) {
        GeometryEdit e;
        e.id = {r.get()};
        e.source = {r.get()};
        e.event = {r.get()};
        e.actor = {r.get()};
        e.parcel = {r.get()};
        e.kind = static_cast<SoilAction>(r.get(1));
        e.time = r.time();
        e.box = read_box(r);
        e.volume_q3 = r.get();
        ensure(e.id.value == i + 1 && e.source.value && e.source.value < s.m.next_scheduled && e.event.value &&
                   e.event.value < s.m.next_event && s.ants.index.contains(e.actor) &&
                   (e.kind == SoilAction::Excavate || e.kind == SoilAction::Fill) && e.time <= s.m.now &&
                   box_valid(e.box) && encloses(c.initial_solid, e.box) && e.volume_q3,
               "invalid geometry edit provenance");
        s.geometry_edits.emplace(e.id, e);
        for (auto key : overlapping_bricks(e.box, c.brick_q, limits.geometry_index_entries)) {
            ensure(s.edit_index.size() < limits.geometry_index_entries, "geometry index host budget");
            s.edit_index.emplace(std::pair{key, e.id}, std::uint8_t{0});
        }
    }
    ensure(s.m.geometry_revision == s.geometry_edits.size(), "geometry revision mismatch");
    count = r.count(limits.entities, 65);
    for (std::size_t i = 0; i < count; ++i) {
        SoilParcel p;
        p.id = {r.get()};
        p.origin_edit = {r.get()};
        p.initial_q3 = r.get();
        p.remaining_q3 = r.get();
        p.carrier = {r.get()};
        p.position = r.position();
        p.state = static_cast<ParcelState>(r.get(1));
        ensure(entity_ids.size() < limits.entities && p.id.value && p.id.value < s.m.next_entity &&
                   entity_ids.insert(p.id.value).second && p.initial_q3 && p.remaining_q3 <= p.initial_q3 &&
                   p.state <= ParcelState::Exhausted && inside(p.position, s.config) &&
                   quantized(p.position, c).has_value() && s.geometry_edits.contains(p.origin_edit),
               "invalid soil parcel");
        if (p.state == ParcelState::Carried)
            ensure(s.ants.index.contains(p.carrier) && s.carriers.emplace(p.carrier, p.id).second,
                   "invalid soil carrier");
        else
            ensure(!p.carrier.value, "unowned soil parcel has carrier");
        ensure((p.state == ParcelState::Exhausted) == (p.remaining_q3 == 0), "parcel exhaustion mismatch");
        s.parcels.emplace(p.id, p);
    }
    count = r.count(limits.committed_events, 73);
    for (std::size_t i = 0; i < count; ++i) {
        const ScheduledId id{r.get()};
        SoilRequest p;
        p.actor = {r.get()};
        p.kind = static_cast<SoilAction>(r.get(1));
        p.box = read_box(r);
        p.parcel = {r.get()};
        p.observed_revision = r.get();
        p.actual_q3 = r.get();
        p.edit = {r.get()};
        ensure(id.value && id.value < s.m.next_scheduled && s.ants.index.contains(p.actor) &&
                   p.kind <= SoilAction::Fill && (p.kind == SoilAction::Excavate || s.parcels.contains(p.parcel)) &&
                   (!(p.kind == SoilAction::Excavate || p.kind == SoilAction::Fill) ||
                    (box_valid(p.box) && encloses(c.initial_solid, p.box))) &&
                   s.soil_requests.emplace(id, p).second,
               "invalid soil request");
    }
    count = r.count(limits.entities, 73);
    for (std::size_t i = 0; i < count; ++i) {
        const EntityId id{r.get()};
        ExcavatorState p;
        p.enabled = r.flag();
        p.decisions = r.get();
        p.digs = r.get();
        p.carrying_moves = r.get();
        p.deliveries = r.get();
        p.path_size = static_cast<std::uint32_t>(r.get(4));
        ensure(p.path_size && p.path_size <= p.path.size(), "invalid excavation memory length");
        for (std::uint32_t j = 0; j < p.path_size; ++j)
            p.path[j] = read_point(r);
        p.wake = {r.get()};
        p.action = {r.get()};
        ensure(s.ants.index.contains(id) && s.physiology.contains(id) && s.excavators.emplace(id, p).second,
               "invalid excavator identity");
    }
    for (const auto &row : s.ants.identities) {
        const auto ant = s.ants.get(s.ants.index.at(row.id));
        ensure(quantized(ant.position, c).has_value(), "nonquantized geometry actor");
        s.spatial_index.emplace(std::pair{spatial_key(ant.position), row.id.value}, std::uint8_t{1});
    }
    for (const auto &food : s.foods.rows) {
        ensure(quantized(food.position, c).has_value(), "nonquantized geometry food");
        s.spatial_index.emplace(std::pair{spatial_key(food.position), food.id.value}, std::uint8_t{2});
    }
}
template <class S> void validate_geometry_evidence(const S &s, const RuntimeLimits &limits) {
    if (!s.geometry) {
        for (const auto &e : s.journal)
            ensure(e.kind < FactKind::GeometryConfigured, "geometry fact without authority");
        for (const auto &[key, e] : s.queue) {
            (void)key;
            ensure(e.kind < ScheduledEvent::Kind::SoilAction, "geometry event without authority");
        }
        return;
    }
    const auto &c = s.geometry->config;
    GeometryEdits edits;
    EditIndex index;
    typename S::Parcels parcels;
    typename S::Carriers carriers;
    typename S::Excavators excavators;
    std::map<EntityId, PositionM> positions;
    std::map<EntityId, FoodMass> cargo;
    std::map<EntityId, LifeStage> stages;
    std::set<ScheduledId> completed;
    SoilLedger ledger;
    bool configured = false;
    auto view = [&] { return GeometryView{*s.geometry, edits, index, limits.geometry_partition_cells}; };
    auto half = [&](EntityId id) {
        return carriers.contains(id) || cargo[id].total_ug() ? c.loaded_half_q : c.body_half_q;
    };
    auto clear = [&](PositionM a, PositionM b, std::int32_t radius) {
        return historical_clear(*s.geometry, edits, index, a, b, radius, limits.geometry_partition_cells);
    };
    for (const auto &e : s.journal) {
        if (e.kind == FactKind::GeometryConfigured) {
            ensure(!configured && positions.empty() && e.time == SimTime{} && !e.actor.value,
                   "invalid geometry configuration history");
            configured = true;
            ledger.initial_q3 = material_volume(view(), c.initial_solid, Material::Soil);
            ledger.remaining_q3 = ledger.initial_q3;
        }
        if (e.kind == FactKind::AntSeeded || e.kind == FactKind::FoodSeeded || e.kind == FactKind::ColonySeeded)
            ensure(configured && clear(e.position, e.position, e.kind == FactKind::AntSeeded ? c.body_half_q : 1),
                   "seed embedded in material");
        if (e.kind == FactKind::AntSeeded) {
            positions[e.actor] = e.position;
            stages[e.actor] = e.stage;
        }
        if (e.kind == FactKind::Moved) {
            ensure(clear(positions.at(e.actor), e.position, half(e.actor)),
                   "historical movement crosses solid material");
            positions[e.actor] = e.position;
            if (carriers.contains(e.actor))
                parcels.at(carriers.at(e.actor)).position = e.position;
            if (excavators.contains(e.actor) && excavators.at(e.actor).enabled) {
                auto &worker = excavators.at(e.actor);
                const auto p = *quantized(e.position, c);
                std::uint32_t i = 0;
                while (i < worker.path_size && worker.path[i] != p)
                    ++i;
                ensure(i < worker.path.size(), "excavation trace overflow");
                worker.path[i] = p;
                worker.path_size = i + 1;
                if (carriers.contains(e.actor))
                    ++worker.carrying_moves;
            }
        }
        if (e.kind == FactKind::FoodCollected) {
            const auto &food = s.foods.rows[s.foods.index.at(e.resource)];
            ensure(clear(positions.at(e.actor), food.position, 1) &&
                       clear(positions.at(e.actor), positions.at(e.actor), c.loaded_half_q),
                   "food crosses solid material");
            cargo[e.actor] = sum(cargo[e.actor], e.transferred);
        }
        if (e.kind == FactKind::FoodDelivered || e.kind == FactKind::NestIngested)
            ensure(clear(positions.at(e.actor), s.colonies.rows[s.colonies.index.at(e.colony)].nest_position, 1),
                   "nest inventory crosses solid material");
        if (e.kind == FactKind::FoodDelivered || e.kind == FactKind::CargoIngested)
            cargo[e.actor] = subtract(cargo[e.actor], e.transferred);
        if (e.kind == FactKind::NutritionTransferred)
            ensure(clear(positions.at(e.actor), positions.at(EntityId{e.payload}), 1),
                   "trophallaxis crosses solid material");
        if (e.kind == FactKind::BehaviorChanged) {
            if (e.payload == static_cast<std::uint64_t>(IndividualBehavior::Excavate)) {
                auto &worker = excavators[e.actor];
                if (!worker.path_size) {
                    ensure(positions.at(e.actor) == s.colonies.rows[s.colonies.index.at(e.colony)].nest_position,
                           "excavator has no known depot");
                    worker.path[0] = *quantized(e.position, c);
                    worker.path_size = 1;
                }
                ensure(worker.path[worker.path_size - 1] == *quantized(e.position, c),
                       "excavator restart has stale position memory");
                worker.enabled = true;
            } else if (excavators.contains(e.actor))
                excavators.at(e.actor).enabled = false;
        }
        if (e.kind == FactKind::ExcavationDecision) {
            ensure(excavators.contains(e.actor) && excavators.at(e.actor).enabled,
                   "decision without active excavation program");
            ensure(e.payload == ++excavators.at(e.actor).decisions, "excavation decision evidence mismatch");
        }
        const bool soil = e.kind >= FactKind::SoilExcavated && e.kind <= FactKind::SoilFilled;
        if (soil) {
            ensure(configured && s.soil_requests.contains(e.source), "soil fact without request");
            const auto &request = s.soil_requests.at(e.source);
            ensure(request.actor == e.actor && e.payload == request.parcel.value &&
                       positions.at(e.actor) == e.position && stages.at(e.actor) == LifeStage::Adult &&
                       s.ants.get(s.ants.index.at(e.actor)).caste == Caste::Worker &&
                       request.observed_revision <= edits.size() && request.actual_q3 &&
                       completed.insert(e.source).second,
                   "invalid soil action evidence");
            const auto q = *quantized(e.position, c);
            if (e.kind == FactKind::SoilExcavated || e.kind == FactKind::SoilFilled) {
                const auto action = e.kind == FactKind::SoilExcavated ? SoilAction::Excavate : SoilAction::Fill;
                ensure(request.kind == action && local_patch(view(), q, request.box) &&
                           !material_volume(view(), request.box, Material::Rock),
                       "invalid reachable soil patch");
                const auto amount = material_volume(view(), request.box,
                                                    action == SoilAction::Excavate ? Material::Soil : Material::Void);
                ensure(amount == request.actual_q3 && s.geometry_edits.contains(request.edit) &&
                           request.edit.value == edits.size() + 1,
                       "edit removes nonexistent material");
                const auto &edit = s.geometry_edits.at(request.edit);
                ensure(edit == GeometryEdit{request.edit, e.source, e.id, e.actor, request.parcel, action, e.time,
                                            request.box, amount},
                       "edit/fact provenance mismatch");
                if (action == SoilAction::Excavate) {
                    ensure(!carriers.contains(e.actor) && clear(e.position, e.position, c.loaded_half_q),
                           "digging violates load clearance");
                    ensure(parcels
                               .emplace(request.parcel, SoilParcel{request.parcel, edit.id, amount, amount, e.actor,
                                                                   e.position, ParcelState::Carried})
                               .second,
                           "reused soil parcel identity");
                    carriers.emplace(e.actor, request.parcel);
                    ledger.remaining_q3 -= amount;
                    ledger.carried_q3 = add(ledger.carried_q3, amount);
                    ledger.excavated_q3 = add(ledger.excavated_q3, amount);
                    if (excavators.contains(e.actor) && excavators.at(e.actor).enabled)
                        ++excavators.at(e.actor).digs;
                } else {
                    ensure(carriers.contains(e.actor) && carriers.at(e.actor) == request.parcel,
                           "fill lacks physical soil carrier");
                    for (const auto &[id, p] : positions)
                        ensure(!box_valid(intersection(around(*quantized(p, c), half(id)), request.box)),
                               "fill embeds an individual");
                    for (const auto &food : s.foods.rows)
                        ensure(!contains(request.box, *quantized(food.position, c)), "fill embeds food");
                    for (const auto &colony : s.colonies.rows)
                        ensure(!contains(request.box, *quantized(colony.nest_position, c)), "fill embeds nest anchor");
                    auto &parcel = parcels.at(request.parcel);
                    ensure(parcel.remaining_q3 >= amount, "fill creates material");
                    parcel.remaining_q3 -= amount;
                    if (!parcel.remaining_q3) {
                        parcel.state = ParcelState::Exhausted;
                        parcel.carrier = {};
                        carriers.erase(e.actor);
                    }
                    ledger.carried_q3 -= amount;
                    ledger.remaining_q3 = add(ledger.remaining_q3, amount);
                    ledger.filled_q3 = add(ledger.filled_q3, amount);
                }
                edits.emplace(edit.id, edit);
                for (auto key : overlapping_bricks(edit.box, c.brick_q, limits.geometry_index_entries))
                    index.emplace(std::pair{key, edit.id}, std::uint8_t{0});
            } else {
                ensure(parcels.contains(request.parcel) && !request.edit.value, "invalid parcel transfer history");
                auto &parcel = parcels.at(request.parcel);
                ensure(parcel.remaining_q3 == request.actual_q3, "parcel transfer amount mismatch");
                if (e.kind == FactKind::SoilDropped) {
                    ensure(request.kind == SoilAction::Drop && carriers.contains(e.actor) &&
                               carriers.at(e.actor) == parcel.id,
                           "drop lacks carried parcel");
                    carriers.erase(e.actor);
                    parcel.carrier = {};
                    parcel.position = e.position;
                    parcel.state = ParcelState::Deposited;
                    ledger.carried_q3 -= parcel.remaining_q3;
                    ledger.deposited_q3 = add(ledger.deposited_q3, parcel.remaining_q3);
                    if (excavators.contains(e.actor) && excavators.at(e.actor).enabled)
                        ++excavators.at(e.actor).deliveries;
                } else {
                    ensure(request.kind == SoilAction::Pickup && parcel.state == ParcelState::Deposited &&
                               !carriers.contains(e.actor) &&
                               distance(e.position, parcel.position) <= s.config.contact_distance_m &&
                               clear(e.position, parcel.position, 1) && clear(e.position, e.position, c.loaded_half_q),
                           "pickup lacks local physical parcel");
                    carriers.emplace(e.actor, parcel.id);
                    parcel.carrier = e.actor;
                    parcel.position = e.position;
                    parcel.state = ParcelState::Carried;
                    ledger.deposited_q3 -= parcel.remaining_q3;
                    ledger.carried_q3 = add(ledger.carried_q3, parcel.remaining_q3);
                }
            }
        }
        if (e.kind == FactKind::AntDied && excavators.contains(e.actor))
            excavators.at(e.actor).enabled = false;
        if (e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied)
            stages[e.actor] = e.stage;
        if (e.actor.value && positions.contains(e.actor)) {
            const auto soil_mass = carriers.contains(e.actor) ? parcels.at(carriers.at(e.actor)).remaining_q3 *
                                                                    (c.dry_ug_per_q3 + c.water_ug_per_q3)
                                                              : 0;
            ensure(add(soil_mass, cargo[e.actor].total_ug()) <=
                       s.ants.get(s.ants.index.at(e.actor)).carrying_capacity_ug,
                   "history exceeds combined cargo capacity");
        }
    }
    ensure(configured && edits == s.geometry_edits && parcels == s.parcels && carriers == s.carriers &&
               ledger == s.m.soil &&
               add(add(ledger.remaining_q3, ledger.carried_q3), ledger.deposited_q3) == ledger.initial_q3,
           "soil authority disagrees with committed history");
    for (const auto &[id, p] : s.soil_requests) {
        ensure((p.actual_q3 != 0) == completed.contains(id), "soil request claims an uncommitted result");
        if (!p.actual_q3)
            ensure(!p.edit.value, "unused request has a geometry edit");
    }
    ensure(excavators.size() == s.excavators.size(), "missing excavation program evidence");
    for (const auto &[id, saved] : s.excavators) {
        auto actual = saved, expected = excavators.at(id);
        actual.wake = {};
        actual.action = {};
        // Unused trace slots are derived scratch and not part of the persisted memory.
        for (std::size_t i = actual.path_size; i < actual.path.size(); ++i) {
            actual.path[i] = {};
            expected.path[i] = {};
        }
        ensure(actual == expected, "excavation memory/counters disagree with history");
        if (saved.enabled) {
            ensure(static_cast<bool>(saved.wake.value) != static_cast<bool>(saved.action.value),
                   "excavator requires exactly one owned event");
            const auto event = saved.wake.value ? saved.wake : saved.action;
            ensure(s.queue_index.contains(event), "missing excavation event");
            const auto &e = s.queue.at(s.queue_index.at(event));
            ensure(e.actor == id && (saved.wake.value ? e.kind == ScheduledEvent::Kind::ExcavationWake
                                                      : e.kind == ScheduledEvent::Kind::SoilAction ||
                                                            e.kind == ScheduledEvent::Kind::Move ||
                                                            e.kind == ScheduledEvent::Kind::Rest),
                   "invalid excavation event ownership");
        } else
            ensure(!saved.wake.value && !saved.action.value, "paused excavator retains owned events");
    }
}
} // namespace antworld::detail
