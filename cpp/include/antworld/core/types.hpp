#pragma once

#include <compare>
#include <cstdint>
#include <string>
#include <string_view>

namespace antworld {
template <typename Tag> struct Id {
    std::uint64_t value{};
    auto operator<=>(const Id&) const = default;
};
using EntityId = Id<struct EntityTag>;
using EventId = Id<struct EventTag>;
using ScheduledId = Id<struct ScheduledTag>;
using ColonyId = Id<struct ColonyTag>;
using ResourceId = Id<struct ResourceTag>;

struct WorldId {
    std::uint64_t high{}, low{};
    auto operator<=>(const WorldId&) const = default;
    static WorldId parse(std::string_view text);
    [[nodiscard]] std::string str() const;
};

struct SimTime {
    std::int64_t milliseconds{};
    auto operator<=>(const SimTime&) const = default;
};
template <typename T> struct WorldRef {
    WorldId world;
    T id;
    bool operator==(const WorldRef&) const = default;
};
using AntRef = WorldRef<EntityId>;
using ColonyRef = WorldRef<ColonyId>;
using FoodRef = WorldRef<ResourceId>;
std::string hex64(std::uint64_t value);
} // namespace antworld
