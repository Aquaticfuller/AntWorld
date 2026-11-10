#include "s6_3_3_3_fixture.hpp"
#include "antworld/core/profiling.hpp"
#include "antworld/storage/store.hpp"
#include "process_memory.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>

using namespace antworld;
using namespace antworld::closure;

namespace {
using Clock=std::chrono::steady_clock;
double ms(Clock::time_point start) {
    return std::chrono::duration<double,std::milli>(Clock::now()-start).count();
}

void profile(std::ostream& out,unsigned sample,std::string_view phase) {
    const auto counters=profiling::snapshot();
    for (std::size_t i=0;i<counters.size();++i) {
        const auto& c=counters[i];
        out<<sample<<','<<phase<<','<<profiling::names[i]<<','<<c.calls<<','<<c.inclusive_ns<<','
           <<c.exclusive_ns<<','<<c.work<<'\n';
    }
    profiling::reset();
}

void encode_record(std::vector<std::uint8_t>& stream,const WorldEvent& event) {
    const auto bytes=encode_event(event);
    require(bytes.size()<=UINT32_MAX,"canonical record too large");
    for (unsigned i=0;i<4;++i)
        stream.push_back(static_cast<std::uint8_t>(bytes.size()>>(8*i)));
    stream.insert(stream.end(),bytes.begin(),bytes.end());
}

void run(const std::filesystem::path& dir,std::ostream& samples,std::ostream& profiles,
         unsigned sample,unsigned n,bool dense,bool integrated,unsigned replicate) {
    const std::string mode=integrated?"integrated":"timed";
    const std::string layout=dense?"dense":"spread";
    const auto label=mode+"_"+layout+"_"+std::to_string(n);
    profiling::reset();
    auto clock=Clock::now();
    WorldRuntime w({6333,7},7,{{-.02,-.02,-.02},{.24,.02,.24},.08,.002},limits());
    w.configure_long_term();
    BehaviorConfig forage;
    forage.trails_enabled=false;
    w.configure_surface({{0,0,0},213,213,.001},{},forage);
    w.configure_social(day_social());
    w.configure_biology(timed_care(integrated));
    const auto colony=w.seed_colony();
    const auto p=day_physiology();
    for (unsigned i=0;i<n;++i) {
        const auto worker=w.seed_ant(colony,{});
        w.enable_physiology(worker,adult,p);
        if (integrated) w.set_autonomy(worker,true);
        else w.enable_brood_care(worker,{CareContext::Worker,{}});
    }
    for (unsigned i=0;i<2*n;++i) {
        const auto x=dense?.001:.001+static_cast<double>(i%16)*.014;
        const auto z=dense?0:static_cast<double>(i/16)*.014;
        const auto brood=w.seed_ant(colony,{{x,0,z},LifeStage::Larva});
        w.enable_physiology(brood,larva,p);
    }
    balanced_supply(w,n,{.005,0,0});
    const auto setup_ms=ms(clock);
    profile(profiles,sample,"setup");
    const auto end=integrated?2*day:600000;
    clock=Clock::now();
    w.advance_to({end});
    const auto advance_ms=ms(clock);
    profile(profiles,sample,"advance");
    clock=Clock::now();
    const auto checkpoint=w.checkpoint();
    const auto checkpoint_ms=ms(clock);
    profile(profiles,sample,"checkpoint");
    clock=Clock::now();
    {
        WorldRuntime restored({1,1},0,{},limits());
        restored.restore(checkpoint);
        const auto restore_ms=ms(clock);
        profile(profiles,sample,"restore");
        require(restored.checkpoint()==checkpoint,"in-memory density restore differs");
        profiling::reset();
        storage::Store store(dir/(label+"_"+std::to_string(replicate)+".sqlite"),limits());
        clock=Clock::now();
        const auto token=store.save(w);
        store.checkpoint_wal();
        const auto save_ms=ms(clock);
        profile(profiles,sample,"sqlite_save");
        clock=Clock::now();
        auto durable=store.load(w.summary().world);
        const auto load_ms=ms(clock);
        profile(profiles,sample,"sqlite_load");
        require(durable.token==token && durable.world.checkpoint()==checkpoint,"durable density restore differs");
        const auto db_bytes=store.database_bytes();
        restored=WorldRuntime({1,1},0,{},limits());
        durable.world=WorldRuntime({1,1},0,{},limits());
        profiling::reset();
        s6_3_fixture::conserved(w);
        const auto facts=w.committed_events();
        const auto state=w.snapshot();
        std::vector<std::uint8_t> stream;
        stream.reserve(facts.size()*224);
        std::uint64_t opportunities=0,starts=0,completions=0,transfers=0,placements=0,switches=0;
        clock=Clock::now();
        for (const auto& e:facts) {
            encode_record(stream,e);
            if (e.kind==FactKind::NutritionTransferred) ++transfers;
            if (e.kind==FactKind::BehaviorChanged) ++switches;
            if (e.kind!=FactKind::BiologicalObservation) continue;
            const auto phase=e.observation.phase;
            if (phase==ObservationPhase::Opportunity) ++opportunities;
            if (phase==ObservationPhase::Started) ++starts;
            if (phase==ObservationPhase::Completed) {
                ++completions;
                if (e.observation.act==CareAct::PlaceBrood) ++placements;
            }
        }
        const auto journal_ms=ms(clock);
        if (replicate==1) {
            std::ofstream archive(dir/(label+".facts"),std::ios::binary);
            archive.exceptions(std::ios::badbit|std::ios::failbit);
            archive.write(reinterpret_cast<const char*>(stream.data()),static_cast<std::streamsize>(stream.size()));
        }
        const auto [rss,peak]=antworld::performance::memory();
        samples<<sample<<','<<mode<<','<<layout<<','<<n<<','<<2*n<<','<<replicate<<','<<(replicate==0)<<",7,"<<end
               <<','<<setup_ms<<','<<advance_ms<<','<<checkpoint_ms<<','<<restore_ms<<','<<save_ms<<','<<load_ms<<','
               <<journal_ms<<','<<opportunities<<','<<starts<<','<<completions<<','<<transfers<<','<<placements<<','
               <<switches<<','<<facts.size()<<','<<stream.size()<<','<<checkpoint.size()<<','<<db_bytes<<','<<rss
               <<','<<peak<<','<<state.state_hash<<','<<state.trace_hash<<",1,1,"<<profiling::enabled<<'\n';
        samples.flush();
        profiles.flush();
        std::cout<<label<<' '<<replicate<<" committed "<<facts.size()<<" facts\n"<<std::flush;
    }
}

void persistence_replay(const std::filesystem::path& output,const std::filesystem::path& reference) {
    std::ofstream samples(output/"persistence.csv",std::ios::binary);
    samples.exceptions(std::ios::badbit|std::ios::failbit);
    samples<<std::setprecision(17)<<"case,source_replica,facts,state_hash,trace_hash,prepare_ms,generation_ms,"
             "history_ms,analytics_ms,commit_ms,wal_flush_ms,sqlite_bytes,restore_equal\n";
    const auto elapsed=[](Clock::time_point a,Clock::time_point b) {
        return std::chrono::duration<double,std::milli>(b-a).count();
    };
    for (std::string_view mode:{"timed","integrated"})
        for (std::string_view layout:{"dense","spread"})
            for (unsigned n:{8U,32U,128U}) {
                const auto label=std::string(mode)+"_"+std::string(layout)+"_"+std::to_string(n);
                const auto path=reference/(label+"_1.sqlite");
                require(std::filesystem::is_regular_file(path),"missing first measured density database");
                storage::Store original(path,limits());
                auto world=original.load({6333,7});
                storage::Store copy(output/(label+".sqlite"),limits());
                std::array<Clock::time_point,5> boundaries{};
                storage::SaveOptions options;
                options.fault_hook=[&](storage::SaveStage stage) {
                    boundaries.at(static_cast<std::size_t>(stage))=Clock::now();
                };
                const auto start=Clock::now();
                const auto token=copy.save(world.world,{},options);
                const auto flush=Clock::now();
                copy.checkpoint_wal();
                const auto end=Clock::now();
                require(boundaries.front()>=start && boundaries.back()<=flush &&
                        std::is_sorted(boundaries.begin(),boundaries.end()),"save stages out of order");
                const auto state=world.world.snapshot();
                const auto loaded=copy.load({6333,7});
                require(world.token==token && loaded.token==token &&
                        loaded.world.checkpoint()==world.world.checkpoint(),"persistent replay differs");
                samples<<label<<",1,"<<state.committed_events<<','<<state.state_hash<<','<<state.trace_hash<<','
                       <<elapsed(start,boundaries.front());
                for (std::size_t i=1;i<boundaries.size();++i) samples<<','<<elapsed(boundaries[i-1],boundaries[i]);
                samples<<','<<elapsed(flush,end)<<','<<copy.database_bytes()<<",1\n";
                samples.flush();
            }
}
} // namespace

