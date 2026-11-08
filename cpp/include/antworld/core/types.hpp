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
std::string hex64(std::uint64_t value);
} // namespace antworld
