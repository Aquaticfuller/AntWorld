#pragma once
#include "antworld/core/entities.hpp"
#include <array>

namespace antworld {
// S2 is a flat, static surface fixture, not the future underground geometry model.
struct Cell {
    std::int32_t x{}, z{};
    auto operator<=>(const Cell&) const = default;
};
enum class Direction : std::uint8_t { North, East, South, West, None };
enum class BehaviorMode : std::uint8_t { Explore, FollowTrail, FollowMemory, Collect, Return, Deliver, Rest };
enum class DecisionReason : std::uint8_t { None, Search, LocalFood, Trail, Memory, HomeTrace, NestContact, NoLegalStep };
inline constexpr std::size_t route_storage_capacity = 64;
inline constexpr std::size_t perception_storage_capacity = 25; // Manhattan radius <= 3.

// All numeric behavior parameters are ENGINEERING_FIXTURE, version s2-local-v1.
struct SurfaceConfig {
    PositionM origin_m{-0.1, 0, -0.1}; // Center of cell (0,0).
    std::uint32_t width{21}, height{21};
    double cell_size_m{0.01};
    bool operator==(const SurfaceConfig&) const = default;
};
struct BehaviorConfig {
    bool trails_enabled{true}, memory_enabled{true};
    std::uint32_t sensing_radius_cells{2}, route_capacity{48}, max_trip_moves{192};
    SimTime step_duration{1100}, decision_delay{1}, memory_lifetime{300000}, field_interval{5000};
    double trail_half_life_s{60}, deposit_units{1}, trail_cap_units{16}, trail_cutoff_units{0.001};
    std::uint32_t explore_weight{10}, persistence_weight{20}, trail_weight{180};
    bool operator==(const BehaviorConfig&) const = default;
};
struct ForagerState {
    bool enabled{};
    BehaviorMode mode{BehaviorMode::Explore};
    Direction heading{Direction::North};
    std::uint64_t decisions{}, trip_moves{}, collections{};
    std::array<Cell, route_storage_capacity> path{}, memory{};
    std::uint32_t path_size{}, memory_size{};
    SimTime learned_at;
    ResourceId last_collected;
    ScheduledId wake, action;
    bool operator==(const ForagerState&) const = default;
};
struct LocalStep {
    Cell cell;
    Direction direction{Direction::None};
    double trail_units{};
    bool operator==(const LocalStep&) const = default;
};
struct FoodCue {
    ResourceId resource;
    Cell cell;
    std::uint32_t distance_cells{};
    Direction first_step{Direction::None};
    bool operator==(const FoodCue&) const = default;
};
// Only bounded reachable local cues cross the behavior boundary. No State,
// global food store, colony coverage or omniscient target coordinate is exposed.
struct LocalObservation {
    SimTime time;
    Cell current;
    std::array<LocalStep, 4> steps{};
    std::uint32_t step_count{};
    std::array<FoodCue, perception_storage_capacity> food{};
    std::uint32_t food_count{}, sampled_cells{};
    bool operator==(const LocalObservation&) const = default;
};
struct BehaviorDecision {
    ActionKind action{ActionKind::Rest};
    BehaviorMode mode{BehaviorMode::Rest};
    DecisionReason reason{DecisionReason::NoLegalStep};
    Cell destination;
    ResourceId resource;
    bool forget_memory{};
    bool operator==(const BehaviorDecision&) const = default;
};
// Pure individual model. Randomness is keyed by seed, identity and decision count.
BehaviorDecision choose_behavior(std::uint64_t seed, EntityId actor, bool carrying,
    const ForagerState&, const LocalObservation&, const BehaviorConfig&);

struct TrailSample {
    ColonyId colony;
    Cell cell;
    double units{};
    bool operator==(const TrailSample&) const = default;
};
struct CellVisit {
    Cell cell;
    std::uint64_t arrivals{};
    bool operator==(const CellVisit&) const = default;
};
struct ForagingCounters {
    std::uint64_t decisions{}, moves{}, explore_moves{}, trail_moves{}, memory_moves{}, return_moves{};
    std::uint64_t trips_started{}, collections{}, collection_attempts{}, deliveries{}, revisits{}, failed_actions{}, memory_failures{};
    std::uint64_t collected_outbound_moves{};
    double deposited_units{};
    bool operator==(const ForagingCounters&) const = default;
};
struct SurfaceSnapshot {
    bool configured{};
    SurfaceConfig surface;
    BehaviorConfig behavior;
    ForagingCounters counters;
    std::uint64_t walkable_cells{}, visited_cells{}, distinct_edges{}, edge_traversals{}, discovered_sources{}, active_trail_cells{};
    SimTime first_discovery{-1};
    EntityId first_discoverer;
    double trail_units{}, evaporated_units{};
    bool operator==(const SurfaceSnapshot&) const = default;
};
} // namespace antworld
