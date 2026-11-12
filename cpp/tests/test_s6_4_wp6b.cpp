#include "wp6b_fixture.hpp"
#include "founding_internal.hpp"
#include "event_block.hpp"
#include "antworld/storage/store.hpp"
#include <filesystem>
#include <iostream>
#include <set>

namespace {
using namespace antworld;
using namespace antworld::wp6b;
using namespace antworld::detail;
using namespace antworld::storage;

template<class F> void rejects(F operation) {
    try { operation(); }
    catch (const std::exception&) { return; }
    throw std::runtime_error("expected F1 rejection");
}

Case probe(bool care=false) { return {1, 1, "probe", care, 0, {}, nominal()}; }

std::vector<WorldEvent> facts(const WorldRuntime& w, FactKind kind) {
    auto rows=w.committed_events();
    std::erase_if(rows,[&](const auto& row) { return row.kind!=kind; });
    return rows;
}

AntRef first_child(const WorldRuntime& w) {
    const auto born=facts(w,FactKind::AntBorn);
    require(!born.empty(), "missing funded birth");
    return {born.front().world,born.front().actor};
}

FoundingProfile single() {
    auto f=nominal();
    f.first_lay={day_ms}; f.opening_width={1}; f.opening_spacing={1}; f.later_spacing={80*day_ms};
    f.brood[0].duration={day_ms}; f.brood[1].duration={day_ms}; f.brood[2].duration={day_ms};
    return f;
}

void legacy_bytes() {
    // The FNV checkpoint digests are the final eight bytes of the accepted WP-5 archives.
    for (const bool on : {true,false}) {
        auto scene=wp5::setup({"founding",on?"on":"off",0,1});
        auto& w=scene.world;
        require(!w.founding_profile() && w.snapshot().state_hash==(on?UINT64_C(4577247255598341539):UINT64_C(101520426321668530)),"legacy input bytes changed");
        for (Time day=1; day<=21; ++day) w.advance_to({day*day_ms});
        require(w.snapshot().state_hash==(on?UINT64_C(9941221514177197401):UINT64_C(109129312142453323)),"legacy outcome bytes changed");
        WorldRuntime restored({646,2},1,{},s6_3_1_fixture::limits());
        const auto bytes=w.checkpoint();
        restored.restore(bytes);
        require(restored.checkpoint()==bytes && restored.committed_events()==w.committed_events(),"legacy replay changed");
    }
}

void config() {
    const auto expect_rejection=[](FoundingProfile f) {
        WorldRuntime w({646,2},1);
        w.configure_long_term(); w.configure_social(); w.configure_biology(closure::timed_care(true));
        const auto q=w.seed_ant(w.seed_colony(),{{},LifeStage::Adult,Caste::Queen});
        const auto before=w.checkpoint();
        rejects([&] { w.enable_founding(q,f); });
        require(w.checkpoint()==before && !w.founding_profile(),"invalid enrollment changed state");
        w.enable_founding(q,nominal());
        check_ledgers(w);
    };
    auto f=nominal(); f.wet_mass_ug=1000; expect_rejection(f);
    f=nominal(); f.lipid_yield_nj_per_ug=UINT64_MAX; expect_rejection(f);
    f=nominal(); f.population=static_cast<FoundingPopulation>(3); expect_rejection(f);
    f=nominal(); f.brood[1].basal_nj_per_day=1; expect_rejection(f);
    f=nominal(); f.egg_water_ug=2001; expect_rejection(f);
}

void conversion() {
    auto s=setup(probe());
    auto& w=s.world;
    for (const Time t : {Time{0},hour_ms/7,6*hour_ms,7*hour_ms,11*hour_ms,2*day_ms}) {
        w.advance_to({t}); check_ledgers(w);
        const auto b=w.founding_budget();
        std::uint64_t converted=0;
        for (const auto& e : facts(w,FactKind::FoundingLipidConverted)) {
            require(e.random_value==e.payload*nominal().lipid_yield_nj_per_ug,"conversion without backing stock");
            converted+=e.payload;
        }
        require(converted==b.spent_lipid_ug,"conversion evidence differs from spent mass");
    }
    auto p=*w.query_physiology(s.queen); auto r=*w.query_founding(s.queen);
    p.body_energy_nj=p.config.energy_capacity_nj;
    const auto old=r;
    require(!convert_founding_lipid(nominal(),p,r,LifeStage::Adult,true) && old==r,"full buffer consumed lipid");
    auto a=p,b=p; auto x=r,y=r;
    settle_founding(nominal(),a,x,LifeStage::Adult,true,{2*day_ms+3});
    settle_founding(nominal(),a,x,LifeStage::Adult,true,{2*day_ms+37});
    settle_founding(nominal(),b,y,LifeStage::Adult,true,{2*day_ms+37});
    require(a==b && x==y,"fractional carries depend on partition");
}

void birth() {
    auto s=setup(probe()); auto& w=s.world;
    const auto when=nominal().first_lay;
    w.advance_to({when.milliseconds-1});
    const auto bytes=w.checkpoint(); const auto before=w.snapshot();
    for (const bool entity_failure : {true,false}) {
        auto limits=s6_3_1_fixture::limits();
        if (entity_failure) limits.entities=2;
        else limits.committed_events=static_cast<std::size_t>(before.committed_events+5);
        WorldRuntime limited({646,2},1,{},limits); limited.restore(bytes);
        rejects([&] { limited.advance_to(when); });
        require(limited.checkpoint()==bytes && limited.snapshot()==before,"birth failure did not roll back allocator, stock, queue and facts");
    }
    w.advance_to(when); check_ledgers(w);
    const auto child=first_child(w); const auto f=nominal();
    const auto p=*w.query_physiology(child);
    const auto reserve=*w.query_founding(child);
    require(p.mother==s.queen.id && p.hydration_ug==f.egg_water_ug && p.tissue_protein_ug==f.egg_protein_ug &&
        reserve.lipid_ug+reserve.spent_lipid_ug==f.egg_lipid_ug && facts(w,FactKind::FoundingEggFunded).size()==1,"partial egg funding");
    auto c=probe(); c.profile.water_ug=600+65+4*60; // Exact maintenance floor after packet.
    auto refused=setup(c); refused.world.advance_to(when);
    require(facts(refused.world,FactKind::AntBorn).empty() && facts(refused.world,FactKind::ReproductionAttempt).size()==1,"exact maternal floor admitted a debit");
    check_ledgers(refused.world);
}

void opening() {
    auto c=probe(); c.profile.protein_ug=2*c.profile.egg_protein_ug;
    auto s=setup(c); auto& w=s.world;
    const auto begin=c.profile.first_lay.milliseconds;
    const auto after_bout=begin+day_ms+2*day_ms;
    w.advance_to({begin-1}); require(facts(w,FactKind::ReproductionAttempt).empty(),"early lay");
    w.advance_to({after_bout-1});
    auto attempts=facts(w,FactKind::ReproductionAttempt);
    require(attempts.size()==12 && attempts.back().time.milliseconds==begin+22*hour_ms && facts(w,FactKind::AntBorn).size()==2,"opening bout or finite funds wrong");
    const auto mid=w.checkpoint(); w.restore(mid); w.advance_to({after_bout});
    attempts=facts(w,FactKind::ReproductionAttempt);
    require(attempts.size()==13 && attempts.back().time.milliseconds==after_bout && !attempts.back().payload,"first later opportunity wrong");
}

void death_priority() {
    for (unsigned mode=0; mode<3; ++mode) {
        auto c=probe(); auto& f=c.profile;
        f.first_lay={1}; f.opening_width={1}; f.opening_spacing={1};
        f.worker.absorption_period={2000}; f.lipid_yield_nj_per_ug=10000;
        f.lay_overhead_nj=1000;
        f.maintenance_floor={1};
        f.egg_lipid_ug=mode==1?2:1; f.egg_water_ug=10;
        f.brood[0]={{10000},founding_day_ms,mode?86400U:1U};
        f.brood[1].basal_nj_per_day=founding_day_ms;
        auto s=setup(c); auto& w=s.world; w.advance_to({10000});
        const auto child=first_child(w);
        require(w.query_ant(child)->stage==LifeStage::Egg,"early development or death");
        w.advance_to({10001});
        require(w.query_ant(child)->stage==LifeStage::Dead && facts(w,FactKind::StageChanged).empty() &&
                w.query_physiology(child)->death_cause==(mode==1?DeathCause::Dehydrated:DeathCause::EnergyDepleted),"death lost its priority on a boundary");
        check_ledgers(w); w.restore(w.checkpoint());
    }
    auto c=probe(); auto& f=c.profile;
    f.worker.absorption_period={2*hour_ms}; f.lipid_ug=1; f.lipid_yield_nj_per_ug=static_cast<std::uint64_t>(hour_ms);
    f.basal_nj_per_day=founding_day_ms; f.active_nj_per_ms=0; f.first_lay={hour_ms};
    auto s=setup(c); s.world.advance_to(f.first_lay);
    require(s.world.query_ant(s.queen)->stage==LifeStage::Dead && facts(s.world,FactKind::ReproductionAttempt).empty(),"dead foundress attempted lay");
}

void larval_cap() {
    auto c=probe(); c.profile=single();
    auto s=setup(c); auto& w=s.world;
    w.advance_to({3*day_ms}); const auto child=first_child(w);
    require(w.query_ant(child)->stage==LifeStage::Larva && w.query_physiology(child)->stage_progress==c.profile.brood[1].duration,"larval protein did not gate exact time cap");
    auto bytes=w.checkpoint(); w.restore(bytes);
    w.set_autonomy(s.queen);
    w.advance_to({15*day_ms});
    require(!facts(w,FactKind::FoundingRation).empty(),"cap case did not receive actual post-cap feeding");
    const auto transitions=facts(w,FactKind::StageChanged);
    require(std::any_of(transitions.begin(),transitions.end(),[&](const auto& event) {
        return event.actor==child.id && event.stage==LifeStage::Pupa && event.time.milliseconds>3*day_ms;
    }),"real local uptake did not release capped development");
    const auto p=*w.query_physiology(child);
    require(p.tissue_protein_ug==c.profile.larval_tissue_ug,"transition lacked tissue accumulation");
    check_ledgers(w);
}

void pupal_margin() {
    const auto f=single(); auto p=initial_founding_physiology(f,false,{}); FoundingReserve r;
    p.stage_progress=f.brood[1].duration; p.tissue_protein_ug=f.larval_tissue_ug;
    p.hydration_ug=f.brood[2].water_ug_per_day;
    p.body_energy_nj=f.brood[2].basal_nj_per_day;
    require(!founding_develops(f,p,r,LifeStage::Larva),"pupal margin accepted exact energy and water tie");
    ++p.hydration_ug;
    require(!founding_develops(f,p,r,LifeStage::Larva),"pupal margin accepted exact energy tie");
    ++p.body_energy_nj;
    require(founding_develops(f,p,r,LifeStage::Larva),"positive pupal margin was rejected");
    settle_founding(f,p,r,LifeStage::Pupa,false,{day_ms});
    require(p.body_energy_nj==1 && p.hydration_ug==1,"closed-stage cost or strict residue differs");
}

void local_feed() {
    auto c=probe(true); c.profile=single();
    auto s=setup(c); auto& w=s.world;
    w.advance_to({6*day_ms});
    const auto meals=facts(w,FactKind::FoundingRation);
    require(!meals.empty(),"no realized local maternal ration in technical fixture");
    const auto child=first_child(w);
    const auto all=w.committed_events();
    for (const auto& e : meals) {
        require(e.actor==s.queen.id && e.payload==child.id.value && e.random_value<=c.profile.ration_lipid_ug,"wrong ration parties or capacity");
        const auto& end=all.at(static_cast<std::size_t>(e.id.value));
        require(end.source==e.source && end.observation.phase==ObservationPhase::Completed && end.observation.act==CareAct::FeedBrood &&
                end.transferred==e.transferred,"ration was not a completed real contact act");
    }
    check_ledgers(w); w.restore(w.checkpoint());
    auto p=initial_founding_physiology(c.profile,true,{}), q=initial_founding_physiology(c.profile,false,{});
    FoundingReserve maternal{c.profile.lipid_ug,0,c.profile.protein_ug}, larva{c.profile.larval_lipid_capacity_ug};
    p.body_energy_nj=1000000000; q.body_energy_nj=100000000;
    q.crop.protein_ug=q.config.crop_capacity_ug;
    require(founding_ration(c.profile,p,maternal,q,larva)==FoundingRation{},"full recipient received stock");
    q.crop={}; q.body_energy_nj=0;
    require(founding_ration(c.profile,p,maternal,q,larva)==FoundingRation{},"dead recipient received stock");
    q.body_energy_nj=1; p.hydration_ug=0;
    require(founding_ration(c.profile,p,maternal,q,larva)==FoundingRation{},"exhausted donor spent stock");
    c.arm="contact-blocked";
    auto wall=setup(c);
    const auto ants=wall.world.ant_states();
    require(ants.size()==3 && wall.world.spatially_clear({},ants[1].position) && !wall.world.spatially_clear({},ants[2].position),"wrong wall probe geometry");
    wall.world.advance_to({day_ms-1});
    bool reachable_seen=false;
    for (const auto& e : facts(wall.world,FactKind::BiologicalObservation)) if (e.observation.phase==ObservationPhase::Opportunity) {
        require(e.observation.target!=ants[2].id,"occluded larva became a care opportunity");
        reachable_seen |= e.observation.target==ants[1].id;
    }
    require(reachable_seen,"wall test missed the reachable larva");

    c.care=false; c.arm="probe";
    auto two=setup(c); auto& competing=two.world;
    const auto world=competing.summary().world;
    const ColonyRef colony{world,competing.colonies().front().id};
    const auto a=competing.seed_ant(colony,{}), b=competing.seed_ant(colony,{});
    for (const auto donor : {a,b}) competing.enable_physiology(donor,{{0,40,0,0},1500000000,1600,0},c.profile.worker);
    competing.advance_to({2*day_ms});
    const auto target=first_child(competing);
    const SimTime shared{2*day_ms+1}, death{2*day_ms+2};
    competing.submit_nutrition({a,shared,NutritionAction::Trophallaxis,target,40});
    competing.submit_nutrition({b,shared,NutritionAction::Trophallaxis,target,40});
    competing.advance_to(shared);
    const auto transfers=facts(competing,FactKind::NutritionTransferred);
    require(transfers.size()==2 && transfers[0].transferred.protein_ug==40 && transfers[1].transferred.protein_ug==25 &&
            competing.query_physiology(target)->crop.protein_ug==65,"same-time gifts exceeded actual receiver demand");
    const auto retained=competing.query_physiology(b)->crop;
    competing.schedule_lifecycle(target,death,LifeStage::Dead);
    const auto late=competing.submit_nutrition({b,death,NutritionAction::Trophallaxis,target,15});
    competing.advance_to(death);
    const auto failures=facts(competing,FactKind::ActionRejected);
    require(std::any_of(failures.begin(),failures.end(),[&](const auto& e) { return e.source==late && e.outcome==Outcome::DeadActor; }) &&
            competing.query_physiology(b)->crop==retained,"dead receiver took a same-time gift");
    check_ledgers(competing); competing.restore(competing.checkpoint());
}

void follow_up() {
    auto c=probe(true); c.profile=single();
    auto s=setup(c); auto& w=s.world; w.advance_to({12*day_ms});
    const auto child=first_child(w);
    auto transitions=facts(w,FactKind::StageChanged);
    require(transitions.size()==3 && transitions.back().actor==child.id && transitions.back().stage==LifeStage::Adult,
        "stage chain lost individual identity or never emerged");
    require(w.query_autonomy(child)->decisions>0,"emerged worker never used ordinary autonomy");
    require(w.query_physiology(child)->config.basal_nj_per_ms==c.profile.worker.basal_nj_per_ms,"worker inherited queen cost");
    w.restore(w.checkpoint()); check_ledgers(w);
}

void exact_restore(const std::filesystem::path& folder) {
    auto c=probe(true); c.profile=single();
    auto s=setup(c); auto& w=s.world; const auto id=w.summary().world;
    const auto limits=s6_3_1_fixture::limits();
    storage::Store store(folder/"exact.sqlite",limits,StoreFormat::Segmented);
    std::optional<SaveToken> token;
    WorldRuntime split({646,2},1,{},limits); split.restore(w.checkpoint());
    for (const Time at : {day_ms-1, day_ms+13, 2*day_ms+381, 3*day_ms+783, 12*day_ms}) {
        w.advance_to({at}); check_ledgers(w);
        const auto expected=w.checkpoint();
        split.advance_to({at-1}); split.advance_to({at});
        require(split.checkpoint()==expected,"F1 partition produced different bytes");
        const auto before=split.snapshot();
        (void)split.ant_states(); (void)split.founding_budget(); (void)split.events_after({},64);
        (void)split.query_founding(s.queen); (void)split.query_physiology(s.queen); (void)split.checkpoint_frame();
        require(split.snapshot()==before && split.checkpoint()==expected,"observer changed state, queue or history");
        token=store.save(w,token);
        auto loaded=store.load(id);
        require(loaded.token==token && loaded.world.checkpoint()==expected && loaded.world.committed_events()==w.committed_events(),"segmented recovery changed F1 facts");
        split=std::move(loaded.world);
    }
    const auto child=first_child(w);
    HistoryFilter filter; filter.world=id; filter.individual=child.id; filter.kind=FactKind::FoundingRation;
    const auto rows=store.history(filter);
    require(!rows.empty() && rows.front().related==child.id,"F1 recipient is absent from segmented history");
}

void corrupt(const std::filesystem::path& folder) {
    auto s=setup(probe()); auto& w=s.world;
    const auto good=w.checkpoint();
    auto damaged=good; damaged[8]=16;
    auto checksum=hash_bytes(std::span{damaged}.first(damaged.size()-8));
    for (std::size_t i=0;i<8;++i) { damaged[damaged.size()-8+i]=static_cast<std::uint8_t>(checksum); checksum>>=8; }
    rejects([&] { w.restore(damaged); });
    require(w.checkpoint()==good,"unsupported save altered running state");
    const auto facts=w.committed_events();
    rejects([&] { (void)storage::detail::seal_block(facts,{}); });
    auto block=storage::detail::seal_block(facts,{},true);
    require(storage::detail::inspect_block(block.bytes).fact_schema==2,"F1 used a legacy block");
    block.bytes[12]=4;
    rejects([&] { (void)storage::detail::inspect_block(block.bytes); });
    auto typed=::facts(w,FactKind::FoundingReserveSeeded).front(); typed.transferred.carbs_ug=1;
    rejects([&] { (void)decode_event(encode_event(typed)); });
    storage::Store legacy(folder/"legacy.sqlite",{},StoreFormat::Legacy);
    rejects([&] { (void)legacy.save(w); });
    storage::Store store(folder/"fault.sqlite",s6_3_1_fixture::limits(),StoreFormat::Segmented);
    const auto token=store.save(w);
    w.advance_to({5*day_ms});
    SaveOptions failure;
    failure.fault_hook=[](SaveStage stage) { if (stage==SaveStage::AfterManifest) throw std::runtime_error("injected F1 publication failure"); };
    rejects([&] { (void)store.save(w,token,failure); });
    require(store.load(token.world).world.checkpoint()==good,"failed F1 publication replaced predecessor");
    require(store.save(w,token)==store.save(w,token),"retry did not preserve F1 publication identity");
}

void bounded() {
    auto s=setup(probe(true)); auto& w=s.world;
    for (Time d=0; d<=30; ++d) {
        w.advance_to({d*day_ms}); check_ledgers(w);
        require(w.founding_budget().enrolled<=w.summary().ant_count && w.summary().pending_events<=3*w.summary().ant_count+5,
                "unbounded F1 state or queue");
    }
    std::set<std::pair<EntityId,SimTime>> conversions;
    for (const auto& f : facts(w,FactKind::FoundingLipidConverted))
        require(conversions.emplace(f.actor,f.time).second,"duplicate same-tick refill");
    require(sizeof(FoundingReserve)==5*sizeof(std::uint64_t) && w.checkpoint_frame().size()<w.checkpoint().size(),"unexpected F1 record or frame growth");
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc==3,"F1 test requires mode and output path");
        const std::string_view mode=argv[1];
        const std::filesystem::path folder=argv[2];
        std::filesystem::create_directories(folder);
        if (mode=="LEGACY_BYTES") legacy_bytes();
        else if (mode=="CONFIG_MASS_OVERFLOW") config();
        else if (mode=="CONVERSION") conversion();
        else if (mode=="BIRTH_COMMIT") birth();
        else if (mode=="OPENING_BOUT") opening();
        else if (mode=="DEATH_PRIORITY") death_priority();
        else if (mode=="LARVA_CAP") larval_cap();
        else if (mode=="PUPAL_MARGIN") pupal_margin();
        else if (mode=="LOCAL_FEED") local_feed();
        else if (mode=="FOLLOW_UP") follow_up();
        else if (mode=="EXACT_RESTORE") exact_restore(folder);
        else if (mode=="CORRUPT_OR_UNSUPPORTED") corrupt(folder);
        else if (mode=="BOUNDED_COST") bounded();
        else throw std::invalid_argument("unknown F1 test mode");
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
