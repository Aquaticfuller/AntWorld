#include "founding_internal.hpp"
#include "ecological_internal.hpp"
#include "care_internal.hpp"

namespace antworld {
using namespace detail;

void WorldRuntime::enable_founding(AntRef ref, const FoundingProfile& profile) {
    auto& s = *state_;
    const auto ant = query_ant(ref);
    if (s.founding || !s.long_term || !s.social || !integrated_care(s) || s.m.now != SimTime{} || s.m.watermark ||
        !ant || ant->stage != LifeStage::Adult || ant->caste != Caste::Queen || s.physiology.contains(ref.id) ||
        s.reproduction.contains(ref.id) || s.pending_conflicts.contains(ref.id))
        throw std::invalid_argument("F1 requires an unenrolled foundress at integrated world setup");
    validate_founding(profile);
    auto p = initial_founding_physiology(profile, true, {});
    if (timed_activity(s)) p.active_work = ScheduledId{};
    FoundingReserve reserve{profile.lipid_ug, 0, profile.protein_ug};
    const auto converted = convert_founding_lipid(profile, p, reserve, LifeStage::Adult, true);
    p.initial.body_energy_nj = p.body_energy_nj;
    Transaction tx(s, limits_);
    s.m.founding_trace = trace_hash(s.journal);
    s.founding = std::make_shared<const State::FoundingSetup>(State::FoundingSetup{ref.id, profile});
    tx.set_founding(ref.id, reserve);
    tx.physiology.set(ref.id, p);
    schedule_physiology(tx, ref.id);
    s.m.physiology_inputs = sum(s.m.physiology_inputs, {0, profile.protein_ug, profile.water_ug, 0});
    s.m.maximum_yield = std::max(s.m.maximum_yield, p.config.carbohydrate_yield_nj_per_ug);
    validate_nutrition_capacity();

    ScheduledEvent lay;
    lay.kind = ScheduledEvent::Kind::Reproduction;
    lay.actor = ref.id;
    lay.key = {profile.first_lay, Phase::Environment, 2, 0, 0};
    tx.reproduction.set(ref.id, {founding_reproduction(profile), tx.insert(lay), 0, 0});

    WorldEvent f;
    f.kind = FactKind::FoundingConfigured;
    f.payload = founding_profile_hash(ref.id, profile);
    f.random_value = profile.model_version();
    tx.fact(f);
    f = {};
    f.actor = ref.id;
    f.colony = ant->colony;
    f.stage = ant->stage;
    f.position = ant->position;
    f.kind = FactKind::PhysiologyEnabled;
    tx.fact(f);
    f.kind = FactKind::FoundingReserveSeeded;
    f.payload = profile.lipid_ug;
    f.transferred = {0, profile.protein_ug, profile.water_ug, 0};
    tx.fact(f);
    tx.fact(lipid_conversion(profile, *ant, {}, converted));
    f.kind = FactKind::ReproductionEnabled;
    f.payload = static_cast<std::uint64_t>(profile.maintenance_floor.milliseconds);
    f.transferred = {};
    tx.fact(f);
    tx.commit();
}

bool WorldRuntime::founding_foundress(EntityId id) const {
    return state_->founding && state_->founding->founder == id;
}

std::optional<FoundingProfile> WorldRuntime::founding_profile() const {
    return state_->founding ? std::optional{state_->founding->profile} : std::nullopt;
}

std::optional<FoundingReserve> WorldRuntime::query_founding(AntRef ref) const {
    const auto& s = *state_;
    if (ref.world != s.world || !s.founding || !s.founding_reserves.contains(ref.id)) return {};
    auto reserve = s.founding_reserves.at(ref.id);
    auto p = s.physiology.at(ref.id);
    const auto stage = s.ants.get(s.ants.index.at(ref.id)).stage;
    settle_founding(s.founding->profile, p, reserve, stage, founding_foundress(ref.id), s.m.now);
    return reserve;
}

FoundingBudget WorldRuntime::founding_budget() const {
    const auto& s = *state_;
    if (!s.founding) return {};
    const auto& f = s.founding->profile;
    FoundingBudget budget;
    budget.introduced_lipid_ug = f.lipid_ug;
    budget.introduced_protein_ug = f.protein_ug;
    budget.effective_energy_nj = multiply(f.lipid_ug, f.lipid_yield_nj_per_ug);
    budget.enrolled = s.founding_reserves.size();
    for (const auto& [id, r] : s.founding_reserves) {
        (void)id;
        budget.owned_lipid_ug = add(budget.owned_lipid_ug, r.lipid_ug);
        budget.spent_lipid_ug = add(budget.spent_lipid_ug, r.spent_lipid_ug);
        budget.owned_mobile_protein_ug = add(budget.owned_mobile_protein_ug, r.mobile_protein_ug);
    }
    return budget;
}

bool WorldRuntime::can_feed_founding(EntityId donor, EntityId larva, bool require_protein) const {
    const auto& s = *state_;
    if (!s.social->exchange_enabled || !s.founding_reserves.contains(larva)) return false;
    const auto q = query_physiology({s.world, donor}), p = query_physiology({s.world, larva});
    const auto a = query_founding({s.world, donor}), b = query_founding({s.world, larva});
    const auto ration = founding_ration(s.founding->profile, *q, *a, *p, *b);
    return require_protein ? ration.crop.protein_ug != 0 : ration.lipid_ug || ration.crop.total_ug();
}

void WorldRuntime::resolve_founding_feed(Transaction& tx, const ScheduledEvent& event, WorldEvent& fact) {
    auto& s = *state_;
    const auto a = s.ants.get(s.ants.index.at(event.actor));
    const auto b = s.ants.get(s.ants.index.at(EntityId{event.payload}));
    fact.payload = b.id.value;
    if (!a.alive() || !b.alive()) { fact.outcome = Outcome::DeadActor; return; }
    if (a.stage != LifeStage::Adult || b.stage != LifeStage::Larva) { fact.outcome = Outcome::InvalidStage; return; }
    if (!contact(a, b, s.config, s.social && s.geometry ? nullptr : s.surface.get()) ||
        !spatially_clear(a.position, b.position) || !surface_care_clear(s, a.position, b.position)) {
        fact.outcome = Outcome::OutOfReach;
        return;
    }
    synchronize_physiology(tx, a.id);
    synchronize_physiology(tx, b.id);
    auto donor = s.physiology.at(a.id), recipient = s.physiology.at(b.id);
    auto maternal = s.founding_reserves.at(a.id), larva = s.founding_reserves.at(b.id);
    const auto& profile = s.founding->profile;
    const auto amount = founding_ration(profile, donor, maternal, recipient, larva);
    if (!s.social->exchange_enabled || (!amount.lipid_ug && !amount.crop.total_ug())) {
        fact.outcome = Outcome::EmptyInventory;
        return;
    }
    apply_founding_ration(amount, donor, maternal, recipient, larva);
    tx.physiology.set(a.id, donor);
    tx.physiology.set(b.id, recipient);
    tx.set_founding(a.id, maternal);
    tx.set_founding(b.id, larva);
    schedule_physiology(tx, a.id);
    fact.kind = FactKind::FoundingRation;
    fact.random_value = amount.lipid_ug;
    fact.transferred = amount.crop;
}
} // namespace antworld
