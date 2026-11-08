#pragma once
#include "antworld/core/rng.hpp"
#include "antworld/core/behavior.hpp"

namespace antworld::detail {
// Domain-separated seed -> identity -> decision mixing. Direct seed XOR actor
// would let adjacent seeds merely permute an even group of worker streams.
inline Rng individual_rng(std::uint64_t seed, EntityId actor, std::uint64_t decision) {
    Rng world(seed ^ UINT64_C(0x53325f4245484156));
    Rng identity(world.next() ^ actor.value);
    return Rng(identity.next() ^ decision);
}
inline Direction initial_heading(std::uint64_t seed, EntityId actor) {
    auto rng = individual_rng(seed, actor, UINT64_MAX);
    return static_cast<Direction>(rng.next() % 4);
}
} // namespace antworld::detail
