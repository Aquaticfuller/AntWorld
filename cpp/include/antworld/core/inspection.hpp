#pragma once
#include "antworld/core/types.hpp"
#include <vector>

namespace antworld::inspection {
// Host-only observer evidence, never an authoritative fact or behavioral input.
// The caller discards records from a failed AdvanceTo; no callback enters Core.
struct Decision {
  std::uint64_t time_ms{}, source{}, actor{}, context{}, behavior{}, choice{},
      recipient{};
  std::uint64_t candidates{}, sampled_queen{}, reachable_queen{}, queen_alive{};
  std::uint64_t queen_energy_nj{}, queen_water_ug{}, queen_crop_carbs_ug{},
      queen_crop_protein_ug{}, queen_crop_water_ug{};
  std::uint64_t signal_carbs_ug{}, signal_protein_ug{}, signal_water_ug{};
  std::uint64_t donor_energy_nj{}, donor_water_ug{}, donor_crop_carbs_ug{},
      donor_crop_protein_ug{}, donor_crop_water_ug{};
  std::uint64_t donor_urgent{}, owns_journey{}, at_depot{}, hold_elapsed_ms{};
};
struct Target {
  WorldId world;
  EntityId queen;
  std::vector<Decision> *output{};
};
inline thread_local Target target;
class Scope {
  Target previous;

public:
  Scope(WorldId world, EntityId queen, std::vector<Decision> &out)
      : previous(target) {
    target = {world, queen, &out};
  }
  ~Scope() { target = previous; }
  Scope(const Scope &) = delete;
  Scope &operator=(const Scope &) = delete;
};
} // namespace antworld::inspection
