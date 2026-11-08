#include "antworld/core/world_runtime.hpp"
#include "antworld/core/rng.hpp"

#include <algorithm>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>

namespace antworld {
namespace {
constexpr std::uint64_t max_u64 = std::numeric_limits<std::uint64_t>::max();
std::uint64_t hash_bytes(std::span<const std::uint8_t> bytes) {
    std::uint64_t result = UINT64_C(14695981039346656037);
    for (auto b : bytes) result = (result ^ b) * UINT64_C(1099511628211);
    return result;
}
struct Writer {
    std::vector<std::uint8_t> bytes;
    void put(std::uint64_t v, unsigned width = 8) {
        for (unsigned i = 0; i < width; ++i) {
            bytes.push_back(static_cast<std::uint8_t>(v & 255));
            v >>= 8;
        }
    }
};
struct Reader {
    std::span<const std::uint8_t> bytes;
    std::size_t cursor{};
    std::uint64_t get(unsigned width = 8) {
        if (width > bytes.size() - cursor) throw std::invalid_argument("truncated checkpoint");
        std::uint64_t result = 0;
        for (unsigned i = 0; i < width; ++i) result |= std::uint64_t{bytes[cursor++]} << (8 * i);
        return result;
    }
    SimTime time() {
        const auto value = get();
        if (value > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()))
            throw std::invalid_argument("checkpoint time outside int64 range");
        return {static_cast<std::int64_t>(value)};
    }
    std::size_t count() {
        const auto value = get();
        if (value > WorldRuntime::max_records) throw std::invalid_argument("checkpoint record limit exceeded");
        return static_cast<std::size_t>(value);
    }
};
void bump(std::uint64_t& value) {
    if (value == max_u64) throw std::overflow_error("monotonic counter exhausted");
    ++value;
}
std::uint64_t take(std::uint64_t& value) {
    const auto result = value;
    bump(value);
    return result;
}
bool valid(Phase p) { return p <= Phase::Reschedule; }
bool valid(DiagnosticAction a) { return a <= DiagnosticAction::RepeatSameTime; }
void write_fact(Writer& w, const WorldEvent& e) {
    w.put(e.id.value); w.put(e.world.high); w.put(e.world.low);
    w.put(static_cast<std::uint64_t>(e.time.milliseconds)); w.put(e.source.value);
    w.put(static_cast<std::uint8_t>(e.action), 1);
    w.put(e.revision); w.put(e.payload); w.put(e.random_value);
}
std::uint64_t trace_hash(const std::vector<WorldEvent>& events) {
    Writer writer;
    for (const auto& e : events) write_fact(writer, e);
    return hash_bytes(writer.bytes);
}
} // namespace

struct WorldRuntime::State {
    WorldId world;
    std::uint64_t seed;
    SimTime now{};
    std::uint64_t revision{}, next_entity{1}, next_scheduled{1}, next_event{1}, next_sequence{1};
    Rng rng;
    std::map<EventKey, ScheduledEvent> queue;
    std::vector<WorldEvent> journal;
    State(WorldId id, std::uint64_t seed_value) : world(id), seed(seed_value), rng(seed_value) {}
};

WorldRuntime::WorldRuntime(WorldId world, std::uint64_t seed) : state_(std::make_unique<State>(world, seed)) {
    if (world == WorldId{}) throw std::invalid_argument("world_id must not be nil");
}
WorldRuntime::~WorldRuntime() = default;
WorldRuntime::WorldRuntime(WorldRuntime&&) noexcept = default;
WorldRuntime& WorldRuntime::operator=(WorldRuntime&&) noexcept = default;

