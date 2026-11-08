#include "s2_2_fixture.hpp"
#include <charconv>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <locale>

using namespace antworld;
int main(int argc, char** argv) {
    try {
        if (argc < 2 || argc > 3) throw std::invalid_argument("usage: antworld_s2_2_experiment OUTPUT_DIR [MAX_SEEDS_1_TO_512]");
        std::uint64_t seeds = 512;
        if (argc == 3) {
            const std::string_view a(argv[2]); const auto [end, error] = std::from_chars(a.data(), a.data()+a.size(), seeds);
            if (error != std::errc{} || end != a.data()+a.size() || !seeds || seeds > 512) throw std::invalid_argument("invalid assay seed count");
        }
        const std::string_view model = WorldRuntime::physics_version == 4 ? "s2.1" : (WorldRuntime::physics_version == 5 ? "s2.2" : (WorldRuntime::physics_version == 6 ? "s3" : "s4"));
        const std::filesystem::path root(argv[1]); std::filesystem::create_directories(root);
        std::ofstream out(root/"local.csv"); out.exceptions(std::ios::badbit | std::ios::failbit); out.imbue(std::locale::classic()); out << std::setprecision(17);
        out << "scope,model,physics_version,seed,context,mirror,treatment,age_ms,persistence_weight,primary,moves,selected_marked,occupancy,near_occupancy,initial_streak,max_streak,streak3,first_deviation_step,deviation_observed,restricted_first_deviation_step,deviations,reacquisitions,uturns,path_m,net_displacement_m,mean_distance_m,release_units,end_units,explore_weight,trail_weight,trail_cap_units,cutoff_units,half_life_s,cell_size_m,step_ms,decision_delay_ms,route_capacity,memory_enabled,trajectory\n";
        std::uint64_t count = 0;
        for (const std::string_view context : {"y_symmetric", "y_conflict", "straight", "bend", "lost", "visited"})
            for (const std::int64_t age : {0, 60000, 180000}) for (const std::uint32_t inertia : {0U, 20U, 40U}) {
                const bool primary = age == 0 && inertia == 20;
                for (std::uint64_t seed = 1; seed <= (primary ? seeds : std::min(seeds, std::uint64_t{128})); ++seed)
                    for (const bool mirror : {false, true}) for (const std::string_view treatment : {"present", "absent", "blind"}) {
                        fixture::TrailAssay a(context, treatment, mirror, age, inertia); a.run(seed); const auto n = a.length();
                        const auto first = a.trajectory.front(), last = a.trajectory.back();
                        const auto dx = static_cast<double>(last.x-first.x), dz = static_cast<double>(last.z-first.z);
                        out << "ENGINEERING_FIXTURE," << model << ',' << WorldRuntime::physics_version << ',' << seed << ',' << context << ',' << mirror << ',' << treatment << ','
                            << age << ',' << inertia << ',' << primary << ',' << n << ',' << (a.distance(a.trajectory[1]) == 0) << ','
                            << static_cast<double>(a.on_moves)/n << ',' << static_cast<double>(a.near_moves)/n << ',' << a.first_streak << ',' << a.max_streak << ',' << (a.max_streak >= 3) << ','
                            << a.first_deviation << ',' << (a.first_deviation >= 0) << ',' << (a.first_deviation < 0 ? static_cast<std::int64_t>(n) : a.first_deviation) << ','
                            << a.deviations << ',' << a.reacquisitions << ',' << a.uturns << ',' << n*0.01 << ',' << std::hypot(dx, dz)*0.01 << ',' << a.distance_sum/n << ','
                            << (treatment == "absent" ? 0 : a.strength(0)) << ',' << (treatment == "absent" ? 0 : a.strength(n)) << ",10," << a.config.trail_weight
                            << ",16,0.001,60,0.01,1100,1,48,0,";
                        for (std::size_t i = 0; i < a.trajectory.size(); ++i) { if (i) out << ';'; out << a.trajectory[i].x << ':' << a.trajectory[i].z; }
                        out << '\n'; ++count;
                    }
            }
        out.close(); std::cout << "PASS local trail assay model=" << model << " rows=" << count << '\n';
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
