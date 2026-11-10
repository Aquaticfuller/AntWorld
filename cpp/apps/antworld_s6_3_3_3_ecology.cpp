#include "s6_3_3_3_fixture.hpp"
#include "antworld/storage/store.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>

using namespace antworld;
using namespace antworld::closure;

namespace {
using Clock=std::chrono::steady_clock;
double ms(Clock::time_point start) {
    return std::chrono::duration<double,std::milli>(Clock::now()-start).count();
}

std::ofstream file(const std::filesystem::path& path) {
    std::ofstream stream(path,std::ios::binary);
    stream.exceptions(std::ios::badbit|std::ios::failbit);
    stream<<std::setprecision(17);
    return stream;
}

void mass(std::ostream& out,FoodMass m) {
    for (const auto value:m.components()) out<<','<<value;
}

void position(std::ostream& out,PositionM p) { out<<','<<p.x<<','<<p.y<<','<<p.z; }

struct Output {
    std::ofstream runs, days, individuals, events, probes, timings;
    std::ofstream canonical, abort;
    explicit Output(const std::filesystem::path& dir,bool isolated=false)
        :runs(file(dir/"runs.csv")),days(file(dir/"days.csv")),individuals(file(dir/"individuals.csv")),
         events(file(dir/"events.csv")),probes(file(dir/"probes.csv")),timings(file(dir/"timings.csv")) {
        if (isolated) {
            canonical=file(dir/"events.facts");
            abort=file(dir/"abort.csv");
            abort<<"run,stage,last_full_day,failed_at_ms,committed_events,state_hash,trace_hash\n";
        }
        runs<<"run,seed,workers,space,food,integrated,queen,displaced_brood,cell_m,perception_m,stride_m,decision_ms,absorption_ms,egg_ms,larva_ms,pupa_ms,reproduction_ms,end_ms,events,checkpoint_bytes,sqlite_bytes,state_hash,trace_hash,direct_equal,restored_equal,sql_fact_count,all_ledgers_equal\n";
        days<<"run,day,events,egg,larva,pupa,adult,dead,adult_worker_ms,introduced_carbs_ug,introduced_protein_ug,introduced_water_ug,introduced_other_ug,accounted_carbs_ug,accounted_protein_ug,accounted_water_ug,accounted_other_ug,available_carbs_ug,available_protein_ug,available_water_ug,available_other_ug,nest_carbs_ug,nest_protein_ug,nest_water_ug,nest_other_ug,crop_carbs_ug,crop_protein_ug,crop_water_ug,crop_other_ug,energy_input_nj,body_energy_nj,dissipated_energy_nj,soil_initial_q3,soil_remaining_q3,soil_carried_q3,soil_deposited_q3,geometry_edits\n";
        individuals<<"run,day,id,mother,stage,caste,x_m,y_m,z_m,program,care_enabled,carrying_brood,autonomous,progress_ms,energy_nj,hydration_ug,tissue_protein_ug,death_cause,crop_carbs_ug,crop_protein_ug,crop_water_ug,crop_other_ug\n";
        events<<"run,event,time_ms,kind,actor,colony,stage,source,related,phase,act,bout,began_ms,duration_known,outcome,x_m,y_m,z_m,carbs_ug,protein_ug,water_ug,other_ug\n";
        probes<<"run,space,cell_m,perception_m,stride_m,initial_geometric_cue,approach_starts,blocked,loaded_out_of_reach,pickups,carried_moves,placements,fill,load_released,unchanged_target,restore_equal\n";
        timings<<"run,setup_ms,advance_ms,observer_ms,checkpoint_ms,sqlite_day10_ms,sqlite_day21_ms,events,state_hash,trace_hash\n";
    }
    void fact(std::string_view run,const WorldEvent& e) {
        const auto& o=e.observation;
        events<<run<<','<<e.id.value<<','<<e.time.milliseconds<<','<<static_cast<unsigned>(e.kind)<<','<<e.actor.value
              <<','<<e.colony.value<<','<<static_cast<unsigned>(e.stage)<<','<<e.source.value<<','
              <<(e.kind==FactKind::BiologicalObservation?o.target.value:e.payload)
              <<','<<static_cast<unsigned>(o.phase)<<','<<static_cast<unsigned>(o.act)<<','<<o.bout.value<<','
              <<o.began_at.milliseconds<<','<<o.duration_known<<','<<static_cast<unsigned>(e.outcome);
        position(events,e.position);
        mass(events,e.transferred);
        events<<'\n';
        if (canonical.is_open()) {
            const auto record=encode_event(e);
            const auto size=static_cast<std::uint32_t>(record.size());
            for (unsigned shift:{0U,8U,16U,24U}) canonical.put(static_cast<char>((size>>shift)&255U));
            canonical.write(reinterpret_cast<const char*>(record.data()),static_cast<std::streamsize>(record.size()));
        }
    }
};

struct Life {
    LifeStage stage{};
    Caste caste{};
    SimTime since;
};

struct History {
    EventId cursor{};
    std::map<EntityId,Life> life;
    std::uint64_t adult_worker_ms{};
    void advance(Life& state,SimTime at) {
        if (state.stage==LifeStage::Adult && state.caste==Caste::Worker)
            adult_worker_ms+=static_cast<std::uint64_t>(at.milliseconds-state.since.milliseconds);
        state.since=at;
    }
    void record(const WorldRuntime& w,Output& out,std::string_view name) {
        for (;;) {
            const auto facts=w.events_after(cursor,4096);
            if (facts.empty()) break;
            for (const auto& e:facts) {
                require(e.id.value==cursor.value+1,"noncontiguous ecology journal");
                if (e.kind==FactKind::AntSeeded || e.kind==FactKind::AntBorn)
                    require(life.emplace(e.actor,Life{e.stage,w.query_ant({e.world,e.actor})->caste,e.time}).second,
                            "reused ecology identity");
                if (e.kind==FactKind::StageChanged || e.kind==FactKind::AntDied) {
                    auto& state=life.at(e.actor);
                    advance(state,e.time);
                    require(state.stage!=LifeStage::Dead && (e.stage==LifeStage::Dead ||
                            static_cast<unsigned>(e.stage)==static_cast<unsigned>(state.stage)+1),
                            "invalid ecology life history");
                    state.stage=e.stage;
                }
                out.fact(name,e);
                cursor=e.id;
            }
        }
        for (auto& [id,state]:life) {
            require(state.stage==w.query_ant({w.summary().world,id})->stage,"life history differs from snapshot");
            advance(state,w.summary().now);
        }
    }
};

void record_day(const WorldRuntime& w,Output& out,std::string_view name,unsigned d,History& history) {
    s6_3_fixture::conserved(w);
    history.record(w,out,name);
    const auto s=w.summary();
    std::array<std::size_t,5> stages{};
    for (const auto& a:w.ant_states()) {
        ++stages.at(static_cast<std::size_t>(a.stage));
        const AntRef ref{s.world,a.id};
        const auto p=*w.query_physiology(ref);
        const auto c=w.query_care(ref);
        const auto autonomy=w.query_autonomy(ref);
        out.individuals<<name<<','<<d<<','<<a.id.value<<','<<p.mother.value<<','<<static_cast<unsigned>(a.stage)
                       <<','<<static_cast<unsigned>(a.caste);
        position(out.individuals,a.position);
        out.individuals<<','<<static_cast<unsigned>(p.behavior)<<','<<(c && c->enabled)<<','<<(c && c->carrying_brood)
                       <<','<<(autonomy && autonomy->enabled)<<','<<p.stage_progress.milliseconds<<','<<p.body_energy_nj
                       <<','<<p.hydration_ug<<','<<p.tissue_protein_ug<<','<<static_cast<unsigned>(p.death_cause);
        mass(out.individuals,p.crop);
        out.individuals<<'\n';
    }
    const auto n=w.nutrition_snapshot();
    const auto g=w.geometry_snapshot();
    out.days<<name<<','<<d<<','<<s.committed_events;
    for (auto count:stages) out.days<<','<<count;
    out.days<<','<<history.adult_worker_ms;
    for (auto m:{n.introduced,n.accounted,s.food_ledger.available,s.food_ledger.stored,n.crop}) mass(out.days,m);
    out.days<<','<<n.energy_input_nj<<','<<n.body_energy_nj<<','<<n.dissipated_energy_nj
            <<','<<g.ledger.initial_q3<<','<<g.ledger.remaining_q3<<','<<g.ledger.carried_q3<<','
            <<g.ledger.deposited_q3<<','<<w.geometry_edits().size()<<'\n';
}

std::uint64_t compare_history(storage::Store& store,const WorldRuntime& w) {
    EventId cursor{};
    for (;;) {
        const auto facts=w.events_after(cursor,1024);
        const auto saved=store.history({w.summary().world,cursor,{0},{INT64_MAX},{},{},1024});
        require(facts.size()==saved.size(),"SQLite history length differs");
        if (facts.empty()) return cursor.value;
        for (std::size_t i=0;i<facts.size();++i)
            require(encode_event(facts[i])==encode_event(saved[i].fact),"SQLite fact bytes differ");
        cursor=facts.back().id;
    }
}

void ecology(Output& out,const std::filesystem::path& dir,std::uint64_t seed,unsigned count,
             std::string_view space,bool food,bool integrated,bool smoke=false,bool continuous=false) {
    const auto name=std::to_string(seed)+"_"+std::to_string(count)+"_"+std::string(space)+
                    (food?"_balanced":"_empty")+(integrated?"_care":"_control");
    auto clock=Clock::now();
    WorldRuntime w({6333,seed},seed,{{-.04,-.02,-.02},{.04,.02,.02},.08,.002,continuous},limits());
    const auto [queen,target,depot,cell]=prepare_ecology(w,count,space,food,integrated);
    const auto p=day_physiology();
    const auto care=*w.care_profile();

    const auto initial=w.checkpoint();
    storage::Store store(dir/(name+".sqlite"),limits());
    const double setup_ms=ms(clock);
    double advance_ms=0,observer_ms=0,mid_save_ms=0;
    storage::SaveToken middle;
    History history;
    for (unsigned d=0;d<=21;++d) {
        clock=Clock::now();
        try {
            if (d==0) w.advance_to({0});
            else for (auto t=(d-1)*day+6*hour;t<=d*day;t+=6*hour) w.advance_to({t});
        } catch (const std::length_error&) {
            if (out.abort.is_open()) {
                history.record(w,out,name);
                const auto last=w.snapshot();
                out.abort<<name<<",advance,"<<static_cast<int>(d)-1<<','<<last.now.milliseconds<<','
                         <<last.committed_events<<','<<last.state_hash<<','<<last.trace_hash<<'\n';
            }
            throw;
        }
        advance_ms+=ms(clock);
        clock=Clock::now();
        record_day(w,out,name,d,history);
        observer_ms+=ms(clock);
        if (d==10) {
            clock=Clock::now();
            middle=store.save(w);
            mid_save_ms=ms(clock);
        }
    }
    clock=Clock::now();
    const auto bytes=w.checkpoint();
    const double checkpoint_ms=ms(clock);
    {
        WorldRuntime direct({1,1},0,{},limits());
        direct.restore(initial);
        direct.advance_to({21*day});
        require(direct.checkpoint()==bytes,"unpartitioned ecology differs");
    }
    {
        auto restored=store.load(w.summary().world,middle.generation);
        for (auto t=10*day+5*hour;t<21*day;t+=5*hour+12007) restored.world.advance_to({t});
        restored.world.advance_to({21*day});
        require(restored.world.checkpoint()==bytes,"restored ecology differs");
    }
    clock=Clock::now();
    const auto end=store.save(w,middle);
    store.checkpoint_wal();
    const double end_save_ms=ms(clock);
    const auto facts=compare_history(store,w);
    for (const auto& a:w.ant_states()) {
        const auto id=store.individual({w.summary().world,a.id});
        require(id && id->current_stage==a.stage && id->created_at==a.born_at,"durable identity differs");
    }
    const auto s=w.snapshot();
    require(end.cursor==facts && facts==s.committed_events,"durable cursor differs");
    if (smoke) {
        const auto journal=w.committed_events();
        const auto has=[&](auto predicate) { return std::any_of(journal.begin(),journal.end(),predicate); };
        require(has([&](const WorldEvent& e) { return e.kind==FactKind::BroodMoved && e.actor==target.id; }) &&
                has([&](const WorldEvent& e) { return e.kind==FactKind::BiologicalObservation &&
                    e.observation.target==target.id && e.observation.act==CareAct::PlaceBrood &&
                    e.observation.phase==ObservationPhase::Completed; }) &&
                has([](const WorldEvent& e) { return e.kind==FactKind::NutritionTransferred && e.transferred.total_ug(); }) &&
                has([&](const WorldEvent& e) { return e.kind==FactKind::AntBorn && e.payload==queen.id.value; }) &&
                has([](const WorldEvent& e) { return e.kind==FactKind::StageChanged && e.stage==LifeStage::Adult; }),
                "day-scale smoke lost a committed ecology capability");
        if (continuous) {
            const auto returned=std::find_if(journal.begin(),journal.end(),[&](const WorldEvent& e) {
                return e.kind==FactKind::FoodDelivered && e.position==depot && e.position.y<0 && e.transferred.total_ug();
            });
            require(returned!=journal.end() && std::any_of(journal.begin(),returned,[&](const WorldEvent& e) {
                return e.kind==FactKind::FoodCollected && e.actor==returned->actor && e.position.y>0;
            }),"day-scale smoke lost actual surface collection or underground delivery");
            const auto after_return=[&](const WorldEvent& e,CareAct act) {
                return e.actor==returned->actor && e.kind==FactKind::BiologicalObservation &&
                    e.observation.phase==ObservationPhase::Completed && e.observation.act==act;
            };
            require(std::any_of(returned,journal.end(),[&](const WorldEvent& e) {
                return after_return(e,CareAct::CleanBrood) && e.observation.duration_known;
            }) && std::any_of(returned,journal.end(),[&](const WorldEvent& e) {
                return after_return(e,CareAct::FeedBrood) && e.transferred.protein_ug;
            }),"returning worker did not later complete physical care and brood feeding");
        }
    }
    out.runs<<name<<','<<seed<<','<<count<<','<<space<<','<<(food?"balanced":"empty")<<','<<integrated
            <<','<<queen.id.value<<','<<target.id.value<<','<<cell<<','<<care.perception_radius_m<<','<<care.step_m
            <<','<<day_social().decision_interval.milliseconds<<','<<p.absorption_period.milliseconds<<','
            <<p.egg_duration.milliseconds<<','<<p.larva_duration.milliseconds<<','<<p.pupa_duration.milliseconds<<','
            <<ReproductionConfig{}.interval.milliseconds<<','<<s.now.milliseconds<<','<<s.committed_events<<','<<bytes.size()
            <<','<<store.database_bytes()<<','<<s.state_hash<<','<<s.trace_hash<<",1,1,"<<facts<<",1\n";
    out.runs.flush();
    out.events.flush();
    out.timings<<name<<','<<setup_ms<<','<<advance_ms<<','<<observer_ms<<','<<checkpoint_ms<<','<<mid_save_ms<<','
               <<end_save_ms<<','<<facts<<','<<s.state_hash<<','<<s.trace_hash<<'\n';
    out.timings.flush();
    std::cout<<name<<" committed "<<facts<<" facts\n";
}

void representation(Output& out,bool fine,double radius) {
    const double cell=fine?.001:.01;
    const std::string space=fine?"fine":"coarse";
    const auto name="representation_"+space+(radius>.006?"_12mm":"_6mm");
    WorldRuntime w({6333,7},7,{{-.01,-.01,-.01},{.02,.01,.01},.08,.002},limits());
    w.configure_long_term();
    w.configure_surface({{0,0,0},fine?21U:3U,1,cell},{});
    w.configure_social(day_social());
    auto c=timed_care(true);
    c.care_probability=1; // ENGINEERING_FIXTURE removes lottery for the representation control.
    c.perception_radius_m=radius;
    w.configure_biology(c);
    const auto colony=w.seed_colony();
    const auto queen=w.seed_ant(colony,{{},LifeStage::Adult,Caste::Queen});
    const PositionM position_m{.01,0,0};
    const auto target=w.seed_ant(colony,{position_m,LifeStage::Larva});
    w.enable_physiology(queen,adult,day_physiology());
    w.enable_physiology(target,larva,day_physiology());
    w.set_autonomy(queen,true);
    w.advance_to({6*hour+60000});
    const auto facts=w.committed_events();
    std::uint64_t starts=0,blocked=0,out_of_reach=0,pickups=0,moves=0,placements=0;
    for (const auto& e:facts) {
        out.fact(name,e);
        if (e.kind==FactKind::BroodMoved && e.actor==target.id) ++moves;
        if (e.kind!=FactKind::BiologicalObservation) continue;
        if (e.observation.act==CareAct::ApproachBrood && e.observation.phase==ObservationPhase::Started) ++starts;
        if (e.observation.act==CareAct::ApproachBrood && e.outcome==Outcome::Blocked) ++blocked;
        if (e.observation.act==CareAct::TransportBrood && e.outcome==Outcome::OutOfReach) ++out_of_reach;
        if (e.observation.act==CareAct::PickUpBrood && e.observation.phase==ObservationPhase::Completed) ++pickups;
        if (e.observation.act==CareAct::PlaceBrood && e.observation.phase==ObservationPhase::Completed) ++placements;
    }
    const bool visible=radius>=.01;
    const bool unchanged=w.query_ant(target)->position==position_m;
    require((starts>0)==(fine && visible) && (blocked>0)==(!fine && visible) &&
            (pickups>0)==(fine && visible) && (moves>0)==(fine && visible) &&
            unchanged==(moves==0),"representation control differs");
    // Report release and threshold failures separately. A sensed and carried
    // target can still fail the remaining path.
    if (fine && visible) require(placements+out_of_reach>0,"fine transport did not reach a terminal fact");
    const auto bytes=w.checkpoint();
    w.restore(bytes);
    require(w.checkpoint()==bytes,"representation restore differs");
    s6_3_fixture::conserved(w);
    out.probes<<name<<','<<space<<','<<cell<<','<<radius<<','<<c.step_m<<','<<visible<<','<<starts
              <<','<<blocked<<','<<out_of_reach<<','<<pickups<<','<<moves<<','<<placements<<",0,0,"<<unchanged<<",1\n";
}

void closed_tunnel(Output& out) {
    WorldRuntime w({6333,7},7,{},limits());
    w.configure_long_term();
    w.configure_social(day_social());
    auto c=timed_care(true);
    c.care_probability=1; // ENGINEERING_FIXTURE for intervention timing only.
    w.configure_biology(c);
    GeometryConfig g;
    const BoxQ tunnel{{2,10,10},{28,14,14}};
    w.configure_geometry(g,std::span{&tunnel,1});
    const auto pos=[&](int x) { return PositionM{static_cast<double>(x)*g.quantum_m,-.010,.006}; };
    const auto colony=w.seed_colony(pos(12));
    const auto queen=w.seed_ant(colony,{pos(12),LifeStage::Adult,Caste::Queen});
    const auto b=w.seed_ant(colony,{pos(19),LifeStage::Larva});
    const auto digger=w.seed_ant(colony,{pos(12),LifeStage::Adult,Caste::Worker,20000});
    w.enable_physiology(queen,adult,day_physiology());
    w.enable_physiology(b,larva,day_physiology());
    w.enable_physiology(digger,adult,day_physiology());
    w.set_autonomy(queen,true);
    w.submit_soil({digger,{102},SoilAction::Excavate,{{10,14,10},{14,15,14}},{},0});
    bool loaded=false;
    while (w.summary().now.milliseconds<6*hour+60000) {
        w.advance_to(w.pending_events().front().key.time);
        const auto care=w.query_care(queen);
        if (care && care->active && care->act==CareAct::TransportBrood && care->carrying_brood) {
            loaded=true;
            break;
        }
    }
    require(loaded && w.soil_parcels().size()==1,"intervention did not reach loaded motion");
    const auto previous=w.query_ant(b)->position;
    const SimTime fill{w.summary().now.milliseconds+g.work_duration.milliseconds};
    w.submit_soil({digger,fill,SoilAction::Fill,{{14,10,10},{15,14,14}},{w.summary().world,w.soil_parcels().front().id},1});
    const auto before=w.checkpoint();
    WorldRuntime restored({1,1},0,{},limits());
    restored.restore(before);
    w.advance_to({fill.milliseconds+60000});
    restored.advance_to(fill);
    restored.advance_to({fill.milliseconds+60000});
    require(w.checkpoint()==restored.checkpoint() && w.geometry_edits().size()==2 &&
            !w.query_care(queen)->carrying_brood && w.query_ant(b)->position==previous,
            "wall failed to interrupt and restore loaded care");
    bool blocked=false;
    for (const auto& e:w.committed_events()) {
        out.fact("tunnel_fill",e);
        if (e.kind==FactKind::BiologicalObservation && e.actor==queen.id && e.observation.act==CareAct::TransportBrood &&
            e.observation.phase==ObservationPhase::Interrupted && e.outcome==Outcome::Blocked) blocked=true;
    }
    require(blocked,"wall interruption fact missing");
    s6_3_fixture::conserved(w);
    std::uint64_t starts=0,pickups=0,moves=0;
    for (const auto& e:w.committed_events()) {
        if (e.kind==FactKind::BroodMoved && e.actor==b.id) ++moves;
        if (e.kind!=FactKind::BiologicalObservation || e.actor!=queen.id) continue;
        if (e.observation.act==CareAct::ApproachBrood && e.observation.phase==ObservationPhase::Started) ++starts;
        if (e.observation.act==CareAct::PickUpBrood && e.observation.phase==ObservationPhase::Completed) ++pickups;
    }
    out.probes<<"tunnel_fill,chamber,0,0.006,0.001,1,"<<starts<<",1,0,"<<pickups<<','<<moves<<",0,1,1,1,1\n";
}
} // namespace

