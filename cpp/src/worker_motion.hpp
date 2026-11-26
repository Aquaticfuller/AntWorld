#pragma once

#include "ecological_internal.hpp"
#include "physiology_internal.hpp"
#include "geometry_internal.hpp"

namespace antworld::detail {
bool center_sweep_clears(PositionM from, PositionM to, PositionM stationary, double width);
bool anatomy_turn_clears(const BodyPose&, std::uint8_t previous, std::uint8_t next, const BodyPose& obstacle);

inline bool uses_floor_body_clearance(const auto& s, const AntState& ant, PositionM to, std::int32_t half) {
    return confirmed_meal_routes(s) && founding_nutrition(s)>=FoundingNutrition::StationaryBodyClearance && s.surface &&
           ant.position.y<s.surface->config.origin_m.y && to.y==ant.position.y &&
           half==s.geometry->config.body_half_q &&
           !(s.care.contains(ant.id) && s.care.at(ant.id).carrying_brood);
}

inline std::optional<PointQ> nearest_grid_point(PositionM p,const GeometryConfig& g,bool include_height=false) {
    const auto snap=[&](double value,double origin) {
        return origin+std::round((value-origin)/g.quantum_m)*g.quantum_m;
    };
    return quantized({snap(p.x,g.origin_m.x),include_height?snap(p.y,g.origin_m.y):p.y,snap(p.z,g.origin_m.z)},g);
}
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
std::uint8_t body_travel_heading(const GeometryView&,const AntState&,PositionM,std::uint8_t previous,
                                 bool alignment=false,double alignment_m=.00019);
inline bool sideways_feeding(const auto& s,Caste caste) {
    return founding_nutrition(s)==FoundingNutrition::FeedingStance || (founder_wick_route(s) && caste==Caste::Queen);
}
inline bool feeding_approach(const auto& s, CareAct act, Caste caste) {
    return worked_exit(s) && (act==CareAct::ApproachNestmate || (sideways_feeding(s,caste) && act==CareAct::DepotApproach));
}
inline double feeding_alignment_m(const auto& s,Caste caste) { return sideways_feeding(s,caste) ? .00051 : .00019; }
inline std::uint8_t segment_heading(const auto& s,EntityId id,PositionM from,PositionM to,bool alignment_probe=false) {
    if (anatomical_nest(s)) {
        const auto previous=std::max<std::uint8_t>(1,actor_facing(s,id));
        if (s.care.contains(id) && s.care.at(id).carrying_brood) return previous;
        auto ant=s.ants.get(s.ants.index.at(id));
        ant.position=from;
        const auto care=s.care.find(id);
        const bool approaching=care!=s.care.end() && care->second.enabled &&
            feeding_approach(s,care->second.act,ant.caste) && care->second.destination==to;
        return body_travel_heading(geometry_view(s,RuntimeLimits{}),ant,to,previous,alignment_probe || approaching,
                                   feeding_alignment_m(s,ant.caste));
    }
    return movement_facing(from,to);
}

inline SimTime with_worker_turn(const auto& s,EntityId id,PositionM from,PositionM to,SimTime translation) {
    if (!worker_motor(s) || from==to || !s.autonomy.contains(id)) return translation;
    return after(translation,turn_ms(actor_facing(s,id),segment_heading(s,id,from,to)));
}

inline std::uint64_t motion_evidence(std::int64_t duration,std::int64_t turn,std::uint8_t facing=0) {
    return (static_cast<std::uint64_t>(duration)<<32) | (static_cast<std::uint64_t>(facing)<<16) |
        static_cast<std::uint32_t>(turn);
}
inline std::uint8_t historical_heading(std::uint64_t evidence,PositionM from,PositionM to) {
    const auto facing=static_cast<std::uint8_t>((evidence>>16)&0xff);
    return facing?facing:movement_facing(from,to);
}
} // namespace antworld::detail
