#pragma once
#include "antworld/core/event.hpp"
#include <bit>
#include <cstring>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

namespace antworld::detail {
static_assert(sizeof(double) == 8 && std::numeric_limits<double>::is_iec559, "checkpoint requires IEEE-754 binary64");
inline void ensure(bool condition, const char* message) { if (!condition) throw std::invalid_argument(message); }
inline constexpr auto fnv_offset=UINT64_C(14695981039346656037);
inline std::uint64_t hash_byte(std::uint64_t state,std::uint8_t byte) {
    return (state^byte)*UINT64_C(1099511628211);
}
struct Writer {
    std::vector<std::uint8_t> bytes;
    std::size_t limit;
    std::uint64_t* streamed_hash;
    std::size_t streamed_size{};
    explicit Writer(std::size_t byte_limit = std::numeric_limits<std::size_t>::max(),std::uint64_t* digest=nullptr)
        :bytes(0),limit(byte_limit),streamed_hash(digest) {}
    void put(std::uint64_t v, unsigned width = 8) {
        if (streamed_hash) {
            if (width > limit-streamed_size) throw std::length_error("checkpoint byte host budget exceeded");
            streamed_size+=width;
            for (unsigned i=0;i<width;++i) {
                *streamed_hash=hash_byte(*streamed_hash,static_cast<std::uint8_t>(v&255));
                v>>=8;
            }
            return;
        }
        if (width > limit-bytes.size()) throw std::length_error("checkpoint byte host budget exceeded");
        for (unsigned i = 0; i < width; ++i) { bytes.push_back(static_cast<std::uint8_t>(v & 255)); v >>= 8; }
    }
    void time(SimTime t) { put(static_cast<std::uint64_t>(t.milliseconds)); }
    void real(double v) { put(std::bit_cast<std::uint64_t>(v)); }
    void position(PositionM p) { real(p.x); real(p.y); real(p.z); }
    void mass(FoodMass f) { for (const auto v : f.components()) put(v); }
    void cell(Cell c) { put(static_cast<std::uint32_t>(c.x), 4); put(static_cast<std::uint32_t>(c.z), 4); }
    void key(EventKey k) { time(k.time); put(static_cast<std::uint32_t>(k.phase), 4); put(k.priority, 4); put(k.tie); put(k.sequence); }
};
struct Reader {
    std::span<const std::uint8_t> bytes;
    std::size_t cursor{};
    std::uint64_t get(unsigned width = 8) {
        if (width > bytes.size()-cursor) throw std::invalid_argument("truncated checkpoint");
        if constexpr (std::endian::native == std::endian::little) {
            if (width == sizeof(std::uint64_t)) {
                std::uint64_t word;
                std::memcpy(&word,bytes.data()+cursor,sizeof(word));
                cursor += sizeof(word);
                return word;
            }
            if (width == sizeof(std::uint32_t)) {
                std::uint32_t word;
                std::memcpy(&word,bytes.data()+cursor,sizeof(word));
                cursor += sizeof(word);
                return word;
            }
        }
        std::uint64_t result = 0;
        for (unsigned i = 0; i < width; ++i) result |= std::uint64_t{bytes[cursor++]} << (8*i);
        return result;
    }
    bool flag() { const auto b = get(1); ensure(b <= 1, "invalid boolean"); return b != 0; }
    SimTime time() { const auto n = get(); ensure(n <= static_cast<std::uint64_t>(INT64_MAX), "invalid checkpoint time"); return {static_cast<std::int64_t>(n)}; }
    double real() { return std::bit_cast<double>(get()); }
    PositionM position() { return {real(), real(), real()}; }
    FoodMass mass() { FoodMass f{get(), get(), get(), get()}; (void)f.total_ug(); return f; }
    Cell cell() {
        const auto x = get(4), z = get(4); ensure(x <= INT32_MAX && z <= INT32_MAX, "invalid cell coordinate");
        return {static_cast<std::int32_t>(x), static_cast<std::int32_t>(z)};
    }
    EventKey key() { return {time(), static_cast<Phase>(get(4)), static_cast<std::uint32_t>(get(4)), get(), get()}; }
    std::size_t count(std::size_t limit, std::size_t record_bytes) {
        const auto n = get();
        ensure(n <= limit && n <= (bytes.size()-cursor)/record_bytes, "checkpoint record host budget or length exceeded");
        return static_cast<std::size_t>(n);
    }
};
} // namespace antworld::detail
