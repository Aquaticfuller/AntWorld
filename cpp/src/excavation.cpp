#include "state.hpp"
#include "physiology_internal.hpp"
#include "ecological_internal.hpp"
#include "worker_motion.hpp"
#include "nest_scoring.hpp"
#include "spatial_navigation.hpp"

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
    const auto q = quantized(ant.position,c);
    const auto view = geometry_view(s, limits_);
    const auto automatic=s.excavators.find(e.actor);
    const auto duration = s.ecological && s.ecological->distance_clock && request.kind==SoilAction::Drop &&
        automatic!=s.excavators.end() && automatic->second.action==e.id
        ? s.ecological->soil_handling : c.work_duration;
    if (e.key.time.milliseconds - e.issued_at.milliseconds < duration.milliseconds) {
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
        if (!q || !local_patch(view,*q,request.box)) {
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
            if (!clear_sweep(view,*q,*q,c.loaded_half_q) || !clear_worker_traffic(ant,ant.position,c.loaded_half_q)) {
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
                if (s.config.continuous_spatial_motion?
                    intersects_body(request.box,other.position,body_half(row.id),c):
                    box_valid(intersection(around(*quantized(other.position,c),body_half(row.id)),request.box))) {
                    f.outcome = Outcome::Blocked;
                    return;
                }
            }
            for (const auto &food : s.foods.rows)
                if (s.config.continuous_spatial_motion?intersects_body(request.box,food.position,0,c):
                    contains(request.box,*quantized(food.position,c))) {
                    f.outcome = Outcome::Blocked;
                    return;
                }
            for (const auto &colony : s.colonies.rows)
                if (s.config.continuous_spatial_motion?intersects_body(request.box,colony.nest_position,0,c):
                    contains(request.box,*quantized(colony.nest_position,c))) {
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
        if (!within_contact(ant.position,parcel.position,s.config) ||
            !spatially_clear(ant.position, parcel.position)) {
            f.outcome = Outcome::OutOfReach;
            return;
        }
        if (carrying != s.carriers.end() ||
            parcel.remaining_q3 * unit_mass > ant.carrying_capacity_ug - ant.carried_food.total_ug()) {
            f.outcome = Outcome::Capacity;
            return;
        }
        if (s.config.continuous_spatial_motion?
            !spatially_clear(ant.position,ant.position,c.loaded_half_q):!clear_sweep(view,*q,*q,c.loaded_half_q)) {
            f.outcome = Outcome::Blocked;
            return;
        }
        if (!clear_worker_traffic(ant,ant.position,c.loaded_half_q)) { f.outcome=Outcome::Blocked; return; }
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
std::optional<BoxQ> WorldRuntime::shallow_soil_cap(PositionM from) const {
    const auto& s=*state_;
    if (!s.ecological || !s.ecological->founding_habitat || !s.care_profile || !s.geometry || !s.surface) return {};
    const auto& c=s.geometry->config;
    const auto point=quantized(from,c);
    const auto surface=surface_level(s);
    if (!point || !surface) return {};
    const auto half=c.loaded_half_q;
    const auto ground=*surface-half;
    const auto p=*point;
    if (ground!=c.initial_solid.max.y ||
        !within_distance(from,physical({p.x,ground,p.z},c),s.care_profile->perception_radius_m,true)) return {};
    const auto view=geometry_view(s,limits_);
    const auto layers=anatomical_nest(s)?4:sealed_chamber(s)?2:1;
    for (int thickness=1;thickness<=layers;++thickness) {
        const PointQ stance{p.x,ground-half-thickness,p.z};
        if (p.y>stance.y || !spatially_clear(from,physical(stance,c),half)) continue;
        const BoxQ cap{{p.x-half,ground-thickness,p.z-half},{p.x+half,ground,p.z+half}};
        if (shaft_attachment(view,stance,half) && local_patch(view,stance,cap) &&
            !material_volume(view,cap,Material::Rock) && material_volume(view,cap,Material::Soil)) return cap;
    }
    return {};
}

std::vector<BoxQ> WorldRuntime::local_frontiers(AntRef ref) const {
    const auto &s = *state_;
    const auto ant = query_ant(ref);
    std::vector<BoxQ> result(0);
    if (!s.geometry || !ant || !ant->alive())
        return result;
    const auto &c = s.geometry->config;
    const auto origin=quantized(ant->position,c);
    if (!origin) return result;
    const auto p=*origin;
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
    const auto origin=quantized(ant.position,s.geometry->config);
    if (!origin) throw std::invalid_argument("excavation requires a geometry waypoint");
    const auto p=*origin;
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
    worker.returning_empty=false;
    tx.excavators.set(id, worker);
}
void WorldRuntime::resolve_excavation_wakes(Transaction &tx, const std::vector<ScheduledEvent> &wakes) {
    auto &s = *state_;
    const auto &c = s.geometry->config;
    struct Choice {
        ScheduledEvent action;
        SoilRequest soil;
        bool stalled{};
        bool returning_empty{};
    };
    std::vector<Choice> choices(0);
    std::map<std::pair<PointQ,int>,ExcavationFeatures> features;
    std::map<PointQ,std::size_t> sensed_bodies;
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
        const auto follow_inbound=[&] {
            const auto previous = worker.path[worker.path_size - 2];
            const bool clear=s.ecological && s.ecological->distance_clock
                ? spatially_clear(ant.position,physical(previous,c),body_half(ant.id))
                : clear_sweep(geometry_view(s, limits_), p, previous, body_half(ant.id));
            if (clear) {
                action.kind = ScheduledEvent::Kind::Move;
                action.destination = physical(previous, c);
            }
        };
        const bool floor_search=local_nest_activity(s);
        const auto score=nest_scoring(s);
        const auto view=geometry_view(s,limits_);
        const bool scored=score!=NestScoring::Original;
        std::size_t local_bodies=0;
        if (score==NestScoring::SpatialDemand) {
            auto [it,new_site]=sensed_bodies.try_emplace(p,0);
            if (new_site)
                it->second=query_neighborhood({s.world,ant.id},std::min(16,3*c.reach_q)*c.quantum_m).ants.size();
            local_bodies=it->second;
        }
        const auto weight_at=[&](PointQ q,bool moving) {
            const auto base_y=worker.path[0].y;
            auto [it,fresh]=features.try_emplace({q,base_y},ExcavationFeatures{});
            if (fresh) it->second=excavation_features(view,score,q,s.m.now,base_y);
            return digging_weight(it->second,score,q,p,worker,local_bodies,moving);
        };
        const auto pick=[&](const auto& items,const auto& metric) -> const auto& {
            if (!scored) return items[static_cast<std::size_t>(bounded_draw(rng,items.size()))];
            std::vector<std::uint64_t> weights(0);
            std::uint64_t total=0;
            for (const auto& item:items) {
                const auto weight=metric(item);
                weights.push_back(weight);
                total+=weight;
            }
            auto draw=bounded_draw(rng,total);
            for (std::size_t i=0;i<weights.size();++i) {
                if (draw<weights[i]) return items[i];
                draw-=weights[i];
            }
            throw std::logic_error("missing weighted excavation candidate");
        };
        if (carrier != s.carriers.end()) {
            if (worker.path_size == 1) {
                action.kind = ScheduledEvent::Kind::SoilAction;
                choice.soil = {ant.id, SoilAction::Drop, {}, carrier->second, s.m.geometry_revision, 0, {}};
            } else follow_inbound();
        } else if (const auto cap=shallow_soil_cap(ant.position)) {
            // A thin reachable plug is a local frontier. Each ascent, dig and
            // loaded return still uses the same timed movement and soil actions.
            const auto amount=material_volume(view,*cap,Material::Soil);
            if (amount*(c.dry_ug_per_q3+c.water_ug_per_q3)<=ant.carrying_capacity_ug-ant.carried_food.total_ug()) {
                if (p.y+c.loaded_half_q==cap->min.y) {
                    action.kind=ScheduledEvent::Kind::SoilAction;
                    choice.soil={ant.id, SoilAction::Excavate,*cap,{},s.m.geometry_revision,0,{}};
                } else {
                    action.kind=ScheduledEvent::Kind::Move;
                    action.destination=physical({p.x,p.y+1,p.z},c);
                }
            }
        } else if (floor_search && (worker.returning_empty || worker.path_size>=(scored?56U:24U))) {
            choice.returning_empty=worker.path_size>1;
            if (choice.returning_empty) follow_inbound();
        } else {
            auto frontiers = local_frontiers({s.world, ant.id});
            if (floor_search)
                std::erase_if(frontiers,[&](BoxQ b) {
                    if (b.max.y-b.min.y>=2*c.loaded_half_q) return false;
                    return !scored || b.min.y<=p.y || !shaft_attachment(view,p,c.loaded_half_q);
                });
            if (scored) std::erase_if(frontiers,[&](BoxQ b) {
                const auto amount=material_volume(view,b,Material::Soil);
                const auto cargo=ant.carrying_capacity_ug-ant.carried_food.total_ug();
                return amount*(c.dry_ug_per_q3+c.water_ug_per_q3)>cargo;
            });
            if (score>=NestScoring::Reinforcement && worker.digs && !frontiers.empty()) {
                const auto d=[&](PointQ q) {
                    return std::abs(worker.last_cut.x-q.x)+std::abs(worker.last_cut.y-q.y)+std::abs(worker.last_cut.z-q.z);
                };
                // A reachable step toward an experienced nearby cut can
                // outrank side-wall work. A cut farther away supplies no cue.
                if (d(p)<=3*c.reach_q && d(p)>c.loaded_half_q) {
                    const auto portals=portal_neighbors(view,p,c.loaded_half_q,s.config);
                    if (std::any_of(portals.begin(),portals.end(),[&](PointQ q) {
                        return q.y==p.y && d(q)<d(p) && work_floor(view,q,c.loaded_half_q) &&
                               spatially_clear(ant.position,physical(q,c),c.loaded_half_q) &&
                               std::find(worker.path.begin(),worker.path.begin()+worker.path_size,q)==worker.path.begin()+worker.path_size;
                    }) && bounded_draw(rng,4)!=0) frontiers.clear();
                }
            }
            if (worker.path_size > 1 && !frontiers.empty()) {
                const auto box=pick(frontiers,[&](BoxQ b) {
                    return weight_at(patch_center(b),false);
                });
                action.kind = ScheduledEvent::Kind::SoilAction;
                choice.soil = {ant.id, SoilAction::Excavate, box, {}, s.m.geometry_revision, 0, {}};
            } else {
                std::vector<PointQ> candidates(0);
                std::int32_t best = -1;
                for (auto q : portal_neighbors(view, p, c.loaded_half_q, s.config)) {
                    if (s.ecological && s.ecological->distance_clock &&
                        !spatially_clear(ant.position,physical(q,c),c.loaded_half_q)) continue;
                    const auto depot = worker.path[0];
                    if (floor_search && (!(scored ?
                        ((q.y==p.y && work_floor(view,q,c.loaded_half_q)) ||
                         (shaft_attachment(view,p,c.loaded_half_q) && shaft_attachment(view,q,c.loaded_half_q))) :
                        q.y==depot.y && work_floor(view,q,c.loaded_half_q)) ||
                        std::find(worker.path.begin(),worker.path.begin()+worker.path_size,q)!=worker.path.begin()+worker.path_size))
                        continue;
                    if (scored) { candidates.push_back(q); continue; }
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
                    action.destination=physical(pick(candidates,[&](PointQ q) {
                        auto weight=weight_at(q,true);
                        if (score>=NestScoring::Reinforcement && worker.digs) {
                            const auto near=[&](PointQ a) { return std::abs(worker.last_cut.x-a.x)+
                                std::abs(worker.last_cut.y-a.y)+std::abs(worker.last_cut.z-a.z); };
                            if (near(p)<=3*c.reach_q && near(q)<near(p)) weight+=3*weight;
                        }
                        return weight;
                    }),c);
                } else if (floor_search && worker.path_size>1) {
                    choice.returning_empty=true;
                    follow_inbound();
                }
            }
        }
        const auto physical_clock = s.ecological && s.ecological->distance_clock;
        if (action.kind == ScheduledEvent::Kind::Move) {
            const auto duration = physical_clock ?
                with_worker_turn(s,ant.id,ant.position,action.destination,
                    segment_duration(*s.ecological, ant.position, action.destination, carrier != s.carriers.end())) : c.move_duration;
            action.key.time = after(s.m.now, duration.milliseconds);
        } else if (physical_clock && action.kind == ScheduledEvent::Kind::SoilAction && choice.soil.kind == SoilAction::Drop)
            action.key.time = after(s.m.now, s.ecological->soil_handling.milliseconds);
        else if (physical_clock && action.kind==ScheduledEvent::Kind::Rest && worker.path_size==1) {
            // At the depot an empty worker with no feasible frontier may
            // reconsider at the ordinary task boundary.
            choice.stalled=true;
            if (s.social) action.key.time=after(s.m.now,s.social->decision_interval.milliseconds);
        }
        choices.push_back(choice);
    }
    for (std::size_t i = 0; i < choices.size(); ++i) {
        auto choice = choices[i];
        const auto ant = s.ants.get(s.ants.index.at(choice.action.actor));
        if (choice.action.kind==ScheduledEvent::Kind::Move &&
            !clear_worker_traffic(ant,choice.action.destination,body_half(ant.id))) {
            choice.action.kind=ScheduledEvent::Kind::Rest;
            choice.action.destination={};
            choice.action.key.time=after(s.m.now,c.decision_delay.milliseconds);
        }
        auto worker = s.excavators.at(choice.action.actor);
        bump(worker.decisions);
        worker.wake = {};
        worker.returning_empty=choice.returning_empty;
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
        f.random_value=worker.returning_empty ? 1 : 0;
        f.colony = ant.colony;
        f.position = ant.position;
        f.stage = ant.stage;
        tx.fact(f);
        if (choice.stalled && s.autonomy.contains(ant.id) && s.autonomy.at(ant.id).enabled) {
            change_behavior(tx,{s.world,ant.id},IndividualBehavior::Rest,wakes[i].id);
            continue;
        }
        if (s.care_profile) {
            const auto act=choice.action.kind==ScheduledEvent::Kind::Move?CareAct::Walk:choice.action.kind==ScheduledEvent::Kind::Rest?
                CareAct::Inactive:choice.soil.kind==SoilAction::Excavate?CareAct::Excavate:CareAct::HandleSoil;
            observe(tx,ant.id,wakes[i].id,{ObservationPhase::Selected,act,{},worker.action,s.m.now,false,
                s.ecological && s.ecological->distance_clock && act==CareAct::Walk ? choice.action.destination : PositionM{}});
        }
        if (choice.action.kind!=ScheduledEvent::Kind::Rest) set_activity_work(tx,ant.id,worker.action);
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
    if (f.kind == FactKind::SoilExcavated) {
        bump(worker.digs);
        if (nest_scoring(s)>=NestScoring::Reinforcement)
            worker.last_cut=patch_center(s.soil_requests.at(e.id).box);
    }
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
