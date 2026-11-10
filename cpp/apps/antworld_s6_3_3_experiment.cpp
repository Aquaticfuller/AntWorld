#include "s6_3_3_fixture.hpp"
#include "process_memory.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <string_view>
using namespace antworld;
using namespace s6_3_3_fixture;
namespace {
constexpr std::int64_t hour=3600000,day=24*hour;
constexpr std::array<std::uint64_t,12> seeds{7,19,43,71,101,137,181,223,269,313,367,421};
constexpr std::array<std::uint64_t,12> holdout_seeds{1009,1013,1019,1021,1031,1033,1039,1049,1051,1061,1063,1069};
struct Outputs {
    std::ofstream windows,scans,runs,events,profiles,initial,ecology;
    explicit Outputs(const std::filesystem::path& directory,bool fidelity)
        :windows(directory/"windows.csv"),scans(directory/"scans.csv"),runs(directory/"runs.csv"),events(directory/"events.csv") {
        windows<<"run,seed,assay,condition,context_age_days,variant,window_h,begin_ms,end_ms,alive,scans51,positive51,positive50,active_ms,inactive_ms,unknown_ms,program_ms,opportunities,contacts,protein_ug,carbs_ug,water_ug,inspect,arrange,clean,transport,feed,worker_contact,body_energy_nj,hydration_ug,last_worker_contact_ms\n";
        scans<<"run,seed,window_h,scan,begin_ms,end_ms,active_care,alive\n";
        runs<<"run,seed,assay,condition,age_days,variant,decision_ms,bout_ms,memory_ms,inhibition,care_probability,worker_contact_probability,perception_m,step_m,arrangement_m,end_ms,events,checkpoint_bytes,advance_ms,checkpoint_ms,restore_ms,continuation_equal,conserved,first_contact_ms,first_retrieval_ms,retrieved,task_end_ms,path_m\n";
        events<<"run,event_id,time_ms,source,kind,actor,stage,target,phase,act,bout,began_ms,duration_known,outcome,x_m,y_m,z_m,carbs_ug,protein_ug,water_ug\n";
        if (fidelity) {
            profiles.open(directory/"profiles.csv");
            initial.open(directory/"initial.csv");
            ecology.open(directory/"ecology.csv");
            profiles<<"run,scenario,layout,variant,origin,neutral_assay,arena_radius_m,speed_cap_m_s,worker_unloaded_m_s,queen_unloaded_m_s,worker_loaded_m_s,queen_loaded_m_s,pickup_ms,placement_ms,manipulation_ms,search_pause_ms,search_steps,integrated\n";
            initial<<"run,role,entity,colony,stage,x_m,y_m,z_m\n";
            ecology<<"run,seed,integrated,end_ms,events,checkpoint_bytes,exact_restore,conserved,births,larvae_at_start\n";
        }
    }
};
struct Window { std::int64_t begin{},label{}; };
double elapsed(std::chrono::steady_clock::time_point start) { return std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count(); }
void advance(WorldRuntime& w,std::int64_t end) {
    while(w.summary().now.milliseconds<end) w.advance_to({std::min(end,w.summary().now.milliseconds+hour)});
}
bool active_care(CareAct act) { return act==CareAct::InspectBrood || act==CareAct::ArrangeBrood || act==CareAct::CleanBrood; }
void record_events(Outputs& out,const std::string& run,const std::vector<WorldEvent>& events) {
    for(const auto& e:events) {
        if(e.kind!=FactKind::BiologicalObservation && e.kind!=FactKind::BroodMoved && e.kind!=FactKind::NutritionTransferred &&
           e.kind!=FactKind::Moved && e.kind!=FactKind::StageChanged && e.kind!=FactKind::AntDied && e.kind!=FactKind::CareProgramChanged &&
           !(out.profiles.is_open() && (e.kind==FactKind::CareTick || e.kind==FactKind::BehaviorChanged ||
             e.kind==FactKind::AutonomyDecision || e.kind==FactKind::ForagingDecision || e.kind==FactKind::AntBorn ||
             e.kind==FactKind::FoodCollected || e.kind==FactKind::FoodDelivered || e.kind==FactKind::SoilExcavated))) continue;
        const auto& o=e.observation;
        out.events<<run<<','<<e.id.value<<','<<e.time.milliseconds<<','<<e.source.value<<','<<static_cast<unsigned>(e.kind)<<','<<e.actor.value<<','<<static_cast<unsigned>(e.stage)<<','
            <<(e.kind==FactKind::BiologicalObservation?o.target.value:e.payload)<<','<<static_cast<unsigned>(o.phase)<<','<<static_cast<unsigned>(o.act)<<','<<o.bout.value<<','
            <<o.began_at.milliseconds<<','<<o.duration_known<<','<<static_cast<unsigned>(e.outcome)<<','<<std::setprecision(17)<<e.position.x<<','<<e.position.y<<','<<e.position.z<<','
            <<e.transferred.carbs_ug<<','<<e.transferred.protein_ug<<','<<e.transferred.water_ug<<'\n';
    }
}
void record_profile(Outputs& out,const std::string& run,std::string_view scenario,std::string_view layout,
                    std::string_view variant,std::string_view origin,const WorldRuntime& w,
                    const EnvironmentCareProfile& environment={}) {
    if (!out.profiles.is_open()) return;
    const auto m=*w.care_profile()->motion;
    out.profiles<<run<<','<<scenario<<','<<layout<<','<<variant<<','<<origin<<','<<environment.neutral_displacement_assay<<','
        <<environment.arena_radius_m<<','<<w.config().max_speed_m_per_s<<','<<m.worker_unloaded_m_per_s<<','<<m.queen_unloaded_m_per_s<<','
        <<m.worker_loaded_m_per_s<<','<<m.queen_loaded_m_per_s<<','<<m.pickup_duration.milliseconds<<','<<m.placement_duration.milliseconds<<','
        <<m.manipulation_duration.milliseconds<<','<<m.search_pause.milliseconds<<','<<static_cast<unsigned>(m.search_steps)<<','<<m.integrate_autonomy<<'\n';
}
void record_initial(Outputs& out,const std::string& run,std::string_view role,const WorldRuntime& w,std::span<const AntRef> refs) {
    if (!out.initial.is_open()) return;
    for (auto ref:refs) {
        const auto a=*w.query_ant(ref);
        out.initial<<run<<','<<role<<','<<a.id.value<<','<<a.colony.value<<','<<static_cast<unsigned>(a.stage)<<','
            <<std::setprecision(17)<<a.position.x<<','<<a.position.y<<','<<a.position.z<<'\n';
    }
}
void assay(Outputs& out,std::uint64_t seed,const std::string& condition,int age,const std::string& variant,
           SpeciesCareProfile profile,bool mesh=false,bool smoke=false) {
    const auto context=age>100?CareContext::EstablishedQueen:CareContext::FoundingQueen;
    const bool absent=condition=="absent" || condition=="no_brood";
    Fixture f(seed,profile,condition=="no_brood"?0:5,absent?0:mesh?3:5,condition=="barrier",context,{age*day},true,condition=="added");
    const std::string name=(mesh?"mesh":"reversal")+std::string("_")+condition+"_"+std::to_string(age)+"_"+variant+"_"+std::to_string(seed);
    record_profile(out,name,"B01","",variant,"",f.w);
    record_initial(out,name,"queen",f.w,std::span{&f.queen,1});
    record_initial(out,name,"worker",f.w,f.workers);
    record_initial(out,name,"brood",f.w,f.brood);
    std::vector<Window> windows;
    const auto start=std::chrono::steady_clock::now();
    if(smoke) windows.push_back({0,0});
    else if(mesh) windows={{2*hour,2},{6*hour,6},{24*hour,24}};
    else {
        windows={{71*hour,0},{96*hour,24},{120*hour,48}};
        advance(f.w,3*day);
        if(condition=="removed" || condition=="added" || condition=="sham") {
            for(auto worker:f.workers) f.w.submit({worker,{3*day+10000},ActionKind::Move,{},
                condition=="removed"?PositionM{.02,0,.02}:PositionM{0,0,-.00025},0});
        }
    }
    // Future windows are queried from the exact committed history, not invented scan labels.
    std::map<std::int64_t,PhysiologyState> physiology_windows;
    std::map<std::int64_t,CareState> care_windows;
    for (const auto& window:windows) { advance(f.w,window.begin+hour); physiology_windows.emplace(window.begin,*f.w.query_physiology(f.queen)); care_windows.emplace(window.begin,*f.w.query_care(f.queen)); }
    const auto advance_ms=elapsed(start);
    conserved(f.w); const auto history=f.w.committed_events();
    std::vector<std::pair<std::int64_t,std::int64_t>> bouts;
    for(const auto& e:history) if(e.actor==f.queen.id && e.kind==FactKind::BiologicalObservation && e.observation.duration_known && active_care(e.observation.act) &&
        (e.observation.phase==ObservationPhase::Completed || e.observation.phase==ObservationPhase::Interrupted)) bouts.emplace_back(e.observation.began_at.milliseconds,e.time.milliseconds);
    const auto current=f.w.query_care(f.queen); if(current->active && active_care(current->act)) bouts.emplace_back(current->began_at.milliseconds,f.w.summary().now.milliseconds);
    for(const auto& window:windows) {
        unsigned positive=0,positive50=0; bool alive=true;
        for(const auto& e:history) if(e.actor==f.queen.id && e.kind==FactKind::AntDied && e.time.milliseconds<window.begin+hour) alive=false;
        for(unsigned minute=5;minute<=55;++minute) {
            const auto begin=window.begin+static_cast<std::int64_t>(minute)*60000,end=begin+10000;
            const bool found=std::any_of(bouts.begin(),bouts.end(),[&](auto b){return b.first<end && b.second>begin;});
            if(found) { ++positive; if(minute<55) ++positive50; }
            out.scans<<name<<','<<seed<<','<<window.label<<','<<minute-5<<','<<begin<<','<<end<<','<<found<<','<<alive<<'\n';
        }
        const auto stats=f.w.behavior_window(f.queen,{window.begin},{window.begin+hour});
        const auto& p=physiology_windows.at(window.begin);
        out.windows<<name<<','<<seed<<','<<(mesh?"mesh":"reversal")<<','<<condition<<','<<age<<','<<variant<<','<<window.label<<','<<window.begin<<','<<window.begin+hour<<','<<alive<<",51,"<<positive<<','<<positive50<<','
            <<stats.known_active_ms<<','<<stats.known_inactive_ms<<','<<stats.unknown_activity_ms<<','<<stats.care_program_ms<<','<<stats.contact_opportunities<<','<<stats.successful_contacts<<','<<stats.transferred.protein_ug<<','<<stats.transferred.carbs_ug<<','<<stats.transferred.water_ug;
        for(auto act:{CareAct::InspectBrood,CareAct::ArrangeBrood,CareAct::CleanBrood,CareAct::TransportBrood,CareAct::FeedBrood,CareAct::CloseWorkerContact}) out.windows<<','<<stats.completed[static_cast<std::size_t>(act)];
        out.windows<<','<<p.body_energy_nj<<','<<p.hydration_ug<<','<<care_windows.at(window.begin).last_worker_contact.milliseconds<<'\n';
    }
    auto clock=std::chrono::steady_clock::now(); const auto bytes=f.w.checkpoint(); const auto checkpoint_ms=elapsed(clock);
    clock=std::chrono::steady_clock::now(); WorldRuntime replay({1,1},0,{},limits()); replay.restore(bytes); const auto restore_ms=elapsed(clock);
    const auto end=f.w.summary().now; replay.advance_to({end.milliseconds+1234}); f.w.advance_to({end.milliseconds+1234});
    const bool equal=f.w.checkpoint()==replay.checkpoint(); require(equal,"assay restore continuation differs");
    out.runs<<name<<','<<seed<<','<<(mesh?"mesh":"reversal")<<','<<condition<<','<<age<<','<<variant<<','<<profile.decision_interval.milliseconds<<','<<profile.bout_duration.milliseconds<<','<<profile.social_memory_horizon.milliseconds<<','<<profile.maximum_inhibition<<','<<profile.care_probability<<','<<profile.worker_contact_probability<<','<<profile.perception_radius_m<<','<<profile.step_m<<','<<profile.arrangement_m<<','<<end.milliseconds<<','<<history.size()<<','<<bytes.size()<<','<<advance_ms<<','<<checkpoint_ms<<','<<restore_ms<<','<<equal<<",1,,,,,\n";
    record_events(out,name,history); out.runs.flush(); out.windows.flush(); out.scans.flush(); out.events.flush();
}
void retrieval(Outputs& out,std::uint64_t seed,bool group,SpeciesCareProfile profile={},std::string_view layout="line",
               std::string_view scenario={},std::string_view variant="base",bool neutral=false,bool foreign=false) {
    const auto environment=EnvironmentCareProfile{21,.8,neutral,profile.motion?.025:0};
    Fixture f(seed,profile,0,group?3:0,false,CareContext::FoundingQueen,{4752000000LL},true,false,environment,profile.motion?.08:.01);
    const auto donor=profile.motion?f.w.seed_colony({.02,0,0}):f.colony;
    f.w.pause_brood_care(f.queen);
    if(group) { auto p=physiology();
        for(auto worker:f.workers) f.w.enable_physiology(worker,{{0,100,0,0},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
    }
    for(unsigned i=0;layout!="empty" && i<6;++i) {
        PositionM place{.005+static_cast<double>(i)*.002,0,0};
        if (layout=="mirror") place.x=-place.x;
        if (layout=="far") place.x=.009+static_cast<double>(i)*.002;
        if (layout=="split" && i>=3) place={0,0,-(.005+static_cast<double>(i-3)*.002)};
        if (layout=="sheltered") place={-.0005,0,static_cast<double>(i%5)*.00025};
        f.brood.push_back(f.w.seed_ant(foreign?donor:f.colony,{place,i%2?LifeStage::Pupa:LifeStage::Larva}));
    }
    std::string name="retrieval_"+std::string(group?"workers":"queen")+"_"+std::to_string(seed)+
        (layout=="line"?std::string{}:"_"+std::string(layout));
    if (!scenario.empty()) {
        name+="_"+std::string(scenario)+"_"+std::string(variant)+(foreign?"_foreign":"_own")+(neutral?"_neutral":"_protected");
        record_profile(out,name,scenario,layout,variant,foreign?"foreign":"own",f.w,environment);
        if (group) record_initial(out,name,"worker",f.w,f.workers);
        else record_initial(out,name,"queen",f.w,std::span{&f.queen,1});
        record_initial(out,name,"brood",f.w,f.brood);
    }
    const auto start=std::chrono::steady_clock::now(); advance(f.w,180000);
    if(group) for(auto worker:f.workers) f.w.enable_brood_care(worker,{CareContext::Worker,{30*day}});
    else f.w.enable_brood_care(f.queen,f.w.query_care(f.queen)->profile);
    const auto baseline=f.w.committed_events().size();
    advance(f.w,780000); const auto advance_ms=elapsed(start); const auto events=f.w.committed_events();
    std::set<EntityId> retrieved; std::int64_t first_contact=-1,first_retrieval=-1,task_end=-1; double path=0;
    std::map<EntityId,PositionM> positions; for(auto actor:group?f.workers:std::vector<AntRef>{f.queen}) positions[actor.id]={};
    for(std::size_t i=0;i<events.size();++i) {
        const auto& e=events[i];
        if(e.kind==FactKind::Moved && positions.contains(e.actor)) {
            const auto old=positions.at(e.actor); if(i>=baseline) path+=std::hypot(e.position.x-old.x,e.position.y-old.y,e.position.z-old.z); positions[e.actor]=e.position;
        }
        if(i<baseline) continue;
        const auto& o=e.observation;
        if(e.kind==FactKind::BiologicalObservation && o.phase==ObservationPhase::Started &&
           ((o.act>=CareAct::InspectBrood && o.act<=CareAct::FeedBrood) || o.act==CareAct::PickUpBrood) &&
           first_contact<0) first_contact=e.time.milliseconds-180000;
        EntityId placement;
        if (profile.motion) {
            if (e.kind==FactKind::BiologicalObservation && o.phase==ObservationPhase::Completed && o.act==CareAct::PlaceBrood)
                placement=o.target;
        } else if (layout!="sheltered" && e.kind==FactKind::BroodMoved && std::hypot(e.position.x,e.position.y,e.position.z)<=f.w.config().contact_distance_m) {
            placement=e.actor;
        }
        if (placement.value) {
            retrieved.insert(placement); if(first_retrieval<0) first_retrieval=e.time.milliseconds-180000; if(retrieved.size()==6 && task_end<0) task_end=e.time.milliseconds-180000;
        }
    }
    auto clock=std::chrono::steady_clock::now(); const auto bytes=f.w.checkpoint(); const auto checkpoint_ms=elapsed(clock);
    clock=std::chrono::steady_clock::now(); WorldRuntime replay({1,1},0,{},limits()); replay.restore(bytes); const auto restore_ms=elapsed(clock);
    require(bytes==replay.checkpoint(),"retrieval restore mismatch"); conserved(f.w);
    out.runs<<name<<','<<seed<<",retrieval,"<<(group?"three_workers":"queen")<<",0,"<<variant<<','<<profile.decision_interval.milliseconds<<','<<profile.bout_duration.milliseconds<<','<<profile.social_memory_horizon.milliseconds<<','<<profile.maximum_inhibition<<','<<profile.care_probability<<','<<profile.worker_contact_probability<<','<<profile.perception_radius_m<<','<<profile.step_m<<','<<profile.arrangement_m<<",780000,"<<events.size()<<','<<bytes.size()<<','<<advance_ms<<','<<checkpoint_ms<<','<<restore_ms<<",1,1,"<<first_contact<<','<<first_retrieval<<','<<retrieved.size()<<','<<task_end<<','<<path<<'\n';
    record_events(out,name,events);
}

void b01(Outputs& out,std::uint64_t seed,std::size_t index,const SpeciesCareProfile& profile) {
    for (const std::string condition:{"absent","added","removed"}) assay(out,seed,condition,55,"base",profile);
    if (index==0) {
        assay(out,seed,"sham",55,"base",profile);
        assay(out,seed,"no_brood",55,"base",profile);
        assay(out,seed,"barrier",52,"base",profile,true);
        assay(out,seed,"removed",932,"base",profile);
    }
}

void fidelity_b02(Outputs& out,std::uint64_t seed,const std::string& mode,SpeciesCareProfile base) {
    for (const bool group:{false,true}) {
        if (mode=="fidelity-b02") {
            retrieval(out,seed,group,base,"line","B02_line","base",true,false);
            retrieval(out,seed,group,base,"line","B02_line","base",true,true);
            retrieval(out,seed,group,base,"line","B02_line","base",false,false);
        } else if (mode=="fidelity-robustness") {
            for (const std::string_view layout:{"line","mirror","split","far","empty","sheltered"})
                retrieval(out,seed,group,base,layout,"B02_robustness","base",true,false);
        } else {
            retrieval(out,seed,group,base,"far","B02_sensitivity","base",true,false);
            for (const std::string_view variant:{"unloaded_low","unloaded_high","loaded_low","loaded_high","decision_fast","decision_slow","search_one"}) {
                auto profile=base;
                auto& m=*profile.motion;
                if (variant=="unloaded_low") { m.worker_unloaded_m_per_s=.005; m.queen_unloaded_m_per_s=.002; }
                if (variant=="unloaded_high") { m.worker_unloaded_m_per_s=.05; m.queen_unloaded_m_per_s=.02; }
                if (variant=="loaded_low") { m.worker_loaded_m_per_s=.001; m.queen_loaded_m_per_s=.001; }
                if (variant=="loaded_high") { m.worker_loaded_m_per_s=.012; m.queen_loaded_m_per_s=.012; }
                if (variant=="decision_fast") profile.decision_interval={15000};
                if (variant=="decision_slow") profile.decision_interval={120000};
                if (variant=="search_one") m.search_steps=1;
                for (const std::string_view layout:{"line","far"})
                    retrieval(out,seed,group,profile,layout,"B02_sensitivity",variant,true,false);
            }
        }
    }
}

void integrated_assay(Outputs& out,std::uint64_t seed,SpeciesCareProfile profile,bool integrated) {
    WorldRuntime world({6332,seed},seed,{{-.025,-.01,-.025},{.025,.01,.025},.08,.002},limits());
    world.configure_long_term();
    BehaviorConfig forage; forage.step_duration={100}; forage.route_capacity=8; forage.max_trip_moves=8;
    world.configure_surface({{-.010,0,-.002},21,5,.001},{},forage);
    SocialConfig social; social.decision_interval={500}; social.minimum_program_time={500};
    social.nurse_weight=20; social.gift_first=true; social.local_work_continuation=true;
    world.configure_social(social);
    profile.motion->integrate_autonomy=integrated;
    world.configure_biology(profile);
    const auto nest=world.seed_colony();
    const auto queen=world.seed_ant(nest,{{},LifeStage::Adult,Caste::Queen});
    auto maternal=physiology(); maternal.adult_protein_target_ug=20;
    world.enable_physiology(queen,{{0,500,0,0},maternal.energy_capacity_nj,maternal.hydration_capacity_ug,0},maternal);
    ReproductionConfig reproduction; reproduction.interval={20000};
    world.enable_reproduction(queen,reproduction);
    if (integrated) world.set_autonomy(queen,true);
    const auto p=physiology();
    std::array<AntRef,3> workers{},larvae{};
    for (std::size_t i=0;i<workers.size();++i) {
        workers[i]=world.seed_ant(nest,{});
        world.enable_physiology(workers[i],{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
        world.set_autonomy(workers[i],true);
        larvae[i]=world.seed_ant(nest,{{.004+static_cast<double>(i)*.001,0,0},LifeStage::Larva});
        world.enable_physiology(larvae[i],{{},p.energy_capacity_nj/2,500,0},p);
    }
    world.seed_food({-.001,0,0},{5000,1000,200,0});
    const auto run="ecology_"+std::to_string(seed)+(integrated?"_lease":"_control");
    record_profile(out,run,"integration","",integrated?"lease":"control","own",world);
    record_initial(out,run,"queen",world,std::span{&queen,1});
    record_initial(out,run,"worker",world,workers);
    record_initial(out,run,"brood",world,larvae);
    world.advance_to({45000});
    const auto checkpoint=world.checkpoint();
    WorldRuntime replay({1,1},0,{},limits());
    replay.restore(checkpoint);
    for (const SimTime end:{SimTime{60000},SimTime{75000},SimTime{90000}}) replay.advance_to(end);
    world.advance_to({90000});
    require(world.checkpoint()==replay.checkpoint(),"ecology save or partition changed continuation");
    conserved(world);
    const auto facts=world.committed_events();
    out.ecology<<run<<','<<seed<<','<<integrated<<",90000,"<<facts.size()<<','<<world.checkpoint().size()<<",1,1,"
        <<world.query_reproduction(queen)->births<<','<<larvae.size()<<'\n';
    record_events(out,run,facts);
}
}
int main(int argc,char** argv) {
    try {
        if(argc<2 || argc>5) throw std::invalid_argument("usage: antworld_s6_3_3_experiment OUTPUT [SEED_INDEX|all] [MODE] [legacy|local]");
        const std::string mode=argc>3?argv[3]:"primary",which=argc>2?argv[2]:"all";
        const std::string_view policy=argc>4?argv[4]:"legacy";
        const bool fidelity=mode.starts_with("fidelity-");
        if ((fidelity && policy!="fidelity") || (!fidelity && policy!="legacy" && policy!="local"))
            throw std::invalid_argument("unknown care policy for experiment");
        SpeciesCareProfile study; study.local_retrieval=policy=="local";
        if (fidelity) { study.local_retrieval=true; study.motion.emplace(); }
        const bool held_out=mode.starts_with("holdout-") || mode=="fidelity-robustness";
        const bool retrieval_only=mode.starts_with("holdout-") || mode.starts_with("retrieval-");
        const auto layout=retrieval_only?std::string_view(mode).substr(mode.find('-')+1):std::string_view("line");
        if (layout!="line" && layout!="mirror" && layout!="split" && layout!="far" && layout!="empty" && layout!="sheltered")
            throw std::invalid_argument("unknown brood placement");
        const std::filesystem::path directory=argv[1]; std::filesystem::create_directories(directory); Outputs out(directory,fidelity);
        const auto& selected=held_out?holdout_seeds:seeds;
        for(std::size_t index=0;index<selected.size();++index) {
            if(which!="all" && index!=std::stoull(which)) continue;
            const auto seed=selected[index];
            if(mode=="smoke") { assay(out,seed,"absent",55,"base",{},false,true); retrieval(out,seed,false); break; }
            if (fidelity) {
                if (mode=="fidelity-b02" || mode=="fidelity-robustness" || (mode=="fidelity-sensitivity" && index<6))
                    fidelity_b02(out,seed,mode,study);
                else if (mode=="fidelity-b01") b01(out,seed,index,study);
                else if (mode=="fidelity-b01-sensitivity" && index<6) {
                    for (const int duration:{500,10000}) {
                        auto profile=study;
                        profile.motion->manipulation_duration={duration};
                        for (const std::string condition:{"absent","added","removed"})
                            assay(out,seed,condition,55,"manipulation"+std::to_string(duration)+"ms",profile);
                    }
                } else if (mode=="fidelity-integration" && index<6) {
                    for (const bool integrated:{false,true}) integrated_assay(out,seed,study,integrated);
                } else if (mode!="fidelity-sensitivity" && mode!="fidelity-b01-sensitivity" && mode!="fidelity-integration")
                    throw std::invalid_argument("unknown fidelity mode");
            } else if (retrieval_only) {
                retrieval(out,seed,false,study,layout);
                retrieval(out,seed,true,study,layout);
            } else if (mode=="b01") b01(out,seed,index,study);
            else if(mode=="primary") {
                for(int age:{35,55,932}) for(const std::string condition:{"absent","present","added","removed","sham","no_brood"}) assay(out,seed,condition,age,"base",{});
                for(const std::string condition:{"absent","present","barrier"}) assay(out,seed,condition,52,"base",{},true);
                retrieval(out,seed,false); retrieval(out,seed,true);
            } else if(mode=="sensitivity" && index<6) {
                for(const std::string variant:{"memory1h","memory24h","inhibition0","inhibition0_4","decision15s","decision240s"}) {
                    SpeciesCareProfile p;
                    if(variant=="memory1h") p.social_memory_horizon={hour};
                    if(variant=="memory24h") p.social_memory_horizon={day};
                    if(variant=="inhibition0") p.maximum_inhibition=0;
                    if(variant=="inhibition0_4") p.maximum_inhibition=.4;
                    if(variant=="decision15s") p.decision_interval={15000};
                    if(variant=="decision240s") p.decision_interval={240000};
                    for(const std::string condition:{"absent","present","removed"}) assay(out,seed,condition,55,variant,p);
                }
            } else if(mode!="sensitivity") throw std::invalid_argument("unknown experiment mode");
        }
        std::cout<<"Completed "<<mode<<" seed selection "<<which<<'\n'; return 0;
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
