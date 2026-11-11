#include "rm02_fixtures.hpp"

#include "history_digest.hpp"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>

namespace {
using namespace antworld;
using namespace antworld::rm02;
using Clock = std::chrono::steady_clock;

double ms(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

std::ofstream output(const std::filesystem::path& path) {
    std::ofstream stream(path, std::ios::binary);
    stream.exceptions(std::ios::failbit | std::ios::badbit);
    stream << std::setprecision(17);
    return stream;
}

void save(const std::filesystem::path& path, std::span<const std::uint8_t> bytes) {
    auto stream = output(path);
    stream.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    stream.close();
}

std::string digest(std::span<const std::uint8_t> bytes) {
    constexpr std::string_view hex{"0123456789abcdef"};
    std::string text;
    for (auto byte : storage::detail::sha256(bytes)) {
        text.push_back(hex[byte >> 4]);
        text.push_back(hex[byte & 15]);
    }
    return text;
}

std::uint64_t integer(std::string_view value) {
    std::uint64_t result{};
    const auto parsed = std::from_chars(value.data(), value.data() + value.size(), result);
    if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size() || !result)
        throw std::invalid_argument("expected positive integer");
    return result;
}

int run(const std::filesystem::path& dir, std::string_view mode, std::string_view arm,
        unsigned workers, std::uint64_t seed, WorldRuntime& world, Plan plan,
        RuntimeLimits limits, std::int64_t end) {
    const bool dense = mode == "dense";
    const bool window = mode == "window";
    if (!std::filesystem::create_directories(dir))
        throw std::runtime_error("new RM-02 output directory required");
    const auto initial = world.checkpoint();
    save(dir / "initial.chk", initial);
    auto configuration = output(dir / "configuration.csv");
    configuration << "mode,arm,workers,seed,horizon_ms,world_id,lineage,fixture_status,initial_sha256\n"
                  << mode << ',' << arm << ',' << workers << ',' << seed << ',' << end << ','
                  << world.summary().world.str() << ',' << plan.lineage << ",ENGINEERING_FIXTURE,"
                  << digest(initial) << '\n';
    configuration.close();
    auto trace = output(dir / "cuts.csv");
    trace << "sim_ms,cursor,revision,examined,selected,records,dropped,pending_coverage,neighbor_coverage,"
             "payload_bytes,capture_ms,publish_ms,status\n";
    auto errors = output(dir / "errors.log");
    std::unique_ptr<Observer> observer;
    bool complete = true;
    try {
        observer = std::make_unique<Observer>(dir / "observer.sqlite", world, plan);
    } catch (const std::exception& e) {
        complete = false;
        errors << "open " << e.what() << '\n';
    }
    const auto observe = [&] {
        const auto current = world.summary();
        try {
            if (!observer)
                throw std::runtime_error("observer unavailable");
            const auto begin = Clock::now();
            const auto cut = observer->capture();
            const auto capture_ms = ms(begin);
            const auto write_start = Clock::now();
            const auto publication = observer->publish(cut, PublicationFault::None, PublicationMode::Buffered);
            const auto publish_ms = ms(write_start);
            complete = complete && !cut.dropped;
            trace << current.now.milliseconds << ',' << cut.end.cursor << ',' << cut.end.revision << ','
                  << cut.examined << ',' << cut.selected << ',' << cut.records << ',' << cut.dropped << ','
                  << static_cast<unsigned>(cut.pending) << ',' << static_cast<unsigned>(cut.neighbors) << ','
                  << cut.payload.size() << ',' << capture_ms << ',' << publish_ms << ','
                  << (cut.dropped ? "OVERFLOW" : publication == Publish::Staged ? "STAGED" : "COMMITTED") << '\n';
        } catch (const std::exception& e) {
            complete = false;
            trace << current.now.milliseconds << ',' << current.committed_events << ',' << current.revision
                  << ",,,,,,,,,,OBSERVATION_FAILED\n";
            errors << "observe " << current.now.milliseconds << ' ' << e.what() << '\n';
        }
    };
    double advance_ms{};
    bool advanced = true;
    if (!dense)
        observe();
    while (world.summary().now.milliseconds < end) {
        const auto now = world.summary();
        auto next = std::min(end, now.now.milliseconds + (dense ? 1000 : s6_3_1_fixture::day));
        if (window) {
            next = std::min(end, now.now.milliseconds + 6 * s6_3_1_fixture::hour);
            if (now.pending_events <= pending_limit) {
                const auto due = world.pending_events();
                if (!due.empty())
                    next = std::min(end, due.front().key.time.milliseconds);
            }
        }
        const auto start = Clock::now();
        try {
            world.advance_to({next});
        } catch (const std::exception& e) {
            advanced = false;
            errors << "advance_rolled_back " << now.now.milliseconds << ' ' << e.what() << '\n';
            break;
        }
        advance_ms += ms(start);
        if (!dense || next == end)
            observe();
    }
    const auto final = world.checkpoint();
    save(dir / "final.chk", final);
    bool rejoined = false;
    if (observer) {
        try {
            observer->flush();
            observer->anchor(final);
            observer.reset();
            WorldRuntime restored({91, 1}, 1, {}, limits);
            restored.restore(final);
            Observer reopened(dir / "observer.sqlite", restored, plan, final);
            rejoined = reopened.publish(reopened.capture()) == Publish::Duplicate;
        } catch (const std::exception& e) {
            errors << "rejoin " << e.what() << '\n';
        }
    }
    WorldRuntime reference({91, 2}, 1, {}, limits);
    reference.restore(initial);
    reference.advance_to(world.summary().now);
    const bool exact = reference.checkpoint() == final;
    const auto s = world.snapshot();
    const auto w = world.contact_work();
    const bool ok = advanced && complete && rejoined && exact;
    auto summary = output(dir / "summary.csv");
    summary << "status,sim_ms,events,pending,individuals,living,state_hash,trace_hash,"
               "checkpoint_bytes,checkpoint_sha256,advance_ms,observer_complete,rejoined,exact_off,"
               "contact_decisions,candidates,bucket_queries,tree_visits,maximum_candidates\n"
            << (ok ? "ENGINEERING_PASS" : "INCOMPLETE") << ',' << s.now.milliseconds << ',' << s.committed_events
            << ',' << s.pending_events << ',' << s.ant_count << ',' << s.living_ants << ',' << hex64(s.state_hash)
            << ',' << hex64(s.trace_hash) << ',' << final.size() << ',' << digest(final) << ',' << advance_ms
            << ',' << complete << ',' << rejoined << ',' << exact << ',' << w.decisions << ',' << w.candidates_examined
            << ',' << w.bucket_queries << ',' << w.tree_visits << ',' << w.maximum_candidates << '\n';
    summary.close();
    return ok ? 0 : 1;
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 6)
            throw std::invalid_argument("usage: antworld_s6_4_rm02 OUTPUT MODE ARM WORKERS SEED");
        const std::string_view mode{argv[2]}, arm{argv[3]};
        const auto count = integer(argv[4]), seed = integer(argv[5]);
        const auto lineage = std::string(mode) + '-' + std::string(arm) + '-' +
            std::to_string(count) + '-' + std::to_string(seed);
        const auto workers = static_cast<unsigned>(count);
        if (mode == "dense" && arm == "dense" && (count == 512 || count == 2048)) {
            DenseFixture fixture(workers, seed);
            return run(argv[1], mode, arm, workers, seed, fixture.world, {lineage, fixture.focal, {}},
                       contact_limits(), 10000);
        }
        if ((mode != "ecology" && mode != "window") || (count != 8 && count != 32) ||
            (mode == "window" && arm != "ordinary"))
            throw std::invalid_argument("invalid frozen RM-02 scenario");
        auto fixture = ecology_fixture(seed, workers, arm);
        const bool window = mode == "window";
        return run(argv[1], mode, arm, workers, seed, fixture.world,
                   {lineage, ecology_focal(fixture), window ? fixture.queen.id : EntityId{}, true, window},
                   s6_3_1_fixture::limits(), (window ? 2 : arm == "depot" ? 180 : 90) * s6_3_1_fixture::day);
    } catch (const std::exception& e) {
        std::cerr << "RM-02: " << e.what() << '\n';
        return 1;
    }
}
