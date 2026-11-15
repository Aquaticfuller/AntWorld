#include "r0r1_fixture.hpp"
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
} // namespace

int main(int argc,char** argv) try {
    require(argc==2,"expected isolated R0-r1 test directory");
    const std::filesystem::path root=argv[1];
    std::filesystem::create_directories(root);
    motor_restore(root/"motion.sqlite");
    motor_negatives();
    morphology();
    return 0;
} catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
}
