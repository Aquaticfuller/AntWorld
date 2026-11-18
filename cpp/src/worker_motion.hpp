#pragma once

#include "ecological_internal.hpp"
#include "physiology_internal.hpp"

namespace antworld::detail {
// ENGINEERING_FIXTURE. A turn occupies time before the next swept translation.
inline constexpr std::int64_t compass_turn_ms = 40;
inline constexpr std::uint8_t facing_down = 10;

inline std::uint8_t movement_facing(PositionM from, PositionM to) {
    const auto dx=to.x-from.x, dy=to.y-from.y, dz=to.z-from.z;
    const auto x=std::abs(dx), z=std::abs(dz);
    if (std::abs(dy)>std::max(x,z)) return dy>0?9:10;
    if (2*z<x) return dx>0?1:5;
    if (2*x<z) return dz>0?3:7;
    if (dx>0) return dz>0?2:8;
    return dz>0?4:6;
}

inline std::int64_t turn_ms(std::uint8_t from,std::uint8_t to) {
    if (!from || from==to) return 0;
    if (from>8 || to>8) return (from>8 && to>8?4:2)*compass_turn_ms;
    const auto angle=std::abs(int(from)-int(to));
    return std::min(angle,8-angle)*compass_turn_ms;
}

inline std::uint8_t actor_facing(const auto& s,EntityId id) {
    const auto a=s.autonomy.find(id);
    return a!=s.autonomy.end()?a->second.facing:0;
}

inline bool motile_caste(const auto& s,Caste caste) {
    return caste==Caste::Worker || (sealed_chamber(s) && caste==Caste::Queen);
}

inline SimTime with_worker_turn(const auto& s,EntityId id,PositionM from,PositionM to,SimTime translation) {
    if (!worker_motor(s) || from==to || !s.autonomy.contains(id)) return translation;
    return after(translation,turn_ms(actor_facing(s,id),movement_facing(from,to)));
}

inline std::uint64_t motion_evidence(std::int64_t duration,std::int64_t turn) {
    return (static_cast<std::uint64_t>(duration)<<32) | static_cast<std::uint32_t>(turn);
}
} // namespace antworld::detail
