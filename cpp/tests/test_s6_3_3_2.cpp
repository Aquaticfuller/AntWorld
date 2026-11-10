#include "s6_3_3_fixture.hpp"
#include "antworld/storage/store.hpp"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <string_view>

using namespace antworld;
using namespace s6_3_3_fixture;

namespace {
SpeciesCareProfile motion_profile(bool integrated=false) {
    SpeciesCareProfile profile;
    profile.local_retrieval=true;
    profile.motion.emplace();
    profile.motion->integrate_autonomy=integrated;
    profile.care_probability=1; // ENGINEERING_FIXTURE deterministic engineering assertions.
    profile.worker_contact_probability=0;
    return profile;
}

SimTime pending(const WorldRuntime& world,ScheduledId id) {
    for (const auto& event:world.pending_events()) if (event.id==id) return event.key.time;
    throw std::runtime_error("missing owned event");
}

void until_act(WorldRuntime& world,AntRef ref,CareAct act) {
    for (unsigned i=0;i<512;++i) {
        const auto state=world.query_care(ref);
        if (state && state->active && state->act==act) return;
        const auto events=world.pending_events();
        require(!events.empty(),"care exhausted its schedule");
        world.advance_to(events.front().key.time);
    }
    throw std::runtime_error("expected care act not reached");
}

std::size_t completed(const WorldRuntime& w,AntRef a,CareAct act) {
    const auto facts=w.committed_events();
    return static_cast<std::size_t>(std::count_if(facts.begin(),facts.end(),[&](const WorldEvent& e) {
        return e.kind==FactKind::BiologicalObservation && e.actor==a.id &&
               e.observation.act==act && e.observation.phase==ObservationPhase::Completed;
    }));
}

void motion(const std::filesystem::path& database) {
    Fixture f(7,motion_profile(),0);
    const auto target=f.w.seed_ant(f.colony,{{.004,0,0},LifeStage::Larva});
    std::vector<std::uint8_t> loaded;
    for (const auto act:{CareAct::ApproachBrood,CareAct::PickUpBrood,CareAct::TransportBrood,CareAct::PlaceBrood}) {
        until_act(f.w,f.queen,act);
        const auto c=*f.w.query_care(f.queen);
        const auto finish=pending(f.w,c.pending);
        const auto duration=finish.milliseconds-c.began_at.milliseconds;
        const auto a=f.w.query_ant(f.queen)->position;
        const auto before=f.w.query_ant(target)->position;
        if (act==CareAct::PickUpBrood || act==CareAct::PlaceBrood)
            require(duration==500,"manipulation reused the translation clock");
        else {
            const auto step=std::hypot(c.destination.x-a.x,c.destination.y-a.y,c.destination.z-a.z);
            const auto speed=act==CareAct::TransportBrood?.003:.006;
            require(duration==static_cast<std::int64_t>(std::ceil(step*1000/speed)) && duration<1000,
                    "translation duration does not use the independent speed");
        }
        const auto bytes=f.w.checkpoint();
        WorldRuntime restored({1,1},1,{},limits());
        restored.restore(bytes);
        require(restored.checkpoint()==bytes,"active motion checkpoint changed");
        if (act==CareAct::TransportBrood) loaded=bytes;
        f.w.advance_to({finish.milliseconds-1});
        require(f.w.query_ant(target)->position==before,"brood moved before the physical segment completed");
        f.w.advance_to(finish);
        restored.advance_to(finish);
        require(f.w.checkpoint()==restored.checkpoint(),"timed motion continuation diverged");
        if (act==CareAct::PickUpBrood) {
            require(f.w.query_care(f.queen)->carrying_brood && f.w.query_ant(target)->position==before,
                    "pickup failed to hold a real target without moving it");
            auto forged=f.w.checkpoint();
            forged.at(forged.size()-11)=0; // Held flag precedes returning, search budget and checksum.
            std::uint64_t digest=14695981039346656037ULL;
            for (std::size_t i=0;i<forged.size()-8;++i) digest=(digest^forged[i])*1099511628211ULL;
            for (unsigned i=0;i<8;++i) forged[forged.size()-8+i]=static_cast<std::uint8_t>(digest>>(8*i));
            bool rejected=false;
            try { restored.restore(forged); } catch (const std::invalid_argument&) { rejected=true; }
            require(rejected && restored.checkpoint()==f.w.checkpoint(),"unaudited custody change restored");
        }
    }
    require(!f.w.query_care(f.queen)->carrying_brood && completed(f.w,f.queen,CareAct::PlaceBrood)==1,
            "placement did not release exclusive custody");
    require(f.w.query_ant(target)->position.x<=f.w.config().contact_distance_m,"brood was placed outside shelter");
    WorldRuntime loaded_world({2,2},2,{},limits());
    loaded_world.restore(loaded);
    storage::Store store(database,limits());
    (void)store.save(loaded_world);
    auto recovered=store.load(f.w.summary().world);
    require(recovered.world.checkpoint()==loaded,"durable loaded checkpoint differs");
    const auto end=f.w.summary().now;
    recovered.world.advance_to(end);
    require(recovered.world.checkpoint()==f.w.checkpoint(),"durable loaded continuation differs");
    conserved(f.w);
}

void foreign() {
    for (const bool neutral:{false,true}) {
        Fixture f(7,{},0,0,false,CareContext::FoundingQueen,{},false);
        f.w.configure_biology(motion_profile(),{21,.8,neutral,.025});
        const auto donor=f.w.seed_colony({.02,0,0});
        const auto larva=f.w.seed_ant(donor,{{.004,0,0},LifeStage::Larva});
        const auto egg=f.w.seed_ant(donor,{{.005,0,0},LifeStage::Egg});
        f.w.enable_brood_care(f.queen);
        f.w.advance_to({15000});
        require(completed(f.w,f.queen,CareAct::PlaceBrood)==static_cast<std::size_t>(neutral),
                "foreign displacement leaked across contexts");
        require(f.w.query_ant(larva)->colony==donor.id && f.w.query_ant(egg)->position.x==.005,
                "retrieval changed membership or carried unsupported foreign stage");
        require(!completed(f.w,f.queen,CareAct::FeedBrood),"neutral retrieval fed foreign brood");
        const auto bytes=f.w.checkpoint();
        f.w.restore(bytes);
        require(f.w.checkpoint()==bytes,"foreign-target evidence did not restore");
        conserved(f.w);
    }
}

void competing() {
    Fixture f(137,motion_profile(),0,2);
    f.w.pause_brood_care(f.queen);
    const auto b=f.w.seed_ant(f.colony,{{.003,0,-.00025},LifeStage::Larva});
    const auto p=physiology();
    for (auto worker:f.workers) {
        f.w.enable_physiology(worker,{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
        f.w.enable_brood_care(worker,{CareContext::Worker,{}});
    }
    f.w.advance_to({2500});
    std::size_t picked=0,placed=0,rejected=0;
    for (auto worker:f.workers) {
        picked+=completed(f.w,worker,CareAct::PickUpBrood);
        placed+=completed(f.w,worker,CareAct::PlaceBrood);
    }
    for (const auto& e:f.w.committed_events())
        if (e.kind==FactKind::BiologicalObservation && e.observation.target==b.id &&
            e.observation.act==CareAct::PickUpBrood && e.outcome==Outcome::DuplicateAction) ++rejected;
    require(picked==1 && placed==1 && rejected==1,"simultaneous pickup did not resolve as one physical load");
    conserved(f.w);
}

void geometry() {
    WorldRuntime w({6332,7},7,{},limits());
    w.configure_long_term(); w.configure_social(); w.configure_biology(motion_profile());
    GeometryConfig g;
    const BoxQ tunnel{{2,10,10},{28,14,14}};
    w.configure_geometry(g,std::span{&tunnel,1});
    const auto pos=[&](int x) { return PositionM{static_cast<double>(x)*g.quantum_m,-.010,.006}; };
    const auto colony=w.seed_colony(pos(12));
    const auto queen=w.seed_ant(colony,{pos(12),LifeStage::Adult,Caste::Queen});
    const auto target=w.seed_ant(colony,{pos(19),LifeStage::Larva});
    const auto digger=w.seed_ant(colony,{pos(12),LifeStage::Adult,Caste::Worker,20000});
    const auto p=physiology();
    for (auto a:{queen,digger}) w.enable_physiology(a,{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
    w.enable_brood_care(queen);
    w.submit_soil({digger,{102},SoilAction::Excavate,{{10,14,10},{14,15,14}},{},0});
    until_act(w,queen,CareAct::TransportBrood);
    const auto previous=w.query_ant(target)->position;
    require(w.query_care(queen)->carrying_brood && w.soil_parcels().size()==1,"geometry fixture did not hold a load");
    const SimTime fill{w.summary().now.milliseconds+g.work_duration.milliseconds};
    w.submit_soil({digger,fill,SoilAction::Fill,{{14,10,10},{15,14,14}},{w.summary().world,w.soil_parcels().front().id},1});
    w.advance_to(fill);
    require(!w.query_care(queen)->carrying_brood,"new wall kept a stale loaded reservation");
    w.advance_to({fill.milliseconds+5000});
    require(w.query_ant(target)->position==previous && w.geometry_edits().size()==2,"loaded brood crossed a closed passage");
    const auto bytes=w.checkpoint();
    w.restore(bytes);
    require(w.checkpoint()==bytes,"post-wall world did not round trip");
    conserved(w);
}

void lifecycle() {
    Fixture f(7,motion_profile(),0);
    const auto b=f.w.seed_ant(f.colony,{{.004,0,0},LifeStage::Larva});
    until_act(f.w,f.queen,CareAct::TransportBrood);
    const auto at=f.w.query_ant(b)->position;
    const SimTime death{f.w.summary().now.milliseconds+1};
    f.w.schedule_lifecycle(b,death,LifeStage::Dead);
    f.w.advance_to(death);
    require(!f.w.query_care(f.queen)->carrying_brood && !f.w.query_ant(b)->alive(),
            "a dead target remained in physical custody");
    const auto saved=f.w.checkpoint();
    f.w.restore(saved);
    f.w.advance_to({10000});
    require(f.w.query_ant(b)->position==at && completed(f.w,f.queen,CareAct::PlaceBrood)==0,
            "lifecycle cancellation allowed later motion");
    conserved(f.w);
}

void autonomy() {
    WorldRuntime world({6332,19},19,{{-.01,-.01,-.01},{.01,.01,.01},.08,.002},limits());
    world.configure_long_term();
    BehaviorConfig forage;
    forage.step_duration={100}; forage.route_capacity=8; forage.max_trip_moves=8;
    world.configure_surface({{-.006,0,0},13,1,.001},{},forage);
    SocialConfig social; social.decision_interval={500}; social.minimum_program_time={500};
    social.rest_weight=4; social.forage_weight=8; social.nurse_weight=20;
    world.configure_social(social);
    const auto colony=world.seed_colony();
    const auto worker=world.seed_ant(colony,{});
    const auto brood=world.seed_ant(colony,{{.004,0,0},LifeStage::Larva});
    const auto p=physiology();
    world.enable_physiology(worker,{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
    world.enable_physiology(brood,{},p);
    world.set_autonomy(worker,true);
    world.configure_biology(motion_profile(true));
    (void)world.seed_food({-.001,0,0},{5000,1000,200,0});
    until_act(world,worker,CareAct::TransportBrood);
    const auto saved=world.checkpoint();
    WorldRuntime replay({1,1},1,{},limits()); replay.restore(saved);
    const SimTime end{world.summary().now.milliseconds+30000};
    world.advance_to(end); replay.advance_to(end);
    require(world.checkpoint()==replay.checkpoint() && world.query_autonomy(worker)->enabled,
            "worker lost its autonomous identity or deterministic continuation");
    require(completed(world,worker,CareAct::PlaceBrood)>0 && world.query_ant(brood)->colony==colony.id,
            "ordinary worker autonomy never committed local brood placement");
    bool care_ended=false,foraged_after=false;
    for (const auto& e:world.committed_events()) if (e.actor==worker.id) {
        if (e.kind==FactKind::CareProgramChanged && !e.payload) care_ended=true;
        if (care_ended && e.kind==FactKind::ForagingDecision) foraged_after=true;
    }
    require(care_ended && foraged_after,"care failed to yield to ordinary foraging");
    conserved(world);
}

void reproduction() {
    WorldRuntime world({6332,43},43,{},limits());
    world.configure_long_term();
    SocialConfig social; social.decision_interval={100};
    world.configure_social(social);
    world.configure_biology(motion_profile(true));
    const auto colony=world.seed_colony();
    const auto queen=world.seed_ant(colony,{{},LifeStage::Adult,Caste::Queen});
    world.seed_ant(colony,{{.004,0,0},LifeStage::Larva});
    auto p=physiology(); p.adult_protein_target_ug=20;
    world.enable_physiology(queen,{{0,500,0,0},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
    world.set_autonomy(queen,true);
    ReproductionConfig r; r.interval={600};
    world.enable_reproduction(queen,r);
    world.advance_to({600});
    require(world.query_reproduction(queen)->births==1 && world.query_autonomy(queen)->enabled,
            "maternal care prevented a funded reproductive attempt");
    const auto c=world.query_care(queen);
    require(c && !c->enabled && !c->carrying_brood,"funded laying left an overlapping maternal act");
    bool interrupted=false;
    for (const auto& e:world.committed_events()) if (e.kind==FactKind::BiologicalObservation && e.actor==queen.id &&
        e.time==SimTime{600} && e.observation.phase==ObservationPhase::Interrupted) interrupted=true;
    require(interrupted,"preemption has no factual observation");
    const auto snapshot=world.checkpoint(); world.restore(snapshot);
    require(world.checkpoint()==snapshot,"integrated queen restoration differs");
    const auto mass=world.nutrition_snapshot();
    require(mass.introduced==mass.accounted && mass.energy_input_nj==mass.body_energy_nj+mass.dissipated_energy_nj,
            "maternal preemption changed the conserved reproductive ledger");
}
}

int main(int argc,char** argv) {
    try {
        if (argc<2) throw std::invalid_argument("missing S6.3.3.2 test case");
        const std::string_view test=argv[1];
        if (test=="MOTION" && argc==3) motion(argv[2]);
        else if (test=="FOREIGN") foreign();
        else if (test=="COMPETING") competing();
        else if (test=="GEOMETRY") geometry();
        else if (test=="LIFECYCLE") lifecycle();
        else if (test=="AUTONOMY") autonomy();
        else if (test=="REPRODUCTION") reproduction();
        else throw std::invalid_argument("unknown S6.3.3.2 test case");
        std::cout<<"PASS "<<test<<'\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
