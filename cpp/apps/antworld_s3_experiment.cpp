#include "s3_fixture.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

using namespace antworld;
using namespace antworld::s3_fixture;
namespace {
std::ofstream output(const std::filesystem::path& path) {
    std::ofstream stream(path); stream.exceptions(std::ios::failbit|std::ios::badbit); return stream;
}
void mass(std::ostream& out, FoodMass m) { for (auto value : m.components()) out << ',' << value; }
void record(std::ostream& out, const WorldRuntime& world, std::uint64_t seed, const char* scenario,
    bool supplied, std::int64_t pulse, std::uint64_t capacity, bool reversed, std::span<const AntRef> focal,
    const NutritionSnapshot& initial, bool partition_equal, std::ostream& individuals) {
    balanced(world); const auto n = world.nutrition_snapshot();
    std::array<std::uint64_t,5> stages{}; std::uint64_t transitions = 0, transfers = 0, transferred_ug = 0, rejected = 0;
    for (const auto& e : world.committed_events()) {
        if (e.kind == FactKind::StageChanged) ++transitions;
        if (e.kind == FactKind::NutritionTransferred) { ++transfers; transferred_ug += e.transferred.total_ug(); }
        if (e.kind == FactKind::ActionRejected) ++rejected;
    }
    std::int64_t emergence_sum = 0; std::uint64_t emerged = 0;
    for (const auto ref : focal) {
        const auto ant = *world.query_ant(ref); const auto p = *world.query_physiology(ref); ++stages[static_cast<unsigned>(ant.stage)];
        std::int64_t larva_at = -1, pupa_at = -1, adult_at = -1;
        FoodMass received;
        for (const auto& e : world.committed_events()) {
            if (e.actor == ref.id && e.kind == FactKind::StageChanged) {
                if (e.stage == LifeStage::Larva) larva_at = e.time.milliseconds;
                if (e.stage == LifeStage::Pupa) pupa_at = e.time.milliseconds;
                if (e.stage == LifeStage::Adult) adult_at = e.time.milliseconds;
            }
            if (e.kind == FactKind::NutritionTransferred && e.payload == ref.id.value) {
                received.carbs_ug += e.transferred.carbs_ug; received.protein_ug += e.transferred.protein_ug;
                received.water_ug += e.transferred.water_ug; received.other_ug += e.transferred.other_ug;
            }
        }
        if (adult_at >= 0) { ++emerged; emergence_sum += adult_at; }
        individuals << "ENGINEERING_FIXTURE," << seed << ',' << scenario << ',' << supplied << ',' << pulse << ',' << capacity << ',' << reversed
            << ',' << ref.id.value << ',' << static_cast<unsigned>(ant.stage) << ',' << larva_at << ',' << pupa_at << ',' << adult_at
            << ',' << (adult_at >= 0) << ',' << world.summary().now.milliseconds;
        mass(individuals, received); mass(individuals, p.crop);
        individuals << ',' << p.tissue_protein_ug << ',' << p.body_energy_nj << ',' << p.hydration_ug << ',' << p.stage_progress.milliseconds << '\n';
    }
    out << "ENGINEERING_FIXTURE," << WorldRuntime::physics_version << ',' << seed << ',' << scenario << ',' << supplied << ',' << pulse << ','
        << capacity << ',' << reversed << ',' << world.summary().now.milliseconds << ',' << focal.size();
    for (auto count : stages) out << ',' << count;
    out << ',' << transitions << ',' << transfers << ',' << transferred_ug << ',' << rejected << ',' << emerged << ',' << emergence_sum;
    mass(out, initial.introduced); mass(out, n.accounted); mass(out, n.crop);
    out << ',' << n.tissue_protein_ug << ',' << n.hydration_ug << ',' << n.oxidized_carbs_ug << ',' << n.lost_water_ug
        << ',' << initial.energy_input_nj << ',' << n.energy_input_nj << ',' << n.body_energy_nj << ',' << n.dissipated_energy_nj
        << ',' << (n.introduced == n.accounted) << ',' << (n.energy_input_nj == n.body_energy_nj+n.dissipated_energy_nj) << ',' << partition_equal << '\n';
}
}
int main(int argc, char** argv) {
    try {
        if (argc < 2 || argc > 3) throw std::invalid_argument("usage: antworld_s3_experiment OUTPUT_DIR [SEEDS_1_TO_64]");
        const std::filesystem::path directory(argv[1]); const auto seeds = argc == 3 ? std::stoull(argv[2]) : 64;
        if (seeds < 1 || seeds > 64) throw std::invalid_argument("seed count must be 1..64");
        std::filesystem::create_directories(directory); auto out = output(directory/"summary.csv"), individuals = output(directory/"individuals.csv");
        const PhysiologyConfig config;
        auto configuration = output(directory/"configuration.json");
        configuration << "{\n  \"scope\": \"ENGINEERING_FIXTURE\",\n  \"physics_version\": " << WorldRuntime::physics_version
            << ",\n  \"seeds\": " << seeds << ",\n  \"crop_capacity_ug\": " << config.crop_capacity_ug
            << ",\n  \"hydration_capacity_ug\": " << config.hydration_capacity_ug << ",\n  \"energy_capacity_nj\": " << config.energy_capacity_nj
            << ",\n  \"carbohydrate_yield_nj_per_ug\": " << config.carbohydrate_yield_nj_per_ug
            << ",\n  \"basal_nj_per_ms\": " << config.basal_nj_per_ms << ",\n  \"active_nj_per_ms\": " << config.active_nj_per_ms
            << ",\n  \"water_loss_ug_per_s\": " << config.water_loss_ug_per_s
            << ",\n  \"carb_absorption_ug_per_s\": " << config.carb_absorption_ug_per_s
            << ",\n  \"water_absorption_ug_per_s\": " << config.water_absorption_ug_per_s
            << ",\n  \"protein_absorption_ug_per_s\": " << config.protein_absorption_ug_per_s
            << ",\n  \"larval_protein_requirement_ug\": " << config.larval_protein_requirement_ug
            << ",\n  \"transfer_limit_ug\": " << config.transfer_limit_ug << ",\n  \"behavior_interval_ms\": " << config.behavior_interval.milliseconds
            << ",\n  \"egg_duration_ms\": " << config.egg_duration.milliseconds << ",\n  \"larva_duration_ms\": " << config.larva_duration.milliseconds
            << ",\n  \"pupa_duration_ms\": " << config.pupa_duration.milliseconds
            << ",\n  \"pulse_periods_ms\": [250, 1000, 2000],\n  \"N2_basal_nj_per_ms\": 0,\n  \"N2_water_loss_ug_per_s\": 0,\n"
            << "  \"N2_requested_ug_per_donor\": 200,\n  \"N2_receiver_capacities_ug\": [0, 100, 1000],\n"
            << "  \"nurses\": 2,\n  \"brood\": 4,\n  \"brood_initial_energy_nj\": \"500000000 + SplitMix64(seed) draw modulo 500000001\",\n"
            << "  \"nurse_initial_crop_ug\": \"100 carb, 400/0 protein, 400 water, 100/500 other\",\n"
            << "  \"all_initial_hydration_ug\": 1000,\n  \"contact_distance_m\": 0.002,\n  \"position_m\": [0, 0, 0]\n}\n";
        out << "scope,physics_version,seed,scenario,supplied,pulse_ms,receiver_capacity_ug,reverse_order,window_ms,focal_count,eggs,larvae,pupae,adults,dead,stage_transitions,transfers,transferred_ug,rejections,emerged,emergence_sum_ms,initial_carbs_ug,initial_protein_ug,initial_water_ug,initial_other_ug,accounted_carbs_ug,accounted_protein_ug,accounted_water_ug,accounted_other_ug,crop_carbs_ug,crop_protein_ug,crop_water_ug,crop_other_ug,tissue_protein_ug,hydration_ug,oxidized_carbs_ug,lost_water_ug,initial_energy_nj,energy_input_nj,body_energy_nj,dissipated_energy_nj,mass_balanced,energy_balanced,partition_equal\n";
        individuals << "scope,seed,scenario,supplied,pulse_ms,receiver_capacity_ug,reverse_order,entity_id,final_stage,larva_at_ms,pupa_at_ms,adult_at_ms,emergence_observed,window_ms,received_carbs_ug,received_protein_ug,received_water_ug,received_other_ug,crop_carbs_ug,crop_protein_ug,crop_water_ug,crop_other_ug,tissue_protein_ug,body_energy_nj,hydration_ug,stage_progress_ms\n";
        for (std::uint64_t seed = 1; seed <= seeds; ++seed) {
            for (bool eggs : {false,true}) for (bool protein : {false,true}) for (auto pulse : {250,1000,2000}) {
                Brood b(seed,protein,eggs,pulse); const auto initial = b.world.nutrition_snapshot();
                WorldRuntime copy({9,9},0); copy.restore(b.world.checkpoint()); b.world.advance_to({180000});
                for (std::int64_t at = 137; at < 180000; at += 1237) copy.advance_to({at}); copy.advance_to({180000});
                const auto equal = b.world.checkpoint() == copy.checkpoint(); require(equal,"partition divergence in experiment"); roundtrip(b.world);
                record(out,b.world,seed,eggs ? "development" : "N1",protein,pulse,1000,false,b.brood,initial,equal,individuals);
            }
            for (bool supply : {false,true}) for (auto capacity : {0U,100U,1000U}) for (bool reverse : {false,true}) {
                Exchange b(seed,capacity,supply,reverse); const auto initial = b.world.nutrition_snapshot();
                WorldRuntime copy({9,9},0); copy.restore(b.world.checkpoint()); b.world.advance_to({500}); copy.advance_to({137}); copy.advance_to({500});
                const auto equal = b.world.checkpoint() == copy.checkpoint(); require(equal,"exchange partition divergence"); roundtrip(b.world);
                const std::array focal{b.first,b.second,b.recipient};
                record(out,b.world,seed,"N2",supply,1000,capacity,reverse,focal,initial,equal,individuals);
            }
        }
        std::cout << "Recorded " << seeds*24 << " complete ENGINEERING_FIXTURE runs\n";
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
