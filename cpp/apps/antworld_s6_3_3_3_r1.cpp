#include "s6_3_3_3_fixture.hpp"
#include "antworld/storage/store.hpp"
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>

using namespace antworld;
using namespace antworld::closure;

namespace {
constexpr WorldConfig spatial{{-.04,-.03,-.04},{.04,.03,.04},.08,.002,true};

struct Output {
    std::filesystem::path root;
    std::ofstream cases,events;
    explicit Output(std::filesystem::path p)
        :root(std::move(p)),cases(root/"cases.csv",std::ios::binary),events(root/"events.csv",std::ios::binary) {
        for (auto* f:{&cases,&events}) {
            f->exceptions(std::ios::failbit|std::ios::badbit);
            *f<<std::setprecision(17);
        }
        cases<<"case,cell_m,stride_m,first_ms,last_ms,physical_moves,endpoint_x_m,endpoint_y_m,endpoint_z_m,trace_hash,checkpoint_bytes\n";
        events<<"case,event,time_ms,kind,actor,related,source,phase,act,bout,began_ms,duration_known,outcome,x_m,y_m,z_m,carbs_ug,protein_ug,water_ug,other_ug\n";
    }
    void dump(std::string_view name,const WorldRuntime& w,double cell,double step,SimTime first,PositionM p) {
        std::size_t moves=0;
        for (const auto& e:w.committed_events()) {
            const auto& o=e.observation;
            moves+=e.kind==FactKind::Moved || e.kind==FactKind::BroodMoved;
            events<<name<<','<<e.id.value<<','<<e.time.milliseconds<<','<<static_cast<unsigned>(e.kind)<<','<<e.actor.value
                  <<','<<(e.kind==FactKind::BiologicalObservation?o.target.value:e.payload)<<','<<e.source.value<<','
                  <<static_cast<unsigned>(o.phase)<<','<<static_cast<unsigned>(o.act)<<','<<o.bout.value<<','
                  <<o.began_at.milliseconds<<','<<o.duration_known<<','<<static_cast<unsigned>(e.outcome)<<','
                  <<e.position.x<<','<<e.position.y<<','<<e.position.z;
            for (auto amount:e.transferred.components()) events<<','<<amount;
            events<<'\n';
        }
        cases<<name<<','<<cell<<','<<step<<','<<first.milliseconds<<','<<w.summary().now.milliseconds<<','<<moves
             <<','<<p.x<<','<<p.y<<','<<p.z<<','<<w.snapshot().trace_hash<<','<<w.checkpoint().size()<<'\n';
        cases.flush();
        events.flush();
    }
};

template<class Predicate> void until(WorldRuntime& w,SimTime limit,Predicate condition) {
    while (!condition()) {
        const auto pending=w.pending_events();
        require(!pending.empty() && pending.front().key.time<=limit,"expected spatial event before deadline");
        w.advance_to(pending.front().key.time);
    }
}

std::optional<WorldEvent> find(const WorldRuntime& w,FactKind kind,EntityId actor={},CareAct act=CareAct::Inactive,
                               ObservationPhase phase=ObservationPhase::Completed) {
    for (const auto& e:w.committed_events())
        if (e.kind==kind && (!actor.value || e.actor==actor) &&
            (kind!=FactKind::BiologicalObservation || (e.observation.act==act && e.observation.phase==phase)))
            return e;
    return {};
}

void exact(WorldRuntime& w) {
    const auto bytes=w.checkpoint();
    w.restore(bytes);
    require(w.checkpoint()==bytes,"spatial checkpoint round trip differs");
    s6_3_fixture::conserved(w);
}

WorldConfig translated_world(double x) {
    auto c=spatial;
    c.min_m.x+=x; c.max_m.x+=x;
    return c;
}

void reach_boundary(Output& out) {
    for (const auto origin:{0.,12.}) for (const int offset_nm:{-1,0,1}) {
        WorldRuntime w({63331,7},7,translated_world(origin),limits());
        const auto colony=w.seed_colony({origin,0,0});
        const auto worker=w.seed_ant(colony,{{origin+.007,0,0}});
        const auto food=w.seed_food({origin+.0090000000000000011+offset_nm*1e-9,0,0},{60,0,0,0});
        w.submit({worker,{1},ActionKind::CollectFood,food,{},60});
        w.advance_to({1});
        const auto gain=w.query_ant(worker)->carried_food.carbs_ug;
        require(gain==(offset_nm<=0?60:0),"physical reach admitted an exterior gap or rejected a boundary");
        if (offset_nm>0) require(find(w,FactKind::ActionRejected,worker.id)->outcome==Outcome::OutOfReach,
                                 "unexpected reason for a real separation");
        exact(w);
        const auto name=std::string(origin==0?"reach_origin_":"reach_translated_")+std::to_string(offset_nm);
        out.dump(name,w,0,0,{1},w.query_ant(worker)->position);
    }
}

void ordinary_motion(Output& out) {
    WorldRuntime w({63331,7},7,spatial,limits());
    constexpr std::array<Cell,1> blocked{{{1,1}}};
    w.configure_surface({{},4,4,.010},blocked);
    const auto colony=w.seed_colony();
    const auto worker=w.seed_ant(colony,{});
    const auto move=[&](SimTime t,PositionM dest,Outcome outcome) {
        w.submit({worker,t,ActionKind::Move,{},dest});
        const auto before=w.query_ant(worker);
        w.advance_to(t);
        const auto last=w.committed_events().back();
        require(last.outcome==outcome,"wrong ordinary movement outcome");
        const auto after=w.query_ant(worker);
        if (outcome==Outcome::Success) require(after->position==dest && after->position_revision==before->position_revision+1,
                                              "ordinary continuous position was snapped");
        else require(after==before,"a blocked or overspeed step changed the actor");
    };
    move({100},{.001,0,0},Outcome::Success);
    move({300},{.006,0,0},Outcome::Success);
    move({301},{.009,0,0},Outcome::TooFast);
    move({1000},{.012,0,.020},Outcome::Blocked);
    move({1200},{.01,0,0},Outcome::Success);
    move({1800},{.02,0,.01},Outcome::Blocked); // The diagonal grazes the blocked corner.
    exact(w);
    out.dump("ordinary_mask",w,.010,0,{},w.query_ant(worker)->position);
}

struct CareWorld {
    WorldRuntime w;
    AntRef caregiver,target,competitor;
    CareWorld(double cell,double stride,bool geometry=false,bool turn=false,bool two=false,LifeStage stage=LifeStage::Larva)
        :w({63331,7},7,spatial,limits()) {
        w.configure_long_term();
        if (cell>0) {
            BehaviorConfig behavior;
            behavior.trails_enabled=false;
            w.configure_surface({{-.02,0,-.01},cell<.005?41U:5U,cell<.005?21U:3U,cell},{},behavior);
        }
        if (geometry) {
            GeometryConfig g;
            g.origin_m={-.008,-.008,-.008};
            g.initial_solid={{0,0,0},{32,16,32}};
            constexpr std::array<BoxQ,4> around_corner{{{{4,2,4},{22,14,31}},{{23,2,4},{31,14,31}},
                                                       {{22,2,4},{23,14,26}},{{22,2,27},{23,14,31}}}};
            constexpr std::array<BoxQ,1> room{{{{4,2,4},{31,14,31}}}};
            w.configure_geometry(g,turn?std::span<const BoxQ>(around_corner):std::span<const BoxQ>(room));
        }
        w.configure_social(day_social());
        auto care=timed_care(false);
        care.perception_radius_m=.012;
        care.step_m=stride;
        care.care_probability=1; // ENGINEERING_FIXTURE control for motion and exclusive ownership.
        w.configure_biology(care);
        const PositionM home{0,geometry?-.004:0,0};
        const auto colony=w.seed_colony(home);
        caregiver=w.seed_ant(colony,{home,LifeStage::Adult,Caste::Queen});
        w.enable_physiology(caregiver,adult,day_physiology());
        const auto initial=geometry?PositionM{.006,turn?-.004:-.0025,.006}:PositionM{.010,0,0};
        target=w.seed_ant(colony,{initial,stage});
        if (two) {
            competitor=w.seed_ant(colony,{home,LifeStage::Adult,Caste::Queen});
            w.enable_physiology(competitor,adult,day_physiology());
            w.enable_brood_care(competitor,{CareContext::FoundingQueen,{}});
        }
        w.enable_brood_care(caregiver,{CareContext::FoundingQueen,{}});
    }
    void loaded() {
        until(w,{30000},[&] {
            const auto c=w.query_care(caregiver);
            return c->active && c->carrying_brood && c->act==CareAct::TransportBrood;
        });
    }
};

void care_motion_matrix(Output& out) {
    ordinary_motion(out);
    for (const auto stride:{.0005,.001,.002}) {
        std::optional<SimTime> time;
        for (const auto cell:{.001,.010}) {
            CareWorld f(cell,stride);
            auto& w=f.w;
            until(w,{30000},[&]{ return find(w,FactKind::BiologicalObservation,f.caregiver.id,CareAct::PlaceBrood).has_value(); });
            const auto finish=w.query_ant(f.target)->position;
            require(finish.x>0 && finish.x<=.002+1e-15 && finish.y==0 && finish.z==0,"physical placement outside shelter");
            if (time) require(w.summary().now==*time,"equivalent surface geometry changed motor time");
            time=w.summary().now;
            require(w.query_ant(f.target)->position_revision>=4 && !w.query_care(f.caregiver)->carrying_brood,
                    "placement lacks committed carried segments");
            exact(w);
            const auto name=std::string(cell<.005?"fine_":"coarse_")+std::to_string(static_cast<unsigned>(stride*1e6));
            out.dump(name,w,cell,stride,{1},finish);
        }
    }
}

void spatial_custody(Output& out) {
    reach_boundary(out);
    for (bool turn:{false,true}) {
        CareWorld f(0,.001,true,turn);
        auto& w=f.w;
        f.loaded();
        const auto grip=w.query_care(f.caregiver)->grip_offset;
        const auto held=w.checkpoint();
        const auto label=std::string(turn?"turn":"diagonal");
        storage::Store store(out.root/(label+".sqlite"),limits());
        store.save(w);
        auto restored=store.load(w.summary().world);
        require(restored.world.checkpoint()==held && restored.world.query_care(f.caregiver)->grip_offset==grip,
                "held grip failed durable restore");
        WorldRuntime split({1,1},0,{},limits());
        split.restore(held);
        const auto first=w.summary().now;
        until(w,{30000},[&]{return find(w,FactKind::BiologicalObservation,f.caregiver.id,CareAct::PlaceBrood).has_value();});
        const auto end=w.summary().now;
        for (auto t=first.milliseconds+137;t<end.milliseconds;t+=137) split.advance_to({t});
        split.advance_to(end);
        restored.world.advance_to(end);
        require(w.checkpoint()==split.checkpoint() && w.checkpoint()==restored.world.checkpoint(),
                "held movement differs after partition or SQLite continuation");
        bool diagonal=false,axis=false;
        auto previous=w.query_care(f.caregiver)->retrieval.pickup_site;
        for (const auto& e:w.committed_events()) if (e.kind==FactKind::Moved && e.actor==f.caregiver.id && e.time>first) {
            const auto axes=(e.position.x!=previous.x)+(e.position.y!=previous.y)+(e.position.z!=previous.z);
            diagonal|=axes>=2; axis|=axes==1;
            previous=e.position;
        }
        require(diagonal && (!turn || axis),"three-dimensional carried path did not exercise the expected direction change");
        require(!w.query_care(f.caregiver)->carrying_brood && w.query_ant(f.target)->position_revision>=3,
                "three-dimensional hold did not move and place the same brood");
        exact(w);
        out.dump(label,w,0,.001,first,w.query_ant(f.target)->position);
    }
    for (std::string_view reason:{"pause","death_actor","death_target","mature_target","budget","competition"}) {
        const bool mature=reason=="mature_target";
        CareWorld f(.010,.001,false,false,reason=="competition",mature?LifeStage::Pupa:LifeStage::Larva);
        auto& w=f.w;
        if (reason=="competition") {
            until(w,{10000},[&] {
                return w.query_care(f.caregiver)->carrying_brood || w.query_care(f.competitor)->carrying_brood;
            });
            require(w.query_care(f.caregiver)->carrying_brood!=w.query_care(f.competitor)->carrying_brood,
                    "competing caregivers acquired simultaneous custody");
            require(find(w,FactKind::BiologicalObservation,{},CareAct::PickUpBrood,ObservationPhase::Interrupted).has_value(),
                    "competing pickup did not retain its rejected fact");
        } else {
            f.loaded();
            const auto before=w.query_ant(f.target)->position;
            if (reason=="budget") {
                auto budget=limits();
                budget.committed_events=w.summary().committed_events+2;
                const auto bytes=w.checkpoint();
                WorldRuntime failed({1,1},0,{},budget);
                failed.restore(bytes);
                bool rejected=false;
                try { failed.advance_to(failed.pending_events().front().key.time); }
                catch (const std::length_error&) { rejected=true; }
                require(rejected && failed.checkpoint()==bytes,"failed carried segment did not roll back");
            } else {
                if (reason=="pause") w.pause_brood_care(f.caregiver);
                else {
                    const SimTime t{w.summary().now.milliseconds+1};
                    w.schedule_lifecycle(reason=="death_actor"?f.caregiver:f.target,t,mature?LifeStage::Adult:LifeStage::Dead);
                    w.advance_to(t);
                }
                require(!w.query_care(f.caregiver)->carrying_brood && w.query_ant(f.target)->position==before,
                        "cancellation moved or retained held brood");
            }
        }
        exact(w);
        out.dump(reason,w,.010,.001,{},w.query_ant(f.target)->position);
    }
}

void held_wall(Output& out) {
    WorldRuntime w({63331,7},7,spatial,limits());
    w.configure_long_term();
    w.configure_social(day_social());
    auto care=timed_care(false);
    care.care_probability=1; // ENGINEERING_FIXTURE controls the intervention time.
    w.configure_biology(care);
    GeometryConfig g;
    const BoxQ tunnel{{2,10,10},{28,14,14}};
    w.configure_geometry(g,std::span{&tunnel,1});
    const auto position=[&](int x) { return PositionM{x*g.quantum_m,-.010,.006}; };
    const auto colony=w.seed_colony(position(12));
    const auto queen=w.seed_ant(colony,{position(12),LifeStage::Adult,Caste::Queen});
    const auto brood=w.seed_ant(colony,{position(19),LifeStage::Larva});
    const auto digger=w.seed_ant(colony,{position(12),LifeStage::Adult,Caste::Worker,20000});
    w.enable_physiology(queen,adult,day_physiology());
    w.enable_brood_care(queen,{CareContext::FoundingQueen,{}});
    w.submit_soil({digger,{100},SoilAction::Excavate,{{10,14,10},{14,15,14}},{},0});
    until(w,{15000},[&] {
        const auto state=w.query_care(queen);
        return state->active && state->carrying_brood && state->act==CareAct::TransportBrood;
    });
    const auto when=w.summary().now;
    const auto last=w.query_ant(brood)->position;
    const auto source=w.soil_parcels().front().id;
    const SimTime fill{when.milliseconds+g.work_duration.milliseconds};
    w.submit_soil({digger,fill,SoilAction::Fill,{{14,10,10},{15,14,14}},{w.summary().world,source},1});
    const auto loaded=w.checkpoint();
    WorldRuntime restored({1,1},0,{},limits());
    restored.restore(loaded);
    w.advance_to(fill);
    restored.advance_to(fill);
    require(w.checkpoint()==restored.checkpoint() && w.geometry_edits().size()==2 &&
        w.query_ant(brood)->position==last && !w.query_care(queen)->carrying_brood,
        "wall did not release the physical load in place");
    const auto stop=find(w,FactKind::BiologicalObservation,queen.id,CareAct::TransportBrood,ObservationPhase::Interrupted);
    require(stop && stop->outcome==Outcome::Blocked,"wall interruption lacks a committed cause");
    exact(w);
    out.dump("held_fill",w,0,.001,when,last);
}

struct Shaft {
    GeometryConfig geometry;
    BoxQ chamber,shaft;
    PositionM depot{0,-.005,0};
    Shaft(unsigned width,bool offset) {
        geometry.origin_m={-.008,-.008,-.008};
        geometry.initial_solid={{0,0,0},{32,16,32}};
        chamber={{7,2,7},{27,11,25}};
        const auto left=offset?18:14;
        shaft={{left,9,14},{left+static_cast<std::int32_t>(width),16,18}};
    }
    [[nodiscard]] PositionM point(int x,int y,int z) const {
        return {geometry.origin_m.x+x*geometry.quantum_m,geometry.origin_m.y+y*geometry.quantum_m,
                geometry.origin_m.z+z*geometry.quantum_m};
    }
};

void connection(Output& out,double cell,unsigned width,bool offset,bool closure) {
    const auto name=std::string(cell<.005?"fine":"coarse")+(width<4?"_narrow":offset?"_offset":closure?"_fill":"_wide");
    WorldRuntime w({63331,7},7,spatial,limits());
    BehaviorConfig behavior;
    behavior.trails_enabled=false;
    w.configure_surface({{},cell<.005?21U:3U,1,cell},{},behavior);
    const Shaft layout(width,offset);
    const auto& g=layout.geometry;
    const std::array voids{layout.chamber,layout.shaft};
    w.configure_geometry(g,voids);
    const auto colony=w.seed_colony(layout.depot);
    const auto worker=w.seed_ant(colony,{layout.depot});
    const auto food=w.seed_food({.010,0,0},{1300,130,700,0});
    if (width<4) {
        const auto empty=w.query_route(worker,layout.point(layout.shaft.min.x+2,18,16));
        require(empty.found,"narrow control lacks unloaded clearance");
        const auto bytes=w.checkpoint();
        bool rejected=false;
        try { w.start_foraging(worker); } catch (const std::invalid_argument&) { rejected=true; }
        require(rejected && w.checkpoint()==bytes,"loaded route crossed a genuinely narrow shaft");
        out.dump(name,w,cell,0,{},w.query_ant(worker)->position);
        return;
    }
    AntRef digger;
    if (closure) {
        digger=w.seed_ant(colony,{layout.point(16,9,16),LifeStage::Adult,Caste::Worker,20000});
        w.submit_soil({digger,{100},SoilAction::Excavate,{{18,11,14},{20,13,18}},{},0});
    }
    w.start_foraging(worker);
    try {
        until(w,{90000},[&]{return w.query_ant(worker)->carried_food.total_ug()!=0;});
    } catch (...) {
        out.dump(name+"_before_collection",w,cell,0,{},w.query_ant(worker)->position);
        throw;
    }
    const auto collected=w.summary().now;
    require(w.query_food(food)->remaining.total_ug()==0,"worker failed to collect the seeded external stock");
    if (closure) {
        const auto parcel=w.soil_parcels();
        require(parcel.size()==1 && parcel[0].remaining_q3==16,"intervention did not excavate source soil");
        const BoxQ wall{{14,12,14},{18,13,18}};
        const SimTime fill{collected.milliseconds+100};
        w.submit_soil({digger,fill,SoilAction::Fill,wall,{w.summary().world,parcel.front().id},1});
        w.advance_to({fill.milliseconds+15000});
        require(w.geometry_edits().size()==2 && !find(w,FactKind::FoodDelivered,worker.id) &&
            w.query_ant(worker)->carried_food.total_ug()>0,"loaded route did not stop on real fill");
        const auto stopped=w.query_ant(worker)->position;
        w.advance_to({w.summary().now.milliseconds+3000});
        require(w.query_ant(worker)->position==stopped,"loaded worker crossed a closed shaft");
        const SimTime reopen{w.summary().now.milliseconds+100};
        w.submit_soil({digger,reopen,SoilAction::Excavate,wall,{},2});
        storage::Store store(out.root/(name+".sqlite"),limits());
        store.save(w);
        auto restored=store.load(w.summary().world);
        const SimTime end{reopen.milliseconds+9000};
        w.advance_to(end);
        restored.world.advance_to(reopen);
        restored.world.advance_to(end);
        require(w.geometry_edits().size()==3 && w.checkpoint()==restored.world.checkpoint(),
                "reopened connector did not resume identically from blocked SQLite state");
    } else {
        try {
            until(w,{120000},[&]{return find(w,FactKind::FoodDelivered,worker.id).has_value();});
        } catch (...) {
            out.dump(name+"_before_delivery",w,cell,0,collected,w.query_ant(worker)->position);
            throw;
        }
    }
    const auto delivered=find(w,FactKind::FoodDelivered,worker.id);
    require(delivered && delivered->position==layout.depot && delivered->transferred==FoodMass{1300,130,700,0},
            "worker did not complete the exterior-to-underground cargo round trip");
    exact(w);
    out.dump(name,w,cell,0,collected,delivered->position);
}
} // namespace

int main(int argc,char** argv) {
    try {
        if (argc!=3) throw std::invalid_argument("usage: antworld_s6_3_3_3_r1 OUTPUT_DIR motion|custody|connectivity");
        const std::filesystem::path path=argv[1];
        if (!std::filesystem::create_directories(path)) throw std::invalid_argument("output already exists");
        Output out(path);
        const std::string_view mode=argv[2];
        if (mode=="motion") care_motion_matrix(out);
        else if (mode=="custody") { spatial_custody(out); held_wall(out); }
        else if (mode=="connectivity") {
            for (const auto cell:{.001,.010}) {
                connection(out,cell,4,false,false);
                connection(out,cell,4,true,false);
                connection(out,cell,3,false,false);
            }
            connection(out,.010,4,false,true);
        } else throw std::invalid_argument("unknown R1 probe mode");
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
