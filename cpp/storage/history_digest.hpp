#pragma once
#include <array>
#include <cstdint>
#include <span>

namespace antworld::storage::detail {
using Digest = std::array<std::uint8_t,32>;
[[nodiscard]] Digest sha256(std::span<const std::uint8_t> first,
                            std::span<const std::uint8_t> second = {});
} // namespace antworld::storage::detail
