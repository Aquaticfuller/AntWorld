#include "antworld/storage/live_history.hpp"
#include "scenario.hpp"
#include <fstream>
#include <iostream>
#include <iterator>

using namespace antworld;
using namespace antworld::storage;
namespace {
RuntimeLimits archive_limits() {
    RuntimeLimits limits;
    limits.committed_events=2000000;
    return limits;
}

SaveToken publish(LiveHistoryWriter& writer,Store& store,WorldRuntime& world,
                  std::optional<SaveToken> predecessor = {}) {
    if (store.format()==StoreFormat::Legacy) return store.save(world,predecessor);
    if (!writer.try_submit(world,predecessor)) throw std::logic_error("archive save admission failed");
    return writer.finish(world).token;
}

void output(const LoadedWorld &loaded) {
    const auto state = loaded.world.snapshot();
    std::cout << "{\"world_id\":\"" << state.world.str() << "\",\"generation\":\"" << loaded.token.generation
              << "\",\"time_ms\":" << state.now.milliseconds << ",\"revision\":\"" << state.revision
              << "\",\"events\":\"" << state.committed_events << "\",\"pending_events\":\""
              << state.pending_events << "\",\"state_hash\":\"" << hex64(state.state_hash)
              << "\",\"trace_hash\":\"" << hex64(state.trace_hash) << "\"}\n";
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc == 2 && std::string_view(argv[1]) == "--help") {
            std::cout << "antworld_archive create DATABASE SCENARIO\n"
                      << "antworld_archive advance DATABASE WORLD_ID TARGET_MS\n"
                      << "antworld_archive inspect DATABASE WORLD_ID\n"
                      << "antworld_archive migrate LEGACY_DATABASE NEW_SHADOW_DATABASE\n";
            return 0;
        }
        if (argc < 4)
            throw std::invalid_argument("use antworld_archive --help");
        const std::string_view mode = argv[1];
        if ((mode == "create" || mode == "inspect" || mode == "migrate") ? argc != 4 : mode == "advance" ? argc != 5 : true)
            throw std::invalid_argument("unknown mode or invalid argument count");
        const std::filesystem::path database = argv[2];
        const auto limits=archive_limits();
        if (mode=="migrate") {
            auto migration_limits=limits;
            // The v1 reader must validate an explicit export containing the whole journal.
            migration_limits.checkpoint_bytes=1024ULL*1024*1024;
            Store::migrate_legacy(database,argv[3],migration_limits);
            std::cout<<"{\"migration\":\"verified\"}\n";
        } else if (mode == "create") {
            const std::filesystem::path input = argv[3];
            if (std::filesystem::file_size(input) > 1024 * 1024)
                throw std::length_error("scenario exceeds 1 MiB");
            std::ifstream stream(input, std::ios::binary);
            if (!stream)
                throw std::runtime_error("cannot open scenario");
            const std::string json{std::istreambuf_iterator<char>(stream), {}};
            const auto scenario = app::parse_scenario(json);
            WorldRuntime world(scenario.world,scenario.seed,{},limits);
            LiveHistoryWriter writer(database,limits);
            writer.bind(world);
            world.advance_to(scenario.observation);
            if (!database.parent_path().empty())
                std::filesystem::create_directories(database.parent_path());
            Store store(database,limits,StoreFormat::Segmented);
            if (store.latest(scenario.world)) throw std::invalid_argument("archive world already exists");
            const auto token=publish(writer,store,world);
            output({std::move(world), token});
        } else {
            if (!std::filesystem::is_regular_file(database))
                throw std::invalid_argument("database does not exist");
            const auto id = WorldId::parse(argv[3]);
            Store store(database,limits);
            auto loaded = store.load(id);
            if (mode == "advance") {
                const auto target = app::parse_unsigned(argv[4]);
                if (target > INT64_MAX)
                    throw std::invalid_argument("target exceeds SimTime range");
                LiveHistoryWriter writer(database,limits);
                if (store.format()==StoreFormat::Segmented) writer.bind(loaded.world);
                loaded.world.advance_to({static_cast<std::int64_t>(target)});
                loaded.token=publish(writer,store,loaded.world,loaded.token);
            }
            output(loaded);
        }
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
