#pragma once

#include "antworld/core/types.hpp"
#include <string>
#include <string_view>

namespace antworld::app {
struct Scenario {
    WorldId world;
    std::uint64_t seed{};
    SimTime observation;
};
Scenario parse_scenario(std::string_view json);
std::uint64_t parse_unsigned(std::string_view text);
} // namespace antworld::app
