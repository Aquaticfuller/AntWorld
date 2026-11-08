#pragma once
#include "antworld/core/entities.hpp"

namespace antworld {
struct CommandId {
    std::uint64_t high{}, low{};
    auto operator<=>(const CommandId &) const = default;
};
struct PlaceFoodCommand {
    WorldId world;
    CommandId id;
    PositionM position;
    FoodMass mass;
    bool operator==(const PlaceFoodCommand &) const = default;
};
struct CommandReceipt {
    PlaceFoodCommand command;
    ResourceId resource;
    EventId event;
    SimTime applied_at;
    std::uint64_t revision{};
    bool operator==(const CommandReceipt &) const = default;
};
} // namespace antworld