int main(int argc,char** argv) {
    try {
        const bool replay=argc==4 && std::string_view(argv[2])=="--sqlite-replay";
        if (argc!=2 && !replay)
            throw std::invalid_argument("usage: antworld_s6_3_3_3_density OUTPUT_DIR [--sqlite-replay REFERENCE_DIR]");
        const std::filesystem::path dir=argv[1];
        if (!std::filesystem::create_directories(dir)) throw std::invalid_argument("density output already exists");
        if (replay) { persistence_replay(dir,argv[3]); return 0; }
        std::ofstream samples(dir/"samples.csv",std::ios::binary),profiles(dir/"profile.csv",std::ios::binary);
        samples.exceptions(std::ios::badbit|std::ios::failbit);
        profiles.exceptions(std::ios::badbit|std::ios::failbit);
        samples<<std::setprecision(17)<<"sample,mode,layout,workers,larvae,replicate,warmup,seed,sim_ms,setup_ms,advance_ms,checkpoint_ms,restore_ms,sqlite_save_ms,sqlite_load_ms,journal_encode_ms,opportunities,started,completed,transfers,placements,switches,facts,journal_bytes,checkpoint_bytes,sqlite_bytes,rss_bytes,process_peak_bytes,state_hash,trace_hash,restore_equal,conserved,profiled\n";
        profiles<<"sample,phase,category,calls,inclusive_ns,exclusive_ns,work\n";
        unsigned sample=0;
        for (bool integrated:{false,true})
            for (unsigned n:{8U,32U,128U})
                for (bool dense:{true,false})
                    for (unsigned replicate=0;replicate<4;++replicate)
                        run(dir,samples,profiles,sample++,n,dense,integrated,replicate);
        return 0;
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
