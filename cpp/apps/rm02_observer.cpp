#include "rm02_observer.hpp"

#include "history_digest.hpp"
#include "sqlite_internal.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <stdexcept>
#include <utility>

namespace antworld::rm02 {
namespace {
using storage::detail::Digest;
using storage::detail::Statement;
using storage::detail::Transaction;
using storage::detail::check;
using storage::detail::exec;
using storage::detail::require;
using storage::detail::sha256;
using Bytes = std::span<const std::uint8_t>;

constexpr auto schema = R"sql(
    PRAGMA application_id = 1096241714;
    PRAGMA user_version = 2;
    CREATE TABLE manifest(id INTEGER PRIMARY KEY CHECK(id=1), identity TEXT NOT NULL, origin INTEGER NOT NULL);
    CREATE TABLE cuts(
        seq INTEGER PRIMARY KEY, sim_ms INTEGER NOT NULL, revision INTEGER NOT NULL, cursor INTEGER NOT NULL,
        rng TEXT NOT NULL, from_cursor INTEGER NOT NULL, examined INTEGER NOT NULL, selected INTEGER NOT NULL,
        records INTEGER NOT NULL, dropped INTEGER NOT NULL, pending INTEGER NOT NULL, neighbors INTEGER NOT NULL,
        payload BLOB NOT NULL, digest BLOB NOT NULL
    );
    CREATE TABLE anchors(seq INTEGER PRIMARY KEY REFERENCES cuts(seq), checkpoint_sha256 BLOB NOT NULL);
)sql";

struct Row {
    std::array<std::uint8_t, 512> bytes{};
    std::size_t size{};
    void put(std::uint64_t value) {
        require(size + 8 <= bytes.size(), "observer row exceeds fixed capacity");
        for (unsigned shift = 0; shift < 64; shift += 8)
            bytes[size++] = static_cast<std::uint8_t>(value >> shift);
    }
    void mass(FoodMass value) {
        for (auto component : value.components())
            put(component);
    }
    void position(PositionM value) {
        put(std::bit_cast<std::uint64_t>(value.x));
        put(std::bit_cast<std::uint64_t>(value.y));
        put(std::bit_cast<std::uint64_t>(value.z));
    }
    [[nodiscard]] Bytes view() const { return Bytes(bytes).first(size); }
};

std::int64_t signed_sql(std::uint64_t value) {
    if (value > static_cast<std::uint64_t>(INT64_MAX))
        throw std::overflow_error("observer integer exceeds SQLite range");
    return static_cast<std::int64_t>(value);
}

std::uint64_t positive_sql(const Statement& row, int column) {
    const auto value = row.number(column);
    require(value >= 0, "negative observer metadata");
    return static_cast<std::uint64_t>(value);
}

Boundary boundary(const WorldSnapshot& state) {
    require(state.next_event_id && state.next_event_id - 1 == state.committed_events,
            "observer requires contiguous committed event identities");
    return {state.now, state.revision, state.next_event_id - 1, state.rng_state};
}

Bytes string_bytes(const std::string& value) {
    return {reinterpret_cast<const std::uint8_t*>(value.data()), value.size()};
}

void validate_plan(Plan& plan) {
    const auto simple = [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-';
    };
    require(!plan.lineage.empty() && plan.lineage.size() <= 128 &&
            std::all_of(plan.lineage.begin(), plan.lineage.end(), simple),
            "invalid observer lineage");
    std::sort(plan.focal.begin(), plan.focal.end());
    require(plan.focal.size() <= focal_limit &&
            std::adjacent_find(plan.focal.begin(), plan.focal.end()) == plan.focal.end() &&
            (plan.focal.empty() || plan.focal.front().value != 0) &&
            plan.payload_limit && plan.payload_limit <= cut_limit, "invalid observer scope or capacity");
}

std::string manifest_identity(const WorldSnapshot& state, const Plan& plan) {
    auto text = std::string("RM02-SIDECAR-1\n") + plan.lineage + '\n' + state.world.str() + '\n' +
        std::to_string(state.seed) + '\n' + std::to_string(plan.all_relevant) + '\n' +
        std::to_string(plan.pending) + '\n' + std::to_string(plan.start_at_current) + '\n' +
        std::to_string(plan.neighbor_actor.value) + '\n' + std::to_string(plan.payload_limit) + '\n';
    for (const auto id : plan.focal)
        text += std::to_string(id.value) + '\n';
    return text;
}

Digest first_digest(const std::string& identity, std::uint64_t origin) {
    Row row;
    row.put(origin);
    return sha256(string_bytes(identity), row.view());
}

Digest cut_digest(const Cut& cut, std::uint64_t seq, const Digest& prior, Bytes stored) {
    Row header;
    for (const auto byte : prior)
        header.bytes[header.size++] = byte;
    for (const auto value : {seq, cut.world.high, cut.world.low,
            static_cast<std::uint64_t>(cut.end.time.milliseconds), cut.end.revision, cut.end.cursor,
            cut.end.rng, cut.from, cut.examined, cut.selected, cut.records, cut.dropped,
            static_cast<std::uint64_t>(cut.pending), static_cast<std::uint64_t>(cut.neighbors)})
        header.put(value);
    return sha256(header.view(), stored);
}

// A zero prefix reserves the sparse encoding outside the raw record-tag space.
// Each following group has a presence mask and the original nonzero bytes.
std::vector<std::uint8_t> pack_cut(Bytes raw) {
    constexpr std::size_t maximum_compressed_input = 400 * 1024;
    if (raw.empty() || raw.size() > maximum_compressed_input)
        return {};
    const auto original = raw.size();
    std::vector<std::uint8_t> packed(5 + original + (original + 7) / 8);
    for (unsigned i = 0; i < 4; ++i)
        packed[i + 1] = static_cast<std::uint8_t>(raw.size() >> (8 * i));
    auto* to = packed.data() + 5;
    const auto group = [&to](Bytes bytes) {
        auto* mask_at = to++;
        unsigned mask{};
        for (std::size_t i = 0; i < bytes.size(); ++i) {
            const unsigned present = bytes[i] != 0;
            *to = bytes[i];
            to += present;
            mask |= present << i;
        }
        *mask_at = static_cast<std::uint8_t>(mask);
    };
    while (raw.size() >= 8) {
        group(raw.first<8>());
        raw = raw.subspan(8);
    }
    if (!raw.empty())
        group(raw);
    const auto size = static_cast<std::size_t>(to - packed.data());
    if (size >= original)
        return {};
    packed.resize(size);
    return packed;
}

void append(Cut& cut, Record type, Bytes record, std::size_t cap) {
    constexpr std::size_t prefix = 5;
    const auto length = prefix + record.size();
    if (length > cap - cut.payload.size()) {
        ++cut.dropped;
        return;
    }
    cut.payload.push_back(static_cast<std::uint8_t>(type));
    for (unsigned shift = 0; shift < 32; shift += 8)
        cut.payload.push_back(static_cast<std::uint8_t>(record.size() >> shift));
    cut.payload.insert(cut.payload.end(), record.begin(), record.end());
    ++cut.records;
}

bool relevant(const WorldEvent& fact) {
    switch (fact.kind) {
    case FactKind::AntSeeded:
    case FactKind::FoodSeeded:
    case FactKind::FoodCollected:
    case FactKind::FoodDelivered:
    case FactKind::FoodPlaced:
    case FactKind::ActionRejected:
    case FactKind::StageChanged:
    case FactKind::AntDied:
    case FactKind::PhysiologyEnabled:
    case FactKind::PhysiologyUpdated:
    case FactKind::BehaviorChanged:
    case FactKind::NutritionDecision:
    case FactKind::CargoIngested:
    case FactKind::NestIngested:
    case FactKind::NutritionTransferred:
    case FactKind::SoilExcavated:
    case FactKind::AutonomyChanged:
    case FactKind::AutonomyDecision:
    case FactKind::ReproductionEnabled:
    case FactKind::ReproductionAttempt:
    case FactKind::AntBorn:
    case FactKind::ResourceCycleConfigured:
    case FactKind::ResourceReleased:
    case FactKind::ProteinRecycled:
        return true;
    case FactKind::BiologicalObservation:
        return fact.observation.act == CareAct::FeedBrood || fact.observation.act == CareAct::TransferNutrition ||
            fact.observation.act == CareAct::IngestFood ||
            (fact.observation.act == CareAct::Inactive && fact.observation.phase == ObservationPhase::Selected);
    default:
        return false;
    }
}

bool included(const Plan& plan, EntityId id) {
    return std::binary_search(plan.focal.begin(), plan.focal.end(), id);
}

bool projected(const Plan& plan, const WorldEvent& fact) {
    if (!relevant(fact))
        return false;
    if (plan.all_relevant || included(plan, fact.actor))
        return true;
    switch (fact.kind) {
    case FactKind::NutritionTransferred:
    case FactKind::AntBorn:
        return included(plan, {fact.payload});
    case FactKind::BiologicalObservation:
        return included(plan, fact.observation.target);
    default:
        return false;
    }
}

void capture_state(Cut& cut, const WorldRuntime& world, EntityId id, std::size_t cap) {
    const AntRef ref{cut.world, id};
    const auto ant = world.query_ant(ref);
    const auto p = world.query_physiology(ref);
    Row row;
    row.put(id.value);
    row.put(ant.has_value());
    row.put(p.has_value());
    if (ant) {
        row.put(ant->colony.value);
        row.put(static_cast<std::uint64_t>(ant->born_at.milliseconds));
        row.put(static_cast<std::uint64_t>(ant->stage));
        row.put(static_cast<std::uint64_t>(ant->caste));
        row.position(ant->position);
        row.mass(ant->carried_food);
    }
    if (p) {
        row.mass(p->crop);
        for (const auto value : {p->mother.value, p->body_energy_nj, p->hydration_ug, p->tissue_protein_ug,
                 p->oxidized_carbs_ug, p->lost_water_ug, p->dissipated_energy_nj, p->exported_energy_nj,
                 static_cast<std::uint64_t>(p->behavior), static_cast<std::uint64_t>(p->death_cause),
                 static_cast<std::uint64_t>(p->next_absorption.milliseconds),
                 static_cast<std::uint64_t>(p->stage_progress.milliseconds),
                 p->physiology_event.value, p->behavior_event.value, p->decisions,
                 p->config.carbohydrate_yield_nj_per_ug})
            row.put(value);
    }
    append(cut, Record::State, row.view(), cap);
}

void capture_ledger(Cut& cut, const WorldRuntime& world, const WorldSnapshot& state, std::size_t cap) {
    const auto n = world.nutrition_snapshot();
    require(n.introduced == n.accounted && n.body_energy_nj <= n.energy_input_nj &&
            n.energy_input_nj - n.body_energy_nj == n.dissipated_energy_nj, "observer found a Core ledger imbalance");
    Row row;
    for (const auto mass : {n.introduced, n.accounted, n.crop, state.food_ledger.available,
             state.food_ledger.carried, state.food_ledger.stored})
        row.mass(mass);
    for (const auto value : {n.hydration_ug, n.tissue_protein_ug, n.oxidized_carbs_ug, n.lost_water_ug,
             n.energy_input_nj, n.body_energy_nj, n.dissipated_energy_nj, n.individuals,
             state.living_ants, state.ant_count})
        row.put(value);
    append(cut, Record::Ledger, row.view(), cap);
}

void capture_pending(Cut& cut, const WorldRuntime& world, const WorldSnapshot& state, const Plan& plan) {
    if (!plan.pending)
        return;
    if (state.pending_events > pending_limit) {
        cut.pending = Coverage::Limit;
        return;
    }
    cut.pending = Coverage::Complete;
    for (const auto& e : world.pending_events()) {
        if (e.kind != ScheduledEvent::Kind::Trophallaxis ||
            (!plan.all_relevant && !included(plan, e.actor) && !included(plan, {e.payload})))
            continue;
        Row row;
        for (const auto value : {e.id.value, e.actor.value, e.payload, e.requested_ug,
                 static_cast<std::uint64_t>(e.issued_at.milliseconds),
                 static_cast<std::uint64_t>(e.key.time.milliseconds), e.observed_position_revision})
            row.put(value);
        append(cut, Record::Pending, row.view(), plan.payload_limit);
    }
}

void capture_neighbors(Cut& cut, const WorldRuntime& world, const WorldSnapshot& state, const Plan& plan) {
    if (!plan.neighbor_actor.value)
        return;
    if (state.ant_count > focal_limit || state.food_source_count > pending_limit) {
        cut.neighbors = Coverage::Limit;
        return;
    }
    const AntRef actor{cut.world, plan.neighbor_actor};
    const auto ant = world.query_ant(actor);
    if (!ant || !ant->alive()) {
        cut.neighbors = Coverage::Missing;
        return;
    }
    cut.neighbors = Coverage::Complete;
    for (const auto ref : world.query_neighborhood(actor, world.config().contact_distance_m).ants) {
        const auto other = world.query_ant(ref);
        if (!other || !other->alive() || other->colony != ant->colony)
            continue;
        Row row;
        row.put(actor.id.value);
        row.put(other->id.value);
        row.put(static_cast<std::uint64_t>(other->stage));
        row.put(static_cast<std::uint64_t>(other->caste));
        append(cut, Record::Neighbor, row.view(), plan.payload_limit);
    }
}

struct CloseDb {
    void operator()(sqlite3* db) const noexcept { sqlite3_close(db); }
};

std::unique_ptr<sqlite3, CloseDb> open_db(const std::filesystem::path& path, bool resume) {
    require(resume ? std::filesystem::is_regular_file(path) : !std::filesystem::exists(path),
            "missing observer sidecar or destination already exists");
    if (resume)
        require(std::filesystem::file_size(path) <= database_limit, "observer database exceeds quota");
    const auto utf8 = path.u8string();
    sqlite3* raw{};
    const int code = sqlite3_open_v2(reinterpret_cast<const char*>(utf8.c_str()), &raw,
                                    SQLITE_OPEN_READWRITE | (resume ? 0 : SQLITE_OPEN_CREATE), nullptr);
    std::unique_ptr<sqlite3, CloseDb> db(raw);
    if (code != SQLITE_OK)
        throw std::runtime_error(raw ? sqlite3_errmsg(raw) : "observer sidecar open failed");
    sqlite3_limit(raw, SQLITE_LIMIT_LENGTH, static_cast<int>(cut_limit + 32768));
    exec(raw, "PRAGMA page_size=4096; PRAGMA max_page_count=16384; PRAGMA cache_size=-768;"
              "PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA wal_autocheckpoint=256;"
              "PRAGMA journal_size_limit=4194304; PRAGMA foreign_keys=ON;");
    Statement journal(raw, "PRAGMA journal_mode");
    require(journal.row() && journal.text(0) == "wal", "observer cannot establish WAL mode");
    return db;
}

void check_header(const Cut& cut, std::uint64_t expected_from) {
    require(cut.from == expected_from && cut.end.cursor >= cut.from &&
            cut.examined == cut.end.cursor - cut.from && cut.selected <= cut.examined &&
            cut.end.time.milliseconds >= 0 && cut.pending <= Coverage::Missing && cut.neighbors <= Coverage::Missing,
            "invalid observer cut interval or coverage");
}
} // namespace

