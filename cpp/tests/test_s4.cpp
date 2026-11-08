#include "s4_fixture.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <string_view>

using namespace antworld;
using namespace antworld::s4_fixture;
namespace {
template <class F> void rejects(F action) {
    bool failed = false;
    try {
        action();
    } catch (const std::exception &) {
        failed = true;
    }
    require(failed, "invalid operation succeeded");
}
void initial() {
    Fixture f;
    auto &w = f.world;
    require(w.geometry_snapshot().ledger.initial_q3 == 13632, "initial exact volume incorrect");
    require(w.query_material(position({14, 12, 12}, f.geometry)) == Material::Soil &&
                w.query_material(position({13, 12, 12}, f.geometry)) == Material::Void,
            "half-open material boundary incorrect");
    const auto before = w.checkpoint();
    rejects([&] { w.seed_ant(f.colony, {position({14, 12, 12}, f.geometry)}); });
    rejects([&] { (void)w.query_material_volume({{INT32_MIN, 0, 0}, {INT32_MAX, 1, 1}}, Material::Soil); });
    rejects([&] { w.configure_geometry(f.geometry, {}); });
    require(w.checkpoint() == before, "invalid geometry mutation was not atomic");
    WorldRuntime invalid({4, 2}, 1);
    auto c = f.geometry;
    c.quantum_m = 0;
    rejects([&] { invalid.configure_geometry(c, {}); });
    c = f.geometry;
    c.dry_ug_per_q3 = UINT64_MAX;
    rejects([&] { invalid.configure_geometry(c, {}); });
    balanced(w);
    roundtrip(w);
}
void material() {
    Fixture f;
    auto &w = f.world;
    f.dig();
    w.advance_to({100});
    require(w.geometry_edits().size() == 1 && w.geometry_snapshot().ledger.carried_q3 == 16,
            "first dig removed wrong volume");
    const auto parcel = w.soil_parcels().front();
    const SoilParcelRef ref{w.summary().world, parcel.id};
    f.dig({200});
    w.advance_to({200});
    require(w.geometry_edits().size() == 1 && w.committed_events().back().outcome == Outcome::Depleted,
            "repeated dig created material");
    w.submit_soil({f.worker, {300}, SoilAction::Drop, {}, ref, 1});
    w.advance_to({300});
    require(w.query_parcel(ref)->state == ParcelState::Deposited && w.geometry_snapshot().ledger.deposited_q3 == 16,
            "drop lost parcel");
    w.submit_soil({f.worker, {400}, SoilAction::Pickup, {}, ref, 1});
    w.advance_to({400});
    w.submit_soil({f.worker, {500}, SoilAction::Fill, patch, ref, 1});
    w.advance_to({500});
    require(w.geometry_snapshot().ledger.remaining_q3 == 13632 && w.query_parcel(ref)->state == ParcelState::Exhausted,
            "fill did not consume real soil");
    require(w.query_material(position({14, 12, 12}, f.geometry)) == Material::Soil, "fill did not restore material");
    f.dig({600});
    w.advance_to({600});
    require(w.soil_parcels().back().id != parcel.id, "parcel ID reused");
    balanced(w);
    roundtrip(w);
}
void overlap() {
    unsigned first = 0;
    for (std::uint64_t seed = 1; seed <= 32; ++seed) {
        Fixture a(seed), b(seed);
        const auto other_a =
            a.world.seed_ant(a.colony, {position({12, 12, 12}, a.geometry), LifeStage::Adult, Caste::Worker, 20000});
        const auto other_b =
            b.world.seed_ant(b.colony, {position({12, 12, 12}, b.geometry), LifeStage::Adult, Caste::Worker, 20000});
        const BoxQ second{{14, 12, 10}, {15, 16, 14}};
        a.dig();
        a.world.submit_soil({other_a, {100}, SoilAction::Excavate, second, {}, 0});
        b.world.submit_soil({other_b, {100}, SoilAction::Excavate, second, {}, 0});
        b.dig();
        a.world.advance_to({100});
        b.world.advance_to({100});
        require(a.world.geometry_snapshot().ledger.excavated_q3 == 24, "overlap counted twice");
        const auto ea = a.world.geometry_edits(), eb = b.world.geometry_edits();
        require(ea.size() == 2 && ea[0].actor == eb[0].actor && ea[0].volume_q3 == 16 && ea[1].volume_q3 == 8,
                "submission order controls soil arbitration");
        if (ea[0].actor == a.worker.id)
            ++first;
        balanced(a.world);
        roundtrip(a.world);
    }
    require(first > 6 && first < 26, "soil arbitration has persistent actor privilege");
}
void constraints() {
    Fixture f;
    auto &w = f.world;
    w.submit_soil({f.worker, {1}, SoilAction::Excavate, patch, {}, 0});
    w.advance_to({1});
    require(w.committed_events().back().outcome == Outcome::TooFast, "work duration ignored");
    f.dig({101}, {{20, 10, 10}, {21, 14, 14}});
    w.advance_to({101});
    require(w.committed_events().back().outcome == Outcome::OutOfReach, "remote excavation accepted");
    f.dig({201}, {{13, 10, 10}, {14, 14, 14}});
    w.advance_to({201});
    require(w.geometry_edits().empty(), "empty cavity yields soil");
    WorldRuntime rock({4, 4}, 1);
    const auto cfg = config();
    const BoxQ hard = patch;
    rock.configure_geometry(cfg, std::span{&room, 1}, std::span{&hard, 1});
    const auto c = rock.seed_colony(position({12, 12, 12}, cfg));
    const auto a = rock.seed_ant(c, {position({12, 12, 12}, cfg)});
    rock.submit_soil({a, {100}, SoilAction::Excavate, patch, {}, 0});
    rock.advance_to({100});
    require(rock.committed_events().back().outcome == Outcome::NonDiggable, "rock excavated as soil");
    Fixture energy(1, {}, {12, 12, 12}, true);
    energy.dig();
    energy.world.advance_to({100});
    const auto p = *energy.world.query_physiology(energy.worker);
    require(p.dissipated_energy_nj == 116000, "dig energy expenditure missing");
    balanced(energy.world);
    roundtrip(energy.world);
    Fixture capacity;
    const auto weak = capacity.world.seed_ant(
        capacity.colony, {position({12, 12, 12}, capacity.geometry), LifeStage::Adult, Caste::Worker, 1999});
    capacity.world.submit_soil({weak, {100}, SoilAction::Excavate, patch, {}, 0});
    capacity.world.advance_to({100});
    require(capacity.world.committed_events().back().outcome == Outcome::Capacity &&
                capacity.world.geometry_edits().empty(),
            "dig exceeded combined carrying capacity");
    Fixture tired;
    tired.world.enable_physiology(tired.worker, {{}, 110000, 1000, 0});
    tired.dig();
    tired.world.advance_to({100});
    require(tired.world.committed_events().back().outcome == Outcome::InsufficientEnergy &&
                tired.world.geometry_edits().empty(),
            "dig created work energy");
    roundtrip(tired.world);
}
void sdf() {
    WorldRuntime w({4, 1}, 1);
    auto c = config();
    const std::array<BoxQ, 2> cavities{{{{8, 8, 8}, {12, 18, 18}}, {{8, 8, 8}, {18, 12, 18}}}};
    w.configure_geometry(c, cavities);
    const auto corner = w.query_signed_distance(position({14, 14, 14}, c));
    require(std::abs(corner + 2 * c.quantum_m) < 1e-12, "union sign/distance incorrect");
    require(std::abs(w.query_signed_distance(position({11, 11, 14}, c)) - std::sqrt(2.0) * c.quantum_m) < 1e-12,
            "overlapping voids use raw CSG distance instead of true boundary distance");
    const auto before = w.checkpoint();
    const std::array<PointQ, 2> keys{{{0, 1, 1}, {1, 1, 1}}};
    w.rebuild_geometry_cache(keys);
    const auto left = *w.query_sdf_brick(keys[0]), right = *w.query_sdf_brick(keys[1]);
    for (std::size_t y = 0; y < 5; ++y)
        for (std::size_t z = 0; z < 5; ++z)
            require(left.distance_m[100 + y * 5 + z] == right.distance_m[y * 5 + z], "SDF cache seam differs");
    require(w.checkpoint() == before, "derived cache changes saved authority");
    w.discard_geometry_cache();
    require(w.checkpoint() == before, "cache eviction changes authority");
    Fixture f;
    const std::array<PointQ, 2> edit_keys{{{1, 1, 1}, {2, 1, 1}}};
    f.world.rebuild_geometry_cache(edit_keys);
    f.dig();
    f.world.advance_to({100});
    require(!f.world.query_sdf_brick(edit_keys[0]) && !f.world.query_sdf_brick(edit_keys[1]) &&
                f.world.dirty_geometry_bricks().size() == 2,
            "edit halo did not dirty both cache seams");
    f.world.rebuild_geometry_cache(edit_keys);
    require(f.world.query_sdf_brick(edit_keys[1])->source_revision == 1, "cache published wrong version");
    roundtrip(f.world);
}
void navigation() {
    WorldRuntime w({4, 1}, 1);
    auto c = config();
    const std::array<BoxQ, 2> corridors{{{{2, 4, 8}, {28, 8, 12}}, {{12, 12, 2}, {16, 16, 22}}}};
    w.configure_geometry(c, corridors);
    const auto colony = w.seed_colony(position({6, 6, 10}, c));
    const auto ant = w.seed_ant(colony, {position({6, 6, 10}, c)});
    auto route = w.query_route(ant, position({24, 6, 10}, c));
    require(route.found && w.validate_route(ant, route), "true 3D corridor not connected");
    require(!w.query_route(ant, position({14, 14, 18}, c)).found, "projected crossing invented a vertical connector");
    w.submit({ant, {1000}, ActionKind::Move, {}, position({14, 14, 10}, c), 0});
    w.advance_to({1000});
    require(w.committed_events().back().outcome == Outcome::Blocked, "move tunneled through different-depth solid");
    roundtrip(w);
    WorldRuntime linked({4, 1}, 1);
    const std::array<BoxQ, 3> connected{corridors[0], corridors[1], BoxQ{{12, 4, 8}, {16, 16, 12}}};
    linked.configure_geometry(c, connected);
    const auto cc = linked.seed_colony(position({6, 6, 10}, c));
    const auto aa = linked.seed_ant(cc, {position({6, 6, 10}, c)});
    require(linked.query_route(aa, position({14, 14, 18}, c)).found, "actual vertical connector ignored");
}
void clearance() {
    WorldRuntime w({4, 1}, 1);
    const auto c = config();
    const BoxQ narrow{{2, 5, 5}, {28, 7, 7}};
    w.configure_geometry(c, std::span{&narrow, 1});
    const auto colony = w.seed_colony(position({6, 6, 6}, c));
    const auto ant = w.seed_ant(colony, {position({6, 6, 6}, c)});
    require(w.query_route(ant, position({20, 6, 6}, c)).found, "unloaded body does not fit exact clearance boundary");
    const auto portals = w.query_portals(ant);
    require(portals.size() == 2 && portals[0].geometry_revision == 0 && portals[0].half_extent_q == 1,
            "narrow tunnel exposes an unproved vertical or lateral portal");
    const auto food = w.seed_food(position({6, 6, 6}, c), {100, 0, 0, 0});
    w.submit({ant, {100}, ActionKind::CollectFood, food, {}, 100});
    w.advance_to({100});
    require(w.committed_events().back().outcome == Outcome::Blocked && w.query_ant(ant)->carried_food.total_ug() == 0,
            "loading violated geometric clearance");
    require(!w.spatially_clear(position({6, 6, 6}, c), position({20, 6, 6}, c), 2),
            "loaded body fit undersized tunnel");
    roundtrip(w);
}
void contact() {
    WorldRuntime w({4, 1}, 1);
    auto c = config();
    const std::array<BoxQ, 2> rooms{{{{2, 2, 2}, {10, 22, 22}}, {{11, 2, 2}, {28, 22, 22}}}};
    w.configure_geometry(c, rooms);
    const auto colony = w.seed_colony(position({8, 12, 12}, c));
    const auto a = w.seed_ant(colony, {position({9, 12, 12}, c)}), b = w.seed_ant(colony, {position({12, 12, 12}, c)});
    w.enable_physiology(a, {{100, 100, 100, 0}, 1000000000, 1000, 0});
    w.enable_physiology(b);
    require(w.query_neighborhood(a, .002).ants.empty(), "neighbor sensing sees through soil wall");
    w.submit_nutrition({a, {100}, NutritionAction::Trophallaxis, b, 100});
    w.advance_to({100});
    require(w.query_physiology(b)->crop.total_ug() == 0 && w.committed_events().back().outcome == Outcome::OutOfReach,
            "nutrition transferred through wall");
    w.submit({a, {1000}, ActionKind::Move, {}, position({12, 12, 12}, c), 0});
    w.advance_to({1000});
    require(w.committed_events().back().outcome == Outcome::Blocked, "thin wall tunnel");
    roundtrip(w);
}
void autonomy() {
    for (std::uint64_t seed = 1; seed <= 8; ++seed) {
        Fixture f(seed, {}, {6, 12, 12}, true);
        auto &w = f.world;
        w.set_behavior(f.worker, IndividualBehavior::Excavate);
        WorldRuntime copy({4, 2}, 0);
        copy.restore(w.checkpoint());
        w.advance_to({20000});
        for (std::int64_t t = 37; t < 20000; t += 137)
            copy.advance_to({t});
        copy.advance_to({20000});
        require(w.checkpoint() == copy.checkpoint(), "host advances change excavation behavior");
        const auto state = *w.query_excavator(f.worker);
        require(state.digs && state.carrying_moves && state.deliveries,
                "local excavation did not carry soil to known depot");
        balanced(w);
        roundtrip(w);
        w.set_behavior(f.worker, IndividualBehavior::Paused);
        const auto parcels = w.soil_parcels();
        w.advance_to({21000});
        require(w.soil_parcels() == parcels && !w.query_excavator(f.worker)->enabled,
                "paused worker loses soil or continues work");
        w.set_behavior(f.worker, IndividualBehavior::Excavate);
        w.schedule_lifecycle(f.worker, {21100}, LifeStage::Dead);
        w.advance_to({22000});
        require(!w.query_excavator(f.worker)->enabled, "dead worker continues excavation");
        balanced(w);
        roundtrip(w);
    }
}
void fill_navigation() {
    WorldRuntime w({4, 1}, 1);
    auto c = config();
    const BoxQ tunnel{{2, 10, 10}, {28, 14, 14}};
    w.configure_geometry(c, std::span{&tunnel, 1});
    const auto colony = w.seed_colony(position({6, 12, 12}, c));
    const auto a = w.seed_ant(colony, {position({12, 12, 12}, c), LifeStage::Adult, Caste::Worker, 20000});
    const auto b = w.seed_ant(colony, {position({16, 12, 12}, c)});
    w.enable_physiology(a, {{100, 100, 100, 0}, 1000000000, 1000, 0});
    w.enable_physiology(b);
    const BoxQ mine{{10, 14, 10}, {14, 15, 14}}, plug{{14, 10, 10}, {15, 14, 14}};
    w.submit_soil({a, {100}, SoilAction::Excavate, mine, {}, 0});
    w.advance_to({100});
    require(w.geometry_edits().size() == 1, "plug fixture soil not excavated");
    const auto route = w.query_route(a, position({24, 12, 12}, c));
    require(route.found, "open tunnel disconnected before fill");
    const SoilParcelRef parcel{w.summary().world, w.soil_parcels().front().id};
    w.submit_nutrition({a, {150}, NutritionAction::Trophallaxis, b, 100});
    w.advance_to({150});
    require(w.query_physiology(b)->crop.total_ug() == 100, "open contact blocked before fill");
    w.submit_nutrition({a, {400}, NutritionAction::Trophallaxis, b, 100});
    w.submit({a, {500}, ActionKind::Move, {}, position({20, 12, 12}, c), 0});
    w.submit_soil({a, {300}, SoilAction::Fill, plug, parcel, 1});
    w.advance_to({300});
    require(w.geometry_edits().size() == 2 && !w.validate_route(a, route) &&
                !w.query_route(a, position({24, 12, 12}, c)).found,
            "fill did not delete passage connectivity");
    w.advance_to({500});
    require(w.query_physiology(b)->crop.total_ug() == 100 && w.query_ant(a)->position == position({12, 12, 12}, c),
            "pending contact/move crossed a newly filled wall");
    balanced(w);
    roundtrip(w);
}
void neighborhood() {
    Fixture f;
    const auto start = position({12, 12, 12}, f.geometry);
    const auto near = f.world.seed_ant(f.colony, {start});
    for (int i = 0; i < 100; ++i)
        f.world.seed_ant(f.colony, {position({5, 5, 5}, f.geometry)});
    const auto before = f.world.checkpoint();
    const auto local = f.world.query_neighborhood(f.worker, .001);
    require(local.ants.size() == 1 && local.ants[0] == near && local.candidates_examined == 2,
            "local index scanned distant population");
    f.world.submit({near, {500}, ActionKind::Move, {}, position({6, 12, 12}, f.geometry), 0});
    f.world.advance_to({500});
    require(f.world.query_neighborhood(f.worker, .001).ants.empty(), "spatial index retained stale position");
    roundtrip(f.world);
    WorldRuntime copy({4, 2}, 0);
    copy.restore(before);
    require(copy.query_neighborhood(f.worker, .001).ants == local.ants, "restore did not rebuild neighborhood index");
}
void rollback() {
    RuntimeLimits limits;
    limits.geometry_edits = 0;
    Fixture f(1, limits);
    f.dig();
    const auto before = f.world.checkpoint();
    rejects([&] { f.world.advance_to({100}); });
    require(f.world.checkpoint() == before, "edit budget failure left partial state");
    RuntimeLimits small;
    small.geometry_index_entries = 0;
    Fixture g(1, small, {12, 12, 12}, true);
    g.dig();
    const auto saved = g.world.checkpoint();
    rejects([&] { g.world.advance_to({100}); });
    require(g.world.checkpoint() == saved, "index budget failure leaked soil or energy");
    Fixture h;
    h.dig();
    h.world.advance_to({100});
    const auto bytes = h.world.checkpoint();
    // Mutate the committed edit's physical volume, retaining a valid checksum.
    const auto id = h.world.geometry_edits().front().id.value;
    (void)id;
    auto bad = bytes;
    bad[8] = 4;
    repair_checksum(bad);
    rejects([&] { h.world.restore(bad); });
    require(h.world.checkpoint() == bytes, "rejected restore changed authority");
    const auto prior = h.world.checkpoint();
    for (int i = 0; i < 5; ++i) {
        (void)h.world.query_signed_distance(position({12, 12, 12}, h.geometry));
        (void)h.world.query_neighborhood(h.worker, .002);
    }
    require(h.world.checkpoint() == prior, "geometry query mutates state");
    roundtrip(h.world);
}
void corruption() {
    Fixture f;
    f.dig();
    f.world.advance_to({100});
    const auto bytes = f.world.checkpoint();
    // Schema 7 retains records and appends the empty command count and social flag.
    // has one of each and no excavation program; alter semantic fields, then rehash.
    const auto requests = bytes.size() - 25 - 81, parcels = requests - 73, edits = parcels - 89, ledger = edits - 56;
    require(bytes[requests] == 1 && bytes[parcels] == 1 && bytes[edits] == 1, "corruption test layout drifted");
    const std::array offsets{edits + 8 + 73, parcels + 32, ledger + 16, requests + 8 + 57, edits + 8 + 16};
    for (auto offset : offsets) {
        auto bad = bytes;
        bad[offset] ^= 1;
        repair_checksum(bad);
        rejects([&] { f.world.restore(bad); });
        require(f.world.checkpoint() == bytes, "semantic corruption changed destination world");
    }
    Fixture active(2, {}, {6, 12, 12}, true);
    active.world.set_behavior(active.worker, IndividualBehavior::Excavate);
    active.world.advance_to({5000});
    const auto saved = active.world.checkpoint();
    auto bad = saved;
    // Owned wake precedes the action, empty command count and checksum.
    bad[bad.size() - 33] ^= 64;
    repair_checksum(bad);
    rejects([&] { active.world.restore(bad); });
    require(active.world.checkpoint() == saved, "bad excavation ownership replaced valid world");
}
void budgets() {
    RuntimeLimits limits;
    limits.sdf_bricks = 1;
    Fixture f(1, limits);
    const std::array<PointQ, 2> keys{{{1, 1, 1}, {2, 1, 1}}};
    const auto before = f.world.checkpoint();
    rejects([&] { f.world.rebuild_geometry_cache(keys); });
    require(!f.world.query_sdf_brick(keys[0]) && f.world.geometry_snapshot().cached_bricks == 0 &&
                f.world.checkpoint() == before,
            "partial cache rebuild survived failure");
    f.world.rebuild_geometry_cache(std::span{keys}.first(1));
    const auto brick = f.world.query_sdf_brick(keys[0]);
    rejects([&] { f.world.rebuild_geometry_cache(keys); });
    require(f.world.query_sdf_brick(keys[0]) == brick, "failed rebuild changed earlier cache");
    RuntimeLimits nav;
    nav.navigation_nodes = 1;
    Fixture n(1, nav);
    const auto route = n.world.query_route(n.worker, position({6, 12, 12}, n.geometry));
    require(!route.found && route.budget_exhausted, "bounded route query invents connectivity");
    RuntimeLimits spatial;
    spatial.neighborhood_buckets = 1;
    Fixture q(1, spatial);
    const auto saved = q.world.checkpoint();
    rejects([&] { (void)q.world.query_neighborhood(q.worker, 1); });
    require(q.world.checkpoint() == saved, "failed neighborhood query mutates state");
}
void connectivity() {
    WorldRuntime w({4, 1}, 1);
    const auto c = config();
    const std::array<BoxQ, 2> cavities{{{{2, 10, 10}, {14, 14, 14}}, {{15, 10, 10}, {28, 14, 14}}}};
    w.configure_geometry(c, cavities);
    const auto colony = w.seed_colony(position({12, 12, 12}, c));
    const auto ant = w.seed_ant(colony, {position({12, 12, 12}, c), LifeStage::Adult, Caste::Worker, 20000});
    const auto destination = position({18, 12, 12}, c);
    require(!w.query_route(ant, destination).found, "wall-separated cavities connected before dig");
    w.submit_soil({ant, {100}, SoilAction::Excavate, patch, {}, 0});
    WorldRuntime copy({4, 2}, 0);
    copy.restore(w.checkpoint());
    w.advance_to({100});
    copy.advance_to({100});
    require(copy.checkpoint() == w.checkpoint(), "restore changed connecting edit");
    const auto route = w.query_route(ant, destination);
    require(route.found && w.validate_route(ant, route), "real excavation did not open body-clear portal");
    w.submit({ant, {600}, ActionKind::Move, {}, destination, 0});
    w.advance_to({600});
    require(w.query_ant(ant)->position == destination && w.soil_parcels().front().position == destination,
            "carried parcel did not cross excavated connection");
    const SoilParcelRef parcel{w.summary().world, w.soil_parcels().front().id};
    w.submit_soil({ant, {700}, SoilAction::Drop, {}, parcel, 1});
    w.advance_to({700});
    require(w.query_parcel(parcel)->position == destination && w.query_parcel(parcel)->state == ParcelState::Deposited,
            "soil delivered at an invented location");
    balanced(w);
    roundtrip(w);
}
void surface_barrier() {
    WorldRuntime w({4, 1}, 1);
    const auto c = config();
    BehaviorConfig behavior;
    behavior.sensing_radius_cells = 3;
    w.configure_surface({position({8, 12, 12}, c), 5, 1, .001}, {}, behavior);
    const std::array<BoxQ, 2> cavities{{{{2, 2, 2}, {11, 22, 22}}, {{12, 2, 2}, {28, 22, 22}}}};
    w.configure_geometry(c, cavities);
    const auto colony = w.seed_colony(position({8, 12, 12}, c));
    const auto ant = w.seed_ant(colony, {position({8, 12, 12}, c)});
    w.seed_food(position({14, 12, 12}, c), {100, 0, 0, 0});
    require(w.sense(ant).food_count == 0 && w.sense(ant).sampled_cells == 2,
            "surface perception traversed solid geometry");
    roundtrip(w);
}
} // namespace
int main(int argc, char **argv) {
    try {
        require(argc == 2, "expected one S4 test case");
        const std::string_view name = argv[1];
        if (name == "INITIAL")
            initial();
        else if (name == "MATERIAL")
            material();
        else if (name == "OVERLAP")
            overlap();
        else if (name == "CONSTRAINTS")
            constraints();
        else if (name == "SDF")
            sdf();
        else if (name == "NAVIGATION")
            navigation();
        else if (name == "CLEARANCE")
            clearance();
        else if (name == "CONTACT")
            contact();
        else if (name == "AUTONOMY")
            autonomy();
        else if (name == "ROLLBACK")
            rollback();
        else if (name == "FILL_NAVIGATION")
            fill_navigation();
        else if (name == "NEIGHBORHOOD")
            neighborhood();
        else if (name == "CORRUPTION")
            corruption();
        else if (name == "BUDGETS")
            budgets();
        else if (name == "CONNECTIVITY")
            connectivity();
        else if (name == "SURFACE_BARRIER")
            surface_barrier();
        else
            throw std::invalid_argument("unknown S4 case");
        std::cout << "PASS S4_" << name << '\n';
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
