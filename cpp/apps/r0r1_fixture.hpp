#pragma once

#include "wp6b_fixture.hpp"

namespace antworld::r0r1 {
inline wp5::Scene digging(std::uint64_t id,std::uint64_t seed,unsigned count,NestScoring scoring,
                          const RuntimeLimits& limits,bool shielded=false) {
    WorldConfig world;
    world.continuous_spatial_motion=true;
    world.min_m={-.08,-.03,-.08}; world.max_m={.08,.01,.08};
    wp5::Scene scene{WorldRuntime({647,id},seed,world,limits),{},{},{},{},{},{}};
    auto& w=scene.world;
    EcologicalClosureConfig profile;
    profile.distance_clock=profile.floor_space=profile.activity_cost=true;
    profile.portable_field=profile.brood_space=profile.portable_care_motion=profile.local_nest_activity=true;
    if (scoring!=NestScoring::Original) profile.nest_dynamics=NestDynamics{false,scoring};
    w.configure_ecological_closure(profile);
    w.configure_long_term();
    auto& g=scene.geometry;
    g.origin_m={};
    g.initial_solid={{-128,-60,-128},{128,0,128}};
    g.work_duration={30*60'000}; // Retain the original R0 physical assay clocks.
    g.decision_delay={60'000};
    scene.voids={{{-6,-10,-6},{6,-4,6}},{{-3,-10,-3},{3,0,3}}};
    scene.rocks=shielded?std::vector<BoxQ>{
        {{-7,-10,-6},{-6,-4,6}},{{6,-10,-6},{7,-4,6}},{{-6,-10,-7},{6,-4,-6}},
        {{-6,-10,6},{6,-4,7}},{{-6,-4,-6},{-3,0,6}},{{3,-4,-6},{6,0,6}},
        {{-3,-4,-6},{3,0,-3}},{{-3,-4,3},{3,0,6}}
    }:std::vector<BoxQ>{{{18,-16,-24},{22,-3,-2}}};
    w.configure_geometry(g,scene.voids,scene.rocks);
    auto social=closure::day_social();
    social.decision_interval={10*60'000};
    social.minimum_program_time={30*60'000};
    social.exchange_enabled=false;
    social.excavate_weight=8;
    w.configure_social(social);
    w.configure_biology(closure::timed_care(true));
    const PositionM depot{0,-.004,0};
    const auto colony=w.seed_colony(depot);
    for (unsigned i=0;i<count;++i) {
        const auto worker=w.seed_ant(colony,{depot,LifeStage::Adult,Caste::Worker,4000});
        w.enable_physiology(worker,wp5::adult,rm01::physiology_config(rm01::legacy_duration));
        w.set_autonomy(worker);
        scene.workers.push_back(worker);
    }
    return scene;
}
} // namespace antworld::r0r1
