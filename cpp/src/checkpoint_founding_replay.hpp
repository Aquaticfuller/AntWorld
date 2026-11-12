#pragma once

#include "checkpoint_codec.hpp"
#include "founding_internal.hpp"
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
public:
    std::map<EntityId, FoundingReserve> reserves;

    FoundingReplay(const S& s, const RuntimeLimits& l) : world(s), limits(l), next_edit(s.geometry_edits.begin()) {}
    bool founder(EntityId id) const { return world.founding && id == world.founding->founder; }
    bool enrolled(EntityId id) const { return world.founding && world.founding_reserves.contains(id); }
    const FoundingProfile& profile() const { return world.founding->profile; }

    bool before(const WorldEvent& e) {
        if (!world.founding) return false;
        const bool required = pending != 0;
        if (required) {
            auto wanted = expected.front();
            wanted.id = e.id;
            wanted.world = e.world;
            wanted.revision = e.revision;
            ensure(wanted == e, "missing or misordered F1 physical evidence");
            expected.front() = expected.back();
            --pending;
        }
        if (e.kind == FactKind::FoundingConfigured) {
            ensure(!declared && e.payload == founding_profile_hash(world.founding->founder, profile()), "F1 profile differs from declaration");
            declared = true;
        }
        if (e.kind == FactKind::FoundingReserveSeeded || e.kind == FactKind::FoundingEggFunded || e.kind == FactKind::FoundingLipidConverted)
            ensure(required, "unattributed F1 material fact");
        return required;
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
               e.payload == world.founding->founder.value && !e.random_value && e.transferred == FoodMass{0, f.egg_protein_ug, f.egg_water_ug, 0}),
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
            ensure(funds_founding_egg(f, *mother, maternal), "F1 birth lacks maternal headroom");
            debit_founding_egg(f, *mother, maternal);
            packet.kind = FactKind::FoundingEggFunded;
            packet.actor = {e.payload};
            packet.stage = LifeStage::Adult;
            packet.payload = e.actor.value;
            packet.random_value = f.egg_lipid_ug;
            packet.transferred = {};
            reserves.emplace(e.actor, FoundingReserve{f.egg_lipid_ug});
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
            ensure(e.transferred == absorb(p, stage), "invalid F1 crop uptake");
            convert(p, e.actor, stage, e, false);
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
        ensure(!world.founding || (declared && !pending && reserves.size() == world.founding_reserves.size()),
               "incomplete F1 physiological evidence");
    }
};
} // namespace antworld::detail
