#include "s6_3_3_fixture.hpp"
#include "antworld/storage/store.hpp"
#include <filesystem>
#include <iostream>
#include <functional>
#include <map>
using namespace antworld;
using namespace s6_3_3_fixture;
namespace {
void rejects(const std::function<void()>& operation) { bool threw=false; try { operation(); } catch(const std::exception&) { threw=true; } require(threw,"expected rejection"); }
void replay(WorldRuntime& w,SimTime end) {
    auto bytes=w.checkpoint(); WorldRuntime r({1,2},0,{},limits()); r.restore(bytes);
    require(r.checkpoint()==bytes,"care roundtrip mismatch");
    r.advance_to({end.milliseconds-1}); r.advance_to(end); w.advance_to(end);
    require(w.checkpoint()==r.checkpoint(),"care deterministic continuation"); conserved(w);
}
void capability() {
    rejects([&]{SpeciesCareProfile p; p.step_m=.000001; p.bout_duration={10}; p.arrangement_m=.002; Fixture invalid(7,p);});
    Fixture f; rejects([&]{f.w.set_behavior(f.queen,IndividualBehavior::Forage);});
    rejects([&]{f.w.set_autonomy(f.queen);});
    f.w.advance_to({3600000}); auto stats=f.w.behavior_window(f.queen,{}, {3600000});
    require(stats.completed[static_cast<std::size_t>(CareAct::CleanBrood)]>0,"foundress cannot clean");
    require(stats.completed[static_cast<std::size_t>(CareAct::ArrangeBrood)]>0,"foundress cannot arrange");
    require(stats.transferred.protein_ug>0,"foundress cannot feed actual protein");
    require(stats.known_active_ms>0 && stats.known_inactive_ms>0,"activity distinction missing");
    require(stats.legacy_program_ms[0]==3600000 && stats.care_program_ms==3600000,"program residence mislabeled");
    require(f.w.query_physiology(f.queen)->behavior==IndividualBehavior::Paused,"queen gained worker task");
    conserved(f.w); replay(f.w,{3700000});
}
void locality() {
    Fixture absent(7,{},5,0),present(7,{},5,5),wall(7,{},5,3,true);
    for(auto* f:{&absent,&present,&wall}) f->w.advance_to({3600000});
    require(!absent.w.query_care(absent.queen)->has_worker_contact,"absent contact invented");
    require(present.w.query_care(present.queen)->has_worker_contact,"near workers not contacted");
    require(!wall.w.query_care(wall.queen)->has_worker_contact,"contact crosses wall");
    replay(wall.w,{3700000});
}
void reversibility() {
    SpeciesCareProfile p; p.social_memory_horizon={60000};
    Fixture f(19,p,5,5); f.w.advance_to({600000}); require(f.w.query_care(f.queen)->has_worker_contact,"no initial contact");
    for(auto worker:f.workers) f.w.submit({worker,{610000},ActionKind::Move,{}, {.02,0,.02},0});
    f.w.advance_to({610000});
    for(auto worker:f.workers) require(f.w.query_ant(worker)->position==PositionM{.02,0,.02},"removal action failed");
    const auto before=f.w.query_care(f.queen)->last_worker_contact;
    f.w.advance_to({700000}); require(f.w.query_care(f.queen)->last_worker_contact==before,"remote worker refreshed memory");
    f.w.advance_to({1200000}); const auto s=f.w.behavior_window(f.queen,{700000},{1200000});
    require(s.completed[static_cast<std::size_t>(CareAct::CleanBrood)]>0,"care did not resume"); replay(f.w,{1300000});
}
void stages() {
    Fixture f(43,{},0); auto before=f.w.checkpoint();
    f.w.advance_to({120000}); const auto s=f.w.behavior_window(f.queen,{}, {120000});
    require(!s.successful_contacts && !s.transferred.total_ug(),"care fabricated without brood");
    require(s.completed[static_cast<std::size_t>(CareAct::Walk)]>0,"local search absent");
    f.w.pause_brood_care(f.queen); replay(f.w,{130000});
    (void)before;
}
void duration() {
    Fixture f; f.w.advance_to({2}); const auto c=*f.w.query_care(f.queen);
    require(c.active,"act did not start"); const auto midway=SimTime{2+(c.act==CareAct::Inactive?60000:10000)/2};
    f.w.advance_to(midway); auto s=f.w.behavior_window(f.queen,{2},midway);
    require(s.duration_ms[static_cast<std::size_t>(c.act)]==static_cast<std::uint64_t>(midway.milliseconds-2),"open bout duration");
    require(!s.completed[static_cast<std::size_t>(c.act)],"unfinished act counted complete");
    replay(f.w,{100000});
}
void interruption() {
    Fixture f; f.w.advance_to({5000}); f.w.pause_brood_care(f.queen);
    auto s=f.w.behavior_window(f.queen,{}, {5000}); // End events are excluded at the half-open right boundary.
    f.w.advance_to({5001}); s=f.w.behavior_window(f.queen,{}, {5001});
    std::uint64_t interrupted=0; for(auto n:s.interrupted) interrupted+=n;
    require(interrupted==1,"pause did not interrupt exactly one act");
    replay(f.w,{10000});
    f.w.enable_brood_care(f.queen,f.w.query_care(f.queen)->profile); f.w.advance_to({10003});
    f.w.schedule_lifecycle(f.queen,{10004},LifeStage::Dead); f.w.advance_to({11000});
    require(!f.w.query_care(f.queen)->enabled,"dead queen retains care"); replay(f.w,{12000});
}
void worker() {
    SpeciesCareProfile config; config.care_probability=1; config.worker_contact_probability=0;
    Fixture f(71,config,5,1); auto p=physiology();
    f.w.enable_physiology(f.workers[0],{{0,100,0,0},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
    f.w.enable_brood_care(f.workers[0],{CareContext::Worker,{}}); f.w.advance_to({600000});
    const auto s=f.w.behavior_window(f.workers[0],{}, {600000});
    require(s.completed[static_cast<std::size_t>(CareAct::CleanBrood)]>0,"worker care observation missing");
    replay(f.w,{700000});
}
void target_lifecycle() {
    SpeciesCareProfile cfg; cfg.care_probability=1;
    Fixture f(7,cfg,1); f.w.advance_to({2});
    require(f.w.query_care(f.queen)->active,"missing initial care bout");
    f.w.schedule_lifecycle(f.brood[0],{100},LifeStage::Dead); f.w.advance_to({101});
    require(!f.w.query_care(f.queen)->active,"dead brood retains care lock");
    const auto s=f.w.behavior_window(f.queen,{}, {101});
    std::uint64_t count=0; for(auto n:s.interrupted) count+=n;
    require(count==1,"target death not observed as interruption"); replay(f.w,{1000});
}
void geometry_closure() {
    WorldRuntime w({633,999},7,{},limits()); w.configure_long_term(); w.configure_social();
    SpeciesCareProfile cfg; cfg.care_probability=1; cfg.worker_contact_probability=0;
    w.configure_biology(cfg); GeometryConfig g;
    const BoxQ tunnel{{2,10,10},{28,14,14}}; w.configure_geometry(g,std::span{&tunnel,1});
    const auto pos=[&](int x) { return PositionM{static_cast<double>(x)*g.quantum_m,-.010,.006}; };
    const auto colony=w.seed_colony(pos(12));
    const auto queen=w.seed_ant(colony,{pos(12),LifeStage::Adult,Caste::Queen});
    const auto larva=w.seed_ant(colony,{pos(16),LifeStage::Larva});
    const auto worker=w.seed_ant(colony,{pos(12),LifeStage::Adult,Caste::Worker,20000});
    const auto p=physiology(); w.enable_physiology(queen,{{0,100,0,0},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
    w.enable_physiology(worker,{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
    w.enable_brood_care(queen); w.advance_to({2});
    require(w.query_care(queen)->active && w.query_care(queen)->target==larva.id,"fixture has no active contact");
    w.submit_soil({worker,{102},SoilAction::Excavate,{{10,14,10},{14,15,14}},{},0}); w.advance_to({102});
    require(w.soil_parcels().size()==1,"fixture excavation failed");
    w.submit_soil({worker,{300},SoilAction::Fill,{{14,10,10},{15,14,14}},{w.summary().world,w.soil_parcels()[0].id},1});
    w.advance_to({300});
    require(w.geometry_edits().size()==2 && !w.query_care(queen)->active,"wall did not interrupt care immediately");
    require(!w.spatially_clear(pos(12),pos(16)),"contact still crosses wall"); replay(w,{20000});
}
void query() {
    Fixture f; f.w.advance_to({200000}); const auto bytes=f.w.checkpoint();
    auto s=f.w.behavior_window(f.queen,{100},{190000}); (void)s;
    (void)f.w.query_care(f.queen); (void)f.w.sample_contacts(f.queen,1);
    require(bytes==f.w.checkpoint(),"observation query mutates simulation");
    rejects([&]{(void)f.w.behavior_window(f.queen,{}, {200001});});
}
void rollback() {
    Fixture f; f.w.advance_to({2}); const auto bytes=f.w.checkpoint();
    auto l=limits(); l.committed_events=f.w.summary().committed_events+3;
    WorldRuntime bounded({1,1},1,{},l); bounded.restore(bytes);
    rejects([&]{bounded.advance_to({100000});}); require(bounded.checkpoint()==bytes,"failed care advance did not roll back");
}
void transport() {
    SpeciesCareProfile cfg; cfg.care_probability=1;
    Fixture f(101,cfg,0);
    const auto b=f.w.seed_ant(f.colony,{{.005,0,0},LifeStage::Pupa});
    bool carrying=false;
    for(std::int64_t t=1;t<300000;++t) {
        f.w.advance_to({t}); const auto c=*f.w.query_care(f.queen);
        if(c.active && c.act==CareAct::TransportBrood) { carrying=true; break; }
    }
    require(carrying,"no local brood transport"); const auto id=b.id;
    replay(f.w,{300000});
    require(f.w.query_ant(b)->position.x<.005 && f.w.query_ant(b)->id==id,"brood did not move with continuous identity");
    require(f.w.query_ant(b)->stage==LifeStage::Pupa,"transport changed life stage");
}
void competition() {
    SpeciesCareProfile cfg; cfg.care_probability=1; cfg.worker_contact_probability=0;
    Fixture f(137,cfg,1); auto p=physiology();
    const auto q=f.w.seed_ant(f.colony,{{},LifeStage::Adult,Caste::Queen});
    f.w.enable_physiology(q,{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
    f.w.enable_brood_care(q); f.w.advance_to({2});
    require(static_cast<int>(f.w.query_care(q)->active)+static_cast<int>(f.w.query_care(f.queen)->active)==1,"two carers own the same brood");
    for(const auto& e:f.w.committed_events()) if(e.kind==FactKind::BiologicalObservation && e.observation.phase==ObservationPhase::Opportunity && e.observation.act==CareAct::CloseWorkerContact)
        require(f.w.query_ant({f.w.summary().world,e.observation.target})->caste==Caste::Worker,"queen mislabeled as worker contact opportunity");
    replay(f.w,{20000});
}
void corruption() {
    Fixture f; f.w.advance_to({2}); auto bytes=f.w.checkpoint();
    // One 125-byte care row is at the end. Forge an unevidenced completed social interaction.
    bytes.at(bytes.size()-8-125+43)=1;
    std::uint64_t hash=14695981039346656037ULL;
    for(std::size_t i=0;i<bytes.size()-8;++i) hash=(hash^bytes[i])*1099511628211ULL;
    for(unsigned i=0;i<8;++i) bytes[bytes.size()-8+i]=static_cast<std::uint8_t>((hash>>(8*i))&255);
    const auto original=f.w.checkpoint(); rejects([&]{f.w.restore(bytes);}); require(f.w.checkpoint()==original,"bad restore changed world");
}
void observation_only() {
    Fixture old(223,{},5,1,false,CareContext::FoundingQueen,{},false),observed(223,{},5,1,false,CareContext::FoundingQueen,{},false);
    observed.w.configure_biology();
    auto p=physiology(); p.behavior_interval={1000};
    for(auto* f:{&old,&observed}) { f->w.enable_physiology(f->workers[0],{{0,400,0,0},p.energy_capacity_nj,p.hydration_capacity_ug,0},p); f->w.set_behavior(f->workers[0],IndividualBehavior::Nurse); f->w.advance_to({300000}); }
    require(old.w.nutrition_snapshot()==observed.w.nutrition_snapshot(),"observation changed nutrition");
    require(old.w.ant_states()==observed.w.ant_states(),"observation changed physical state");
    const auto o=observed.w.behavior_window(observed.workers[0],{}, {300000});
    require(o.unknown_duration_completions>0 && o.known_active_ms==0 && o.known_inactive_ms==0 && o.unknown_activity_ms==300000,"instantaneous history invented duration");
    replay(observed.w,{301000});
}
void durable(const std::filesystem::path& path) {
    Fixture f; f.w.advance_to({5000}); storage::Store db(path,limits()); auto token=db.save(f.w);
    auto restored=db.load(f.w.summary().world); require(restored.world.checkpoint()==f.w.checkpoint(),"SQLite mid-bout restore");
    f.w.advance_to({120000}); restored.world.advance_to({120000});
    require(f.w.checkpoint()==restored.world.checkpoint(),"SQLite continuation"); db.save(f.w,token);
    auto rows=db.history({f.w.summary().world,{}, {},{INT64_MAX},f.brood[0].id,FactKind::BiologicalObservation,1000});
    require(!rows.empty(),"brood related history missing");
}
}
int main(int argc,char** argv) {
    try {
        const std::string name=argc>1?argv[1]:"CAPABILITY";
        const std::map<std::string,std::function<void()>> tests{{"CAPABILITY",capability},{"LOCALITY",locality},{"REVERSIBILITY",reversibility},
            {"STAGES",stages},{"DURATION",duration},{"INTERRUPTION",interruption},{"WORKER",worker},{"QUERY",query},{"ROLLBACK",rollback},
            {"TRANSPORT",transport},{"COMPETITION",competition},{"CORRUPTION",corruption},{"OBSERVATION_ONLY",observation_only},
            {"TARGET_LIFECYCLE",target_lifecycle},{"GEOMETRY_CLOSURE",geometry_closure}};
        if(name=="STORAGE") { if(argc<3) throw std::runtime_error("database path required"); durable(argv[2]); }
        else tests.at(name)();
        std::cout<<"PASS "<<name<<'\n'; return 0;
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
