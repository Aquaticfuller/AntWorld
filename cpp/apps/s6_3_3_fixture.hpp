#pragma once
#include "antworld/core/world_runtime.hpp"
#include <stdexcept>

namespace s6_3_3_fixture {
using namespace antworld;
inline RuntimeLimits limits() {
    RuntimeLimits l; l.committed_events=2000000; l.checkpoint_bytes=1024ULL*1024*1024;
    l.events_per_timestamp=100000; return l;
}
inline void require(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
inline PhysiologyConfig physiology() {
    // ENGINEERING_FIXTURE short behavioral assays: declared stores, not calibrated founding reserves.
    PhysiologyConfig p; p.absorption_period={3600000}; p.behavior_interval={60000};
    p.energy_capacity_nj=2000000000; p.basal_nj_per_ms=1; p.active_nj_per_ms=1;
    p.hydration_capacity_ug=2000; p.water_loss_period={3600000};
    p.egg_duration={864000000}; p.larva_duration={864000000}; p.pupa_duration={864000000};
    return p;
}
inline void conserved(const WorldRuntime& w) {
    const auto n=w.nutrition_snapshot(); require(n.introduced==n.accounted,"care nutrient conservation");
    require(n.energy_input_nj==n.body_energy_nj+n.dissipated_energy_nj,"care energy conservation");
}
struct Fixture {
    WorldRuntime w;
    ColonyRef colony;
    AntRef queen;
    std::vector<AntRef> brood,workers;
    Fixture(std::uint64_t seed=7,SpeciesCareProfile profile={},std::size_t larvae=5,std::size_t worker_count=0,
            bool barrier=false,CareContext context=CareContext::FoundingQueen,SimTime age={4752000000LL},bool contract=true,
            bool remote_workers=false,EnvironmentCareProfile environment={},double speed_cap=.01)
        :w({633,seed},seed,{{-.025,-.01,-.025},{.025,.01,.025},speed_cap,.002},limits()) {
        w.configure_long_term(); w.configure_social();
        if(barrier) {
            GeometryConfig g; g.origin_m={-.025,-.009,-.025}; g.quantum_m=.00025;
            g.initial_solid={{0,0,0},{200,72,200}};
            const std::array<BoxQ,2> voids{{{{0,0,0},{102,72,200}},{{103,0,0},{200,72,200}}}};
            w.configure_geometry(g,voids);
        }
        if(contract) w.configure_biology(profile,environment);
        colony=w.seed_colony(); queen=w.seed_ant(colony,{{},LifeStage::Adult,Caste::Queen});
        auto p=physiology(); w.enable_physiology(queen,{{0,500,0,0},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
        for(std::size_t i=0;i<larvae;++i) {
            const auto b=w.seed_ant(colony,{{-.0005,0,static_cast<double>(i%5)*.00025},LifeStage::Larva});
            w.enable_physiology(b,{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p); brood.push_back(b);
        }
        for(std::size_t i=0;i<worker_count;++i) workers.push_back(w.seed_ant(colony,{remote_workers?PositionM{.02,0,.02}:PositionM{barrier?.0015:0,0,-.00025}}));
        if(contract) w.enable_brood_care(queen,{context,age});
    }
};
} // namespace s6_3_3_fixture
