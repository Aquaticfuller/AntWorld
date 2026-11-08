#pragma once
#include "antworld/core/world_runtime.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace antworld::fixture {
// Detached ENGINEERING_FIXTURE assay. Controlled substrate is not a WorldRuntime
// field, and these observations/positions are not fabricated committed facts.
struct TrailAssay {
    std::string_view context, treatment;
    bool mirror;
    std::int64_t age_ms;
    BehaviorConfig config;
    ForagerState ant;
    std::vector<Cell> trajectory = std::vector<Cell>(0);
    std::uint32_t on_moves{}, near_moves{}, first_streak{}, max_streak{}, streak{}, deviations{}, reacquisitions{}, uturns{};
    std::int64_t first_deviation{-1};
    double distance_sum{};
    bool initial_run{true};

    TrailAssay(std::string_view shape, std::string_view control, bool reflected, std::int64_t age, std::uint32_t persistence)
        : context(shape), treatment(control), mirror(reflected), age_ms(age) {
        config.memory_enabled = false; config.persistence_weight = persistence;
        if (control == "absent") config.trails_enabled = false;
        else if (control == "blind") config.trail_weight = 0;
        else if (control != "present") throw std::invalid_argument("unknown local trail control");
        ant.path[0] = reflect({40, 19}); ant.path[1] = reflect({40, 20}); ant.path_size = 2;
        ant.heading = Direction::North;
        if (shape == "lost") {
            ant.path[0] = reflect({40, 23}); ant.path[1] = reflect({40, 24}); ant.path[2] = reflect({41, 24}); ant.path_size = 3;
            ant.heading = mirror ? Direction::West : Direction::East;
        } else if (shape == "visited") {
            ant.path[0] = reflect({41, 24}); ant.path[1] = reflect({41, 23});
            ant.path[2] = reflect({40, 23}); ant.path[3] = reflect({40, 24}); ant.path_size = 4;
        } else if (shape != "straight" && shape != "bend" && shape != "y_symmetric" && shape != "y_conflict")
            throw std::invalid_argument("unknown local trail geometry");
        trajectory.push_back(ant.path[ant.path_size-1]);
    }
    Cell reflect(Cell c) const { return {mirror ? 80-c.x : c.x, c.z}; }
    bool open(Cell physical) const {
        const auto c = reflect(physical);
        if (c.x < 0 || c.x > 80 || c.z < 0 || c.z > 80) return false;
        if (context != "y_symmetric" && context != "y_conflict") return true;
        if (c.x == 40 && c.z <= 20) return true;
        if (context == "y_conflict" && c.x == 40 && c.z > 20) return true;
        if (context == "y_conflict" && c.x < 40) return false;
        const auto dx = std::abs(c.x-40), dz = c.z-20;
        return dx > 0 && (dz == dx || dz == dx-1);
    }
    int distance(Cell physical) const {
        const auto c = reflect(physical);
        if (context == "straight" || context == "lost") return std::abs(c.x-40);
        if (context == "visited") return std::abs(c.x-41);
        if (context == "bend") return std::min(std::abs(c.x-40)+std::max(0, c.z-26), std::abs(c.z-26)+std::max(0, 40-c.x));
        if (c.x == 40 && c.z <= 20) return 0;
        const auto dx = c.x-40, dz = c.z-20;
        return dx > 0 && (dz == dx || dz == dx-1) ? 0 : 1;
    }
    double strength(std::uint32_t move) const {
        const auto elapsed = age_ms+static_cast<std::int64_t>(move)*1101;
        const auto v = std::exp2(-static_cast<double>(elapsed)/60000.0);
        return v < config.trail_cutoff_units ? 0 : v;
    }
    LocalObservation observe(std::uint32_t move) const {
        LocalObservation local; local.current = trajectory.back(); local.time = {age_ms+static_cast<std::int64_t>(move)*1101};
        constexpr std::array<Cell, 4> delta{{{0, 1}, {1, 0}, {0, -1}, {-1, 0}}};
        for (std::uint32_t i = 0; i < 4; ++i) {
            const Cell c{local.current.x+delta[i].x, local.current.z+delta[i].z};
            if (open(c)) local.steps[local.step_count++] = {c, static_cast<Direction>(i), config.trails_enabled && distance(c) == 0 ? strength(move) : 0};
        }
        return local;
    }
    std::uint32_t length() const { return context == "straight" || context == "bend" ? 24U : 1U; }
    void step(std::uint64_t seed) {
        const auto moved = static_cast<std::uint32_t>(trajectory.size()-1);
        const auto local = observe(moved); const auto choice = choose_behavior(seed, {7}, false, ant, local, config);
        if (choice.action != ActionKind::Move || choice.resource.value || ant.memory_size) throw std::logic_error("assay fabricated a target or nonlocal action");
        const auto to = choice.destination, from = trajectory.back();
        if (!open(to) || std::abs(to.x-from.x)+std::abs(to.z-from.z) != 1) throw std::logic_error("assay movement not locally legal");
        const auto previous = trajectory.size() == 1 ? ant.path[ant.path_size-2] : trajectory[trajectory.size()-2];
        if (to == previous) ++uturns;
        const auto was_on = distance(from) == 0, now_on = distance(to) == 0;
        if (was_on && !now_on) { ++deviations; if (first_deviation < 0) first_deviation = static_cast<std::int64_t>(moved)+1; }
        if (!was_on && now_on) ++reacquisitions;
        if (now_on) { ++on_moves; ++streak; max_streak = std::max(max_streak, streak); if (initial_run) ++first_streak; }
        else { streak = 0; initial_run = false; }
        if (distance(to) <= 1) ++near_moves;
        distance_sum += static_cast<double>(distance(to))*0.01;
        ant.heading = to.z > from.z ? Direction::North : (to.x > from.x ? Direction::East : (to.z < from.z ? Direction::South : Direction::West));
        ant.mode = choice.mode; ++ant.decisions; ++ant.trip_moves;
        bool found = false;
        for (std::uint32_t i = 0; i < ant.path_size; ++i) if (ant.path[i] == to) {
            for (auto j = i+1; j < ant.path_size; ++j) ant.path[j] = {};
            ant.path_size = i+1; found = true; break;
        }
        if (!found) {
            if (ant.path_size >= config.route_capacity) throw std::logic_error("assay exceeded bounded trace");
            ant.path[ant.path_size++] = to;
        }
        if (to == ant.path[0]) { ant.mode = BehaviorMode::Explore; ant.trip_moves = 0; }
        trajectory.push_back(to);
    }
    void run(std::uint64_t seed) { for (std::uint32_t i = 0; i < length(); ++i) step(seed); }
};
} // namespace antworld::fixture
