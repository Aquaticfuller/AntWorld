#include "antworld/core/world_runtime.hpp"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <vector>

int main() {
    using namespace antworld;
    using Clock = std::chrono::steady_clock;
    constexpr std::size_t trials = 64;
    constexpr std::uint64_t events_per_trial = 128;
    std::vector<double> advances, saves, restores;
    std::size_t checkpoint_bytes{};
    double total_advance_ms = 0;
    for (std::size_t trial = 0; trial < trials; ++trial) {
        WorldRuntime world({1, 2}, 12345);
        for (std::uint64_t i = 0; i < events_per_trial; ++i)
            world.schedule({{static_cast<std::int64_t>(i + 1)}, Phase::Environment, 0, 0, i, DiagnosticAction::DrawRandom});
        const auto start = Clock::now();
        world.advance_to({60000});
        const auto advanced = Clock::now();
        const auto bytes = world.checkpoint();
        const auto saved = Clock::now();
        world.restore(bytes);
        const auto restored = Clock::now();
        const auto advance_ms = std::chrono::duration<double, std::milli>(advanced - start).count();
        advances.push_back(advance_ms); total_advance_ms += advance_ms;
        saves.push_back(std::chrono::duration<double, std::milli>(saved - advanced).count());
        restores.push_back(std::chrono::duration<double, std::milli>(restored - saved).count());
        checkpoint_bytes = bytes.size();
    }
    auto percentile = [](std::vector<double> samples, std::size_t index) {
        std::sort(samples.begin(), samples.end()); return samples.at(index);
    };
    std::cout << "{\n  \"scope\": \"S0_DIAGNOSTICS_ONLY\",\n  \"trials\": " << trials
        << ",\n  \"events_per_trial\": " << events_per_trial << ",\n  \"simulated_ms_per_trial\": 60000"
        << ",\n  \"advance_p50_ms\": " << percentile(advances, 31)
        << ",\n  \"advance_p95_ms\": " << percentile(advances, 60)
        << ",\n  \"checkpoint_p50_ms\": " << percentile(saves, 31)
        << ",\n  \"restore_p50_ms\": " << percentile(restores, 31)
        << ",\n  \"checkpoint_bytes\": " << checkpoint_bytes
        << ",\n  \"simulated_seconds_per_advance_wall_second\": " << 60000.0 * static_cast<double>(trials) / total_advance_ms
        << ",\n  \"setup_included_in_timing\": false,\n  \"memory_measured_by_core\": false\n}\n";
}
