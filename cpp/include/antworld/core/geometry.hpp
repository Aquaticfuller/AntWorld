#pragma once
#include "antworld/core/entities.hpp"
#include <array>
#include <vector>

namespace antworld {
using GeometryEditId = Id<struct GeometryEditTag>;
using SoilParcelId = Id<struct SoilParcelTag>;
using SoilParcelRef = WorldRef<SoilParcelId>;
// Integer coordinates multiply quantum_m and add origin_m. Boxes are half-open.
struct PointQ {
    std::int32_t x{}, y{}, z{};
    auto operator<=>(const PointQ &) const = default;
};
struct BoxQ {
    PointQ min, max;
    bool operator==(const BoxQ &) const = default;
};
enum class Material : std::uint8_t { Void, Soil, Rock };
enum class SoilAction : std::uint8_t { Excavate, Drop, Pickup, Fill };
enum class ParcelState : std::uint8_t { Carried, Deposited, Exhausted };
// ENGINEERING_FIXTURE values throughout; coordinate/density choices are not calibration.
struct GeometryConfig {
    PositionM origin_m{0, -0.016, 0};
    double quantum_m{0.0005};
    BoxQ initial_solid{{0, 0, 0}, {32, 32, 32}};
    std::uint64_t dry_ug_per_q3{100}, water_ug_per_q3{25};
    std::int32_t body_half_q{1}, loaded_half_q{2}, reach_q{4}, max_patch_extent_q{4};
    std::int32_t brick_q{8}, sample_step_q{2}, sdf_band_q{4};
    SimTime work_duration{100}, move_duration{500}, decision_delay{1};
    std::uint64_t dig_energy_nj_per_q3{1000};
    bool operator==(const GeometryConfig &) const = default;
};
struct GeometryEdit {
    GeometryEditId id;
    ScheduledId source;
    EventId event;
    EntityId actor;
    SoilParcelId parcel;
    SoilAction kind{SoilAction::Excavate};
    SimTime time;
    BoxQ box;
    std::uint64_t volume_q3{};
    bool operator==(const GeometryEdit &) const = default;
};
struct SoilParcel {
    SoilParcelId id;
    GeometryEditId origin_edit;
    std::uint64_t initial_q3{}, remaining_q3{};
    EntityId carrier;
    PositionM position;
    ParcelState state{ParcelState::Carried};
    bool operator==(const SoilParcel &) const = default;
};
struct SoilProposal {
    AntRef actor;
    SimTime execute_at;
    SoilAction kind{SoilAction::Excavate};
    BoxQ box;
    SoilParcelRef parcel;
    std::uint64_t observed_geometry_revision{};
};
struct SoilRequest {
    EntityId actor;
    SoilAction kind{SoilAction::Excavate};
    BoxQ box;
    SoilParcelId parcel;
    std::uint64_t observed_revision{}, actual_q3{};
    GeometryEditId edit;
    bool operator==(const SoilRequest &) const = default;
};
struct SoilLedger {
    std::uint64_t initial_q3{}, remaining_q3{}, carried_q3{}, deposited_q3{};
    std::uint64_t excavated_q3{}, filled_q3{};
    bool operator==(const SoilLedger &) const = default;
};
struct GeometrySnapshot {
    WorldId world;
    bool configured{};
    std::uint64_t geometry_revision{}, parcels{}, indexed_entries{}, cached_bricks{}, dirty_bricks{};
    GeometryConfig config;
    SoilLedger ledger;
};
// 5^3 samples including both faces of an 8-quantum brick at two-quantum spacing.
struct SdfBrick {
    PointQ key;
    std::uint64_t source_revision{};
    std::array<double, 125> distance_m{};
    bool operator==(const SdfBrick &) const = default;
};
struct Route3D {
    WorldId world;
    std::uint64_t geometry_revision{};
    std::int32_t half_extent_q{};
    bool found{}, budget_exhausted{};
    std::uint64_t examined{};
    std::vector<PointQ> points = std::vector<PointQ>(0);
};
// A disposable local graph edge, identified by its endpoints and source revision.
// The entire swept body envelope has been proved empty, not inferred from SDF samples.
struct Portal3D {
    WorldId world;
    std::uint64_t geometry_revision{};
    PointQ from, to;
    std::int32_t half_extent_q{};
    bool operator==(const Portal3D &) const = default;
};
struct Neighborhood {
    std::vector<AntRef> ants = std::vector<AntRef>(0);
    std::vector<FoodRef> food = std::vector<FoodRef>(0);
    std::uint64_t candidates_examined{};
};
struct ExcavatorState {
    bool enabled{};
    std::uint64_t decisions{}, digs{}, carrying_moves{}, deliveries{};
    std::array<PointQ, 64> path{};
    std::uint32_t path_size{};
    ScheduledId wake, action;
    bool operator==(const ExcavatorState &) const = default;
};
} // namespace antworld
