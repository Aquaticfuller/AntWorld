#pragma once

#include "antworld/core/physiology.hpp"
#include <array>
#include <optional>

namespace antworld {
enum class FoundingPopulation : std::uint8_t { Borisovka = 1, StPetersburg = 2 };

struct FoundingStageProfile {
    SimTime duration;
    std::uint64_t basal_nj_per_day{}, water_ug_per_day{};
    bool operator==(const FoundingStageProfile&) const = default;
};

// ENGINEERING_FIXTURE. Applies only to the explicitly selected F1-R1 experiment.
struct FoundingFeedingPersistence {
    SimTime window;
    std::uint32_t repeat_ppm{};
    bool operator==(const FoundingFeedingPersistence&) const = default;
};

struct FoundingEarlyAccess {
    bool mobilize_larval_lipid{}, local_hatch_cue{};
    bool operator==(const FoundingEarlyAccess&) const = default;
};

struct FoundingProvisioning {
    bool local_exchange{};
    bool operator==(const FoundingProvisioning&) const = default;
};

// Warm protected founding experiment. All uncalibrated inputs are ENGINEERING_FIXTURE.
// Stage order is egg, larva, prepupa plus pupa. The population identifies the clock context.
struct FoundingProfile {
    static constexpr std::uint32_t version = 1;
    static constexpr std::uint32_t persistence_version = 2;
    static constexpr std::uint32_t early_access_version = 3;
    static constexpr std::uint32_t provisioning_version = 4;
    FoundingPopulation population{};
    std::array<FoundingStageProfile, 3> brood;
    PhysiologyConfig worker;
    SimTime first_lay, opening_width, opening_spacing, later_spacing, maintenance_floor;
    std::uint64_t wet_mass_ug{}, structural_minimum_ug{}, lipid_ug{}, protein_ug{}, water_ug{};
    std::uint64_t lipid_yield_nj_per_ug{}, basal_nj_per_day{}, active_nj_per_ms{}, water_ug_per_day{};
    std::uint64_t egg_lipid_ug{}, egg_protein_ug{}, egg_water_ug{}, lay_overhead_nj{};
    std::uint64_t larval_tissue_ug{}, larval_lipid_capacity_ug{};
    std::uint64_t ration_lipid_ug{}, ration_protein_ug{}, ration_water_ug{};
    std::optional<FoundingFeedingPersistence> feeding_persistence;
    std::optional<FoundingEarlyAccess> early_access;
    std::optional<FoundingProvisioning> provisioning;
    [[nodiscard]] std::uint32_t model_version() const {
        if (provisioning) return provisioning_version;
        if (early_access) return early_access_version;
        return feeding_persistence ? persistence_version : version;
    }
    bool operator==(const FoundingProfile&) const = default;
};

struct FoundingReserve {
    std::uint64_t lipid_ug{}, spent_lipid_ug{}, mobile_protein_ug{};
    std::uint64_t energy_remainder{}, water_remainder{};
    bool operator==(const FoundingReserve&) const = default;
};

struct FoundingBudget {
    std::uint64_t introduced_lipid_ug{}, owned_lipid_ug{}, spent_lipid_ug{};
    std::uint64_t introduced_protein_ug{}, owned_mobile_protein_ug{}, effective_energy_nj{};
    std::uint64_t enrolled{};
    bool operator==(const FoundingBudget&) const = default;
};
} // namespace antworld
