#pragma once
#include "anatomy.hpp"
#include "care_internal.hpp"
#include "checkpoint_codec.hpp"
#include "brood_space.hpp"
#include "ecological_internal.hpp"
#include "surface_internal.hpp"
#include "state.hpp"
#include "nest_scoring.hpp"
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
        if (local_nest_activity(s)) w.put(p.returning_empty,1);
        if (nest_scoring(s)>=NestScoring::Reinforcement && p.digs) write_point(w,p.last_cut);
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
        rebuild_index_edit(s.geometry_edits, s.edit_index, e, c.brick_q, limits.geometry_index_entries);
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
                   (s.config.continuous_spatial_motion || quantized(p.position,c).has_value()) &&
                   s.geometry_edits.contains(p.origin_edit),
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
        if (local_nest_activity(s)) p.returning_empty=r.flag();
        if (nest_scoring(s)>=NestScoring::Reinforcement && p.digs) {
            p.last_cut=read_point(r);
            ensure(contains(c.initial_solid,p.last_cut),"remembered excavation outside the bed");
        }
        ensure(s.ants.index.contains(id) && s.physiology.contains(id) && s.excavators.emplace(id, p).second,
               "invalid excavator identity");
    }
    for (const auto &row : s.ants.identities) {
        const auto ant = s.ants.get(s.ants.index.at(row.id));
        ensure(s.config.continuous_spatial_motion || quantized(ant.position,c).has_value(),"nonquantized geometry actor");
        s.spatial_index.emplace(std::pair{spatial_key(ant.position), row.id.value}, std::uint8_t{1});
    }
    for (const auto &food : s.foods.rows) {
        ensure(s.config.continuous_spatial_motion || quantized(food.position,c).has_value(),"nonquantized geometry food");
        s.spatial_index.emplace(std::pair{spatial_key(food.position), food.id.value}, std::uint8_t{2});
    }
}
template <class S> void validate_geometry_evidence(const S &s, const RuntimeLimits &limits,
                                                  std::set<EventId>& spatial_waits) {
    if (!s.geometry) {
        for (const auto &e : s.journal)
            ensure(e.kind < FactKind::GeometryConfigured || e.kind > FactKind::ExcavationDecision, "geometry fact without authority");
        for (const auto &[key, e] : s.queue) {
            (void)key;
            ensure(e.kind != ScheduledEvent::Kind::SoilAction && e.kind != ScheduledEvent::Kind::ExcavationWake, "geometry event without authority");
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
    std::map<EntityId,std::uint8_t> headings_at_cut;
    std::set<ScheduledId> completed;
    std::set<ResourceId> present_food;
    SoilLedger ledger;
    bool configured = false;
    auto view = [&] { return GeometryView{*s.geometry, edits, index, limits.geometry_partition_cells}; };
    auto half = [&](EntityId id) {
        return carriers.contains(id) || cargo[id].total_ug() ? c.loaded_half_q : c.body_half_q;
    };
    const auto spatial=s.config.continuous_spatial_motion;
    const bool anatomical=anatomical_nest(s);
    const auto contact_half=spatial?0:1;
    std::map<EntityId,EntityId> held_brood;
    auto clear = [&](PositionM a, PositionM b, std::int32_t radius) {
        return spatial?continuous_clear(view(),a,b,radius):
            historical_clear(*s.geometry,edits,index,a,b,radius,limits.geometry_partition_cells);
    };
    const auto embedded=[&](BoxQ box,PositionM p,std::int32_t extent) {
        if (spatial) return intersects_body(box,p,extent,c);
        const auto q=*quantized(p,c);
        return extent?box_valid(intersection(around(q,extent),box)):contains(box,q);
    };
    const auto clear_brood=[&](EntityId mover,PositionM from,PositionM to) {
        return std::none_of(positions.begin(),positions.end(),[&](const auto& row) {
            return row.first!=mover && brood(stages.at(row.first)) && intersects_brood(from,to,row.second);
        });
    };
    const auto past_ant=[&](EntityId id) {
        auto ant=s.ants.get(s.ants.index.at(id));
        ant.stage=stages.at(id);
        ant.position=positions.at(id);
        return ant;
    };
    const auto past_body=[&](EntityId id) {
        const auto ant=past_ant(id);
        const auto heading=headings_at_cut[id];
        return body_pose(ant,heading,attachment(view(),ant,heading));
    };
    const auto emergence_clear=[&](EntityId id) -> std::optional<std::uint8_t> {
        for (const auto& [carrier,target]:held_brood) {
            (void)carrier;
            if (target==id) return {};
        }
        auto actor=past_ant(id);
        actor.stage=LifeStage::Adult;
        return emergence_pose(view(),actor,sustained_supply(s) && s.autonomy.contains(id),[&](const BodyPose& pose) {
            return std::any_of(positions.begin(),positions.end(),[&](const auto& other) {
                return other.first!=id && stages.at(other.first)==LifeStage::Adult &&
                    within_distance(actor.position,other.second,.008,true) && physical_overlap(pose,past_body(other.first));
            });
        });
    };
    std::optional<std::pair<EntityId,PositionM>> expected_egg;
    for (const auto &e : s.journal) {
        if (spatial && e.kind==FactKind::BiologicalObservation) {
            const auto& o=e.observation;
            if (anatomical && o.duration_known &&
                (o.phase==ObservationPhase::Started || o.phase==ObservationPhase::Completed) &&
                handles_brood(o.act) && o.act!=CareAct::TransportBrood && o.act!=CareAct::PlaceBrood) {
                const auto b=past_ant(o.target);
                const auto a=past_body(e.actor);
                ensure(brood(b.stage) && mouth_reaches(a,b.position,b.stage) && clear(a.mouth_m,b.position,0),
                       "brood action lacks a clear mouth contact");
            }
            if (o.act==CareAct::PickUpBrood && o.phase==ObservationPhase::Completed) held_brood[e.actor]=o.target;
            if (o.phase==ObservationPhase::Interrupted || (o.act==CareAct::PlaceBrood && o.phase==ObservationPhase::Completed))
                held_brood.erase(e.actor);
        }
        if (spatial && e.kind==FactKind::CareProgramChanged && !e.payload) held_brood.erase(e.actor);
        if (e.kind == FactKind::GeometryConfigured) {
            ensure(!configured && positions.empty() && e.time == SimTime{} && !e.actor.value,
                   "invalid geometry configuration history");
            configured = true;
            ledger.initial_q3 = material_volume(view(), c.initial_solid, Material::Soil);
            ledger.remaining_q3 = ledger.initial_q3;
        }
        const bool ant_origin=e.kind==FactKind::AntSeeded || e.kind==FactKind::AntBorn;
        if (anatomical && ant_origin) {
            auto ant=s.ants.get(s.ants.index.at(e.actor));
            ant.stage=e.stage;
            ant.position=e.position;
            ensure(configured && substrate_clear(view(),body_pose(ant,0,attachment(view(),ant,0)),e.position),
                   "anatomical birth or seed embedded in material");
        } else if (ant_origin || e.kind==FactKind::FoodSeeded || e.kind==FactKind::FoodPlaced || e.kind==FactKind::ColonySeeded) {
            ensure(configured && clear(e.position,e.position,ant_origin?c.body_half_q:contact_half),"seed embedded in material");
        }
        if (bounded_brood_space(s)) {
            if (expected_egg) {
                ensure(e.kind==FactKind::AntBorn && expected_egg->first==e.actor && expected_egg->second==e.position,
                       "MicroWorld birth disagrees with available placement");
                expected_egg.reset();
            } else if (e.kind==FactKind::ReproductionAttempt && (e.payload || e.outcome==Outcome::Capacity)) {
                ensure(positions.contains(e.actor) && positions.at(e.actor)==e.position,"invalid MicroWorld maternal origin");
                const auto site=anatomical?
                    posterior_egg_site(view(),past_body(e.actor),s.config,[&](PositionM b) {
                        return clear_brood({},b,b);
                    }):pick_egg_site(e.position,s.config,
                    [&](PositionM a,PositionM b) {
                        const auto below=below_brood(b,c,sealed_chamber(s));
                        return inside(b,s.config) && (!s.surface || surface_allows(*s.surface,true,a,b)) &&
                            clear(a,b,brood_half(c)) && !clear(below,below,0);
                    },
                    [&](PositionM b) { return clear_brood({},b,b); },
                    [&](PositionM b) {
                        return static_cast<std::size_t>(std::count_if(positions.begin(),positions.end(),[&](const auto& row) {
                            return brood(stages.at(row.first)) && within_distance(b,row.second,brood_adjacency_m,true) &&
                                s.ants.get(s.ants.index.at(row.first)).colony==e.colony &&
                                (!s.surface || surface_allows(*s.surface,true,b,row.second)) && clear(b,row.second,0);
                        }));
                    },sealed_chamber(s) ? std::optional{s.ecological->founding_habitat->brood_site} : std::nullopt);
                ensure(site.has_value()==(e.payload!=0),"MicroWorld no-space outcome contradicts the local clutch");
                if (site) expected_egg=std::pair{EntityId{e.payload},*site};
            } else if (e.kind==FactKind::AntBorn) ensure(false,"MicroWorld egg lacks a preceding spatial attempt");
            if (e.kind==FactKind::AntSeeded && brood(e.stage))
                ensure(clear_brood(e.actor,e.position,e.position),"overlapping seeded MicroWorld brood");
        }
        if (e.kind == FactKind::AntSeeded || e.kind==FactKind::AntBorn) {
            positions[e.actor] = e.position;
            stages[e.actor] = e.stage;
        }
        if (e.kind == FactKind::FoodSeeded || e.kind == FactKind::FoodPlaced) present_food.insert(e.resource);
        if (e.kind == FactKind::Moved || e.kind==FactKind::BroodMoved) {
            const auto carrier=e.kind==FactKind::BroodMoved?EntityId{e.payload}:e.actor;
            const auto held=held_brood.find(carrier);
            const bool loaded_care=held!=held_brood.end() && (carrier==e.actor || held->second==e.actor);
            const auto from=positions.at(e.actor);
            ensure(clear(from,e.position,anatomical && e.kind==FactKind::BroodMoved?0:loaded_care?c.loaded_half_q:half(e.actor)),
                   "historical movement crosses solid material");
            if (anatomical && e.kind==FactKind::Moved && stages.at(e.actor)==LifeStage::Adult) {
                const auto heading=historical_heading(e.random_value,from,e.position);
                ensure(heading && heading<=facing_down &&
                    (heading==(held_brood.contains(e.actor)?std::max<std::uint8_t>(1,headings_at_cut[e.actor]):
                    body_travel_heading(view(),past_ant(e.actor),e.position,std::max<std::uint8_t>(1,headings_at_cut[e.actor])))) &&
                    anatomy_sweep(view(),past_ant(e.actor),e.position,headings_at_cut[e.actor],heading),
                    "historical body crosses solid material");
                headings_at_cut[e.actor]=heading;
            }
            if (anatomical && e.kind==FactKind::BroodMoved)
                ensure(continuous_box_clear(view(),from,e.position,brood_half_axes(stages.at(e.actor))),
                       "historical brood carrying crosses solid material");
            if (bounded_brood_space(s) && e.kind==FactKind::BroodMoved)
                ensure(clear_brood(e.actor,positions.at(e.actor),e.position),"MicroWorld brood movement intersects live brood");
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
            ensure(clear(positions.at(e.actor),food.position,contact_half) &&
                       clear(positions.at(e.actor), positions.at(e.actor), c.loaded_half_q),
                   "food crosses solid material");
            cargo[e.actor] = sum(cargo[e.actor], e.transferred);
        }
        if (e.kind == FactKind::FoodDelivered || (!mouth_access(s) && e.kind==FactKind::NestIngested) || e.kind==FactKind::ProteinRecycled)
            ensure(clear(positions.at(e.actor),s.colonies.rows[s.colonies.index.at(e.colony)].nest_position,contact_half),
                   "nest inventory crosses solid material");
        if (mouth_access(s) && e.kind==FactKind::FoundingConfigured) {
            const auto founder=past_ant(s.founding->founder);
            const auto depot=s.colonies.rows[s.colonies.index.at(founder.colony)].nest_position;
            ensure(within_contact(founder.position,depot,s.config) && clear(founder.position,depot,0),
                   "founder lacks local experience of the handoff site");
        }
        const bool wall_delivery=e.kind==FactKind::FoodDelivered && wall_handoff(s) && e.payload==wall_delivery_payload;
        if (sustained_supply(s) && (e.kind==FactKind::WorkerWaterIngested || e.kind==FactKind::FoundressWaterIngested)) {
            const auto target=s.foods.rows[s.foods.index.at(e.resource)].position;
            const auto body=past_body(e.actor);
            const auto edge=feeding_patch_point(body.mouth_m,target);
            const auto contact=clear(target,edge,0)?edge:target;
            ensure(supply_in_reach(body,contact) && clear(body.mouth_m,contact,0),"wick draw lacks historical mouth contact");
        }
        if (mouth_access(s) && (e.kind==FactKind::FoundressNestMeal || e.kind==FactKind::NestIngested || wall_delivery)) {
            const auto body=past_body(e.actor);
            const auto depot=s.colonies.rows[s.colonies.index.at(e.colony)].nest_position;
            auto contact_site=depot;
            if (variable_conditions(s) && (!wall_delivery || sustained_supply(s))) {
                const auto edge=feeding_patch_point(body.mouth_m,depot);
                if (clear(depot,edge,0)) contact_site=edge;
            }
            ensure(supply_in_reach(body,contact_site) && clear(body.mouth_m,contact_site,0),
                   "depot exchange lacks historical mouth contact");
            if (wall_delivery) ensure(body.center_m.y!=depot.y && positions.at(e.actor)==e.position,
                                      "wall delivery has no historical off-floor berth");
        }
        if (e.kind == FactKind::FoodDelivered || e.kind == FactKind::CargoIngested)
            cargo[e.actor] = subtract(cargo[e.actor], e.transferred);
        if (e.kind == FactKind::NutritionTransferred) {
            const EntityId recipient{e.payload};
            if (adult_offers(s) && stages.at(recipient)==LifeStage::Adult) {
                const auto donor=past_body(e.actor), receiver=past_body(recipient);
                ensure(mouths_meet(donor,receiver) &&
                       clear(donor.mouth_m,receiver.mouth_m,0),"adult food transfer lacks mutual mouth contact");
            } else ensure(clear(positions.at(e.actor),positions.at(recipient),contact_half),
                          "trophallaxis crosses solid material");
        }
        if (anatomical && (e.kind==FactKind::FoundingRation || (e.kind==FactKind::NutritionTransferred &&
            stages.at(EntityId{e.payload})==LifeStage::Larva))) {
            const auto b=past_ant({e.payload});
            const auto a=past_body(e.actor);
            ensure(brood(b.stage) && mouth_reaches(a,b.position,b.stage) && clear(a.mouth_m,b.position,0),
                   "larval ration lacks mouth contact");
        }
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
            } else if (excavators.contains(e.actor)) {
                excavators.at(e.actor).enabled = false;
                excavators.at(e.actor).returning_empty=false;
            }
        }
        if (e.kind == FactKind::ExcavationDecision) {
            ensure(excavators.contains(e.actor) && excavators.at(e.actor).enabled,
                   "decision without active excavation program");
            ensure(e.payload == ++excavators.at(e.actor).decisions, "excavation decision evidence mismatch");
            if (local_nest_activity(s)) excavators.at(e.actor).returning_empty=e.random_value!=0;
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
            if (e.kind == FactKind::SoilExcavated || e.kind == FactKind::SoilFilled) {
                const auto q=quantized(e.position,c);
                const auto action = e.kind == FactKind::SoilExcavated ? SoilAction::Excavate : SoilAction::Fill;
                ensure(q && request.kind==action && local_patch(view(),*q,request.box) &&
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
                    if (excavators.contains(e.actor) && excavators.at(e.actor).enabled) {
                        auto& worker=excavators.at(e.actor);
                        ++worker.digs;
                        if (nest_scoring(s)>=NestScoring::Reinforcement) worker.last_cut=patch_center(request.box);
                    }
                } else {
                    ensure(carriers.contains(e.actor) && carriers.at(e.actor) == request.parcel,
                           "fill lacks physical soil carrier");
                    for (const auto &[id, p] : positions)
                        ensure(!embedded(request.box,p,half(id)),
                               "fill embeds an individual");
                    for (auto id : present_food)
                        ensure(!embedded(request.box,s.foods.rows[s.foods.index.at(id)].position,0),"fill embeds food");
                    for (const auto &colony : s.colonies.rows)
                        ensure(!embedded(request.box,colony.nest_position,0),"fill embeds nest anchor");
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
                rebuild_index_edit(edits, index, edit, c.brick_q, limits.geometry_index_entries);
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
                               within_contact(e.position,parcel.position,s.config) &&
                               clear(e.position,parcel.position,contact_half) && clear(e.position,e.position,c.loaded_half_q),
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
        if (e.kind == FactKind::AntDied && excavators.contains(e.actor)) {
            excavators.at(e.actor).enabled = false;
            excavators.at(e.actor).returning_empty=false;
        }
        if (anatomical && e.kind==FactKind::PhysiologyUpdated && e.stage==LifeStage::Pupa && !emergence_clear(e.actor))
            spatial_waits.insert(e.id);
        if (anatomical && e.kind==FactKind::StageChanged && e.stage==LifeStage::Adult) {
            const auto facing=emergence_clear(e.actor);
            ensure(facing && e.random_value==*facing,"adult emergence lacks physical space for its recorded pose");
            if (e.random_value) headings_at_cut[e.actor]=*facing;
        }
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
    ensure(!expected_egg && configured && edits == s.geometry_edits && parcels == s.parcels && carriers == s.carriers &&
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
