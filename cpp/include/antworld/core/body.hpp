#pragma once

#include "antworld/core/entities.hpp"
#include <array>

namespace antworld {
// Half axes in the forward, surface-normal and lateral directions, in metres.
struct BodySegment {
    double forward_offset_m;
    PositionM half_axes_m;
};

struct BodyPose {
    PositionM center_m, forward, up, mouth_m, abdomen_tip_m;
    std::array<BodySegment,3> segments;
    unsigned segment_count;
};
} // namespace antworld
