#include "s6_fixture.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace antworld;
int main(int argc,char** argv) {
    try {
        if (argc<2 || argc>4) throw std::invalid_argument("usage: antworld_s6_surplus OUTPUT_DIR [SEEDS=64] [primary|sensitivity]");
        const std::filesystem::path dir=argv[1]; std::filesystem::create_directories(dir);
        const auto seeds=argc>2?std::stoul(argv[2]):64UL;
        const std::string suite=argc>3?argv[3]:"primary";
        if ((suite!="primary" && suite!="sensitivity") || !seeds || seeds>(suite=="primary"?64UL:16UL)) throw std::invalid_argument("invalid frozen seed range/suite");
        std::ofstream out(dir/"summary.csv"),evidence(dir/"events.csv");
        out.exceptions(std::ios::badbit|std::ios::failbit); evidence.exceptions(std::ios::badbit|std::ios::failbit);
        out<<"scope,seed,condition,initial_donor_stage,encounter_budget,simulation_ms,donor_id,donor_stage,donor_protein_ug,adult_recipients,protein_transferred_ug,total_transferred_ug,autonomy_decisions,events,carb_residual_ug,protein_residual_ug,water_residual_ug,other_residual_ug,energy_residual_nj,soil_residual_q3\n";
        evidence<<"seed,condition,initial_donor_stage,encounter_budget,event_id,source_id,time_ms,kind,actor_id,recipient_id,carbs_ug,protein_ug,water_ug,other_ug,stage\n";
        const std::vector<std::uint32_t> budgets=suite=="primary"?std::vector<std::uint32_t>{16}:std::vector<std::uint32_t>{8,16,32};
        for (std::uint64_t seed=1;seed<=seeds;++seed) for (auto budget:budgets) for (bool pupa:{false,true})
            for (const auto condition:{"contact","wall","range","no_response","no_protein"}) {
                if (suite=="sensitivity" && std::string(condition)!="contact") continue;
                s6_fixture::Surplus fixture(seed,condition,pupa,budget); auto& w=fixture.world;
                w.advance_to({180000}); s6_fixture::balanced(w); s3_fixture::roundtrip(w);
                std::uint64_t protein=0,total=0,adults=0;
                for (const auto& e:w.committed_events()) {
                    if (e.kind==FactKind::NutritionTransferred) { protein+=e.transferred.protein_ug; total+=e.transferred.total_ug(); }
                    if (e.kind==FactKind::NutritionTransferred || e.kind==FactKind::StageChanged || e.kind==FactKind::AntDied || e.kind==FactKind::BehaviorChanged)
                        evidence<<seed<<','<<condition<<','<<(pupa?"pupa":"adult")<<','<<budget<<','<<e.id.value<<','<<e.source.value<<','<<e.time.milliseconds
                            <<','<<static_cast<unsigned>(e.kind)<<','<<e.actor.value<<','<<(e.kind==FactKind::NutritionTransferred?e.payload:0)<<','<<e.transferred.carbs_ug
                            <<','<<e.transferred.protein_ug<<','<<e.transferred.water_ug<<','<<e.transferred.other_ug<<','<<static_cast<unsigned>(e.stage)<<'\n';
                }
                for (auto a:fixture.larvae) adults+=w.query_ant(a)->stage==LifeStage::Adult;
                const auto n=w.nutrition_snapshot(); const auto g=w.geometry_snapshot().ledger;
                out<<"ENGINEERING_FIXTURE,"<<seed<<','<<condition<<','<<(pupa?"pupa":"adult")<<','<<budget<<",180000,"<<fixture.donor.id.value
                    <<','<<static_cast<unsigned>(w.query_ant(fixture.donor)->stage)<<','<<w.query_physiology(fixture.donor)->crop.protein_ug<<','<<adults<<','<<protein<<','<<total
                    <<','<<w.query_autonomy(fixture.donor)->decisions<<','<<w.summary().committed_events<<','<<n.introduced.carbs_ug-n.accounted.carbs_ug
                    <<','<<n.introduced.protein_ug-n.accounted.protein_ug<<','<<n.introduced.water_ug-n.accounted.water_ug<<','<<n.introduced.other_ug-n.accounted.other_ug
                    <<','<<n.energy_input_nj-n.body_energy_nj-n.dissipated_energy_nj<<','<<g.initial_q3-g.remaining_q3-g.carried_q3-g.deposited_q3<<'\n';
            }
        std::cout<<"PASS S6 surplus matrix; all seeds and negative controls retained\n";
    } catch (const std::exception& e) { std::cerr<<"FAIL: "<<e.what()<<'\n'; return 1; }
}
