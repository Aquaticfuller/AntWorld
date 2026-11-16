#include "r0r1_fixture.hpp"
#include "traffic_observer_fixture.hpp"
#include "nest_scoring.hpp"
#include "worker_motion.hpp"
#include "antworld/storage/store.hpp"
#include <iostream>
#include <set>

namespace {
using namespace antworld;
using namespace antworld::detail;
using wp4::require;

WorldRuntime crowd(bool blocked,RuntimeLimits limits={}) {
    WorldConfig config;
    config.continuous_spatial_motion=true;
    WorldRuntime world({333,1},7,config,limits);
    EcologicalClosureConfig profile;
    profile.distance_clock=profile.floor_space=profile.activity_cost=true;
    profile.portable_field=profile.brood_space=profile.portable_care_motion=profile.local_nest_activity=true;
    profile.nest_dynamics=NestDynamics{true};
    world.configure_ecological_closure(profile);
    world.configure_long_term();
    GeometryConfig geometry;
    geometry.origin_m={};
    geometry.initial_solid={{-30,-18,-30},{30,0,30}};
    const int width=blocked?1:8;
    const std::array<BoxQ,1> hollow{{{{-width,-10,-width},{width,-4,width}}}};
    world.configure_geometry(geometry,hollow);
    auto settings=closure::day_social();
    settings.decision_interval={1000};
    settings.minimum_program_time={2000};
    settings.rest_weight=1'000'000;
    settings.exchange_enabled=false;
    world.configure_social(settings);
    world.configure_biology(closure::timed_care(true));
    const PositionM depot{0,-.004,0};
    const auto group=world.seed_colony(depot);
    for (int i=0;i<4;++i) {
        const auto worker=world.seed_ant(group,{depot,LifeStage::Adult,Caste::Worker,4000});
        world.enable_physiology(worker,closure::adult,closure::day_physiology());
        world.set_autonomy(worker);
    }
    return world;
}

void motor_restore(const std::filesystem::path& path) {
    auto world=crowd(false);
    world.advance_to({1001});
    const auto world_id=world.summary().world;
    std::vector<std::pair<AntRef,WorkerMotion>> pending(0);
    std::set<std::pair<double,double>> destinations;
    for (const auto& ant:world.ant_states()) {
        const AntRef ref{world_id,ant.id};
        if (const auto step=world.query_worker_motion(ref)) {
            require(step->from==ant.position && step->ends>step->translates &&
                    step->translates>=step->begins && step->target_facing,
                    "invalid physical segment clock");
            require(destinations.emplace(step->to.x,step->to.z).second,"active motor leases share a berth");
            require(world.spatially_clear(step->from,step->to,1),"motor reservation crosses the wall");
            pending.emplace_back(ref,*step);
        }
    }
    require(pending.size()>1,"crowd did not produce actual overlapping worker displacement");
    storage::Store store(path,{},storage::StoreFormat::Segmented);
    const auto token=store.save(world);
    auto restored=store.load(world_id);
    require(restored.token==token && restored.world.checkpoint_frame()==world.checkpoint_frame(),
            "motor checkpoint frame changed on SQLite recovery");
    for (const auto& [ref,move]:pending)
        require(restored.world.query_worker_motion(ref)==move,"in-flight motor lease changed");
    restored.world.advance_to({1018});
    world.advance_to({1999});
    restored.world.advance_to({1999});
    require(restored.world.checkpoint()==world.checkpoint(),"motor advance partition changed state");
    for (const auto& [ref,move]:pending) {
        require(world.query_ant(ref)->position==move.to && world.query_autonomy(ref)->facing==move.target_facing,
                "committed rest position or bearing differs from its segment");
    }
    const auto facts=world.committed_events();
    require(std::count_if(facts.begin(),facts.end(),[](const auto& e) {
        return e.kind==FactKind::Moved && (e.random_value>>32)>0;
    })==static_cast<std::ptrdiff_t>(pending.size()),"timed motion lost its canonical segment evidence");
    wp6b::check_ledgers(world);
}

void motor_negatives() {
    auto tight=crowd(true);
    tight.advance_to({1999});
    const auto facts=tight.committed_events();
    require(std::none_of(facts.begin(),facts.end(),[](const auto& e) {return e.kind==FactKind::Moved;}),
            "worker walked into a blocked berth");
    auto fatal=crowd(false);
    fatal.advance_to({1001});
    for (const auto& ant:fatal.ant_states()) {
        const AntRef ref{fatal.summary().world,ant.id};
        const auto plan=fatal.query_worker_motion(ref);
        if (!plan) continue;
        fatal.schedule_lifecycle(ref,{1002},LifeStage::Dead);
        fatal.advance_to(plan->ends);
        require(!fatal.query_worker_motion(ref) && fatal.query_ant(ref)->position==plan->from &&
                !fatal.query_ant(ref)->alive(),"motion continued after a preempting death");
        break;
    }
    wp6b::check_ledgers(fatal);
    RuntimeLimits limits;
    limits.committed_events=28;
    auto limited=crowd(false,limits);
    const auto before=limited.checkpoint();
    bool rejected=false;
    try { limited.advance_to({1001}); } catch (const std::length_error&) { rejected=true; }
    require(rejected && limited.checkpoint()==before,"failed motor publication leaked a berth or event");
    require(turn_ms(1,5)==160 && turn_ms(8,1)==40 && turn_ms(9,10)==160,
            "turn clocks or wraparound changed");
}

void morphology() {
    for (const bool shielded:{false,true}) {
        auto scene=r0r1::digging(11,1,15,NestScoring::SpatialDemand,{},shielded);
        auto& world=scene.world;
        world.advance_to({2*3'600'000});
        const auto snapshot=world.geometry_snapshot();
        require(shielded || snapshot.ledger.excavated_q3>0,"scored worker never produced an actual cut");
        for (const auto& edit:world.geometry_edits()) {
            require(edit.actor.value && edit.parcel.value && edit.volume_q3,"unpaid or anonymous edit");
            require(std::none_of(scene.rocks.begin(),scene.rocks.end(),[&](const auto& rock) {
                return box_valid(intersection(edit.box,rock));
            }),"scored excavation passed through rock");
        }
        wp6b::check_ledgers(world);
        const auto checkpoint=world.checkpoint(); world.restore(checkpoint);
        require(world.checkpoint()==checkpoint,"scored soil history changed on replay");
    }
    const auto hex=hex_site({-9,-5,-5},4,-8);
    require(hex_site(hex_center(hex,4,-8),4,-8)==hex,"hex rounding differs at a negative boundary");
}

void adult_traffic() {
    for (const bool traffic:{false,true}) {
        WorldConfig config;
        config.continuous_spatial_motion=true;
        WorldRuntime w({648,91},17,config);
        EcologicalClosureConfig model;
        model.distance_clock=model.floor_space=model.activity_cost=true;
        model.portable_field=model.brood_space=model.portable_care_motion=model.local_nest_activity=true;
        model.nest_dynamics=NestDynamics{true};
        model.local_traffic=traffic;
        w.configure_ecological_closure(model);
        GeometryConfig ground;
        ground.origin_m={};
        ground.initial_solid={{-30,-18,-30},{30,0,30}};
        const std::array<BoxQ,1> chamber{{{{-18,-10,-18},{18,-4,18}}}};
        w.configure_geometry(ground,chamber);
        const auto colony=w.seed_colony({0,-.004,-.003});
        const auto walker=w.seed_ant(colony,{{-.004,-.004,0},LifeStage::Adult,Caste::Worker,3000});
        w.seed_ant(colony,{{0,-.004,0},LifeStage::Adult,Caste::Worker,3000});
        w.submit({walker,{1000},ActionKind::Move,{},{.004,-.004,0},0});
        w.advance_to({1000});
        const auto crossing=w.committed_events().back();
        require(traffic ? crossing.outcome==Outcome::Blocked : crossing.kind==FactKind::Moved,
                "legal endpoints did not distinguish a swept-body collision");
        if (traffic) {
            w.submit({walker,{2000},ActionKind::Move,{},{-.004,-.004,.003},0});
            w.advance_to({2000});
            w.submit({walker,{3000},ActionKind::Move,{},{.004,-.004,.003},0});
            w.advance_to({3000});
            require(w.committed_events().back().kind==FactKind::Moved,"empty parallel passage rejected");
        }
    }
}

void nursery_restore(const std::filesystem::path& database) {
    auto world=traffic_observer::nursery(92,17,true);
    const auto id=world.summary().world;
    bool observed=false;
    for (std::int64_t time=4000;time<=20000 && !observed;time+=20) {
        world.advance_to({time});
        for (const auto& ant:world.ant_states()) {
            const auto ref=AntRef{id,ant.id};
            const auto motion=world.query_worker_motion(ref);
            const auto work=world.query_care(ref);
            if (!motion || !work || work->act!=CareAct::ApproachNestmate || !work->target.value) continue;
            storage::Store store(database,{},storage::StoreFormat::Segmented);
            const auto token=store.save(world);
            auto restored=store.load(id);
            require(token==restored.token && world.checkpoint_frame()==restored.world.checkpoint_frame() &&
                    motion==restored.world.query_worker_motion(ref),"pending local contact motion did not recover");
            world.advance_to(motion->ends);
            restored.world.advance_to(motion->ends);
            require(world.checkpoint()==restored.world.checkpoint(),"local approach differs after recovery");
            observed=true;
            break;
        }
    }
    require(observed,"no purposeful local contact approach was observed");
    wp6b::check_ledgers(world);
}

void provisioned_nursery(const std::filesystem::path& database) {
    using traffic_observer::Nursery;
    const auto limits=closure::limits();
    auto resumed=traffic_observer::nursery(91,41,Nursery::Provisioned,limits);
    const auto id=resumed.summary().world;
    std::optional<WorkerMotion> yielding;
    AntRef yielding_worker;
    while (const auto time=resumed.next_scheduled_time()) {
        if (time->milliseconds>300'000 || yielding) break;
        resumed.advance_to(*time);
        for (const auto& ant:resumed.ant_states()) {
            const AntRef who{id,ant.id};
            const auto action=resumed.query_care(who);
            if (action && action->act==CareAct::YieldToCarrier && action->target.value) {
                yielding=resumed.query_worker_motion(who);
                if (yielding) { yielding_worker=who; break; }
            }
        }
    }
    require(yielding.has_value(),"the resident did not yield to a blocked carrier");
    storage::Store store(database,limits,storage::StoreFormat::Segmented);
    store.save(resumed);
    auto loaded=store.load(id);
    require(loaded.world.query_worker_motion(yielding_worker)==yielding &&
            loaded.world.checkpoint_frame()==resumed.checkpoint_frame(),"save lost the yielding segment");
    resumed.advance_to({300'000}); loaded.world.advance_to({300'000});
    require(resumed.checkpoint_frame()==loaded.world.checkpoint_frame(),"the restored delivery differs");
    bool delivered=false;
    for (const auto& event:resumed.committed_events())
        delivered=delivered || (event.kind==FactKind::FoodDelivered && event.transferred.total_ug()>0);
    require(delivered,"the carrier never reached the provisioned depot");
    wp6b::check_ledgers(loaded.world);

    auto watched=traffic_observer::nursery(91,17,Nursery::Provisioned,limits);
    watched.advance_to({2'700'000});
    const EventId cursor{watched.summary().committed_events};
    watched.advance_to({3'600'000});
    const auto late=watched.events_after(cursor,static_cast<std::size_t>(watched.summary().committed_events-cursor.value));
    require(std::any_of(late.begin(),late.end(),[](const WorldEvent& f) { return f.kind==FactKind::Moved; }),
            "the preview stopped moving after its initial nursery visits");
    wp6b::check_ledgers(watched);
}
} // namespace

int main(int argc,char** argv) try {
    require(argc==2,"expected isolated R0-r1 test directory");
    const std::filesystem::path root=argv[1];
    std::filesystem::create_directories(root);
    motor_restore(root/"motion.sqlite");
    motor_negatives();
    morphology();
    adult_traffic();
    nursery_restore(root/"nursery.sqlite");
    provisioned_nursery(root/"provisioned.sqlite");
    return 0;
} catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
}
