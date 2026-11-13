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
    throw std::runtime_error("expected founding transaction to fail");
}

Case founding_case(std::string arm="balanced", bool intake=true, bool eggs=true, bool uptake=false, bool refill=false) {
    auto f=nominal();
    f.feeding_persistence=FoundingFeedingPersistence{{2*day_ms},750'000};
    f.early_access=FoundingEarlyAccess{true,true};
    f.provisioning=FoundingProvisioning{true};
    f.worker.behavior_interval={hour_ms};
    f.worker.carbohydrate_yield_nj_per_ug=8'000'000;
    f.dietary=FoundingDietaryAccess{intake,eggs,uptake,refill};
    const FoodMass stock=arm=="absent"?FoodMass{}:FoodMass{6000,3000,18000,0};
    return {201,1,std::move(arm),true,0,stock,f,{150*day_ms},true};
}

void funded_components() {
    const auto f=founding_case().profile;
    auto donor=initial_founding_physiology(f,false,{});
    donor.crop={19,3,20,0};
    require(founding_gift_supply(f,donor)==FoodMass{8,3,20,0},
            "gift did not protect its next two scheduled energy intervals");
    donor.hydration_ug=1;
    require(founding_gift_supply(f,donor)==FoodMass{8,3,9,0},
            "gift did not protect its next two scheduled water intervals");
    auto q=initial_founding_physiology(f,true,{});
    q.body_energy_nj=1'995'000'000;
    q.crop.protein_ug=20;
    FoundingReserve reserve{};
    require(founding_egg_fuel(f,q,reserve)==FoundingEggFuel::None,"the empty reserve funded an unassimilated egg");
    q.oxidized_carbs_ug=1;
    require(founding_egg_fuel(f,q,reserve)==FoundingEggFuel::Body,"actual energy did not fund the paid route");
    require(debit_dietary_egg(f,q,reserve)==20 && !q.crop.total_ug() && !reserve.lipid_ug && !reserve.mobile_protein_ug &&
            q.exported_energy_nj==408'000'000 && q.dissipated_energy_nj==10'000'000 &&
            q.body_energy_nj==1'577'000'000 && q.hydration_ug==6935,"dietary egg compartments did not close");
    q.body_energy_nj=0;
    require(!foundress_nest_meal(f,q,reserve,{1000,1000,1000,0}).total_ug(),"an exhausted queen could ingest");
    q.body_energy_nj=1; q.hydration_ug=0;
    require(!foundress_nest_meal(f,q,reserve,{1000,1000,1000,0}).total_ug(),"a dehydrated queen could ingest");
}

void real_colony(const std::filesystem::path& folder) {
    auto scene=setup(founding_case());
    auto& w=scene.world;
    require(w.ant_states().size()==1,"the integrated case seeded offspring");
    w.advance_to({75*day_ms});
    const auto checkpoint=w.checkpoint();
    const auto id=w.summary().world;
    require(checkpoint[6]=='J' && w.founding_profile()->model_version()==5,"wrong dietary checkpoint identity");
    storage::Store store(folder/"exact.sqlite",s6_3_1_fixture::limits(),storage::StoreFormat::Segmented);
    const auto saved=store.save(w);
    auto recovery=store.load(id).world;
    require(recovery.checkpoint()==checkpoint,"dietary checkpoint failed after normal publication");
    auto events=w.committed_events();
    const auto locate=[&](FactKind kind) {
        return std::find_if(events.begin(),events.end(),[&](const auto& event) { return event.kind==kind; });
    };
    const auto adult=std::find_if(events.begin(),events.end(),[](const auto& e) {
        return e.kind==FactKind::StageChanged && e.stage==LifeStage::Adult;
    });
    const auto delivered=locate(FactKind::FoodDelivered), meal=locate(FactKind::FoundressNestMeal);
    const auto funded=locate(FactKind::FoundingDietaryEggFunded);
    require(adult!=events.end() && delivered!=events.end() && meal!=events.end() && funded!=events.end() &&
            adult->id<delivered->id && delivered->id<meal->id && meal->id<funded->id,"actual funded food chain did not occur");
    const auto eclosion=std::find_if(events.begin(),delivered,[&](const auto& e) {
        return e.actor==delivered->actor && e.kind==FactKind::StageChanged && e.stage==LifeStage::Adult;
    });
    require(eclosion!=delivered && std::any_of(eclosion,delivered,[&](const auto& e) {
        return e.actor==delivered->actor && e.kind==FactKind::Moved && e.position.y>0;
    }),"delivery did not traverse the physical surface link");
    const auto birth=std::find_if(events.begin(),funded,[&](const auto& e) {
        return e.actor.value==funded->payload && e.kind==FactKind::AntBorn && e.source==funded->source;
    });
    require(birth!=funded && birth->random_value==funded->random_value,"egg energy has no maternal evidence");
    const auto nutritional_boundary=std::find_if(meal,funded,[&](const auto& e) {
        return e.actor==scene.queen.id && e.kind==FactKind::PhysiologyUpdated && e.transferred.carbs_ug;
    });
    require(nutritional_boundary!=funded && nutritional_boundary->time>meal->time,"a nest meal was counted as immediate uptake");
    using Schema=storage::detail::FactSchema;
    rejects([&] { (void)storage::detail::seal_block(std::span<const WorldEvent>(&*funded,1),{},Schema::FoundingProvisioning); });
    const auto block=storage::detail::seal_block(std::span<const WorldEvent>(&*funded,1),{},Schema::FoundingDietary);
    require(storage::detail::inspect_block(block.bytes).fact_schema==6,"dietary event block lacks its distinct version");
    WorldRuntime before(id,1,{},s6_3_1_fixture::limits());
    before.restore(checkpoint);
    recovery.advance_to({91*day_ms+17}); recovery.advance_to({110*day_ms});
    w.advance_to({110*day_ms});
    require(w.checkpoint()==recovery.checkpoint(),"partitioned durable recovery differs after a dietary egg");
    storage::SaveOptions failure;
    failure.fault_hook=[](auto stage) {
        if (stage==storage::SaveStage::AfterManifest) throw std::runtime_error("injected founding publication failure");
    };
    rejects([&] { (void)store.save(w,saved,failure); });
    require(store.load(id).world.checkpoint()==checkpoint,"failed publication changed the last durable authority");
    check_ledgers(w);
}

void no_local_source() {
    for (const auto* label : {"blocked","absent"}) {
        auto s=setup(founding_case(label));
        s.world.advance_to({100*day_ms});
        const auto events=s.world.committed_events();
        require(std::none_of(events.begin(),events.end(),[](const auto& e) {
            return e.kind==FactKind::FoodCollected || e.kind==FactKind::FoundressNestMeal || e.kind==FactKind::FoundingDietaryEggFunded;
        }),"an obstructed or absent source financed a meal or egg");
        check_ledgers(s.world);
        s.world.restore(s.world.checkpoint());
    }
}

void boundary_components() {
    const auto f=founding_case("balanced",true,true,true).profile;
    auto p=initial_founding_physiology(f,false,{});
    const SimTime slice{1000};
    p.updated_at=slice;
    p.crop={100,5,0,0};
    p.body_energy_nj=p.hydration_ug=0;
    FoundingUptakeClock clock{};
    const auto unchanged=p;
    require(founding_boundary_uptake(p,clock)==FoodMass{} && p==unchanged && clock==FoundingUptakeClock{},
            "a missing component changed an exhausted adult");
    p.crop.water_ug=100;
    const auto brood=p;
    require(!founding_boundary_enabled(f,LifeStage::Larva),"adult crop boundary was enabled for brood");
    const auto first=founding_boundary_uptake(p,clock);
    require(first.carbs_ug && first.water_ug && p.crop==subtract(brood.crop,first) && p.crop.protein_ug==5 &&
            clock.carb==slice && clock.water==slice,"crop boundary failed to debit the real stock");
    require(founding_pulse(p,clock,LifeStage::Adult)==FoodMass{},"the aligned pulse spent the same allowance twice");
    p.body_energy_nj=0;
    const auto same_time=p;
    require(founding_boundary_uptake(p,clock)==FoodMass{} && p==same_time,
            "a second zero-elapsed uptake was accepted");
}

void boundary_colony(const std::filesystem::path& folder) {
    auto s=setup(founding_case("balanced",true,true,true));
    auto& w=s.world;
    w.advance_to({150*day_ms});
    const auto checkpoint=w.checkpoint();
    require(checkpoint[6]=='K' && w.founding_profile()->model_version()==6,"wrong boundary-uptake checkpoint identity");
    storage::Store store(folder/"exact.sqlite",s6_3_1_fixture::limits(),storage::StoreFormat::Segmented);
    store.save(w);
    auto restored=store.load(w.summary().world).world;
    require(restored.checkpoint()==checkpoint,"boundary uptake was not durable");
    const auto events=w.committed_events();
    const auto witness=std::find_if(events.begin(),events.end(),[](const auto& e) { return e.kind==FactKind::FoundingBoundaryUptake; });
    require(witness!=events.end(),"integrated case did not exercise boundary crop uptake");
    require(std::next(witness)!=events.end() && std::next(witness)->kind==FactKind::PhysiologyUpdated &&
            witness->source==std::next(witness)->source && witness->time==std::next(witness)->time,"boundary witness lacked the scheduled outcome");
    using Schema=storage::detail::FactSchema;
    rejects([&] { (void)storage::detail::seal_block(std::span<const WorldEvent>(&*witness,1),{},Schema::FoundingDietary); });
    const auto block=storage::detail::seal_block(std::span<const WorldEvent>(&*witness,1),{},Schema::FoundingUptake);
    require(storage::detail::inspect_block(block.bytes).fact_schema==7,"boundary event block has the wrong schema");
    w.advance_to({159*day_ms});
    restored.advance_to({153*day_ms+1}); restored.advance_to({159*day_ms});
    require(w.checkpoint()==restored.checkpoint(),"boundary uptake changed under partitioned durable recovery");
    check_ledgers(w);
}

void local_resupply(const std::filesystem::path& folder) {
    auto control=setup(founding_case("balanced",true,true,true));
    auto treatment=setup(founding_case("balanced",true,true,true,true));
    auto blocked=setup(founding_case("blocked",true,true,true,true));
    const auto f=*treatment.world.founding_profile();
    auto p=initial_founding_physiology(f,true,{});
    const auto deficit=founding_resupply_shortfall(f,p,{},true,{6*hour_ms});
    require(deficit.carbs_ug && !deficit.water_ug,"available water was treated as an energy resource");
    const FoundingReserve owned{500};
    require(!founding_resupply_shortfall(f,p,owned,true,{6*hour_ms}).total_ug(),"usable lipid was ignored");
    constexpr SimTime cut{85*day_ms};
    control.world.advance_to(cut);
    treatment.world.advance_to(cut);
    blocked.world.advance_to(cut);
    const auto has_delivery=[](const WorldRuntime& world) {
        const auto facts=world.committed_events();
        return std::any_of(facts.begin(),facts.end(),[](const auto& e) { return e.kind==FactKind::FoodDelivered; });
    };
    require(has_delivery(control.world) && has_delivery(treatment.world) && !has_delivery(blocked.world),"resupply ignored the accessible source");
    const auto checkpoint=treatment.world.checkpoint();
    require(checkpoint[6]=='L',"resupply has no unique format identity");
    storage::Store store(folder/"exact.sqlite",s6_3_1_fixture::limits(),storage::StoreFormat::Segmented);
    const auto token=store.save(treatment.world);
    rejects([&] { (void)store.save(control.world,token); });
    auto loaded=store.load(treatment.world.summary().world).world;
    require(loaded.checkpoint()==checkpoint,"resupply did not replay its own history");
    treatment.world.advance_to({91*day_ms});
    loaded.advance_to({88*day_ms+1}); loaded.advance_to({91*day_ms});
    require(loaded.checkpoint()==treatment.world.checkpoint(),"resupply continuation changed across cuts");
    check_ledgers(loaded);
}
} // namespace

int main(int argc,char** argv) {
    try {
        require(argc==3,"expected mode and output directory");
        const std::string_view mode=argv[1];
        if (mode=="IF_COMPONENTS") funded_components();
        else if (mode=="IF_COLONY") real_colony(argv[2]);
        else if (mode=="IF_NO_SOURCE") no_local_source();
        else if (mode=="IF_BOUNDARY_COMPONENTS") boundary_components();
        else if (mode=="IF_BOUNDARY_COLONY") boundary_colony(argv[2]);
        else if (mode=="IF_LOCAL_RESUPPLY") local_resupply(argv[2]);
        else throw std::invalid_argument("unknown integrated founding test");
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
