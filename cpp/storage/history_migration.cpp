#include "schema.hpp"
#include "segmented_analytics.hpp"

namespace antworld::storage {
using namespace detail;
namespace {
void require_legacy(sqlite3* db) {
    Statement version(db,"PRAGMA user_version"),application(db,"PRAGMA application_id");
    require(version.row() && version.number(0)==1 && application.row() && application.number(0)==1096234835,
            "migration requires an AntWorld v1 database");
}

void backup(sqlite3* source,const std::filesystem::path& path) {
    sqlite3* raw=nullptr;
    const auto filename=path.u8string();
    const auto code=sqlite3_open_v2(reinterpret_cast<const char*>(filename.c_str()),&raw,
                                   SQLITE_OPEN_CREATE|SQLITE_OPEN_READWRITE|SQLITE_OPEN_FULLMUTEX,nullptr);
    Database destination(raw);
    check(code,destination.get());
    {
        Statement empty(destination.get(),"SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'");
        require(empty.row() && empty.number(0)==0,"migration target is not an empty shadow");
    }
    auto* operation=sqlite3_backup_init(destination.get(),"main",source,"main");
    require(operation,"cannot initialize SQLite shadow backup");
    const auto copied=sqlite3_backup_step(operation,-1);
    const auto closed=sqlite3_backup_finish(operation);
    check(copied,destination.get());
    check(closed,destination.get());
    require(copied==SQLITE_DONE,"SQLite shadow backup was incomplete");
}

struct RetainedFrame {
    SaveToken token;
    SimTime time;
    std::vector<std::uint8_t> frame;
};

std::vector<WorldId> worlds(sqlite3* db) {
    Statement q(db,"SELECT world FROM worlds ORDER BY world");
    std::vector<WorldId> result(0);
    while (q.row()) result.push_back(WorldId::parse(q.text(0)));
    return result;
}

std::vector<std::uint64_t> generations(sqlite3* db,WorldId world) {
    Statement q(db,"SELECT generation FROM generations WHERE world=? ORDER BY generation");
    q.text(1,world.str());
    std::vector<std::uint64_t> result(0);
    while (q.row()) result.push_back(q.u64(0));
    require(!result.empty(),"world has no retained source generations");
    return result;
}

void write_converted(sqlite3* db,WorldId world,std::span<RetainedFrame> frames,const WorldRuntime& authority,
                     std::size_t byte_limit) {
    const auto capture=authority.capture_history();
    auto previous=Digest{};
    auto cursor=EventId{};
    Statement update(db,"UPDATE generations SET checkpoint_hash=?,checkpoint=? WHERE world=? AND generation=?");
    for (auto& state:frames) {
        const auto tail=append_blocks(db,world,capture,cursor,{state.token.cursor});
        cursor={state.token.cursor};
        state.token.checkpoint_hash=hash(state.frame);
        update.u64(1,state.token.checkpoint_hash); update.blob(2,state.frame);
        update.text(3,world.str()); update.u64(4,state.token.generation);
        update.done(); update.reset();
        put_anchor(db,state.token,state.time,state.frame,previous,tail);
        previous=read_anchor(db,world,state.token.generation,byte_limit).digest;
    }
    const auto& tip=frames.back().token;
    require(tip.cursor==capture.size(),"retained tip does not cover the legacy journal");
    require_history_prefix(db,world,capture,{tip.cursor},block_tail(db,world,{tip.cursor}));
    Statement manifest(db,"UPDATE worlds SET checkpoint_hash=?,prefix_hash=? WHERE world=?");
    manifest.u64(1,tip.checkpoint_hash); manifest.u64(2,0); manifest.text(3,world.str()); manifest.done();
    const auto edits=authority.geometry_edits();
    put_geometry(db,world,authority.geometry_snapshot(),edits,{});
    Statement identities(db,"UPDATE individuals SET seeded=(SELECT kind=? FROM events "
                            "WHERE events.world=individuals.world AND events.id=individuals.created_event) "
                            "WHERE world=?");
    identities.number(1,static_cast<std::int64_t>(FactKind::AntSeeded));
    identities.text(2,world.str()); identities.done();
}
} // namespace

void Store::migrate_legacy(const std::filesystem::path& source,const std::filesystem::path& shadow,
                           RuntimeLimits limits) {
    require(std::filesystem::is_regular_file(source),"legacy source must exist");
    for (const auto* suffix:{"","-wal","-shm","-journal"}) {
        auto candidate=shadow;
        candidate+=suffix;
        require(!std::filesystem::exists(std::filesystem::symlink_status(candidate)),"shadow path must be unused");
    }
    auto original=open_readonly(source);
    Transaction source_snapshot(original.get(),false);
    require_legacy(original.get());
    backup(original.get(),shadow);
    Store destination(shadow,limits);
    auto* db=destination.impl_->db;
    const auto ids=worlds(db);
    {
        Transaction convert(db);
        exec(db,segmented_tables);
        for (const auto world:ids) {
            const auto current=destination.latest(world);
            const auto retained=generations(db,world);
            require(current && retained.back()==current->generation,"legacy generation/manifest mismatch");
            std::vector<RetainedFrame> frames(0);
            std::optional<LoadedWorld> authority;
            for (const auto generation:retained) {
                auto loaded=destination.load_legacy(world,generation);
                frames.push_back({loaded.token,loaded.world.summary().now,loaded.world.checkpoint_frame()});
                if (generation==retained.back()) authority=std::move(loaded);
            }
            write_converted(db,world,frames,authority->world,limits.checkpoint_bytes);
        }
        exec(db,finalize_segmented_schema);
        convert.commit();
    }
    destination.impl_->format=StoreFormat::Segmented;
    // Compare reconstructed Core bytes against the same source snapshot used
    // for backup. This also independently validates derived indexes at the tip.
    for (const auto world:ids) for (const auto generation:generations(original.get(),world)) {
        auto recovered=destination.load(world,generation);
        Statement old(original.get(),"SELECT revision,cursor,checkpoint FROM generations WHERE world=? AND generation=?");
        old.text(1,world.str()); old.u64(2,generation);
        require(old.row() && old.u64(0)==recovered.token.revision && old.u64(1)==recovered.token.cursor &&
                old.blob(2,limits.checkpoint_bytes)==recovered.world.checkpoint(),
                "migrated checkpoint or canonical facts differ from source");
    }
    source_snapshot.commit();
    exec(db,"VACUUM");
    destination.checkpoint_wal();
}
} // namespace antworld::storage
