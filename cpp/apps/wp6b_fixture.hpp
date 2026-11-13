#pragma once

#include <filesystem>
#include "s6_3_1_fixture.hpp"
#include "wp5_fixtures.hpp"

namespace antworld::wp6b {
using wp5::Time;
using wp5::day_ms;
using wp5::hour_ms;
using wp4::require;

inline FoundingProfile nominal(FoundingPopulation population = FoundingPopulation::Borisovka) {
    FoundingProfile f;
    f.population = population;
    const bool borisovka = population == FoundingPopulation::Borisovka;
    f.brood = {{{{borisovka?1442880000:1356480000}, 15000000, 2},
                {{borisovka?881280000:915840000}, 35000000, 6},
                {{borisovka?1252800000:1175040000}, 25000000, 3}}};
    f.worker = rm01::physiology_config(rm01::legacy_duration);
    f.first_lay = {4 * day_ms}; f.opening_width = {day_ms}; f.opening_spacing = {2 * hour_ms};
    f.later_spacing = {2 * day_ms}; f.maintenance_floor = {10 * day_ms};
    f.wet_mass_ug = 27600; f.structural_minimum_ug = 10000; f.lipid_ug = 5500;
    f.protein_ug = 1200; f.water_ug = 7000; f.lipid_yield_nj_per_ug = 34000000;
    f.basal_nj_per_day = 2340000000; f.active_nj_per_ms = 1; f.water_ug_per_day = 60;
    f.egg_lipid_ug = 12; f.egg_protein_ug = 20; f.egg_water_ug = 65; f.lay_overhead_nj = 10000000;
    f.larval_tissue_ug = 85; f.larval_lipid_capacity_ug = 40;
    f.ration_lipid_ug = 6; f.ration_protein_ug = 16; f.ration_water_ug = 20;
    return f;
}

struct Case {
    std::uint64_t identity, seed;
    std::string arm;
    bool care;
    unsigned workers;
    FoodMass food;
    FoundingProfile profile;
    SimTime horizon{90 * day_ms};
    bool integrated_assay{};
    unsigned release_days{120}; // ENGINEERING_FIXTURE. Only the scope assay selects another finite budget.
};

inline void configure_integrated_assay(wp5::Scene& scene, const Case& c, PositionM nest) {
    auto& w = scene.world;
    const auto side = c.seed % 2 ? 1 : -1;
    std::vector<Cell> blocked;
    if (c.arm == "blocked")
        for (int z=0; z<5; ++z) blocked.push_back({4 + side*2, z});
    BehaviorConfig behavior;
    behavior.trails_enabled = false;
    behavior.step_duration = {30'000}; // ENGINEERING_FIXTURE.
    w.configure_surface({{-.04, 0, -.02}, 9, 5, .01}, blocked, behavior);
    closure::chamber(w);
    scene.target = {.03*side, 0, 0};
    const PositionM outside{scene.target.x,.001,scene.target.z};
    require(!w.spatially_clear(nest,scene.target) &&
            w.spatially_clear({0,.001,0},outside,2)==(c.arm!="blocked"),
            "integrated source access does not match the closed or open strip");
}

inline wp5::Scene setup(const Case& c, const RuntimeLimits& limits = s6_3_1_fixture::limits(),
                        SocialConfig social = closure::day_social(), SpeciesCareProfile care = closure::timed_care(true)) {
    WorldConfig config;
    config.continuous_spatial_motion = c.integrated_assay;
    wp5::Scene scene{WorldRuntime({646, c.identity}, c.seed, config, limits), {}, {}, {}, {}, {}, {}};
    auto& w = scene.world;
    const PositionM nest{0,c.integrated_assay?-.004:0,0};
    w.configure_long_term();
    BehaviorConfig behavior;
    behavior.trails_enabled = false;
    if (c.integrated_assay) configure_integrated_assay(scene,c,nest);
    else w.configure_surface({{-.03, 0, -.03}, 7, 7, .01}, {}, behavior);
    const bool water_trial=c.arm=="water-reachable" || c.arm=="water-blocked" || c.arm=="water-absent";
    if (!c.integrated_assay && (c.workers || water_trial)) {
        scene.geometry.origin_m = {-.020, -.006, -.012};
        scene.geometry.initial_solid = {{0, 0, 0}, {80, 24, 80}};
        scene.geometry.work_duration = {hour_ms / 2};
        scene.geometry.move_duration = scene.geometry.work_duration;
        scene.geometry.decision_delay = {60000};
        scene.voids = {{{36, 8, 20}, {44, 16, 28}}, {{0, 10, 22}, {80, 14, 26}}, {{36, 8, 60}, {44, 16, 68}}};
        w.configure_geometry(scene.geometry, scene.voids);
    } else if (!c.integrated_assay && c.arm == "contact-blocked") {
        // Same site with a narrow wall and a genuine route around its end.
        scene.geometry.origin_m = {-.008, -.006, -.006};
        scene.geometry.initial_solid = {{0, 0, 0}, {32, 24, 24}};
        scene.voids = {{{11, 8, 8}, {17, 16, 17}}, {{18, 8, 8}, {23, 16, 17}}, {{11, 8, 15}, {23, 16, 19}}};
        w.configure_geometry(scene.geometry, scene.voids);
    } else if (!c.integrated_assay) wp5::configure(scene, {"founding", "on", 0, c.seed});
    w.configure_social(social);
    w.configure_biology(care);
    const auto colony = w.seed_colony(nest);
    scene.queen = w.seed_ant(colony, {nest, LifeStage::Adult, Caste::Queen, 4000});
    w.enable_founding(scene.queen, c.profile);
    if (c.arm == "contact-blocked") {
        // One legacy assay larva on each side of the wall, at equal distances.
        // Their origins remain fixture seeds and cannot count as F1 offspring.
        const PositionM near{-.0015, 0, 0}, far{.0015, 0, 0};
        require(w.spatially_clear({}, near) && !w.spatially_clear({}, far), "blocked contact probe does not isolate reach");
        for (const auto position : {near, far}) {
            const auto larva = w.seed_ant(colony, {position, LifeStage::Larva});
            w.enable_physiology(larva, closure::larva, rm01::physiology_config(rm01::legacy_duration));
        }
    }
    if (c.care) w.set_autonomy(scene.queen);
    for (unsigned i = 0; i < c.workers; ++i) {
        const auto worker = w.seed_ant(colony, {{}, LifeStage::Adult, Caste::Worker, 4000});
        w.enable_physiology(worker, wp5::adult, rm01::physiology_config(rm01::legacy_duration));
        w.set_autonomy(worker);
        scene.workers.push_back(worker);
    }
    if (c.integrated_assay && c.food.total_ug()) {
        const auto source=w.seed_food(scene.target,c.food);
        const auto daily = c.arm == "limited" ? FoodMass{188,94,563,0} :
            FoodMass{c.food.carbs_ug/4,c.food.protein_ug/4,c.food.water_ug/4,0};
        w.configure_resource_cycle(source, {{daily.carbs_ug*c.release_days,daily.protein_ug*c.release_days,
                                              daily.water_ug*c.release_days,0},daily});
    } else if (!c.integrated_assay && c.food.total_ug()) {
        const bool blocked=c.arm=="blocked" || c.arm=="water-blocked";
        const PositionM depot = blocked ? PositionM{0, 0, .020} : PositionM{};
        w.seed_food(depot, c.food);
        if (blocked) require(!w.query_route(scene.queen, depot).found && !w.spatially_clear({}, depot),
                             "blocked food is reachable at setup");
        else if (water_trial) require(w.spatially_clear({},depot) && w.query_material(depot)==Material::Void,
                                      "accessible water is not in the same clear local pocket");
    }
    return scene;
}

inline void check_ledgers(const WorldRuntime& w) {
    const auto n = w.nutrition_snapshot();
    require(n.introduced == n.accounted && n.energy_input_nj == n.body_energy_nj + n.dissipated_energy_nj, "F1 nutrition ledger mismatch");
    const auto reserve = w.founding_budget();
    require(reserve.introduced_lipid_ug == reserve.owned_lipid_ug + reserve.spent_lipid_ug, "F1 lipid ledger mismatch");
    const auto soil = w.geometry_snapshot().ledger;
    require(soil.initial_q3 == soil.remaining_q3 + soil.carried_q3 + soil.deposited_q3, "F1 soil ledger mismatch");
}
} // namespace antworld::wp6b
