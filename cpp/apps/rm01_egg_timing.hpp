#pragma once

#include "antworld/core/world_runtime.hpp"

#include <array>
#include <charconv>
#include <limits>
#include <stdexcept>
#include <string_view>

namespace antworld::rm01 {
inline constexpr std::int64_t hour_ms = 3600000;
inline constexpr std::int64_t day_ms = 24 * hour_ms;
inline constexpr SimTime legacy_duration{2 * day_ms};

struct Profile {
    std::string_view id, population, condition, source, days, unit;
};

inline constexpr std::array profiles{
    Profile{"legacy", "unspecified", "S6.3.1 long-term control", "ENGINEERING_FIXTURE", "2", "d"},
    Profile{"borisovka", "Borisovka", "B06 Table 2 nominal 25 C, egg mean near 24.7 C",
            "10.1023/B:JOEY.0000033808.45455.75", "16.7", "d"},
    Profile{"st-petersburg", "St. Petersburg", "B06 Table 2 nominal 25 C, egg mean near 24.7 C",
            "10.1023/B:JOEY.0000033808.45455.75", "15.7", "d"},
};

inline const Profile& profile(std::string_view id) {
    for (const auto& row : profiles)
        if (row.id == id) return row;
    throw std::invalid_argument("unsupported egg clock profile");
}

inline std::uint64_t unsigned_integer(std::string_view value) {
    std::uint64_t result{};
    if (value.empty()) throw std::invalid_argument("expected an unsigned integer");
    const auto [end, error] = std::from_chars(value.data(), value.data() + value.size(), result);
    if (error == std::errc::result_out_of_range) throw std::overflow_error("integer overflow");
    if (error != std::errc{} || end != value.data() + value.size())
        throw std::invalid_argument("expected an unsigned integer");
    return result;
}

// The admitted rows report whole days or tenths of a day.
inline SimTime parse_days(std::string_view value, std::string_view unit) {
    if (unit != "d") throw std::invalid_argument("egg clock unit must be d");
    const auto dot = value.find('.');
    const auto whole = unsigned_integer(value.substr(0, dot));
    constexpr auto scale = static_cast<std::uint64_t>(day_ms);
    std::uint64_t part{};
    if (dot != std::string_view::npos) {
        const auto fraction = value.substr(dot + 1);
        if (fraction.size() != 1) throw std::invalid_argument("expected tenths of a day");
        part = unsigned_integer(fraction) * (scale / 10);
    }
    constexpr auto max_time = static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max());
    if (whole > (max_time - part) / scale) throw std::overflow_error("egg duration exceeds SimTime");
    const auto ms = whole * scale + part;
    if (!ms) throw std::invalid_argument("egg duration must be positive");
    return {static_cast<std::int64_t>(ms)};
}

inline SimTime resolve_egg_duration(const Profile& request) {
    const auto& source = profile(request.id);
    if (request.population != source.population || request.condition != source.condition || request.source != source.source)
        throw std::invalid_argument("egg clock provenance does not match the fixed reference row");
    const auto duration = parse_days(request.days, request.unit);
    if (duration != parse_days(source.days, source.unit))
        throw std::invalid_argument("egg duration does not match the fixed reference row");
    return duration;
}

// The remaining fields reproduce the frozen S6.3.1 default long-term arm.
inline PhysiologyConfig physiology_config(SimTime egg_duration) {
    PhysiologyConfig config;
    config.absorption_period = {6 * hour_ms};
    config.behavior_interval = {6 * hour_ms};
    config.water_loss_period = {hour_ms};
    config.egg_duration = egg_duration;
    config.larva_duration = {3 * day_ms};
    config.pupa_duration = {2 * day_ms};
    config.basal_nj_per_ms = 1;
    config.active_nj_per_ms = 1;
    return config;
}

inline PhysiologySeed original_egg_budget() {
    const ReproductionConfig reproduction;
    return {{}, reproduction.egg_energy_nj, reproduction.egg_water_ug, reproduction.egg_protein_ug};
}

inline void enable_seeded_egg(WorldRuntime& world, AntRef egg, const PhysiologySeed& budget, const Profile& request) {
    const auto config = physiology_config(resolve_egg_duration(request));
    world.enable_physiology(egg, budget, config);
}
} // namespace antworld::rm01
