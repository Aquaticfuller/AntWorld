#include "s6_nutrition_fixture.hpp"
#include "s4_fixture.hpp"
#include "s6_fixture.hpp"
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
void surplus() {
    for (bool pupa:{false,true}) for (const auto condition:{"contact","range","wall","no_response","no_protein"}) {
        s6_fixture::Surplus f(43,condition,pupa); const auto id=f.donor.id;
        f.world.advance_to({180000}); s6_fixture::balanced(f.world); s3_fixture::roundtrip(f.world);
        std::uint64_t protein=0;
        for (const auto& e:f.world.committed_events()) if (e.kind==FactKind::NutritionTransferred) protein+=e.transferred.protein_ug;
        if (std::string(condition)=="contact") require(protein==200,"adult crop surplus did not meet contacted larval demand");
        else require(protein==0,"negative surplus control transferred protein");
        require(f.world.query_ant(f.donor)->id==id && f.world.query_ant(f.donor)->stage==LifeStage::Adult,"emergence replaced original identity");
        require(f.world.query_autonomy(f.donor)->decisions>0,"enrolled emerged worker never activated");
    }
}
void autonomy_control() {
    s6_fixture::Surplus f(1,"contact",true); auto& w=f.world;
    require(!w.query_autonomy(f.donor)->wake.value,"pupa has adult behavior wake");
    w.advance_to({30000}); require(w.query_ant(f.donor)->stage==LifeStage::Adult && w.query_autonomy(f.donor)->wake.value,"emergence did not activate ownership");
    s3_fixture::roundtrip(w); w.advance_to({45000});
    w.set_behavior(f.donor,IndividualBehavior::Paused); const auto before=w.query_autonomy(f.donor)->decisions;
    require(!w.query_autonomy(f.donor)->enabled && !w.query_autonomy(f.donor)->wake.value,"manual pause left automatic ownership");
    w.advance_to({60000}); require(w.query_autonomy(f.donor)->decisions==before,"paused worker resumed itself");
    w.set_autonomy(f.donor); w.advance_to({75000}); require(w.query_autonomy(f.donor)->decisions>before,"runtime enrollment failed");
    w.schedule_lifecycle(f.donor,{75001},LifeStage::Dead); w.advance_to({75001});
    for (const auto& e:w.pending_events()) require(e.actor!=f.donor.id,"dead individual still owns work");
    s6_fixture::balanced(w); s3_fixture::roundtrip(w);
}
void mixed_space() {
    s6_fixture::Integrated f(3); auto& w=f.world; const auto a=f.identities[1];
    w.set_behavior(a,IndividualBehavior::Excavate); w.advance_to({20000});
    const auto x=w.query_excavator(a); require(x && x->digs && x->carrying_moves,"mixed substrate blocked actual 3D excavation");
    s6_fixture::balanced(w); s3_fixture::roundtrip(w);
    WorldRuntime copy({9,9},0,{},s6_fixture::limits()); copy.restore(w.checkpoint());
    w.advance_to({60000}); for (std::int64_t t=21000;t<=60000;t+=1000) copy.advance_to({t});
    require(w.checkpoint()==copy.checkpoint(),"mixed ecology depends on host time slicing");
    s6_fixture::balanced(w); s3_fixture::roundtrip(w);
}
void off_plane() {
    WorldRuntime w({6,11},1); w.configure_surface({{-.01,0,-.01},3,3,.01},{});
    GeometryConfig g; g.origin_m={-.016,-.016,-.016}; g.initial_solid={{0,0,0},{64,64,64}};
    const BoxQ room{{4,4,4},{60,60,60}}; w.configure_geometry(g,std::span{&room,1}); w.configure_social();
    const auto c=w.seed_colony(); const auto donor=w.seed_ant(c,{}),larva=w.seed_ant(c,{{0,.0005,0},LifeStage::Larva});
    w.enable_physiology(donor,{{0,200,0,0},1000000000,1000,0}); w.enable_physiology(larva);
    w.submit_nutrition({donor,{1},NutritionAction::Trophallaxis,larva,100}); w.advance_to({1});
    require(w.query_physiology(larva)->crop.protein_ug==100,"reachable off-plane brood was not fed");
    s6_fixture::balanced(w); s3_fixture::roundtrip(w);
}
void sealed() {
    s6_fixture::Integrated f(11,"sealed"); f.world.advance_to({60000});
    require(f.world.summary().food_ledger.available==f.world.summary().food_ledger.introduced,"sealed workers accessed external food");
    require(f.world.geometry_edits().empty(),"workers excavated through immutable shell");
    for (const auto& a:f.world.ant_states()) require(a.position==PositionM{},"sealed worker crossed a wall");
    s6_fixture::balanced(f.world); s3_fixture::roundtrip(f.world);
}
void determinism() {
    for (std::uint64_t seed=1;seed<=8;++seed) {
        auto build=[&](bool reverse) {
            WorldRuntime w({6,12},seed); w.configure_surface({{},3,1,.01},{}); w.configure_social(); const auto c=w.seed_colony();
            std::vector<AntRef> ants(0);
            for (unsigned i=0;i<5;++i) {
                const auto a=w.seed_ant(c,{{},i<3?LifeStage::Adult:LifeStage::Larva}); ants.push_back(a);
                w.enable_physiology(a,{i<3?FoodMass{100,200,200,0}:FoodMass{},1000000000,1000,0});
            }
            w.seed_food({.02,0,0},{100,400,400,100}); if (reverse) std::reverse(ants.begin(),ants.end());
            for (auto a:ants) w.set_autonomy(a); return w;
        };
        auto a=build(false),b=build(true); a.advance_to({60000});
        for (std::int64_t t=1000;t<=60000;t+=1000) b.advance_to({t});
        require(a.ant_states()==b.ant_states() && a.nutrition_snapshot()==b.nutrition_snapshot(),"enrollment order changed individual ecology");
        auto facts=[](const WorldRuntime& w) {
            std::vector<WorldEvent> out(0); for (auto e:w.committed_events()) {
                if (e.kind==FactKind::AutonomyChanged) continue;
                e.id={}; e.source={}; e.revision=0; out.push_back(e);
            } return out;
        };
        require(facts(a)==facts(b),"enrollment order selected behavior");
        s3_fixture::roundtrip(a); s3_fixture::roundtrip(b);
    }
}
void limits() {
    RuntimeLimits limit; limit.committed_events=17; WorldRuntime w({6,13},1,{},limit); w.configure_social();
    const auto c=w.seed_colony();
    const auto a=w.seed_ant(c,{}),b=w.seed_ant(c,{{},LifeStage::Larva});
    w.enable_physiology(a,{{0,200,0,0},1000000000,1000,0}); w.enable_physiology(b); w.set_autonomy(a);
    w.advance_to({4999}); const auto before=w.checkpoint(); const auto sample=w.sample_contacts(a,3);
    bool rejected=false; try { w.advance_to({5000}); } catch (const std::length_error&) { rejected=true; }
    require(rejected && before==w.checkpoint() && sample==w.sample_contacts(a,3),"failed automatic transaction did not roll back");
}
void corruption() {
    s6_fixture::Surplus f(3,"contact"); f.world.advance_to({35000}); const auto bytes=f.world.checkpoint();
    for (const auto offset:{bytes.size()-16,bytes.size()-8-(1+39+40+8+3*41)+4}) {
        auto bad=bytes; bad[offset]^=1;
        std::uint64_t hash=UINT64_C(14695981039346656037);
        for (std::size_t i=0;i<bad.size()-8;++i) hash=(hash^bad[i])*UINT64_C(1099511628211);
        for (unsigned i=0;i<8;++i) bad[bad.size()-8+i]=static_cast<std::uint8_t>(hash>>(8*i));
        bool rejected=false; try { f.world.restore(bad); } catch (const std::exception&) { rejected=true; }
        require(rejected && f.world.checkpoint()==bytes,"corrupt social state accepted or restore changed authority");
    }
}
}
int main(int argc,char** argv) {
    try {
        if (argc!=2) throw std::invalid_argument("usage: antworld_s6_tests TEST");
        const std::string test=argv[1];
        if (test=="DEMAND") demand(); else if (test=="CONCURRENT") concurrent();
        else if (test=="CONTACTS") contacts(); else if (test=="CONTACT_INDEX") contact_index();
        else if (test=="CONTACT_WALL") contact_wall(); else if (test=="SURPLUS") surplus();
        else if (test=="AUTONOMY_CONTROL") autonomy_control(); else if (test=="MIXED_SPACE") mixed_space();
        else if (test=="OFF_PLANE") off_plane(); else if (test=="SEALED") sealed();
        else if (test=="DETERMINISM") determinism(); else if (test=="LIMITS") limits(); else if (test=="CORRUPTION") corruption();
        else throw std::invalid_argument("unknown test");
        std::cout<<"PASS S6_"<<test<<'\n'; return 0;
    } catch (const std::exception& e) { std::cerr<<"FAIL: "<<e.what()<<'\n'; return 1; }
}
