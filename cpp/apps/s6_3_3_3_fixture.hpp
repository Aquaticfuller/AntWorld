#pragma once
#include "s6_3_fixture.hpp"

namespace antworld::closure {
using s3_fixture::require;
using s6_3_fixture::day;
using s6_3_fixture::hour;
using s6_3_fixture::limits;

// ENGINEERING_FIXTURE: the unchanged S6.3 clocks expressed in game time.
inline PhysiologyConfig day_physiology() {
    PhysiologyConfig p;
    p.absorption_period={6*hour};
    p.behavior_interval={6*hour};
    p.water_loss_period={hour};
    p.egg_duration={2*day};
    p.larva_duration={3*day};
    p.pupa_duration={2*day};
    p.basal_nj_per_ms=1;
    p.active_nj_per_ms=1;
    return p;
}

inline SocialConfig day_social() {
    SocialConfig s;
    s.decision_interval={6*hour};
    s.minimum_program_time={6*hour};
    s.gift_first=true;
    s.local_work_continuation=true;
    return s;
}

inline SpeciesCareProfile timed_care(bool integrated) {
    SpeciesCareProfile c;
    c.local_retrieval=true;
    c.motion.emplace();
    c.motion->integrate_autonomy=integrated;
    return c;
}

inline void chamber(WorldRuntime& w) {
    GeometryConfig g;
    g.origin_m={-.008,-.008,-.008};
    g.initial_solid={{0,0,0},{32,16,32}};
    constexpr std::array<BoxQ,2> voids{{{{8,4,8},{24,12,24}},{{12,4,12},{20,16,20}}}};
    w.configure_geometry(g,voids);
}

inline constexpr PhysiologySeed adult{{200,100,200,0},1500000000,1600,0};
inline constexpr PhysiologySeed egg{{},500000000,1000,20};
inline constexpr PhysiologySeed larva{{},1000000000,1000,0};
inline constexpr PhysiologySeed pupa{{},1000000000,1000,100};
inline constexpr FoodMass patch{4000,500,4000,0};

inline void balanced_supply(WorldRuntime& w,unsigned population,PositionM position) {
    const auto food=w.seed_food(position,patch);
    ResourceCycleConfig cycle;
    cycle.reserve={20000ULL*population,2000ULL*population,5000ULL*population,0};
    cycle.release_limit={4000,400,2000,0};
    w.configure_resource_cycle(food,cycle);
}

inline WorldRuntime density_world(unsigned n,bool dense,bool integrated,bool continuous) {
    WorldRuntime w({6333,7},7,{{-.02,-.02,-.02},{.24,.02,.24},.08,.002,continuous},limits());
    w.configure_long_term();
    BehaviorConfig forage;
    forage.trails_enabled=false;
    w.configure_surface({{0,0,0},213,213,.001},{},forage);
    w.configure_social(day_social());
    w.configure_biology(timed_care(integrated));
    const auto colony=w.seed_colony();
    const auto p=day_physiology();
    for (unsigned i=0;i<n;++i) {
        const auto worker=w.seed_ant(colony,{});
        w.enable_physiology(worker,adult,p);
        if (integrated) w.set_autonomy(worker,true);
        else w.enable_brood_care(worker,{CareContext::Worker,{}});
    }
    for (unsigned i=0;i<2*n;++i) {
        const auto x=dense?.001:.001+static_cast<double>(i%16)*.014;
        const auto z=dense?0:static_cast<double>(i/16)*.014;
        const auto brood=w.seed_ant(colony,{{x,0,z},LifeStage::Larva});
        w.enable_physiology(brood,larva,p);
    }
    balanced_supply(w,n,{.005,0,0});
    return w;
}

struct EcologySite {
    AntRef queen,target;
    PositionM depot;
    double cell_m;
};

inline EcologySite prepare_ecology(WorldRuntime& w,unsigned count,std::string_view space,bool food,bool integrated) {
    w.configure_long_term();
    const bool fine=space=="fine";
    const bool underground=space=="underground";
    const bool mixed=space=="chamber" || underground;
    const PositionM depot{0,underground?-.004:0,0};
    const double cell=fine?.001:.01;
    BehaviorConfig forage;
    forage.trails_enabled=false;
    w.configure_surface({{-.03,0,-.01},fine?61U:7U,fine?21U:3U,cell},{},forage);
    if (mixed) chamber(w);
    w.configure_social(day_social());
    auto care=timed_care(integrated);
    care.perception_radius_m=.012;
    w.configure_biology(care);
    const auto colony=w.seed_colony(depot);
    const auto queen=w.seed_ant(colony,{depot,LifeStage::Adult,Caste::Queen});
    const auto p=day_physiology();
    auto maternal=p;
    maternal.adult_protein_target_ug=20;
    w.enable_physiology(queen,adult,maternal);
    w.enable_reproduction(queen);
    if (integrated) w.set_autonomy(queen,true);
    for (unsigned i=0;i<count;++i) {
        const auto ref=w.seed_ant(colony,{depot});
        w.enable_physiology(ref,adult,p);
        w.set_autonomy(ref,true);
    }
    w.enable_physiology(w.seed_ant(colony,{depot,LifeStage::Egg}),egg,p);
    w.enable_physiology(w.seed_ant(colony,{depot,LifeStage::Larva}),larva,p);
    const PositionM displaced=underground?PositionM{.003,-.004,.0015}:
        mixed?PositionM{0,-.004,0}:PositionM{.010,0,0};
    const auto target=w.seed_ant(colony,{displaced,LifeStage::Larva});
    w.enable_physiology(target,larva,p);
    w.enable_physiology(w.seed_ant(colony,{depot,LifeStage::Pupa}),pupa,p);
    if (food) balanced_supply(w,count,{.010,0,0});
    return {queen,target,depot,cell};
}
} // namespace antworld::closure
