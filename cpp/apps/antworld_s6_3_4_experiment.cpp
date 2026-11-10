#include "antworld/storage/live_history.hpp"
#include "process_memory.hpp"
#include "s6_3_1_fixture.hpp"
#include "s6_3_3_3_fixture.hpp"
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <thread>

using namespace antworld;
using namespace antworld::storage;
using closure::require;
namespace {
using Clock=std::chrono::steady_clock;
constexpr auto day=s6_3_fixture::day;
constexpr auto hour=s6_3_fixture::hour;
double elapsed(Clock::time_point start) {
    return std::chrono::duration<double,std::milli>(Clock::now()-start).count();
}

std::ofstream output(const std::filesystem::path& path) {
    std::ofstream stream(path,std::ios::binary);
    stream.exceptions(std::ios::badbit|std::ios::failbit);
    stream<<std::setprecision(17);
    return stream;
}

std::uint64_t wal_bytes(std::filesystem::path path) {
    path+="-wal";
    return std::filesystem::exists(path)?std::filesystem::file_size(path):0;
}

struct Runner {
    std::filesystem::path path;
    RuntimeLimits limits;
    Store store;
    LiveHistoryWriter writer;
    std::ofstream cuts,summary;
    std::optional<SaveToken> previous;
    double advance_ms{},query_ms{},scoped_ms{},restore_ms{};
    std::uint64_t wal_peak{};

    explicit Runner(const std::filesystem::path& root,RuntimeLimits policy)
        :path(root/"world.sqlite"),limits(policy),store(path,limits,StoreFormat::Segmented),writer(path,limits),
         cuts(output(root/"cuts.csv")),summary(output(root/"sample.csv")) {
        cuts<<"generation,time_ms,new_facts,cursor,checkpoint_ms,capture_ms,foreground_ms,background_ms,"
              "ready_wait_ms,ack_ms,wal_flush_ms,restore_ms,frame_bytes,captured_bytes,blocks,raw_bytes,"
              "packed_bytes,database_bytes,wal_before_flush_bytes,rss_bytes,process_peak_bytes\n";
        summary<<"case,seed,workers,continuous,sim_ms,facts,state_hash,trace_hash,opportunities,births,emerged,"
                 "deaths,birth_days,death_days,advance_ms,restore_ms,history_page_ms,scoped_history_ms,"
                 "online_rss_bytes,online_peak_bytes,explicit_export_peak_bytes,blocks,raw_bytes,packed_bytes,"
                 "frames,all_frame_bytes,database_bytes,peak_wal_before_flush_bytes,exact\n";
    }

    void advance(WorldRuntime& world,SimTime time) {
        const auto start=Clock::now();
        world.advance_to(time);
        advance_ms+=elapsed(start);
    }

    void publish(WorldRuntime& world,bool restore) {
        const auto old=previous?previous->cursor:0;
        const auto start=Clock::now();
        require(writer.try_submit(world,previous),"benchmark publication was not admitted");
        const auto foreground=elapsed(start);
        auto phase=Clock::now();
        while (!writer.ready()) std::this_thread::sleep_for(std::chrono::milliseconds(1));
        const auto wait=elapsed(phase);
        phase=Clock::now();
        const auto published=writer.finish(world);
        const auto acknowledge=elapsed(phase);
        previous=published.token;
        require(!world.unpublished_history(),"acknowledged benchmark history remains hot");
        const auto pending_wal=wal_bytes(path);
        wal_peak=std::max(wal_peak,pending_wal);
        phase=Clock::now();
        store.checkpoint_wal();
        const auto flush=elapsed(phase);
        auto loading=-1.0;
        if (restore) {
            phase=Clock::now();
            auto recovered=store.load(previous->world);
            loading=elapsed(phase);
            restore_ms=loading;
            require(recovered.token==*previous && recovered.world.checkpoint_frame()==world.checkpoint_frame(),
                    "validated restore did not reproduce captured state");
            world=std::move(recovered.world);
            writer.bind(world);
        }
        const auto stats=store.history_storage(previous->world);
        const auto [rss,peak]=performance::memory();
        cuts<<previous->generation<<','<<world.summary().now.milliseconds<<','<<previous->cursor-old<<','
            <<previous->cursor<<','<<published.checkpoint_ms<<','<<published.capture_ms<<','<<foreground<<','
            <<published.background_ms<<','<<wait<<','<<acknowledge<<','<<flush<<','<<loading<<','
            <<published.frame_bytes<<','<<published.captured_bytes<<','<<stats.blocks<<','<<stats.raw_bytes<<','
            <<stats.packed_bytes<<','<<store.database_bytes()<<','<<pending_wal<<','<<rss<<','<<peak<<'\n'<<std::flush;
    }

