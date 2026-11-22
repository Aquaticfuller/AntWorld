#pragma once

#include "wp6b_fixture.hpp"
#include <algorithm>

namespace antworld::founding_habitat {
struct Temperature {
    std::uint64_t tenths_c, saturation_pa, activity_permille;
    std::array<std::int64_t,3> duration_tenths_day;
};

// Nominal regimes and observed Borisovka stage means from Kipyatkov et al.
// (2004), Table 2. The stage clocks share a nominal regime, not a fitted curve.
// Saturation pressure uses the Tetens equation. Activity scaling (Q10=2)
// and the reference physiological rates are ENGINEERING_FIXTURE.
inline constexpr std::array<Temperature,3> temperatures{{
    {225,2726,841,{207,135,204}},
    {250,3168,1000,{167,102,145}},
    {270,3565,1149,{147,87,125}}
}};
inline constexpr std::uint64_t reference_deficit=3168*20;

inline wp5::Scene setup(wp6b::Case c,const RuntimeLimits& limits,std::uint64_t tenths_c,std::uint64_t humidity,
                        bool external_supply=true,bool alternate_berth=false,bool sealed=false,bool anatomical=false,
                        bool mouth_access=false,bool adult_offers=false,bool wall_handoff=false,bool anatomical_handoff=false,
                        bool familiar_return=false,std::optional<TrailExposure> exposure={},
                        FoundingNutrition nutrition=FoundingNutrition::Original) {
    const auto climate=std::find_if(temperatures.begin(),temperatures.end(),
        [tenths_c](const Temperature& t){return t.tenths_c==tenths_c;});
    wp6b::require(climate!=temperatures.end() && (humidity==60 || humidity==80 || humidity==90),
        "Choose a supported founding temperature and humidity");
    const auto deficit=climate->saturation_pa*(100-humidity);
    const auto loss=[deficit](std::uint64_t baseline) {
        return std::max<std::uint64_t>(1,(baseline*deficit+reference_deficit/2)/reference_deficit);
    };
    for (std::size_t i=0;i<c.profile.brood.size();++i) {
        c.profile.brood[i].duration={climate->duration_tenths_day[i]*(wp6b::day_ms/10)};
        c.profile.brood[i].water_ug_per_day=loss(c.profile.brood[i].water_ug_per_day);
    }
    c.profile.water_ug_per_day=loss(c.profile.water_ug_per_day);
    auto& worker=c.profile.worker;
    const auto baseline_worker_loss=worker.water_loss_ug_per_period*
        static_cast<std::uint64_t>(wp6b::day_ms/worker.water_loss_period.milliseconds);
    worker.water_loss_period={wp6b::day_ms};
    worker.water_loss_ug_per_period=loss(baseline_worker_loss);

    auto& ecology=*c.ecological;
    ecology.local_nest_activity=ecology.local_traffic=ecology.yield_to_loaded=ecology.local_pantry_checks=true;
    ecology.nest_dynamics=NestDynamics{true,NestScoring::SpatialDemand};
    ecology.founding_habitat=FoundingHabitat{{anatomical?-.005:sealed?-.00175:-.004,-.004,0},2000,
                                           alternate_berth || sealed,sealed,anatomical,mouth_access,adult_offers,wall_handoff,anatomical_handoff,
                                           familiar_return,exposure,nutrition};
    const auto interval=[&](std::int64_t ms) {
        return SimTime{ms*1000/static_cast<std::int64_t>(climate->activity_permille)};
    };
    ecology.worker_activity_timing=WorkerActivityTiming{interval(900000),interval(wp6b::hour_ms)};
    ecology.water_sip_ug=25;

    // Split the environmental water budget between the mixed feeder and a
    // separate water source. The queen's finite wick is registered separately.
    c.food.water_ug=9000;
    if (!external_supply) c.food={};
    auto care=closure::timed_care(true);
    if (sealed) {
        care.step_m=.0005;
        care.arrangement_m=.00025;
    }
    if (anatomical) care.motion->search_steps=12;
    auto scene=wp6b::setup(c,limits,closure::day_social(),care,
        {static_cast<double>(tenths_c)/10,static_cast<double>(humidity)/100});
    if (external_supply) {
        const auto add_water=[&](PositionM position,std::uint64_t initial,std::uint64_t daily) {
            const auto water=scene.world.seed_food(position,{0,0,initial,0});
            scene.world.configure_resource_cycle(water,{{0,0,daily*c.release_days,0},{0,0,daily,0}});
        };
        if (exposure) {
            add_water({0,0,.03},6750,1688);
            add_water({0,0,-.04},2250,562);
        } else add_water({0,0,.03},9000,2250);
    }
    return scene;
}
} // namespace antworld::founding_habitat
