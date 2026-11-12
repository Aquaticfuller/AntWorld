#pragma once

#include "rm01_egg_timing.hpp"
#include "s6_3_3_3_fixture.hpp"
#include "wp5_geometry_view.hpp"

namespace antworld::wp5 {
using Time = std::int64_t;
using rm01::day_ms;
using rm01::hour_ms;

struct Case {
    std::string_view family, arm;
    unsigned workers;
    std::uint64_t seed;

    bool terrain() const { return family == "excavation" || family == "joint" || family == "gate"; }
    Time end() const { return family == "gate" ? 1600 : family == "excavation" ? 60000 : 21 * day_ms; }
    Time midpoint() const { return family == "gate" ? 300 : end() / 2; }
};

inline void validate(const Case& c) {
    const bool accepted_seed = c.seed == 1 || c.seed == 7 || c.seed == 19 || c.seed == 42 || c.seed == 43 || c.seed == 97;
    const bool group = c.workers == 8 || c.workers == 32;
    wp4::require(accepted_seed && (
        (c.family == "founding" && !c.workers && (c.arm == "on" || c.arm == "off")) ||
        (c.family == "worker-reserve" && group && c.arm == "half") ||
        (c.family == "excavation" && (group || c.workers == 4) && (c.arm == "compact" || c.arm == "wet" ||
          c.arm == "roomy" || c.arm == "isolated" || c.arm == "shielded")) ||
        (c.family == "joint" && group && (c.arm == "depot" || c.arm == "empty")) ||
        (c.family == "gate" && c.arm == "reopen" && c.workers == 2 && c.seed == 1)), "invalid WP-5 case");
}

// ENGINEERING_FIXTURE inherited from the WP-4 ecology reference.
inline constexpr PhysiologySeed adult{{200, 100, 200, 0}, 1500000000, 1600, 0};
inline constexpr PointQ depot{8, 12, 12};
inline constexpr BoxQ mine{{10, 14, 10}, {14, 15, 14}}, plug{{14, 10, 10}, {15, 14, 14}};

struct Scene {
    WorldRuntime world;
    GeometryConfig geometry;
    std::vector<BoxQ> voids, rocks;
    AntRef queen;
    std::vector<AntRef> workers;
    PositionM target;
};

inline AntRef register_queen(WorldRuntime& world, ColonyRef colony, PositionM nest) {
    const auto ant = world.seed_ant(colony, {nest, LifeStage::Adult, Caste::Queen, 4000});
    auto physiology = rm01::physiology_config(rm01::legacy_duration);
    physiology.adult_protein_target_ug = 20;
    world.enable_physiology(ant, adult, physiology);
    ReproductionConfig reproduction;
    reproduction.maintenance_horizon = reproduction.interval;
    world.enable_reproduction(ant, reproduction);
    return ant;
}

inline void configure(Scene& s, const Case& c) {
    auto& g = s.geometry;
    g.initial_solid = {{0, 0, 0}, {32, 24, 24}};
    g.origin_m = {-.004, -.006, -.006};
    if (c.family == "gate") {
        s.voids = {{{2, 10, 10}, {28, 14, 14}}};
        s.target = physical({24, 12, 12}, g);
    } else if (c.terrain()) {
        s.voids = {{{6, 10, 10}, {12, 14, 14}}, {{22, 9, 9}, {30, 15, 15}}};
        s.target = physical({10, 12, 12}, g);
        if (c.arm == "roomy") s.voids.front() = {{4, 7, 7}, {16, 17, 17}};
        if (c.arm == "wet") g.water_ug_per_q3 = 100;
        if (c.arm == "shielded") {
            s.rocks = {{{5, 9, 9}, {6, 15, 15}}, {{12, 9, 9}, {13, 15, 15}},
                       {{6, 9, 9}, {12, 10, 15}}, {{6, 14, 9}, {12, 15, 15}},
                       {{6, 10, 9}, {12, 14, 10}}, {{6, 10, 14}, {12, 14, 15}}};
        }
        if (c.family == "joint") {
            g.work_duration = {hour_ms / 2};
            g.move_duration = g.work_duration;
            g.decision_delay = {60000};
        }
    } else {
        g.origin_m = {-.008, -.006, -.006};
        s.voids = {{{12, 8, 8}, {20, 16, 16}}, {{0, 10, 10}, {32, 14, 14}}};
        s.target = physical({18, 12, 12}, g);
    }
    s.world.configure_geometry(g, s.voids, s.rocks);
}

inline Scene setup(const Case& c) {
    const std::uint64_t family = c.family == "founding" ? 1 : c.family == "worker-reserve" ? 2 :
                                 c.family == "excavation" ? 3 : c.family == "joint" ? 4 : 5;
    Scene s{WorldRuntime({645, family}, c.seed, {}, s6_3_1_fixture::limits()), {}, {}, {}, {}, {}, {}};
    auto& world = s.world;
    world.configure_long_term();
    if (!c.terrain() || c.family == "joint") {
        BehaviorConfig behavior;
        behavior.trails_enabled = false;
        world.configure_surface({{-.03, 0, -.03}, 7, 7, .01}, {}, behavior);
    }
    configure(s, c);
    auto social = closure::day_social();
    if (c.family == "excavation") social.minimum_program_time = social.decision_interval = {2000};
    world.configure_social(social);
    if (c.family == "founding") world.configure_biology(closure::timed_care(true));
    if (c.terrain()) world.configure_biology({}); // Typed action facts with no care enrollment.
    const auto nest = c.terrain() ? physical(c.family == "gate" ? PointQ{6, 12, 12} : depot, s.geometry) : PositionM{};
    const auto colony = world.seed_colony(nest);
    if (c.family != "excavation" && c.family != "gate") s.queen = register_queen(world, colony, nest);
    if (c.family == "founding" && c.arm == "on") world.set_autonomy(s.queen);
    for (unsigned i = 0; i < c.workers; ++i) {
        auto start = nest;
        if (c.arm == "isolated" && i) start = physical({26, 12, 12}, s.geometry);
        if (c.family == "gate") start = physical({i ? 16 : 12, 12, 12}, s.geometry);
        const auto worker = world.seed_ant(colony, {start, LifeStage::Adult, Caste::Worker,
                                                  c.family == "gate" ? 20000U : 4000U});
        auto reserve = adult;
        if (c.family == "worker-reserve") {
            reserve.body_energy_nj /= 2;
            reserve.hydration_ug /= 2;
        }
        world.enable_physiology(worker, reserve, rm01::physiology_config(rm01::legacy_duration));
        if (c.family != "gate") world.set_autonomy(worker);
        s.workers.push_back(worker);
    }
    if (c.family == "worker-reserve") {
        const auto food = world.seed_food({.02, 0, .01}, {4000, 500, 4000, 0});
        ResourceCycleConfig cycle;
        cycle.reserve = {20000ULL * c.workers, 2000ULL * c.workers, 5000ULL * c.workers, 0};
        cycle.release_limit = {4000, 400, 2000, 0};
        world.configure_resource_cycle(food, cycle);
    }
    if (c.family == "joint" && c.arm == "depot")
        world.seed_food(nest, {200000ULL * c.workers, 20000ULL * c.workers, 100000ULL * c.workers, 0});
    return s;
}

inline std::vector<Time> cuts(const Case& c) {
    if (c.family == "gate") return {0, 100, 300, 500, 600, 700, 900, 1400, 1500, 1600};
    std::vector<Time> times;
    const auto interval = c.family == "excavation" ? 10000 : day_ms;
    for (Time at = 0; at <= c.end(); at += interval) times.push_back(at);
    if (c.midpoint() % interval) times.insert(times.begin() + static_cast<std::ptrdiff_t>(c.midpoint() / interval + 1), c.midpoint());
    return times;
}

template<class Record>
void gate_input(const Scene& s, WorldRuntime& world, Time at, Record record) {
    const auto worker = s.workers.front();
    const auto p = [&](PointQ q) { return physical(q, s.geometry); };
    const auto submit = [&](Time when, std::string_view label, SoilAction action, BoxQ region,
                            SoilParcelRef parcel, std::uint64_t revision) {
        const auto id = world.submit_soil({worker, {when}, action, region, parcel, revision});
        record(at, when, label, id);
    };
    if (!at) submit(100, "mine", SoilAction::Excavate, mine, {}, 0);
    if (at == 100) {
        wp4::require(world.geometry_snapshot().geometry_revision == 1, "WP-5 plug soil was not mined");
        wp4::require(world.query_route(worker, s.target).found, "WP-5 initial passage is closed");
        const SoilParcelRef parcel{worker.world, world.soil_parcels().front().id};
        submit(300, "fill", SoilAction::Fill, plug, parcel, 1);
        record(at, 500, "attempt_crossing", world.submit({worker, {500}, ActionKind::Move, {}, p({20, 12, 12}), 0}));
    }
    if (at == 300) wp4::require(!world.query_route(worker, s.target).found, "WP-5 fill did not close the passage");
    if (at == 500) {
        wp4::require(world.query_ant(worker)->position == p({12, 12, 12}), "WP-5 move crossed soil");
        submit(600, "future_revision", SoilAction::Excavate, plug, {}, 3);
    }
    if (at == 600) {
        wp4::require(world.geometry_snapshot().geometry_revision == 2, "WP-5 rejected revision changed geometry");
        submit(700, "reopen", SoilAction::Excavate, plug, {}, 2);
    }
    if (at == 700) {
        wp4::require(world.query_route(worker, s.target).found, "WP-5 re-excavation failed to reopen the passage");
        record(at, 900, "too_fast_reopened", world.submit({worker, {900}, ActionKind::Move, {}, p({20, 12, 12}), 0}));
    }
    if (at == 900) {
        wp4::require(world.query_ant(worker)->position == p({12, 12, 12}), "WP-5 reopened move exceeded speed limit");
        record(at, 1400, "cross_reopened", world.submit({worker, {1400}, ActionKind::Move, {}, p({20, 12, 12}), 0}));
    }
    if (at == 1400 || at == 1500) {
        wp4::require(world.query_ant(worker)->position == p({20, 12, 12}), "WP-5 reopened traversal did not finish");
        const SoilParcelRef parcel{worker.world, world.soil_parcels().back().id};
        submit(at + 100, at == 1400 ? "drop" : "pickup", at == 1400 ? SoilAction::Drop : SoilAction::Pickup,
               {}, parcel, 3);
    }
}
} // namespace antworld::wp5
