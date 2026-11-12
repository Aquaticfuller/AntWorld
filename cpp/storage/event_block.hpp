#pragma once
#include "antworld/core/event.hpp"
#include "history_digest.hpp"
#include <vector>

namespace antworld::storage::detail {
inline constexpr std::size_t block_records=4096;
inline constexpr std::size_t block_raw_limit=block_records*214;
inline constexpr std::size_t block_encoded_limit=block_raw_limit+4096;
enum class FactSchema : unsigned { Legacy = 1, Founding = 2, FoundingPersistence = 3 };
struct BlockHeader {
    WorldId world;
    EventId first,last;
    SimTime begin,end;
    std::size_t raw_bytes{},compressed_bytes{};
    Digest previous,digest;
    unsigned fact_schema{1};
};
struct EventBlock {
    BlockHeader header;
    std::vector<std::uint8_t> bytes;
};

[[nodiscard]] EventBlock seal_block(std::span<const WorldEvent>,const Digest& previous,FactSchema = FactSchema::Legacy);
[[nodiscard]] inline EventBlock seal_block(std::span<const WorldEvent> facts, const Digest& previous, bool founding) {
    return seal_block(facts, previous, founding ? FactSchema::Founding : FactSchema::Legacy);
}
[[nodiscard]] BlockHeader inspect_block(std::span<const std::uint8_t>);
[[nodiscard]] std::vector<WorldEvent> read_block(std::span<const std::uint8_t>,const BlockHeader&);
} // namespace antworld::storage::detail
