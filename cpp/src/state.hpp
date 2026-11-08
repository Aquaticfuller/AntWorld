#pragma once
#include "antworld/core/world_runtime.hpp"
#include "antworld/core/rng.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <stdexcept>

namespace antworld::detail {
inline void bump(std::uint64_t& n) {
    if (n == UINT64_MAX) throw std::overflow_error("monotonic counter exhausted");
    ++n;
}
inline std::uint64_t take(std::uint64_t& n) { const auto v = n; bump(n); return v; }
inline std::uint64_t add(std::uint64_t a, std::uint64_t b) {
    if (b > UINT64_MAX - a) throw std::overflow_error("mass overflow");
    return a + b;
}
inline FoodMass sum(FoodMass a, FoodMass b) {
    return {add(a.carbs_ug, b.carbs_ug), add(a.protein_ug, b.protein_ug),
        add(a.water_ug, b.water_ug), add(a.other_ug, b.other_ug)};
}
inline FoodMass subtract(FoodMass a, FoodMass b) {
    if (a.carbs_ug < b.carbs_ug || a.protein_ug < b.protein_ug ||
        a.water_ug < b.water_ug || a.other_ug < b.other_ug)
        throw std::logic_error("mass underflow");
    return {a.carbs_ug-b.carbs_ug, a.protein_ug-b.protein_ug,
        a.water_ug-b.water_ug, a.other_ug-b.other_ug};
}
inline bool finite(PositionM p) { return std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z); }
inline bool inside(PositionM p, const WorldConfig& c) {
    return finite(p) && p.x >= c.min_m.x && p.x <= c.max_m.x &&
        p.y >= c.min_m.y && p.y <= c.max_m.y && p.z >= c.min_m.z && p.z <= c.max_m.z;
}
inline void validate_config(const WorldConfig& c) {
    if (!finite(c.min_m) || !finite(c.max_m) || c.min_m.x >= c.max_m.x ||
        c.min_m.y >= c.max_m.y || c.min_m.z >= c.max_m.z ||
        !std::isfinite(c.max_speed_m_per_s) || c.max_speed_m_per_s <= 0 ||
        !std::isfinite(c.contact_distance_m) || c.contact_distance_m < 0)
        throw std::invalid_argument("invalid ENGINEERING_FIXTURE world configuration");
}
inline double distance(PositionM a, PositionM b) { return std::hypot(a.x-b.x, a.y-b.y, a.z-b.z); }
inline bool valid(Phase p) { return p <= Phase::Reschedule; }
inline bool valid(DiagnosticAction a) { return a <= DiagnosticAction::RepeatSameTime; }
inline bool valid(LifeStage a) { return a <= LifeStage::Dead; }

// Minimal grouped SoA: stable identity, lifecycle, spatial and material columns.
// Rows survive death. Stable IDs are not row indices. No mutable pointers escape.
struct AntStore {
    struct Identity { EntityId id; ColonyId colony; SimTime born; Caste caste; };
    struct Spatial { PositionM position; std::uint64_t revision; };
    struct Inventory { std::uint64_t capacity; FoodMass mass; };
    // Use the throwing count constructor: MSVC Debug allocates iterator proxies
    // even for empty vectors, but its default constructor is noexcept.
    std::vector<Identity> identities = std::vector<Identity>(0);
    std::vector<LifeStage> stages = std::vector<LifeStage>(0);
    std::vector<Spatial> spatial = std::vector<Spatial>(0);
    std::vector<Inventory> inventories = std::vector<Inventory>(0);
    std::map<EntityId, std::size_t> index;
    std::size_t size() const { return identities.size(); }
    AntState get(std::size_t i) const {
        const auto& a = identities[i]; const auto& p = spatial[i]; const auto& f = inventories[i];
        return {a.id, a.colony, a.born, stages[i], a.caste, p.position, p.revision, f.capacity, f.mass};
    }
    void set(std::size_t i, const AntState& a) noexcept {
        identities[i] = {a.id, a.colony, a.born_at, a.caste}; stages[i] = a.stage;
        spatial[i] = {a.position, a.position_revision}; inventories[i] = {a.carrying_capacity_ug, a.carried_food};
    }
    void append(const AntState& a) {
        const auto n = size();
        // Allocate all columns before changing logical row count.
        if (n == identities.capacity() || n == stages.capacity() || n == spatial.capacity() || n == inventories.capacity()) {
            const auto capacity = std::max<std::size_t>(8, n * 2 + 1);
            identities.reserve(capacity); stages.reserve(capacity); spatial.reserve(capacity); inventories.reserve(capacity);
        }
        if (!index.emplace(a.id, n).second) throw std::invalid_argument("duplicate ant ID");
        identities.push_back({a.id, a.colony, a.born_at, a.caste}); stages.push_back(a.stage);
        spatial.push_back({a.position, a.position_revision}); inventories.push_back({a.carrying_capacity_ug, a.carried_food});
    }
    void truncate(std::size_t n) noexcept {
        while (size() > n) { index.erase(identities.back().id); identities.pop_back(); }
        stages.resize(n); spatial.resize(n); inventories.resize(n);
    }
};
template <typename IdType, typename Row> struct Store {
    std::vector<Row> rows = std::vector<Row>(0);
    std::map<IdType, std::size_t> index;
    void append(Row row) {
        if (rows.size() == rows.capacity()) rows.reserve(std::max<std::size_t>(8, rows.size()*2+1));
        if (!index.emplace(row.id, rows.size()).second) throw std::invalid_argument("duplicate entity ID");
        rows.push_back(row);
    }
    void truncate(std::size_t n) noexcept {
        while (rows.size() > n) { index.erase(rows.back().id); rows.pop_back(); }
    }
};
std::uint64_t hash_bytes(std::span<const std::uint8_t> bytes);
std::uint64_t trace_hash(const std::vector<WorldEvent>& events);
} // namespace antworld::detail

