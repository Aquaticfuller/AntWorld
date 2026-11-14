#include "wp6b_fixture.hpp"
#include "brood_space.hpp"
#include "antworld/storage/store.hpp"
#include <array>
#include <bit>
#include <iostream>

namespace {
using namespace antworld;
using namespace antworld::detail;
using namespace antworld::wp6b;

WorldRuntime colony(bool blocked=false, bool micro=true, RuntimeLimits limits={}) {
    WorldConfig bounds;
    bounds.continuous_spatial_motion=true;
    WorldRuntime world({27,1},7,bounds,limits);
    EcologicalClosureConfig profile;
    profile.portable_field=true; profile.brood_space=micro; profile.activity_cost=true;
    profile.portable_care_motion=micro;
    world.configure_ecological_closure(profile);
    world.configure_long_term();
    GeometryConfig geometry;
    geometry.origin_m={}; geometry.initial_solid={{-12,-18,-12},{12,0,12}};
    const std::array voids{blocked?BoxQ{{-2,-10,-2},{2,-4,2}}:BoxQ{{-5,-10,-5},{5,-4,5}}};
    world.configure_geometry(geometry,voids);
    world.configure_social(closure::day_social());
    world.configure_biology(closure::timed_care(true));
    const PositionM nest{0,-.004,0};
    const auto c=world.seed_colony(nest);
    const auto queen=world.seed_ant(c,{nest,LifeStage::Adult,Caste::Queen,4000});
    world.enable_founding(queen,nominal());
    return world;
}

void place_and_restore(const std::filesystem::path& path) {
    auto world=colony();
    const auto id=world.summary().world;
    const SimTime past{4*day_ms+4*hour_ms}, end{4*day_ms+20*hour_ms};
    world.advance_to(past);
    const auto ants=world.ant_states();
    require(ants.size()==4,"expected three actually laid eggs");
    for (std::size_t i=1;i<ants.size();++i) {
        require(ants[i].stage==LifeStage::Egg && ants[i].position!=ants[0].position &&
                within_contact(ants[0].position,ants[i].position,world.config()),"invalid egg location");
        for (std::size_t j=1;j<i;++j)
            require(!intersects_brood(ants[i].position,ants[i].position,ants[j].position),"overlapping eggs");
    }
    storage::Store store(path,{},storage::StoreFormat::Segmented);
    const auto saved=store.save(world);
    auto restored=store.load(id);
    require(restored.token==saved && restored.world.checkpoint()==world.checkpoint(),"MicroWorld initial durable cut changed");
    world.advance_to(end);
    restored.world.advance_to({past.milliseconds+1});
    restored.world.advance_to(end);
    require(restored.world.checkpoint()==world.checkpoint(),"partitions changed canonical history or RNG");
    check_ledgers(world);
    auto control=colony(false,false);
    control.advance_to(past);
    require(control.ant_states().size()==4 && control.ant_states()[1].position==control.ant_states()[0].position,
            "legacy opt-out changed the birth site");
}

void spatial_refusal() {
    auto sealed=colony(true);
    const auto id=sealed.summary().world;
    const AntRef queen{id,{2}};
    const auto before=*sealed.query_founding(queen);
    sealed.advance_to({4*day_ms});
    const auto facts=sealed.committed_events();
    const auto attempt=std::find_if(facts.begin(),facts.end(),[](const auto& fact) {return fact.kind==FactKind::ReproductionAttempt;});
    require(attempt!=facts.end() && attempt->outcome==Outcome::Capacity && !attempt->payload && sealed.ant_states().size()==1,
            "an egg was booked into rock");
    require(sealed.query_founding(queen)->mobile_protein_ug==before.mobile_protein_ug &&
            sealed.query_physiology(queen)->exported_energy_nj==0,"failed placement charged the mother");
    check_ledgers(sealed);
    const auto checkpoint=sealed.checkpoint(); sealed.restore(checkpoint);
    require(sealed.checkpoint()==checkpoint,"refused attempt did not survive validation");

    auto full=colony();
    const ColonyRef c{full.summary().world,{1}};
    std::vector<AntRef> seeded;
    const auto origin=full.query_ant({c.world,{2}})->position;
    for (int x=-2;x<=2;++x) for (int z=-2;z<=2;++z) {
        const PositionM place{x*brood_pitch_m,origin.y,z*brood_pitch_m};
        if (x*x+z*z>=2 && within_contact(origin,place,full.config()))
            seeded.push_back(full.seed_ant(c,{place,LifeStage::Egg}));
    }
    bool refused=false;
    try { (void)full.seed_ant(c,{full.query_ant(seeded.front())->position,LifeStage::Pupa}); }
    catch (const std::invalid_argument&) { refused=true; }
    require(refused,"seed fixture created overlapping brood");
    full.advance_to({4*day_ms});
    require(full.ant_states().size()==seeded.size()+1,"full clutch accepted another egg");
    const auto released=full.query_ant(seeded.front())->position;
    full.schedule_lifecycle(seeded.front(),{4*day_ms+1},LifeStage::Dead);
    full.advance_to({4*day_ms+2*hour_ms});
    require(full.ant_states().size()==seeded.size()+2 && full.ant_states().back().position==released,
            "a vacated brood slot could not be reused");
    check_ledgers(full);
    const auto after=full.checkpoint(); full.restore(after);
    require(full.checkpoint()==after,"full clutch identity changed on restore");
}

void rollback() {
    RuntimeLimits limits; limits.entities=2;
    auto world=colony(false,true,limits);
    world.advance_to({4*day_ms-1});
    const auto last=world.committed_events();
    bool threw=false;
    try { world.advance_to({4*day_ms}); }
    catch (const std::length_error&) { threw=true; }
    require(threw && world.committed_events()==last && world.ant_states().size()==1,"failed egg transaction leaked facts or identity");
    require(world.query_physiology({world.summary().world,{2}})->exported_energy_nj==0,"failed payment leaked to ledger");
    check_ledgers(world);
    const auto restored=world.checkpoint(); world.restore(restored);
    require(world.checkpoint()==restored,"failed birth state was not recoverable");
}

void diagonal_clock() {
    const PositionM from{-.00075,-.004,-.00075}, shelter{0,-.004,0};
    const auto next=portable_care_toward(from,shelter,.001);
    require(std::bit_cast<std::uint64_t>(next.x)==UINT64_C(0xbf067d07c6b47e20) && next.x==next.z && next.y==from.y,
            "portable care segment changed its authoritative diagonal end position");
    const auto duration=care_duration(closure::timed_care(true),WorldConfig{},Caste::Worker,CareAct::ReturnToCareShelter,from,next,true);
    require(duration.milliseconds==101,"portable care segment changed its integer-boundary clock");
}
} // namespace

int main(int argc,char** argv) try {
    require(argc==2,"expected a dedicated test directory");
    const std::filesystem::path folder=argv[1];
    std::filesystem::create_directories(folder);
    place_and_restore(folder/"micro-world.sqlite");
    spatial_refusal();
    rollback();
    diagonal_clock();
    return 0;
} catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
}