struct Observer::Impl {
    const WorldRuntime& world;
    Plan plan;
    WorldId world_id;
    std::unique_ptr<sqlite3, CloseDb> db;
    std::string identity;
    struct Tail {
        std::uint64_t seq{}, cursor{};
        Boundary last;
        Digest prior{};
    } written, durable;
    std::unique_ptr<Transaction> batch;
    std::size_t batch_bytes{};
    bool sparse_codec{true};

    void discard() noexcept {
        batch.reset();
        written = durable;
        batch_bytes = 0;
    }

    void flush() {
        if (!batch)
            return;
        try {
            batch->commit();
            durable = written;
        } catch (...) {
            discard();
            throw;
        }
        discard();
    }

    Impl(const std::filesystem::path& path, const WorldRuntime& owner, Plan requested,
         bool resume, Bytes checkpoint)
        : world(owner), plan(std::move(requested)), world_id(world.summary().world) {
        validate_plan(plan);
        identity = manifest_identity(world.summary(), plan);
        db = open_db(path, resume);
        if (resume) {
            restore(checkpoint);
            return;
        }
        written.cursor = plan.start_at_current ? boundary(world.summary()).cursor : 0;
        written.prior = first_digest(identity, written.cursor);
        Transaction tx(db.get());
        exec(db.get(), schema);
        Statement m(db.get(), "INSERT INTO manifest VALUES(1,?,?)");
        m.text(1, identity);
        m.number(2, signed_sql(written.cursor));
        m.done();
        tx.commit();
        durable = written;
    }

