#include "state.hpp"
#include "physiology_internal.hpp"

namespace antworld {
using namespace detail;
namespace detail {
bool local_patch(const GeometryView &view, PointQ actor, BoxQ box) {
    const auto &c = view.definition.config;
    if (!box_valid(box) || !encloses(c.initial_solid, box) || !encloses(around(actor, c.reach_q), box) ||
        box.max.x - box.min.x > c.max_patch_extent_q || box.max.y - box.min.y > c.max_patch_extent_q ||
        box.max.z - box.min.z > c.max_patch_extent_q)
        return false;
    const PointQ mid{(box.min.x + box.max.x) / 2, (box.min.y + box.max.y) / 2, (box.min.z + box.max.z) / 2};
    const std::array<PointQ, 6> faces{{{box.min.x - 1, mid.y, mid.z},
                                       {box.max.x + 1, mid.y, mid.z},
                                       {mid.x, box.min.y - 1, mid.z},
                                       {mid.x, box.max.y + 1, mid.z},
                                       {mid.x, mid.y, box.min.z - 1},
                                       {mid.x, mid.y, box.max.z + 1}}};
    for (auto p : faces) {
        if (std::abs(p.x - actor.x) > c.reach_q || std::abs(p.y - actor.y) > c.reach_q ||
            std::abs(p.z - actor.z) > c.reach_q)
            continue;
        if (clear_sweep(view, actor, p, 1))
            return true;
    }
    return false;
}
} // namespace detail
ScheduledId WorldRuntime::submit_soil(const SoilProposal &p) {
    auto &s = *state_;
    const auto ant = query_ant(p.actor);
    if (!s.geometry || !ant || p.kind > SoilAction::Fill ||
        (s.care.contains(p.actor.id) && s.care.at(p.actor.id).enabled) ||
        (s.autonomy.contains(p.actor.id) && s.autonomy.at(p.actor.id).enabled) ||
        (s.foragers.contains(p.actor.id) && s.foragers.at(p.actor.id).enabled) ||
        (s.physiology.contains(p.actor.id) && s.physiology.at(p.actor.id).behavior != IndividualBehavior::Paused) ||
        ((p.kind == SoilAction::Pickup || p.kind == SoilAction::Fill || p.kind == SoilAction::Drop) &&
         !query_parcel(p.parcel)))
        throw std::invalid_argument("invalid soil proposal or active individual program");
    if ((p.kind == SoilAction::Excavate || p.kind == SoilAction::Fill) &&
        (!box_valid(p.box) || !encloses(s.geometry->config.initial_solid, p.box)))
        throw std::invalid_argument("invalid soil patch");
    ScheduledEvent e;
    e.actor = p.actor.id;
    e.kind = ScheduledEvent::Kind::SoilAction;
    e.issued_at = s.m.now;
    e.key = {p.execute_at, Phase::Resolution, 0, 0, 0};
    e.observed_position_revision = ant->position_revision;
    Transaction tx(s, limits_);
    const auto id = tx.insert(e);
    if (s.soil_requests.size() >= limits_.committed_events)
        throw std::length_error("soil request history budget exceeded");
    tx.soil_requests.set(id, {p.actor.id, p.kind, p.box, p.parcel.id, p.observed_geometry_revision, 0, {}});
    tx.commit();
    return id;
}
void WorldRuntime::resolve_soil_action(Transaction &tx, const ScheduledEvent &e, WorldEvent &f) {
    auto &s = *state_;
    auto request = s.soil_requests.at(e.id);
    const auto &c = s.geometry->config;
    const auto ant = s.ants.get(s.ants.index.at(e.actor));
    const auto q = *quantized(ant.position, c);
    const auto view = geometry_view(s, limits_);
    if (e.key.time.milliseconds - e.issued_at.milliseconds < c.work_duration.milliseconds) {
        f.outcome = Outcome::TooFast;
        return;
    }
    if (request.observed_revision > s.m.geometry_revision) {
        f.outcome = Outcome::StaleGeometry;
        return;
    }
    const auto unit_mass = c.dry_ug_per_q3 + c.water_ug_per_q3;
    const auto carrying = s.carriers.find(e.actor);
    if (request.kind == SoilAction::Excavate || request.kind == SoilAction::Fill) {
        if (!local_patch(view, q, request.box)) {
            f.outcome = Outcome::OutOfReach;
            return;
        }
        if (material_volume(view, request.box, Material::Rock)) {
            f.outcome = Outcome::NonDiggable;
            return;
        }
        const auto amount =
            material_volume(view, request.box, request.kind == SoilAction::Excavate ? Material::Soil : Material::Void);
        if (!amount) {
            f.outcome = Outcome::Depleted;
            return;
        }
        if (request.kind == SoilAction::Excavate) {
            if (carrying != s.carriers.end() ||
                amount * unit_mass > ant.carrying_capacity_ug - ant.carried_food.total_ug()) {
                f.outcome = Outcome::Capacity;
                return;
            }
            // The larger loaded envelope must already fit at the worker's stationary position.
            if (!clear_sweep(view, q, q, c.loaded_half_q)) {
                f.outcome = Outcome::Blocked;
                return;
            }
            if (s.physiology.contains(e.actor)) {
                const auto p = *query_physiology({s.world, e.actor});
                if (multiply(amount, c.dig_energy_nj_per_q3) >= p.body_energy_nj) {
                    f.outcome = Outcome::InsufficientEnergy;
                    return;
                }
            }
        } else {
            if (carrying == s.carriers.end() || carrying->second != request.parcel ||
                s.parcels.at(request.parcel).remaining_q3 < amount) {
                f.outcome = Outcome::EmptyInventory;
                return;
            }
            // Filling cannot embed an individual (including a dead body), food or a nest anchor.
            for (const auto &row : s.ants.identities) {
                const auto other = s.ants.get(s.ants.index.at(row.id));
                const auto p = *quantized(other.position, c);
                if (box_valid(intersection(around(p, body_half(row.id)), request.box))) {
                    f.outcome = Outcome::Blocked;
                    return;
                }
            }
            for (const auto &food : s.foods.rows)
                if (contains(request.box, *quantized(food.position, c))) {
                    f.outcome = Outcome::Blocked;
                    return;
                }
            for (const auto &colony : s.colonies.rows)
                if (contains(request.box, *quantized(colony.nest_position, c))) {
                    f.outcome = Outcome::Blocked;
                    return;
                }
        }
        if (s.geometry_edits.size() >= limits_.geometry_edits)
            throw std::length_error("geometry edit budget exceeded");
        const GeometryEditId edit_id{s.m.geometry_revision + 1};
        if (request.kind == SoilAction::Excavate) {
            tx.entity_budget();
            const SoilParcelId id{take(s.m.next_entity)};
            SoilParcel parcel{id, edit_id, amount, amount, e.actor, ant.position, ParcelState::Carried};
            tx.parcels.set(id, parcel);
            tx.carriers.set(e.actor, id);
            request.parcel = id;
            s.m.soil.remaining_q3 -= amount;
            s.m.soil.carried_q3 = add(s.m.soil.carried_q3, amount);
            s.m.soil.excavated_q3 = add(s.m.soil.excavated_q3, amount);
            f.kind = FactKind::SoilExcavated;
            if (s.physiology.contains(e.actor)) {
                synchronize_physiology(tx, e.actor);
                auto p = s.physiology.at(e.actor);
                const auto cost = multiply(amount, c.dig_energy_nj_per_q3);
                p.body_energy_nj -= cost;
                p.dissipated_energy_nj = add(p.dissipated_energy_nj, cost);
                tx.physiology.set(e.actor, p);
                schedule_physiology(tx, e.actor);
            }
        } else {
            auto parcel = s.parcels.at(request.parcel);
            parcel.remaining_q3 -= amount;
            if (!parcel.remaining_q3) {
                parcel.state = ParcelState::Exhausted;
                parcel.carrier = {};
                tx.carriers.erase(e.actor);
            }
            tx.parcels.set(parcel.id, parcel);
            s.m.soil.carried_q3 -= amount;
            s.m.soil.remaining_q3 = add(s.m.soil.remaining_q3, amount);
            s.m.soil.filled_q3 = add(s.m.soil.filled_q3, amount);
            f.kind = FactKind::SoilFilled;
        }
        GeometryEdit edit{edit_id,      e.id,    {s.m.next_event}, e.actor, request.parcel,
                          request.kind, s.m.now, request.box,      amount};
        tx.geometry_edits.set(edit_id, edit);
        bump(s.m.geometry_revision);
        index_geometry_edit(s.geometry_edits, s.edit_index, edit, c.brick_q, limits_.geometry_index_entries,
                            [&](const auto& key) { tx.edit_index.erase(key); },
                            [&](const auto& key) { tx.edit_index.set(key, 0); });
        const auto halo = c.sdf_band_q + c.loaded_half_q + 1;
        const BoxQ dirty{{request.box.min.x - halo, request.box.min.y - halo, request.box.min.z - halo},
                         {request.box.max.x + halo, request.box.max.y + halo, request.box.max.z + halo}};
        // Only existing cache entries require invalidation. Dirty reports cover cached seams.
        for (auto key : overlapping_bricks(dirty, c.brick_q, limits_.sdf_bricks))
            if (s.sdf_cache.contains(key))
                tx.dirty_bricks.set(key, s.m.geometry_revision);
        request.actual_q3 = amount;
        request.edit = edit_id;
        tx.soil_requests.set(e.id, request);
        f.payload = request.parcel.value;
    } else if (request.kind == SoilAction::Drop) {
        if (carrying == s.carriers.end() || carrying->second != request.parcel) {
            f.outcome = Outcome::EmptyInventory;
            return;
        }
        auto parcel = s.parcels.at(request.parcel);
        parcel.state = ParcelState::Deposited;
        parcel.carrier = {};
        parcel.position = ant.position;
        tx.parcels.set(parcel.id, parcel);
        tx.carriers.erase(e.actor);
        s.m.soil.carried_q3 -= parcel.remaining_q3;
        s.m.soil.deposited_q3 = add(s.m.soil.deposited_q3, parcel.remaining_q3);
        request.actual_q3 = parcel.remaining_q3;
        tx.soil_requests.set(e.id, request);
        f.kind = FactKind::SoilDropped;
        f.payload = parcel.id.value;
    } else {
        auto parcel = s.parcels.at(request.parcel);
        if (parcel.state != ParcelState::Deposited) {
            f.outcome = Outcome::Depleted;
            return;
        }
        if (distance(ant.position, parcel.position) > s.config.contact_distance_m ||
            !spatially_clear(ant.position, parcel.position)) {
            f.outcome = Outcome::OutOfReach;
            return;
        }
        if (carrying != s.carriers.end() ||
            parcel.remaining_q3 * unit_mass > ant.carrying_capacity_ug - ant.carried_food.total_ug()) {
            f.outcome = Outcome::Capacity;
            return;
        }
        if (!clear_sweep(view, q, q, c.loaded_half_q)) {
            f.outcome = Outcome::Blocked;
            return;
        }
        parcel.state = ParcelState::Carried;
        parcel.carrier = e.actor;
        parcel.position = ant.position;
        tx.parcels.set(parcel.id, parcel);
        tx.carriers.set(e.actor, parcel.id);
        s.m.soil.deposited_q3 -= parcel.remaining_q3;
        s.m.soil.carried_q3 = add(s.m.soil.carried_q3, parcel.remaining_q3);
        request.actual_q3 = parcel.remaining_q3;
        tx.soil_requests.set(e.id, request);
        f.kind = FactKind::SoilPickedUp;
        f.payload = parcel.id.value;
    }
}
std::vector<BoxQ> WorldRuntime::local_frontiers(AntRef ref) const {
    const auto &s = *state_;
    const auto ant = query_ant(ref);
    std::vector<BoxQ> result(0);
    if (!s.geometry || !ant || !ant->alive())
        return result;
    const auto &c = s.geometry->config;
    const auto p = *quantized(ant->position, c);
    const auto half = c.loaded_half_q;
    if (2 * half > c.max_patch_extent_q)
        return result;
    auto box = around(p, half);
    std::array<BoxQ, 6> candidates{box, box, box, box, box, box};
    candidates[0].min.x = box.max.x;
    candidates[0].max.x = box.max.x + 1;
    candidates[1].max.x = box.min.x;
    candidates[1].min.x = box.min.x - 1;
    candidates[2].min.y = box.max.y;
    candidates[2].max.y = box.max.y + 1;
    candidates[3].max.y = box.min.y;
    candidates[3].min.y = box.min.y - 1;
    candidates[4].min.z = box.max.z;
    candidates[4].max.z = box.max.z + 1;
    candidates[5].max.z = box.min.z;
    candidates[5].min.z = box.min.z - 1;
    const auto view = geometry_view(s, limits_);
    for (auto b : candidates)
        if (local_patch(view, p, b) && !material_volume(view, b, Material::Rock) &&
            material_volume(view, b, Material::Soil))
            result.push_back(b);
    return result;
}
void WorldRuntime::activate_excavator(Transaction &tx, EntityId id) {
    auto &s = *state_;
    auto worker = s.excavators.contains(id) ? s.excavators.at(id) : ExcavatorState{};
    const auto ant = s.ants.get(s.ants.index.at(id));
    const auto p = *quantized(ant.position, s.geometry->config);
    if (!worker.path_size) {
        if (ant.position != s.colonies.rows[s.colonies.index.at(ant.colony)].nest_position)
            throw std::invalid_argument("first excavation activation requires the known depot");
        worker.path[0] = p;
        worker.path_size = 1;
    } else if (worker.path[worker.path_size - 1] != p)
        throw std::invalid_argument("excavation memory no longer ends at the worker position");
    worker.enabled = true;
    ScheduledEvent e;
    e.kind = ScheduledEvent::Kind::ExcavationWake;
    e.actor = id;
    e.issued_at = s.m.now;
    e.key = {after(s.m.now, s.geometry->config.decision_delay.milliseconds), Phase::Perception, 0, 0, 0};
    worker.wake = tx.insert(e);
    tx.excavators.set(id, worker);
}
void WorldRuntime::stop_excavator(Transaction &tx, EntityId id) {
    auto &s = *state_;
    if (!s.excavators.contains(id))
        return;
    auto worker = s.excavators.at(id);
    for (auto event : {worker.wake, worker.action})
        if (s.queue_index.contains(event))
            tx.remove(s.queue_index.at(event));
    worker.enabled = false;
    worker.wake = {};
    worker.action = {};
    tx.excavators.set(id, worker);
}
void WorldRuntime::resolve_excavation_wakes(Transaction &tx, const std::vector<ScheduledEvent> &wakes) {
    auto &s = *state_;
    const auto &c = s.geometry->config;
    struct Choice {
        ScheduledEvent action;
        SoilRequest soil;
    };
    std::vector<Choice> choices(0);
    for (const auto &wake : wakes) {
        const auto &worker = s.excavators.at(wake.actor);
        const auto ant = s.ants.get(s.ants.index.at(wake.actor));
        const auto p = *quantized(ant.position, c);
        Rng rng(s.seed ^ 0x4558434156415445ULL ^ ant.id.value ^ (worker.decisions * 0x9e3779b97f4a7c15ULL));
        Choice choice;
        auto &action = choice.action;
        action.actor = ant.id;
        action.kind = ScheduledEvent::Kind::Rest;
        action.issued_at = s.m.now;
        action.observed_position_revision = ant.position_revision;
        action.key = {after(s.m.now, c.work_duration.milliseconds), Phase::Resolution, 0, 0, 0};
        const auto carrier = s.carriers.find(ant.id);
        if (carrier != s.carriers.end()) {
            if (worker.path_size == 1) {
                action.kind = ScheduledEvent::Kind::SoilAction;
                choice.soil = {ant.id, SoilAction::Drop, {}, carrier->second, s.m.geometry_revision, 0, {}};
            } else {
                const auto previous = worker.path[worker.path_size - 2];
                if (clear_sweep(geometry_view(s, limits_), p, previous, body_half(ant.id))) {
                    action.kind = ScheduledEvent::Kind::Move;
                    action.destination = physical(previous, c);
                }
            }
        } else {
            const auto frontiers = local_frontiers({s.world, ant.id});
            if (worker.path_size > 1 && !frontiers.empty()) {
                const auto box = frontiers[static_cast<std::size_t>(bounded_draw(rng, frontiers.size()))];
                action.kind = ScheduledEvent::Kind::SoilAction;
                choice.soil = {ant.id, SoilAction::Excavate, box, {}, s.m.geometry_revision, 0, {}};
            } else {
                std::vector<PointQ> candidates(0);
                std::int32_t best = -1;
                for (auto q : portal_neighbors(geometry_view(s, limits_), p, c.loaded_half_q, s.config)) {
                    const auto depot = worker.path[0];
                    const auto d = std::abs(q.x - depot.x) + std::abs(q.y - depot.y) + std::abs(q.z - depot.z);
                    if (d > best) {
                        candidates.clear();
                        best = d;
                    }
                    if (d == best)
                        candidates.push_back(q);
                }
                if (worker.path_size >= worker.path.size())
                    candidates = {worker.path[worker.path_size - 2]};
                if (!candidates.empty()) {
                    action.kind = ScheduledEvent::Kind::Move;
                    action.destination =
                        physical(candidates[static_cast<std::size_t>(bounded_draw(rng, candidates.size()))], c);
                }
            }
        }
        if (action.kind == ScheduledEvent::Kind::Move)
            action.key.time = after(s.m.now, c.move_duration.milliseconds);
        choices.push_back(choice);
    }
    for (std::size_t i = 0; i < choices.size(); ++i) {
        const auto &choice = choices[i];
        auto worker = s.excavators.at(choice.action.actor);
        bump(worker.decisions);
        worker.wake = {};
        worker.action = tx.insert(choice.action);
        if (choice.action.kind == ScheduledEvent::Kind::SoilAction) {
            if (s.soil_requests.size() >= limits_.committed_events)
                throw std::length_error("soil request history budget exceeded");
            tx.soil_requests.set(worker.action, choice.soil);
        }
        tx.excavators.set(choice.action.actor, worker);
        WorldEvent f;
        f.kind = FactKind::ExcavationDecision;
        f.actor = choice.action.actor;
        f.source = wakes[i].id;
        f.payload = worker.decisions;
        const auto ant = s.ants.get(s.ants.index.at(f.actor));
        f.colony = ant.colony;
        f.position = ant.position;
        f.stage = ant.stage;
        tx.fact(f);
        if (s.care_profile) {
            const auto act=choice.action.kind==ScheduledEvent::Kind::Move?CareAct::Walk:choice.action.kind==ScheduledEvent::Kind::Rest?
                CareAct::Inactive:choice.soil.kind==SoilAction::Excavate?CareAct::Excavate:CareAct::HandleSoil;
            observe(tx,ant.id,wakes[i].id,{ObservationPhase::Selected,act,{},worker.action,s.m.now,false});
        }
    }
}
void WorldRuntime::after_excavation_action(Transaction &tx, const ScheduledEvent &e, const WorldEvent &f,
                                           const AntState &) {
    auto &s = *state_;
    if (!s.excavators.contains(e.actor))
        return;
    auto worker = s.excavators.at(e.actor);
    if (!worker.enabled || worker.action != e.id)
        return;
    if (f.kind == FactKind::Moved) {
        const auto p = *quantized(f.position, s.geometry->config);
        std::uint32_t i = 0;
        while (i < worker.path_size && worker.path[i] != p)
            ++i;
        if (i == worker.path_size && i == worker.path.size())
            throw std::logic_error("excavation memory capacity exceeded");
        worker.path[i] = p;
        worker.path_size = i + 1;
        for (std::size_t j = worker.path_size; j < worker.path.size(); ++j)
            worker.path[j] = {};
        if (s.carriers.contains(e.actor))
            bump(worker.carrying_moves);
    }
    if (f.kind == FactKind::SoilExcavated)
        bump(worker.digs);
    if (f.kind == FactKind::SoilDropped)
        bump(worker.deliveries);
    ScheduledEvent wake;
    wake.actor = e.actor;
    wake.kind = ScheduledEvent::Kind::ExcavationWake;
    wake.issued_at = s.m.now;
    wake.key = {after(s.m.now, s.geometry->config.decision_delay.milliseconds), Phase::Perception, 0, 0, 0};
    worker.action = {};
    worker.wake = tx.insert(wake);
    tx.excavators.set(e.actor, worker);
}
} // namespace antworld
