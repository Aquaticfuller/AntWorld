#pragma once

#include <cstdint>
#include <string_view>

namespace antworld {
// SplitMix64 by Sebastiano Vigna (2015), public-domain reference:
// https://prng.di.unimi.it/splitmix64.c
// This small S0 stream is not a biological model or cryptographic generator.
class Rng {
public:
    static constexpr std::string_view version = "splitmix64-v1";
    explicit Rng(std::uint64_t state) : state_(state) {}
    [[nodiscard]] std::uint64_t state() const noexcept { return state_; }
    std::uint64_t next() noexcept {
        auto z = (state_ += UINT64_C(0x9e3779b97f4a7c15));
        z = (z ^ (z >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
        z = (z ^ (z >> 27)) * UINT64_C(0x94d049bb133111eb);
        return z ^ (z >> 31);
    }
private:
    std::uint64_t state_;
};
} // namespace antworld