    void restore(Bytes checkpoint) {
        require(!checkpoint.empty(), "observer restore requires the authoritative checkpoint");
        Statement application(db.get(), "PRAGMA application_id");
        require(application.row() && application.number(0) == 1096241714, "foreign observer database");
        Statement version(db.get(), "PRAGMA user_version");
        require(version.row() && (version.number(0) == 1 || version.number(0) == 2),
                "unsupported observer sidecar version");
        sparse_codec = version.number(0) == 2;
        Statement m(db.get(), "SELECT identity,origin FROM manifest WHERE id=1");
        require(m.row() && m.text(0) == identity, "observer lineage, world or scope differs");
        auto& [seq, cursor, last, prior] = written;
        cursor = positive_sql(m, 1);
        prior = first_digest(identity, cursor);
        Statement q(db.get(), "SELECT seq,sim_ms,revision,cursor,rng,from_cursor,examined,selected,"
                              "records,dropped,pending,neighbors,payload,digest FROM cuts ORDER BY seq");
        while (q.row()) {
            const auto next = positive_sql(q, 0);
            require(next == seq + 1, "noncontiguous observer cut sequence");
            Cut cut{};
            cut.world = world_id;
            cut.end = {{q.number(1)}, positive_sql(q, 2), positive_sql(q, 3), q.u64(4)};
            cut.from = positive_sql(q, 5);
            cut.examined = positive_sql(q, 6);
            cut.selected = positive_sql(q, 7);
            cut.records = positive_sql(q, 8);
            cut.dropped = positive_sql(q, 9);
            const auto pending = positive_sql(q, 10);
            const auto neighbors = positive_sql(q, 11);
            require(pending <= static_cast<std::uint64_t>(Coverage::Missing) &&
                    neighbors <= static_cast<std::uint64_t>(Coverage::Missing), "invalid observer coverage");
            cut.pending = static_cast<Coverage>(pending);
            cut.neighbors = static_cast<Coverage>(neighbors);
            cut.payload = q.blob(12, plan.payload_limit);
            check_header(cut, cursor);
            require(!seq || (last.time <= cut.end.time && last.revision <= cut.end.revision && last != cut.end),
                    "reordered observer cuts");
            const auto digest = cut_digest(cut, next, prior, cut.payload);
            require(std::ranges::equal(digest, q.blob(13, digest.size())), "observer cut digest mismatch");
            prior = digest;
            seq = next;
            last = cut.end;
            cursor = last.cursor;
        }
        require(seq && last == boundary(world.summary()), "observer tail is not the restored cut");
        Statement a(db.get(), "SELECT checkpoint_sha256 FROM anchors WHERE seq=?");
        a.number(1, signed_sql(seq));
        const auto expected = sha256(checkpoint);
        require(a.row() && std::ranges::equal(expected, a.blob(0, expected.size())),
                "observer checkpoint anchor absent or different");
        durable = written;
    }
};

