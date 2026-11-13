#pragma once

#include "antworld/core/world_runtime.hpp"
#include <array>
#include <stdexcept>
#include <string_view>

namespace antworld::ecological_assay {
struct RecruitmentScene {
    WorldRuntime world;
    AntRef scout;
    std::array<AntRef,3> receivers;
};

inline RecruitmentScene recruitment(std::uint64_t seed, std::string_view arm, RuntimeLimits limits = {}) {
    const bool enabled = arm == "scout" || arm == "sham" || arm == "naive" || arm == "blocked" || arm == "depleted";
    if (!enabled && arm != "disabled" && arm != "existing")
        throw std::invalid_argument("unknown recruitment treatment");
    WorldConfig config;
    config.continuous_spatial_motion = true;
    RecruitmentScene scene{WorldRuntime({648,seed},seed,config,limits),{},{}};
    auto& w=scene.world;
    EcologicalClosureConfig ecological;
    ecological.distance_clock=true;
    // In the disabled arm scouts still leave the physical cue and trail.
    ecological.recruitment=true;
    if (!enabled) ecological.cue_response_ppm=0;
    w.configure_ecological_closure(ecological);
    w.configure_long_term();
    BehaviorConfig behavior;
    behavior.memory_enabled=false;
    behavior.sensing_radius_cells=1;
    behavior.route_capacity=12;
    behavior.max_trip_moves=24;
    behavior.step_duration={1000};
    behavior.decision_delay={1000};
    behavior.field_interval={60000};
    const auto sign = seed%2 ? 1 : -1;
    std::vector<Cell> wall{{0,0},{4,0},{0,2},{4,2}};
    if (arm=="blocked") wall.push_back({2+sign,1});
    w.configure_surface({{-.02,0,-.01},5,3,.01},wall,behavior);
    SocialConfig social;
    social.decision_interval={5000};
    social.minimum_program_time={10000};
    social.exchange_enabled=false;
    w.configure_social(social);
    const auto colony=w.seed_colony();
    scene.scout=w.seed_ant(colony,{{},LifeStage::Adult,Caste::Worker,200});
    PhysiologyConfig physiology;
    physiology.energy_capacity_nj=1000000000;
    physiology.basal_nj_per_ms=1;
    physiology.active_nj_per_ms=1;
    physiology.hydration_capacity_ug=1000;
    physiology.water_loss_ug_per_period=1;
    physiology.water_loss_period={86400000};
    physiology.absorption_period={60000};
    physiology.behavior_interval={10000};
    physiology.crop_capacity_ug=1000;
    w.enable_physiology(scene.scout,{{},950000000,950,0},physiology);
    for (auto& receiver:scene.receivers) {
        receiver=w.seed_ant(colony,{{},LifeStage::Adult,Caste::Worker,200});
        const auto energy=arm=="existing"?200000000U:950000000U;
        w.enable_physiology(receiver,{{},energy,950,0},physiology);
        w.set_autonomy(receiver);
    }
    if (arm!="sham") w.seed_food({.02*sign,0,0},{arm=="depleted"?150U:6000U,0,arm=="depleted"?50U:2000U,0});
    if (arm!="naive" && arm!="existing") w.start_foraging(scene.scout);
    return scene;
}
} // namespace antworld::ecological_assay
