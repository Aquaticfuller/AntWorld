#pragma once
#include "care_internal.hpp"

namespace antworld::detail {
// ENGINEERING_FIXTURE. A floor layer reserves enough room for later growth.
// Stage widths are display/shape proxies; competition uses the larger envelope.
inline constexpr double brood_pitch_m=0.00075;
inline constexpr double brood_adjacency_m=0.0011;
inline constexpr std::array<double,3> brood_width_m{0.00045,0.00060,0.00070};

inline std::int32_t brood_half(const GeometryConfig& g) {
    return std::max(g.body_half_q,static_cast<std::int32_t>(std::ceil(brood_pitch_m/(2*g.quantum_m))));
}

inline PositionM below_brood(PositionM site,const GeometryConfig& g) {
    site.y-=static_cast<double>(brood_half(g)+2)*g.quantum_m;
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
                                       Clear clear,Free free,Neighbors neighbors) {
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