Observer::Observer(const std::filesystem::path& path, const WorldRuntime& world, Plan plan)
    : impl_(std::make_unique<Impl>(path, world, std::move(plan), false, Bytes{})) {}

Observer::Observer(const std::filesystem::path& path, const WorldRuntime& world, Plan plan, Bytes checkpoint)
    : impl_(std::make_unique<Impl>(path, world, std::move(plan), true, checkpoint)) {}

Observer::~Observer() = default;

Cut Observer::capture() const {
    const auto& a = *impl_;
    const auto& [seq, origin, last, prior] = a.written;
    const auto state = a.world.summary();
    Cut cut{};
    cut.world = state.world;
    cut.end = boundary(state);
    cut.from = origin;
    require(cut.world == a.world_id && cut.end.cursor >= origin &&
            (!seq || (cut.end.time >= last.time && cut.end.revision >= last.revision)),
            "observer cannot read a foreign or rewound runtime");
    if (seq && cut.end == last)
        return cut;
    cut.payload.reserve(a.plan.payload_limit);
    for (auto cursor = cut.from; cursor < cut.end.cursor;) {
        const auto limit = static_cast<std::size_t>(std::min<std::uint64_t>(fact_page, cut.end.cursor - cursor));
        const auto page = a.world.events_after({cursor}, limit);
        require(page.size() == limit, "observer read a short fact page");
        for (const auto& fact : page) {
            require(fact.id.value == ++cursor && fact.world == cut.world && fact.time <= cut.end.time,
                    "observer fact identity or ordering mismatch");
            ++cut.examined;
            if (projected(a.plan, fact)) {
                ++cut.selected;
                append(cut, Record::Fact, encode_event(fact), a.plan.payload_limit);
            }
        }
    }
    for (const auto id : a.plan.focal)
        capture_state(cut, a.world, id, a.plan.payload_limit);
    capture_ledger(cut, a.world, state, a.plan.payload_limit);
    capture_pending(cut, a.world, state, a.plan);
    capture_neighbors(cut, a.world, state, a.plan);
    return cut;
}

