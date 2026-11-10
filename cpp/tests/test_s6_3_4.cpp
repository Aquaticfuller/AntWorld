#include "antworld/storage/live_history.hpp"
#include "../storage/event_block.hpp"
#include "s4_fixture.hpp"
#include "sqlite3.h"
#include <cstdlib>
#include <future>
#include <iostream>
#include <tuple>

using namespace antworld;
using namespace antworld::storage;
using s4_fixture::require;
namespace {
constexpr WorldId diagnostic_id{634,7};

template<class Operation> void rejects(Operation operation,const char* message) {
    try { operation(); } catch (const std::exception&) { return; }
    throw std::runtime_error(message);
}

void sql(const std::filesystem::path& path,const char* statement) {
    sqlite3* db=nullptr;
    const auto filename=path.u8string();
    const auto status=sqlite3_open(reinterpret_cast<const char*>(filename.c_str()),&db);
    const auto code=status==SQLITE_OK?sqlite3_exec(db,statement,nullptr,nullptr,nullptr):status;
    const std::string error=sqlite3_errmsg(db);
    sqlite3_close(db);
    if (code!=SQLITE_OK) throw std::runtime_error(error);
}

WorldRuntime diagnostic(WorldId id=diagnostic_id,unsigned n=4100) {
    WorldRuntime world(id,7);
    const auto colony=world.seed_colony();
    world.seed_ant(colony,{});
    for (unsigned i=1;i<=n;++i)
        world.schedule({{i},Phase::Environment,0,0,i,DiagnosticAction::DrawRandom});
    return world;
}

void same_history(const Store& store,const WorldRuntime& world) {
    const auto id=world.summary().world;
    auto after=EventId{};
    for (;;) {
        const auto expected=world.events_after(after,333);
        const auto durable=store.history({id,after,{},{INT64_MAX},{},{},333});
        require(expected.size()==durable.size(),"history page count differs");
        if (expected.empty()) break;
        for (std::size_t i=0;i<expected.size();++i)
            require(encode_event(expected[i])==encode_event(durable[i].fact),"canonical history bytes differ");
        after=expected.back().id;
    }
}

void codec() {
    using namespace antworld::storage::detail;
    constexpr Digest abc{0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
                         0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
    constexpr std::array<std::uint8_t,3> text{'a','b','c'};
    require(sha256(std::span{text}.first(1),std::span{text}.last(2))==abc,"SHA-256 test vector mismatch");
    auto world=diagnostic();
    world.advance_to({4100});
    const auto events=world.events_after({},4096);
    const auto first=seal_block(events,{});
    const auto tail=world.events_after({4096},4096);
    const auto second=seal_block(tail,first.header.digest);
    const auto a=inspect_block(first.bytes),b=inspect_block(second.bytes);
    require(a.last.value==4096 && b.first.value==4097 && b.previous==a.digest && a.previous==Digest{},
            "canonical block count or chain mismatch");
    require(read_block(first.bytes,a)==events && read_block(second.bytes,b)==tail,"block roundtrip differs");
    auto corrupt=second.bytes;
    corrupt.back()^=1;
    rejects([&]{(void)inspect_block(corrupt);},"codec accepted damaged compressed bytes");
    corrupt=first.bytes;
    corrupt[64]=255;
    corrupt[65]=255;
    corrupt[66]=255;
    corrupt[67]=255;
    rejects([&]{(void)inspect_block(corrupt);},"codec accepted an oversized declared output");
    auto reverse=tail;
    std::swap(reverse[0],reverse[1]);
    rejects([&]{(void)seal_block(reverse,a.digest);},"codec accepted reordered facts");
    std::cout<<"codec_blocks=2, canonical_records="<<world.summary().committed_events<<"\n";
}

void live(const std::filesystem::path& root) {
    const auto path=root/"live.sqlite";
    Store reader(path,{},StoreFormat::Segmented);
    LiveHistoryWriter writer(path);
    auto w=diagnostic();
    const auto initial=w.checkpoint();
    require(writer.try_submit(w),"initial save admission failed");
    const auto first=writer.finish(w).token;
    require(!w.unpublished_history() && reader.load(diagnostic_id).world.checkpoint()==initial,
            "initial acknowledgement changed Core");
    w.advance_to({4098});
    const auto cut=w.checkpoint();
    std::promise<void> entered,proceed;
    auto after_blocks=entered.get_future();
    auto continuation=proceed.get_future().share();
    struct Release {
        std::promise<void>& signal;
        ~Release() { try {signal.set_value();} catch (...) {} }
    } release{proceed};
    SaveOptions hold;
    hold.fault_hook=[&](SaveStage stage) {
        if (stage==SaveStage::AfterBlocks) { entered.set_value(); continuation.wait(); }
    };
    require(writer.try_submit(w,first,hold),"second save admission failed");
    require(after_blocks.wait_for(std::chrono::seconds(5))==std::future_status::ready,"worker did not stage blocks");
    w.advance_to({4100});
    require(!writer.try_submit(w,first) && reader.latest(diagnostic_id)==first,
            "queued save or staged blocks escaped the admission boundary");
    proceed.set_value();
    const auto second=writer.finish(w).token;
    require(w.unpublished_history()==2 && reader.load(diagnostic_id).world.checkpoint()==cut,
            "acknowledgement consumed facts after the captured cut");

    const auto full=w.checkpoint();
    SaveOptions failure;
    failure.fault_hook=[](SaveStage stage) {
        if (stage==SaveStage::AfterManifest) throw std::runtime_error("injected after staging manifest");
    };
    require(writer.try_submit(w,second,failure),"faulted capture was not admitted");
    rejects([&]{(void)writer.finish(w);},"faulted writer acknowledged a partial publication");
    require(reader.latest(diagnostic_id)==second && w.checkpoint()==full && w.unpublished_history()==2,
            "failed save lost facts or advanced manifest");

    // Lose the acknowledgement, then retry the identical published cut with its original parent.
    const auto third=reader.save(w,second);
    require(writer.try_submit(w,second) && writer.finish(w).token==third && !w.unpublished_history(),
            "lost acknowledgement duplicated the publication");
    const auto resumed=reader.recover(diagnostic_id,first.generation,third.generation);
    require(resumed.world.checkpoint()==full,"anchor plus subsequent facts recovered a different world");
    same_history(reader,w);
    w.schedule({{4101},Phase::Environment,0,0,1,DiagnosticAction::Record});
    require(writer.try_submit(w,third),"same-time zero-fact publication not admitted");
    const auto fourth=writer.finish(w).token;
    require(fourth.generation==third.generation+1 && fourth.cursor==third.cursor &&
            reader.load(diagnostic_id).world.checkpoint()==w.checkpoint(),"zero-fact frame lost pending work");
    auto other=diagnostic({634,8},2);
    other.advance_to({2});
    require(writer.try_submit(other),"independent world admission failed");
    const auto isolated=writer.finish(other).token;
    require(isolated.cursor==4 && reader.latest(diagnostic_id)==fourth,"world-local IDs collided");
    same_history(reader,other);
    auto conflicting=diagnostic();
    conflicting.advance_to({4100});
    conflicting.schedule({{4101},Phase::Environment,0,0,2,DiagnosticAction::Record});
    rejects([&]{(void)reader.save(conflicting,third);},"divergent same-time retry overwrote a cut");
    std::cout<<"initial, staged visibility, post-cut facts, rollback, idempotency, same-time frame and isolation verified\n";
}

void pressure(const std::filesystem::path& root) {
    auto w=diagnostic(diagnostic_id,4);
    LiveHistoryWriter writer(root/"bounded.sqlite",{},LiveHistoryLimits{3,1024*1024});
    writer.bind(w);
    w.advance_to({1});
    const auto before=w.checkpoint();
    rejects([&]{w.advance_to({2});},"unpublished budget accepted an extra fact");
    require(w.checkpoint()==before,"backpressure failed to roll back the transaction");
    require(writer.try_submit(w),"bounded queue did not admit allowed cut");
    const auto first=writer.finish(w).token;
    w.advance_to({4});
    require(writer.try_submit(w,first),"released capacity did not admit continuation");
    const auto final=writer.finish(w).token;
    require(final.cursor==6 && !w.unpublished_history(),"backpressure skipped a real event");
    auto other=diagnostic({634,9},1);
    LiveHistoryWriter tiny(root/"tiny.sqlite",{},LiveHistoryLimits{3,1});
    const auto unchanged=other.checkpoint();
    rejects([&]{(void)tiny.try_submit(other);},"byte budget admitted an oversized capture");
    require(!tiny.pending() && other.checkpoint()==unchanged,"rejected immutable capture changed state");
    std::cout<<"hot fact limit, queue byte limit and exact retry verified\n";
}

void compare_metrics(const Store& legacy,const Store& converted,const WorldRuntime& world) {
    const auto state=world.summary();
    const SimTime end{state.now.milliseconds+60001};
    for (const auto& def:metric_definitions()) for (const auto owner:{ColonyId{},world.colonies().front().id}) {
        if (def.kind==MetricKind::Flow)
            require(legacy.flow_total(state.world,owner,def.id,{},{state.now.milliseconds+1})==
                    converted.flow_total(state.world,owner,def.id,{},{state.now.milliseconds+1}),"migrated flow differs");
        else {
            const auto a=legacy.series(state.world,owner,def.id,{},end);
            const auto b=converted.series(state.world,owner,def.id,{},end);
            require(a.size()==b.size(),"migrated gauge count differs");
            for (std::size_t i=0;i<a.size();++i)
                require(std::tie(a[i].time,a[i].generation,a[i].revision,a[i].value,a[i].cursor)==
                        std::tie(b[i].time,b[i].generation,b[i].revision,b[i].value,b[i].cursor),"migrated gauge differs");
        }
        const auto a=legacy.buckets(state.world,owner,def.id,{},end);
        const auto b=converted.buckets(state.world,owner,def.id,{},end);
        require(a.size()==b.size(),"migrated bucket count differs");
        for (std::size_t i=0;i<a.size();++i) {
            const auto key=[](const MetricBucket& p) {
                return std::tie(p.begin,p.end,p.samples,p.sum,p.minimum,p.maximum,p.last,p.first_event,p.last_event);
            };
            require(key(a[i])==key(b[i]),"migrated bucket evidence differs");
        }
    }
}

void migration(const std::filesystem::path& root) {
    const auto source=root/"v1.sqlite",shadow=root/"shadow.sqlite";
    Store legacy(source);
    s4_fixture::Fixture f;
    auto& w=f.world;
    const auto id=w.summary().world;
    const auto command=PlaceFoodCommand{id,{17,UINT64_MAX},w.query_ant(f.worker)->position,{50,20,30,0}};
    auto first=legacy.save(w);
    const auto receipt=legacy.place_food(w,first,command);
    f.dig();
    w.advance_to({100});
    const SoilParcelRef parcel{id,w.soil_parcels().front().id};
    w.submit_soil({f.worker,{300},SoilAction::Drop,{},parcel,1});
    w.schedule({{500},Phase::Environment,0,0,2,DiagnosticAction::DrawRandom});
    require(w.query_parcel(parcel)->state==ParcelState::Carried,"soil fixture lacks actual load");
    const auto held=w.checkpoint();
    const auto middle=legacy.save(w,first);
    w.advance_to({500});
    const auto final=legacy.save(w,middle);
    Store::migrate_legacy(source,shadow);
    Store converted(shadow);
    require(legacy.format()==StoreFormat::Legacy && converted.format()==StoreFormat::Segmented,
            "migration replaced or mislabeled legacy source");
    require(legacy.latest(id)==final && converted.latest(id)->generation==final.generation,
            "migration changed source or generation identity");
    auto carried=converted.load(id,middle.generation);
    require(carried.world.checkpoint()==held && carried.world.query_parcel(parcel)->state==ParcelState::Carried &&
            carried.world.pending_events().size()==2,"migration lost soil, pending work or exact checkpoint");
    carried.world.advance_to({500});
    s4_fixture::balanced(carried.world);
    require(carried.world.checkpoint()==w.checkpoint() && converted.recover(id,middle.generation,final.generation)
            .world.checkpoint()==w.checkpoint(),"historical soil recovery differs");
    require(converted.load(id).world.place_food(command)==receipt,"migration lost command identity");
    same_history(converted,w);
    compare_metrics(legacy,converted,w);
    const auto filter=HistoryFilter{id,{},{1},{301},f.worker.id,{},10};
    const auto before=legacy.history(filter),after=converted.history(filter);
    require(before.size()==after.size() && !after.empty(),"filtered history count differs");
    for (std::size_t i=0;i<before.size();++i)
        require(encode_event(before[i].fact)==encode_event(after[i].fact) && before[i].geometry_edit==after[i].geometry_edit &&
                before[i].parcel==after[i].parcel && before[i].related==after[i].related,"filtered history evidence differs");
    require(!converted.history({id,{},{},{500},EntityId{}, {},10}).size(),"zero actor is not an individual");
    sql(shadow,"DELETE FROM buckets; DELETE FROM individuals; DELETE FROM geometry_evidence; DELETE FROM receipts;");
    rejects([&]{(void)converted.load(id);},"corrupt indexes were silently accepted");
    converted.rebuild_history_indexes(id);
    require(converted.load(id).world.checkpoint()==w.checkpoint(),"rebuild changed source facts or state");
    compare_metrics(legacy,converted,w);
    rejects([&]{Store::migrate_legacy(source,shadow);},"migration overwrote an existing shadow");
    std::cout<<"legacy source, retained cuts, soil, queued work, metrics and rebuilt indexes verified\n";
}

void corrupt(const std::filesystem::path& root) {
    const std::array controls{
        "UPDATE fact_blocks SET envelope=zeroblob(length(envelope)) WHERE first_id='0000000000000001'",
        "DELETE FROM fact_blocks WHERE first_id='0000000000000001'",
        "UPDATE fact_blocks SET envelope=(SELECT envelope FROM fact_blocks ORDER BY last_id DESC LIMIT 1) WHERE first_id='0000000000000001'",
        "UPDATE fact_blocks SET digest=zeroblob(32) WHERE first_id='0000000000000001'",
        "UPDATE history_anchors SET parent=zeroblob(32) WHERE generation='0000000000000002'",
        "DELETE FROM history_anchors WHERE generation='0000000000000001'",
        "UPDATE worlds SET quantum_m=1000.0"
    };
    for (std::size_t i=0;i<controls.size();++i) {
        const auto path=root/("corrupt-"+std::to_string(i)+".sqlite");
        Store store(path,{},StoreFormat::Segmented);
        auto w=diagnostic();
        const auto first=store.save(w);
        w.advance_to({4100});
        store.save(w,first);
        sql(path,controls[i]);
        rejects([&]{(void)store.load(diagnostic_id);},"damaged block or anchor passed recovery");
        rejects([&]{store.rebuild_history_indexes(diagnostic_id);},"index rebuild accepted damaged authority");
        std::cout<<"rejected_corruption_case="<<i<<"\n";
    }
}

void crash(std::string_view mode,const std::filesystem::path& path) {
    Store store(path,{},StoreFormat::Segmented);
    auto w=diagnostic(diagnostic_id,30);
    if (mode=="SEED") {
        store.save(w);
        store.checkpoint_wal();
    } else if (mode.starts_with("EXIT_")) {
        const auto target=static_cast<SaveStage>(std::stoi(std::string(mode.substr(5))));
        const auto first=*store.latest(diagnostic_id);
        w.advance_to({30});
        SaveOptions fault;
        fault.fault_hook=[&](SaveStage stage) { if (stage==target) std::_Exit(77); };
        store.save(w,first,fault);
        throw std::runtime_error("crash boundary was never reached");
    } else {
        require(mode=="OLD" || mode=="NEW","unknown crash recovery");
        if (mode=="NEW") w.advance_to({30});
        require(store.load(diagnostic_id).world.checkpoint()==w.checkpoint(),"crash published a mixed generation");
        same_history(store,w);
        std::cout<<"process_recovery="<<mode<<", cursor="<<w.summary().committed_events<<"\n";
    }
}
} // namespace

int main(int argc,char** argv) {
    try {
        require(argc==3,"usage: antworld_s6_3_4_tests MODE PATH");
        const std::string_view mode=argv[1];
        const std::filesystem::path path=argv[2];
        if (mode=="CODEC") codec();
        else if (mode=="SEED" || mode.starts_with("EXIT_") || mode=="OLD" || mode=="NEW")
            crash(mode,path);
        else {
            require(std::filesystem::create_directories(path),"test output already exists");
            if (mode=="LIVE") live(path);
            else if (mode=="PRESSURE") pressure(path);
            else if (mode=="MIGRATION") migration(path);
            else if (mode=="CORRUPT") corrupt(path);
            else throw std::invalid_argument("unknown history test");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr<<error.what()<<'\n';
        return 1;
    }
}
