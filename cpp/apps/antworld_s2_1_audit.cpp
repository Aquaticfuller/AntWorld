#include "antworld/core/behavior.hpp"
#include <iostream>
#include <stdexcept>

using namespace antworld;
int main() {
    try {
        BehaviorConfig p; ForagerState f; f.path_size = 1; f.path[0] = {2, 2}; f.heading = Direction::North;
        LocalObservation local; local.current = {2, 2}; local.step_count = 4;
        local.steps = {{{{2, 3}, Direction::North, 0}, {{3, 2}, Direction::East, 0},
                        {{2, 1}, Direction::South, 0}, {{1, 2}, Direction::West, 0}}};
        std::uint64_t lower_id = 0, physical_flips = 0, weak_changes = 0, weak_labels = 0, fresh_changes = 0;
        std::uint64_t empty_east = 0, weak_east = 0, fresh_east = 0;
        for (std::uint64_t seed = 1; seed <= 4096; ++seed) {
            auto food = local; food.food_count = 2;
            food.food[0] = {{100}, {3, 2}, 1, Direction::East}; food.food[1] = {{200}, {1, 2}, 1, Direction::West};
            const auto a = choose_behavior(seed, {7}, false, f, food, p);
            if (a.destination == Cell{3, 2}) ++lower_id;
            std::swap(food.food[0].resource, food.food[1].resource);
            if (choose_behavior(seed, {7}, false, f, food, p).destination != a.destination) ++physical_flips;
            const auto empty = choose_behavior(seed, {7}, false, f, local, p);
            if (empty.destination == Cell{3, 2}) ++empty_east;
            auto trail = local; trail.steps[1].trail_units = 0.04;
            const auto weak = choose_behavior(seed, {7}, false, f, trail, p);
            if (weak.destination != empty.destination) ++weak_changes;
            if (weak.mode == BehaviorMode::FollowTrail) ++weak_labels;
            if (weak.destination == Cell{3, 2}) ++weak_east;
            trail.steps[1].trail_units = 1;
            const auto fresh = choose_behavior(seed, {7}, false, f, trail, p);
            if (fresh.destination != empty.destination) ++fresh_changes;
            if (fresh.destination == Cell{3, 2}) ++fresh_east;
        }
        std::cout << "scope,seeds,lower_id_choices,physical_changes_after_id_swap,weak_signal_choice_changes,weak_signal_follow_labels,fresh_signal_choice_changes,empty_east,weak_east,fresh_east\n"
            << "ENGINEERING_FIXTURE,4096," << lower_id << ',' << physical_flips << ',' << weak_changes << ',' << weak_labels << ',' << fresh_changes
            << ',' << empty_east << ',' << weak_east << ',' << fresh_east << '\n';
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
