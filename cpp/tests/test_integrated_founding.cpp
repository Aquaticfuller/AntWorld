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

Case founding_case(std::string arm="balanced", bool intake=true, bool eggs=true) {
    auto f=nominal();
    f.feeding_persistence=FoundingFeedingPersistence{{2*day_ms},750'000};
    f.early_access=FoundingEarlyAccess{true,true};
    f.provisioning=FoundingProvisioning{true};
    f.worker.behavior_interval={hour_ms};
    f.worker.carbohydrate_yield_nj_per_ug=8'000'000;
    f.dietary=FoundingDietaryAccess{intake,eggs};
    const FoodMass stock=arm=="absent"?FoodMass{}:FoodMass{6000,3000,18000,0};
    return {201,1,std::move(arm),true,0,stock,f,{150*day_ms},true};
}

void funded_components() {
    const auto f=founding_case().profile;
    auto donor=initial_founding_physiology(f,false,{});
    donor.crop={9,3,20,0};
    require(founding_gift_supply(f,donor)==FoodMass{3,3,20,0},
            "gift did not protect its next two scheduled energy intervals");
    donor.hydration_ug=1;
    require(founding_gift_supply(f,donor)==FoodMass{3,3,9,0},
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
    storage::Store store(folder/"founding.sqlite",s6_3_1_fixture::limits(),storage::StoreFormat::Segmented);
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
} // namespace

int main(int argc,char** argv) {
    try {
        require(argc==3,"expected mode and output directory");
        const std::string_view mode=argv[1];
        if (mode=="IF_COMPONENTS") funded_components();
        else if (mode=="IF_COLONY") real_colony(argv[2]);
        else if (mode=="IF_NO_SOURCE") no_local_source();
        else throw std::invalid_argument("unknown integrated founding test");
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