int main(int argc,char** argv) {
    try {
        if (argc!=3 && argc!=4) throw std::invalid_argument(
            "usage: antworld_s6_3_3_3_ecology OUTPUT_DIR matrix|workload|probes|smoke|r1-matrix|r1-depot|r1-smoke [R1_CASE]");
        const std::string_view mode=argv[2];
        const std::string_view selected=argc==4?argv[3]:"";
        if (argc==4 && (selected.empty() || (mode!="r1-matrix" && mode!="r1-depot")))
            throw std::invalid_argument("case selection requires r1-matrix or r1-depot");
        const std::filesystem::path dir=argv[1];
        if (!std::filesystem::create_directories(dir)) throw std::invalid_argument("ecology output already exists");
        Output out(dir,!selected.empty());
        bool matched=selected.empty();
        const auto run=[&](std::uint64_t seed,unsigned count,std::string_view space,bool food,bool integrated) {
            const auto name=std::to_string(seed)+"_"+std::to_string(count)+"_"+std::string(space)+
                            (food?"_balanced":"_empty")+(integrated?"_care":"_control");
            if (selected.empty() || selected==name) {
                ecology(out,dir,seed,count,space,food,integrated,false,mode!="matrix");
                matched=true;
            }
        };
        if (mode=="matrix" || mode=="r1-matrix") {
            for (const std::uint64_t seed:{7U,19U,43U})
                for (const unsigned count:{4U,16U})
                    for (const std::string_view space:{"coarse","fine","chamber"})
                        for (const bool food:{true,false})
                            for (const bool integrated:{false,true}) run(seed,count,space,food,integrated);
        } else if (mode=="r1-depot") {
            for (const std::uint64_t seed:{7U,19U,43U})
                for (const unsigned count:{4U,16U})
                    for (const bool food:{true,false})
                        for (const bool integrated:{false,true}) run(seed,count,"underground",food,integrated);
        } else if (mode=="r1-smoke") {
            ecology(out,dir,7,4,"underground",true,true,true,true);
        } else if (mode=="workload") {
            for (const std::uint64_t seed:{7U,19U,43U})
                for (const unsigned count:{4U,16U})
                    for (const std::string_view space:{"fine","chamber"})
                        for (const bool integrated:{false,true}) ecology(out,dir,seed,count,space,true,integrated);
        } else if (mode=="probes") {
            for (const bool fine:{false,true})
                for (const double radius:{.006,.012}) representation(out,fine,radius);
            closed_tunnel(out);
        } else if (mode=="smoke") {
            ecology(out,dir,7,4,"chamber",true,true,true);
        } else throw std::invalid_argument("unknown ecology mode");
        if (!matched) throw std::invalid_argument("unknown frozen ecology case");
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
