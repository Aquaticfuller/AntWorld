#include "founding_internal.hpp"
#include "ecological_internal.hpp"

namespace antworld {
using namespace detail;

void WorldRuntime::configure_ecological_closure(const EcologicalClosureConfig& config) {
    auto& s = *state_;
    validate_ecological_closure(config, s.config);
    if (s.ecological || s.m.now != SimTime{} || s.m.watermark || s.ants.size() || !s.foods.rows.empty())
        throw std::invalid_argument("ecological closure must precede the first ant or source");
    Transaction tx(s, limits_);
    s.ecological = config;
    bump(s.m.revision);
    tx.commit();
}

std::optional<EcologicalClosureConfig> WorldRuntime::ecological_closure() const {
    return state_->ecological;
}

void WorldRuntime::record_recruitment_cue(Transaction& tx, const WorldEvent& returned) {
    auto& s = *state_;
    if (!s.ecological || !s.ecological->recruitment || returned.kind != FactKind::FoodDelivered ||
        returned.transferred.carbs_ug < s.ecological->cue_minimum_carbs_ug ||
        !s.foragers.contains(returned.actor) || !s.foragers.at(returned.actor).enabled ||
        !s.foragers.at(returned.actor).collections) return;
    WorldEvent cue;
    cue.kind = FactKind::RecruitmentCue;
    cue.actor = returned.actor; cue.colony = returned.colony; cue.stage = returned.stage;
    cue.position = returned.position; cue.source = returned.source;
    cue.payload = s.m.next_event - 1;
    tx.set_recruitment_signal(cue.actor, {{s.m.next_event}, s.m.now, cue.position});
    tx.fact(cue);
}

void WorldRuntime::set_activity_work(Transaction& tx, EntityId actor, ScheduledId next) {
    auto& s = *state_;
    if (!timed_activity(s) || !s.physiology.contains(actor)) return;
    const auto previous = *s.physiology.at(actor).active_work;
    if (previous == next) return;
    if (previous.value && next.value) throw std::logic_error("overlapping paid work");
    const auto ant = s.ants.get(s.ants.index.at(actor));
    if (ant.stage != LifeStage::Adult) throw std::logic_error("paid work requires a living adult");
    synchronize_physiology(tx, actor);
    auto p = s.physiology.at(actor);
    p.active_work = next;
    tx.physiology.set(actor, p);
    if (p.config.active_nj_per_ms && p.body_energy_nj && p.hydration_ug) {
        // Keep an existing identical boundary and its insertion order. A
        // phase change only needs to reschedule when the threshold moves.
        const auto& events = s.queue_index;
        const auto current = events.find(p.physiology_event);
        const auto target = s.founding && s.founding_reserves.contains(actor)
            ? detail::next_founding_physiology(s.founding->profile,p,s.founding_reserves.at(actor),ant.stage,founding_foundress(actor))
            : detail::next_physiology(p,ant.stage);
        if (current == events.end() || current->second.time != target)
            schedule_physiology(tx, actor);
    }
    WorldEvent f;
    f.kind = FactKind::ActivityChanged;
    f.actor = actor; f.colony = ant.colony; f.stage = ant.stage; f.position = ant.position;
    f.source = next.value ? next : previous;
    f.payload = next.value ? 1 : 0;
    tx.fact(f);
}

void WorldRuntime::draw_founding_water(Transaction& tx, const ScheduledEvent& event, const AntState& ant) {
    auto& s = *state_;
    if (!s.ecological || !s.ecological->water_sip_ug || !s.geometry || !s.surface) return;
    auto p = s.physiology.at(ant.id);
    const auto need = p.config.hydration_capacity_ug - p.hydration_ug;
    if (p.crop.water_ug >= need) return;
    const auto maximum = std::min({s.ecological->water_sip_ug, need - p.crop.water_ug,
                                   p.config.crop_capacity_ug - p.crop.total_ug()});
    if (!maximum) return;
    for (const auto ref : query_neighborhood({s.world, ant.id}, s.config.contact_distance_m).food) {
        const auto j = s.foods.index.at(ref.id);
        auto& food = s.foods.rows[j];
        if (!sip_source(s, food.position, food.initial) || !food.remaining.water_ug) continue;
        const FoodMass dose{0, 0, std::min(maximum, food.remaining.water_ug), 0};
        tx.touch_food(j);
        food.remaining = subtract(food.remaining, dose);
        s.m.ledger.available = subtract(s.m.ledger.available, dose);
        p.crop = sum(p.crop, dose);
        tx.physiology.set(ant.id, p);
        WorldEvent f;
        f.kind = FactKind::FoundressWaterIngested;
        f.actor = ant.id; f.colony = ant.colony; f.stage = ant.stage; f.position = ant.position;
        f.resource = food.id; f.source = event.id; f.transferred = dose;
        tx.fact(f);
        break;
    }
}
} // namespace antworld
