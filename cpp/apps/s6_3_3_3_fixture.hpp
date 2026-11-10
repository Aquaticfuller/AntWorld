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
} // namespace antworld::closure
