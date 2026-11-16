#pragma once

#include "s6_3_3_3_fixture.hpp"
#include "antworld/core/ecological_closure.hpp"

namespace antworld::traffic_observer {
enum class Nursery : std::uint8_t { Reference, Traffic, Provisioned, CadenceOnly, NoFood, LocalEcology, DryEcology };

inline WorldRuntime nursery(std::uint64_t id,std::uint64_t seed,Nursery treatment,const RuntimeLimits& limits={}) {
    const bool local_ecology = treatment == Nursery::LocalEcology || treatment == Nursery::DryEcology;
    const bool new_layout = treatment == Nursery::Provisioned || treatment == Nursery::NoFood || local_ecology;
    const bool short_nutrition = new_layout || treatment == Nursery::CadenceOnly;
    WorldConfig config;
    config.continuous_spatial_motion=true;
    config.min_m={-.025,-.012,-.025}; config.max_m={.025,.008,.025};
    const auto tag = local_ecology ? (treatment == Nursery::DryEcology ? 652ULL : 651ULL) : (new_layout ? 650ULL : 649ULL);
    WorldRuntime w({tag,id},seed,config,limits);
    EcologicalClosureConfig ecology;
    ecology.distance_clock=ecology.floor_space=ecology.activity_cost=true;
    ecology.portable_field=ecology.brood_space=ecology.portable_care_motion=ecology.local_nest_activity=true;
    ecology.nest_dynamics=NestDynamics{true};
    ecology.local_traffic=treatment!=Nursery::Reference;
    ecology.yield_to_loaded=ecology.local_pantry_checks=new_layout;
    w.configure_ecological_closure(ecology);
    w.configure_long_term();
    BehaviorConfig surface;
    surface.trails_enabled=false;
    w.configure_surface({{-.020,0,-.020},9,9,.005},{},surface);
    GeometryConfig ground;
    ground.origin_m={};
    ground.initial_solid={{-34,-20,-28},{34,0,28}};
    if (new_layout) {
        // ENGINEERING_FIXTURE: physical digging occupies time and blocked digs back off.
        ground.decision_delay={1500};
        ground.work_duration={30000};
    }
    std::array<BoxQ,5> voids{{
        {{-27,-10,-18},{-2,-4,18}}, {{2,-10,-18},{27,-4,18}},
        {{-2,-10,-16},{2,-4,-5}}, {{-2,-10,5},{2,-4,16}}, {{18,-10,-5},{25,0,3}}
    }};
    if (new_layout) voids.back()={{-25,-10,-6},{-18,0,2}};
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
    // Keep the food handoff physically separate from the queen's body.
    const auto depot=new_layout ? at(-16,-2) : at(-10,-3);
    const auto colony=w.seed_colony(depot);
    auto queen=w.seed_ant(colony,{at(-10,-3),LifeStage::Adult,Caste::Queen,4000});
    auto queen_physiology=closure::day_physiology();
    if (local_ecology) {
        // Expose the existing uptake and paid reproduction mechanisms in an
        // initialized colony. The laboratory cadences remain ENGINEERING_FIXTURE.
        queen_physiology.absorption_period={60000};
        queen_physiology.behavior_interval=social.decision_interval;
        queen_physiology.adult_protein_target_ug=20;
    }
    w.enable_physiology(queen,closure::adult,queen_physiology);
    if (local_ecology) {
        ReproductionConfig reproduction;
        reproduction.maintenance_horizon=reproduction.interval;
        w.enable_reproduction(queen,reproduction);
        w.set_autonomy(queen);
    }
    auto physiology=closure::day_physiology();
    // ENGINEERING_FIXTURE: review nutrition on the same clock as program selection.
    if (short_nutrition) physiology.behavior_interval=social.decision_interval;
    if (new_layout) physiology.absorption_period={60000};
    for (const auto [x,z]:std::array<Cell,4>{{{-10,8},{-12,-11},{13,0},{14,10}}}) {
        const auto larva=w.seed_ant(colony,{at(x,z),LifeStage::Larva,Caste::Worker,0});
        w.enable_physiology(larva,closure::larva,physiology);
    }
    std::array<Cell,10> berths{{{-21,-12},{-21,0},{-21,10},{-7,-12},{-6,11},
                                {7,-10},{7,10},{19,-7},{21,9},{24,2}}};
    if (new_layout) berths[1]={-16,-2};
    for (const auto [x,z]:berths) {
        const auto ant=w.seed_ant(colony,{at(x,z),LifeStage::Adult,Caste::Worker,4000});
        const auto reserves = new_layout && at(x,z)==depot ? PhysiologySeed{{},400000000,450,0} : closure::adult;
        w.enable_physiology(ant,reserves,physiology);
        w.set_autonomy(ant);
    }
    if (treatment==Nursery::Provisioned) w.seed_food({-.010,0,.005},closure::patch);
    if (local_ecology) {
        // Fixed laboratory conditions. The entire seven-pulse reserve enters
        // the Core ledger at setup. No rain, humidity uptake or free water.
        auto mixture=closure::patch;
        if (treatment==Nursery::DryEcology) mixture.water_ug=0;
        const auto source=w.seed_food({-.010,0,.005},mixture);
        ResourceCycleConfig supply;
        supply.release_limit={mixture.carbs_ug/4,mixture.protein_ug/4,mixture.water_ug/4,0};
        const auto& daily=supply.release_limit;
        supply.reserve={7*daily.carbs_ug,7*daily.protein_ug,7*daily.water_ug,0};
        w.configure_resource_cycle(source,supply);
    }
    return w;
}

inline WorldRuntime nursery(std::uint64_t id,std::uint64_t seed,bool traffic,const RuntimeLimits& limits={}) {
    return nursery(id,seed,traffic?Nursery::Traffic:Nursery::Reference,limits);
}
} // namespace antworld::traffic_observer
