#include "antworld/core/world_runtime.hpp"
#include <cstdlib>
#include <cstdio>
#include <exception>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string_view>

// Single-threaded fault injection. Only the operation under test has injection
// enabled. Verification and rollback comparisons run after it is disabled.
namespace {
long remaining = -1;
const char* current_scenario = "setup";
long current_fault = -1;
void* allocate(std::size_t bytes) {
    if (remaining == 0) throw std::bad_alloc{};
    if (remaining > 0) --remaining;
    if (auto* p = std::malloc(bytes == 0 ? 1 : bytes)) return p;
    throw std::bad_alloc{};
}
}
void* operator new(std::size_t bytes) { return allocate(bytes); }
void* operator new[](std::size_t bytes) { return allocate(bytes); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }

using namespace antworld;
namespace {
template <typename Fn> void sweep(const char* name, WorldRuntime& world, Fn action) {
    current_scenario = name;
    const auto before = world.checkpoint();
    auto encounters=[&] {
        std::vector<ContactSample> result(0);
        if (world.social_config()) for (const auto& a:world.ant_states()) if (a.alive())
            result.push_back(world.sample_contacts({world.summary().world,a.id},17));
        return result;
    };
    const auto prior_encounters=encounters();
    for (long fault = 0; fault < 10000; ++fault) {
        world.restore(before); current_fault = fault; remaining = fault;
        bool failed = false;
        try { action(); } catch (const std::bad_alloc&) { failed = true; }
        catch (...) { remaining = -1; throw; }
        remaining = -1;
        if (!failed) {
            if (fault == 0) throw std::runtime_error("fault sweep exercised no allocation");
            std::cout << name << " rollback_points=" << fault << '\n';
            world.restore(before); return;
        }
        if (world.checkpoint() != before) throw std::runtime_error("allocation failure left partial world state");
        if (encounters()!=prior_encounters) throw std::runtime_error("allocation failure left a partial derived contact tree");
    }
    throw std::runtime_error("fault sweep never completed");
}
void s2_sweeps() {
    // ENGINEERING_FIXTURE: a three-cell corridor isolates each commit boundary.
    WorldRuntime world({1, 2}, 12345); SurfaceConfig grid{{0, 0, 0}, 3, 1, 0.01};
    BehaviorConfig params; params.trail_half_life_s = 1; params.trail_cutoff_units = 0.5;
    sweep("surface_configure", world, [&] { world.configure_surface(grid, {}, params); });
    world.configure_surface(grid, {}, params); const auto colony = world.seed_colony();
    const auto ant = world.seed_ant(colony, {{}, LifeStage::Adult, Caste::Worker, 1000});
    sweep("local_food_index", world, [&] { world.seed_food({0.02, 0, 0}, {1000, 0, 0, 0}); });
    world.seed_food({0.02, 0, 0}, {1000, 0, 0, 0});
    sweep("activate_forager", world, [&] { world.start_foraging(ant); }); world.start_foraging(ant);
    sweep("local_decision_discovery", world, [&] { world.advance_to({0}); });
    world.advance_to({1099}); sweep("local_move", world, [&] { world.advance_to({1100}); });
    world.advance_to({3301}); sweep("collect_learned_route", world, [&] { world.advance_to({3302}); });
    world.advance_to({4402}); sweep("return_deposit", world, [&] { world.advance_to({4403}); });
    world.advance_to({4999}); sweep("field_decay_prune", world, [&] { world.advance_to({5000}); });
    world.advance_to({6604}); sweep("physical_delivery", world, [&] { world.advance_to({6605}); });
    world.advance_to({6605}); const auto bytes = world.checkpoint();
    sweep("restore_surface_history", world, [&] { world.restore(bytes); });
    world.schedule_lifecycle(ant, {6606}, LifeStage::Dead);
    sweep("cancel_dead_forager", world, [&] { world.advance_to({6606}); });
    world.advance_to({9999}); sweep("erase_decayed_trails", world, [&] { world.advance_to({10000}); });
    std::cout << "PASS S2_ALLOCATION_FAILURE\n";
}
void s2_1_sweeps() {
    WorldRuntime world({1, 2}, 12345);
    world.configure_surface({{}, 3, 1, 0.01}, {}); const auto colony = world.seed_colony();
    const auto ant = world.seed_ant(colony, {}); world.seed_food({0.02, 0, 0}, {1000, 0, 0, 0});
    world.advance_to({6000});
    sweep("late_first_activation", world, [&] { world.start_foraging(ant); });
    world.start_foraging(ant); const auto bytes = world.checkpoint();
    sweep("restore_late_activation", world, [&] { world.restore(bytes); });
    sweep("late_first_decision", world, [&] { world.advance_to({6001}); });
    std::cout << "PASS S2_1_ALLOCATION_FAILURE\n";
}
void s3_sweeps() {
    WorldRuntime world({1,2},9); world.configure_surface({{},3,1,.01},{});
    const auto c = world.seed_colony(); const auto a = world.seed_ant(c,{}), b = world.seed_ant(c,{});
    world.seed_food({.02,0,0},{1000,0,0,0});
    PhysiologySeed seed{{200,200,200,0},1000000000,1000,0};
    sweep("physiology_enable", world, [&] { world.enable_physiology(a,seed); });
    world.enable_physiology(a,seed); world.enable_physiology(b);
    sweep("physiology_program", world, [&] { world.set_behavior(a,IndividualBehavior::Nurse); });
    sweep("nutrition_proposal", world, [&] { world.submit_nutrition({a,{500},NutritionAction::Trophallaxis,b,200}); });
    world.submit_nutrition({a,{500},NutritionAction::Trophallaxis,b,200});
    sweep("nutrition_atomic_transfer", world, [&] { world.advance_to({500}); }); world.advance_to({500});
    sweep("physiology_absorption", world, [&] { world.advance_to({1000}); }); world.advance_to({1000});
    world.set_behavior(a,IndividualBehavior::Forage); world.advance_to({2000});
    sweep("physiology_pause_pending_action", world, [&] { world.set_behavior(a,IndividualBehavior::Paused); });
    sweep("physiology_switch_pending_action", world, [&] { world.set_behavior(a,IndividualBehavior::Nurse); });
    const auto bytes = world.checkpoint(); sweep("physiology_restore", world, [&] { world.restore(bytes); });
    world.schedule_lifecycle(a,{2001},LifeStage::Dead);
    sweep("physiology_cancel_at_death", world, [&] { world.advance_to({2001}); });
    WorldRuntime brood({1,2},8); const auto colony = brood.seed_colony();
    const auto egg = brood.seed_ant(colony,{{},LifeStage::Egg,Caste::Worker,4000});
    PhysiologyConfig config; config.egg_duration = {2}; brood.enable_physiology(egg,{},config);
    sweep("physiology_stage_transition", brood, [&] { brood.advance_to({2}); });
    std::cout << "PASS S3_ALLOCATION_FAILURE\n";
}
void s4_sweeps() {
    WorldRuntime world({4,1},9); GeometryConfig config; const BoxQ room{{2,2,2},{14,22,22}},patch{{14,10,10},{15,14,14}};
    sweep("geometry_configuration",world,[&] { world.configure_geometry(config,std::span{&room,1}); });
    world.configure_geometry(config,std::span{&room,1}); const PositionM point{.006,-.010,.006}; const auto colony=world.seed_colony(point);
    sweep("geometry_actor_index",world,[&] { world.seed_ant(colony,{point,LifeStage::Adult,Caste::Worker,20000}); });
    const auto ant=world.seed_ant(colony,{point,LifeStage::Adult,Caste::Worker,20000}); world.enable_physiology(ant);
    sweep("geometry_proposal",world,[&] { world.submit_soil({ant,{100},SoilAction::Excavate,patch,{},0}); });
    world.submit_soil({ant,{100},SoilAction::Excavate,patch,{},0});
    sweep("geometry_excavate_ledger_energy",world,[&] { world.advance_to({100}); }); world.advance_to({100});
    const SoilParcelRef parcel{world.summary().world,world.soil_parcels().front().id};
    world.submit_soil({ant,{200},SoilAction::Drop,{},parcel,1});
    sweep("geometry_soil_drop",world,[&] { world.advance_to({200}); }); world.advance_to({200});
    world.submit_soil({ant,{300},SoilAction::Pickup,{},parcel,1});
    sweep("geometry_soil_pickup",world,[&] { world.advance_to({300}); }); world.advance_to({300});
    world.submit({ant,{500},ActionKind::Move,{}, {.0055,-.010,.006},0});
    sweep("geometry_loaded_move_index",world,[&] { world.advance_to({500}); }); world.advance_to({500});
    world.submit_soil({ant,{600},SoilAction::Fill,patch,parcel,1});
    sweep("geometry_fill_authority",world,[&] { world.advance_to({600}); }); world.advance_to({600});
    const auto bytes=world.checkpoint(); sweep("geometry_restore_audit",world,[&] { world.restore(bytes); });
    const std::array<PointQ,1> keys{{{1,1,1}}};
    sweep("geometry_cache_rebuild",world,[&] { world.rebuild_geometry_cache(keys); });
    WorldRuntime active({4,2},2); active.configure_geometry(config,std::span{&room,1}); const auto c=active.seed_colony(point);
    const auto a=active.seed_ant(c,{point,LifeStage::Adult,Caste::Worker,20000}); active.enable_physiology(a);
    sweep("geometry_program_activate",active,[&] { active.set_behavior(a,IndividualBehavior::Excavate); }); active.set_behavior(a,IndividualBehavior::Excavate);
    sweep("geometry_local_decision",active,[&] { active.advance_to({1}); }); active.advance_to({1});
    sweep("geometry_program_pause",active,[&] { active.set_behavior(a,IndividualBehavior::Paused); });
    std::cout << "PASS S4_ALLOCATION_FAILURE\n";
}
void s6_sweeps(bool corrected=false) {
    SocialConfig policy; policy.gift_first=corrected; policy.local_work_continuation=corrected;
    WorldRuntime w({6,7},42); const auto c=w.seed_colony();
    const auto a=w.seed_ant(c,{}),b=w.seed_ant(c,{{},LifeStage::Larva});
    for (unsigned i=0;i<24;++i) w.seed_ant(c,{});
    sweep("social_configuration_contact_tree",w,[&]{w.configure_social(policy);}); w.configure_social(policy);
    sweep("contact_tree_seed",w,[&]{w.seed_ant(c,{});});
    w.enable_physiology(a,{{0,400,0,0},1000000000,1000,0}); w.enable_physiology(b);
    sweep("autonomy_enrollment",w,[&]{w.set_autonomy(a);});
    w.submit_nutrition({a,{1},NutritionAction::Trophallaxis,b,100});
    sweep("demand_limited_exchange",w,[&]{w.advance_to({1});}); w.advance_to({1});
    w.submit({a,{1000},ActionKind::Move,{}, {.01,0,0},0});
    sweep("contact_tree_move",w,[&]{w.advance_to({1000});}); w.advance_to({1000});
    w.schedule_lifecycle(a,{1001},LifeStage::Dead);
    sweep("contact_tree_death",w,[&]{w.advance_to({1001});});
    const auto bytes=w.checkpoint(); sweep("contact_tree_restore",w,[&]{w.restore(bytes);});
    WorldRuntime active({6,10},1); active.configure_social(policy); const auto colony=active.seed_colony();
    const auto worker=active.seed_ant(colony,{}),larva=active.seed_ant(colony,{{},LifeStage::Larva});
    active.enable_physiology(worker,{{0,400,0,0},1000000000,1000,0}); active.enable_physiology(larva); active.set_autonomy(worker);
    active.advance_to({4999}); sweep("automatic_program_choice",active,[&]{active.advance_to({5000});}); active.advance_to({5000});
    sweep("automatic_program_pause",active,[&]{active.set_behavior(worker,IndividualBehavior::Paused);});
    active.schedule_lifecycle(worker,{5001},LifeStage::Dead);
    sweep("automatic_death_cancellation",active,[&]{active.advance_to({5001});});
    if(corrected) {
        WorldRuntime gift({61,6},7); gift.configure_social(policy); const auto nest=gift.seed_colony();
        const auto donor=gift.seed_ant(nest,{}),recipient=gift.seed_ant(nest,{{},LifeStage::Larva}),carrier=gift.seed_ant(nest,{});
        gift.enable_physiology(donor,{{0,100,0,0},1000000000,1000,0}); gift.enable_physiology(recipient);
        const auto food=gift.seed_food({}, {200,200,600,0});
        gift.submit({carrier,{1},ActionKind::CollectFood,food,{},1000}); gift.advance_to({1});
        gift.submit({carrier,{2},ActionKind::DeliverFood,{},{},0}); gift.advance_to({2}); gift.set_behavior(donor,IndividualBehavior::Nurse);
        sweep("gift_before_refill_selection",gift,[&]{gift.advance_to({1002});}); gift.advance_to({1002});
        sweep("gift_before_refill_commit",gift,[&]{gift.advance_to({1003});});
    }
    std::cout<<(corrected?"PASS S6_1_ALLOCATION_FAILURE\n":"PASS S6_ALLOCATION_FAILURE\n");
}
} // namespace
int main(int argc, char** argv) {
    // Turn an unexpected noexcept failure into a useful CI failure, not a CRT dialog.
    std::set_terminate([] {
        remaining = -1;
        std::fprintf(stderr, "Unexpected terminate: scenario=%s allocation=%ld\n", current_scenario, current_fault);
        std::_Exit(86);
    });
    try {
        if (argc==2 && std::string_view(argv[1])=="S6.3.3") {
            WorldRuntime w({633,9},7); w.configure_long_term(); w.configure_social();
            sweep("care_contract",w,[&]{w.configure_biology();}); w.configure_biology();
            const auto colony=w.seed_colony(); const auto queen=w.seed_ant(colony,{{},LifeStage::Adult,Caste::Queen});
            const auto larva=w.seed_ant(colony,{{.001,0,0},LifeStage::Larva});
            PhysiologyConfig p; p.basal_nj_per_ms=1; p.active_nj_per_ms=1; p.absorption_period={100000};
            w.enable_physiology(queen,{{0,400,0,0},1000000000,1000,0},p); w.enable_physiology(larva,{},p);
            sweep("queen_care_enrollment",w,[&]{w.enable_brood_care(queen);}); w.enable_brood_care(queen);
            sweep("care_select",w,[&]{w.advance_to({1});}); w.advance_to({1});
            sweep("care_start_and_reserve",w,[&]{w.advance_to({2});}); w.advance_to({2});
            sweep("care_pause",w,[&]{w.pause_brood_care(queen);});
            const auto end=w.pending_events().front().key.time;
            sweep("care_complete",w,[&]{w.advance_to(end);}); w.advance_to(end);
            sweep("care_observer_query",w,[&]{(void)w.behavior_window(queen,{0},w.summary().now);});
            const auto saved=w.checkpoint(); sweep("care_restore",w,[&]{w.restore(saved);});
            std::cout<<"PASS S6.3.3 allocation failure\n"; return 0;
        }
        if (argc==2 && (std::string_view(argv[1])=="S6.3" || std::string_view(argv[1])=="S6.3.1")) {
            WorldRuntime w({63,9},7); w.configure_long_term(); w.configure_social({});
            const auto colony=w.seed_colony(); const auto queen=w.seed_ant(colony,{{},LifeStage::Adult,Caste::Queen});
            PhysiologyConfig p; p.adult_protein_target_ug=20;
            w.enable_physiology(queen,{{0,100,0,0},1500000000,1600,0},p);
            ReproductionConfig r; r.interval={1};
            if (std::string_view(argv[1])=="S6.3.1") r.maintenance_horizon={1};
            sweep("enable_maternal_allocation",w,[&]{w.enable_reproduction(queen,r);});
            w.enable_reproduction(queen,r);
            const auto food=w.seed_food({},{1,1,1,0}); ResourceCycleConfig c; c.reserve={10,10,10,0}; c.release_limit={1,1,1,0}; c.interval={1};
            sweep("configure_finite_reserve",w,[&]{w.configure_resource_cycle(food,c);}); w.configure_resource_cycle(food,c);
            sweep("fund_birth_and_release",w,[&]{w.advance_to({1});}); w.advance_to({1});
            const auto saved=w.checkpoint(); sweep("restore_birth_evidence",w,[&]{w.restore(saved);});
            std::cout<<"PASS "<<argv[1]<<" allocation failure\n"; return 0;
        }
        if (argc == 2 && std::string_view(argv[1]) == "S6") { s6_sweeps(); return 0; }
        if (argc == 2 && std::string_view(argv[1]) == "S6.1") { s6_sweeps(true); return 0; }
        if (argc == 2 && std::string_view(argv[1]) == "S5") {
            WorldRuntime world({5,1},5);world.seed_colony();
            const PlaceFoodCommand command{{5,1},{1,2},{},{100,50,25,0}};
            sweep("place_food_command_and_receipt",world,[&]{world.place_food(command);});world.place_food(command);
            const auto saved=world.checkpoint();sweep("restore_command_receipt",world,[&]{world.restore(saved);});
            std::cout<<"PASS S5_ALLOCATION_FAILURE\n";return 0;
        }
        if (argc == 2 && std::string_view(argv[1]) == "S4") { s4_sweeps(); return 0; }
        if (argc == 2 && std::string_view(argv[1]) == "S3") { s3_sweeps(); return 0; }
        if (argc == 2 && std::string_view(argv[1]) == "S2.1") { s2_1_sweeps(); return 0; }
        if (argc == 2 && std::string_view(argv[1]) == "S2") { s2_sweeps(); return 0; }
        if (argc != 1) throw std::invalid_argument("usage: antworld_allocation_tests [S2]");
        // ENGINEERING_FIXTURE: no biological parameter is inferred here.
        WorldRuntime world({1, 2}, 12345); const auto colony = world.seed_colony();
        const auto a = world.seed_ant(colony, {}); const auto b = world.seed_ant(colony, {});
        const auto food = world.seed_food({}, {1000, 1000, 1000, 1000});
        sweep("seed_ant", world, [&] { world.seed_ant(colony, {}); });
        sweep("seed_colony", world, [&] { world.seed_colony(); });
        sweep("seed_food", world, [&] { world.seed_food({}, {1, 2, 3, 4}); });
        for (int i = 0; i < 6; ++i) world.seed_ant(colony, {});
        sweep("grow_ant_columns", world, [&] { world.seed_ant(colony, {}); });
        sweep("schedule", world, [&] { world.schedule({{5}}); });
        sweep("submit", world, [&] { world.submit({a, {10}, ActionKind::CollectFood, food, {}, 3000}); });
        const auto diagnostic = world.schedule({{1}, Phase::Environment, 0, 0, 0, DiagnosticAction::DrawRandom});
        sweep("cancel", world, [&] { world.cancel(diagnostic); });
        world.submit({a, {2}, ActionKind::CollectFood, food, {}, 3000});
        world.submit({b, {2}, ActionKind::CollectFood, food, {}, 3000});
        world.submit({a, {1000}, ActionKind::Move, {}, {0.001, 0, 0}, 0});
        world.schedule_lifecycle(b, {1001}, LifeStage::Dead);
        sweep("advance", world, [&] { world.advance_to({2000}); });
        const auto loaded = world.checkpoint();
        sweep("restore", world, [&] { world.restore(loaded); });
        std::cout << "PASS S1_ALLOCATION_FAILURE\n"; return 0;
    } catch (const std::exception& e) { remaining = -1; std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
