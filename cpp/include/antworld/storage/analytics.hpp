#pragma once
#include "antworld/core/world_runtime.hpp"
#include <string_view>

namespace antworld::storage {
enum class Metric : std::uint32_t {
    Alive,
    WorkerAlive,
    QueenAlive,
    MaleAlive,
    Egg,
    Larva,
    Pupa,
    DeadRetained,
    CargoCarbs,
    CargoProtein,
    CargoWater,
    CargoOther,
    NestCarbs,
    NestProtein,
    NestWater,
    NestOther,
    CropCarbs,
    CropProtein,
    CropWater,
    CropOther,
    BodyEnergy,
    Hydration,
    TissueProtein,
    OxidizedCarbs,
    LostWater,
    DissipatedEnergy,
    PhysiologyIndividuals,
    Paused,
    Rest,
    Nurse,
    Forage,
    Excavate,
    BehaviorUnknown,
    AvailableCarbs,
    AvailableProtein,
    AvailableWater,
    AvailableOther,
    SoilRemaining,
    SoilCarried,
    SoilDeposited,
    VoidVolume,
    GeometryEdits,
    Seeded,
    Emerged,
    Deaths,
    CollectedCarbs,
    CollectedProtein,
    CollectedWater,
    DeliveredCarbs,
    DeliveredProtein,
    DeliveredWater,
    MetabolizedCarbs,
    Trophallaxis,
    ExcavatedDry,
    ExcavatedWater,
    FilledDry,
    FilledWater,
    Moves,
    Rejected,
    BehaviorChanges,
    Born,
    RecycledProtein,
    ReleasedCarbs,
    ReleasedProtein,
    ReleasedWater,
    ReserveCarbs,
    ReserveProtein,
    ReserveWater,
    ReserveOther,
    Count
};
enum class MetricKind { Gauge, Flow };
struct MetricDefinition {
    Metric id;
    std::string_view name, unit, definition;
    MetricKind kind;
};
inline constexpr std::uint32_t metric_version = 1;
const MetricDefinition &metric_definition(Metric);
std::span<const MetricDefinition> metric_definitions();
struct MetricValue {
    // Owner 0 means world; other values are ColonyId, qualified by the enclosing world.
    ColonyId owner;
    Metric metric{};
    std::uint64_t value{};
    bool operator==(const MetricValue &) const = default;
};
struct Observation {
    WorldId world;
    SimTime time;
    std::uint64_t revision{};
    EventId cursor;
    double geometry_quantum_m{};
    std::vector<MetricValue> values = std::vector<MetricValue>(0);
};
Observation observe(const WorldRuntime &);
std::vector<MetricValue> contributions(const WorldEvent &, const GeometrySnapshot &,
                                       const GeometryEdit *edit = nullptr);
std::uint64_t checked_add(std::uint64_t, std::uint64_t);
struct MetricPoint {
    SimTime time;
    std::uint64_t generation{}, revision{}, value{};
    EventId cursor;
};
struct MetricBucket {
    SimTime begin, end;
    std::uint64_t samples{}, sum{}, minimum{}, maximum{}, last{};
    EventId first_event, last_event;
    // Sample-weighted, not time-weighted. No samples means no observation.
    [[nodiscard]] double mean() const {
        return samples ? static_cast<double>(sum) / static_cast<double>(samples) : 0;
    }
};
} // namespace antworld::storage
