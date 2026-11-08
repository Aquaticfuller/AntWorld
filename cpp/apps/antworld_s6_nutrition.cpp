#include "s6_nutrition_fixture.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>

using namespace antworld;
int main(int argc, char **argv) {
  try {
    if (argc < 2 || argc > 3)
      throw std::invalid_argument(
          "usage: antworld_s6_nutrition OUTPUT_DIR [SEEDS=64]");
    const std::filesystem::path output = argv[1];
    const auto seeds = argc == 3 ? std::stoul(argv[2]) : 64UL;
    if (!seeds || seeds > 64)
      throw std::invalid_argument("invalid seed count");
    std::filesystem::create_directories(output);
    std::ofstream summary(output / "summary.csv"),
        individuals(output / "individuals.csv");
    summary.exceptions(std::ios::badbit | std::ios::failbit);
    individuals.exceptions(std::ios::badbit | std::ios::failbit);
    summary << "scope,seed,policy,seed_stage,protein_per_nurse_ug,simulation_"
               "ms,adult_brood,larvae,deaths,oversupplied_brood,transfer_ug,"
               "protein_transfer_ug,nurse_protein_ug,carb_residual_ug,protein_"
               "residual_ug,water_residual_ug,energy_residual_nj\n";
    individuals << "scope,seed,policy,seed_stage,protein_per_nurse_ug,id,stage,"
                   "crop_protein_ug,tissue_protein_ug,received_protein_ug,"
                   "larva_ms,pupa_ms,adult_ms,death_ms\n";
    std::uint64_t runs = 0;
    for (std::uint64_t seed = 1; seed <= seeds; ++seed)
      for (bool eggs : {false, true})
        for (std::uint64_t protein : {400U, 100U, 0U})
          for (bool demand : {false, true}) {
            s6_fixture::Nutrition f(seed, protein, eggs, demand);
            auto &w = f.world;
            w.advance_to({180000});
            s3_fixture::balanced(w);
            s3_fixture::roundtrip(w);
            std::uint64_t adults = 0, larvae = 0, deaths = 0, excess = 0,
                          transfer = 0, protein_transfer = 0, nurse_protein = 0;
            std::map<EntityId, std::uint64_t> received;
            std::map<std::pair<EntityId, LifeStage>, std::int64_t> stages;
            for (const auto &e : w.committed_events()) {
              if (e.kind == FactKind::NutritionTransferred) {
                transfer += e.transferred.total_ug();
                protein_transfer += e.transferred.protein_ug;
                received[EntityId{e.payload}] += e.transferred.protein_ug;
              }
              if (e.kind == FactKind::StageChanged ||
                  e.kind == FactKind::AntDied)
                stages[{e.actor, e.stage}] = e.time.milliseconds;
            }
            const auto policy = demand ? "local_demand" : "legacy";
            const auto initial = eggs ? "egg" : "larva";
            for (auto id : f.nurses)
              nurse_protein += w.query_physiology(id)->crop.protein_ug;
            for (auto id : f.brood) {
              const auto a = *w.query_ant(id);
              const auto p = *w.query_physiology(id);
              adults += a.stage == LifeStage::Adult;
              larvae += a.stage == LifeStage::Larva;
              deaths += !a.alive();
              excess += p.crop.protein_ug + p.tissue_protein_ug >
                        p.config.larval_protein_requirement_ug;
              individuals << "ENGINEERING_FIXTURE," << seed << ',' << policy
                          << ',' << initial << ',' << protein << ','
                          << id.id.value << ','
                          << static_cast<unsigned>(a.stage) << ','
                          << p.crop.protein_ug << ',' << p.tissue_protein_ug
                          << ',' << received[id.id];
              for (auto stage : {LifeStage::Larva, LifeStage::Pupa,
                                 LifeStage::Adult, LifeStage::Dead})
                individuals << ','
                            << (stages.contains({id.id, stage})
                                    ? stages.at({id.id, stage})
                                    : -1);
              individuals << '\n';
            }
            summary << "ENGINEERING_FIXTURE," << seed << ',' << policy << ','
                    << initial << ',' << protein << ",180000," << adults << ','
                    << larvae << ',' << deaths << ',' << excess << ','
                    << transfer << ',' << protein_transfer << ','
                    << nurse_protein << ",0,0,0,0\n";
            ++runs;
          }
    std::cout << "PASS S6 local nutrition: " << runs
              << " complete runs; all ingredient/energy residuals checked\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
