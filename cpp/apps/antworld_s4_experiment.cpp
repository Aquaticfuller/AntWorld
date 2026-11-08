#include "s4_fixture.hpp"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace antworld;
using namespace antworld::s4_fixture;
namespace {
struct Output {
    std::ofstream summary, edits, trajectories;
    explicit Output(const std::filesystem::path &directory)
        : summary(directory / "summary.csv"), edits(directory / "edits.csv"),
          trajectories(directory / "trajectories.csv") {
        for (auto *stream : {&summary, &edits, &trajectories}) {
            stream->exceptions(std::ios::badbit | std::ios::failbit);
            stream->precision(17);
        }
        summary << "scope,physics_version,seed,scenario,workers,reverse_order,window_ms,quantum_m,dry_ug_per_q3,water_"
                   "ug_per_q3,edits,excavated_q3,filled_q3,initial_q3,remaining_q3,carried_q3,deposited_q3,excavated_"
                   "dry_ug,excavated_water_ug,deposited_dry_ug,deposited_water_ug,carrying_moves,deliveries,decisions,"
                   "rejections,first_actor,restore_equal,mass_balanced,energy_balanced,checkpoint_bytes\n";
        edits << "scope,seed,scenario,workers,reverse_order,edit_id,time_ms,source_id,event_id,actor_id,parcel_id,kind,"
                 "min_x_q,min_y_q,min_z_q,max_x_q,max_y_q,max_z_q,volume_q3\n";
        trajectories << "scope,seed,scenario,workers,reverse_order,time_ms,actor_id,x_q,y_q,z_q,carried_q3,digs,"
                        "carrying_moves,deliveries\n";
    }
    void trajectory(const Fixture &f, const std::vector<AntRef> &ants, const char *scenario, bool reverse) {
        const auto &w = f.world;
        for (const auto ref : ants) {
            const auto ant = *w.query_ant(ref);
            const auto p = ant.position;
            const auto &c = f.geometry;
            auto coordinate = [&](double v, double origin) {
                return static_cast<std::int32_t>(std::llround((v - origin) / c.quantum_m));
            };
            std::uint64_t soil = 0;
            for (const auto &parcel : w.soil_parcels())
                if (parcel.carrier == ref.id)
                    soil += parcel.remaining_q3;
            const auto worker = w.query_excavator(ref).value_or(ExcavatorState{});
            trajectories << "ENGINEERING_FIXTURE," << w.summary().seed << ',' << scenario << ',' << ants.size() << ','
                         << reverse << ',' << w.summary().now.milliseconds << ',' << ref.id.value << ','
                         << coordinate(p.x, c.origin_m.x) << ',' << coordinate(p.y, c.origin_m.y) << ','
                         << coordinate(p.z, c.origin_m.z) << ',' << soil << ',' << worker.digs << ','
                         << worker.carrying_moves << ',' << worker.deliveries << '\n';
        }
    }
    void finish(const Fixture &f, const std::vector<AntRef> &ants, const char *scenario, bool reverse, bool replay) {
        const auto &w = f.world;
        balanced(w);
        roundtrip(w);
        const auto g = w.geometry_snapshot();
        const auto &l = g.ledger;
        std::uint64_t moves = 0, delivered = 0, decisions = 0, rejected = 0;
        for (auto ant : ants)
            if (const auto p = w.query_excavator(ant)) {
                moves += p->carrying_moves;
                delivered += p->deliveries;
                decisions += p->decisions;
            }
        for (const auto &e : w.committed_events())
            if (e.kind == FactKind::ActionRejected)
                ++rejected;
        const auto all = w.geometry_edits();
        summary << "ENGINEERING_FIXTURE," << WorldRuntime::physics_version << ',' << w.summary().seed << ',' << scenario
                << ',' << ants.size() << ',' << reverse << ',' << w.summary().now.milliseconds << ','
                << g.config.quantum_m << ',' << g.config.dry_ug_per_q3 << ',' << g.config.water_ug_per_q3 << ','
                << all.size() << ',' << l.excavated_q3 << ',' << l.filled_q3 << ',' << l.initial_q3 << ','
                << l.remaining_q3 << ',' << l.carried_q3 << ',' << l.deposited_q3 << ','
                << l.excavated_q3 * g.config.dry_ug_per_q3 << ',' << l.excavated_q3 * g.config.water_ug_per_q3 << ','
                << l.deposited_q3 * g.config.dry_ug_per_q3 << ',' << l.deposited_q3 * g.config.water_ug_per_q3 << ','
                << moves << ',' << delivered << ',' << decisions << ',' << rejected << ','
                << (all.empty() ? 0 : all.front().actor.value) << ',' << replay << ",1,1," << w.checkpoint().size()
                << '\n';
        for (const auto &e : all)
            edits << "ENGINEERING_FIXTURE," << w.summary().seed << ',' << scenario << ',' << ants.size() << ','
                  << reverse << ',' << e.id.value << ',' << e.time.milliseconds << ',' << e.source.value << ','
                  << e.event.value << ',' << e.actor.value << ',' << e.parcel.value << ','
                  << static_cast<unsigned>(e.kind) << ',' << e.box.min.x << ',' << e.box.min.y << ',' << e.box.min.z
                  << ',' << e.box.max.x << ',' << e.box.max.y << ',' << e.box.max.z << ',' << e.volume_q3 << '\n';
    }
};
void autonomous(Output &out, std::uint64_t seed, unsigned count, bool reverse) {
    Fixture f(seed, {}, {6, 12, 12}, true);
    std::vector<AntRef> ants{f.worker};
    for (unsigned i = 1; i < count; ++i) {
        const auto ant =
            f.world.seed_ant(f.colony, {position({6, 12, 12}, f.geometry), LifeStage::Adult, Caste::Worker, 20000});
        f.world.enable_physiology(ant, {{500, 0, 500, 0}, 1000000000, 1000, 0});
        ants.push_back(ant);
    }
    auto order = ants;
    if (reverse)
        std::reverse(order.begin(), order.end());
    for (auto ant : order)
        f.world.set_behavior(ant, IndividualBehavior::Excavate);
    WorldRuntime copy({4, 2}, 0);
    out.trajectory(f, ants, "autonomous", reverse);
    for (std::int64_t t = 5000; t <= 60000; t += 5000) {
        f.world.advance_to({t});
        balanced(f.world);
        out.trajectory(f, ants, "autonomous", reverse);
        if (t == 30000)
            copy.restore(f.world.checkpoint());
    }
    copy.advance_to({60000});
    const auto equal = copy.checkpoint() == f.world.checkpoint();
    require(equal, "checkpoint continuation changed excavation");
    out.finish(f, ants, "autonomous", reverse, equal);
}
void overlap(Output &out, std::uint64_t seed, bool reverse) {
    Fixture f(seed);
    const auto other =
        f.world.seed_ant(f.colony, {position({12, 12, 12}, f.geometry), LifeStage::Adult, Caste::Worker, 20000});
    const BoxQ second{{14, 12, 10}, {15, 16, 14}};
    if (!reverse)
        f.dig();
    f.world.submit_soil({other, {100}, SoilAction::Excavate, second, {}, 0});
    if (reverse)
        f.dig();
    WorldRuntime copy({4, 2}, 0);
    copy.restore(f.world.checkpoint());
    f.world.advance_to({100});
    copy.advance_to({50});
    copy.advance_to({100});
    const auto equal = copy.checkpoint() == f.world.checkpoint();
    require(equal, "competition replay diverged");
    out.trajectory(f, {f.worker, other}, "overlap", reverse);
    out.finish(f, {f.worker, other}, "overlap", reverse, equal);
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc < 2 || argc > 3)
            throw std::invalid_argument("usage: antworld_s4_experiment OUTPUT_DIRECTORY [SEEDS_1_TO_32]");
        const auto seeds = argc == 3 ? std::stoull(argv[2]) : 32ULL;
        require(seeds >= 1 && seeds <= 32, "seed range must be 1..32");
        const std::filesystem::path directory = argv[1];
        std::filesystem::create_directories(directory);
        Output out(directory);
        std::ofstream configuration(directory / "configuration.json");
        configuration.exceptions(std::ios::badbit | std::ios::failbit);
        configuration
            << "{\n  \"scope\": \"ENGINEERING_FIXTURE\",\n  \"physics_version\": " << WorldRuntime::physics_version
            << ",\n  \"seeds\": " << seeds
            << ",\n  \"coordinate_quantum_m\": 0.0005,\n  \"origin_m\": [0,-0.012,0],\n  \"initial_solid_q\": "
               "[0,0,0,32,24,24],\n  \"seed_void_q\": [2,2,2,14,22,22],\n"
            << "  \"dry_water_ug_per_q3\": [100,25],\n  \"body_loaded_half_q\": [1,2],\n  \"reach_q\": 4,\n  "
               "\"max_patch_extent_q\": 4,\n  \"sdf_brick_step_band_q\": [8,2,4],\n"
            << "  \"work_move_decision_ms\": [100,500,1],\n  \"dig_energy_nj_per_q3\": 1000,\n  \"capacity_ug\": "
               "20000,\n  \"autonomous\": {\"workers\": [1,4], \"depot_q\": [6,12,12], \"window_ms\": 60000, "
               "\"sample_ms\": 5000, \"restore_ms\": 30000, \"reversed_activation_for_four\": true, "
               "\"crop_carbs_water_ug\": [500,500], \"energy_nj\": 1000000000, \"hydration_ug\": 1000},\n"
            << "  \"overlap\": {\"workers\": 2, \"position_q\": [12,12,12], \"patches_q\": "
               "[[14,10,10,15,14,14],[14,12,10,15,16,14]], \"window_ms\": 100, \"reverse_submission\": [false,true], "
               "\"physiology_enabled\": false},\n"
            << "  \"world_and_physiology_defaults\": \"Versioned C++ WorldConfig and PhysiologyConfig "
               "ENGINEERING_FIXTURE defaults; source commit recorded in S4_RESULTS.md\"\n}\n";
        for (std::uint64_t seed = 1; seed <= seeds; ++seed) {
            autonomous(out, seed, 1, false);
            autonomous(out, seed, 4, false);
            autonomous(out, seed, 4, true);
            overlap(out, seed, false);
            overlap(out, seed, true);
        }
        std::cout << "S4 experiment complete: seeds=1.." << seeds << " runs=" << seeds * 5 << '\n';
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL: " << e.what() << '\n';
        return 1;
    }
}
