#include "wp6b_fixture.hpp"
#include "founding_internal.hpp"
#include "event_block.hpp"
#include "antworld/storage/store.hpp"
#include <algorithm>
#include <iostream>

namespace {
using namespace antworld;
using namespace antworld::detail;
using namespace antworld::wp6b;

template<class F> void rejects(F operation) {
    try { operation(); }
    catch (const std::exception&) { return; }
    throw std::runtime_error("expected R2 rejection");
}

std::vector<WorldEvent> facts(const WorldRuntime& w,FactKind kind) {
    auto events=w.committed_events();
    std::erase_if(events,[&](const auto& e) { return e.kind!=kind; });
    return events;
}

Case thin(bool care, bool h1, bool h2) {
    auto f=nominal();
    f.lipid_ug=5000; f.water_ug=9000; f.basal_nj_per_day=2'000'000'000;
    f.egg_lipid_ug=11; f.brood[0].basal_nj_per_day=22'000'000;
    f.feeding_persistence=FoundingFeedingPersistence{{2*day_ms},750'000};
    if (h1 || h2) f.early_access=FoundingEarlyAccess{h1,h2};
    return {37,1,"ordinary",care,0,{},f};
}

void mobilization() {
    constexpr SimTime death{5'519'972'572}, pulse{5'529'600'000};
    auto base=setup(thin(true,false,false)); auto test=setup(thin(true,true,false));
    auto& w=test.world;
    const AntRef larva{w.summary().world,{35}};
    w.advance_to({death.milliseconds-1}); base.world.advance_to({death.milliseconds-1});
    auto before=*w.query_physiology(larva); auto stock=*w.query_founding(larva);
    require(before.body_energy_nj==1 && before.hydration_ug==31 && before.crop.protein_ug==16 && stock.lipid_ug==6,
            "R2 inherited evidence does not match the archived paid larva");
    const auto cut=w.checkpoint();
    w.advance_to(death); base.world.advance_to(death);
    const auto conversions=facts(w,FactKind::FoundingLipidMobilized);
    require(conversions.size()==1 && conversions.front().actor==larva.id && conversions.front().time==death &&
            conversions.front().payload==1 && conversions.front().random_value==34'000'000 &&
            base.world.query_ant(larva)->stage==LifeStage::Dead,"real exhaustion did not debit one bounded lipid quantum");
    const auto after=*w.query_physiology(larva);
    require(after.body_energy_nj==34'000'000 && after.hydration_ug==31 && after.crop==before.crop &&
            after.tissue_protein_ug==20 && after.next_absorption==pulse && w.query_founding(larva)->lipid_ug==5,
            "emergency conversion altered protein or water timing");
    WorldRuntime restored(w.summary().world,1,{},s6_3_1_fixture::limits());
    restored.restore(cut); restored.advance_to(death);
    require(restored.checkpoint()==w.checkpoint(),"exhaustion split or restore changed a paid boundary");
    w.restore(w.checkpoint()); w.advance_to(pulse);
    require(w.query_physiology(larva)->tissue_protein_ug==36 && w.query_ant(larva)->stage==LifeStage::Larva,
            "deferred protein pulse disappeared or forced development");
    auto no_care=setup(thin(false,true,false)); no_care.world.advance_to({22*day_ms});
    require(facts(no_care.world,FactKind::FoundingLipidMobilized).empty() &&
            !facts(no_care.world,FactKind::AntDied).empty(),"H1 funded an unfed zero-lipid larva");
    auto f=thin(true,true,false).profile;
    auto p=initial_founding_physiology(f,false,{}); FoundingReserve r{6}; p.hydration_ug=0;
    require(!mobilize_founding_larval_lipid(f,p,r,LifeStage::Larva) && r.lipid_ug==6 && !p.body_energy_nj,
            "water and energy tie incorrectly converted lipid");
    p.hydration_ug=1;
    for (const auto stage : {LifeStage::Egg,LifeStage::Pupa,LifeStage::Adult,LifeStage::Dead})
        require(!mobilize_founding_larval_lipid(f,p,r,stage),"wrong stage mobilized lipid");
    check_ledgers(w);
}

Case cue_case(bool care=true) {
    auto c=thin(care,false,true);
    c.profile.first_lay={day_ms}; c.profile.opening_width={1'000}; c.profile.opening_spacing={100};
    c.profile.later_spacing={80*day_ms}; c.profile.brood[0].duration={day_ms};
    return c;
}

void cue_and_rate() {
    auto c=cue_case(); auto scene=setup(c); auto& w=scene.world;
    w.advance_to({2*day_ms});
    const auto cues=facts(w,FactKind::FoundingHatchCue);
    require(cues.size()==1 && cues.front().actor==scene.queen.id && cues.front().time==SimTime{2*day_ms},
            "real local hatch did not open one bounded care opportunity");
    const auto pending=w.pending_events();
    const auto candidate=std::find_if(pending.begin(),pending.end(),[&](const auto& e) { return e.id.value==cues.front().random_value; });
    require(candidate!=pending.end() && candidate->payload==cues.front().payload && candidate->key.time==SimTime{2*day_ms+1},
            "hatch cue did not preserve its bounded contact witness");
    const auto initial=w.checkpoint();
    w.restore(initial); w.advance_to({2*day_ms+1'000});
    require(facts(w,FactKind::FoundingHatchCue).size()==1,"burst of same-hour hatches exceeded the lease cap");
    w.restore(w.checkpoint()); check_ledgers(w);
    auto off=setup(cue_case(false)); off.world.advance_to({3*day_ms});
    require(facts(off.world,FactKind::FoundingHatchCue).empty() && facts(off.world,FactKind::FoundingRation).empty(),
            "disabled care responded to a hatch cue");
    auto decline=closure::timed_care(true); decline.care_probability=0;
    auto refused=setup(c,s6_3_1_fixture::limits(),closure::day_social(),decline);
    refused.world.advance_to({2*day_ms+1'000});
    require(facts(refused.world,FactKind::FoundingHatchCue).size()==1 && facts(refused.world,FactKind::FoundingRation).empty(),
            "hatch cue bypassed ordinary refusal");
    refused.world.restore(refused.world.checkpoint());
}

void cue_fault_and_format(const std::filesystem::path& folder) {
    auto scene=setup(cue_case()); auto& w=scene.world; const auto id=w.summary().world;
    auto limits=s6_3_1_fixture::limits();
    const SimTime due{2*day_ms};
    w.advance_to({due.milliseconds-1}); const auto cut=w.checkpoint();
    w.advance_to(due); const auto pending=w.checkpoint();
    const auto cue=facts(w,FactKind::FoundingHatchCue).front();
    limits.committed_events=static_cast<std::size_t>(cue.id.value-1);
    WorldRuntime failing(id,1,{},limits); failing.restore(cut);
    rejects([&] { failing.advance_to(due); });
    require(failing.checkpoint()==cut,"failed hatch cue changed phase, stock, queue or cooldown");

    const auto all=w.committed_events();
    const auto schema=storage::detail::FactSchema::FoundingEarlyAccess;
    auto block=storage::detail::seal_block(all,{},schema);
    require(pending[6]=='H' && storage::detail::inspect_block(block.bytes).fact_schema==4 &&
            storage::detail::read_block(block.bytes,block.header)==all,"R2 format lost its exact history");
    rejects([&] { (void)storage::detail::seal_block(all,{},storage::detail::FactSchema::FoundingPersistence); });
    auto corrupted=pending; corrupted[corrupted.size()-16]^=1;
    auto checksum=hash_bytes(std::span{corrupted}.first(corrupted.size()-8));
    for (auto i=corrupted.size()-8; i<corrupted.size(); ++i) { corrupted[i]=static_cast<std::uint8_t>(checksum); checksum>>=8; }
    rejects([&] { w.restore(corrupted); });
    require(w.checkpoint()==pending,"corrupt cooldown changed live R2 state");

    storage::Store store(folder/"exact.sqlite",s6_3_1_fixture::limits(),storage::StoreFormat::Segmented);
    const auto saved=store.save(w); auto loaded=store.load(id).world;
    require(loaded.checkpoint()==pending,"SQLite lost pending local cue");
    w.advance_to({3*day_ms}); loaded.advance_to({due.milliseconds+1}); loaded.advance_to({3*day_ms});
    require(loaded.checkpoint()==w.checkpoint(),"R2 queue partition or recovery changed canonical authority");
    storage::SaveOptions fail;
    fail.fault_hook=[](auto stage) { if (stage==storage::SaveStage::AfterManifest) throw std::runtime_error("injected R2 save failure"); };
    rejects([&] { (void)store.save(w,saved,fail); });
    require(store.load(id).world.checkpoint()==pending,"failed publication displaced the saved R2 world");
    check_ledgers(w);
}

void finite_water_paths() {
    for (const auto arm : {"water-reachable","water-blocked","water-absent"}) {
        auto c=thin(true,true,true); c.arm=arm;
        c.profile=nominal(); c.profile.feeding_persistence=FoundingFeedingPersistence{{2*day_ms},750'000};
        c.profile.early_access=FoundingEarlyAccess{true,true};
        if (c.arm!="water-absent") c.food={0,0,200'000,0};
        auto scene=setup(c); auto& w=scene.world;
        w.advance_to({56*day_ms});
        const auto uptake=facts(w,FactKind::PhysiologyUpdated);
        const bool drank=std::any_of(uptake.begin(),uptake.end(),[&](const auto& e) {
            return e.actor!=scene.queen.id && e.stage==LifeStage::Adult && e.transferred.water_ug;
        });
        require(drank==(c.arm=="water-reachable"),"reachable, obstructed and absent water paths are not physically distinct");
        check_ledgers(w); w.restore(w.checkpoint());
    }
}
} // namespace

int main(int argc,char** argv) {
    try {
        require(argc==3,"R2 test requires mode and output path");
        const std::string_view mode=argv[1];
        if (mode=="R2_MOBILIZATION") mobilization();
        else if (mode=="R2_HATCH_CUE") cue_and_rate();
        else if (mode=="R2_RESTORE_FAULT_FORMAT") cue_fault_and_format(argv[2]);
        else if (mode=="R2_FINITE_WATER") finite_water_paths();
        else throw std::invalid_argument("unknown R2 probe");
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