namespace antworld {
struct WorldRuntime::State {
    struct Metadata {
        SimTime now{};
        std::uint64_t revision{}, next_entity{1}, next_scheduled{1}, next_event{1}, next_sequence{1};
        Rng rng{0};
        std::optional<EventKey> watermark;
        std::uint64_t executed{}, living{};
        FoodLedger ledger;
    } m;
    WorldId world;
    std::uint64_t seed;
    WorldConfig config;
    using Queue = std::map<EventKey, ScheduledEvent>;
    using QueueIndex = std::map<ScheduledId, EventKey>;
    Queue queue;
    QueueIndex queue_index;
    std::vector<WorldEvent> journal = std::vector<WorldEvent>(0);
    detail::AntStore ants;
    detail::Store<ColonyId, Colony> colonies;
    detail::Store<ResourceId, FoodSource> foods;
    State(WorldId id, std::uint64_t value, WorldConfig c = {}) : world(id), seed(value), config(c) { m.rng = Rng(value); }
    State(const State&) = delete;
    State& operator=(const State&) = delete;
};

// Rollback allocates no memory: removed queue nodes and touched row before-images
// are retained, and append-only stores/journal return to their original lengths.
class WorldRuntime::Transaction {
    struct QueueUndo {
        EventKey key; ScheduledId id; bool inserted;
        State::Queue::node_type event;
        State::QueueIndex::node_type index;
    };
    State& s;
    const RuntimeLimits& limits;
    State::Metadata before;
    std::size_t ants_before, colonies_before, foods_before, journal_before;
    std::vector<QueueUndo> queue_undo = std::vector<QueueUndo>(0);
    std::vector<std::pair<std::size_t, AntState>> ant_undo = std::vector<std::pair<std::size_t, AntState>>(0);
    std::vector<std::pair<std::size_t, FoodSource>> food_undo = std::vector<std::pair<std::size_t, FoodSource>>(0);
    bool committed{};
public:
    Transaction(State& state, const RuntimeLimits& policy) : s(state), limits(policy), before(state.m),
        ants_before(s.ants.size()), colonies_before(s.colonies.rows.size()),
        foods_before(s.foods.rows.size()), journal_before(s.journal.size()) {}
    Transaction(const Transaction&) = delete;
    Transaction& operator=(const Transaction&) = delete;
    ~Transaction() noexcept {
        if (committed) return;
        for (auto i = ant_undo.rbegin(); i != ant_undo.rend(); ++i) s.ants.set(i->first, i->second);
        for (auto i = food_undo.rbegin(); i != food_undo.rend(); ++i) s.foods.rows[i->first] = i->second;
        s.ants.truncate(ants_before); s.colonies.truncate(colonies_before); s.foods.truncate(foods_before);
        s.journal.resize(journal_before);
        for (auto i = queue_undo.rbegin(); i != queue_undo.rend(); ++i) {
            if (i->inserted) { s.queue.erase(i->key); s.queue_index.erase(i->id); }
            else { s.queue.insert(std::move(i->event)); s.queue_index.insert(std::move(i->index)); }
        }
        s.m = before;
    }
    void commit() noexcept { committed = true; }
    void touch_ant(std::size_t i) { ant_undo.emplace_back(i, s.ants.get(i)); }
    void touch_food(std::size_t i) { food_undo.emplace_back(i, s.foods.rows[i]); }
    void entity_budget() const {
        if (s.ants.size() + s.colonies.rows.size() + s.foods.rows.size() >= limits.entities)
            throw std::length_error("entity host budget exceeded");
    }
    ScheduledId insert(ScheduledEvent e) {
        if (e.key.time < s.m.now || (e.key.time == s.m.now && s.m.watermark &&
            EventKey{e.key.time, e.key.phase, e.key.priority, e.key.tie, s.m.next_sequence} <= *s.m.watermark))
            throw std::invalid_argument("event precedes the persisted execution watermark");
        if (s.queue.size() >= limits.pending_events) throw std::length_error("future event host budget exceeded");
        e.id = {detail::take(s.m.next_scheduled)}; e.key.sequence = detail::take(s.m.next_sequence);
        State::Queue temporary; State::QueueIndex temporary_index;
        temporary.emplace(e.key, e); temporary_index.emplace(e.id, e.key);
        queue_undo.push_back({e.key, e.id, true, {}, {}});
        s.queue.insert(temporary.extract(e.key)); s.queue_index.insert(temporary_index.extract(e.id));
        detail::bump(s.m.revision); return e.id;
    }
    ScheduledEvent remove(EventKey key) {
        const auto e = s.queue.at(key);
        queue_undo.push_back({key, e.id, false, {}, {}});
        queue_undo.back().event = s.queue.extract(key); queue_undo.back().index = s.queue_index.extract(e.id);
        return e;
    }
    void time(SimTime at) {
        if (at != s.m.now) { s.m.now = at; s.m.watermark.reset(); s.m.executed = 0; }
    }
    void executing(const ScheduledEvent& e) {
        time(e.key.time);
        if (s.m.executed >= limits.events_per_timestamp)
            throw std::runtime_error("same-time event host budget exceeded; advance rolled back");
        ++s.m.executed; s.m.watermark = e.key;
    }
    void fact(WorldEvent e) {
        if (s.journal.size() >= limits.committed_events) throw std::length_error("committed event host budget exceeded");
        e.id = {detail::take(s.m.next_event)}; e.world = s.world; e.time = s.m.now;
        detail::bump(s.m.revision); e.revision = s.m.revision; s.journal.push_back(e);
    }
};
} // namespace antworld
