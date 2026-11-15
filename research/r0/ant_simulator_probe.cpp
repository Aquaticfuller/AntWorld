#include <fstream>
#include <iostream>

#include "simulation/ant/ant_updater.hpp"
#include "simulation/world/distance_field_builder.hpp"

// Standalone probe for the pinned AntSimulator build. No upstream source is
// vendored here. Join its include and SFML link paths as for src/main.cpp.
int main() {
    RNGf::initialize();
    Conf::WORLD_WIDTH = 320;
    Conf::WORLD_HEIGHT = 240;
    World world(320, 240);
    ColonyBase base({60, 120}, 12);
    world.addMarker(base.position, Mode::ToHome, 60, 0, true);
    for (int y = 18; y < 43; ++y) world.addWall(sf::Vector2i(40, y));
    for (int y = 23; y < 38; ++y)
        for (int x = 62; x < 72; ++x) world.addFoodAt(sf::Vector2i{x, y}, 20);
    DistanceFieldBuilder::computeDistance(world.map);
    std::vector<Ant> ants;
    for (int i = 0; i < 24; ++i) {
        ants.emplace_back(60, 120, RNGf::getFullRange(PI), 0);
        ants.back().id = static_cast<int16_t>(i);
    }
    std::cout << "step,ant,x,y,angle,wall_hits,phase,delivered\n";
    constexpr float dt = 1.f / 60;
    for (int i = 0; i < 2400; ++i) {
        world.update(dt);
        for (auto& ant : ants) AntUpdater::initialUpdate(ant, world, dt);
        for (auto& ant : ants) {
            AntUpdater::update(ant, world, dt);
            ant.checkColony(base);
            if (i % 3 == 0)
                std::cout << i << ',' << ant.id << ',' << ant.position.x << ',' << ant.position.y << ','
                          << ant.direction.getCurrentAngle() << ',' << ant.hits << ',' << static_cast<int>(ant.phase)
                          << ',' << base.food << '\n';
        }
    }
}
