#include "antworld/core/world_runtime.hpp"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() {
    using namespace antworld;
    using Clock = std::chrono::steady_clock;
    constexpr std::int64_t rounds = 256;
    try {
        std::cout << "scope,ants,active_per_round,rounds,simulated_ms,advance_p50_us,advance_p95_us,submit_advance_p50_us,sim_seconds_per_advance_wall_second,checkpoint_bytes,save_ms,restore_ms\n";
        for (const std::size_t population : {32u, 2000u, 20000u}) {
            WorldRuntime w({1, 2}, 12345); const auto colony = w.seed_colony(); std::vector<AntRef> ants;
            for (std::size_t i = 0; i < population; ++i) ants.push_back(w.seed_ant(colony, {}));
            const auto food = w.seed_food({}, {UINT64_C(4000)*population, 0, 0, 0});
            std::vector<double> advances, totals; double advance_us = 0;
            for (std::int64_t round = 1; round <= rounds; ++round) {
                const auto start = Clock::now();
                for (std::size_t i = 0; i < 32; ++i) w.submit({ants[i], {round*1000}, ActionKind::CollectFood, food, {}, 1});
                const auto submitted = Clock::now(); w.advance_to({round*1000}); const auto end = Clock::now();
                const auto us = std::chrono::duration<double, std::micro>(end-submitted).count();
                advances.push_back(us); advance_us += us; totals.push_back(std::chrono::duration<double, std::micro>(end-start).count());
            }
            const auto before_save = Clock::now(); const auto saved = w.checkpoint(); const auto after_save = Clock::now();
            WorldRuntime restored({3, 4}, 0); restored.restore(saved); const auto after_load = Clock::now();
            if (restored.checkpoint() != saved || w.summary().food_ledger.carried.total_ug() != 32*static_cast<std::uint64_t>(rounds))
                throw std::runtime_error("benchmark conservation/restore validation failed");
            std::sort(advances.begin(), advances.end()); std::sort(totals.begin(), totals.end());
            std::cout << "ENGINEERING_FIXTURE," << population << ",32," << rounds << ',' << rounds*1000 << ','
                << advances[128] << ',' << advances[243] << ',' << totals[128] << ','
                << static_cast<double>(rounds)*1e6/advance_us << ',' << saved.size() << ','
                << std::chrono::duration<double, std::milli>(after_save-before_save).count() << ','
                << std::chrono::duration<double, std::milli>(after_load-after_save).count() << '\n';
        }
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
