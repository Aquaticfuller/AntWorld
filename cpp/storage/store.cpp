#include "schema.hpp"
#include "segmented_archive.hpp"
#include <algorithm>

namespace antworld::storage {
using namespace detail;
Store::Store(const std::filesystem::path &path,RuntimeLimits limits,StoreFormat preference) : impl_(std::make_unique<Impl>()) {
    impl_->path = std::filesystem::absolute(path);
    impl_->limits = limits;
    const auto filename = path.u8string();
    check(sqlite3_open_v2(reinterpret_cast<const char *>(filename.c_str()), &impl_->db,
                          SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX, nullptr),
          impl_->db);
    auto *db = impl_->db;
    check(sqlite3_busy_timeout(db, 5000), db);
    int version{}, application{};
    {
        Statement q(db, "PRAGMA user_version");
        require(q.row(), "missing database version");
        version = static_cast<int>(q.number(0));
    }
    {
        Statement q(db, "PRAGMA application_id");
        require(q.row(), "missing application ID");
        application = static_cast<int>(q.number(0));
    }
    if (version == 0 && application == 0) {
        {
            Statement q(db,"SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'");
            require(q.row() && q.number(0)==0,"refusing to initialize a foreign database");
        }
        Transaction tx(db);
        exec(db, schema);
        if (preference==StoreFormat::Segmented) {
            exec(db,segmented_tables);
            exec(db,finalize_segmented_schema);
        }
        impl_->format=preference;
        tx.commit();
    } else {
        require((version==1 || version==2) && application==1096234835,
                "unsupported AntWorld database version/application");
        impl_->format=version==2?StoreFormat::Segmented:StoreFormat::Legacy;
    }
    exec(db, "PRAGMA foreign_keys=ON; PRAGMA trusted_schema=OFF; PRAGMA synchronous=FULL; PRAGMA "
             "cache_size=-4096;");
    {
        Statement q(db, "PRAGMA journal_mode=WAL");
        require(q.row() && q.text(0) == "wal", "persistent storage requires local WAL support");
    }
    {
        Statement q(db, "PRAGMA synchronous");
        require(q.row() && q.number(0) == 2, "FULL synchronization unavailable");
    }
    check(sqlite3_db_config(db, SQLITE_DBCONFIG_DEFENSIVE, 1, nullptr), db);
}
Store::~Store() = default;
Store::Store(Store &&) noexcept = default;
Store &Store::operator=(Store &&) noexcept = default;
const char *Store::sqlite_version() { return sqlite3_libversion(); }
StoreFormat Store::format() const noexcept { return impl_->format; }
std::optional<SaveToken> Store::latest(WorldId world) const {
    Statement q(impl_->db, "SELECT generation,revision,cursor,checkpoint_hash FROM worlds WHERE world=?");
    q.text(1, world.str());
    if (!q.row())
        return {};
    return token(q, world);
}
SaveToken Store::save(const WorldRuntime &w, std::optional<SaveToken> expected, const SaveOptions &options) {
    if (format()==StoreFormat::Segmented) return save_segmented(capture_frame(w),expected,options);
    if (w.founding_profile()) throw std::invalid_argument("F1 requires the versioned segmented store");
    if (impl_->requires_recovery)
        throw RecoveryRequired("reopen and recover after an uncertain database commit");
    if (!options.retained_generations || options.retained_generations > 64)
        throw std::invalid_argument("invalid generation retention");
    const auto bytes = w.checkpoint();
    const auto observation = observe(w);
    const auto events = w.committed_events();
    const auto summary = w.summary();
    const auto geometry = w.geometry_snapshot();
    if (bytes.size() > impl_->limits.checkpoint_bytes || events.size() > impl_->limits.committed_events)
        throw std::length_error("storage host budget exceeded");
    std::map<EventId, GeometryEdit> edits;
    for (const auto &e : w.geometry_edits())
        edits.emplace(e.event, e);
    const auto blob_hash = hash(bytes);
    auto hook = [&](SaveStage stage) {
        if (options.fault_hook)
            options.fault_hook(stage);
    };
    hook(SaveStage::BeforeTransaction);
    Transaction tx(impl_->db);
    const auto previous = latest(summary.world);
    require(previous == expected, "stale/missing durable generation token");
    std::uint64_t old_cursor = 0, previous_prefix = UINT64_C(14695981039346656037);
    std::int64_t previous_time = -1;
    if (previous) {
        require(summary.revision >= previous->revision && summary.committed_events >= previous->cursor,
                "stale world state");
        Statement old(impl_->db, "SELECT time_ms,prefix_hash,seed FROM worlds WHERE world=?");
        old.text(1, summary.world.str());
        require(old.row(), "missing metadata");
        require(summary.now.milliseconds >= old.number(0) && summary.seed == old.u64(2),
                "world timeline or seed conflict");
        previous_prefix = old.u64(1);
        old_cursor = previous->cursor;
        previous_time = old.number(0);
    }
    auto prefix = UINT64_C(14695981039346656037);
    if (!old_cursor)
        require(previous_prefix == prefix, "invalid empty history prefix");
    for (const auto &e : events) {
        prefix = hash(encode_event(e), prefix);
        if (e.id.value == old_cursor)
            require(prefix == previous_prefix, "divergent committed history prefix");
    }
    if (previous && summary.revision == previous->revision && summary.now.milliseconds == previous_time) {
        require(blob_hash == previous->checkpoint_hash, "same revision has divergent continuation state");
        tx.commit();
        return *previous;
    }
    const auto generation = previous ? checked_add(previous->generation, 1) : 1;
    const SaveToken result{summary.world, generation, summary.revision, summary.committed_events, blob_hash};
    Statement meta(impl_->db, "INSERT INTO worlds VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(world) DO UPDATE SET "
                              "generation=excluded.generation,revision=excluded.revision,time_ms=excluded."
                              "time_ms,cursor=excluded.cursor,checkpoint_hash=excluded.checkpoint_hash,"
                              "prefix_hash=excluded.prefix_hash,quantum_m=excluded.quantum_m");
    meta.text(1, summary.world.str());
    meta.u64(2, summary.seed);
    meta.u64(3, generation);
    meta.u64(4, summary.revision);
    meta.number(5, summary.now.milliseconds);
    meta.u64(6, summary.committed_events);
    meta.u64(7, blob_hash);
    meta.u64(8, prefix);
    meta.real(9, observation.geometry_quantum_m);
    meta.done();
    Statement checkpoint(impl_->db, "INSERT INTO generations VALUES(?,?,?,?,?,?,?)");
    checkpoint.text(1, summary.world.str());
    checkpoint.u64(2, generation);
    checkpoint.u64(3, summary.revision);
    checkpoint.number(4, summary.now.milliseconds);
    checkpoint.u64(5, summary.committed_events);
    checkpoint.u64(6, blob_hash);
    checkpoint.blob(7, bytes);
    checkpoint.done();
    hook(SaveStage::AfterCheckpoint);
    Statement fact(impl_->db, "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)");
    Statement flow(impl_->db, "INSERT INTO flows VALUES(?,?,?,?,?,?)");
    for (const auto &e : events) {
        if (e.id.value <= old_cursor)
            continue;
        const auto edit = edits.find(e.id);
        const auto *linked = edit == edits.end() ? nullptr : &edit->second;
        const auto related = e.kind==FactKind::BiologicalObservation ? e.observation.target.value :
            e.kind == FactKind::NutritionTransferred || e.kind==FactKind::AntBorn || e.kind==FactKind::BroodMoved ? e.payload : 0;
        const bool soil = e.kind >= FactKind::SoilExcavated && e.kind <= FactKind::SoilFilled;
        fact.text(1, e.world.str());
        fact.u64(2, e.id.value);
        fact.number(3, e.time.milliseconds);
        fact.number(4, static_cast<std::int64_t>(e.kind));
        fact.u64(5, e.actor.value);
        fact.u64(6, related);
        fact.u64(7, e.colony.value);
        fact.u64(8, e.resource.value);
        fact.u64(9, e.source.value);
        fact.u64(10, e.revision);
        fact.u64(11, linked ? linked->id.value : 0);
        fact.u64(12, soil ? e.payload : 0);
        fact.blob(13, encode_event(e));
        fact.done();
        fact.reset();
        for (auto individual_id : {e.actor.value, related})
            if (individual_id) {
                Statement put(impl_->db, "INSERT INTO participants VALUES(?,?,?)");
                put.text(1, e.world.str());
                put.u64(2, individual_id);
                put.u64(3, e.id.value);
                put.done();
            }
        if (e.kind == FactKind::AntSeeded || e.kind==FactKind::AntBorn) {
            const auto ant = w.query_ant({e.world, e.actor});
            require(ant.has_value(), "seeded identity missing");
            Statement put(impl_->db, "INSERT INTO individuals VALUES(?,?,?,?,?,?,?,?,?,?,?,?)");
            put.text(1, e.world.str());
            put.u64(2, e.actor.value);
            put.u64(3, e.colony.value);
            put.number(4, static_cast<std::int64_t>(ant->caste));
            put.number(5, static_cast<std::int64_t>(e.stage));
            put.number(6, static_cast<std::int64_t>(e.stage));
            put.number(7, e.time.milliseconds);
            put.u64(8, e.id.value);
            put.u64(9, e.id.value);
            put.u64(10, 0);
            put.number(11, -1);
            put.u64(12, 0);
            put.done();
        } else if (e.actor.value) {
            Statement put(impl_->db, "UPDATE individuals SET last_event=? WHERE world=? AND id=?");
            put.u64(1, e.id.value);
            put.text(2, e.world.str());
            put.u64(3, e.actor.value);
            put.done();
            if (e.kind == FactKind::StageChanged || e.kind == FactKind::AntDied) {
                Statement stage(impl_->db,
                                "UPDATE individuals SET stage=?,death_event=?,death_ms=?,death_cause=? WHERE "
                                "world=? AND id=?");
                stage.number(1, static_cast<std::int64_t>(e.stage));
                stage.u64(2, e.kind == FactKind::AntDied ? e.id.value : 0);
                stage.number(3, e.kind == FactKind::AntDied ? e.time.milliseconds : -1);
                stage.u64(4, e.kind == FactKind::AntDied ? e.payload : 0);
                stage.text(5, e.world.str());
                stage.u64(6, e.actor.value);
                stage.done();
            }
        }
        if (related) {
            Statement put(impl_->db, "UPDATE individuals SET last_event=? WHERE world=? AND id=?");
            put.u64(1, e.id.value);
            put.text(2, e.world.str());
            put.u64(3, related);
            put.done();
        }
        for (const auto &value : contributions(e, geometry, linked)) {
            flow.text(1, e.world.str());
            flow.u64(2, value.owner.value);
            flow.number(3, static_cast<std::int64_t>(value.metric));
            flow.number(4, e.time.milliseconds);
            flow.u64(5, e.id.value);
            flow.u64(6, value.value);
            flow.done();
            flow.reset();
            persist_bucket(impl_->db, e.world, value, e.time, e.id);
        }
    }
    for (const auto &receipt : w.command_receipts()) {
        Statement put(impl_->db, "INSERT OR IGNORE INTO receipts VALUES(?,?,?,?)");
        put.text(1, summary.world.str());
        put.text(2, hex64(receipt.command.id.high) + hex64(receipt.command.id.low));
        put.u64(3, receipt.event.value);
        put.u64(4, receipt.resource.value);
        put.done();
    }
    hook(SaveStage::AfterHistory);
    Statement sample(impl_->db, "INSERT INTO samples VALUES(?,?,?,?,?,?,?,?,?)");
    auto digest = observation_header(observation);
    for (const auto &value : observation.values) {
        digest = observation_value(digest, value);
        sample.text(1, summary.world.str());
        sample.u64(2, generation);
        sample.u64(3, value.owner.value);
        sample.number(4, static_cast<std::int64_t>(value.metric));
        sample.number(5, summary.now.milliseconds);
        sample.u64(6, summary.revision);
        sample.u64(7, summary.committed_events);
        sample.u64(8, value.value);
        sample.number(9, metric_version);
        sample.done();
        sample.reset();
        persist_bucket(impl_->db, summary.world, value, summary.now, {summary.committed_events});
    }
    Statement anchor(impl_->db, "INSERT INTO observations VALUES(?,?,?,?,?,?,?)");
    anchor.text(1, summary.world.str());
    anchor.u64(2, generation);
    anchor.number(3, summary.now.milliseconds);
    anchor.u64(4, summary.revision);
    anchor.u64(5, summary.committed_events);
    anchor.real(6, observation.geometry_quantum_m);
    anchor.u64(7, digest);
    anchor.done();
    Statement prune(impl_->db, "DELETE FROM generations WHERE world=? AND generation NOT IN (SELECT "
                               "generation FROM generations WHERE world=? ORDER BY generation DESC LIMIT ?)");
    prune.text(1, summary.world.str());
    prune.text(2, summary.world.str());
    prune.number(3, static_cast<std::int64_t>(options.retained_generations));
    prune.done();
    hook(SaveStage::BeforeCommit);
    try {
        tx.commit();
    } catch (const std::exception &error) {
        impl_->requires_recovery = true;
        throw RecoveryRequired(std::string("commit outcome requires reopening/recovery: ") + error.what());
    }
    // Failure after commit cannot be reported as a rollback. Crash hooks terminate the process.
    try {
        hook(SaveStage::AfterCommit);
    } catch (...) {
    }
    return result;
}
CommandReceipt Store::place_food(WorldRuntime &world, SaveToken &saved, const PlaceFoodCommand &command,
                                 const SaveOptions &options) {
    require(saved.world == world.summary().world && command.world == saved.world, "command world mismatch");
    WorldRuntime candidate(command.world, 0, {}, impl_->limits);
    candidate.restore(world.checkpoint());
    const auto receipt = candidate.place_food(command);
    const auto committed = save(candidate, saved, options);
    world = std::move(candidate);
    saved = committed;
    return receipt;
}
void Store::checkpoint_wal() {
    check(sqlite3_wal_checkpoint_v2(impl_->db, nullptr, SQLITE_CHECKPOINT_TRUNCATE, nullptr, nullptr),
          impl_->db);
}
std::uint64_t Store::database_bytes() const {
    std::uint64_t total = 0;
    for (const auto &suffix : {std::string{}, std::string{"-wal"}, std::string{"-shm"}}) {
        auto p = impl_->path;
        p += suffix;
        std::error_code error;
        if (std::filesystem::exists(p, error))
            total = checked_add(total, std::filesystem::file_size(p));
    }
    return total;
}
std::uint64_t Store::sqlite_memory_bytes() const { return static_cast<std::uint64_t>(sqlite3_memory_used()); }
} // namespace antworld::storage
