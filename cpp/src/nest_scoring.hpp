#pragma once

#include "geometry_internal.hpp"
#include "antworld/core/ecological_closure.hpp"
#include "antworld/core/behavior.hpp"
#include "antworld/core/rng.hpp"

namespace antworld::detail {
struct HexSite {
    std::int32_t column{}, row{}, level{};
    auto operator<=>(const HexSite&) const = default;
};

inline PointQ patch_center(BoxQ b) {
    return {b.min.x+(b.max.x-b.min.x)/2,b.min.y+(b.max.y-b.min.y)/2,b.min.z+(b.max.z-b.min.z)/2};
}

inline constexpr std::array<Cell,6> hex_neighbors{{{1,0},{0,1},{-1,1},{-1,0},{0,-1},{1,-1}}};

// A discrete triangular lattice overlays the voxel plane with a Voronoi hex
// per center. Pitch is two loaded half-extents. The 7/8 lattice aspect uses
// integer arithmetic on every platform. The layers align to the known depot.
inline PointQ hex_center(HexSite key,int pitch,int base_y) {
    return {pitch*key.column+pitch*key.row/2,base_y+pitch*key.level,floor_div(7*pitch*key.row,8)};
}

inline HexSite hex_site(PointQ p,int pitch,int base_y) {
    const auto row=floor_div(8*p.z,7*pitch);
    const auto level=floor_div(p.y-base_y+pitch/2,pitch);
    HexSite best{};
    int squared=INT32_MAX;
    for (int r=row-1;r<=row+1;++r) {
        const auto column=floor_div(p.x-pitch*r/2,pitch);
        for (int q=column;q<=column+1;++q) {
            const HexSite key{q,r,level};
            const auto center=hex_center(key,pitch,base_y);
            const auto dx=center.x-p.x,dz=center.z-p.z;
            const auto d=dx*dx+dz*dz;
            if (d<squared || (d==squared && key<best)) { best=key; squared=d; }
        }
    }
    return best;
}

inline int hex_open_neighbors(const GeometryView& view,HexSite cell,int pitch,int base_y) {
    int connected=0;
    for (const auto [q,r]:hex_neighbors)
        connected+=material_at(view,hex_center({cell.column+q,cell.row+r,cell.level},pitch,base_y))==Material::Void;
    return connected;
}

inline bool shaft_attachment(const GeometryView& view,PointQ p,int half) {
    for (const auto [x,z] : std::array<Cell,4>{{{1,0},{0,1},{-1,0},{0,-1}}}) {
        const PointQ contact{p.x+(x<0?-(half+1):half*x),p.y,p.z+(z<0?-(half+1):half*z)};
        if (material_at(view,contact)!=Material::Void) return true;
    }
    return false;
}

inline bool work_floor(const GeometryView& view,PointQ p,int half) {
    return material_at(view,{p.x,p.y-half-1,p.z})!=Material::Void;
}

inline int excavated_reinforcement(const GeometryView& view,PointQ p,SimTime now,int reach) {
    if (view.edits.empty()) return 0;
    const auto near=around(p,reach);
    const auto ids=relevant_edits(view,near);
    int credit=0;
    for (auto i=ids.rbegin();i!=ids.rend() && credit<8;++i) {
        const auto& edit=view.edits.at(*i);
        if (now.milliseconds-edit.time.milliseconds>2*3'600'000) break;
        if (edit.kind==SoilAction::Excavate && box_valid(intersection(edit.box,near))) ++credit;
    }
    return credit;
}

// ENGINEERING_FIXTURE weights. All candidates already arise from physical
// fronts or traversable portals. The hex lattice is a disposable query.
struct ExcavationFeatures { int openings{}, recent{}, roomy{}; };

inline ExcavationFeatures excavation_features(const GeometryView& view,NestScoring mode,
                                                PointQ target,SimTime now,int base_y) {
    const auto pitch=2*view.definition.config.loaded_half_q;
    const auto cell=hex_site(target,pitch,base_y);
    ExcavationFeatures result;
    result.openings=hex_open_neighbors(view,cell,pitch,base_y);
    if (mode>=NestScoring::Reinforcement) result.recent=excavated_reinforcement(view,target,now,pitch);
    if (mode==NestScoring::SpatialDemand) for (const auto [x,z]:hex_neighbors) {
        const HexSite adjacent{cell.column+x,cell.row+z,cell.level};
        const auto center=hex_center(adjacent,pitch,base_y);
        if (material_at(view,center)==Material::Void &&
            hex_open_neighbors(view,adjacent,pitch,base_y)>=4) ++result.roomy;
    }
    return result;
}

inline std::uint64_t digging_weight(ExcavationFeatures features,NestScoring mode,
                                    PointQ target,PointQ current,const ExcavatorState& trip,
                                    std::size_t local_bodies,bool moving) {
    const auto [openings,recent,roomy]=features;
    const int perimeter_delta=6-2*openings;
    int weight=24-2*perimeter_delta;
    if (mode>=NestScoring::Reinforcement) {
        weight+=recent*(openings<=2?7:3);
        if (trip.path_size>1) {
            const auto from=trip.path[trip.path_size-2];
            const auto projection=(target.x-current.x)*(current.x-from.x)+
                                  (target.y-current.y)*(current.y-from.y)+
                                  (target.z-current.z)*(current.z-from.z);
            if (projection>0) weight+=(moving?24:16)+recent*(openings<=2?9:2);
        }
    }
    if (mode==NestScoring::SpatialDemand) {
        // Recent activity near an undersupplied tip favours widening once
        // enough local workers arrive. Existing wide cores inhibit new nearby
        // pockets. Distance uses actually visited unit steps of this trip.
        weight+=static_cast<int>(std::min<std::size_t>(local_bodies,16))*(roomy<=1 && openings>=2?6:1);
        weight-=8*roomy+static_cast<int>(trip.path_size)/3;
    }
    if (target.y!=current.y && moving) weight-=10;
    return static_cast<std::uint64_t>(std::max(1,weight));
}
} // namespace antworld::detail
