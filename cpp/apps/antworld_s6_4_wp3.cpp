#include "rm02_observer.hpp"
#include "s2_1_fixture.hpp"
#include "s2_2_fixture.hpp"
#include "process_memory.hpp"
#include "antworld/storage/store.hpp"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <initializer_list>
#include <sstream>

namespace {
using namespace antworld;
using namespace antworld::rm02;
using Clock = std::chrono::steady_clock;
using Path = std::filesystem::path;
using namespace std::string_view_literals;

constexpr std::int64_t second = 1000;
constexpr std::size_t view_limit = 2 * 1024 * 1024;
constexpr double neighbor_radius_m = .012; // ENGINEERING_FIXTURE host query, independent of the motor.

void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}

struct Case {
    std::string_view family, layout, signal, age;
    bool memory;
    std::uint64_t seed;

    bool scout() const { return family == "scout" || family == "density"; }
    std::int64_t age_ms() const { return age == "fresh" ? 0 : age == "aged" ? 120 * second : 600 * second; }
    std::int64_t window_ms() const { return (scout() ? 90 : 120) * second; }

    WorldId world_id() const {
        // Stable case-specific identity, with the RNG seed shared across paired arms.
        std::uint64_t high = UINT64_C(14695981039346656037);
        for (auto component : {family, layout, signal, age, memory ? "1"sv : "0"sv}) {
            for (char ch : component) high = (high ^ static_cast<unsigned char>(ch)) * UINT64_C(1099511628211);
            high = (high ^ static_cast<unsigned char>('/')) * UINT64_C(1099511628211);
        }
        return {high, seed};
    }
};

void validate(const Case& c) {
    const auto one_of = [](std::string_view v, std::initializer_list<std::string_view> values) {
        return std::find(values.begin(), values.end(), v) != values.end();
    };
    require(c.seed && one_of(c.signal, {"absent", "blind", "present"}) &&
            one_of(c.age, {"fresh", "aged", "expired"}), "invalid signal, age or seed");
    require((c.family == "factorial" && one_of(c.layout, {"near", "far"}) && c.age == "fresh") ||
            (c.family == "scout" && c.layout == "near" && !c.memory) ||
            (c.family == "density" && one_of(c.layout, {"sparse8", "dense8", "dense32"}) &&
             !c.memory && c.signal == "present" && c.age == "fresh") ||
            (c.family == "disruption" && one_of(c.layout, {"open", "wall", "gap", "deplete", "empty"}) &&
             c.memory && c.signal == "absent" && c.age == "fresh") ||
            (c.family == "prepared" && c.layout == "straight" && !c.memory), "invalid WP-3 case combination");
}

std::ofstream output(const Path& path) {
    std::ofstream stream(path, std::ios::binary);
    stream.exceptions(std::ios::badbit | std::ios::failbit);
    stream << std::setprecision(17);
    return stream;
}

void write_bytes(std::ostream& stream, std::span<const std::uint8_t> bytes) {
    stream.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
}

void save(const Path& path, std::span<const std::uint8_t> bytes) {
    auto stream = output(path);
    write_bytes(stream, bytes);
    stream.close();
}

