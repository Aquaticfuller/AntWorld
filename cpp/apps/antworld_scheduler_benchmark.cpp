#include "antworld/core/world_runtime.hpp"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <vector>

// Intentionally uses only S0 APIs so the identical source can measure the reviewed baseline.
int main() {
    using namespace antworld;
    using Clock = std::chrono::steady_clock;
    std::cout << "scope,pending_events,operations,trials,p50_us_per_schedule_cancel,p95_us_per_schedule_cancel\n";
    for (const std::int64_t population : {128, 1024, 4096}) {
        WorldRuntime w({1, 2}, 12345);
        for (std::int64_t i = 0; i < population; ++i) w.schedule({{100000+i}});
        std::vector<double> times;
        for (int trial = 0; trial < 21; ++trial) {
            const auto start = Clock::now();
            for (int i = 0; i < 100; ++i) { const auto id = w.schedule({{200000}}); w.cancel(id); }
            times.push_back(std::chrono::duration<double, std::micro>(Clock::now()-start).count()/100);
        }
        std::sort(times.begin(), times.end());
        std::cout << "ENGINEERING_FIXTURE," << population << ",100,21," << times[10] << ',' << times[19] << '\n';
    }
}
