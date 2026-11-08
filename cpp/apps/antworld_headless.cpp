#include "scenario.hpp"
#include "antworld/core/world_runtime.hpp"
#include "antworld/core/rng.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>

int main(int argc, char** argv) {
    using namespace antworld;
    try {
        std::map<std::string, std::string> options;
        for (int i = 1; i < argc; ++i) {
            const std::string key = argv[i];
            if (key == "--help" && argc == 2) {
                std::cout << "antworld_headless --scenario FILE [--advance-ms N] [--output FILE] [--diagnostic-events N]\n";
                return 0;
            }
            if (key != "--scenario" && key != "--advance-ms" && key != "--output" && key != "--diagnostic-events")
                throw std::invalid_argument("unknown option: " + key);
            if (++i >= argc || !options.emplace(key, argv[i]).second)
                throw std::invalid_argument("missing or duplicate option: " + key);
        }
        if (!options.contains("--scenario")) throw std::invalid_argument("--scenario is required");
        const std::filesystem::path input_path = options.at("--scenario");
        if (std::filesystem::file_size(input_path) > 1024 * 1024) throw std::invalid_argument("scenario exceeds 1 MiB");
        std::ifstream input(input_path, std::ios::binary);
        if (!input) throw std::runtime_error("cannot open scenario");
        const std::string text{std::istreambuf_iterator<char>(input), {}};
        const auto scenario = app::parse_scenario(text);
        auto target = scenario.observation;
        if (options.contains("--advance-ms")) {
            const auto value = app::parse_unsigned(options.at("--advance-ms"));
            if (value > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()))
                throw std::invalid_argument("advance target outside int64 range");
            target = {static_cast<std::int64_t>(value)};
        }
        WorldRuntime world(scenario.world, scenario.seed);
        if (options.contains("--diagnostic-events")) {
            const auto count = app::parse_unsigned(options.at("--diagnostic-events"));
            if (count > 1024) throw std::invalid_argument("diagnostic event count exceeds 1024");
            for (std::uint64_t i = 0; i < count; ++i)
                world.schedule({{static_cast<std::int64_t>(i + 1)}, Phase::Environment, 0, 0, i, DiagnosticAction::DrawRandom});
        }
        world.advance_to(target);
        const auto s = world.snapshot();
        std::ostringstream out;
        out << "{\n  \"world_id\": \"" << s.world.str() << "\",\n"
            << "  \"status\": \"ENGINEERING_FIXTURE\",\n  \"scope\": \"S0_EMPTY_WORLD\",\n"
            << "  \"seed\": " << s.seed << ",\n  \"sim_time_ms\": " << s.now.milliseconds
            << ",\n  \"revision\": " << s.revision << ",\n  \"pending_events\": " << s.pending_events
            << ",\n  \"committed_events\": " << s.committed_events
            << ",\n  \"rng_version\": \"" << Rng::version << "\",\n  \"schema_version\": " << WorldRuntime::schema_version
            << ",\n  \"physics_version\": " << WorldRuntime::physics_version
            << ",\n  \"hash_version\": \"fnv1a64-le-v1\",\n  \"state_hash\": \"" << hex64(s.state_hash)
            << "\",\n  \"trace_hash\": \"" << hex64(s.trace_hash) << "\"\n}\n";
        if (options.contains("--output")) {
            const std::filesystem::path path = options.at("--output");
            if (std::filesystem::weakly_canonical(path) == std::filesystem::weakly_canonical(input_path))
                throw std::invalid_argument("output must not overwrite the input scenario");
            if (!path.parent_path().empty()) std::filesystem::create_directories(path.parent_path());
            std::ofstream output(path, std::ios::binary | std::ios::trunc);
            output << out.str(); output.close();
            if (!output) throw std::runtime_error("cannot write output");
            std::cerr << "Output written to " << path.generic_string() << '\n';
        }
        std::cout << out.str();
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << '\n';
        return 2;
    }
}
