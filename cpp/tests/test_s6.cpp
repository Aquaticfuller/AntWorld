#include "s6_nutrition_fixture.hpp"
#include "s4_fixture.hpp"
#include <iostream>
#include <algorithm>
#include <map>

using namespace antworld;
using s3_fixture::require;
namespace {
void demand() {
    s6_fixture::Nutrition old(43,400,true,false), corrected(43,400,true,true);
    old.world.advance_to({180000}); corrected.world.advance_to({180000});
    unsigned before=0,after=0;
    for (auto id:old.brood) before+=old.world.query_ant(id)->stage==LifeStage::Adult;
    for (auto id:corrected.brood) {
        after+=corrected.world.query_ant(id)->stage==LifeStage::Adult;
        const auto p=*corrected.world.query_physiology(id);
        require(p.crop.protein_ug+p.tissue_protein_ug<=100,"local demand still oversupplies protein");
    }
    require(before==3,"lost original seed-43 negative control");
    require(after==4,"seed-43 local deficit was not resolved");
    s3_fixture::balanced(old.world); s3_fixture::balanced(corrected.world); s3_fixture::roundtrip(corrected.world);
}
void concurrent() {
    for (bool reverse:{false,true}) {
        WorldRuntime w({6,2},43); SocialConfig social; social.bounded_contacts=false; w.configure_social(social);
        auto colony=w.seed_colony(); auto a=w.seed_ant(colony,{}),b=w.seed_ant(colony,{});
        auto larva=w.seed_ant(colony,{{},LifeStage::Larva,Caste::Worker,4000});
        w.enable_physiology(a,{{0,400,0,0},1000000000,1000,0});
        w.enable_physiology(b,{{0,400,0,0},1000000000,1000,0});
        w.enable_physiology(larva,{{},2000000000,2000,0});
        for (auto donor:(reverse?std::array{b,a}:std::array{a,b}))
            w.submit_nutrition({donor,{1},NutritionAction::Trophallaxis,larva,100});
        w.advance_to({1});
        require(w.query_physiology(larva)->crop.protein_ug==100,"same-time donors duplicated recipient need");
        require(w.query_physiology(a)->crop.protein_ug+w.query_physiology(b)->crop.protein_ug==700,"donor inventory mismatch");
        s3_fixture::balanced(w); s3_fixture::roundtrip(w);
    }
}
void contacts() {
    WorldRuntime w({6,3},17); w.configure_social(); const auto c=w.seed_colony();
    std::vector<AntRef> ants(0);
    for (unsigned i=0;i<200;++i) ants.push_back(w.seed_ant(c,{}));
    const auto before=w.checkpoint(); std::map<EntityId,unsigned> counts;
    for (std::uint64_t decision=0;decision<4096;++decision) {
        const auto sample=w.sample_contacts(ants[0],decision);
        require(sample.candidates_examined==16 && sample.bucket_queries==27,"dense encounters exceed fixed budget");
        require(sample.tree_visits<512,"rank selection enumerated dense population");
        for (const auto a:sample.ants) ++counts[a.id];
    }
    require(w.checkpoint()==before,"contact query mutated RNG/time/state");
    for (std::size_t i=1;i<ants.size();++i)
        require(counts[ants[i].id]>220 && counts[ants[i].id]<440,"contact identity sampling is biased");
    WorldRuntime restored({9,9},0); restored.restore(before);
    for (std::uint64_t decision=0;decision<100;++decision) {
        const auto a=w.sample_contacts(ants[0],decision),b=restored.sample_contacts(ants[0],decision);
        require(a.ants==b.ants && a.tree_visits==b.tree_visits,"derived contact tree changed on restore");
    }
}
void contact_index() {
    WorldRuntime w({6,4},1); const auto c=w.seed_colony(); const auto a=w.seed_ant(c,{}),b=w.seed_ant(c,{}),d=w.seed_ant(c,{});
    // Configuring after initial identities must build the same disposable index.
    w.configure_social(); require(w.sample_contacts(a,0).ants==std::vector<AntRef>{b,d},"late configuration lost identities");
    w.submit({b,{1000},ActionKind::Move,{}, {.01,0,0},0}); w.schedule_lifecycle(d,{1000},LifeStage::Dead);
    w.advance_to({1000}); require(w.sample_contacts(a,0).ants.empty(),"moved/dead contact stayed indexed");
    s3_fixture::roundtrip(w);
    w.submit({b,{2000},ActionKind::Move,{}, {},0}); w.advance_to({2000});
    require(w.sample_contacts(a,0).ants==std::vector<AntRef>{b},"returning contact was not indexed");
    s3_fixture::roundtrip(w);
}
void contact_wall() {
    using s4_fixture::position;
    WorldRuntime w({6,5},7); auto g=s4_fixture::config();
    const std::array<BoxQ,2> rooms{{{{2,2,2},{10,22,22}},{{11,2,2},{28,22,22}}}};
    w.configure_geometry(g,rooms); w.configure_social();
    const auto c=w.seed_colony(position({8,12,12},g));
    const auto a=w.seed_ant(c,{position({9,12,12},g)}),b=w.seed_ant(c,{position({12,12,12},g),LifeStage::Larva});
    w.enable_physiology(a,{{0,400,0,0},1000000000,1000,0}); w.enable_physiology(b);
    require(w.sample_contacts(a,0).ants.empty(),"bounded encounters crossed solid wall");
    w.submit_nutrition({a,{1},NutritionAction::Trophallaxis,b,100}); w.advance_to({1});
    require(w.query_physiology(b)->crop.protein_ug==0,"demand transfer crossed wall");
    s3_fixture::balanced(w); s3_fixture::roundtrip(w);
}
}
int main(int argc,char** argv) {
    try {
        if (argc!=2) throw std::invalid_argument("usage: antworld_s6_tests TEST");
        const std::string test=argv[1];
        if (test=="DEMAND") demand(); else if (test=="CONCURRENT") concurrent();
        else if (test=="CONTACTS") contacts(); else if (test=="CONTACT_INDEX") contact_index();
        else if (test=="CONTACT_WALL") contact_wall(); else throw std::invalid_argument("unknown test");
        std::cout<<"PASS S6_"<<test<<'\n'; return 0;
    } catch (const std::exception& e) { std::cerr<<"FAIL: "<<e.what()<<'\n'; return 1; }
}
