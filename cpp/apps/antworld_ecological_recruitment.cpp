#include "ecological_recruitment_fixture.hpp"
#include "antworld/storage/store.hpp"
#include <charconv>
#include <filesystem>
#include <fstream>
#include <iostream>

int main(int argc,char** argv) {
    using namespace antworld;
    if (argc!=4 && argc!=5) return 1;
    try {
        const std::string_view input=argv[1];
        std::uint64_t seed{};
        const auto parsed=std::from_chars(input.data(),input.data()+input.size(),seed);
        if (parsed.ec!=std::errc{} || parsed.ptr!=input.data()+input.size() || !seed)
            throw std::invalid_argument("invalid recruitment seed");
        auto scene=ecological_assay::recruitment(seed,argv[2]);
        const auto output=std::filesystem::path(argv[3]);
        std::filesystem::create_directories(output);
        auto write=[&](const char* name,std::span<const std::uint8_t> bytes) {
            std::ofstream stream(output/name,std::ios::binary);
            stream.exceptions(std::ios::badbit|std::ios::failbit);
            stream.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
        };
        write("initial.chk",scene.world.checkpoint());
        scene.world.advance_to({30000});
        if (argc==5) {
            storage::Store store(output/"live.sqlite",{},storage::StoreFormat::Segmented);
            const auto initial=scene.world.checkpoint();
            const auto token=store.save(scene.world);
            auto restored=store.load(scene.scout.world);
            if (restored.token!=token || restored.world.checkpoint()!=initial)
                throw std::logic_error("recruitment restoration mismatch");
            scene.world=std::move(restored.world);
        }
        for (auto at=60000;at<=1200000;at+=60000) scene.world.advance_to({at});
        write("final.frame",scene.world.checkpoint_frame());
        const auto n=scene.world.nutrition_snapshot();
        if (n.introduced!=n.accounted || n.energy_input_nj!=n.body_energy_nj+n.dissipated_energy_nj)
            throw std::logic_error("recruitment budget mismatch");
        std::ofstream facts(output/"facts.bin",std::ios::binary);
        facts.exceptions(std::ios::badbit|std::ios::failbit);
        for (const auto& event:scene.world.committed_events()) {
            const auto bytes=encode_event(event);
            const std::array length{static_cast<char>(bytes.size()),static_cast<char>(bytes.size()>>8),char{},char{}};
            facts.write(length.data(),static_cast<std::streamsize>(length.size()));
            facts.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
        }
        std::ofstream ids(output/"identities.csv");
        ids.exceptions(std::ios::badbit|std::ios::failbit);
        ids << "role,id\nscout," << scene.scout.id.value << '\n';
        for (const auto receiver:scene.receivers) ids << "receiver," << receiver.id.value << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
