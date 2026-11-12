#include "process_memory.hpp"
#include "rm02_fixtures.hpp"
#include "wp5_fixtures.hpp"
#include "antworld/storage/store.hpp"

#include <chrono>
#include <iostream>

namespace {
using namespace antworld;
using namespace antworld::wp5;
using antworld::wp4::mass;
using antworld::wp4::output;
using antworld::wp4::require;
using Path = std::filesystem::path;
using Clock = std::chrono::steady_clock;

double elapsed(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

void write(std::ostream& out, std::span<const std::uint8_t> bytes) {
    out.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
}

void save(const Path& path, std::span<const std::uint8_t> bytes) {
    auto out = output(path);
    write(out, bytes);
    out.close();
}

void canonical(const WorldRuntime& world, const WorldRuntime& reference, const Path& path) {
    auto out = output(path);
    EventId cursor;
    while (cursor.value < world.summary().committed_events) {
        const auto page = world.events_after(cursor, rm02::fact_page);
        const auto expected = reference.events_after(cursor, rm02::fact_page);
        require(!page.empty() && page.size() == expected.size(), "WP-5 canonical history gap");
        for (std::size_t i = 0; i < page.size(); ++i) {
            const auto bytes = encode_event(page[i]);
            require(page[i].id.value == cursor.value + 1 && bytes == encode_event(expected[i]),
                    "WP-5 canonical bytes changed with observation or segmentation");
            const auto n = static_cast<std::uint32_t>(bytes.size());
            const std::array<std::uint8_t, 4> length{static_cast<std::uint8_t>(n), static_cast<std::uint8_t>(n >> 8),
                static_cast<std::uint8_t>(n >> 16), static_cast<std::uint8_t>(n >> 24)};
            write(out, length);
            write(out, bytes);
            cursor = page[i].id;
        }
    }
    out.close();
}

void configuration(const Scene& s, const Case& c, const Path& dir) {
    auto out = output(dir / "configuration.csv");
    out << "family,arm,workers,seed,world_id,queen,horizon_ms,midpoint_ms,egg_export_nj,egg_export_protein_ug,"
           "egg_export_water_ug,egg_heat_nj,classification\n"
        << c.family << ',' << c.arm << ',' << c.workers << ',' << c.seed << ',' << s.world.summary().world.str()
        << ',' << s.queen.id.value << ',' << c.end() << ',' << c.midpoint();
    if (s.queen.id.value) {
        const auto r = s.world.query_reproduction(s.queen).value().config;
        out << ',' << r.egg_energy_nj << ',' << r.egg_protein_ug << ',' << r.egg_water_ug << ',' << r.dissipated_energy_nj;
    } else out << ",,,,";
    out << ",ENGINEERING_FIXTURE\n";
    out.close();
    auto sources = output(dir / "initial_food.csv");
    sources << "resource,x_m,y_m,z_m,carbs_ug,protein_ug,water_ug,other_ug,reserve_carbs_ug,reserve_protein_ug,"
               "reserve_water_ug,reserve_other_ug,release_period_ms,release_carbs_ug,release_protein_ug,"
               "release_water_ug,release_other_ug\n";
    for (const auto& food : s.world.food_sources()) {
        const auto cycle = s.world.query_resource_cycle({s.world.summary().world, food.id});
        mass(position(sources << food.id.value, food.position), food.initial);
        if (cycle) mass(mass(sources, cycle->config.reserve) << ',' << cycle->config.interval.milliseconds,
                        cycle->config.release_limit);
        else sources << ",,,,,,,,,";
        sources << '\n';
    }
    sources.close();
    auto geometry = output(dir / "geometry_config.csv");
    const auto& g = s.geometry;
    geometry << "quantum_m,origin_x_m,origin_y_m,origin_z_m,dry_ug_per_q3,water_ug_per_q3,body_half_q,loaded_half_q,"
                "reach_q,max_patch_extent_q,work_ms,move_ms,decision_delay_ms,energy_nj_per_q3\n";
    position(geometry << g.quantum_m, g.origin_m) << ',' << g.dry_ug_per_q3 << ',' << g.water_ug_per_q3 << ','
        << g.body_half_q << ',' << g.loaded_half_q << ',' << g.reach_q << ',' << g.max_patch_extent_q << ','
        << g.work_duration.milliseconds << ',' << g.move_duration.milliseconds << ',' << g.decision_delay.milliseconds
        << ',' << g.dig_energy_nj_per_q3 << '\n';
    geometry.close();
    auto layout = output(dir / "layout.csv");
    layout << "kind,min_x_q,min_y_q,min_z_q,max_x_q,max_y_q,max_z_q\n";
    box(layout << "solid", g.initial_solid) << '\n';
    for (const auto region : s.voids) box(layout << "void", region) << '\n';
    for (const auto region : s.rocks) box(layout << "rock", region) << '\n';
    layout.close();
}

void geometry_history(const WorldRuntime& world, const Path& dir) {
    auto edits = output(dir / "edits.csv");
    edits << "edit,source,event,actor,parcel,kind,sim_ms,volume_q3,min_x_q,min_y_q,min_z_q,max_x_q,max_y_q,max_z_q\n";
    for (const auto& e : world.geometry_edits())
        box(edits << e.id.value << ',' << e.source.value << ',' << e.event.value << ',' << e.actor.value << ','
                  << e.parcel.value << ',' << (e.kind == SoilAction::Excavate ? "excavate" : "fill") << ','
                  << e.time.milliseconds << ',' << e.volume_q3, e.box) << '\n';
    edits.close();
    auto parcels = output(dir / "parcels.csv");
    parcels << "parcel,origin_edit,initial_q3,remaining_q3,carrier,state,x_m,y_m,z_m\n";
    for (const auto& p : world.soil_parcels())
        position(parcels << p.id.value << ',' << p.origin_edit.value << ',' << p.initial_q3 << ',' << p.remaining_q3
                         << ',' << p.carrier.value << ',' << static_cast<unsigned>(p.state), p.position) << '\n';
    parcels.close();
}

void run(const Path& dir, const Case& c) {
    auto scene = setup(c);
    auto& world = scene.world;
    const auto identity = world.summary().world;
    const auto limits = s6_3_1_fixture::limits();
    const auto initial = world.checkpoint();
    save(dir / "initial.chk", initial);
    configuration(scene, c, dir);
    rm02::Plan plan{"survival-excavation", {}, {}, true};
    for (const auto& ant : world.ant_states()) plan.focal.push_back(ant.id);
    const auto database = dir / "observer.sqlite";
    auto observer = std::make_unique<rm02::Observer>(database, world, plan);
    observer->start_background();
    wp4::Lineage lineage(dir);
    auto snapshots = output(dir / "cuts.csv");
    snapshots << "cut,cursor,sim_ms,examined,selected,records,dropped,payload_bytes,lineage_bytes,probe_bytes,"
                 "capture_ms,lineage_ms,probe_ms,submission_ms,nest_carbs_ug,nest_protein_ug,nest_water_ug,nest_other_ug,"
                 "soil_initial_q3,soil_remaining_q3,soil_carried_q3,soil_deposited_q3,geometry_revision,excavated_q3,filled_q3\n";
    auto routes = output(dir / "routes.csv");
    routes << "cut,cursor,sim_ms,geometry_revision," << probe_columns << '\n';
    auto work = output(dir / "excavators.csv");
    work << "cut,cursor,actor,enabled,decisions,digs,carrying_moves,deliveries,wake,action\n";
    auto inputs = output(dir / "inputs.csv");
    inputs << "issued_ms,execute_ms,kind,scheduled_id\n";
    const auto record = [&](Time now, Time at, std::string_view kind, ScheduledId id) {
        inputs << now << ',' << at << ',' << kind << ',' << id.value << '\n';
    };
    const auto midpoint = dir / "midpoint.sqlite";
    const auto focal = scene.workers.empty() ? scene.queen : scene.workers.front();
    std::size_t seq{}, peak_queue{};
    double advance_ms{}, drain_ms{}, writer_ms{}, restore_ms{};
    const auto drain = [&] {
        const auto begin = Clock::now();
        observer->flush();
        drain_ms += elapsed(begin);
        require(observer->committed_cuts() == seq, "WP-5 unpublished cut");
        const auto stats = observer->background_stats();
        writer_ms += stats.write_ms;
        peak_queue = std::max(peak_queue, stats.peak_payload_bytes);
    };
    const auto started = Clock::now();
    for (const auto at : cuts(c)) {
        auto begin = Clock::now();
        if (at) world.advance_to({at});
        advance_ms += elapsed(begin);
        if (c.family == "gate") gate_input(scene, world, at, record);
        begin = Clock::now();
        auto cut = observer->capture();
        const auto capture_ms = elapsed(begin);
        require(!cut.dropped && cut.end.time.milliseconds == at, "WP-5 sidecar has incomplete coverage");
        const auto payload = cut.payload.size();
        begin = Clock::now();
        const auto view = lineage.capture(world, ++seq, cut.end.cursor, cut.end.time);
        const auto lineage_ms = elapsed(begin);
        begin = Clock::now();
        const auto geometry = world.geometry_snapshot();
        routes << seq << ',' << cut.end.cursor << ',' << at << ',' << geometry.geometry_revision << ',';
        const auto probe_bytes = probe(routes, world, focal, scene.target);
        const auto probe_ms = elapsed(begin);
        begin = Clock::now();
        observer->submit(std::move(cut));
        const auto submission_ms = elapsed(begin);
        for (const auto& ant : world.ant_states()) {
            const auto state = world.query_excavator({identity, ant.id});
            if (state) work << seq << ',' << cut.end.cursor << ',' << ant.id.value << ',' << state->enabled << ','
                << state->decisions << ',' << state->digs << ',' << state->carrying_moves << ',' << state->deliveries
                << ',' << state->wake.value << ',' << state->action.value << '\n';
        }
        s6_3_1_fixture::conserved(world);
        const auto& soil = geometry.ledger;
        snapshots << seq << ',' << cut.end.cursor << ',' << at << ',' << cut.examined << ',' << cut.selected << ','
                  << cut.records << ',' << cut.dropped << ',' << payload << ',' << view << ',' << probe_bytes << ','
                  << capture_ms << ',' << lineage_ms << ',' << probe_ms << ',' << submission_ms;
        mass(snapshots, world.colonies().front().nest_food) << ',' << soil.initial_q3 << ',' << soil.remaining_q3 << ','
            << soil.carried_q3 << ',' << soil.deposited_q3 << ',' << geometry.geometry_revision << ','
            << soil.excavated_q3 << ',' << soil.filled_q3 << '\n';
        if (at != c.midpoint()) continue;
        drain();
        begin = Clock::now();
        const auto checkpoint = world.checkpoint();
        save(dir / "midpoint.chk", checkpoint);
        observer->anchor(checkpoint);
        observer.reset();
        {
            storage::Store store(midpoint, limits, storage::StoreFormat::Segmented);
            store.save(world);
            store.checkpoint_wal();
        }
        storage::Store store(midpoint, limits);
        auto restored = store.load(identity).world.checkpoint();
        require(restored == checkpoint, "WP-5 SQLite checkpoint changed");
        world.restore(restored);
        observer = std::make_unique<rm02::Observer>(database, world, plan, restored);
        require(observer->publish(observer->capture()) == rm02::Publish::Duplicate, "WP-5 duplicate cut was republished");
        observer->start_background();
        restore_ms = elapsed(begin);
    }
    drain();
    lineage.close();
    routes.close();
    work.close();
    inputs.close();
    snapshots.close();
    const auto final = world.checkpoint();
    save(dir / "final.chk", final);
    observer->anchor(final);
    observer.reset();
    const auto wall_ms = elapsed(started);
    const auto [rss, peak] = performance::memory();
    const auto replay_start = Clock::now();
    WorldRuntime reference(identity, c.seed, {}, limits);
    reference.restore(initial);
    if (c.family == "gate") {
        Time previous{};
        for (const auto at : cuts(c)) {
            if (at) {
                reference.advance_to({previous + (at - previous) / 2});
                reference.advance_to({at});
            }
            gate_input(scene, reference, at, [](auto...) {});
            previous = at;
        }
    } else reference.advance_to({c.end()});
    const auto state = world.snapshot();
    require(reference.snapshot() == state && reference.checkpoint() == final && restore_ms > 0,
            "WP-5 observer-off or segmented replay diverged");
    canonical(world, reference, dir / "canonical.bin");
    geometry_history(world, dir);
    auto result = output(dir / "summary.csv");
    result << "status,horizon_ms,events,cuts,state_hash,trace_hash,rng,exact_off,sqlite_midpoint_exact,"
              "advance_ms,wall_ms,midpoint_ms,drain_ms,writer_ms,replay_and_canonical_ms,peak_queue_bytes,"
              "rss_bytes,peak_rss_bytes,observer_bytes,midpoint_sqlite_bytes\n"
           << "PASS," << state.now.milliseconds << ',' << state.committed_events << ',' << seq << ','
           << state.state_hash << ',' << state.trace_hash << ',' << state.rng_state << ",1,1," << advance_ms << ','
           << wall_ms << ',' << restore_ms << ',' << drain_ms << ',' << writer_ms << ',' << elapsed(replay_start) << ','
           << peak_queue << ',' << rss << ',' << peak << ',' << std::filesystem::file_size(database) << ','
           << std::filesystem::file_size(midpoint) << '\n';
    result.close();
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 6, "usage: antworld_s6_4_wp5 OUTPUT FAMILY ARM WORKERS SEED");
        const auto workers = rm01::unsigned_integer(argv[4]);
        require(workers <= 32, "invalid WP-5 worker count");
        const Case c{argv[2], argv[3], static_cast<unsigned>(workers), rm01::unsigned_integer(argv[5])};
        validate(c);
        const Path dir = argv[1];
        require(std::filesystem::create_directories(dir), "WP-5 requires a new output directory");
        run(dir, c);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
