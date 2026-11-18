#pragma once
#include "care_internal.hpp"

namespace antworld::detail {
// ENGINEERING_FIXTURE. A floor layer reserves a common envelope for growth.
inline constexpr double brood_pitch_m=0.00075;
inline constexpr double brood_adjacency_m=0.0011;

inline std::int32_t brood_half(const GeometryConfig& g) {
    return std::max(g.body_half_q,static_cast<std::int32_t>(std::ceil(brood_pitch_m/(2*g.quantum_m))));
}

inline PositionM below_brood(PositionM site,const GeometryConfig& g,bool sealed = false) {
    // The fine chamber keeps the stepping plane at one loaded-body half
    // width above the floor. Test inside the supporting material.
    site.y-=static_cast<double>(sealed?g.loaded_half_q+1:brood_half(g)+2)*g.quantum_m;
    return site;
}

inline bool intersects_brood(PositionM from, PositionM to, PositionM occupant) {
    // Sweep the center against the open exclusion cube of two brood envelopes.
    // A shared face is legal. The margin is arithmetic only.
    const auto radius=brood_pitch_m-arithmetic_margin(position_scale(from,to),brood_pitch_m);
    double enter=0, exit=1;
    for (auto axis : {&PositionM::x,&PositionM::y,&PositionM::z}) {
        const auto a=from.*axis-occupant.*axis;
        const auto d=to.*axis-from.*axis;
        if (d==0) {
            if (std::abs(a)>=radius) return false;
        } else {
            const auto t0=(-radius-a)/d, t1=(radius-a)/d;
            enter=std::max(enter,std::min(t0,t1));
            exit=std::min(exit,std::max(t0,t1));
            if (enter>=exit) return false;
        }
    }
    return true;
}

template<class Clear,class Free,class Neighbors>
std::optional<PositionM> pick_egg_site(PositionM mother,const WorldConfig& world,
                                       Clear clear,Free free,Neighbors neighbors,
                                       std::optional<PositionM> nursery = {}) {
    if (nursery) {
        // The foundress faces the familiar nursery during laying. Search the
        // local posterior sector on a 0.125 mm lattice. Brood envelopes still
        // reserve space for later growth.
        constexpr double increment=.000125;
        const auto dx=mother.x-nursery->x, dz=mother.z-nursery->z;
        const bool along_x=std::abs(dx)>=std::abs(dz);
        const auto sign=(along_x?dx:dz)<0 ? -1 : 1;
        for (int rear=9;rear<=16;++rear) for (int offset=0;offset<=12;++offset) {
            const auto lateral=(offset%2?-1:1)*((offset+1)/2)*increment;
            const auto displacement=rear*sign*increment;
            const PositionM site{mother.x+(along_x?displacement:lateral),mother.y,
                                 mother.z+(along_x?lateral:displacement)};
            if (inside(site,world) && clear(mother,site) && free(site)) return site;
        }
        return {};
    }
    std::optional<PositionM> best;
    std::size_t best_neighbors{};
    int best_distance{};
    for (int x=-2;x<=2;++x) for (int z=-2;z<=2;++z) {
        const auto ring=x*x+z*z;
        if (ring<2) continue; // Keep the new brood outside the foundress's center.
        const PositionM site{mother.x+x*brood_pitch_m,mother.y,mother.z+z*brood_pitch_m};
        if (!within_contact(mother,site,world) || !clear(mother,site) || !free(site)) continue;
        const auto adjacent=neighbors(site);
        if (!best || adjacent>best_neighbors || (adjacent==best_neighbors && ring<best_distance)) {
            best=site; best_neighbors=adjacent; best_distance=ring;
        }
    }
    return best;
}
} // namespace antworld::detail