    void queries(const WorldRuntime& world) {
        const auto state=world.summary();
        auto phase=Clock::now();
        const auto first=state.committed_events>256?state.committed_events-256:0;
        const auto page=store.history({state.world,{first},{},{INT64_MAX},{},{},256});
        query_ms=elapsed(phase);
        require(page.size()==state.committed_events-first,"indexed page has an incorrect number of facts");
        const auto ants=world.ant_states();
        const std::optional<EntityId> actor=ants.empty()?std::nullopt:std::optional{ants.front().id};
        const auto kind=ants.empty()?FactKind::Diagnostic:FactKind::BiologicalObservation;
        phase=Clock::now();
        const auto scoped=store.history({state.world,{},{state.now.milliseconds/2},{INT64_MAX},actor,kind,256});
        scoped_ms=elapsed(phase);
        for (const auto& item:scoped)
            require(item.fact.kind==kind && item.fact.time.milliseconds>=state.now.milliseconds/2,
                    "scoped query returned unrelated facts");
    }
};

void record(Runner& runner,std::string_view label,std::uint64_t seed,unsigned workers,bool continuous,
            const WorldRuntime& world,const WorldRuntime& reference,std::pair<std::uint64_t,std::uint64_t> online) {
    closure::require(world.checkpoint_frame()==reference.checkpoint_frame(),"published continuation differs from direct reference");
    s6_3_fixture::conserved(world);
    const auto [rss,peak]=online;
    const auto snapshot=world.snapshot();
    const auto target=reference.snapshot();
    require(snapshot==target,"published state or trace differs from direct reference");
    std::uint64_t opportunities=0,births=0,emerged=0,deaths=0;
    std::set<std::int64_t> birth_days,death_days;
    EventId after{};
    while (after.value<snapshot.committed_events) {
        const auto a=world.events_after(after,4096);
        const auto b=reference.events_after(after,4096);
        require(a.size()==b.size() && !a.empty(),"published event page size differs");
        for (std::size_t i=0;i<a.size();++i) {
            const auto& fact=a[i];
            require(encode_event(fact)==encode_event(b[i]),"published canonical event differs from direct reference");
            if (fact.kind==FactKind::BiologicalObservation && fact.observation.phase==ObservationPhase::Opportunity)
                ++opportunities;
            if (fact.kind==FactKind::AntBorn) { ++births; birth_days.insert(fact.time.milliseconds/day); }
            if (fact.kind==FactKind::AntDied) { ++deaths; death_days.insert(fact.time.milliseconds/day); }
            if (fact.kind==FactKind::StageChanged && fact.stage==LifeStage::Adult) ++emerged;
        }
        after=a.back().id;
    }
    const auto stats=runner.store.history_storage(snapshot.world);
    const auto exported_peak=performance::memory().second;
    runner.summary<<label<<','<<seed<<','<<workers<<','<<continuous<<','<<snapshot.now.milliseconds<<','
        <<snapshot.committed_events<<','<<snapshot.state_hash<<','<<snapshot.trace_hash<<','<<opportunities<<','
        <<births<<','<<emerged<<','<<deaths<<','<<birth_days.size()<<','<<death_days.size()<<','
        <<runner.advance_ms<<','<<runner.restore_ms<<','<<runner.query_ms<<','<<runner.scoped_ms<<','<<rss<<','<<peak<<','
        <<exported_peak<<','<<stats.blocks<<','<<stats.raw_bytes<<','<<stats.packed_bytes<<','<<stats.frames<<','
        <<stats.frame_bytes<<','<<runner.store.database_bytes()<<','<<runner.wal_peak<<",1\n";
}

// Capture the online peak before constructing the unbounded reference runtime
// or exporting a legacy checkpoint for the equality audit.
template<class CreateReference>
void complete(Runner& runner,std::string_view label,std::uint64_t seed,unsigned workers,bool continuous,
              const WorldRuntime& world,CreateReference create_reference) {
    runner.queries(world);
    const auto online=performance::memory();
    auto reference=create_reference();
    record(runner,label,seed,workers,continuous,world,reference,online);
}

void diagnostic_batch(WorldRuntime& world,std::uint64_t from,std::uint64_t end) {
    for (auto i=from+1;i<=end;++i)
        world.schedule({{static_cast<std::int64_t>(i)},Phase::Environment,0,0,i,DiagnosticAction::DrawRandom});
}

void diagnostic(Runner& runner,std::string_view label,std::uint64_t facts) {
    auto create=[] { return WorldRuntime({634,7},7,{},closure::limits()); };
    auto w=create();
    runner.writer.bind(w);
    for (std::uint64_t base=0;base<facts;base+=10000) {
        diagnostic_batch(w,base,base+10000);
        runner.advance(w,{static_cast<std::int64_t>(base+10000)});
        runner.publish(w,false);
    }
    runner.advance(w,{static_cast<std::int64_t>(facts+1)});
    runner.publish(w,true);
    complete(runner,label,7,0,false,w,[&] {
        auto direct=create();
        for (std::uint64_t base=0;base<facts;base+=10000) {
            diagnostic_batch(direct,base,base+10000);
            direct.advance_to({static_cast<std::int64_t>(base+10000)});
        }
        direct.advance_to({static_cast<std::int64_t>(facts+1)});
        return direct;
    });
}

void care(Runner& runner,std::string_view label,bool integrated,bool continuous) {
    auto w=closure::density_world(128,true,integrated,continuous);
    const SimTime end{integrated?2*day:600000};
    runner.writer.bind(w);
    runner.advance(w,end);
    runner.publish(w,true);
    complete(runner,label,7,128,continuous,w,[&] {
        auto direct=closure::density_world(128,true,integrated,continuous);
        direct.advance_to(end);
        return direct;
    });
}

void ecology(Runner& runner,std::string_view label,std::uint64_t seed,unsigned workers,bool food,bool integrated) {
    auto create=[&] {
        WorldRuntime world({6333,seed},seed,{{-.04,-.02,-.02},{.04,.02,.02},.08,.002,true},runner.limits);
        (void)closure::prepare_ecology(world,workers,"underground",food,integrated);
        return world;
    };
    auto w=create();
    runner.writer.bind(w);
    for (auto t=6*hour;t<=10*day;t+=6*hour) runner.advance(w,{t});
    runner.publish(w,true);
    for (auto t=10*day+5*hour;t<21*day;t+=5*hour+12007) runner.advance(w,{t});
    runner.advance(w,{21*day});
    runner.publish(w,true);
    complete(runner,label,seed,workers,true,w,[&] {
        auto direct=create();
        direct.advance_to({21*day});
        return direct;
    });
}

void long_ecology(Runner& runner,std::uint64_t seed) {
    auto create=[&] {
        s6_3_1_fixture::Controls controls;
        controls.positive=true;
        controls.reserve_mode=1;
        LongTermConfig policy;
        policy.protein_recycling=true;
        policy.demand_feedback=true;
        policy.post_intake_contact=true;
        policy.complete_depot_visits=true;
        s6_3_1_fixture::World fixture(seed,32,"balanced",false,policy,6,false,controls);
        return std::move(fixture.world);
    };
    auto w=create();
    runner.writer.bind(w);
    for (std::int64_t t=day;t<=180*day;t+=day) {
        runner.advance(w,{t});
        if (t%(10*day)==0) runner.publish(w,t==90*day || t==180*day);
    }
    complete(runner,"long",seed,32,false,w,[&] {
        auto direct=create();
        direct.advance_to({180*day});
        return direct;
    });
}
} // namespace

