#include "brood_space.hpp"
#include "ecological_internal.hpp"

namespace antworld {
using namespace detail;
namespace {
template<class State>
std::vector<AntState> nearby_brood(const State& s,const RuntimeLimits& limits,PositionM from,PositionM to,double pad) {
    const auto lo=spatial_key({std::min(from.x,to.x)-pad,std::min(from.y,to.y)-pad,std::min(from.z,to.z)-pad});
    const auto hi=spatial_key({std::max(from.x,to.x)+pad,std::max(from.y,to.y)+pad,std::max(from.z,to.z)+pad});
    std::vector<AntState> result(0);
    for (const auto key : overlapping_bricks({lo,{hi.x+1,hi.y+1,hi.z+1}},1,limits.neighborhood_buckets)) {
        auto entry=s.spatial_index.lower_bound({key,0});
        while (entry!=s.spatial_index.end() && entry->first.first==key) {
            if (entry->second==1) {
                const auto ant=s.ants.get(s.ants.index.at(EntityId{entry->first.second}));
                if (brood(ant.stage)) result.push_back(ant);
            }
            ++entry;
        }
    }
    return result;
}
}

std::optional<PositionM> WorldRuntime::local_egg_site(const AntState& mother) const {
    const auto& s=*state_;
    if (!s.geometry || !spatially_clear(mother.position,mother.position,s.geometry->config.body_half_q)) return {};
    const auto& geometry=s.geometry->config;
    const auto view=geometry_view(s,limits_);
    const auto local=nearby_brood(s,limits_,mother.position,mother.position,2*brood_pitch_m+brood_adjacency_m);
    return pick_egg_site(mother.position,s.config,
        [&](PositionM a,PositionM b) {
            const auto below=below_brood(b,geometry);
            return spatially_clear(a,b,brood_half(geometry)) && !continuous_clear(view,below,below,0);
        },
        [&](PositionM b) {
            return std::none_of(local.begin(),local.end(),[&](const auto& ant) { return intersects_brood(b,b,ant.position); });
        },
        [&](PositionM b) {
            return static_cast<std::size_t>(std::count_if(local.begin(),local.end(),[&](const auto& ant) {
                return ant.colony==mother.colony && within_distance(b,ant.position,brood_adjacency_m,true) &&
                    spatially_clear(b,ant.position);
            }));
        });
}

bool WorldRuntime::clear_brood_space(EntityId id,PositionM from,PositionM to) const {
    const auto& s=*state_;
    if (!bounded_brood_space(s)) return true;
    const auto local=nearby_brood(s,limits_,from,to,brood_pitch_m);
    return std::none_of(local.begin(),local.end(),[&](const auto& ant) {
        return ant.id!=id && intersects_brood(from,to,ant.position);
    });
}

std::optional<PositionM> WorldRuntime::arrange_brood_site(const AntState& brood_ant,PositionM shelter) const {
    const auto& s=*state_;
    const auto& geometry=s.geometry->config;
    const auto view=geometry_view(s,limits_);
    const auto from=brood_ant.position;
    const auto local=nearby_brood(s,limits_,from,from,brood_adjacency_m+s.care_profile->arrangement_m);
    const auto neighbors=[&](PositionM site) {
        return std::count_if(local.begin(),local.end(),[&](const auto& ant) {
            return ant.id!=brood_ant.id && ant.colony==brood_ant.colony &&
                within_distance(site,ant.position,brood_adjacency_m,true) && spatially_clear(site,ant.position);
        });
    };
    const auto step=s.care_profile->arrangement_m;
    const auto current=neighbors(from);
    auto best_count=current;
    auto best_distance=distance(from,shelter);
    std::optional<PositionM> best;
    // Try only nearby displacements. A move may compact the pile or fill a gap
    // without converging every individual onto the same point.
    for (const auto& offset : std::array<PositionM,4>{{{step,0,0},{-step,0,0},{0,0,step},{0,0,-step}}}) {
        const auto to=translated(from,offset);
        const auto below=below_brood(to,geometry);
        if (!within_contact(to,shelter,s.config) || intersects_brood(to,to,shelter) ||
            !clear_care_segment(from,to,brood_half(geometry)) ||
            continuous_clear(view,below,below,0) || !clear_brood_space(brood_ant.id,from,to)) continue;
        const auto adjacent=neighbors(to);
        const auto distance_to_shelter=distance(to,shelter);
        if (adjacent>best_count || (adjacent==best_count && distance_to_shelter<best_distance)) {
            best=to; best_count=adjacent; best_distance=distance_to_shelter;
        }
    }
    return best;
}
} // namespace antworld
