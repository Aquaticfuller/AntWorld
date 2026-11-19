#pragma once

#include "antworld/core/body.hpp"
#include "geometry_internal.hpp"
#include "worker_motion.hpp"

namespace antworld::detail {
// ENGINEERING_FIXTURE. Adult length is anchored to Collingwood (1979),
// L. niger pp. 99–100. Segment proportions, contact and clearance are proxies.
inline constexpr std::array<BodySegment,3> queen_segments{{
    { .00315,{.00110,.00068,.00079}},
    { .00070,{.00165,.00095,.00104}},
    {-.00208,{.00217,.00095,.00124}}
}};
inline constexpr std::array<BodySegment,3> worker_segments{{
    { .00132,{.00048,.00032,.00039}},
    { .00036,{.00062,.00033,.00032}},
    {-.00089,{.00091,.00040,.00049}}
}};
inline constexpr std::array<PositionM,3> brood_radii{{
    {.00028,.00015,.00017}, {.00045,.00024,.00029}, {.00082,.00031,.00035}
}};
inline constexpr double micro_step_m=.0000625;
inline constexpr PositionM floor_normal{0,1,0};
inline constexpr std::array<PositionM,6> normals{{
    floor_normal,{1,0,0},{-1,0,0},{0,0,1},{0,0,-1},{0,-1,0}
}};
inline constexpr double compass_diagonal=0.7071067811865476;
inline constexpr std::array<PositionM,10> headings{{
    {1,0,0},{compass_diagonal,0,compass_diagonal},{0,0,1},{-compass_diagonal,0,compass_diagonal},{-1,0,0},
    {-compass_diagonal,0,-compass_diagonal},{0,0,-1},{compass_diagonal,0,-compass_diagonal},{0,1,0},{0,-1,0}
}};
inline PositionM scale(PositionM v,double n) { return {v.x*n,v.y*n,v.z*n}; }
inline double dot(PositionM a,PositionM b) { return (a.x*b.x+a.y*b.y)+a.z*b.z; }
inline PositionM cross(PositionM a,PositionM b) {
    return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};
}
inline PositionM tangent(PositionM heading,PositionM normal) {
    const auto v=translated(heading,scale(normal,-dot(heading,normal)));
    const auto magnitude=std::sqrt(dot(v,v));
    return magnitude>.0001?scale(v,1/magnitude):normal.y!=0?PositionM{1,0,0}:floor_normal;
}
inline PositionM body_heading(std::uint8_t heading) { return headings[heading?heading-1:0]; }
inline PositionM brood_half_axes(LifeStage stage) {
    return brood_radii[static_cast<unsigned>(stage)]; // Only for living brood.
}
inline BodyPose body_pose(const AntState& ant,std::uint8_t facing,PositionM up) {
    const auto forward=tangent(body_heading(facing),up);
    if (ant.stage!=LifeStage::Adult) {
        return {ant.position,forward,up,ant.position,ant.position,
                {{BodySegment{0,brood_half_axes(ant.stage)},{},{}}},1};
    }
    const auto& parts=ant.caste==Caste::Queen?queen_segments:worker_segments;
    return {ant.position,forward,up,
            translated(ant.position,scale(forward,parts.front().forward_offset_m+parts.front().half_axes_m.x)),
            translated(ant.position,scale(forward,parts.back().forward_offset_m-parts.back().half_axes_m.x)),parts,3};
}
inline PositionM lobe_center(const BodyPose& pose,const BodySegment& part) {
    return translated(pose.center_m,scale(pose.forward,part.forward_offset_m));
}
inline PositionM lobe_extents(const BodyPose& pose,const BodySegment& part) {
    const auto lateral=cross(pose.forward,pose.up);
    const auto half=part.half_axes_m;
    const auto extent=[&](double f,double u,double l) {
        return std::sqrt((f*half.x)*(f*half.x)+(u*half.y)*(u*half.y)+(l*half.z)*(l*half.z));
    };
    return {extent(pose.forward.x,pose.up.x,lateral.x),extent(pose.forward.y,pose.up.y,lateral.y),
            extent(pose.forward.z,pose.up.z,lateral.z)};
}
inline bool substrate_clear(const GeometryView& view,const BodyPose& pose,PositionM to) {
    const auto delta=displacement(to,pose.center_m);
    for (unsigned i=0;i<pose.segment_count;++i) {
        const auto& part=pose.segments[i];
        const auto center=lobe_center(pose,part);
        if (!continuous_box_clear(view,center,translated(center,delta),lobe_extents(pose,part))) return false;
    }
    return true;
}
inline bool physical_overlap(const BodyPose& a,const BodyPose& b) {
    for (unsigned i=0;i<a.segment_count;++i) for (unsigned j=0;j<b.segment_count;++j) {
        const auto p=lobe_center(a,a.segments[i]),q=lobe_center(b,b.segments[j]);
        const auto span=translated(lobe_extents(a,a.segments[i]),lobe_extents(b,b.segments[j]));
        if (std::abs(p.x-q.x)<span.x && std::abs(p.y-q.y)<span.y && std::abs(p.z-q.z)<span.z) return true;
    }
    return false;
}
inline std::optional<PositionM> support_normal(const GeometryView& view,PositionM center,
                                              PositionM heading,double reach) {
    for (const auto normal:normals) {
        if (std::abs(dot(heading,normal))>.999) continue;
        const auto anchor=translated(center,scale(normal,-reach));
        if (!continuous_clear(view,anchor,anchor,0)) return normal;
        if (std::abs(heading.y)>.999) {
            // The body center can pass the lip while the front or rear pair
            // of legs is still in reach of the vertical substrate.
            for (const auto step:{-.0012,-.0006,.0006,.0012}) {
                const auto foot=translated(anchor,scale(heading,step));
                if (!continuous_clear(view,foot,foot,0)) return normal;
            }
        }
    }
    return {};
}
inline PositionM attachment(const GeometryView& view,const AntState& ant,std::uint8_t facing) {
    if (ant.stage!=LifeStage::Adult) return floor_normal;
    return support_normal(view,ant.position,body_heading(facing),.00125).value_or(floor_normal);
}
inline bool anatomy_sweep(const GeometryView& view,AntState ant,PositionM to,std::uint8_t previous,
                          std::uint8_t heading) {
    const auto original=body_pose(ant,previous,attachment(view,ant,previous));
    if (to==ant.position) return substrate_clear(view,original,to);
    const auto forward=body_heading(heading);
    const auto start_up=support_normal(view,ant.position,forward,.00125);
    const auto end_up=support_normal(view,to,forward,.00125);
    const auto ground=physical(view.definition.config.initial_solid.max,view.definition.config).y;
    if (std::max(ant.position.y,to.y)>ground+.00125) return false;
    const auto delta=displacement(to,ant.position);
    if (std::min(ant.position.y,to.y)<ground) {
        const auto steps=static_cast<int>(std::ceil(distance(ant.position,to)/.00025));
        if (steps>128) return false;
        // Underground motion stays within leg reach of material along its
        // path. Surface endpoints use the existing terrain raster rules.
        std::optional<PositionM> support;
        for (int i=0;i<=steps;++i) {
            const auto p=translated(ant.position,scale(delta,static_cast<double>(i)/steps));
            if (p.y>=ground) continue;
            const auto current=support_normal(view,p,forward,.00125);
            if (!current) return false;
            if (support && current!=support) {
                const auto previous_point=translated(p,scale(delta,-1.0/steps));
                const auto next_contact=translated(previous_point,scale(*current,-.00125));
                const auto old_contact=translated(p,scale(*support,-.00125));
                if (dot(*current,*support)!=0 || (continuous_clear(view,next_contact,next_contact,0) &&
                    continuous_clear(view,old_contact,old_contact,0))) return false;
            }
            support=current;
        }
    }
    const auto up=start_up.value_or(end_up.value_or(floor_normal));
    const auto pose=body_pose(ant,heading,up);
    if (!substrate_clear(view,pose,to)) return false;
    // Check each intermediate compass pose before translating. The orienting
    // body uses the same clearance lobes as a straight sweep.
    if (original.up==up && previous && previous<=8 && heading<=8) {
        const int clockwise=(int(heading)-previous+8)%8;
        const int step=clockwise<=4?1:-1;
        auto facing=previous;
        while (facing!=heading) {
            if (!substrate_clear(view,body_pose(ant,facing,up),ant.position)) return false;
            facing=static_cast<std::uint8_t>((int(facing)+step+7)%8+1);
        }
    } else if (!substrate_clear(view,original,ant.position)) return false;
    if (end_up && *end_up!=up) {
        ant.position=to;
        if (!substrate_clear(view,body_pose(ant,heading,*end_up),to)) return false;
    }
    return true;
}
inline PositionM snap_micro(PositionM p) {
    const auto axis=[](double value){return std::round(value/micro_step_m)*micro_step_m;};
    return {axis(p.x),axis(p.y),axis(p.z)};
}
inline bool mouth_reaches(const BodyPose& adult,PositionM brood_position,LifeStage stage) {
    const auto gap=displacement(brood_position,adult.mouth_m);
    // Small head/antenna excursion, including a downward reach from the
    // stepping plane. The obstacle ray is checked by the caller.
    return dot(gap,adult.forward)>=-.00012 &&
        within_distance(adult.mouth_m,brood_position,.00048+brood_half_axes(stage).z,true);
}
template<class Free>
std::optional<PositionM> posterior_egg_site(const GeometryView& view,const BodyPose& mother,
                                           const WorldConfig& world,Free free) {
    const auto lateral=cross(mother.forward,mother.up);
    const auto down=scale(mother.up,-.0005);
    for (int rear=6;rear<=26;rear+=2) for (int side=0;side<=24;++side) {
        const auto offset=micro_step_m*((side+1)/2)*(side%2?1:-1);
        const auto site=snap_micro(translated(mother.abdomen_tip_m,
            translated(down,translated(scale(mother.forward,-rear*micro_step_m),scale(lateral,offset)))));
        const auto support=translated(site,scale(mother.up,-.00065));
        if (inside(site,world) && !continuous_clear(view,support,support,0) &&
            continuous_box_clear(view,mother.abdomen_tip_m,site,brood_half_axes(LifeStage::Egg)) &&
            free(site)) return site;
    }
    return {};
}
} // namespace antworld::detail