int main(int argc,char** argv) {
    try {
        if (argc!=4) throw std::invalid_argument("usage: antworld_s6_3_4_experiment OUTPUT CASE SEED");
        const std::filesystem::path root=argv[1];
        const std::string_view label=argv[2];
        const auto seed=static_cast<std::uint64_t>(std::stoull(argv[3]));
        require(std::filesystem::create_directories(root),"experiment output already exists");
        Runner runner(root,closure::limits());
        if (label=="timed-legacy" || label=="timed-continuous" || label=="integrated-legacy" ||
            label=="integrated-continuous") {
            require(seed==7,"care density seed differs from protocol");
            care(runner,label,label.starts_with("integrated"),label.ends_with("continuous"));
        } else if (label=="facts-10000" || label=="facts-100000" || label=="facts-1000000") {
            require(seed==7,"diagnostic seed differs from protocol");
            diagnostic(runner,label,std::stoull(std::string(label.substr(6))));
        } else if (label=="long") {
            require(seed>=1 && seed<=3,"long ecological seed differs from protocol");
            long_ecology(runner,seed);
        } else if (label=="ecology-4-balanced-care" || label=="ecology-16-empty-care" ||
                   label=="ecology-4-balanced-control" || label=="ecology-16-empty-control") {
            require(seed==7 || seed==19 || seed==43,"R1 ecological seed differs from protocol");
            const bool funded=label.starts_with("ecology-4-");
            ecology(runner,label,seed,funded?4U:16U,funded,label.ends_with("-care"));
        } else throw std::invalid_argument("unknown frozen history experiment");
        std::cout<<"PASS "<<label<<' '<<seed<<'\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr<<error.what()<<'\n';
        return 1;
    }
}
