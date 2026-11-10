#pragma once
#include "antworld/core/types.hpp"
#include <array>
#include <cstddef>

namespace antworld {
inline constexpr auto parameter_source = "ENGINEERING_FIXTURE";
struct PositionM {
    double x{}, y{}, z{};
    bool operator==(const PositionM&) const = default;
};
// Carbohydrate, protein, water and other material, all in integer micrograms.
struct FoodMass {
    std::uint64_t carbs_ug{}, protein_ug{}, water_ug{}, other_ug{};
    [[nodiscard]] std::uint64_t total_ug() const;
    [[nodiscard]] std::array<std::uint64_t, 4> components() const;
    bool operator==(const FoodMass&) const = default;
};
enum class LifeStage : std::uint8_t { Egg, Larva, Pupa, Adult, Dead };
enum class Caste : std::uint8_t { Worker, Queen, Male };
enum class Species : std::uint8_t { LasiusNigerEngineeringFixture };
struct Colony {
    ColonyId id;
    Species species{Species::LasiusNigerEngineeringFixture};
    SimTime founded_at;
    PositionM nest_position;
    FoodMass nest_food;
    bool operator==(const Colony&) const = default;
};
// ENGINEERING_FIXTURE defaults; no species calibration is claimed.
struct AntSeed {
    PositionM position;
    LifeStage stage{LifeStage::Adult};
    Caste caste{Caste::Worker};
    std::uint64_t carrying_capacity_ug{4000};
};
struct AntState {
    EntityId id;
    ColonyId colony;
    SimTime born_at;
    LifeStage stage{};
    Caste caste{};
    PositionM position;
    std::uint64_t position_revision{}, carrying_capacity_ug{};
    FoodMass carried_food;
    [[nodiscard]] bool alive() const { return stage != LifeStage::Dead; }
    bool operator==(const AntState&) const = default;
};
struct FoodSource {
    ResourceId id;
    PositionM position;
    FoodMass initial, remaining;
    bool operator==(const FoodSource&) const = default;
};
// ENGINEERING_FIXTURE obstacle-free bounds, movement speed and contact range.
struct WorldConfig {
    PositionM min_m{-1, -1, -1}, max_m{1, 1, 1};
    double max_speed_m_per_s{0.01}, contact_distance_m{0.002};
    // Select the continuous spatial contract for a newly created world.
    // Historical checkpoints retain their original movement rules.
    bool continuous_spatial_motion{};
    bool operator==(const WorldConfig&) const = default;
};
// Temporary host resource policies, not ecological constants or save-format maxima.
struct RuntimeLimits {
    std::size_t entities{65536}, pending_events{65536}, committed_events{65536};
    std::size_t events_per_timestamp{1024}, checkpoint_bytes{16 * 1024 * 1024};
    std::size_t surface_cells{65536}, trail_cells{65536};
    std::size_t geometry_edits{65536}, geometry_index_entries{1000000}, geometry_partition_cells{200000};
    std::size_t sdf_bricks{4096}, navigation_nodes{65536}, neighborhood_buckets{4096};
};
enum class ActionKind : std::uint8_t { Move, CollectFood, DeliverFood, Rest };
struct ActionProposal {
    AntRef actor;
    SimTime execute_at;
    ActionKind kind{ActionKind::CollectFood};
    FoodRef food;
    PositionM destination;
    std::uint64_t requested_ug{};
};
enum class Outcome : std::uint8_t {
    Success, Partial, MissingEntity, DeadActor, InvalidStage, OutOfBounds,
    TooFast, StalePosition, OutOfReach, Depleted, Capacity, DuplicateAction,
    InvalidTransition, AlreadyDead, Blocked, NonLocalMove, NotAtNest, EmptyInventory,
    StaleGeometry, NonDiggable, InvalidGeometry, InsufficientEnergy
};
struct FoodLedger {
    FoodMass introduced, available, carried, stored;
    bool operator==(const FoodLedger&) const = default;
};
} // namespace antworld
