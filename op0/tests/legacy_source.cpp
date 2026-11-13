// Test-only writer for a real SQLite v1 store. Link against the unchanged Core and Store.
#include "antworld/storage/store.hpp"
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    try {
        antworld::WorldRuntime world({1, 2}, 7);
        const auto colony = world.seed_colony();
        world.seed_ant(colony, {});
        antworld::storage::Store store(argv[1]);
        const auto first = store.save(world);
        world.seed_food({0.01, 0, 0}, {50, 0, 10, 0});
        world.advance_to({1902});
        store.save(world, first);
        store.checkpoint_wal();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