Publish Observer::publish(const Cut& cut, PublicationFault fault, PublicationMode mode) {
    auto& a = *impl_;
    auto& [previous, cursor, last, prior] = a.written;
    const auto current = a.world.summary();
    require(cut.world == a.world_id && cut.world == current.world && cut.end == boundary(current),
            "observer cannot publish a stale or foreign cut");
    if (previous && cut.end == last)
        return Publish::Duplicate;
    check_header(cut, cursor);
    require(cut.payload.size() <= a.plan.payload_limit &&
            (!previous || (cut.end.time >= last.time && cut.end.revision >= last.revision)),
            "observer cut exceeds capacity or order");
    constexpr std::size_t batch_limit = 1024 * 1024;
    constexpr std::uint64_t batch_cuts = 16;
    if (a.batch && a.batch_bytes + cut.payload.size() > batch_limit)
        a.flush();
    const auto seq = previous + 1;
    const auto packed = a.sparse_codec ? pack_cut(cut.payload) : std::vector<std::uint8_t>{};
    const auto stored = packed.empty() ? Bytes(cut.payload) : Bytes(packed);
    const auto digest = cut_digest(cut, seq, prior, stored);
    if (!a.batch)
        a.batch = std::make_unique<Transaction>(a.db.get());
    try {
        const std::uint8_t empty{};
        Statement q(a.db.get(), "INSERT INTO cuts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
        q.number(1, signed_sql(seq));
        q.number(2, cut.end.time.milliseconds);
        q.number(3, signed_sql(cut.end.revision));
        q.number(4, signed_sql(cut.end.cursor));
        q.u64(5, cut.end.rng);
        q.number(6, signed_sql(cut.from));
        q.number(7, signed_sql(cut.examined));
        q.number(8, signed_sql(cut.selected));
        q.number(9, signed_sql(cut.records));
        q.number(10, signed_sql(cut.dropped));
        q.number(11, static_cast<std::int64_t>(cut.pending));
        q.number(12, static_cast<std::int64_t>(cut.neighbors));
        check(sqlite3_bind_blob64(q.p, 13, stored.empty() ? &empty : stored.data(), stored.size(), SQLITE_STATIC),
              a.db.get());
        q.blob(14, digest);
        q.done();
        if (fault == PublicationFault::BeforeCommit)
            throw std::runtime_error("injected observer publication failure");
    } catch (...) {
        a.discard();
        throw;
    }
    a.written = {seq, cut.end.cursor, cut.end, digest};
    a.batch_bytes += cut.payload.size();
    if (mode == PublicationMode::Immediate || a.batch_bytes >= batch_limit || seq - a.durable.seq >= batch_cuts) {
        a.flush();
        return Publish::Committed;
    }
    return Publish::Staged;
}

void Observer::flush() { impl_->flush(); }

void Observer::anchor(Bytes checkpoint) {
    auto& a = *impl_;
    require(!a.batch && a.durable.seq && !checkpoint.empty() && a.world.summary().world == a.world_id &&
            a.durable.last == boundary(a.world.summary()), "observer anchor requires the current durable cut");
    const auto digest = sha256(checkpoint);
    Transaction tx(a.db.get());
    Statement existing(a.db.get(), "SELECT checkpoint_sha256 FROM anchors WHERE seq=?");
    existing.number(1, signed_sql(a.durable.seq));
    if (existing.row()) {
        require(std::ranges::equal(digest, existing.blob(0, digest.size())), "observer anchor already differs");
    } else {
        Statement put(a.db.get(), "INSERT INTO anchors VALUES(?,?)");
        put.number(1, signed_sql(a.durable.seq));
        put.blob(2, digest);
        put.done();
    }
    tx.commit();
}

std::uint64_t Observer::committed_cuts() const { return impl_->durable.seq; }
std::uint64_t Observer::cursor() const { return impl_->durable.cursor; }
} // namespace antworld::rm02
