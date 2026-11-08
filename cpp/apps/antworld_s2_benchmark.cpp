#include "s2_fixture.hpp"
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>

int main() {
    using namespace antworld; using Clock = std::chrono::steady_clock;
    try {
        std::cout << "scope,active_workers,simulated_ms,committed_events,moves,advance_p50_us,advance_p95_us,sim_seconds_per_wall_second,checkpoint_bytes,save_ms,restore_ms\n";
        RuntimeLimits limits; limits.committed_events = 1000000; limits.checkpoint_bytes = 256*1024*1024;
        for (const std::size_t population : {16u, 128u, 512u}) {
            fixture::Scene scene(12345, true, true, "barrier", population, false, limits);
            std::vector<double> timings(0); double elapsed_us = 0;
            constexpr std::int64_t duration = 180000;
            for (std::int64_t t = 1101; t < duration+1101; t += 1101) {
                const auto start = Clock::now(); scene.world.advance_to({std::min(t, duration)});
                const auto us = std::chrono::duration<double, std::micro>(Clock::now()-start).count();
                timings.push_back(us); elapsed_us += us;
            }
            const auto start = Clock::now(); const auto bytes = scene.world.checkpoint(); const auto saved = Clock::now();
            WorldRuntime restored({8, 9}, 0, {}, limits); restored.restore(bytes); const auto loaded = Clock::now();
            if (restored.checkpoint() != bytes) throw std::runtime_error("S2 benchmark restore mismatch");
            const auto summary = scene.world.summary(); const auto snapshot = scene.world.surface_snapshot();
            scene.world.advance_to({181101}); restored.advance_to({181101});
            if (scene.world.checkpoint() != restored.checkpoint()) throw std::runtime_error("S2 benchmark continuation mismatch");
            std::sort(timings.begin(), timings.end());
            std::cout << std::setprecision(9) << "ENGINEERING_FIXTURE," << population << ',' << duration << ',' << summary.committed_events << ','
                << snapshot.counters.moves << ',' << timings[timings.size()/2] << ',' << timings[timings.size()*95/100] << ','
                << static_cast<double>(duration)*1000/elapsed_us << ',' << bytes.size() << ','
                << std::chrono::duration<double, std::milli>(saved-start).count() << ','
                << std::chrono::duration<double, std::milli>(loaded-saved).count() << '\n';
        }
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
