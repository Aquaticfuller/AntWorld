#include "rm01_egg_timing.hpp"

#include <iostream>

namespace {
using namespace antworld;

void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}

template<class Error>
void rejected(WorldRuntime& world, AntRef egg, const rm01::Profile& request) {
    const auto before = world.checkpoint();
    const auto prior_queue = world.pending_events();
    const auto prior = world.snapshot();
    try {
        rm01::enable_seeded_egg(world, egg, rm01::original_egg_budget(), request);
        throw std::runtime_error("invalid egg clock was accepted");
    } catch (const Error&) {
        require(world.checkpoint() == before && world.pending_events() == prior_queue &&
                    world.snapshot() == prior && !world.query_physiology(egg),
                "rejected setup changed the world");
    }
}

void check_profiles() {
    using namespace rm01;
    require(resolve_egg_duration(profile("legacy")) == SimTime{172800000}, "legacy clock");
    require(resolve_egg_duration(profile("borisovka")) == SimTime{1442880000}, "Borisovka clock");
    require(resolve_egg_duration(profile("st-petersburg")) == SimTime{1356480000}, "St. Petersburg clock");
    require(PhysiologyConfig{}.egg_duration == SimTime{30000}, "Core default clock changed");

    WorldRuntime world({64, 1}, 1);
    world.configure_long_term();
    const auto colony = world.seed_colony();
    const auto egg = world.seed_ant(colony, {{}, LifeStage::Egg, Caste::Worker, 4000});
    const auto borisovka = profile("borisovka");
    auto wrong = borisovka;
    wrong.id = "unknown";
    rejected<std::invalid_argument>(world, egg, wrong);
    wrong = borisovka;
    wrong.condition = "other temperature";
    rejected<std::invalid_argument>(world, egg, wrong);
    wrong = borisovka;
    wrong.population = "St. Petersburg";
    rejected<std::invalid_argument>(world, egg, wrong);
    wrong = borisovka;
    wrong.source = "different DOI";
    rejected<std::invalid_argument>(world, egg, wrong);
    wrong = borisovka;
    wrong.unit = "ms";
    rejected<std::invalid_argument>(world, egg, wrong);
    wrong = borisovka;
    for (const auto days : {"", "0", "-2", "16.7d", "16.", "16.75", "16.8"}) {
        wrong.days = days;
        rejected<std::invalid_argument>(world, egg, wrong);
    }
    for (const auto days : {"106751991168", "18446744073709551616"}) {
        wrong.days = days;
        rejected<std::overflow_error>(world, egg, wrong);
    }
    enable_seeded_egg(world, egg, original_egg_budget(), borisovka);
    require(world.query_physiology(egg)->config == physiology_config({1442880000}),
            "valid setup did not apply the exact clock");
}
} // namespace

int main() {
    try {
        check_profiles();
        std::cout << "RM-01 profile and rejection checks passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
