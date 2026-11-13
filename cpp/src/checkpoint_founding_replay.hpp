#pragma once

#include "checkpoint_codec.hpp"
#include "founding_internal.hpp"
#include "founding_memory.hpp"
#include "spatial_navigation.hpp"
#include "care_internal.hpp"

namespace antworld::detail {
// Replay the versioned physical ledger from the committed inputs and acts.
// Saved rows provide an identity index, never the balances used for decisions.
template<class S> class FoundingReplay {
    const S& world;
    const RuntimeLimits& limits;
    std::array<WorldEvent, 2> expected{};
    std::size_t pending{};
    GeometryEdits edits;
    EditIndex index;
    GeometryEdits::const_iterator next_edit;
    bool declared{};
    FoundingMealMemory memory;
    ScheduledId repeated_wake;
    bool repeated_contact{};
    std::optional<WorldEvent> last_hatch, hatch_cue;
    std::optional<WorldEvent> last_pulse;
    SimTime last_cue;
    EntityId cue_target;
    ScheduledId cue_wake;
    std::optional<WorldEvent> opened_care;
    bool cue_contact{}, founder_autonomous{}, founder_caring{};
    std::map<EntityId, std::uint64_t> dietary_eggs;

    void expect(WorldEvent e) {
        ensure(pending < expected.size(), "too many F1 facts in one physiological boundary");
        expected[pending++] = e;
    }
    void convert(PhysiologyState& p, EntityId id, LifeStage stage, const WorldEvent& source, bool initial) {
        const auto amount = convert_founding_lipid(profile(), p, reserves.at(id), stage, founder(id));
        if (initial) p.initial.body_energy_nj = p.body_energy_nj;
        if (!amount) return;
        auto ant = world.ants.get(world.ants.index.at(id));
        ant.stage = stage;
        ant.position = source.position;
        auto conversion = lipid_conversion(profile(), ant, source.source, amount);
        conversion.time = source.time;
        expect(conversion);
    }
    void review_care(const WorldEvent& e) {
        const auto founder_id = world.founding->founder;
        const auto& repeat = profile().feeding_persistence;
        if (repeated_wake.value) {
            ensure(e.kind == FactKind::BiologicalObservation && e.source == repeated_wake && e.actor == founder_id,
                   "F1-R1 repeat lacks its local care observations");
            const auto& o = e.observation;
            if (o.phase == ObservationPhase::Opportunity) repeated_contact |= o.target == memory.target;
            else {
                ensure(repeated_contact && o.phase == ObservationPhase::Selected && o.act == CareAct::FeedBrood &&
                       o.target == memory.target && o.bout.value, "F1-R1 repeat lacks its witnessed feeding selection");
                repeated_wake = {};
                repeated_contact = false;
            }
        }
        if (e.kind == FactKind::CareTick && e.random_value) {
            ensure(repeat && repeat->repeat_ppm && e.actor == founder_id && memory.target.value && e.time > memory.fed_at,
                   "F1-R1 annotation lacks a preceding ration");
            const auto status = static_cast<FoundingCareWake>(e.random_value);
            const bool expired = e.time.milliseconds - memory.fed_at.milliseconds >= repeat->window.milliseconds;
            ensure(expired == (status == FoundingCareWake::Expired), "F1-R1 memory age contradicts the care annotation");
            if (status == FoundingCareWake::Repeat) repeated_wake = e.source;
        }
        if (repeat && repeat->repeat_ppm) update_founding_meal_memory(memory, founder_id, e);
    }
    void review_hatch(const WorldEvent& e) {
        if (e.kind==FactKind::StageChanged && e.stage==LifeStage::Larva) last_hatch=e;
        if (cue_wake.value) {
            const bool released=e.kind==FactKind::CareProgramChanged && !e.payload && !e.source.value;
            ensure(founder(e.actor) && e.time==after(last_cue,1) &&
                   ((e.kind==FactKind::BiologicalObservation && e.source==cue_wake) || released),
                   "R2 hatch wake has no bounded care decision");
            if (e.kind==FactKind::BiologicalObservation && e.observation.phase==ObservationPhase::Opportunity)
                cue_contact |= e.observation.target==cue_target;
            else {
                ensure(released || (cue_contact && e.observation.phase==ObservationPhase::Selected &&
                       e.observation.target==cue_target && e.observation.bout.value), "R2 hatch cue selected an unwitnessed larva");
                cue_wake={}; cue_target={}; cue_contact=false;
            }
        }
        if (e.kind==FactKind::FoundingHatchCue) {
            ensure(profile().early_access->local_hatch_cue && !hatch_cue && last_hatch && opened_care && founder_autonomous &&
                   founder(e.actor) && enrolled({e.payload}) && last_hatch->actor==EntityId{e.payload} &&
                   last_hatch->source==e.source && last_hatch->time==e.time && last_hatch->colony==e.colony &&
                   opened_care->source.value==0 && opened_care->id.value+1==e.id.value && opened_care->position==e.position &&
                   world.colonies.rows[world.colonies.index.at(e.colony)].nest_position==e.position &&
                   e.random_value<world.m.next_scheduled &&
                   (last_cue==SimTime{} || e.time.milliseconds-last_cue.milliseconds>=founding_hatch_cooldown_ms) &&
                   within_contact(e.position,last_hatch->position,world.config) &&
                   within_distance(e.position,last_hatch->position,world.care_profile->perception_radius_m,
                                   world.config.continuous_spatial_motion) &&
                   surface_care_clear(world,e.position,last_hatch->position) && clear(e.position,last_hatch->position,0,e.id),
                   "R2 hatch cue lacks a bounded local hatch");
            last_cue=e.time;
            hatch_cue=e;
        } else if (hatch_cue && founder(e.actor)) {
            if (e.kind==FactKind::CareTick && e.payload==static_cast<std::uint64_t>(ScheduledEvent::Kind::CareWake)) {
                ensure(e.source.value==hatch_cue->random_value && e.time==after(last_cue,1), "R2 hatch cue lost its first care wake");
                cue_wake=e.source; cue_target={hatch_cue->payload};
                hatch_cue.reset();
            } else if ((e.kind==FactKind::CareProgramChanged && !e.payload) || e.kind==FactKind::AntDied) hatch_cue.reset();
        }
        if (founder(e.actor)) {
            if (e.kind==FactKind::AutonomyChanged) founder_autonomous=e.payload!=0;
            if (e.kind==FactKind::AntDied) founder_autonomous=false;
            if (e.kind==FactKind::CareProgramChanged) {
                if (e.payload && !founder_caring) opened_care=e;
                founder_caring=e.payload!=0;
            }
        }
    }
public:
    std::map<EntityId, FoundingReserve> reserves;

    FoundingReplay(const S& s, const RuntimeLimits& l) : world(s), limits(l), next_edit(s.geometry_edits.begin()) {}
    bool founder(EntityId id) const { return world.founding && id == world.founding->founder; }
    bool enrolled(EntityId id) const { return world.founding && world.founding_reserves.contains(id); }
    const FoundingProfile& profile() const { return world.founding->profile; }
    std::uint64_t dietary_energy(EntityId id) const {
        const auto it=dietary_eggs.find(id);
        return it==dietary_eggs.end()?0:it->second;
    }

    bool before(const WorldEvent& e) {
        if (!world.founding) return false;
        // A stage transition can first interrupt the existing care bout for that brood.
        const bool interrupted_brood = pending && profile().early_access && expected.front().kind==FactKind::StageChanged &&
            e.kind==FactKind::BiologicalObservation && e.time==expected.front().time &&
            e.observation.phase==ObservationPhase::Interrupted && e.outcome==Outcome::InvalidStage &&
            e.observation.target==expected.front().actor;
        const bool required = pending != 0 && !interrupted_brood;
        if (required) {
            auto wanted = expected.front();
            wanted.id = e.id;
            wanted.world = e.world;
            wanted.revision = e.revision;
            if (wanted != e) throw std::runtime_error("missing or misordered F1 physical evidence at event " +
                std::to_string(e.id.value) + ": expected kind " + std::to_string(static_cast<unsigned>(wanted.kind)) +
                ", found kind " + std::to_string(static_cast<unsigned>(e.kind)));
            expected.front() = expected.back();
            --pending;
        }
        if (e.kind == FactKind::FoundingConfigured) {
            ensure(!declared && e.random_value == profile().model_version() &&
                   e.payload == founding_profile_hash(world.founding->founder, profile()), "F1 profile differs from declaration");
            declared = true;
        }
        if (profile().feeding_persistence) review_care(e);
        if (e.kind==FactKind::FoundingHatchCue)
            ensure(profile().early_access && profile().early_access->local_hatch_cue, "R2 hatch cue is disabled");
        if (profile().early_access && profile().early_access->local_hatch_cue) review_hatch(e);
        if (e.kind == FactKind::FoundingReserveSeeded || e.kind == FactKind::FoundingEggFunded ||
            e.kind == FactKind::FoundingDietaryEggFunded || e.kind == FactKind::FoundingLipidConverted)
            ensure(required, "unattributed F1 material fact");
        return required;
    }

    void mobilize(PhysiologyState& p, const WorldEvent& e, LifeStage stage) {
        const auto amount=mobilize_founding_larval_lipid(profile(),p,reserves.at(e.actor),stage);
        ensure(amount && e.payload==amount && e.random_value==multiply(amount,profile().lipid_yield_nj_per_ug),
               "unfunded or misplaced R2 lipid mobilization");
    }

    void settle(EntityId id, PhysiologyState& p, LifeStage stage, SimTime time) {
        if (enrolled(id)) settle_founding(profile(), p, reserves.at(id), stage, founder(id), time);
        else detail::settle(p, stage, time);
    }

    SimTime next(EntityId id, const PhysiologyState& p, LifeStage stage, const FoundingReserve* row = nullptr) const {
        return enrolled(id) ? next_founding_physiology(profile(), p, row ? *row : reserves.at(id), stage, founder(id))
                            : next_physiology(p, stage);
    }

    bool clear(PositionM a, PositionM b, std::int32_t half, EventId fact) {
        while (next_edit != world.geometry_edits.end() && next_edit->second.event < fact) {
            const auto& edit = next_edit->second;
            edits.emplace(edit.id, edit);
            rebuild_index_edit(edits, index, edit, world.geometry->config.brick_q, limits.geometry_index_entries);
            ++next_edit;
        }
        if (world.config.continuous_spatial_motion) {
            if (!inside(a, world.config) || !inside(b, world.config) ||
                (world.surface && !surface_allows(*world.surface, world.geometry != nullptr, a, b))) return false;
            return !world.geometry || continuous_clear({*world.geometry, edits, index, limits.geometry_partition_cells}, a, b, half);
        }
        return !world.geometry || historical_clear(*world.geometry, edits, index, a, b, half, limits.geometry_partition_cells);
    }

    void initialize(PhysiologyState& p, const WorldEvent& e, PhysiologyState* mother) {
        const bool is_founder = founder(e.actor);
        const auto& f = profile();
        ensure(declared && !reserves.contains(e.actor) && (is_founder ? !mother && e.kind == FactKind::PhysiologyEnabled &&
               e.time == SimTime{} && e.stage == LifeStage::Adult && e.transferred == FoodMass{} : mother && e.kind == FactKind::AntBorn &&
               e.payload == world.founding->founder.value && e.transferred == FoodMass{0, f.egg_protein_ug, f.egg_water_ug, 0}),
               "invalid F1 physiology origin");
        p = initial_founding_physiology(f, is_founder, e.time, is_founder ? EntityId{} : EntityId{e.payload});
        WorldEvent packet = e;
        packet.id = {};
        packet.world = {};
        packet.revision = 0;
        if (is_founder) {
            packet.kind = FactKind::FoundingReserveSeeded;
            packet.payload = f.lipid_ug;
            packet.transferred = {0, f.protein_ug, f.water_ug, 0};
            reserves.emplace(e.actor, FoundingReserve{f.lipid_ug, 0, f.protein_ug});
        } else {
            auto& maternal = reserves.at({e.payload});
            const auto fuel=founding_egg_fuel(f,*mother,maternal);
            const bool body=fuel==FoundingEggFuel::Body;
            const auto energy=multiply(f.egg_lipid_ug,f.lipid_yield_nj_per_ug);
            ensure(fuel!=FoundingEggFuel::None && e.random_value==(body?energy:0), "F1 birth lacks maternal headroom");
            const auto protein=body?debit_dietary_egg(f,*mother,maternal):0;
            if (!body) debit_founding_egg(f,*mother,maternal);
            packet.kind = body ? FactKind::FoundingDietaryEggFunded : FactKind::FoundingEggFunded;
            packet.actor = {e.payload};
            packet.stage = LifeStage::Adult;
            packet.payload = e.actor.value;
            packet.random_value = body ? energy : f.egg_lipid_ug;
            packet.transferred = {0,protein,0,0};
            reserves.emplace(e.actor, FoundingReserve{body?0:f.egg_lipid_ug});
            if (body) {
                p.initial.body_energy_nj=p.body_energy_nj=energy;
                dietary_eggs.emplace(e.actor,energy);
                expect(packet);
                return;
            }
        }
        expect(packet);
        convert(p, e.actor, e.stage, e, true);
    }

    bool funded(const PhysiologyState& p, const WorldEvent& e) {
        return funds_founding_egg(profile(), p, reserves.at(e.actor)) &&
               clear(e.position, e.position, world.geometry ? world.geometry->config.body_half_q : 0, e.id);
    }

    void pulse(PhysiologyState& p, const WorldEvent& e, LifeStage stage) {
        ensure(p.body_energy_nj && p.hydration_ug, "F1 uptake after exhaustion");
        if (e.time == p.next_absorption) {
            ensure(e.transferred == founding_pulse(profile(),p,reserves.at(e.actor),stage), "invalid F1 crop uptake");
            convert(p, e.actor, stage, e, false);
            if (founder(e.actor) && profile().dietary && profile().dietary->local_nest_intake) last_pulse=e;
            if (founding_develops(profile(), p, reserves.at(e.actor), stage)) {
                auto transition = e;
                transition.kind = FactKind::StageChanged;
                transition.stage = static_cast<LifeStage>(static_cast<unsigned>(stage)+1);
                transition.transferred = {};
                expect(transition);
            }
        } else ensure(stage == LifeStage::Larva && p.stage_progress == p.config.larva_duration && e.transferred == FoodMass{} &&
                      !founding_develops(profile(), p, reserves.at(e.actor), stage), "unexpected F1 developmental wait");
    }

    void nest_meal(PhysiologyState& p, const WorldEvent& e, FoodMass stock) {
        ensure(founder(e.actor) && profile().dietary && profile().dietary->local_nest_intake &&
               last_pulse && last_pulse->source==e.source && last_pulse->time==e.time,
               "foundress meal lacks its physiological pulse");
        const auto nest=world.colonies.rows[world.colonies.index.at(e.colony)].nest_position;
        ensure(within_contact(e.position,nest,world.config) && clear(e.position,nest,0,e.id) &&
               foundress_nest_meal(profile(),p,reserves.at(e.actor),stock)==e.transferred,
               "foundress meal lacks reachable local stock or crop room");
        p.crop=sum(p.crop,e.transferred);
        last_pulse.reset();
    }

    void ration(PhysiologyState& p, PhysiologyState& receiver, const WorldEvent& e, PositionM b, LifeStage stage) {
        ensure(founder(e.actor) && enrolled({e.payload}) && receiver.mother == e.actor && stage == LifeStage::Larva &&
               world.social->exchange_enabled && within_contact(e.position, b, world.config) &&
               surface_care_clear(world, e.position, b) && clear(e.position, b, 0, e.id), "F1 ration lacks a living local recipient");
        auto& donor = reserves.at(e.actor);
        auto& larva = reserves.at({e.payload});
        const auto amount = founding_ration(profile(), p, donor, receiver, larva);
        ensure(amount == FoundingRation{e.random_value, e.transferred}, "F1 ration exceeds real local stock or demand");
        apply_founding_ration(amount, p, donor, receiver, larva);
    }

    void finish() const {
        ensure(!world.founding || (declared && !pending && !repeated_wake.value && !cue_wake.value && memory == world.m.founding_meal &&
               reserves.size() == world.founding_reserves.size() && last_cue==world.m.last_founding_hatch_cue),
               "incomplete F1 physiological evidence");
        if (world.founding && world.founding->profile.early_access) {
            unsigned pending_cues=0;
            for (const auto& [key,e] : world.queue) {
                if (e.kind!=ScheduledEvent::Kind::CareWake || !e.payload) continue;
                ++pending_cues;
                ensure(hatch_cue && founder(e.actor) && e.id.value==hatch_cue->random_value && e.payload==hatch_cue->payload &&
                       e.issued_at==last_cue && key.time==after(last_cue,1) && key.phase==Phase::Perception,
                       "pending R2 cue has no local hatch witness");
            }
            ensure(pending_cues==static_cast<unsigned>(hatch_cue.has_value()), "R2 pending hatch cue count disagrees with history");
        }
    }
};
} // namespace antworld::detail
