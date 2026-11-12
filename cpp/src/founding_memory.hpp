#pragma once

#include "antworld/core/event.hpp"

namespace antworld::detail {
struct FoundingMealMemory {
    EntityId target;
    SimTime fed_at;
    EventId meal;
    bool operator==(const FoundingMealMemory&) const = default;
};

inline void update_founding_meal_memory(FoundingMealMemory& memory, EntityId founder, const WorldEvent& fact) {
    if (fact.actor == founder && fact.kind == FactKind::FoundingRation) {
        memory = {EntityId{fact.payload}, fact.time, fact.id};
        return;
    }
    if (!memory.target.value) return;
    if (fact.actor == founder && ((fact.kind == FactKind::AutonomyChanged && !fact.payload) ||
            (fact.kind == FactKind::CareTick &&
                (fact.random_value == static_cast<std::uint64_t>(FoundingCareWake::Expired) ||
                 fact.random_value == static_cast<std::uint64_t>(FoundingCareWake::Unavailable))) ||
            (fact.kind == FactKind::BiologicalObservation && fact.observation.phase == ObservationPhase::Interrupted &&
             fact.observation.act == CareAct::FeedBrood && fact.observation.target == memory.target))) memory = {};
    else if ((fact.kind == FactKind::AntDied && (fact.actor == founder || fact.actor == memory.target)) ||
             (fact.kind == FactKind::StageChanged && fact.actor == memory.target)) memory = {};
}
} // namespace antworld::detail