EntityId WorldRuntime::allocate_entity_id() {
    auto next = std::make_unique<State>(*state_);
    const EntityId id{take(next->next_entity)};
    bump(next->revision);
    state_.swap(next);
    return id;
}
ScheduledId WorldRuntime::schedule_in(State& state, const EventRequest& r) {
    if (r.time < state.now) throw std::invalid_argument("cannot schedule an event in the past");
    if (!valid(r.phase) || !valid(r.action)) throw std::invalid_argument("invalid phase or diagnostic action");
    if (state.queue.size() >= max_records) throw std::length_error("future event limit exceeded");
    ScheduledEvent event{{take(state.next_scheduled)},
        {r.time, r.phase, r.priority, r.tie, take(state.next_sequence)}, r.action, r.payload};
    state.queue.emplace(event.key, event);
    bump(state.revision);
    return event.id;
}
ScheduledId WorldRuntime::schedule(const EventRequest& request) {
    auto next = std::make_unique<State>(*state_);
    const auto id = schedule_in(*next, request);
    state_.swap(next);
    return id;
}
bool WorldRuntime::cancel(ScheduledId id) {
    const auto found = std::find_if(state_->queue.begin(), state_->queue.end(),
        [id](const auto& entry) { return entry.second.id == id; });
    if (found == state_->queue.end()) return false;
    auto next = std::make_unique<State>(*state_);
    next->queue.erase(found->first);
    bump(next->revision);
    state_.swap(next);
    return true;
}
void WorldRuntime::advance_to(SimTime target) {
    if (target < state_->now) throw std::invalid_argument("simulation time cannot move backwards");
    auto next = std::make_unique<State>(*state_);
    SimTime last_time{-1};
    std::size_t same_time = 0;
    while (!next->queue.empty() && next->queue.begin()->first.time <= target) {
        const auto event = next->queue.begin()->second;
        if (event.key.time != last_time) { last_time = event.key.time; same_time = 0; }
        if (++same_time > max_same_time_events)
            throw std::runtime_error("same-time event budget exceeded; advance rolled back");
        if (next->journal.size() >= max_records) throw std::length_error("committed event limit exceeded");
        next->queue.erase(next->queue.begin());
        next->now = event.key.time;
        const auto random = event.action == DiagnosticAction::DrawRandom ? next->rng.next() : 0;
        bump(next->revision);
        next->journal.push_back({{take(next->next_event)}, next->world, next->now, event.id,
            event.action, next->revision, event.payload, random});
        if (event.action == DiagnosticAction::RepeatSameTime) {
            schedule_in(*next, {event.key.time, event.key.phase, event.key.priority,
                event.key.tie, event.payload, event.action});
        }
    }
    next->now = target;
    state_.swap(next);
}
std::vector<std::uint8_t> WorldRuntime::encode(const State& s) {
    Writer w;
    w.put(UINT64_C(0x3154504b435741), 8); // "AWCKPT1" followed by a zero byte.
    w.put(schema_version, 4); w.put(physics_version, 4); w.put(1, 4); // RNG version.
    w.put(s.world.high); w.put(s.world.low); w.put(s.seed);
    w.put(static_cast<std::uint64_t>(s.now.milliseconds)); w.put(s.revision);
    w.put(s.next_entity); w.put(s.next_scheduled); w.put(s.next_event); w.put(s.next_sequence);
    w.put(s.rng.state()); w.put(s.queue.size());
    for (const auto& [key, e] : s.queue) {
        w.put(e.id.value); w.put(static_cast<std::uint64_t>(key.time.milliseconds));
        w.put(static_cast<std::uint32_t>(key.phase), 4); w.put(key.priority, 4);
        w.put(key.tie); w.put(key.sequence); w.put(static_cast<std::uint8_t>(e.action), 1); w.put(e.payload);
    }
    w.put(s.journal.size());
    for (const auto& e : s.journal) write_fact(w, e);
    w.put(hash_bytes(w.bytes));
    return w.bytes;
}
std::unique_ptr<WorldRuntime::State> WorldRuntime::decode(std::span<const std::uint8_t> bytes) {
    if (bytes.size() < 124 || bytes.size() > 16 * 1024 * 1024)
        throw std::invalid_argument("checkpoint size is invalid");
    Reader checksum{bytes.last(8)};
    if (hash_bytes(bytes.first(bytes.size() - 8)) != checksum.get())
        throw std::invalid_argument("checkpoint checksum mismatch");
    Reader r{bytes.first(bytes.size() - 8)};
    if (r.get() != UINT64_C(0x3154504b435741)) throw std::invalid_argument("invalid checkpoint magic");
    if (r.get(4) != schema_version || r.get(4) != physics_version || r.get(4) != 1)
        throw std::invalid_argument("unsupported checkpoint schema, physics or RNG version");
    const WorldId world{r.get(), r.get()};
    if (world == WorldId{}) throw std::invalid_argument("nil checkpoint world");
    auto s = std::make_unique<State>(world, r.get());
    s->now = r.time(); s->revision = r.get();
    s->next_entity = r.get(); s->next_scheduled = r.get(); s->next_event = r.get(); s->next_sequence = r.get();
    s->rng = Rng(r.get());
    if (!s->next_entity || !s->next_scheduled || !s->next_event || !s->next_sequence)
        throw std::invalid_argument("checkpoint has a zero ID allocator");
    std::set<std::uint64_t> ids, sequences;
    const auto count = r.count();
    for (std::size_t i = 0; i < count; ++i) {
        ScheduledEvent e;
        e.id = {r.get()}; e.key.time = r.time(); e.key.phase = static_cast<Phase>(r.get(4));
        e.key.priority = static_cast<std::uint32_t>(r.get(4)); e.key.tie = r.get(); e.key.sequence = r.get();
        e.action = static_cast<DiagnosticAction>(r.get(1)); e.payload = r.get();
        if (!e.id.value || e.id.value >= s->next_scheduled || !e.key.sequence ||
            e.key.sequence >= s->next_sequence || e.key.time < s->now || !valid(e.key.phase) ||
            !valid(e.action) || !ids.insert(e.id.value).second || !sequences.insert(e.key.sequence).second ||
            (!s->queue.empty() && e.key <= s->queue.rbegin()->first))
            throw std::invalid_argument("invalid future event in checkpoint");
        s->queue.emplace(e.key, e);
    }
    const auto facts = r.count();
    std::uint64_t previous_revision = 0;
    SimTime previous_time{};
    for (std::size_t i = 0; i < facts; ++i) {
        WorldEvent e;
        e.id = {r.get()}; e.world = {r.get(), r.get()}; e.time = r.time(); e.source = {r.get()};
        e.action = static_cast<DiagnosticAction>(r.get(1)); e.revision = r.get();
        e.payload = r.get(); e.random_value = r.get();
        if (e.id.value != i + 1 || e.world != world || e.time < previous_time || e.time > s->now ||
            !e.source.value || e.source.value >= s->next_scheduled || !ids.insert(e.source.value).second ||
            !valid(e.action) || e.revision <= previous_revision || e.revision > s->revision ||
            (e.action != DiagnosticAction::DrawRandom && e.random_value != 0))
            throw std::invalid_argument("invalid committed event in checkpoint");
        previous_time = e.time; previous_revision = e.revision;
        s->journal.push_back(e);
    }
    if (s->next_event != facts + 1 || r.cursor != r.bytes.size())
        throw std::invalid_argument("invalid event allocator or trailing checkpoint data");
    return s;
}
void WorldRuntime::restore(std::span<const std::uint8_t> bytes) {
    auto restored = decode(bytes);
    state_.swap(restored);
}
std::vector<std::uint8_t> WorldRuntime::checkpoint() const { return encode(*state_); }
std::vector<WorldEvent> WorldRuntime::committed_events() const { return state_->journal; }
std::vector<ScheduledEvent> WorldRuntime::pending_events() const {
    std::vector<ScheduledEvent> result;
    for (const auto& [key, event] : state_->queue) { (void)key; result.push_back(event); }
    return result;
}
WorldSnapshot WorldRuntime::snapshot() const {
    const auto& s = *state_;
    const auto bytes = encode(s);
    return {s.world, s.now, s.seed, s.revision, s.queue.size(), s.journal.size(), s.next_entity,
        s.next_scheduled, s.next_event, s.next_sequence, s.rng.state(),
        hash_bytes(std::span{bytes}.first(bytes.size() - 8)), trace_hash(s.journal)};
}
} // namespace antworld
