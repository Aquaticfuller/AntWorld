#pragma once
#include "s4_fixture.hpp"
#include <filesystem>
#include <iostream>

namespace antworld::s5_fixture {
inline void clean_database(const std::filesystem::path &path) {
    for (const auto &suffix : {std::string{}, std::string{"-wal"}, std::string{"-shm"}}) {
        auto p = path;
        p += suffix;
        if (std::filesystem::is_regular_file(p))
            std::filesystem::remove(p);
    }
}
// ENGINEERING_FIXTURE. Four real actions per cycle; overlapping boxes use two real parcels.
struct History {
    WorldRuntime world;
    GeometryConfig geometry = s4_fixture::config();
    ColonyRef colony;
    AntRef first, second;
    std::int64_t time{};
    explicit History(std::uint64_t seed = 1) : world({5, 50}, seed) {
        world.configure_geometry(geometry, std::span{&s4_fixture::room, 1});
        const auto p = s4_fixture::position({12, 12, 12}, geometry);
        colony = world.seed_colony(p);
        first = world.seed_ant(colony, {p, LifeStage::Adult, Caste::Worker, 20000});
        second = world.seed_ant(colony, {p, LifeStage::Adult, Caste::Worker, 20000});
    }
    SoilParcelRef dig(AntRef actor, BoxQ box) {
        const auto cursor = world.summary().committed_events;
        time += 100;
        world.submit_soil(
            {actor, {time}, SoilAction::Excavate, box, {}, world.geometry_snapshot().geometry_revision});
        world.advance_to({time});
        const auto fact = world.events_after({cursor}, 1).at(0);
        s4_fixture::require(fact.kind == FactKind::SoilExcavated, "history fixture dig failed");
        return {world.summary().world, {fact.payload}};
    }
    void fill(AntRef actor, BoxQ box, SoilParcelRef parcel) {
        const auto cursor = world.summary().committed_events;
        time += 100;
        world.submit_soil(
            {actor, {time}, SoilAction::Fill, box, parcel, world.geometry_snapshot().geometry_revision});
        world.advance_to({time});
        s4_fixture::require(world.events_after({cursor}, 1).at(0).kind == FactKind::SoilFilled,
                            "history fixture fill failed");
    }
    void append(unsigned edits, bool interleaved) {
        s4_fixture::require(edits % 4 == 0, "fixture needs complete four-edit cycles");
        const auto a = s4_fixture::patch;
        const BoxQ b{{14, 11, 10}, {15, 15, 14}};
        for (unsigned i = 0; i < edits / 4; ++i) {
            if (interleaved) {
                const auto pa = dig(first, a), pb = dig(second, b);
                fill(first, a, pa);
                fill(second, b, pb);
            } else {
                const auto pa = dig(first, a);
                fill(first, a, pa);
                const auto pb = dig(first, a);
                fill(first, a, pb);
            }
        }
    }
};
} // namespace antworld::s5_fixture
