#pragma once

#include "s6_3_3_3_fixture.hpp"
#include "antworld/core/ecological_closure.hpp"

namespace antworld::traffic_observer {
inline WorldRuntime nursery(std::uint64_t id,std::uint64_t seed,bool traffic,const RuntimeLimits& limits={}) {
    WorldConfig config;
    config.continuous_spatial_motion=true;
    config.min_m={-.025,-.012,-.025}; config.max_m={.025,.008,.025};
    WorldRuntime w({649,id},seed,config,limits);
    EcologicalClosureConfig ecology;
    ecology.distance_clock=ecology.floor_space=ecology.activity_cost=true;
    ecology.portable_field=ecology.brood_space=ecology.portable_care_motion=ecology.local_nest_activity=true;
    ecology.nest_dynamics=NestDynamics{true};
    ecology.local_traffic=traffic;
    w.configure_ecological_closure(ecology);
    w.configure_long_term();
    BehaviorConfig surface;
    surface.trails_enabled=false;
    w.configure_surface({{-.020,0,-.020},9,9,.005},{},surface);
    GeometryConfig ground;
    ground.origin_m={};
    ground.initial_solid={{-34,-20,-28},{34,0,28}};
    const std::array<BoxQ,5> voids{{
        {{-27,-10,-18},{-2,-4,18}}, {{2,-10,-18},{27,-4,18}},
        {{-2,-10,-16},{2,-4,-5}}, {{-2,-10,5},{2,-4,16}}, {{18,-10,-5},{25,0,3}}
    }};
    const std::array<BoxQ,1> stone{{{{-2,-10,-5},{2,-4,5}}}};
    w.configure_geometry(ground,voids,stone);
    auto social=closure::day_social();
    // ENGINEERING_FIXTURE for a short observable bout from a provisioned nursery.
    social.decision_interval={4000};
    social.minimum_program_time={20000};
    social.rest_weight=40;
    w.configure_social(social);
    auto care=closure::timed_care(true);
    care.perception_radius_m=.007;
    w.configure_biology(care);
    const auto at=[&](int x,int z) { return PositionM{x*ground.quantum_m,-.004,z*ground.quantum_m}; };
    const auto colony=w.seed_colony(at(-10,-3));
    auto queen=w.seed_ant(colony,{at(-10,-3),LifeStage::Adult,Caste::Queen,4000});
    w.enable_physiology(queen,closure::adult,closure::day_physiology());
    for (const auto [x,z]:std::array<Cell,4>{{{-10,8},{-12,-11},{13,0},{14,10}}}) {
        const auto larva=w.seed_ant(colony,{at(x,z),LifeStage::Larva,Caste::Worker,0});
        w.enable_physiology(larva,closure::larva,closure::day_physiology());
    }
    for (const auto [x,z]:std::array<Cell,10>{{{-21,-12},{-21,0},{-21,10},{-7,-12},{-6,11},
                                              {7,-10},{7,10},{19,-7},{21,9},{24,2}}}) {
        const auto ant=w.seed_ant(colony,{at(x,z),LifeStage::Adult,Caste::Worker,4000});
        w.enable_physiology(ant,closure::adult,closure::day_physiology());
        w.set_autonomy(ant);
    }
    return w;
}
} // namespace antworld::traffic_observer
