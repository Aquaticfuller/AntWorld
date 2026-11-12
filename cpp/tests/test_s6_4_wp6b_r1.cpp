#include "wp6b_fixture.hpp"
#include "founding_internal.hpp"
#include "event_block.hpp"
#include "antworld/storage/store.hpp"
#include <algorithm>
#include <iostream>
#include <set>

namespace {
using namespace antworld;
using namespace antworld::detail;
using namespace antworld::storage;
using namespace antworld::wp6b;

template<class F> void rejects(F operation) {
    try { operation(); }
    catch (const std::exception&) { return; }
    throw std::runtime_error("expected F1-R1 rejection");
}

Case probe(bool multi=false) {
    auto f=nominal();
    f.first_lay={day_ms}; f.opening_width={multi?3*hour_ms:1}; f.opening_spacing={multi?hour_ms:1};
    f.later_spacing={80*day_ms};
    for (auto& stage : f.brood) stage.duration={day_ms};
    f.feeding_persistence=FoundingFeedingPersistence{{2*day_ms},750'000};
    return {1,1,"r1-probe",true,0,{},f};
}

std::vector<WorldEvent> kind(const WorldRuntime& w, FactKind fact) {
    auto events=w.committed_events();
    std::erase_if(events,[&](const auto& e) { return e.kind!=fact; });
    return events;
}

std::vector<WorldEvent> annotations(const WorldRuntime& w, FoundingCareWake mark) {
    auto events=kind(w,FactKind::CareTick);
    std::erase_if(events,[&](const auto& e) { return e.random_value!=static_cast<unsigned>(mark); });
    return events;
}

// Advance to the first boundary at which the predicate observes an actual event.
template<class Predicate> void until(WorldRuntime& w, SimTime limit, Predicate done) {
    while (!done()) {
        const auto pending=w.pending_events();
        require(!pending.empty() && pending.front().key.time<=limit,"missing declared F1-R1 probe boundary");
        w.advance_to(pending.front().key.time);
    }
}

WorldEvent end_of_started_feed(WorldRuntime& w, EntityId queen, SimTime limit) {
    const auto before=w.summary().committed_events;
    std::optional<WorldEvent> started;
    until(w,limit,[&] {
        for (const auto& e : w.events_after({before},4096))
            if (e.actor==queen && e.kind==FactKind::BiologicalObservation &&
                e.observation.phase==ObservationPhase::Started && e.observation.act==CareAct::FeedBrood) started=e;
        return started.has_value();
    });
    return *started;
}

SimTime feed_end(const WorldRuntime& w, EntityId queen) {
    for (const auto& e : w.pending_events())
        if (e.actor==queen && e.kind==ScheduledEvent::Kind::CareEnd) return e.key.time;
    throw std::runtime_error("missing pending maternal feed end");
}

void repeat_and_distribution() {
    for (const bool multi : {false,true}) {
        const auto c=probe(multi);
        auto scene=setup(c); auto& w=scene.world;
        w.advance_to({18*day_ms});
        const auto births=kind(w,FactKind::AntBorn);
        require(births.size()==(multi?3U:1U),"local care test has unpaid or missing sibling");
        const auto repeats=annotations(w,FoundingCareWake::Repeat);
        require(!repeats.empty(),"no committed repeat choice");
        const auto all=w.committed_events();
        for (const auto& repeat : repeats) {
            const auto latest=std::find_if(all.rbegin(),all.rend(),[&](const auto& e) {
                return e.id<repeat.id && e.kind==FactKind::FoundingRation;
            });
            require(latest!=all.rend() && latest->actor==scene.queen.id &&
                    repeat.time.milliseconds-latest->time.milliseconds<c.profile.feeding_persistence->window.milliseconds,
                    "repeat lacks a recent paid recipient");
            const auto selection=std::find_if(all.begin(),all.end(),[&](const auto& e) {
                return e.kind==FactKind::BiologicalObservation && e.source==repeat.source && e.observation.phase==ObservationPhase::Selected;
            });
            require(selection!=all.end() && selection->observation.target.value==latest->payload &&
                    selection->observation.act==CareAct::FeedBrood,"repeat did not select real local feeding");
        }
        const auto meals=kind(w,FactKind::FoundingRation);
        const auto clipped=std::any_of(meals.begin(),meals.end(),[&](const auto& e) {
            return e.transferred.protein_ug && e.transferred.protein_ug<c.profile.ration_protein_ug;
        });
        require(clipped,"technical colony did not exercise a demand-clipped paid ration");
        if (multi) {
            std::set<std::uint64_t> recipients;
            for (const auto& e : meals) if (e.transferred.protein_ug) recipients.insert(e.payload);
            require(recipients.size()>1,"memory monopolized all maternal protein in the sibling probe");
        } else {
            const auto child=AntRef{births.front().world,births.front().actor};
            const auto stages=kind(w,FactKind::StageChanged);
            require(stages.size()==3 && stages.back().actor==child.id && stages.back().stage==LifeStage::Adult &&
                    w.query_autonomy(child)->decisions,"paid juvenile did not become an autonomous worker");
        }
        check_ledgers(w); w.restore(w.checkpoint());
    }
}

void expiry_and_unavailable() {
    auto c=probe(); c.profile.feeding_persistence->window={1};
    auto expiry=setup(c); auto& w=expiry.world;
    const auto start=end_of_started_feed(w,expiry.queen.id,{9*day_ms});
    const auto due=feed_end(w,expiry.queen.id);
    w.advance_to(due);
    require(kind(w,FactKind::FoundingRation).size()==1 && annotations(w,FoundingCareWake::Expired).empty(),"expired at meal time");
    w.restore(w.checkpoint()); w.advance_to({due.milliseconds+1});
    require(annotations(w,FoundingCareWake::Expired).size()==1 && annotations(w,FoundingCareWake::Repeat).empty(),"memory survived exact expiry");
    require(start.time<due,"missing timed handling interval");

    c=probe(); c.profile.protein_ug=c.profile.egg_protein_ug+c.profile.ration_protein_ug;
    auto scarce=setup(c); auto& sw=scarce.world;
    sw.advance_to({9*day_ms});
    const auto meals=kind(sw,FactKind::FoundingRation);
    require(!meals.empty() && meals.front().transferred.protein_ug==c.profile.ration_protein_ug &&
            sw.query_founding(scarce.queen)->mobile_protein_ug==0,"scarcity fixture did not exhaust available maternal protein");
    require(annotations(sw,FoundingCareWake::Repeat).empty() && !annotations(sw,FoundingCareWake::Unavailable).empty(),
            "unpayable protein deficit retained a repeat advantage");
    check_ledgers(sw); sw.restore(sw.checkpoint());
}

void blocked_funded_recipient() {
    auto c=probe(); c.profile.first_lay={6*hour_ms+253};
    WorldConfig config; config.continuous_spatial_motion=true;
    WorldRuntime w({646,52},1,config,s6_3_1_fixture::limits());
    w.configure_long_term(); w.configure_social(closure::day_social());
    auto care=closure::timed_care(true); care.worker_contact_probability=0; care.care_probability=1; care.step_m=.0015;
    w.configure_biology(care);
    GeometryConfig g; g.origin_m={-.006,-.006,-.006}; g.quantum_m=.00025; g.initial_solid={{0,0,0},{48,48,48}}; g.reach_q=12;
    const std::array<BoxQ,1> room{{{{4,18,18},{44,30,30}}}};
    const BoxQ mine{{20,23,30},{22,25,34}}, plug{{27,22,22},{28,26,26}};
    w.configure_geometry(g,room);
    const auto colony=w.seed_colony();
    const auto queen=w.seed_ant(colony,{{},LifeStage::Adult,Caste::Queen});
    w.enable_founding(queen,c.profile);
    const auto decoy=w.seed_ant(colony,{{.004,0,0},LifeStage::Pupa});
    const auto mason=w.seed_ant(colony,{{-.00075,0,.0005},LifeStage::Adult,Caste::Worker,4000});
    w.submit_soil({mason,{100},SoilAction::Excavate,mine,{},0});
    w.set_autonomy(queen);
    w.advance_to(c.profile.first_lay);
    require(w.soil_parcels().size()==1,"wall fixture failed to excavate paid material");
    const auto born=kind(w,FactKind::AntBorn);
    require(born.size()==1 && born.front().position.x==.0015,"maternal approach did not place the funded egg off the shelter");
    const auto birth=born.front();
    const AntRef larva{colony.world,birth.actor};
    require(w.query_ant(larva)->stage==LifeStage::Egg && w.query_physiology(larva)->mother==queen.id,
            "wall fixture target was not born with a paid lineage");
    w.schedule_lifecycle(decoy,{c.profile.first_lay.milliseconds+1},LifeStage::Dead);
    until(w,{day_ms},[&] { return w.query_ant(queen)->position==PositionM{}; });
    const auto target=w.query_ant(larva)->position;
    require(w.spatially_clear({},target),"the funded egg was unreachable before the edit");
    const auto cut=w.checkpoint();
    const auto close=SimTime{w.summary().now.milliseconds+g.work_duration.milliseconds};
    w.submit_soil({mason,close,SoilAction::Fill,plug,{colony.world,w.soil_parcels().front().id},1});
    w.advance_to(close);
    require(!w.spatially_clear({},target) && w.geometry_snapshot().ledger.filled_q3==16,"soil was not physically occluding the larva");
    w.advance_to({6*day_ms});
    require(kind(w,FactKind::FoundingRation).empty(),"occluded funded larva received a ration");
    for (const auto& e : kind(w,FactKind::BiologicalObservation))
        require(e.time<close || e.actor!=queen.id || e.observation.target!=larva.id,"wall leaked larval care contact");
    check_ledgers(w); w.restore(w.checkpoint());
    w.restore(cut); w.advance_to({6*day_ms});
    require(!kind(w,FactKind::FoundingRation).empty(),"open control did not pay a local larva");
    check_ledgers(w);
}

void competition_and_interruption() {
    for (const bool kill : {false,true}) {
        auto c=probe(); auto scene=setup(c); auto& w=scene.world;
        const auto world=w.summary().world;
        const auto worker=w.seed_ant({world,w.colonies().front().id},{});
        w.enable_physiology(worker,{{0,70,0,0},1500000000,1600,0},c.profile.worker);
        (void)end_of_started_feed(w,scene.queen.id,{8*day_ms});
        w.advance_to(feed_end(w,scene.queen.id));
        const auto repeat=end_of_started_feed(w,scene.queen.id,{10*day_ms});
        const AntRef larva{world,repeat.observation.target};
        const auto due=feed_end(w,scene.queen.id);
        const auto before=kind(w,FactKind::FoundingRation).size();
        if (kill) w.schedule_lifecycle(larva,due,LifeStage::Dead);
        const auto action=w.submit_nutrition({worker,due,NutritionAction::Trophallaxis,larva,70});
        w.advance_to(due);
        if (kill) {
            require(w.query_ant(larva)->stage==LifeStage::Dead && kind(w,FactKind::FoundingRation).size()==before,
                    "same-tick death did not cancel maternal payment");
            const auto rejected=kind(w,FactKind::ActionRejected);
            require(std::any_of(rejected.begin(),rejected.end(),[&](const auto& e) { return e.source==action && e.outcome==Outcome::DeadActor; }),
                    "worker transferred to dead larva");
            const auto observations=kind(w,FactKind::BiologicalObservation);
            require(std::any_of(observations.begin(),observations.end(),[&](const auto& e) {
                return e.actor==scene.queen.id && e.observation.phase==ObservationPhase::Interrupted && e.observation.target==larva.id;
            }),"death failed to record the interrupted maternal bout");
        } else {
            const auto p=*w.query_physiology(larva);
            require(p.tissue_protein_ug+p.crop.protein_ug==c.profile.larval_tissue_ug,
                    "same-time paid donors did not respect the actual protein deficit");
        }
        check_ledgers(w); w.restore(w.checkpoint());
    }
}

void restore_and_fault(const std::filesystem::path& folder) {
    const auto c=probe(); auto scene=setup(c); auto& w=scene.world;
    (void)end_of_started_feed(w,scene.queen.id,{8*day_ms});
    w.advance_to(feed_end(w,scene.queen.id));
    (void)end_of_started_feed(w,scene.queen.id,{10*day_ms});
    const auto cut=w.checkpoint();
    const auto boundary=feed_end(w,scene.queen.id);
    const auto id=w.summary().world;
    const auto limits=s6_3_1_fixture::limits();
    storage::Store store(folder/"fault.sqlite",limits,StoreFormat::Segmented);
    const auto token=store.save(w);
    auto resumed=store.load(id).world;
    require(resumed.checkpoint()==cut,"resuming active repeated care altered checkpoint or witness");
    w.advance_to(boundary);
    resumed.advance_to({boundary.milliseconds-1}); resumed.advance_to(boundary);
    require(w.checkpoint()==resumed.checkpoint(),"partitioned repeated payment changed world or fact bytes");

    auto bounded=limits;
    bounded.committed_events=static_cast<std::size_t>(kind(w,FactKind::FoundingRation).back().id.value);
    WorldRuntime failing(id,1,{},bounded); failing.restore(cut);
    rejects([&] { failing.advance_to(boundary); });
    require(failing.checkpoint()==cut,"failed meal did not roll back stock, memory, queue and facts");

    SaveOptions injected;
    injected.fault_hook=[](SaveStage stage) { if (stage==SaveStage::AfterManifest) throw std::runtime_error("injected publication failure"); };
    rejects([&] { (void)store.save(w,token,injected); });
    require(store.load(id).world.checkpoint()==cut,"failed publication replaced live meal cut");
    const auto next=store.save(w,token);
    require(next==store.save(w,token) && store.recover(id,token.generation,next.generation).world.checkpoint()==w.checkpoint(),
            "segmented retry or historical recovery changed the repeated ration");
}

void format_and_zero() {
    auto c=probe(); c.profile.feeding_persistence->repeat_ppm=0;
    auto zero=setup(c);
    c.profile.feeding_persistence.reset(); auto v1=setup(c);
    for (auto* world : {&zero.world,&v1.world}) world->advance_to({12*day_ms});
    auto a=zero.world.committed_events(), b=v1.world.committed_events();
    std::erase_if(a,[](const auto& e) { return e.kind==FactKind::FoundingConfigured; });
    std::erase_if(b,[](const auto& e) { return e.kind==FactKind::FoundingConfigured; });
    require(a==b && zero.world.summary().rng_state==v1.world.summary().rng_state,"zero repeat changed ordinary choices or RNG");
    const auto good=zero.world.checkpoint();
    require(good[6]=='G' && v1.world.checkpoint()[6]=='F',"model versions share a checkpoint marker");
    const auto journal=zero.world.committed_events();
    auto page=std::span{journal}.first(std::min(journal.size(),storage::detail::block_records));
    const auto sealed=storage::detail::seal_block(page,{},storage::detail::FactSchema::FoundingPersistence);
    require(storage::detail::inspect_block(sealed.bytes).fact_schema==3,"missing versioned fact block");
    rejects([&] { (void)storage::detail::seal_block(page,{},true); });
    auto damaged=good;
    damaged[damaged.size()-32]=1; // Forged witness, with a valid outer checksum.
    auto checksum=hash_bytes(std::span{damaged}.first(damaged.size()-8));
    for (auto i=damaged.size()-8; i<damaged.size(); ++i) { damaged[i]=static_cast<std::uint8_t>(checksum); checksum>>=8; }
    rejects([&] { zero.world.restore(damaged); });
    require(zero.world.checkpoint()==good,"witness corruption changed the running world");
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc==3,"F1-R1 probe requires mode and output directory");
        const std::string_view mode=argv[1];
        if (mode=="R1_REPEAT_DISTRIBUTION") repeat_and_distribution();
        else if (mode=="R1_EXPIRY_UNAVAILABLE") expiry_and_unavailable();
        else if (mode=="R1_FUNDED_WALL") blocked_funded_recipient();
        else if (mode=="R1_COMPETITION_INTERRUPT") competition_and_interruption();
        else if (mode=="R1_RESTORE_FAULT") restore_and_fault(argv[2]);
        else if (mode=="R1_FORMAT_ZERO") format_and_zero();
        else throw std::invalid_argument("unknown F1-R1 probe");
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
