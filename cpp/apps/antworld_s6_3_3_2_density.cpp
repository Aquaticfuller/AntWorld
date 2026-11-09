#include "s6_3_3_fixture.hpp"
#include "antworld/core/profiling.hpp"
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>

using namespace antworld;
using namespace s6_3_3_fixture;

namespace {
using Clock=std::chrono::steady_clock;
double ms(Clock::time_point start) {
    return std::chrono::duration<double,std::milli>(Clock::now()-start).count();
}

void emit_profile(std::ostream& out, unsigned sample, std::string_view phase,
                  const profiling::Counters& counters) {
    for (std::size_t i=0;i<counters.size();++i) {
        const auto& c=counters[i];
        out<<sample<<','<<phase<<','<<profiling::names[i]<<','<<c.calls<<','<<c.inclusive_ns<<','
           <<c.exclusive_ns<<','<<c.work<<'\n';
    }
}

void density(std::ostream& out,std::ostream& attribution,unsigned sample,unsigned count,
             unsigned brood_per_carer,bool dense,unsigned replicate) {
    // ENGINEERING_FIXTURE. Caregivers share their real initial shelter and colony.
    WorldRuntime world({6332,7},7,{{-.02,-.01,-.02},{.28,.01,.14},.08,.002},limits());
    world.configure_long_term();
    world.configure_social();
    SpeciesCareProfile profile;
    profile.local_retrieval=true;
    world.configure_biology(profile);
    const auto colony=world.seed_colony();
    const auto physiology_config=physiology();
    const IndividualCareProfile worker_profile{CareContext::Worker,{}};
    std::vector<AntRef> caregivers;
    caregivers.reserve(count);
    for (unsigned i=0;i<count;++i) {
        const PositionM destination{.00025+(dense?0.0:static_cast<double>(i%16)*.014),
                                    0,dense?0.0:static_cast<double>(i/16)*.014};
        const auto worker=world.seed_ant(colony,{});
        caregivers.push_back(worker);
        world.enable_physiology(worker,{{},physiology_config.energy_capacity_nj,physiology_config.hydration_capacity_ug,0},
                                physiology_config);
        world.enable_brood_care(worker,worker_profile);
        world.pause_brood_care(worker);
        world.submit({worker,{4000},ActionKind::Move,{},destination,0});
        for (unsigned j=0;j<brood_per_carer;++j)
            world.seed_ant(colony,{{destination.x+.0005,0,destination.z},LifeStage::Larva});
    }
    world.advance_to({4000});
    for (const auto worker:caregivers) {
        require(world.query_ant(worker)->position.x>=.00025,"density placement move did not commit");
        world.enable_brood_care(worker,worker_profile);
    }
    const auto before=world.summary().committed_events;
    profiling::reset();
    auto start=Clock::now();
    world.advance_to({64000});
    const auto advance_ms=ms(start);
    const auto advance=profiling::snapshot();
    profiling::reset();
    start=Clock::now();
    const auto checkpoint=world.checkpoint();
    const auto checkpoint_ms=ms(start);
    const auto encode=profiling::snapshot();
    WorldRuntime restored({1,1},0,{},limits());
    profiling::reset();
    start=Clock::now();
    restored.restore(checkpoint);
    const auto restore_ms=ms(start);
    const auto restore=profiling::snapshot();
    require(restored.checkpoint()==checkpoint,"density restore differs");
    conserved(world);
    const auto snapshot=world.snapshot();
    const auto history=world.committed_events();
    std::array<std::size_t,static_cast<std::size_t>(FactKind::BroodMoved)+1> sizes{};
    std::uint64_t journal_bytes=0,opportunities=0,initial=0,starts=0,terminals=0,handled=0,moves=0,transfers=0;
    for (const auto& event:history) {
        auto& size=sizes.at(static_cast<std::size_t>(event.kind));
        if (!size) size=encode_event(event).size();
        journal_bytes+=size;
        if (event.kind==FactKind::NutritionTransferred) ++transfers;
        if (event.kind==FactKind::BroodMoved) ++moves;
        if (event.kind!=FactKind::BiologicalObservation) continue;
        const auto o=event.observation;
        if (o.phase==ObservationPhase::Opportunity) {
            ++opportunities;
            if (event.time==SimTime{4001}) ++initial;
        } else if (o.phase==ObservationPhase::Started) ++starts;
        else if (o.phase==ObservationPhase::Completed || o.phase==ObservationPhase::Interrupted) {
            ++terminals;
            if (o.phase==ObservationPhase::Completed && o.act>=CareAct::InspectBrood && o.act<=CareAct::FeedBrood) ++handled;
        }
    }
    const auto expected=dense?count*(count-1+count*brood_per_carer):count*brood_per_carer;
    require(initial==expected,"density opportunity set differs");
    out<<sample<<','<<count<<','<<count*brood_per_carer<<','<<brood_per_carer<<','<<(dense?"dense":"dispersed")
       <<','<<replicate<<','<<(replicate==0)<<",7,60000,"<<std::setprecision(17)
       <<advance_ms<<','<<checkpoint_ms<<','<<restore_ms<<','<<initial<<','<<opportunities<<','<<starts<<','<<terminals
       <<','<<handled<<','<<moves<<','<<transfers<<','<<history.size()-before<<','<<history.size()<<','<<journal_bytes
       <<','<<checkpoint.size()<<','<<snapshot.state_hash<<','<<snapshot.trace_hash<<",1\n";
    emit_profile(attribution,sample,"advance",advance);
    emit_profile(attribution,sample,"encode",encode);
    emit_profile(attribution,sample,"restore",restore);
    out.flush();
    attribution.flush();
}
}

int main(int argc,char** argv) {
    try {
        if (argc!=2) throw std::invalid_argument("usage: antworld_s6_3_3_2_density OUTPUT_DIR");
        const std::filesystem::path dir=argv[1];
        if (!std::filesystem::create_directories(dir)) throw std::invalid_argument("density output already exists");
        std::ofstream samples(dir/"samples.csv",std::ios::binary),profile(dir/"profile.csv",std::ios::binary);
        samples.exceptions(std::ios::badbit|std::ios::failbit);
        profile.exceptions(std::ios::badbit|std::ios::failbit);
        samples<<"sample,caregivers,brood,brood_per_caregiver,layout,replicate,warmup,seed,sim_ms,advance_ms,checkpoint_ms,restore_ms,"
                 "initial_opportunities,opportunities,started,terminals,completed_brood_handling,brood_moves,nutrition_transfers,advance_facts,"
                 "journal_facts,encoded_history_bytes,checkpoint_bytes,state_hash,trace_hash,restore_equal\n";
        profile<<"sample,phase,category,calls,inclusive_ns,exclusive_ns,work\n";
        unsigned sample=0;
        for (unsigned count:{1U,8U,32U,128U})
            for (unsigned brood_per_carer:{1U,4U})
                for (bool dense:{true,false})
                    for (unsigned replicate=0;replicate<4;++replicate)
                        density(samples,profile,sample++,count,brood_per_carer,dense,replicate);
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
