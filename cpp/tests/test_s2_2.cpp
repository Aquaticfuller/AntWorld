#include "s2_2_fixture.hpp"
#include "s2_1_fixture.hpp"
#include <iostream>

using namespace antworld;
namespace {
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
void model() {
    std::uint64_t corrections = 0;
    for (std::uint64_t seed = 1; seed <= 8192; ++seed) for (const bool mirror : {false, true}) {
        fixture::TrailAssay a("lost", "present", mirror, 0, 20), b("lost", "absent", mirror, 0, 20), c("lost", "blind", mirror, 0, 20);
        a.run(seed); b.run(seed); c.run(seed); corrections += a.uturns;
        require(b.uturns == 0 && b.trajectory == c.trajectory, "no-response correction changed control");
        // Use a fresh input to test non-lost and priority cases.
        fixture::TrailAssay original("lost", "present", mirror, 0, 20); auto local = original.observe(0);
        const auto predecessor = original.ant.path[original.ant.path_size-2];
        for (std::uint32_t i = 0; i < local.step_count; ++i) if (local.steps[i].direction == original.ant.heading) local.steps[i].trail_units = 1;
        require(choose_behavior(seed, {7}, false, original.ant, local, original.config).destination != predecessor, "correction overrides visible forward alternative");
        require(choose_behavior(seed, {7}, true, original.ant, local, original.config).destination == predecessor, "correction changed loaded homing");
        original.config.memory_enabled = true; original.ant.memory_size = 2; original.ant.memory[0] = local.current;
        original.ant.memory[1] = mirror ? Cell{38,24} : Cell{42,24};
        require(choose_behavior(seed, {7}, false, original.ant, local, original.config).mode == BehaviorMode::FollowMemory, "correction overrode learned route");
    }
    const auto measured = static_cast<double>(corrections)/16384;
    require(std::abs(measured-12.25/62.25) < 0.015, "correction draw changed unchanged relative weights");
    std::cout << "corrections=" << corrections << "/16384\n";
}
void locality() {
    fixture::TrailAssay a("lost", "present", false, 0, 20);
    const auto before = a.ant; auto local = a.observe(0);
    const auto decision = choose_behavior(9, {7}, false, a.ant, local, a.config);
    require(a.ant == before && a.ant.memory_size == 0 && decision.resource.value == 0, "pure local policy mutated knowledge");
    require(local.food_count == 0 && local.step_count == 4, "assay exposed nonlocal food or motion");
    for (auto& step : local.steps) step.trail_units = 0.0001;
    for (std::uint64_t seed = 1; seed <= 512; ++seed)
        require(choose_behavior(seed, {7}, false, a.ant, local, a.config).destination != a.ant.path[1], "invisible signal enabled correction");
    fixture::TrailAssay y("y_symmetric", "present", false, 0, 20), ym("y_symmetric", "present", true, 0, 20), asymmetric("y_conflict", "present", false, 0, 20);
    require(y.observe(0).step_count == 3 && ym.observe(0).step_count == 3 && asymmetric.observe(0).step_count == 3, "Y fixture is not a three-way junction");
    require(y.distance({41,20}) == 0 && ym.distance({39,20}) == 0, "reflection failed to move marked arm");
}
void continuous() {
    for (const std::string_view shape : {"straight", "bend"}) for (std::uint64_t seed = 1; seed <= 128; ++seed) for (const bool mirror : {false,true}) {
        fixture::TrailAssay a(shape, "present", mirror, 0, 20), copy(shape, "present", mirror, 0, 20), b(shape, "absent", mirror, 0, 20), c(shape, "blind", mirror, 0, 20);
        a.run(seed); b.run(seed); c.run(seed);
        for (unsigned i = 0; i < 24; ++i) copy.step(seed);
        require(a.trajectory == copy.trajectory && a.ant == copy.ant, "continuous policy replay differs");
        require(b.trajectory == c.trajectory, "blind substrate steered continuous trajectory");
        require(a.trajectory.size() == 25 && a.ant.memory_size == 0 && a.config.trail_weight == 180, "continuous fixture silently changed scope");
    }
}
void replay() {
    for (std::uint64_t seed = 1; seed <= 8; ++seed) {
        fixture::Recruitment r(seed, false, "present"); require(r.train(), "integrated trail training failed");
        r.world.start_foraging(r.novice); r.world.advance_to({r.retired_at.milliseconds+45000});
        const auto start = r.world.checkpoint(); WorldRuntime copy({4,5}, 8); copy.restore(start);
        const auto end = r.retired_at.milliseconds+180000;
        r.world.advance_to({end}); for (auto t = copy.summary().now.milliseconds; t < end; t += 997) copy.advance_to({t}); copy.advance_to({end});
        fixture::check_ingredients(r.world); require(copy.checkpoint() == r.world.checkpoint(), "correction changed saved/chunked integrated evolution");
        auto old = start; old[12] = 4; old[13] = old[14] = old[15] = 0;
        std::uint64_t hash = UINT64_C(14695981039346656037);
        for (std::size_t i = 0; i < old.size()-8; ++i) hash = (hash ^ old[i])*UINT64_C(1099511628211);
        for (unsigned i = 0; i < 8; ++i) old[old.size()-8+i] = static_cast<std::uint8_t>(hash >> (8*i));
        const auto before = copy.checkpoint(); bool rejected = false;
        try { copy.restore(old); } catch (const std::exception&) { rejected = true; }
        require(rejected && before == copy.checkpoint(), "old physics restore was not atomic");
    }
}
}
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: antworld_s2_2_tests CASE");
        const std::string_view name(argv[1]);
        if (name == "MODEL") model(); else if (name == "LOCALITY") locality(); else if (name == "CONTINUOUS") continuous(); else if (name == "REPLAY") replay();
        else throw std::invalid_argument("unknown S2.2 test");
        std::cout << "PASS " << name << '\n';
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
