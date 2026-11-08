#pragma once
#include "antworld/core/world_runtime.hpp"
#include <stdexcept>

namespace antworld::s4_fixture {
inline void require(bool value, const char *message) {
    if (!value)
        throw std::runtime_error(message);
}
inline PositionM position(PointQ p, const GeometryConfig &c) {
    return {c.origin_m.x + p.x * c.quantum_m, c.origin_m.y + p.y * c.quantum_m, c.origin_m.z + p.z * c.quantum_m};
}
inline GeometryConfig config() {
    GeometryConfig c;
    c.origin_m = {0, -.012, 0};
    c.initial_solid = {{0, 0, 0}, {32, 24, 24}};
    return c;
}
inline constexpr BoxQ room{{2, 2, 2}, {14, 22, 22}}, patch{{14, 10, 10}, {15, 14, 14}};
struct Fixture {
    GeometryConfig geometry = config();
    WorldRuntime world;
    ColonyRef colony;
    AntRef worker;
    explicit Fixture(std::uint64_t seed = 1, RuntimeLimits limits = {}, PointQ start = {12, 12, 12},
                     bool physiology = false)
        : world({4, 1}, seed, {}, limits) {
        world.configure_geometry(geometry, std::span{&room, 1});
        const auto p = position(start, geometry);
        colony = world.seed_colony(p);
        worker = world.seed_ant(colony, {p, LifeStage::Adult, Caste::Worker, 20000});
        if (physiology)
            world.enable_physiology(worker, {{500, 0, 500, 0}, 1000000000, 1000, 0});
    }
    ScheduledId dig(SimTime at = {100}, BoxQ box = patch) {
        return world.submit_soil(
            {worker, at, SoilAction::Excavate, box, {}, world.geometry_snapshot().geometry_revision});
    }
};
inline void balanced(const WorldRuntime &w) {
    const auto s = w.geometry_snapshot();
    const auto &l = s.ledger;
    require(l.initial_q3 == l.remaining_q3 + l.carried_q3 + l.deposited_q3, "soil volume is not conserved");
    require(l.initial_q3 + l.filled_q3 == l.remaining_q3 + l.excavated_q3, "geometry volume ledger disagrees");
    require(w.query_material_volume(s.config.initial_solid, Material::Soil) == l.remaining_q3,
            "authority disagrees with soil ledger");
    std::uint64_t carried = 0, deposited = 0;
    for (const auto &p : w.soil_parcels()) {
        if (p.state == ParcelState::Carried)
            carried += p.remaining_q3;
        if (p.state == ParcelState::Deposited)
            deposited += p.remaining_q3;
    }
    require(carried == l.carried_q3 && deposited == l.deposited_q3, "soil parcel inventory mismatch");
    const auto n = w.nutrition_snapshot();
    require(n.introduced == n.accounted && n.energy_input_nj == n.body_energy_nj + n.dissipated_energy_nj,
            "nutrition balance changed during excavation");
}
inline void roundtrip(const WorldRuntime &w) {
    WorldRuntime copy({4, 2}, 0);
    const auto bytes = w.checkpoint();
    copy.restore(bytes);
    require(copy.checkpoint() == bytes, "geometry checkpoint is not canonical");
    balanced(copy);
}
inline std::uint64_t checksum(std::span<const std::uint8_t> bytes) {
    std::uint64_t value = UINT64_C(14695981039346656037);
    for (auto b : bytes)
        value = (value ^ b) * UINT64_C(1099511628211);
    return value;
}
inline void repair_checksum(std::vector<std::uint8_t> &bytes) {
    auto value = checksum(std::span{bytes}.first(bytes.size() - 8));
    for (std::size_t i = bytes.size() - 8; i < bytes.size(); ++i) {
        bytes[i] = static_cast<std::uint8_t>(value & 255);
        value >>= 8;
    }
}
} // namespace antworld::s4_fixture
