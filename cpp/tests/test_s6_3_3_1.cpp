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
SpeciesCareProfile retrieval_profile() {
    SpeciesCareProfile profile;
    profile.local_retrieval=true;
    profile.care_probability=1;
    profile.worker_contact_probability=0;
    return profile;
}

void until_act(WorldRuntime& w, AntRef actor, CareAct act) {
    const auto start=w.summary().now.milliseconds;
    for (std::int64_t offset=100; offset<=300000; offset+=100) {
        const auto c=*w.query_care(actor);
        if (c.active && c.act==act) return;
        w.advance_to({start+offset});
    }
    throw std::runtime_error("expected care act was never started");
}

bool at_shelter(const WorldRuntime& w, AntRef brood, PositionM nest={}) {
    const auto p=w.query_ant(brood)->position;
    return std::hypot(p.x-nest.x,p.y-nest.y,p.z-nest.z)<=w.config().contact_distance_m;
}

void persistence() {
    Fixture f(7,retrieval_profile(),1);
    const auto first=f.w.seed_ant(f.colony,{{.004,0,0},LifeStage::Larva});
    const auto second=f.w.seed_ant(f.colony,{{.0065,0,0},LifeStage::Pupa});
    f.w.advance_to({1});
    require(f.w.query_care(f.queen)->target==first.id,"settled brood diverted the first local retrieval");
    f.w.advance_to({70000});
    require(at_shelter(f.w,first),"first brood was not delivered");
    require(f.w.query_care(f.queen)->retrieval.target==second.id,"revisit did not find the second displaced brood");
    f.w.advance_to({220000});
    require(at_shelter(f.w,second),"second brood was not delivered");
    bool revisited=false;
    std::size_t moves=0;
    for (const auto& e:f.w.committed_events()) {
        if (e.kind==FactKind::BroodMoved && (e.actor==first.id || e.actor==second.id)) ++moves;
        if (e.kind==FactKind::BiologicalObservation && e.observation.act==CareAct::RevisitBroodSite &&
            e.observation.phase==ObservationPhase::Completed) revisited=true;
    }
    require(moves>=7 && revisited,"deliveries bypassed finite transport or the observed return search");
    conserved(f.w);
}

void locality() {
    Fixture control(19,retrieval_profile(),1), hidden(19,retrieval_profile(),1);
    const auto remote=hidden.w.seed_ant(hidden.colony,{{.02,0,0},LifeStage::Pupa});
    control.w.advance_to({200000});
    hidden.w.advance_to({200000});
    const auto c=*control.w.query_care(control.queen), h=*hidden.w.query_care(hidden.queen);
    require(c==h && !h.retrieval.target.value && !h.retrieval.pickup_bout.value,"hidden brood changed a local care decision");
    require(hidden.w.query_ant(remote)->position==PositionM{.02,0,0},"hidden brood was moved");
}

void contact() {
    Fixture f(7,retrieval_profile(),0);
    const auto b=f.w.seed_ant(f.colony,{{.004,0,0},LifeStage::Larva});
    until_act(f.w,f.queen,CareAct::ApproachBrood);
    require(f.w.query_ant(b)->position.x==.004,"a selected approach moved its target");
    const auto early=f.w.behavior_window(f.queen,{},f.w.summary().now);
    require(early.successful_contacts==0,"approach was counted as contact");
    until_act(f.w,f.queen,CareAct::TransportBrood);
    const auto q=f.w.query_ant(f.queen)->position;
    const auto now=f.w.summary().now;
    require(std::abs(f.w.query_ant(b)->position.x-q.x)<=f.w.config().contact_distance_m,"transport started outside physical reach");
    require(f.w.query_ant(b)->position.x==.004,"pickup teleported brood");
    f.w.advance_to({now.milliseconds+10000});
    const auto result=f.w.query_ant(b)->position;
    require(result.x<.004 && .004-result.x<=.001000000000001,"one transport moved more than its step");
}

