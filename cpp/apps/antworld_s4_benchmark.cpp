#include "s4_fixture.hpp"
#include <chrono>
#include <fstream>
#include <functional>
#include <iostream>

using namespace antworld;
using namespace antworld::s4_fixture;
namespace {
using Clock = std::chrono::steady_clock;
struct Bench {
    std::ofstream out;
    explicit Bench(const char *path) : out(path) {
        out.exceptions(std::ios::badbit | std::ios::failbit);
        out.precision(17);
        out << "scope,case,population,lifetime_edits,iteration,operation,elapsed_us,candidates,nodes,checkpoint_bytes,"
               "cached_bricks\n";
    }
    template <class F>
    void sample(const char *name, unsigned population, std::size_t edits, unsigned iteration, const char *operation,
                F fn) {
        const auto start = Clock::now();
        const auto metrics = fn();
        const auto elapsed = std::chrono::duration<double, std::micro>(Clock::now() - start).count();
        out << "ENGINEERING_FIXTURE," << name << ',' << population << ',' << edits << ',' << iteration << ','
            << operation << ',' << elapsed;
        for (const auto v : metrics)
            out << ',' << v;
        out << '\n';
    }
};
void geometry(Bench &b, unsigned lifetime) {
    WorldRuntime w({4, 1}, 1);
    auto cfg = config();
    cfg.initial_solid.max.x = 128;
    const std::array<BoxQ, 2> rooms{room, BoxQ{{100, 2, 2}, {112, 22, 22}}};
    w.configure_geometry(cfg, rooms);
    const auto c = w.seed_colony(position({6, 12, 12}, cfg));
    const auto local = w.seed_ant(c, {position({12, 12, 12}, cfg), LifeStage::Adult, Caste::Worker, 20000});
    const auto remote = w.seed_ant(c, {position({110, 12, 12}, cfg), LifeStage::Adult, Caste::Worker, 20000});
    const BoxQ remote_patch{{112, 10, 10}, {113, 14, 14}};
    std::int64_t time = 0;
    for (unsigned i = 0; i < lifetime / 2; ++i) {
        time += 100;
        w.submit_soil(
            {remote, {time}, SoilAction::Excavate, remote_patch, {}, w.geometry_snapshot().geometry_revision});
        w.advance_to({time});
        const auto parcel = w.geometry_edits().back().parcel;
        time += 100;
        w.submit_soil({remote,
                       {time},
                       SoilAction::Fill,
                       remote_patch,
                       {w.summary().world, parcel},
                       w.geometry_snapshot().geometry_revision});
        w.advance_to({time});
    }
    require(w.geometry_edits().size() == lifetime, "benchmark setup edits failed");
    const auto bytes = w.checkpoint();
    WorldRuntime copy({4, 2}, 0);
    const std::array<PointQ, 1> keys{{{1, 1, 1}}};
    for (unsigned iteration = 0; iteration < 30; ++iteration) {
        b.sample("remote_history", 2, lifetime, iteration, "point_query_1000", [&] {
            for (unsigned i = 0; i < 1000; ++i)
                require(w.query_material(position({14, 12, 12}, cfg)) == Material::Soil, "wrong local query");
            return std::array<std::uint64_t, 4>{0, 0, bytes.size(), w.geometry_snapshot().cached_bricks};
        });
        b.sample("remote_history", 2, lifetime, iteration, "sdf_rebuild_125", [&] {
            w.rebuild_geometry_cache(keys);
            return std::array<std::uint64_t, 4>{0, 0, bytes.size(), w.geometry_snapshot().cached_bricks};
        });
        b.sample("remote_history", 2, lifetime, iteration, "route_query", [&] {
            const auto route = w.query_route(local, position({6, 6, 6}, cfg));
            require(route.found, "benchmark route missing");
            return std::array<std::uint64_t, 4>{0, route.examined, bytes.size(), w.geometry_snapshot().cached_bricks};
        });
        b.sample("remote_history", 2, lifetime, iteration, "checkpoint_encode", [&] {
            const auto saved = w.checkpoint();
            return std::array<std::uint64_t, 4>{0, 0, saved.size(), w.geometry_snapshot().cached_bricks};
        });
        b.sample("remote_history", 2, lifetime, iteration, "checkpoint_restore_audit", [&] {
            copy.restore(bytes);
            return std::array<std::uint64_t, 4>{0, 0, bytes.size(), copy.geometry_snapshot().cached_bricks};
        });
    }
    for (unsigned iteration = 0; iteration < 30; ++iteration) {
        time += 100;
        w.submit_soil({local, {time}, SoilAction::Excavate, patch, {}, w.geometry_snapshot().geometry_revision});
        b.sample("local_repeated_patch", 2, w.geometry_edits().size(), iteration, "excavate_commit", [&] {
            w.advance_to({time});
            return std::array<std::uint64_t, 4>{0, 0, 0, w.geometry_snapshot().cached_bricks};
        });
        const auto parcel = w.geometry_edits().back().parcel;
        time += 100;
        w.submit_soil({local,
                       {time},
                       SoilAction::Fill,
                       patch,
                       {w.summary().world, parcel},
                       w.geometry_snapshot().geometry_revision});
        b.sample("local_repeated_patch", 2, w.geometry_edits().size(), iteration, "fill_commit", [&] {
            w.advance_to({time});
            return std::array<std::uint64_t, 4>{0, 0, 0, w.geometry_snapshot().cached_bricks};
        });
    }
    balanced(w);
}
void neighbors(Bench &b, unsigned population, bool dense) {
    Fixture f;
    auto &w = f.world;
    const auto p = w.query_ant(f.worker)->position;
    for (unsigned i = 1; i < population; ++i) {
        const PositionM far{.05 + .006 * (i % 100), .05 + .006 * (i / 100), .05};
        w.seed_ant(f.colony, {dense ? p : far});
    }
    for (unsigned iteration = 0; iteration < 30; ++iteration)
        b.sample(
            dense ? "dense_contacts" : "dispersed_population", population, 0, iteration, "neighborhood_query", [&] {
                const auto result = w.query_neighborhood(f.worker, .002);
                require(result.ants.size() == (dense ? population - 1 : 0), "incorrect neighborhood benchmark result");
                return std::array<std::uint64_t, 4>{result.candidates_examined, 0, 0, 0};
            });
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc != 2)
            throw std::invalid_argument("usage: antworld_s4_benchmark OUTPUT_CSV");
        Bench b(argv[1]);
        for (auto edits : {0U, 200U, 1000U})
            geometry(b, edits);
        for (auto population : {10U, 100U, 1000U})
            for (bool dense : {false, true})
                neighbors(b, population, dense);
        std::cout << "S4 performance samples complete\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL: " << e.what() << '\n';
        return 1;
    }
}