double elapsed(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

std::ostream& point(std::ostream& stream, PositionM p) {
    return stream << p.x << ',' << p.y << ',' << p.z;
}

struct Actor { AntRef ref; std::string_view role; };

struct Scene {
    WorldRuntime world;
    SurfaceConfig grid{{-.10, 0, -.07}, 21, 15, .01};
    ColonyRef colony;
    FoodRef resource;
    AntRef scout, drainer;
    std::vector<Actor> actors;
    std::vector<Cell> blocked;

    explicit Scene(const Case& c) : world(c.world_id(), c.seed) {
        const bool partition = c.layout == "wall" || c.layout == "gap";
        if (partition) for (std::int32_t z = 0; z < 15; ++z)
            if (c.layout == "wall" || z != 10) blocked.push_back({11, z});
        BehaviorConfig behavior;
        behavior.memory_enabled = c.memory;
        behavior.trails_enabled = c.signal != "absent";
        if (c.signal == "blind") behavior.trail_weight = 0;
        world.configure_surface(grid, blocked, behavior);
        const auto nest = fixture::position(grid, {10, 7});
        colony = world.seed_colony(nest);
        const auto seed = [&](std::string_view role, PositionM p, std::uint64_t capacity = 800) {
            const auto ant = world.seed_ant(colony, {p, LifeStage::Adult, Caste::Worker, capacity});
            actors.push_back({ant, role});
            return ant;
        };
        if (c.scout()) {
            scout = seed("scout", nest);
            seed("host_started", nest);
            seed("host_started", nest);
            const auto policy = seed("policy_enrolled", nest);
            // Paused assay sentinel starts with the same reserves after every field age.
            // The ordinary active surcharge and normal uptake/death logic remain available.
            PhysiologyConfig budgets;
            budgets.basal_nj_per_ms = 0;
            budgets.water_loss_ug_per_period = 0;
            world.enable_physiology(policy, {}, budgets);
            const auto count = c.family == "scout" ? 4 : c.layout == "dense32" ? 32 : 8;
            for (int i = 3; i < count; ++i) {
                const auto cell = Cell{2 + i % 3, 2 + i};
                seed("passive", c.layout == "sparse8" ? fixture::position(grid, cell) : nest);
            }
            world.configure_social();
        } else {
            seed("forager", nest);
        }
        const auto food = fixture::position(grid, c.layout == "far" ? Cell{17, 8} : Cell{13, 7});
        if (c.layout != "empty") {
            const FoodMass mass = c.layout == "far" ? FoodMass{1200, 200, 400, 0} : FoodMass{8000, 1000, 1000, 0};
            resource = world.seed_food(food, mass);
        }
        if (c.family == "disruption" && c.layout != "empty") drainer = seed("fixture", food, 10000);
    }
};

// Every supplemental table uses the same owner-thread cut sequence and cursor.
// These are detached read-only values with no historical decision reconstruction.
class Views {
public:
    explicit Views(const Path& dir) : actors(output(dir / "actors.csv")), steps(output(dir / "local_steps.csv")),
        cues(output(dir / "food_cues.csv")), routes(output(dir / "routes.csv")), field(output(dir / "field.csv")),
        resources(output(dir / "resources.csv")) {
        actors << "cut,cursor,sim_ms,actor,role,sensing_status,cell_x,cell_z,steps,food_cues,neighbors,"
                  "forager_exists,forager_enabled,mode,decisions,collections,learned_at_ms,wake_id,action_id,"
                  "path_cells,memory_cells,position_revision,autonomy_enabled\n";
        steps << "cut,cursor,sim_ms,actor,direction,cell_x,cell_z,effective_trail_units\n";
        cues << "cut,cursor,sim_ms,actor,resource,cell_x,cell_z,distance_cells,first_direction\n";
        routes << "cut,cursor,sim_ms,actor,route,ordinal,cell_x,cell_z\n";
        field << "cut,cursor,sim_ms,colony,cell_x,cell_z,effective_trail_units\n";
        resources << "cut,cursor,sim_ms,resource,x_m,y_m,z_m,carbs_ug,protein_ug,water_ug,other_ug\n";
    }

    std::size_t capture(const Scene& scene, const Cut& cut, std::size_t sequence) {
        const auto& world = scene.world;
        const auto prefix = std::to_string(sequence) + ',' + std::to_string(cut.end.cursor) + ',' +
                            std::to_string(cut.end.time.milliseconds) + ',';
        std::array<std::ostringstream, 6> rows;
        for (auto& row : rows) row << std::setprecision(17);
        auto& [a, s, c, r, f, food] = rows;
        for (const auto& actor : scene.actors) {
            const auto ant = world.query_ant(actor.ref).value();
            const auto nav = world.query_forager(actor.ref);
            const auto policy = world.query_autonomy(actor.ref);
            std::optional<LocalObservation> local;
            if (ant.alive()) local = world.sense(actor.ref);
            const auto actor_prefix = prefix + std::to_string(ant.id.value) + ',';
            a << actor_prefix << actor.role << ',' << (local ? "CUT_SNAPSHOT" : "NOT_APPLICABLE_DEAD") << ',';
            if (local) {
                const auto nearby = world.query_neighborhood(actor.ref, neighbor_radius_m);
                const auto living = std::ranges::count_if(nearby.ants, [&](AntRef other) {
                    return world.query_ant(other).value().alive();
                });
                a << local->current.x << ',' << local->current.z << ',' << local->step_count << ','
                  << local->food_count << ',' << living << ',';
                for (std::uint32_t i = 0; i < local->step_count; ++i) {
                    const auto& step = local->steps[i];
                    s << actor_prefix << static_cast<unsigned>(step.direction) << ',' << step.cell.x << ','
                      << step.cell.z << ',' << step.trail_units << '\n';
                }
                for (std::uint32_t i = 0; i < local->food_count; ++i) {
                    const auto& cue = local->food[i];
                    c << actor_prefix << cue.resource.value << ',' << cue.cell.x << ',' << cue.cell.z << ','
                      << cue.distance_cells << ',' << static_cast<unsigned>(cue.first_step) << '\n';
                }
            } else a << ",,,,,";
            a << nav.has_value() << ',';
            if (nav) {
                a << nav->enabled << ',' << static_cast<unsigned>(nav->mode) << ',' << nav->decisions << ','
                  << nav->collections << ',' << nav->learned_at.milliseconds << ',' << nav->wake.value << ','
                  << nav->action.value << ',' << nav->path_size << ',' << nav->memory_size << ',';
                const auto cells = [&](std::string_view name, std::span<const Cell> route) {
                    for (std::size_t i = 0; i < route.size(); ++i)
                        r << actor_prefix << name << ',' << i << ',' << route[i].x << ',' << route[i].z << '\n';
                };
                cells("trace", std::span(nav->path).first(nav->path_size));
                cells("learned", std::span(nav->memory).first(nav->memory_size));
            } else a << ",,,,,,,,,";
            a << ant.position_revision << ',' << (policy && policy->enabled) << '\n';
        }
        for (const auto& item : world.trails())
            f << prefix << item.colony.value << ',' << item.cell.x << ',' << item.cell.z << ',' << item.units << '\n';
        for (const auto& item : world.food_sources()) {
            point(food << prefix << item.id.value << ',', item.position);
            for (auto mass : item.remaining.components()) food << ',' << mass;
            food << '\n';
        }
        std::size_t bytes{};
        for (const auto& row : rows) bytes += row.view().size();
        require(bytes <= view_limit, "WP-3 cut view budget exceeded");
        actors << a.view(); steps << s.view(); cues << c.view(); routes << r.view();
        field << f.view(); resources << food.view();
        return bytes;
    }

    void close() {
        actors.close(); steps.close(); cues.close(); routes.close(); field.close(); resources.close();
    }

private:
    std::ofstream actors, steps, cues, routes, field, resources;
};

template<class Advance>
std::int64_t train(WorldRuntime& world, AntRef scout, Advance advance) {
    constexpr SimTime cap{240 * second};
    EventId cursor{world.summary().committed_events};
    world.start_foraging(scout);
    while (world.summary().now < cap) {
        const auto pending = world.pending_events();
        require(!pending.empty(), "scout lost its schedule before the training cap");
        advance(std::min(cap, pending.front().key.time).milliseconds);
        for (const auto& e : world.events_after(cursor, fact_page)) {
            cursor = e.id;
            if (e.actor == scout.id && e.kind == FactKind::FoodDelivered) return e.time.milliseconds;
        }
        require(cursor.value == world.summary().committed_events, "scout training facts exceeded page");
    }
    return -1;
}

template<class Advance, class Capture, class Input>
std::int64_t drive(const Scene& scene, WorldRuntime& world, const Case& c, Advance advance, Capture capture, Input input) {
    std::int64_t release{};
    if (c.scout()) {
        capture(0, false);
        const auto delivered = train(world, scene.scout, advance);
        input(world.summary().now.milliseconds, scene.scout, delivered < 0 ? "scout_cap" : "scout_delivery", 0);
        const auto retired = world.summary().now.milliseconds + 1;
        const auto death = world.schedule_lifecycle(scene.scout, {retired}, LifeStage::Dead);
        input(retired, scene.scout, "fixture_retirement", death.value);
        advance(retired);
        release = retired + c.age_ms();
        if (release != retired) {
            capture(retired, false);
            advance(release);
        }
        for (const auto& actor : scene.actors) {
            if (actor.role == "host_started") {
                world.start_foraging(actor.ref);
                input(release, actor.ref, "host_start", 0);
            } else if (actor.role == "policy_enrolled") {
                world.set_autonomy(actor.ref);
                input(release, actor.ref, "policy_enrollment", 0);
            }
        }
    } else {
        const auto worker = scene.actors.front().ref;
        world.start_foraging(worker);
        input(0, worker, "host_start", 0);
        if (c.layout == "deplete") {
            const auto event = world.submit({scene.drainer, {20 * second}, ActionKind::CollectFood, scene.resource, {}, 10000});
            input(20 * second, scene.drainer, "fixture_stock_removal_request", event.value);
        }
    }
    capture(release, false);
    for (std::int64_t offset = 5 * second; offset <= c.window_ms(); offset += 5 * second) {
        advance(release + offset);
        capture(release + offset, offset == c.window_ms() / 2);
    }
    return release;
}

void canonical(const WorldRuntime& world, const Path& path) {
    auto stream = output(path);
    EventId cursor{};
    while (cursor.value < world.summary().committed_events) {
        const auto page = world.events_after(cursor, fact_page);
        require(!page.empty(), "WP-3 canonical history gap");
        for (const auto& fact : page) {
            const auto bytes = encode_event(fact);
            const auto size = static_cast<std::uint32_t>(bytes.size());
            const std::array<std::uint8_t, 4> length{static_cast<std::uint8_t>(size), static_cast<std::uint8_t>(size >> 8),
                static_cast<std::uint8_t>(size >> 16), static_cast<std::uint8_t>(size >> 24)};
            write_bytes(stream, length);
            write_bytes(stream, bytes);
            cursor = fact.id;
        }
    }
    stream.close();
}

void live(const Path& dir, const Case& c) {
    Scene scene(c);
    auto& world = scene.world;
    const auto identity = world.summary().world;
    const auto initial = world.checkpoint();
    save(dir / "initial.chk", initial);
    auto config = output(dir / "configuration.csv");
    const auto behavior = world.surface_snapshot().behavior;
    config << "family,layout,signal,memory,age,age_ms,seed,world_id,window_ms,cell_size_m,sensing_cells,"
              "step_duration_ms,decision_delay_ms,field_interval_ms,trail_weight,half_life_s,deposit_units,"
              "trail_cutoff_units,policy_fixture_basal_nj_per_ms,policy_fixture_water_loss_ug_per_s,classification\n"
           << c.family << ',' << c.layout << ',' << c.signal << ',' << c.memory << ',' << c.age << ',' << c.age_ms()
           << ',' << c.seed << ',' << identity.str() << ',' << c.window_ms() << ',' << scene.grid.cell_size_m << ','
           << behavior.sensing_radius_cells << ',' << behavior.step_duration.milliseconds << ','
           << behavior.decision_delay.milliseconds << ',' << behavior.field_interval.milliseconds << ','
           << behavior.trail_weight << ',' << behavior.trail_half_life_s << ',' << behavior.deposit_units << ','
           << behavior.trail_cutoff_units << (c.scout() ? ",0,0" : ",,") << ",ENGINEERING_FIXTURE\n";
    config.close();
    auto geometry = output(dir / "layout.csv");
    geometry << "feature,cell_x,cell_z\n" << "nest,10,7\n";
    for (auto cell : scene.blocked) geometry << "blocked," << cell.x << ',' << cell.z << '\n';
    geometry.close();

    Plan plan{"foraging-recruitment", {}, {}, true};
    plan.foraging = true;
    for (const auto& actor : scene.actors) plan.focal.push_back(actor.ref.id);
    const auto database = dir / "observer.sqlite";
    auto observer = std::make_unique<Observer>(database, world, plan);
    observer->start_background();
    Views views(dir);
    auto cuts = output(dir / "cuts.csv");
    cuts << "cut,cursor,sim_ms,examined,selected,records,dropped,canonical_payload_bytes,view_bytes,"
            "capture_ms,submission_ms,view_ms,soil_initial_q3,soil_remaining_q3,soil_carried_q3,soil_deposited_q3\n";
    auto interventions = output(dir / "inputs.csv");
    interventions << "sim_ms,actor,input,scheduled_id\n";
    std::size_t sequence{}, peak_queued{};
    double advance_ms{}, flush_ms{}, writer_ms{}, midpoint_ms{};
    const auto drain = [&] {
        const auto start = Clock::now();
        observer->flush();
        flush_ms += elapsed(start);
        require(observer->committed_cuts() == sequence, "WP-3 unpublished cut");
        const auto stats = observer->background_stats();
        writer_ms += stats.write_ms;
        peak_queued = std::max(peak_queued, stats.peak_payload_bytes);
    };
    const auto capture = [&](std::int64_t time, bool midpoint) {
        const auto start = Clock::now();
        auto cut = observer->capture();
        const auto capture_ms = elapsed(start);
        require(!cut.dropped && cut.end.time.milliseconds == time, "incomplete WP-3 capture");
        const auto bytes = cut.payload.size();
        const auto submission = Clock::now();
        observer->submit(std::move(cut));
        const auto submission_ms = elapsed(submission);
        const auto start_view = Clock::now();
        const auto view_bytes = views.capture(scene, cut, ++sequence);
        const auto view_ms = elapsed(start_view);
        const auto soil = world.geometry_snapshot().ledger;
        require(soil.initial_q3 == soil.remaining_q3 + soil.carried_q3 + soil.deposited_q3, "WP-3 soil ledger mismatch");
        cuts << sequence << ',' << cut.end.cursor << ',' << time << ',' << cut.examined << ',' << cut.selected << ','
             << cut.records << ',' << cut.dropped << ',' << bytes << ',' << view_bytes << ',' << capture_ms << ','
             << submission_ms << ',' << view_ms << ',' << soil.initial_q3 << ',' << soil.remaining_q3 << ','
             << soil.carried_q3 << ',' << soil.deposited_q3 << '\n';
        if (!midpoint) return;
        drain();
        const auto recovery = Clock::now();
        const auto checkpoint = world.checkpoint();
        save(dir / "midpoint.chk", checkpoint);
        observer->anchor(checkpoint);
        observer.reset();
        const auto store_path = dir / "midpoint.sqlite";
        {
            storage::Store store(store_path, {}, storage::StoreFormat::Segmented);
            store.save(world);
        }
        storage::Store store(store_path);
        const auto loaded = store.load(identity).world.checkpoint();
        require(loaded == checkpoint, "WP-3 authoritative SQLite recovery diverged");
        world.restore(loaded);
        observer = std::make_unique<Observer>(database, world, plan, loaded);
        require(observer->publish(observer->capture()) == Publish::Duplicate, "WP-3 midpoint duplicated a cut");
        observer->start_background();
        midpoint_ms = elapsed(recovery);
    };
    const auto start = Clock::now();
    const auto release = drive(scene, world, c, [&](auto time) {
        const auto begin = Clock::now(); world.advance_to({time}); advance_ms += elapsed(begin);
    }, capture, [&](auto time, AntRef actor, auto name, auto scheduled) {
        interventions << time << ',' << actor.id.value << ',' << name << ',' << scheduled << '\n';
    });
    drain();
    views.close();
    cuts.close();
    interventions.close();
    const auto final = world.checkpoint();
    save(dir / "final.chk", final);
    observer->anchor(final);
    observer.reset();
    const auto wall_ms = elapsed(start);
    const auto [rss, peak] = performance::memory();
    const auto state = world.snapshot();
    canonical(world, dir / "canonical.bin");

    WorldRuntime off({91, 3}, c.seed);
    off.restore(initial);
    const auto direct = drive(scene, off, c, [&](auto time) { off.advance_to({time}); }, [](auto, auto) {},
                              [](auto, auto, auto, auto) {});
    require(direct == release && off.checkpoint() == final, "WP-3 observer on/off continuation diverged");
    auto result = output(dir / "summary.csv");
    result << "status,release_ms,horizon_ms,events,cuts,state_hash,trace_hash,rng,exact_off,sqlite_midpoint_exact,"
              "advance_ms,wall_ms,midpoint_ms,drain_ms,writer_ms,peak_queue_bytes,rss_bytes,peak_rss_bytes,"
              "observer_bytes,midpoint_sqlite_bytes\n"
           << "PASS," << release << ',' << state.now.milliseconds << ',' << state.committed_events << ',' << sequence
           << ',' << state.state_hash << ',' << state.trace_hash << ',' << state.rng_state << ",1,1," << advance_ms
           << ',' << wall_ms << ',' << midpoint_ms << ',' << flush_ms << ',' << writer_ms << ',' << peak_queued
           << ',' << rss << ',' << peak << ',' << std::filesystem::file_size(database) << ','
           << std::filesystem::file_size(dir / "midpoint.sqlite") << '\n';
    result.close();
}

void prepared(const Path& dir, const Case& c) {
    fixture::TrailAssay assay(c.layout, c.signal, false, c.age_ms(), BehaviorConfig{}.persistence_weight);
    auto config = output(dir / "configuration.csv");
    config << "family,layout,signal,memory,age,age_ms,seed,classification\nprepared," << c.layout << ','
           << c.signal << ",0," << c.age << ',' << c.age_ms() << ',' << c.seed << ",ENGINEERING_FIXTURE\n";
    config.close();
    auto result = output(dir / "prepared.csv");
    result << "step,from_x,from_z,to_x,to_z,age_ms,visible_marked_steps,max_visible_units,chosen_mode,marked_line,"
              "provenance\n";
    for (std::uint32_t i = 0; i < assay.length(); ++i) {
        const auto local = assay.observe(i);
        double strength{};
        std::uint32_t marked{};
        for (std::uint32_t j = 0; j < local.step_count; ++j) {
            const auto units = local.steps[j].trail_units;
            marked += units > 0;
            strength = std::max(strength, units);
        }
        assay.step(c.seed);
        const auto to = assay.trajectory.back();
        result << i + 1 << ',' << local.current.x << ',' << local.current.z << ',' << to.x << ',' << to.z << ','
               << local.time.milliseconds << ',' << marked << ',' << strength << ',' << static_cast<unsigned>(assay.ant.mode)
               << ',' << (assay.distance(to) == 0) << ",DETACHED_ENGINEERING_FIXTURE\n";
    }
    result.close();
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 8, "usage: antworld_s6_4_wp3 OUTPUT FAMILY LAYOUT SIGNAL MEMORY AGE SEED");
        const auto memory = std::string_view(argv[5]);
        require(memory == "0"sv || memory == "1"sv, "invalid memory setting");
        const auto seed_text = std::string_view(argv[7]);
        std::uint64_t seed{};
        const auto* const seed_end = seed_text.data() + seed_text.size();
        const auto parsed = std::from_chars(seed_text.data(), seed_end, seed);
        require(parsed.ec == std::errc{} && parsed.ptr == seed_end, "invalid seed integer");
        const Case c{argv[2], argv[3], argv[4], argv[6], memory == "1"sv, seed};
        validate(c);
        const Path dir = argv[1];
        require(std::filesystem::create_directories(dir), "WP-3 output must be new");
        if (c.family == "prepared") prepared(dir, c);
        else live(dir, c);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "WP-3 assay: " << error.what() << '\n';
        return 1;
    }
}
