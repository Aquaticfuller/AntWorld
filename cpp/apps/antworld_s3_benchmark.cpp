#include "s3_fixture.hpp"
#include <chrono>
#include <algorithm>
#include <iostream>
#include <vector>

using namespace antworld;
using namespace antworld::s3_fixture;
using Clock = std::chrono::steady_clock;
double ms(Clock::time_point start) { return std::chrono::duration<double,std::milli>(Clock::now()-start).count(); }
int main() {
    try {
        std::cout << "scope,individuals,active_nurses,advance_ms,advance_p50_ms,advance_p95_ms,save_ms,restore_ms,checkpoint_bytes,committed_events,pending_events\n";
        for (const auto count : {1U,100U,1000U}) for (const auto active : {0U,1U,count}) {
            if (count == 1 && active == 1) continue; // The larger cases include one active nurse.
            RuntimeLimits limits; limits.events_per_timestamp = 10000; limits.committed_events = 100000;
            WorldRuntime w({3,5},42,{},limits); const auto c = w.seed_colony(); std::vector<AntRef> ants(0);
            for (unsigned i = 0; i < count; ++i) {
                const auto a = w.seed_ant(c,{}); ants.push_back(a);
                w.enable_physiology(a,{{100,400,400,100},1000000000,1000,0});
            }
            for (unsigned i = 0; i < active; ++i) w.set_behavior(ants[i],IndividualBehavior::Nurse);
            std::vector<double> samples(0); double advance = 0;
            for (std::int64_t at = 1000; at <= 10000; at += 1000) {
                const auto step = Clock::now(); w.advance_to({at}); const auto elapsed = ms(step); advance += elapsed; samples.push_back(elapsed);
            }
            std::sort(samples.begin(),samples.end()); auto start = Clock::now();
            balanced(w); start = Clock::now(); const auto bytes = w.checkpoint(); const auto save = ms(start);
            WorldRuntime restored({9,9},0,{},limits); start = Clock::now(); restored.restore(bytes); const auto restore = ms(start);
            require(restored.checkpoint() == bytes,"benchmark restore divergence");
            std::cout << "ENGINEERING_FIXTURE," << count << ',' << active << ',' << advance << ',' << samples[4] << ',' << samples[9] << ',' << save << ',' << restore << ',' << bytes.size()
                << ',' << w.summary().committed_events << ',' << w.summary().pending_events << '\n';
        }
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
