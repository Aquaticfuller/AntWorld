#pragma once
#include "antworld/core/entities.hpp"

namespace antworld {
// Every numeric default in this file is ENGINEERING_FIXTURE, not species calibration.
enum class IndividualBehavior : std::uint8_t { Paused, Rest, Nurse, Forage, Excavate };
enum class DeathCause : std::uint8_t { None, EnergyDepleted, Dehydrated, Fixture };
struct PhysiologyConfig {
    SimTime absorption_period{1000};
    SimTime egg_duration{30000}, larva_duration{60000}, pupa_duration{30000};
    std::uint64_t crop_capacity_ug{1000}, hydration_capacity_ug{2000};
    std::uint64_t energy_capacity_nj{2000000000}, carbohydrate_yield_nj_per_ug{1000000};
    std::uint64_t basal_nj_per_ms{1000}, active_nj_per_ms{1000}, water_loss_ug_per_period{1};
    std::uint64_t carb_absorption_ug_per_s{10}, water_absorption_ug_per_s{100}, protein_absorption_ug_per_s{10};
    std::uint64_t larval_protein_requirement_ug{100}, transfer_limit_ug{100};
    SimTime behavior_interval{1000};
    SimTime water_loss_period{1000}; // water_loss_ug_per_period is ug per this interval.
    std::uint64_t adult_protein_target_ug{}; // Queen provisioning; zero in legacy worlds.
    bool operator==(const PhysiologyConfig&) const = default;
};
struct PhysiologySeed {
    FoodMass crop;
    std::uint64_t body_energy_nj{1000000000}, hydration_ug{1000}, tissue_protein_ug{};
    bool operator==(const PhysiologySeed&) const = default;
};
struct PhysiologyState {
    PhysiologyConfig config;
    PhysiologySeed initial;
    FoodMass crop;
    std::uint64_t body_energy_nj{}, hydration_ug{}, tissue_protein_ug{};
    std::uint64_t oxidized_carbs_ug{}, lost_water_ug{}, dissipated_energy_nj{};
    std::uint64_t water_loss_remainder{}, carb_remainder{}, water_remainder{}, protein_remainder{};
    SimTime updated_at, next_absorption, stage_progress;
    ScheduledId physiology_event, behavior_event;
    IndividualBehavior behavior{IndividualBehavior::Paused};
    DeathCause death_cause{DeathCause::None};
    std::uint64_t decisions{};
    EntityId mother; // Nonzero means initial stores were funded by a birth, not external input.
    std::uint64_t exported_energy_nj{};
    [[nodiscard]] double body_energy_j() const { return static_cast<double>(body_energy_nj) / 1e9; }
    bool operator==(const PhysiologyState&) const = default;
};
enum class NutritionAction : std::uint8_t { IngestCargo, WithdrawNest, Trophallaxis, ReturnProtein };
struct NutritionProposal {
    AntRef actor;
    SimTime execute_at;
    NutritionAction kind{NutritionAction::Trophallaxis};
    AntRef recipient;
    std::uint64_t requested_ug{100};
};
struct NutritionSnapshot {
    FoodMass introduced, accounted, crop;
    std::uint64_t hydration_ug{}, tissue_protein_ug{}, oxidized_carbs_ug{}, lost_water_ug{};
    std::uint64_t energy_input_nj{}, body_energy_nj{}, dissipated_energy_nj{};
    std::uint64_t individuals{};
    bool operator==(const NutritionSnapshot&) const = default;
};
} // namespace antworld
