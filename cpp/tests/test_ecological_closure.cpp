#include "ecological_recruitment_fixture.hpp"
#include "wp6b_fixture.hpp"
#include "antworld/storage/store.hpp"
#include <algorithm>
#include <filesystem>
#include <iostream>

namespace {
using namespace antworld;
using antworld::wp6b::require;
template<class F> void rejects(F action) {
    try { action(); }
    catch (const std::exception&) { return; }
    throw std::runtime_error("expected ecological transaction to fail");
}

void trail_evidence() {
    ForagerState f;
    f.path_size=1;
    LocalObservation local;
    local.step_count=1;
    local.steps[0]={{1,0},Direction::East,1.0};
    BehaviorConfig cfg;
    cfg.trail_weight=0;
    const auto old=choose_behavior(1,{1},false,f,local,cfg);
    const auto blind=choose_behavior(1,{1},false,f,local,cfg,true);
    require(old.mode==BehaviorMode::FollowTrail && blind.mode==BehaviorMode::Explore &&
            blind.trail_evidence==1 && old.destination==blind.destination,"blind cue falsely influenced choice");
    cfg.trail_weight=180;
    const auto weighted=choose_behavior(1,{1},false,f,local,cfg,true);
    require(weighted.mode==BehaviorMode::FollowTrail && weighted.trail_evidence==7,"weighted edge missing evidence");
}

void local_causality() {
    auto a=ecological_assay::recruitment(1,"scout");
    auto b=ecological_assay::recruitment(1,"disabled");
    auto c=ecological_assay::recruitment(1,"depleted");
    for (auto* scene:{&a,&b,&c}) scene->world.advance_to({120000});
    const auto has=[](const auto& scene,FactKind kind,AntRef actor) {
        const auto facts=scene.world.committed_events();
        return std::any_of(facts.begin(),facts.end(),[&](const auto& f) { return f.kind==kind && f.actor==actor.id; });
    };
    require(has(a,FactKind::RecruitmentCue,a.scout) && has(b,FactKind::RecruitmentCue,b.scout),"scout did not really return");
    for (auto receiver:a.receivers) {
        require(has(a,FactKind::RecruitmentActivated,receiver) && has(a,FactKind::FoodDelivered,receiver),"recruited worker failed to bring food");
        require(has(b,FactKind::RecruitmentObserved,receiver) && !has(b,FactKind::RecruitmentActivated,receiver) &&
                !has(b,FactKind::FoodDelivered,receiver),"disabled response activated the worker");
        require(!has(c,FactKind::FoodDelivered,receiver),"depleted food reappeared");
    }
}

void authority() {
    auto a=ecological_assay::recruitment(1,"scout");
    a.world.advance_to({30000});
    const auto first=a.world.checkpoint();
    require(first[6]=='M',"ecological checkpoint silently uses an older identity");
    const auto directory=std::filesystem::path("ecological-test-saves");
    std::filesystem::create_directories(directory);
    const auto db=directory/"recruitment.sqlite";
    std::filesystem::remove(db);
    {
    storage::Store s(db,{},storage::StoreFormat::Segmented);
    const auto initial=s.save(a.world);
    auto restored=s.load(a.scout.world);
    require(restored.world.checkpoint()==first,"live cue lost after segmented restoration");
    restored.world.advance_to({40001});
    restored.world.advance_to({80000});
    a.world.advance_to({80000});
    const auto last=a.world.checkpoint();
    require(restored.world.checkpoint()==last,"split playback differs");
    storage::SaveOptions fault;
    fault.fault_hook=[](auto stage) {
        if (stage==storage::SaveStage::AfterManifest) throw std::runtime_error("injected write failure");
    };
    rejects([&] { (void)s.save(a.world,initial,fault); });
    require(s.load(a.scout.world).world.checkpoint()==first,"failure changed the published generation");
    const auto next=s.save(a.world,initial);
    require(s.recover(a.scout.world,initial.generation,next.generation).world.checkpoint()==last,
            "ecological fact schemas failed generation replay");
    }
    std::filesystem::remove(db);
    RuntimeLimits small;
    small.committed_events=80;
    auto limited=ecological_assay::recruitment(1,"scout",small);
    const auto before=limited.world.checkpoint();
    rejects([&] { limited.world.advance_to({120000}); });
    require(limited.world.checkpoint()==before,"failed advance left changes in authority");
}

void paid_motion() {
    WorldConfig cfg;
    cfg.continuous_spatial_motion=true;
    WorldRuntime w({44,55},7,cfg);
    EcologicalClosureConfig ecology;
    ecology.distance_clock=ecology.activity_cost=true;
    w.configure_ecological_closure(ecology);
    BehaviorConfig behavior;
    behavior.trails_enabled=false;
    w.configure_surface({{0,0,0},3,1,.01},{},behavior);
    auto colony=w.seed_colony();
    auto a=w.seed_ant(colony,{});
    w.seed_food({.01,0,0},{100,0,0,0});
    PhysiologyConfig p;
    p.basal_nj_per_ms=1;
    p.active_nj_per_ms=20;
    p.water_loss_ug_per_period=0;
    w.enable_physiology(a,{{},1000,1000,0},p);
    w.start_foraging(a);
    w.advance_to({20});
    auto at=w.query_physiology(a);
    require(at->active_work->value && at->dissipated_energy_nj==400 && w.query_ant(a)->position==PositionM{},
            "pending work did not spend the declared rate");
    const auto middle=w.checkpoint();
    WorldRuntime other({44,55},7);
    other.restore(middle);
    other.advance_to({3000});
    w.advance_to({3000});
    require(w.checkpoint()==other.checkpoint() && w.query_ant(a)->stage==LifeStage::Dead &&
            w.query_physiology(a)->dissipated_energy_nj==1000 &&
            w.query_ant(a)->position==PositionM{},"death boundary did not cancel work exactly");
}
} // namespace

int main(int argc,char** argv) {
    try {
        if (argc!=2) return 1;
        const std::string_view name=argv[1];
        if (name=="trail") trail_evidence();
        else if (name=="scout") local_causality();
        else if (name=="restore") authority();
        else if (name=="activity") paid_motion();
        else return 1;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