void conflict() {
    Fixture f(137,retrieval_profile(),0,2);
    f.w.pause_brood_care(f.queen);
    const auto b=f.w.seed_ant(f.colony,{{.003,0,-.00025},LifeStage::Larva});
    const auto p=physiology();
    for (auto worker:f.workers) {
        f.w.enable_physiology(worker,{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
        f.w.enable_brood_care(worker,{CareContext::Worker,{}});
    }
    f.w.advance_to({12000});
    unsigned active=0;
    for (auto worker:f.workers) {
        const auto c=*f.w.query_care(worker);
        active+=static_cast<unsigned>(c.active && c.act==CareAct::TransportBrood);
    }
    require(active==1,"two simultaneous workers acquired one displaced item");
    unsigned rejected=0;
    for (const auto& e:f.w.committed_events()) if (e.kind==FactKind::BiologicalObservation &&
        e.observation.act==CareAct::TransportBrood && e.observation.target==b.id &&
        e.observation.phase==ObservationPhase::Interrupted && e.outcome==Outcome::DuplicateAction) ++rejected;
    require(rejected==1,"reservation conflict lacks a committed interruption");
    f.w.advance_to({130000});
    require(at_shelter(f.w,b),"reservation winner did not deliver");
    conserved(f.w);
}

void geometry() {
    WorldRuntime w({6331,7},7,{},limits());
    w.configure_long_term(); w.configure_social(); w.configure_biology(retrieval_profile());
    GeometryConfig g;
    const BoxQ tunnel{{2,10,10},{28,14,14}};
    w.configure_geometry(g,std::span{&tunnel,1});
    const auto pos=[&](int x) { return PositionM{static_cast<double>(x)*g.quantum_m,-.010,.006}; };
    const auto colony=w.seed_colony(pos(12));
    const auto queen=w.seed_ant(colony,{pos(12),LifeStage::Adult,Caste::Queen});
    const auto b=w.seed_ant(colony,{pos(19),LifeStage::Larva});
    const auto digger=w.seed_ant(colony,{pos(12),LifeStage::Adult,Caste::Worker,20000});
    const auto p=physiology();
    for (auto a:{queen,digger}) w.enable_physiology(a,{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
    w.enable_brood_care(queen);
    w.submit_soil({digger,{102},SoilAction::Excavate,{{10,14,10},{14,15,14}},{},0});
    until_act(w,queen,CareAct::TransportBrood);
    const auto previous=w.query_ant(b)->position;
    require(w.soil_parcels().size()==1,"fixture excavation failed");
    const SimTime fill{w.summary().now.milliseconds+100};
    w.submit_soil({digger,fill,SoilAction::Fill,{{14,10,10},{15,14,14}},{w.summary().world,w.soil_parcels().front().id},1});
    w.advance_to(fill);
    require(w.geometry_edits().size()==2 && !w.query_care(queen)->active,"wall did not interrupt loaded movement");
    require(w.query_care(queen)->retrieval==RetrievalMemory{},"blocked carrier retained its episode");
    w.advance_to({fill.milliseconds+20000});
    require(w.query_ant(b)->position==previous && !at_shelter(w,b,pos(12)),"brood crossed the wall");
    conserved(w);
}

void restore(const std::filesystem::path& database) {
    Fixture f(7,retrieval_profile(),0);
    f.w.seed_ant(f.colony,{{.004,0,0},LifeStage::Larva});
    f.w.seed_ant(f.colony,{{.0065,0,0},LifeStage::Pupa});
    for (auto act:{CareAct::ApproachBrood,CareAct::TransportBrood,CareAct::RevisitBroodSite}) {
        until_act(f.w,f.queen,act);
        const auto bytes=f.w.checkpoint();
        WorldRuntime replay({2,3},0,{},limits()); replay.restore(bytes);
        require(replay.checkpoint()==bytes,"mid-bout checkpoint differs");
        const SimTime next{f.w.summary().now.milliseconds+1};
        f.w.advance_to(next); replay.advance_to(next);
        require(f.w.checkpoint()==replay.checkpoint(),"mid-bout continuation differs");
    }
    const auto original=f.w.checkpoint();
    auto corrupt=original;
    // Pickup position is the final field of this one-carer checkpoint before the checksum.
    corrupt.at(corrupt.size()-32)^=1;
    std::uint64_t hash=14695981039346656037ULL;
    for (std::size_t i=0;i<corrupt.size()-8;++i) hash=(hash^corrupt[i])*1099511628211ULL;
    for (unsigned i=0;i<8;++i) corrupt[corrupt.size()-8+i]=static_cast<std::uint8_t>((hash>>(8*i))&255);
    bool rejected=false;
    try { f.w.restore(corrupt); } catch (const std::invalid_argument&) { rejected=true; }
    require(rejected && f.w.checkpoint()==original,"unevidenced pickup site was restored");
    storage::Store store(database,limits());
    (void)store.save(f.w);
    auto saved=store.load(f.w.summary().world);
    require(saved.world.checkpoint()==original,"durable retrieval continuation differs");
    f.w.advance_to({200000}); saved.world.advance_to({200000});
    require(f.w.checkpoint()==saved.world.checkpoint(),"durable revisit changed future facts");
    conserved(f.w);
}
}

int main(int argc, char** argv) {
    try {
        const std::string_view name=argc>1?argv[1]:"";
        if (name=="PERSISTENCE") persistence();
        else if (name=="LOCALITY") locality();
        else if (name=="CONTACT") contact();
        else if (name=="CONFLICT") conflict();
        else if (name=="GEOMETRY") geometry();
        else if (name=="STORAGE" && argc==3) restore(argv[2]);
        else throw std::invalid_argument("unknown retrieval regression");
        std::cout<<"PASS "<<name<<'\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
