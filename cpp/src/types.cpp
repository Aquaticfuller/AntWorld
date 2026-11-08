#include "antworld/core/types.hpp"

#include <stdexcept>

namespace antworld {
std::string hex64(std::uint64_t value) {
    constexpr auto digits = "0123456789abcdef";
    std::string result(16, '0');
    for (std::size_t i = 0; i < 16; ++i) {
        result[15 - i] = digits[value & 15];
        value >>= 4;
    }
    return result;
}
WorldId WorldId::parse(std::string_view text) {
    if (text.size() != 36) throw std::invalid_argument("world_id must be a UUID");
    WorldId result;
    std::size_t digits = 0;
    for (std::size_t i = 0; i < text.size(); ++i) {
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (text[i] != '-') throw std::invalid_argument("invalid UUID separator");
            continue;
        }
        const auto c = text[i];
        int value = -1;
        if (c >= '0' && c <= '9') value = c - '0';
        if (c >= 'a' && c <= 'f') value = c - 'a' + 10;
        if (c >= 'A' && c <= 'F') value = c - 'A' + 10;
        if (value < 0) throw std::invalid_argument("invalid UUID digit");
        auto& word = digits++ < 16 ? result.high : result.low;
        word = (word << 4) | static_cast<std::uint64_t>(value);
    }
    if (result == WorldId{}) throw std::invalid_argument("world_id must not be nil");
    return result;
}
std::string WorldId::str() const {
    const auto raw = hex64(high) + hex64(low);
    return raw.substr(0, 8) + '-' + raw.substr(8, 4) + '-' + raw.substr(12, 4)
        + '-' + raw.substr(16, 4) + '-' + raw.substr(20);
}
} // namespace antworld
