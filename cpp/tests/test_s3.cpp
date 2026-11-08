#include "s3_fixture.hpp"
#include <algorithm>
#include <iostream>
#include <string_view>

using namespace antworld;
using namespace antworld::s3_fixture;
namespace {
template <typename Fn> void rejects(Fn fn) {
    bool rejected = false; try { fn(); } catch (const std::exception&) { rejected = true; }
    require(rejected, "invalid operation was accepted");
}
void initialization() {
    WorldRuntime w({1,3}, 2); const auto c = w.seed_colony(); const auto a = w.seed_ant(c, {});
    const auto before = w.checkpoint(); PhysiologyConfig cfg; cfg.absorption_period = {0};
    rejects([&] { w.enable_physiology(a, {}, cfg); });
    require(before == w.checkpoint(), "invalid setup mutated state");
    w.enable_physiology(a, {{10,20,30,40}, 1000000000, 1000, 0});
    const auto seeded = w.checkpoint(); rejects([&] { w.enable_physiology(a); });
    rejects([&] { w.enable_physiology({{9,9},a.id}); });
    require(w.checkpoint() == seeded, "duplicate initialization mutated state");
    require(w.query_physiology(a)->body_energy_j() == 1.0 && w.query_ant(a)->carried_food == FoodMass{}, "crop/body/parcel mixed");
    balanced(w); roundtrip(w);
    const auto prior = w.checkpoint();
    rejects([&] { w.seed_food({}, {UINT64_MAX,0,0,0}); });
    require(w.checkpoint() == prior, "combined nutrition capacity rejection was not atomic");
    w.advance_to({123}); const auto queried = w.checkpoint();
    for (unsigned i = 0; i < 20; ++i) { (void)w.query_physiology(a); (void)w.nutrition_snapshot(); }
    require(w.checkpoint() == queried, "physiology reads mutate state"); roundtrip(w);
}
void integration() {
    for (auto pulse : {250,1000,2000}) {
        WorldRuntime w({1,3}, 2); const auto c = w.seed_colony(); const auto a = w.seed_ant(c, {});
        PhysiologyConfig cfg; cfg.absorption_period = {pulse}; cfg.water_loss_ug_per_s = 3;
        w.enable_physiology(a, {{100,0,100,0},1000000000,1000,0}, cfg);
        WorldRuntime copy({1,4}, 0); copy.restore(w.checkpoint());
        w.advance_to({10333}); for (std::int64_t t = 17; t < 10333; t += 137) copy.advance_to({t}); copy.advance_to({10333});
        require(w.checkpoint() == copy.checkpoint(), "AdvanceTo partition changed physiology");
        const auto p = *w.query_physiology(a);
        require(p.dissipated_energy_nj == 10333000 && p.lost_water_ug == 30 && p.water_loss_remainder == 999, "analytic consumption incorrect");
        balanced(w); roundtrip(w);
    }
}
void exchange() {
    unsigned first_wins = 0;
    for (std::uint64_t seed = 1; seed <= 64; ++seed) for (auto capacity : {0U,100U,1000U}) {
        Exchange a(seed, capacity, true, false), b(seed, capacity, true, true);
        a.world.advance_to({500}); b.world.advance_to({500});
        const auto p = *a.world.query_physiology(a.recipient);
        require(p.crop.total_ug() == std::min<std::uint64_t>(capacity,400), "partial transfer or capacity broken");
        require(a.world.query_physiology(a.first)->crop == b.world.query_physiology(b.first)->crop &&
            p.crop == b.world.query_physiology(b.recipient)->crop, "submission order determines recipient inventory");
        if (capacity == 100 && a.world.query_physiology(a.first)->crop.total_ug() < 200) ++first_wins;
        balanced(a.world); roundtrip(a.world);
    }
    require(first_wins > 16 && first_wins < 48, "persistent donor ID privilege");
    Exchange empty(1,1000,false,false); empty.world.advance_to({500});
    require(empty.world.query_physiology(empty.recipient)->crop.total_ug() == 0, "empty donor fabricated nutrients"); roundtrip(empty.world);
}
void constraints() {
    for (unsigned condition = 0; condition < 5; ++condition) {
        WorldRuntime w({1,3}, 4); const auto c = w.seed_colony(), other = w.seed_colony();
        const auto a = w.seed_ant(c, {});
        AntSeed seed; if (condition == 0) seed.position.x = .01;
        if (condition == 1) seed.stage = LifeStage::Egg;
        if (condition == 2) seed.stage = LifeStage::Pupa;
        const auto b = w.seed_ant(condition == 3 ? other : c, seed);
        w.enable_physiology(a, {{100,100,100,100},1000000000,1000,0}); w.enable_physiology(b);
        if (condition == 4) w.schedule_lifecycle(b,{500},LifeStage::Dead);
        w.submit_nutrition({a,{500},NutritionAction::Trophallaxis,b,100}); w.advance_to({500});
        require(w.query_physiology(a)->crop.total_ug() == 400 && w.query_physiology(b)->crop.total_ug() == 0, "illegal contact/stage transfer");
        balanced(w); roundtrip(w);
    }
}
void ingestion() {
    WorldRuntime w({1,3}, 2); const auto c = w.seed_colony(); const auto a = w.seed_ant(c, {});
    const auto food = w.seed_food({}, {400,200,300,100}); w.enable_physiology(a);
    w.submit({a,{10},ActionKind::CollectFood,food,{},1000}); w.advance_to({10});
    w.submit_nutrition({a,{20},NutritionAction::IngestCargo,{},200}); w.advance_to({20});
    require(w.query_ant(a)->carried_food.total_ug() == 800 && w.query_physiology(a)->crop.total_ug() == 200, "ingestion duplicated cargo");
    w.submit({a,{30},ActionKind::DeliverFood,{},{},0}); w.advance_to({30});
    w.submit_nutrition({a,{40},NutritionAction::WithdrawNest,{},1000}); w.advance_to({40});
    require(w.query_colony(c)->nest_food.total_ug() == 0 && w.query_physiology(a)->crop.total_ug() == 1000, "physical nest withdrawal incorrect");
    w.advance_to({1000}); require(w.query_physiology(a)->oxidized_carbs_ug == 10, "carbohydrate was not actually absorbed");
    require(w.query_physiology(a)->tissue_protein_ug == 0, "adult uses larval growth rules"); balanced(w); roundtrip(w);
}
void thresholds() {
    for (bool water : {false,true}) {
        WorldRuntime w({1,3}, 2); const auto c = w.seed_colony(); const auto a = w.seed_ant(c, {});
        PhysiologyConfig cfg; cfg.water_loss_ug_per_s = water ? 1000U : 0U;
        w.enable_physiology(a, {{100,0,100,0}, water ? UINT64_C(1000000000) : UINT64_C(250001),water ? 251U : 1000U,0},cfg);
        w.submit({a,{251},ActionKind::Rest,{},{},0}); w.advance_to({10000});
        require(w.query_ant(a)->stage == LifeStage::Dead, "depletion did not kill before action");
        unsigned deaths = 0, rests = 0;
        for (const auto& e : w.committed_events()) {
            if (e.kind == FactKind::AntDied) { ++deaths; require(e.time == SimTime{251}, "threshold not located at first millisecond"); }
            if (e.kind == FactKind::Rested) ++rests;
        }
        require(deaths == 1 && rests == 0 && w.pending_events().empty(), "dead individual acts or has autonomous work");
        balanced(w); roundtrip(w);
    }
}
void lifecycle() {
    for (bool protein : {false,true}) {
        Brood b(17,protein,true); const auto ids = b.brood;
        rejects([&] { b.world.schedule_lifecycle(ids[0],{2},LifeStage::Larva); });
        b.world.advance_to({180000}); unsigned transitions = 0;
        for (const auto& e : b.world.committed_events()) if (e.kind == FactKind::StageChanged) ++transitions;
        for (const auto id : ids) require(b.world.query_ant(id)->id == id.id && b.world.query_ant(id)->stage ==
            (protein ? LifeStage::Adult : LifeStage::Larva), "nutrition or continuous identity gate failed");
        require(transitions == (protein ? 12U : 4U) && b.world.summary().ant_count == 6, "emergence duplicates identity/events");
        balanced(b.world); roundtrip(b.world);
    }
}
void behavior() {
    WorldRuntime w({1,3}, 10); w.configure_surface({{},4,1,.01},{}); const auto c = w.seed_colony(); const auto a = w.seed_ant(c,{});
    w.seed_food({.03,0,0},{1000,0,0,0}); w.enable_physiology(a); w.start_foraging(a); w.advance_to({1500});
    const auto before = *w.query_forager(a); const auto energy = w.query_physiology(a)->body_energy_nj;
    w.set_behavior(a,IndividualBehavior::Paused); w.advance_to({4000});
    require(w.query_forager(a)->path == before.path && w.query_forager(a)->decisions == before.decisions &&
        w.query_physiology(a)->body_energy_nj < energy, "pause erased route or stopped physiology"); roundtrip(w);
    w.set_behavior(a,IndividualBehavior::Rest); w.advance_to({5500}); roundtrip(w);
    w.set_behavior(a,IndividualBehavior::Nurse); w.advance_to({7000}); roundtrip(w);
    w.set_behavior(a,IndividualBehavior::Forage); w.advance_to({18000});
    require(w.surface_snapshot().counters.deliveries > 0, "resumed worker cannot use its real return trace");
    w.schedule_lifecycle(a,{18001},LifeStage::Dead); w.advance_to({18001}); roundtrip(w); balanced(w);
}
void replay() {
    Brood b(8,true,true); b.world.advance_to({34567}); roundtrip(b.world);
    WorldRuntime copy({1,2},0); copy.restore(b.world.checkpoint()); b.world.advance_to({180000});
    for (std::int64_t at = 35001; at < 180000; at += 1237) { copy.advance_to({at}); }
    copy.advance_to({180000});
    require(copy.checkpoint() == b.world.checkpoint(), "saved continuation differs");
    auto bytes = copy.checkpoint(); const auto before = bytes;
    // Corrupt a physiological enum with a valid checksum: not merely a torn save.
    bytes[bytes.size()-9] = 255;
    std::uint64_t hash = UINT64_C(14695981039346656037);
    for (std::size_t i = 0; i < bytes.size()-8; ++i) hash = (hash^bytes[i])*UINT64_C(1099511628211);
    for (unsigned i = 0; i < 8; ++i) bytes[bytes.size()-8+i] = static_cast<std::uint8_t>(hash>>(8*i));
    rejects([&] { copy.restore(bytes); }); require(copy.checkpoint() == before, "failed restore changed world");
}
void rollback() {
    RuntimeLimits limits; limits.committed_events = 14;
    WorldRuntime w({1,3}, 2,{},limits); const auto c = w.seed_colony(); const auto a = w.seed_ant(c,{}), b = w.seed_ant(c,{});
    w.enable_physiology(a,{{100,100,100,100},1000000000,1000,0}); w.enable_physiology(b);
    w.submit_nutrition({a,{500},NutritionAction::Trophallaxis,b,200}); const auto before = w.checkpoint();
    rejects([&] { w.advance_to({10000}); }); require(w.checkpoint() == before, "failed AdvanceTo lost atomic nutrition rollback");
}
void locality() {
    for (bool near : {false,true}) {
        WorldRuntime w({1,3},7); const auto c = w.seed_colony(); const auto a = w.seed_ant(c,{});
        const auto larva = w.seed_ant(c,{{near ? 0.0 : .01,0,0},LifeStage::Larva,Caste::Worker,4000});
        w.enable_physiology(a,{{100,400,400,100},1000000000,1000,0}); w.enable_physiology(larva);
        w.set_behavior(a,IndividualBehavior::Nurse); w.advance_to({20000});
        const auto p = *w.query_physiology(larva);
        require(near ? p.tissue_protein_ug == 100 : p.tissue_protein_ug == 0, "nursing consulted distant brood needs");
        balanced(w); roundtrip(w);
    }
    Brood a(11,true,false), b(11,true,false); a.world.advance_to({180000}); b.world.advance_to({180000});
    require(a.world.checkpoint() == b.world.checkpoint(), "local nursing is not deterministic");
}
void corruption() {
    Brood b(3,true,true); b.world.advance_to({32123}); const auto original = b.world.checkpoint();
    WorldRuntime restored({1,1},0); restored.restore(original);
    // Last row is 362 bytes: alter each stored budget, remainder and scheduler field.
    for (const auto offset : {0U, 144U, 200U, 232U, 240U, 248U, 256U, 264U, 272U, 280U, 288U, 296U, 304U, 312U, 320U, 328U, 336U, 344U, 352U, 360U, 361U}) {
        auto bytes = original; const auto index = bytes.size()-8-362+offset; bytes[index] ^= 128;
        std::uint64_t hash = UINT64_C(14695981039346656037);
        for (std::size_t i = 0; i < bytes.size()-8; ++i) hash = (hash^bytes[i])*UINT64_C(1099511628211);
        for (unsigned i = 0; i < 8; ++i) bytes[bytes.size()-8+i] = static_cast<std::uint8_t>(hash>>(8*i));
        rejects([&] { restored.restore(bytes); }); require(restored.checkpoint() == original, "semantic corruption changed live world");
    }
}
void allocation_limit() {
    Brood b(43,true,true); b.world.advance_to({180000});
    unsigned adults = 0, larvae = 0; std::uint64_t unused_protein = 0;
    for (const auto id : b.brood) {
        const auto ant = *b.world.query_ant(id); const auto p = *b.world.query_physiology(id);
        if (ant.stage == LifeStage::Adult) ++adults;
        if (ant.stage == LifeStage::Larva) { ++larvae; require(p.tissue_protein_ug == 80, "retained negative fixture changed"); }
        unused_protein += p.crop.protein_ug;
    }
    require(adults == 3 && larvae == 1 && unused_protein == 420, "surplus redistribution was silently introduced");
    balanced(b.world); roundtrip(b.world);
}
}
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: antworld_s3_tests CASE");
        const std::string_view name(argv[1]);
        if (name == "INITIALIZATION") initialization(); else if (name == "INTEGRATION") integration();
        else if (name == "EXCHANGE") exchange(); else if (name == "CONSTRAINTS") constraints();
        else if (name == "INGESTION") ingestion(); else if (name == "THRESHOLDS") thresholds();
        else if (name == "LIFECYCLE") lifecycle(); else if (name == "BEHAVIOR") behavior();
        else if (name == "REPLAY") replay(); else if (name == "ROLLBACK") rollback();
        else if (name == "LOCALITY") locality(); else if (name == "CORRUPTION") corruption();
        else if (name == "ALLOCATION_LIMIT") allocation_limit();
        else throw std::invalid_argument("unknown S3 test");
        std::cout << "PASS " << name << '\n';
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
