#include "antworld/core/behavior.hpp"
#include "antworld/core/rng.hpp"
#include "behavior_rng.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace antworld {
namespace {
std::uint64_t bounded(Rng& rng, std::uint64_t n) {
    const auto threshold = (std::uint64_t{0}-n) % n;
    for (;;) { const auto v = rng.next(); if (v >= threshold) return v % n; }
}
}
BehaviorDecision choose_behavior(std::uint64_t seed, EntityId actor, bool carrying,
    const ForagerState& state, const LocalObservation& local, const BehaviorConfig& config) {
    if (!actor.value || !state.path_size || config.sensing_radius_cells < 1 || config.sensing_radius_cells > 3 ||
        config.route_capacity < 2 || config.route_capacity > route_storage_capacity ||
        state.path_size > config.route_capacity || state.memory_size > config.route_capacity ||
        local.step_count > 4 || local.food_count > perception_storage_capacity || local.time.milliseconds < 0 ||
        state.learned_at.milliseconds < 0 || state.learned_at > local.time || config.memory_lifetime.milliseconds < 0 ||
        state.path[state.path_size-1] != local.current || state.mode > BehaviorMode::Rest || state.heading > Direction::None ||
        config.max_trip_moves < config.route_capacity || !config.explore_weight || config.explore_weight > 1000000 ||
        config.persistence_weight > 1000000 || config.trail_weight > 1000000 ||
        !std::isfinite(config.trail_cap_units) || config.trail_cap_units <= 0 ||
        !std::isfinite(config.trail_cutoff_units) || config.trail_cutoff_units <= 0 || config.trail_cutoff_units > config.trail_cap_units)
        throw std::invalid_argument("invalid bounded individual input");
    for (std::uint32_t i = 0; i < local.step_count; ++i) {
        const auto& step = local.steps[i];
        const auto dx = std::int64_t{step.cell.x}-local.current.x, dz = std::int64_t{step.cell.z}-local.current.z;
        if (std::abs(dx)+std::abs(dz) != 1 || step.direction >= Direction::None ||
            !std::isfinite(step.trail_units) || step.trail_units < 0)
            throw std::invalid_argument("invalid local step cue");
        for (std::uint32_t j = 0; j < i; ++j) if (local.steps[j].cell == step.cell || local.steps[j].direction == step.direction)
            throw std::invalid_argument("duplicate local step cue");
    }
    for (std::uint32_t i = 0; i < local.food_count; ++i) {
        const auto& cue = local.food[i];
        if (!cue.resource.value || cue.distance_cells > config.sensing_radius_cells ||
            ((cue.cell == local.current) != (cue.distance_cells == 0))) throw std::invalid_argument("invalid local food cue");
        bool reachable = cue.distance_cells == 0;
        for (std::uint32_t j = 0; j < local.step_count; ++j) if (cue.first_step == local.steps[j].direction) reachable = true;
        if (!reachable) throw std::invalid_argument("food cue lacks a reachable first step");
    }
    BehaviorDecision choice;
    auto walk = [&](Cell cell, BehaviorMode mode, DecisionReason reason) {
        for (std::uint32_t i = 0; i < local.step_count; ++i) if (local.steps[i].cell == cell) {
            choice.action = ActionKind::Move; choice.destination = cell; choice.mode = mode; choice.reason = reason; return;
        }
    };
    const auto at_home = local.current == state.path[0];
    if (carrying && at_home) {
        choice.action = ActionKind::DeliverFood; choice.mode = BehaviorMode::Deliver; choice.reason = DecisionReason::NestContact;
        return choice;
    }
    if (!at_home && (carrying || state.mode == BehaviorMode::Return || state.path_size >= config.route_capacity ||
        state.trip_moves >= config.max_trip_moves)) {
        if (state.path_size > 1) walk(state.path[state.path_size-2], BehaviorMode::Return, DecisionReason::HomeTrace);
        return choice;
    }
    // Local food always takes precedence over speculative trails or learned routes.
    if (local.food_count) {
        const FoodCue* best = &local.food[0];
        for (std::uint32_t i = 1; i < local.food_count; ++i) {
            const auto& food = local.food[i];
            if (food.distance_cells < best->distance_cells ||
                (food.distance_cells == best->distance_cells && food.resource < best->resource)) best = &food;
        }
        if (best->cell == local.current) {
            choice.action = ActionKind::CollectFood; choice.resource = best->resource;
            choice.mode = BehaviorMode::Collect; choice.reason = DecisionReason::LocalFood; return choice;
        }
        for (std::uint32_t i = 0; i < local.step_count; ++i) if (local.steps[i].direction == best->first_step)
            walk(local.steps[i].cell, BehaviorMode::Explore, DecisionReason::LocalFood);
        return choice;
    }
    if (config.memory_enabled && state.memory_size) {
        const auto expired = local.time.milliseconds-state.learned_at.milliseconds > config.memory_lifetime.milliseconds;
        if (!expired) {
            for (std::uint32_t i = 0; i < state.memory_size; ++i) if (state.memory[i] == local.current) {
                if (i+1 < state.memory_size) walk(state.memory[i+1], BehaviorMode::FollowMemory, DecisionReason::Memory);
                if (choice.action == ActionKind::Move) return choice;
                choice.forget_memory = true; break; // Empty endpoint or locally blocked learned step.
            }
        } else choice.forget_memory = true;
    }
    if (!local.step_count) return choice;
    std::array<std::uint64_t, 4> weights{}; std::uint64_t total = 0;
    for (std::uint32_t i = 0; i < local.step_count; ++i) {
        const auto& step = local.steps[i];
        if (local.step_count > 1 && state.path_size > 1 && step.cell == state.path[state.path_size-2]) continue;
        bool visited = false;
        for (std::uint32_t j = 0; j < state.path_size; ++j) if (state.path[j] == step.cell) visited = true;
        auto weight = visited ? std::uint64_t{1} : config.explore_weight;
        if (step.direction == state.heading) weight += config.persistence_weight;
        if (config.trails_enabled) weight += static_cast<std::uint64_t>(
            std::clamp(step.trail_units/config.trail_cap_units, 0.0, 1.0)*config.trail_weight);
        weights[i] = weight; total += weight;
    }
    auto rng = detail::individual_rng(seed, actor, state.decisions);
    auto pick = bounded(rng, total);
    for (std::uint32_t i = 0; i < local.step_count; ++i) {
        if (pick < weights[i]) {
            const auto trail = config.trails_enabled && local.steps[i].trail_units >= config.trail_cutoff_units;
            walk(local.steps[i].cell, trail ? BehaviorMode::FollowTrail : BehaviorMode::Explore,
                trail ? DecisionReason::Trail : DecisionReason::Search);
            return choice;
        }
        pick -= weights[i];
    }
    throw std::logic_error("weighted local decision failed");
}
} // namespace antworld
