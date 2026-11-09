#include "s6_3_3_fixture.hpp"
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>

using namespace antworld;
using namespace s6_3_3_fixture;

namespace {
using Clock = std::chrono::steady_clock;
double milliseconds(Clock::time_point start) {
    return std::chrono::duration<double,std::milli>(Clock::now()-start).count();
}

void density(std::ostream& out, unsigned caregivers, unsigned per_carer, bool dense, bool local, unsigned replicate) {
    // ENGINEERING_FIXTURE. Only placement and colony partition differ between layouts.
    WorldRuntime w({6331,7},7,{{-.01,-.01,-.01},{.27,.01,.13},.01,.002},limits());
    w.configure_long_term();
    w.configure_social();
    SpeciesCareProfile profile;
    profile.local_retrieval=local;
    w.configure_biology(profile);
    const auto p=physiology();
    ColonyRef colony;
    AntRef first;
    for (unsigned i=0;i<caregivers;++i) {
        const PositionM nest=dense?PositionM{}:PositionM{static_cast<double>(i%16)*.014,0,static_cast<double>(i/16)*.014};
        if (i==0 || !dense) colony=w.seed_colony(nest);
        const auto worker=w.seed_ant(colony,{nest});
        if (i==0) first=worker;
        w.enable_physiology(worker,{{},p.energy_capacity_nj,p.hydration_capacity_ug,0},p);
        w.enable_brood_care(worker,{CareContext::Worker,{}});
        for (unsigned j=0;j<per_carer;++j) w.seed_ant(colony,{{nest.x+.0005,0,nest.z},LifeStage::Larva});
    }
    const auto examined=w.query_neighborhood(first,profile.perception_radius_m).candidates_examined;
    require(examined==caregivers*(1+per_carer),"open-neighborhood candidate accounting differs");
    const auto before=w.summary().committed_events;
    auto start=Clock::now();
    w.advance_to({60000});
    const auto advance_ms=milliseconds(start);
    start=Clock::now();
    const auto checkpoint=w.checkpoint();
    const auto checkpoint_ms=milliseconds(start);
    WorldRuntime restored({1,1},0,{},limits());
    start=Clock::now();
    restored.restore(checkpoint);
    const auto restore_ms=milliseconds(start);
    require(restored.checkpoint()==checkpoint,"density round trip differs");
    conserved(w);
    const auto history=w.committed_events();
    std::array<std::size_t,static_cast<std::size_t>(FactKind::BroodMoved)+1> encoded_size{};
    std::uint64_t decisions=0, opportunities=0, initial_opportunities=0, handled=0, transfer_facts=0;
    std::uint64_t selected=0, started=0, completed=0, interrupted=0, history_bytes=0;
    for (const auto& event:history) {
        auto& length=encoded_size.at(static_cast<std::size_t>(event.kind));
        if (!length) length=encode_event(event).size();
        history_bytes+=length;
        if (event.kind==FactKind::CareTick && event.payload==static_cast<std::uint64_t>(ScheduledEvent::Kind::CareWake)) ++decisions;
        if (event.kind==FactKind::NutritionTransferred) ++transfer_facts;
        if (event.kind!=FactKind::BiologicalObservation) continue;
        const auto& observation=event.observation;
        if (observation.phase==ObservationPhase::Opportunity) {
            ++opportunities;
            if (event.time==SimTime{1}) ++initial_opportunities;
        } else if (observation.phase==ObservationPhase::Selected) ++selected;
        else if (observation.phase==ObservationPhase::Started) ++started;
        else if (observation.phase==ObservationPhase::Completed) {
            ++completed;
            if (observation.act>=CareAct::InspectBrood && observation.act<=CareAct::FeedBrood) ++handled;
        } else ++interrupted;
    }
    const auto expected=dense?caregivers*(caregivers-1+caregivers*per_carer):caregivers*per_carer;
    require(initial_opportunities==expected,"synchronous opportunity facts were lost");
    const auto trace=w.snapshot().trace_hash;
    out<<caregivers<<','<<caregivers*per_carer<<','<<per_carer<<','<<(dense?"dense":"dispersed")<<','
       <<(local?"local":"legacy")<<','<<replicate<<','<<(replicate==0)<<",7,60000,"<<std::setprecision(17)
       <<advance_ms<<','<<checkpoint_ms<<','<<restore_ms<<','<<decisions<<','<<decisions*examined<<','<<examined<<','
       <<initial_opportunities<<','<<opportunities<<','<<selected<<','<<started<<','<<completed<<','<<interrupted<<','
       <<handled<<','<<transfer_facts<<','<<history.size()-before<<','<<history.size()<<','<<history_bytes<<','
       <<checkpoint.size()<<','<<trace<<",1\n";
    out.flush();
}
}

int main(int argc,char** argv) {
    try {
        if (argc!=2) throw std::invalid_argument("usage: antworld_s6_3_3_1_density OUTPUT_CSV");
        const std::filesystem::path path=argv[1];
        if (std::filesystem::exists(path)) throw std::invalid_argument("density output already exists");
        std::ofstream out(path,std::ios::binary);
        if (!out) throw std::runtime_error("cannot open density output");
        out<<"caregivers,brood,brood_per_caregiver,layout,policy,replicate,warmup,seed,sim_ms,advance_ms,checkpoint_ms,restore_ms,"
             "decisions,candidates_examined,candidates_per_query,initial_opportunities,opportunities,selected,started,completed,interrupted,"
             "completed_brood_handling,nutrition_transfers,advance_facts,journal_facts,encoded_history_bytes,checkpoint_bytes,trace_hash,restore_equal\n";
        for (unsigned count:{1U,8U,32U,128U})
            for (unsigned brood_per_caregiver:{1U,4U})
                for (bool dense:{true,false})
                    for (bool local:{false,true})
                        for (unsigned replicate=0;replicate<4;++replicate)
                            density(out,count,brood_per_caregiver,dense,local,replicate);
        if (!out) throw std::runtime_error("density output write failed");
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
