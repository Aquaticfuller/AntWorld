#include "wp6b_fixture.hpp"
#include "antworld/storage/store.hpp"

#include <charconv>
#include <cstdio>
#include <iostream>
#include <span>
#include <sstream>
#include <string_view>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
using namespace antworld;
using namespace antworld::wp6b;

// The same protected, balanced shaft profile as the portable M0 witness.
Case live_case(std::uint64_t id, std::uint64_t seed) {
    Case c{};
    c.identity = id;
    c.seed = seed;
    c.arm = "balanced";
    c.care = c.integrated_assay = c.micro_world = c.expanded_history = true;
    c.food = {6000, 3000, 18000, 0};
    c.profile = nominal();
    c.profile.worker.absorption_period = {6 * hour_ms};
    c.profile.worker.behavior_interval = {hour_ms};
    c.profile.worker.carbohydrate_yield_nj_per_ug = 8000000;
    c.profile.feeding_persistence = FoundingFeedingPersistence{{2 * day_ms}, 750000};
    c.profile.early_access = FoundingEarlyAccess{true, true};
    c.profile.provisioning = FoundingProvisioning{true};
    c.profile.dietary = FoundingDietaryAccess{true, true, true, true};
    auto& e = c.ecological.emplace();
    e.distance_clock = e.floor_space = e.recruitment = e.activity_cost = true;
    e.portable_field = e.brood_space = e.portable_care_motion = true;
    e.cue_lifetime = {6 * hour_ms};
    return c;
}

std::string word(std::istringstream& request) {
    std::string result;
    require(static_cast<bool>(request >> result), "Missing live Core argument");
    return result;
}

void end(std::istringstream& request) {
    std::string extra;
    require(!(request >> extra), "Unexpected live Core argument");
}

std::uint64_t number(std::istringstream& request) {
    const auto token = word(request);
    std::uint64_t value{};
    const auto [last, error] = std::from_chars(token.data(), token.data() + token.size(), value);
    require(error == std::errc{} && last == token.data() + token.size(), "Invalid live Core number");
    return value;
}

std::filesystem::path staged_save(std::istringstream& request) {
    const auto id = word(request);
    require(id.size() == 32 && id.find_first_not_of("0123456789abcdef") == std::string::npos,
            "Invalid live save staging ID");
    return id + ".sqlite";
}

void message(std::string_view status, std::string_view data = {}) {
    std::cout << status << ' ' << data.size() << '\n' << data << std::flush;
}

void payload(std::span<const std::uint8_t> bytes) {
    message("OK", {reinterpret_cast<const char*>(bytes.data()), bytes.size()});
}

void recent(const WorldRuntime& world) {
    constexpr std::uint64_t cap = 120;
    const auto count = world.summary().committed_events;
    std::vector<std::uint8_t> bytes;
    for (const auto& fact : world.events_after({count > cap ? count - cap : 0}, cap)) {
        const auto data = encode_event(fact);
        const auto size = data.size();
        bytes.insert(bytes.end(), {static_cast<std::uint8_t>(size), static_cast<std::uint8_t>(size >> 8),
                                   static_cast<std::uint8_t>(size >> 16), static_cast<std::uint8_t>(size >> 24)});
        bytes.insert(bytes.end(), data.begin(), data.end());
    }
    if (bytes.empty()) message("OK");
    else payload(bytes);
}
} // namespace

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdout), _O_BINARY) == -1) return 1;
#endif
    const auto limits = assay_limits(live_case(1, 1));
    std::optional<WorldRuntime> world;
    std::string line;
    while (std::getline(std::cin, line)) {
        try {
            std::istringstream request(line);
            const auto command = word(request);
            if (command == "HELLO") {
                end(request);
                message("OK", "antworld.m0.live.v1");
            } else if (command == "NEW") {
                const auto id = number(request), seed = number(request);
                end(request);
                require(id != 0, "A live colony needs a world ID");
                auto scene = setup(live_case(id, seed), limits);
                const auto frame = scene.world.checkpoint_frame();
                world.emplace(std::move(scene.world));
                payload(frame);
            } else if (command == "LOAD") {
                const auto path = staged_save(request);
                const auto id = WorldId::parse(word(request));
                end(request);
                require(std::filesystem::is_regular_file(path), "Live load snapshot is missing");
                storage::Store store(path, limits);
                require(store.format() == storage::StoreFormat::Segmented, "Live load needs a segmented save");
                auto loaded = store.load(id);
                const auto model = loaded.world.ecological_closure();
                require(model && model->brood_space, "Live load needs a MicroWorld save");
                const auto frame = loaded.world.checkpoint_frame();
                world.emplace(std::move(loaded.world));
                payload(frame);
            } else {
                require(world.has_value(), "Create or load a colony first");
                if (command == "ADVANCE") {
                    const auto target = number(request);
                    end(request);
                    require(target <= ((UINT64_C(1) << 53) - 1), "Live time exceeds the observation clock");
                    world->advance_to({static_cast<std::int64_t>(target)});
                    payload(world->checkpoint_frame());
                } else if (command == "FRAME") {
                    end(request);
                    payload(world->checkpoint_frame());
                } else if (command == "RECENT") {
                    end(request);
                    recent(*world);
                } else if (command == "SAVE") {
                    const auto path = staged_save(request);
                    end(request);
                    require(!std::filesystem::exists(path), "Live save staging path already exists");
                    {
                        storage::Store store(path, limits, storage::StoreFormat::Segmented);
                        store.save(*world);
                        store.checkpoint_wal();
                    }
                    message("OK");
                } else {
                    throw std::invalid_argument("Unknown live Core command");
                }
            }
        } catch (const std::exception& error) {
            message("ERR", error.what());
        }
        if (!std::cout) return 1;
    }
    return 0;
}
