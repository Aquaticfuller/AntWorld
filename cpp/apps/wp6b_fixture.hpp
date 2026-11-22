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

enum class TrailTreatment { Silent, Marked, Blind };

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
    bool qualification{}, compact{}, shaft{}, fast_connector{};
    TrailTreatment trail_treatment{TrailTreatment::Silent};
    bool dogleg{}, blocked_water{};
    std::optional<EcologicalClosureConfig> ecological{};
    bool expanded_history{};
    bool cohort_assay{};
    bool micro_world{};
    bool seasonal_supply{};
    double habitat_trail_half_life_s{60};
    std::uint64_t habitat_wick_ug{1200};
    bool nearby_surface_feeder{};
    bool nursery_wick{};
};

inline RuntimeLimits assay_limits(const Case& c) {
    auto limits=s6_3_1_fixture::limits();
    if (c.expanded_history) limits.committed_events=4'000'000;
    return limits;
}

inline void configure_micro_world(wp5::Scene& scene, const Case& c, PositionM nest) {
    auto& w=scene.world;
    BehaviorConfig behavior;
    const bool habitat=c.ecological && c.ecological->founding_habitat.has_value();
    behavior.field_interval={6*hour_ms};
    if (habitat) {
        behavior.trail_half_life_s=c.habitat_trail_half_life_s;
        // ENGINEERING_FIXTURE: a trained L. niger forager can recall a
        // food-associated location the following day (10.1007/s00265-014-1710-2).
        if (c.ecological->founding_habitat->nutrition>=FoundingNutrition::SustainedSupply)
            behavior.memory_lifetime={day_ms};
    }
    behavior.step_duration={30'000}; // Retained collection/handling clock, not the travel clock.
    w.configure_surface({{-.15,0,-.15},31,31,.01},{},behavior);
    auto& g=scene.geometry;
    g.origin_m={0,0,0};
    g.initial_solid={{-300,-300,-300},{300,0,300}};
    g.work_duration={hour_ms/2}; g.move_duration={500}; g.decision_delay={60'000};
    if (habitat && c.ecological->founding_habitat->sealed_chamber) {
        // ENGINEERING_FIXTURE. One 12 x 7 mm pocket with a local, closed roof.
        // The larger solid is parametric; the finer quantum needs no dense grid.
        g.quantum_m=.00025;
        g.initial_solid={{-600,-600,-600},{600,0,600}};
        g.body_half_q=2; g.loaded_half_q=4; g.reach_q=8; g.max_patch_extent_q=8;
        g.dry_ug_per_q3=12; g.water_ug_per_q3=3; g.dig_energy_nj_per_q3=125;
        scene.voids={{{-24,-20,-24},{24,-2,4}}};
        if (c.ecological->founding_habitat->anatomical)
            scene.voids={{{-36,-20,-36},{36,-4,12}}}; // 18 x 12 x 4 mm; one closed pocket.
        if (c.ecological->founding_habitat->nutrition>=FoundingNutrition::ProtectedFounding) {
            // One rounded chamber, cut in abutting 0.5 mm bands. The floor,
            // closed roof and 0.25 mm collision quantum remain authoritative.
            constexpr std::array<int,12> half_width{11,18,22,26,28,30,32,33,34,35,36,36};
            scene.voids.clear();
            for (int band=0;band<24;++band) {
                const auto width=half_width[static_cast<std::size_t>(band<12?band:23-band)];
                scene.voids.push_back({{-width,-20,-36+band*2},{width,-4,-34+band*2}});
            }
        }
        w.configure_geometry(g,scene.voids);
        const double feeder_distance=c.nearby_surface_feeder?.005:.03;
        scene.target={c.seed%2?feeder_distance:-feeder_distance,0,0};
        require(w.spatially_clear(nest,nest,g.loaded_half_q) &&
                !w.spatially_clear(nest,{0,.001,0},g.loaded_half_q),"Founding chamber lacks its closed roof");
        return;
    }
    // A founding pocket and an entrance-side handoff alcove can share a
    // narrow traversable neck. The seed geometry is a laboratory fixture.
    scene.voids=habitat ? std::vector<BoxQ>{{{-12,-10,-5},{-4,-4,5}}, {{-2,-10,-6},{6,-4,6}},
                                          {{-6,-10,-3},{1,-4,3}}}
                         : std::vector<BoxQ>{{{-4,-10,-4},{4,-4,4}}};
    const auto top=c.arm=="blocked"?-4:c.arm=="plugged"?-1:0;
    if (c.dogleg) {
        scene.voids.push_back({{-2,-10,-3},{11,-4,3}});
        if (top==0) scene.voids.push_back({{6,-10,-3},{12,top,3}});
    } else if (top==0) scene.voids.push_back({{-3,-10,-3},{3,top,3}});
    else if (top==-1) scene.voids.push_back({{-2,-10,-2},{2,top,2}});
    w.configure_geometry(g,scene.voids);
    scene.target={c.seed%2?.03:-.03,0,0};
    require(w.spatially_clear(nest,nest,g.loaded_half_q),"MicroWorld founding site lacks load clearance");
    require(w.spatially_clear(nest,{0,.001,0},g.loaded_half_q)==(top==0 && !c.dogleg),
            "MicroWorld direct opening differs from its control");
}

inline void configure_integrated_assay(wp5::Scene& scene, const Case& c, PositionM nest) {
    auto& w = scene.world;
    const auto side = c.seed % 2 ? 1 : -1;
    std::vector<Cell> blocked;
    if (c.arm == "blocked")
        for (int z=0; z<5; ++z) blocked.push_back({4 + side*2, z});
    BehaviorConfig behavior;
    behavior.trails_enabled = c.trail_treatment != TrailTreatment::Silent;
    behavior.step_duration = {30'000}; // ENGINEERING_FIXTURE.
    if (behavior.trails_enabled) behavior.field_interval = {6 * hour_ms}; // ENGINEERING_FIXTURE cleanup cadence.
    if (c.trail_treatment == TrailTreatment::Blind) behavior.trail_weight = 0;
    w.configure_surface({{-.04, 0, -.02}, 9, 5, .01}, blocked, behavior);
    if (c.compact) {
        scene.geometry.origin_m = {-.008, -.008, -.008};
        scene.geometry.initial_solid = {{0, 0, 0}, {32, 16, 32}};
        // ENGINEERING_FIXTURE clocks reused from the WP-5 joint assay.
        scene.geometry.work_duration = {hour_ms / 2};
        scene.geometry.move_duration = c.fast_connector ? SimTime{500} : scene.geometry.work_duration;
        scene.geometry.decision_delay = {60'000};
        if (c.dogleg) scene.voids = {{{12,6,14},{25,10,18}}, {{21,6,14},{25,10,27}}, {{21,6,23},{25,16,27}}};
        else if (c.shaft) scene.voids = {{{14,6,14},{18,16,18}}};
        else scene.voids = {{{14,4,14},{18,16,18}}, {{12,5,14},{20,11,18}}};
        if (c.blocked_water && !c.cohort_assay) scene.voids.push_back({{19,7,15},{21,9,17}});
        if (c.cohort_assay) scene.voids.push_back({{9,7,15},{11,9,17}});
        w.configure_geometry(scene.geometry, scene.voids);
    } else closure::chamber(w);
    scene.target = {.03*side, 0, 0};
    const PositionM outside{scene.target.x,.001,scene.target.z};
    require(!w.spatially_clear(nest,scene.target) &&
            w.spatially_clear({0,.001,0},outside,2)==(c.arm!="blocked"),
            "integrated source access does not match the closed or open strip");
    if (c.qualification && !c.dogleg)
        require(w.spatially_clear(nest, {0,.001,0}, 2), "qualification shaft lacks loaded clearance");
    if (c.dogleg)
        require(!w.spatially_clear(nest,{0,.001,0},2), "dogleg unexpectedly has a direct vertical route");
}

inline wp5::Scene setup(const Case& c, const RuntimeLimits& limits = s6_3_1_fixture::limits(),
                        SocialConfig social = closure::day_social(), SpeciesCareProfile care = closure::timed_care(true),
                        EnvironmentCareProfile environment = {}) {
    WorldConfig config;
    config.continuous_spatial_motion = c.integrated_assay;
    if (c.micro_world) { config.min_m={-.155,-.15,-.155}; config.max_m={.155,.005,.155}; }
    const bool habitat=c.ecological && c.ecological->founding_habitat.has_value();
    wp5::Scene scene{WorldRuntime({habitat?653ULL:646ULL, c.identity}, c.seed, config, limits), {}, {}, {}, {}, {}, {}};
    auto& w = scene.world;
    if (c.ecological) w.configure_ecological_closure(*c.ecological);
    const bool anatomical=habitat && c.ecological->founding_habitat->anatomical;
    const PositionM nest{0,c.integrated_assay?-.004:0,anatomical?.002:0};
    const auto brood=habitat ? c.ecological->founding_habitat->brood_site : nest;
    w.configure_long_term();
    BehaviorConfig behavior;
    behavior.trails_enabled = false;
    if (c.micro_world) configure_micro_world(scene,c,nest);
    else if (c.integrated_assay) configure_integrated_assay(scene,c,nest);
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
    w.configure_biology(care,environment);
    const auto colony = w.seed_colony(nest);
    const bool sealed=habitat && c.ecological->founding_habitat->sealed_chamber;
    const auto laying_site=anatomical?PositionM{0,nest.y,0}:sealed?nest:brood;
    scene.queen = w.seed_ant(colony, {laying_site, LifeStage::Adult, Caste::Queen, 4000});
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
    if (c.ecological && c.ecological->water_sip_ug) {
        const auto water=c.nursery_wick ? brood : sealed ? PositionM{laying_site.x-.001,laying_site.y,laying_site.z}
            : habitat ? PositionM{brood.x,brood.y,brood.z+.001}
            : c.blocked_water ? PositionM{c.cohort_assay?-.003:.002,nest.y,0} : nest;
        require(w.spatially_clear(brood,water)!=c.blocked_water && w.query_material(water)==Material::Void,
                "wrong water contact treatment");
        w.seed_food(water, {0,0,c.habitat_wick_ug,0});
    }
    for (unsigned i = 0; i < c.workers; ++i) {
        const auto worker = w.seed_ant(colony, {{}, LifeStage::Adult, Caste::Worker, 4000});
        w.enable_physiology(worker, wp5::adult, rm01::physiology_config(rm01::legacy_duration));
        w.set_autonomy(worker);
        scene.workers.push_back(worker);
    }
    if (c.integrated_assay && c.food.total_ug()) {
        const auto daily = c.arm == "limited" ? FoodMass{188,94,563,0} :
            FoodMass{c.food.carbs_ug/4,c.food.protein_ug/4,c.food.water_ug/4,0};
        const auto feeder=[&](PositionM position,FoodMass initial,FoodMass pulse) {
            const auto source=w.seed_food(position,initial);
            ResourceCycleConfig cycle{{pulse.carbs_ug*c.release_days,pulse.protein_ug*c.release_days,
                                        pulse.water_ug*c.release_days,0},pulse};
            if (c.seasonal_supply) {
                cycle.cyclic=true;
                cycle.productive_span={182*day_ms};
                cycle.low_productivity_permille=250;
            }
            w.configure_resource_cycle(source,cycle);
        };
        if (habitat && c.ecological->founding_habitat->variable_conditions) {
            const bool dry_food=c.ecological->founding_habitat->nutrition>=FoundingNutrition::ProtectedFounding;
            const auto split=[dry_food](FoodMass amount) {
                const FoodMass extra{dry_food?0:amount.carbs_ug/4,amount.protein_ug/2,dry_food?0:amount.water_ug/4,0};
                amount.carbs_ug-=extra.carbs_ug;
                amount.protein_ug-=extra.protein_ug;
                amount.water_ug-=extra.water_ug;
                return std::pair{amount,extra};
            };
            const auto [main_food,extra_food]=split(c.food);
            const auto [main_pulse,extra_pulse]=split(daily);
            feeder(scene.target,main_food,main_pulse);
            feeder({-scene.target.x,0,.02},extra_food,extra_pulse);
        } else {
            feeder(scene.target,c.food,daily);
        }
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
