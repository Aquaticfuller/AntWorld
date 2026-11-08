#pragma once
#include "antworld/core/physiology.hpp"
#include <vector>

namespace antworld {
// ENGINEERING_FIXTURE: these controls do not claim calibrated Lasius niger sensing or task rates.
struct SocialConfig {
    bool demand_sensitive{true}, bounded_contacts{true}, exchange_enabled{true};
    std::uint32_t encounter_budget{16};
    SimTime decision_interval{5000}, minimum_program_time{10000};
    std::uint32_t rest_weight{4}, forage_weight{8}, nurse_weight{12}, excavate_weight{4};
    bool operator==(const SocialConfig&) const = default;
};
struct ContactSample {
    std::vector<AntRef> ants = std::vector<AntRef>(0);
    std::uint64_t candidates_examined{}, bucket_queries{}, tree_visits{};
};
struct ContactWork {
    std::uint64_t decisions{}, candidates_examined{}, bucket_queries{}, tree_visits{}, maximum_candidates{};
    bool operator==(const ContactWork&) const = default;
};
} // namespace antworld
