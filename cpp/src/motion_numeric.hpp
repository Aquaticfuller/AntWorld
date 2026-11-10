#pragma once
#include "antworld/core/entities.hpp"
#include <algorithm>
#include <cmath>
#include <limits>

namespace antworld::detail {
inline PositionM displacement(PositionM a,PositionM b) {
    return {a.x-b.x,a.y-b.y,a.z-b.z};
}
inline PositionM translated(PositionM position,PositionM offset) {
    return {position.x+offset.x,position.y+offset.y,position.z+offset.z};
}
inline double distance(PositionM a,PositionM b) {
    return std::hypot(a.x-b.x,a.y-b.y,a.z-b.z);
}
inline double position_scale(PositionM a,PositionM b) {
    return std::max({std::abs(a.x),std::abs(a.y),std::abs(a.z),std::abs(b.x),std::abs(b.y),std::abs(b.z)});
}
inline double arithmetic_margin(double coordinate_scale,double reference_scale) {
    // Bound the numerical envelope even when absolute coordinates are very large.
    return std::min(0x1p-32*reference_scale,
                    8*std::numeric_limits<double>::epsilon()*std::max(coordinate_scale,reference_scale));
}
inline bool within_distance(PositionM a,PositionM b,double radius,bool continuous) {
    const auto d=distance(a,b);
    return d<=radius || (continuous && std::isfinite(d) &&
        d-radius<=arithmetic_margin(position_scale(a,b),radius));
}
inline bool within_contact(PositionM a,PositionM b,const WorldConfig& c) {
    return within_distance(a,b,c.contact_distance_m,c.continuous_spatial_motion);
}
inline double grid_coordinate(double value,double origin,double quantum) {
    const auto q=(value-origin)/quantum;
    const auto boundary=std::round(q);
    const auto margin=arithmetic_margin(std::max(std::abs(value),std::abs(origin)),quantum)/quantum;
    return std::abs(q-boundary)<=margin?boundary:q;
}
} // namespace antworld::detail
