#include "antworld/core/world_runtime.hpp"
#include "antworld/core/rng.hpp"
#include "scenario.hpp"

#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <type_traits>

using namespace antworld;
namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template <typename Fn> void rejects(Fn action, const char* message) {
    bool rejected = false;
    try { action(); } catch (const std::exception&) { rejected = true; }
    require(rejected, message);
}
const WorldId id{0x381b1f4791b84b2d, 0x9d51967a3e2b2a01};
EventRequest request(std::int64_t at, std::uint64_t payload = 0,
    DiagnosticAction action = DiagnosticAction::Record) {
    return {{at}, Phase::Environment, 0, 0, payload, action};
}
void put(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint64_t value, unsigned width = 8) {
    for (unsigned i = 0; i < width; ++i) { bytes.at(offset + i) = static_cast<std::uint8_t>(value & 255); value >>= 8; }
}
void checksum(std::vector<std::uint8_t>& bytes) {
    std::uint64_t hash = 14695981039346656037ULL;
    for (std::size_t i = 0; i < bytes.size() - 8; ++i) hash = (hash ^ bytes[i]) * 1099511628211ULL;
    put(bytes, bytes.size() - 8, hash);
}
std::string read(const char* path) {
    std::ifstream stream(path, std::ios::binary);
    require(static_cast<bool>(stream), "cannot read test fixture");
    return {std::istreambuf_iterator<char>(stream), {}};
}
void test(std::string_view name, const std::string& fixture) {
    WorldRuntime world(id, 12345);
    if (name == "T00") {
        const auto scenario = app::parse_scenario(fixture);
        WorldRuntime created(scenario.world, scenario.seed);
        require(created.snapshot().world == id && created.snapshot().seed == 12345, "wrong scenario identity/seed");
        require(created.snapshot().now == SimTime{0} && created.snapshot().revision == 0, "initial time/revision");
        require(id.str() == "381b1f47-91b8-4b2d-9d51-967a3e2b2a01", "UUID encoding");
    } else if (name == "T01") {
        world.schedule(request(100, 0, DiagnosticAction::DrawRandom));
        world.advance_to({100}); const auto before = world.checkpoint();
        world.advance_to({100}); require(before == world.checkpoint(), "same-target advance mutated state");
    } else if (name == "T02") {
        world.advance_to({100}); const auto before = world.checkpoint();
        rejects([&] { world.advance_to({99}); }, "backwards advance accepted");
        rejects([&] { world.schedule(request(99)); }, "past event accepted");
        require(before == world.checkpoint(), "invalid time mutated state");
    } else if (name == "T03") {
        std::vector<EventKey> keys;
        for (int phase = 7; phase >= 0; --phase) {
            keys.push_back({{50}, static_cast<Phase>(phase), 0, 0, 9});
            auto r = request(50, static_cast<std::uint64_t>(phase)); r.phase = static_cast<Phase>(phase); world.schedule(r);
        }
        std::sort(keys.begin(), keys.end()); world.advance_to({50});
        const auto facts = world.committed_events();
        for (std::size_t i = 0; i < 8; ++i) {
            require(keys[i].phase == static_cast<Phase>(i), "phase comparator ignores phase before sequence");
            require(facts[i].payload == i, "runtime phase order");
        }
    } else if (name == "T04") {
        WorldRuntime other(id, 12345);
        for (std::uint64_t i = 0; i < 10; ++i) {
            auto r = request(20, i); r.tie = (9 - i) % 3;
            world.schedule(r); other.schedule(r);
        }
        world.advance_to({20}); other.advance_to({20});
        const std::array<std::uint64_t, 10> expected{0, 3, 6, 9, 2, 5, 8, 1, 4, 7};
        const auto facts = world.committed_events();
        for (std::size_t i = 0; i < expected.size(); ++i) require(facts[i].payload == expected[i], "tie/sequence order");
        require(facts == other.committed_events(), "same-key ordering not deterministic");
    } else if (name == "T05") {
        const auto scheduled = world.schedule(request(1, 0, DiagnosticAction::RepeatSameTime));
        const auto before = world.checkpoint();
        bool diagnosed = false;
        try { world.advance_to({50}); } catch (const std::runtime_error& e) {
            diagnosed = std::string(e.what()).find("same-time") != std::string::npos;
        }
        require(diagnosed, "missing finite recursion diagnostic");
        require(before == world.checkpoint(), "failed advance partially committed");
        require(world.cancel(scheduled), "cannot cancel runaway event"); world.advance_to({50});
    } else if (name == "T06") {
        world.schedule(request(10, 0, DiagnosticAction::DrawRandom));
        const auto before = world.checkpoint(); const auto s = world.snapshot();
        for (int i = 0; i < 20; ++i) {
            require(s == world.snapshot(), "snapshot changed state/hash");
            (void)world.pending_events(); (void)world.committed_events();
        }
        require(before == world.checkpoint(), "read consumed random state");
    } else if (name == "T07") {
        // Frozen independently evaluated reference vectors, not generated during tests.
        constexpr std::array<std::array<std::uint64_t, 5>, 5> vectors{{
            {0, 0xe220a8397b1dcdaf, 0x6e789e6aa1b965f4, 0x06c45d188009454f, 0xf88bb8a8724c81ec},
            {1, 0x910a2dec89025cc1, 0xbeeb8da1658eec67, 0xf893a2eefb32555e, 0x71c18690ee42c90b},
            {12345, 0x22118258a9d111a0, 0x346edce5f713f8ed, 0x1e9a57bc80e6721d, 0x2d160e7e5c3f42ca},
            {0x123456789abcdef0, 0x161922c645ce50e8, 0xad760cafa1697b60, 0x3501ff44902ca50d, 0x417cb9a826d831df},
            {0xffffffffffffffff, 0xe4d971771b652c20, 0xe99ff867dbf682c9, 0x382ff84cb27281e9, 0x6d1db36ccba982d2}
        }};
        for (const auto& v : vectors) {
            Rng rng(v[0]);
            for (std::size_t i = 1; i < v.size(); ++i) require(rng.next() == v[i], "RNG golden vector mismatch");
            Rng restored(rng.state());
            for (int i = 0; i < 100; ++i) require(rng.next() == restored.next(), "RNG continuation mismatch");
        }
    } else if (name == "T08") {
        world.schedule(request(10, 1, DiagnosticAction::DrawRandom));
        world.schedule(request(200, 2, DiagnosticAction::DrawRandom));
        world.advance_to({50});
        WorldRuntime restored({1, 2}, 0); restored.restore(world.checkpoint());
        world.advance_to({250}); restored.advance_to({250});
        require(world.checkpoint() == restored.checkpoint(), "future events/RNG lost on restore");
        require(restored.committed_events().at(1).time == SimTime{200}, "event ran at wrong time");
    } else if (name == "T09") {
        world.allocate_entity_id(); world.allocate_entity_id();
        auto canceled = world.schedule(request(20)); world.cancel(canceled);
        world.schedule(request(5, 8, DiagnosticAction::DrawRandom)); world.schedule(request(200)); world.advance_to({50});
        const auto bytes = world.checkpoint(); WorldRuntime restored({5, 6}, 9); restored.restore(bytes);
        require(restored.snapshot() == world.snapshot(), "round-trip fields differ");
        require(restored.checkpoint() == bytes, "round-trip bytes differ");
        require(world.allocate_entity_id() == restored.allocate_entity_id(), "entity allocator not restored");
        require(world.schedule(request(100)) == restored.schedule(request(100)), "scheduled allocator not restored");
        world.advance_to({200}); restored.advance_to({200});
        require(world.checkpoint() == restored.checkpoint(), "round-trip continuation differs");
    } else if (name == "T10") {
        world.schedule(request(10)); world.advance_to({5}); const auto before = world.checkpoint();
        for (std::size_t n = 0; n < before.size(); ++n) {
            rejects([&] { world.restore(std::span{before}.first(n)); }, "truncated checkpoint accepted");
            require(world.checkpoint() == before, "truncated load changed world");
        }
        for (auto offset : {8u, 12u, 16u}) {
            auto bad = before; put(bad, offset, 99, 4); checksum(bad);
            rejects([&] { world.restore(bad); }, "incompatible version accepted");
        }
        for (auto offset : {60u, 68u, 76u, 84u}) {
            auto bad = before; put(bad, offset, 0); checksum(bad);
            rejects([&] { world.restore(bad); }, "zero allocator accepted");
        }
        auto bad = before; bad[30] ^= 1;
        rejects([&] { world.restore(bad); }, "corruption accepted");
        bad = before; put(bad, 124, 8, 4); checksum(bad);
        rejects([&] { world.restore(bad); }, "invalid event phase accepted");
        bad = before; put(bad, 116, 1); checksum(bad);
        rejects([&] { world.restore(bad); }, "past future event accepted");
        bad = before; put(bad, 100, 65537); checksum(bad);
        rejects([&] { world.restore(bad); }, "excessive record count accepted");
        require(world.checkpoint() == before, "invalid checkpoint partially applied");
    } else if (name == "T12") {
        static_assert(std::is_same_v<decltype(std::declval<const WorldRuntime&>().snapshot()), WorldSnapshot>);
        static_assert(std::is_same_v<decltype(std::declval<const WorldRuntime&>().pending_events()), std::vector<ScheduledEvent>>);
        static_assert(!std::is_copy_constructible_v<WorldRuntime>);
        world.schedule(request(5)); world.advance_to({5}); const auto before = world.checkpoint();
        auto s = world.snapshot(); s.now = {999};
        auto facts = world.committed_events(); facts[0].payload = 123;
        auto bytes = world.checkpoint(); bytes.clear();
        require(world.checkpoint() == before, "query returned writable world state");
        require(s.now != world.snapshot().now, "snapshot not detached");
        auto invalid = request(10); invalid.phase = static_cast<Phase>(8);
        rejects([&] { world.schedule(invalid); }, "invalid mutation accepted");
        require(before == world.checkpoint(), "validation failure changed world");
    } else if (name == "EDGE") {
        auto first = world.allocate_entity_id(); const auto canceled = world.schedule(request(1));
        require(world.cancel(canceled) && !world.cancel(canceled), "cancel idempotency");
        require(world.allocate_entity_id().value > first.value, "entity ID reused");
        auto a = request(10, 1); a.priority = 9; auto b = request(10, 2); b.priority = 2;
        world.schedule(a); world.schedule(b); world.advance_to({10});
        require(world.committed_events().front().payload == 2, "priority order");
        // S1 persists the complete key: a same-phase event cannot jump back to priority zero.
        rejects([&] { world.schedule(request(10, 3)); }, "earlier same-time priority accepted");
        auto later = request(10, 3); later.priority = 9; world.schedule(later); world.advance_to({10});
        require(world.committed_events().back().payload == 3, "new due work at same target not drained");
        const auto before = world.checkpoint();
        auto invalid = request(20); invalid.action = static_cast<DiagnosticAction>(255);
        rejects([&] { world.schedule(invalid); }, "invalid action accepted");
        require(before == world.checkpoint(), "invalid action changed state");
        auto full = before; put(full, 60, std::numeric_limits<std::uint64_t>::max()); checksum(full); world.restore(full);
        rejects([&] { world.allocate_entity_id(); }, "ID overflow accepted");
        require(world.checkpoint() == full, "overflow changed state");
        world.restore(before); world.advance_to({std::numeric_limits<std::int64_t>::max()});
        require(world.snapshot().now.milliseconds == std::numeric_limits<std::int64_t>::max(), "maximum time not reached");
        rejects([] { (void)WorldId::parse("00000000-0000-0000-0000-000000000000"); }, "nil UUID accepted");
        rejects([] { (void)WorldId::parse("381b1f47X91b8-4b2d-9d51-967a3e2b2a01"); }, "invalid UUID accepted");
        for (const auto& raw : {"{}", "[]", "{\"a\":1,\"a\":2}", "{\"x\":01}", "{\"x\":true garbage}",
                "{\"x\":\"\\ud800\"}", "{\"x\":1.}", "{\"x\":1e}", "{\"x\":null,}"})
            rejects([&] { (void)app::parse_scenario(raw); }, "malformed scenario accepted");
        for (auto needle : {"\"seed\": 12345", "\"time_unit\": \"ms\"", "\"x_min\": -1"}) {
            auto bad = fixture; const auto pos = bad.find(needle); require(pos != bad.npos, "fixture token missing");
            const auto replacement = std::string_view(needle).starts_with("\"seed") ? "\"seed\": 18446744073709551616" :
                std::string_view(needle).starts_with("\"time") ? "\"time_unit\": \"seconds\"" : "\"x_min\": 1e9999";
            bad.replace(pos, std::string(needle).size(), replacement);
            rejects([&] { (void)app::parse_scenario(bad); }, "invalid schema value accepted");
        }
        WorldRuntime one(id, 99), split(id, 99);
        for (int i = 0; i < 100; ++i) { auto r = request(i, static_cast<std::uint64_t>(i), DiagnosticAction::DrawRandom); one.schedule(r); split.schedule(r); }
        one.advance_to({100}); for (int i = 0; i <= 100; ++i) split.advance_to({i});
        require(one.checkpoint() == split.checkpoint(), "advance chunking changed trajectory");
    } else throw std::runtime_error("unknown test case");
}
} // namespace
int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("usage: antworld_tests CASE SCENARIO");
        test(argv[1], read(argv[2])); std::cout << "PASS " << argv[1] << '\n'; return 0;
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
