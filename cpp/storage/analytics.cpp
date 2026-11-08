#include "antworld/storage/analytics.hpp"
#include <array>
#include <limits>
#include <map>
#include <stdexcept>

namespace antworld::storage {
namespace {
using K = MetricKind;
constexpr auto definitions = std::to_array<MetricDefinition>(
    {{Metric::Alive, "population.alive", "individuals", "All living identities, any stage/caste", K::Gauge},
     {Metric::WorkerAlive, "population.worker_alive", "individuals", "Living adult workers", K::Gauge},
     {Metric::QueenAlive, "population.queen_alive", "individuals", "Living adult queens", K::Gauge},
     {Metric::MaleAlive, "population.male_alive", "individuals", "Living adult males", K::Gauge},
     {Metric::Egg, "population.egg", "individuals", "Living eggs", K::Gauge},
     {Metric::Larva, "population.larva", "individuals", "Living larvae", K::Gauge},
     {Metric::Pupa, "population.pupa", "individuals", "Living pupae", K::Gauge},
     {Metric::DeadRetained, "population.dead_retained", "individuals",
      "Retained terminal identities; not a window flow", K::Gauge},
     {Metric::CargoCarbs, "cargo.carbs", "ug", "Actual cargo including retained dead inventories", K::Gauge},
     {Metric::CargoProtein, "cargo.protein", "ug", "Actual cargo including retained dead inventories",
      K::Gauge},
     {Metric::CargoWater, "cargo.water", "ug", "Actual cargo including retained dead inventories", K::Gauge},
     {Metric::CargoOther, "cargo.other", "ug", "Actual cargo including retained dead inventories", K::Gauge},
     {Metric::NestCarbs, "nest_food.carbs", "ug", "Physical nest stock, excluding crops/cargo", K::Gauge},
     {Metric::NestProtein, "nest_food.protein", "ug", "Physical nest stock, excluding crops/cargo", K::Gauge},
     {Metric::NestWater, "nest_food.water", "ug", "Physical nest stock, excluding crops/cargo", K::Gauge},
     {Metric::NestOther, "nest_food.other", "ug", "Physical nest stock, excluding crops/cargo", K::Gauge},
     {Metric::CropCarbs, "crop.carbs", "ug", "Actual crops including dead inventories", K::Gauge},
     {Metric::CropProtein, "crop.protein", "ug", "Actual crops including dead inventories", K::Gauge},
     {Metric::CropWater, "crop.water", "ug", "Actual crops including dead inventories", K::Gauge},
     {Metric::CropOther, "crop.other", "ug", "Actual crops including dead inventories", K::Gauge},
     {Metric::BodyEnergy, "body.energy", "nJ", "Analytically settled body energy at observation time",
      K::Gauge},
     {Metric::Hydration, "body.water", "ug", "Analytically settled hydration including dead inventory",
      K::Gauge},
     {Metric::TissueProtein, "body.tissue_protein", "ug", "Retained actual tissue protein", K::Gauge},
     {Metric::OxidizedCarbs, "sink.oxidized_carbs", "ug", "Cumulative actual carbohydrate oxidation",
      K::Gauge},
     {Metric::LostWater, "sink.lost_water", "ug", "Cumulative actual body water loss", K::Gauge},
     {Metric::DissipatedEnergy, "sink.dissipated_energy", "nJ", "Cumulative basal/activity/dig expenditure",
      K::Gauge},
     {Metric::PhysiologyIndividuals, "coverage.physiology", "individuals",
      "Identities with enabled physiology, including dead", K::Gauge},
     {Metric::Paused, "behavior.paused", "individuals", "Living adults with explicit Paused program",
      K::Gauge},
     {Metric::Rest, "behavior.rest", "individuals", "Living adults with explicit Rest program", K::Gauge},
     {Metric::Nurse, "behavior.nurse", "individuals", "Living adults with explicit Nurse program", K::Gauge},
     {Metric::Forage, "behavior.forage", "individuals", "Living adults with enabled foraging program",
      K::Gauge},
     {Metric::Excavate, "behavior.excavate", "individuals", "Living adults with explicit Excavate program",
      K::Gauge},
     {Metric::BehaviorUnknown, "behavior.unspecified", "individuals",
      "Living adults without an explicit program", K::Gauge},
     {Metric::AvailableCarbs, "environment_food.carbs", "ug", "World-only source inventory", K::Gauge},
     {Metric::AvailableProtein, "environment_food.protein", "ug", "World-only source inventory", K::Gauge},
     {Metric::AvailableWater, "environment_food.water", "ug", "World-only source inventory", K::Gauge},
     {Metric::AvailableOther, "environment_food.other", "ug", "World-only source inventory", K::Gauge},
     {Metric::SoilRemaining, "soil.remaining", "q3", "World-only exact remaining soil volume", K::Gauge},
     {Metric::SoilCarried, "soil.carried", "q3", "World-only actual carried soil volume", K::Gauge},
     {Metric::SoilDeposited, "soil.deposited", "q3", "World-only loose deposited soil volume", K::Gauge},
     {Metric::VoidVolume, "nest.void_volume", "q3",
      "Void inside InitialSolid; m3 = q3 * quantum_m^3; not colony ownership", K::Gauge},
     {Metric::GeometryEdits, "geometry.edit_count", "edits", "Complete authoritative edit log length",
      K::Gauge},
     {Metric::Seeded, "life.seeded", "events", "Actual AntSeeded facts; not biological births", K::Flow},
     {Metric::Emerged, "life.emerged", "events", "Actual Pupa to Adult transitions", K::Flow},
     {Metric::Deaths, "life.deaths", "events", "Unique committed deaths", K::Flow},
     {Metric::CollectedCarbs, "food.collected_carbs", "ug", "External food actually collected", K::Flow},
     {Metric::CollectedProtein, "food.collected_protein", "ug", "External food actually collected", K::Flow},
     {Metric::CollectedWater, "food.collected_water", "ug", "External food actually collected", K::Flow},
     {Metric::DeliveredCarbs, "food.delivered_carbs", "ug", "Actual cargo to physical nest stock", K::Flow},
     {Metric::DeliveredProtein, "food.delivered_protein", "ug", "Actual cargo to physical nest stock",
      K::Flow},
     {Metric::DeliveredWater, "food.delivered_water", "ug", "Actual cargo to physical nest stock", K::Flow},
     {Metric::MetabolizedCarbs, "food.metabolized_carbs", "ug", "Carbohydrate actually absorbed/oxidized",
      K::Flow},
     {Metric::Trophallaxis, "nutrition.internal_transfer", "ug",
      "Actual internal transfer; never counted as external intake", K::Flow},
     {Metric::ExcavatedDry, "excavation.dry", "ug",
      "Actual removed dry soil, including repeated remove/fill work", K::Flow},
     {Metric::ExcavatedWater, "excavation.water", "ug", "Actual removed soil water", K::Flow},
     {Metric::FilledDry, "fill.dry", "ug", "Actual supplied dry soil filled", K::Flow},
     {Metric::FilledWater, "fill.water", "ug", "Actual supplied soil water filled", K::Flow},
     {Metric::Moves, "behavior.moves", "events", "Committed moves, not intentions", K::Flow},
     {Metric::Rejected, "behavior.rejected", "events", "Rejected outcomes, not ecological success", K::Flow},
     {Metric::BehaviorChanges, "behavior.changes", "events", "Explicit recorded program changes", K::Flow}});
static_assert(definitions.size() == static_cast<std::size_t>(Metric::Count));
constexpr auto gauges = static_cast<std::size_t>(Metric::Seeded);
using Values = std::array<std::uint64_t, gauges>;
void add(Values &v, Metric metric, std::uint64_t value) {
    auto &target = v.at(static_cast<std::size_t>(metric));
    target = checked_add(target, value);
}
void mass(Values &v, Metric first, FoodMass value) {
    auto i = static_cast<std::size_t>(first);
    for (auto amount : value.components()) {
        v[i] = checked_add(v[i], amount);
        ++i;
    }
}
} // namespace
std::uint64_t checked_add(std::uint64_t a, std::uint64_t b) {
    if (b > UINT64_MAX - a)
        throw std::overflow_error("metric uint64 accumulation overflow");
    return a + b;
}
const MetricDefinition &metric_definition(Metric id) { return definitions.at(static_cast<std::size_t>(id)); }
std::span<const MetricDefinition> metric_definitions() { return definitions; }
Observation observe(const WorldRuntime &w) {
    const auto s = w.summary();
    Observation o{s.world, s.now, s.revision, {s.committed_events}, 0, std::vector<MetricValue>(0)};
    std::map<ColonyId, Values> values;
    values[{}] = {};
    for (const auto &c : w.colonies())
        mass(values[c.id], Metric::NestCarbs, c.nest_food);
    for (const auto &a : w.ant_states()) {
        auto &v = values[a.colony];
        if (a.alive()) {
            add(v, Metric::Alive, 1);
            if (a.stage < LifeStage::Adult)
                add(v,
                    static_cast<Metric>(static_cast<unsigned>(Metric::Egg) + static_cast<unsigned>(a.stage)),
                    1);
            else
                add(v,
                    static_cast<Metric>(static_cast<unsigned>(Metric::WorkerAlive) +
                                        static_cast<unsigned>(a.caste)),
                    1);
        } else
            add(v, Metric::DeadRetained, 1);
        mass(v, Metric::CargoCarbs, a.carried_food);
        const auto p = w.query_physiology({s.world, a.id});
        if (p) {
            mass(v, Metric::CropCarbs, p->crop);
            for (auto pair : {std::pair{Metric::BodyEnergy, p->body_energy_nj},
                              {Metric::Hydration, p->hydration_ug},
                              {Metric::TissueProtein, p->tissue_protein_ug},
                              {Metric::OxidizedCarbs, p->oxidized_carbs_ug},
                              {Metric::LostWater, p->lost_water_ug},
                              {Metric::DissipatedEnergy, p->dissipated_energy_nj}})
                add(v, pair.first, pair.second);
            add(v, Metric::PhysiologyIndividuals, 1);
        }
        if (a.stage == LifeStage::Adult) {
            const auto forager = w.query_forager({s.world, a.id});
            auto behavior = Metric::BehaviorUnknown;
            if (p)
                behavior = static_cast<Metric>(static_cast<unsigned>(Metric::Paused) +
                                               static_cast<unsigned>(p->behavior));
            else if (forager)
                behavior = forager->enabled ? Metric::Forage : Metric::Paused;
            add(v, behavior, 1);
        }
    }
    for (const auto &[owner, v] : values)
        if (owner.value)
            for (std::size_t i = 0; i < gauges; ++i)
                values[{}][i] = checked_add(values[{}][i], v[i]);
    auto &global = values[{}];
    mass(global, Metric::AvailableCarbs, s.food_ledger.available);
    const auto g = w.geometry_snapshot();
    if (g.configured) {
        o.geometry_quantum_m = g.config.quantum_m;
        add(global, Metric::SoilRemaining, g.ledger.remaining_q3);
        add(global, Metric::SoilCarried, g.ledger.carried_q3);
        add(global, Metric::SoilDeposited, g.ledger.deposited_q3);
        add(global, Metric::GeometryEdits, g.geometry_revision);
        add(global, Metric::VoidVolume, w.query_material_volume(g.config.initial_solid, Material::Void));
    }
    for (const auto &[owner, v] : values)
        for (std::size_t i = 0; i < gauges; ++i) {
            if (owner.value && i >= static_cast<std::size_t>(Metric::AvailableCarbs))
                continue;
            if (!g.configured && i >= static_cast<std::size_t>(Metric::SoilRemaining))
                continue;
            o.values.push_back({owner, static_cast<Metric>(i), v[i]});
        }
    return o;
}
std::vector<MetricValue> contributions(const WorldEvent &e, const GeometrySnapshot &g,
                                       const GeometryEdit *edit) {
    std::vector<MetricValue> out(0);
    auto add_flow = [&](Metric metric, std::uint64_t amount) {
        if (!amount)
            return;
        out.push_back({{}, metric, amount});
        if (e.colony.value)
            out.push_back({e.colony, metric, amount});
    };
    auto food = [&](Metric first) {
        const auto v = e.transferred.components();
        for (unsigned i = 0; i < 3; ++i)
            add_flow(static_cast<Metric>(static_cast<unsigned>(first) + i), v[i]);
    };
    switch (e.kind) {
    case FactKind::AntSeeded:
        add_flow(Metric::Seeded, 1);
        break;
    case FactKind::StageChanged:
        if (e.stage == LifeStage::Adult)
            add_flow(Metric::Emerged, 1);
        break;
    case FactKind::AntDied:
        add_flow(Metric::Deaths, 1);
        break;
    case FactKind::FoodCollected:
        food(Metric::CollectedCarbs);
        break;
    case FactKind::FoodDelivered:
        food(Metric::DeliveredCarbs);
        break;
    case FactKind::PhysiologyUpdated:
        add_flow(Metric::MetabolizedCarbs, e.transferred.carbs_ug);
        break;
    case FactKind::NutritionTransferred:
        add_flow(Metric::Trophallaxis, e.transferred.total_ug());
        break;
    case FactKind::Moved:
        add_flow(Metric::Moves, 1);
        break;
    case FactKind::ActionRejected:
        add_flow(Metric::Rejected, 1);
        break;
    case FactKind::BehaviorChanged:
        add_flow(Metric::BehaviorChanges, 1);
        break;
    case FactKind::SoilExcavated:
    case FactKind::SoilFilled:
        if (!edit || edit->event != e.id || !g.configured)
            throw std::logic_error("soil metric lacks actual edit evidence");
        add_flow(e.kind == FactKind::SoilExcavated ? Metric::ExcavatedDry : Metric::FilledDry,
                 edit->volume_q3 * g.config.dry_ug_per_q3);
        add_flow(e.kind == FactKind::SoilExcavated ? Metric::ExcavatedWater : Metric::FilledWater,
                 edit->volume_q3 * g.config.water_ug_per_q3);
        break;
    default:
        break;
    }
    return out;
}
} // namespace antworld::storage
