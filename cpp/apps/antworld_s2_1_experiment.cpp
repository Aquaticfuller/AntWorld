#include "s2_1_fixture.hpp"
#include <charconv>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <locale>

using namespace antworld;
namespace {
constexpr std::int64_t window_ms = 180000;
struct Metrics {
    std::int64_t discovery{-1}, collection{-1}, delivery{-1};
    std::uint64_t steps{}, before_steps{}, route_steps{}, trail_before{}, trail_moves{}, decisions{}, signal_decisions{};
    std::uint64_t collections{}, deliveries{}, collected{}, delivered{};
};
void field(std::ostream& out, const WorldRuntime& world, std::string_view model, std::uint64_t seed,
    std::string_view orientation, std::string_view treatment, std::int64_t delay, std::int64_t elapsed) {
    const auto samples = world.trails();
    const auto prefix = [&] { out << model << ',' << seed << ',' << orientation << ',' << treatment << ',' << delay << ',' << elapsed << ','; };
    if (samples.empty()) { prefix(); out << "-1,-1,0\n"; }
    for (const auto& s : samples) { prefix(); out << s.cell.x << ',' << s.cell.z << ',' << s.units << '\n'; }
}
void social(std::ostream& out, std::ostream& fields, std::uint64_t seeds, std::string_view model) {
    out << "scope,experiment,model,physics_version,seed,orientation,treatment,release_delay_ms,training_limit_ms,window_ms,trained,training_delivery_ms,release_time_ms,"
        "discovery_observed,first_discovery_ms,followup_ms,first_collection_ms,first_delivery_ms,path_before_discovery_m,path_window_m,"
        "route_steps_before_discovery,steps_before_discovery,route_overlap_fraction,trail_moves_before_discovery,trail_moves,decisions,signal_decisions,"
        "collections,deliveries,collected_ug,delivered_ug,trace_edges,release_trace_coverage,release_continuous,release_trail_cells,release_trail_units,"
        "release_trail_min,release_trail_max,end_trail_units,initial_memory_cells,cell_size_m,sensing_radius,route_capacity,step_ms,decision_delay_ms,"
        "half_life_s,deposit_units,trail_cap_units,trail_cutoff_units,explore_weight,persistence_weight,trail_weight,memory_enabled,food_x,food_z\n";
    fields << "model,seed,orientation,treatment,release_delay_ms,elapsed_ms,cell_x,cell_z,units\n";
    for (std::uint64_t seed = 1; seed <= seeds; ++seed) for (const bool reflected : {false, true}) {
        std::int64_t paired_training = -2;
        std::vector<Cell> paired_route(0);
        for (const std::string_view treatment : {"present", "absent", "blind"}) {
            fixture::Recruitment fixture(seed, reflected, treatment); const bool trained = fixture.train();
            if (paired_training == -2) { paired_training = fixture.delivered_at.milliseconds; paired_route = fixture.experienced_route; }
            if (fixture.delivered_at.milliseconds != paired_training || fixture.experienced_route != paired_route)
                throw std::logic_error("paired scout histories differ before first return");
            const auto base = fixture.world.checkpoint(); const auto orientation = reflected ? "west" : "east";
            for (const std::int64_t delay : {0, 180000, 600000}) {
                fixture.world.restore(base); auto& world = fixture.world;
                Metrics m; std::int64_t release = -1;
                std::uint64_t covered = 0; double minimum = 0, maximum = 0;
                SurfaceSnapshot released = world.surface_snapshot();
                if (trained) {
                    release = fixture.retired_at.milliseconds+delay; world.advance_to({release}); released = world.surface_snapshot();
                    std::set<Cell> trail_cells;
                    const auto trail = world.trails();
                    if (!trail.empty()) minimum = trail.front().units;
                    for (const auto& s : trail) { trail_cells.insert(s.cell); minimum = std::min(minimum, s.units); maximum = std::max(maximum, s.units); }
                    for (std::size_t i = 0; i+1 < fixture.experienced_route.size(); ++i) if (trail_cells.contains(fixture.experienced_route[i])) ++covered;
                    if (world.query_forager(fixture.novice) || world.sense(fixture.novice).food_count)
                        throw std::logic_error("novice not naive or food visible at release");
                    world.start_foraging(fixture.novice); const auto initial = *world.query_forager(fixture.novice);
                    if (initial.memory_size || initial.decisions || initial.path_size != 1 || world.query_ant(fixture.novice)->carried_food.total_ug())
                        throw std::logic_error("novice initial state differs from fresh nest worker");
                    field(fields, world, model, seed, orientation, treatment, delay, 0);
                    EventId cursor{world.summary().next_event_id-1}; Cell previous{10, 7};
                    std::set<std::pair<Cell, Cell>> experienced_edges;
                    for (std::size_t i = 1; i < paired_route.size(); ++i)
                        experienced_edges.emplace(std::min(paired_route[i-1], paired_route[i]), std::max(paired_route[i-1], paired_route[i]));
                    std::int64_t sample = release+30000;
                    while (world.summary().now.milliseconds < release+window_ms) {
                        const auto pending = world.pending_events();
                        const auto next = pending.empty() ? release+window_ms : pending.front().key.time.milliseconds;
                        world.advance_to({std::min({next, sample, release+window_ms})});
                        for (const auto& e : world.events_after(cursor, 64)) {
                            cursor = e.id; if (e.actor != fixture.novice.id) continue;
                            if (e.kind == FactKind::ForagingDecision) {
                                ++m.decisions; const auto sensed = world.sense(fixture.novice);
                                bool has_signal = false;
                                for (std::uint32_t i = 0; i < sensed.step_count; ++i) if (sensed.steps[i].trail_units > 0) has_signal = true;
                                if (has_signal) ++m.signal_decisions;
                                if (e.resource.value && m.discovery < 0) m.discovery = e.time.milliseconds-release;
                            }
                            if (e.kind == FactKind::Moved) {
                                const auto current = fixture.locate(e.position); ++m.steps;
                                if (e.mode == BehaviorMode::FollowTrail) ++m.trail_moves;
                                if (m.discovery < 0) {
                                    ++m.before_steps;
                                    if (experienced_edges.contains({std::min(previous, current), std::max(previous, current)})) ++m.route_steps;
                                    if (e.mode == BehaviorMode::FollowTrail) ++m.trail_before;
                                }
                                previous = current;
                            }
                            if (e.kind == FactKind::FoodCollected) {
                                ++m.collections; m.collected += e.transferred.total_ug();
                                if (m.collection < 0) m.collection = e.time.milliseconds-release;
                            }
                            if (e.kind == FactKind::FoodDelivered) {
                                ++m.deliveries; m.delivered += e.transferred.total_ug();
                                if (m.delivery < 0) m.delivery = e.time.milliseconds-release;
                            }
                        }
                        if (world.summary().now.milliseconds == sample) {
                            field(fields, world, model, seed, orientation, treatment, delay, sample-release); sample += 30000;
                        }
                        fixture::check_ingredients(world);
                    }
                }
                const auto final = world.checkpoint(); world.restore(final);
                if (world.checkpoint() != final) throw std::logic_error("recruitment final checkpoint mismatch");
                const auto edges = fixture.experienced_route.empty() ? 0 : fixture.experienced_route.size()-1;
                const auto p = released.behavior;
                out << "ENGINEERING_FIXTURE,social," << model << ',' << WorldRuntime::physics_version << ',' << seed << ',' << orientation << ',' << treatment << ','
                    << delay << ",1800000," << window_ms << ',' << trained << ',' << fixture.delivered_at.milliseconds << ',' << release << ','
                    << (m.discovery >= 0) << ',' << m.discovery << ',' << (trained ? (m.discovery >= 0 ? m.discovery : window_ms) : 0) << ','
                    << m.collection << ',' << m.delivery << ',' << static_cast<double>(m.before_steps)*fixture.grid.cell_size_m << ','
                    << static_cast<double>(m.steps)*fixture.grid.cell_size_m << ',' << m.route_steps << ',' << m.before_steps << ','
                    << (m.before_steps ? static_cast<double>(m.route_steps)/static_cast<double>(m.before_steps) : 0) << ','
                    << m.trail_before << ',' << m.trail_moves << ',' << m.decisions << ',' << m.signal_decisions << ','
                    << m.collections << ',' << m.deliveries << ',' << m.collected << ',' << m.delivered << ',' << edges << ','
                    << (edges ? static_cast<double>(covered)/static_cast<double>(edges) : 0) << ',' << (trained && edges && covered == edges) << ','
                    << released.active_trail_cells << ',' << released.trail_units << ',' << minimum << ',' << maximum << ',' << world.surface_snapshot().trail_units
                    << ",0," << fixture.grid.cell_size_m << ',' << p.sensing_radius_cells << ',' << p.route_capacity << ',' << p.step_duration.milliseconds << ','
                    << p.decision_delay.milliseconds << ',' << p.trail_half_life_s << ',' << p.deposit_units << ',' << p.trail_cap_units << ',' << p.trail_cutoff_units << ','
                    << p.explore_weight << ',' << p.persistence_weight << ',' << p.trail_weight << ",0," << (reflected ? 2 : 18) << ",7\n";
            }
        }
        std::cout << "completed seed=" << seed << " orientation=" << (reflected ? "west" : "east") << '\n';
    }
}
void choice_audits(std::ostream& out, std::string_view model) {
    out << "scope,experiment,model,physics_version,seed,orientation,treatment,selected_x,selected_z,swapped_x,swapped_z,reordered_x,reordered_z,"
        "id_swap_invariant,cue_order_invariant,lower_id_selected,signal_units,trail_weight,follow_label\n";
    BehaviorConfig p; ForagerState f; f.path_size = 1; f.path[0] = {2, 2}; f.heading = Direction::North;
    LocalObservation local; local.current = {2, 2}; local.step_count = 4;
    local.steps = {{{{2, 3}, Direction::North, 0}, {{3, 2}, Direction::East, 0}, {{2, 1}, Direction::South, 0}, {{1, 2}, Direction::West, 0}}};
    for (std::uint64_t seed = 1; seed <= 4096; ++seed) {
        for (const bool rotated : {false, true}) {
            auto cue = local; cue.food_count = 2;
            const auto a = rotated ? local.steps[0] : local.steps[1], b = rotated ? local.steps[2] : local.steps[3];
            cue.food[0] = {{100}, a.cell, 1, a.direction}; cue.food[1] = {{200}, b.cell, 1, b.direction};
            const auto selected = choose_behavior(seed, {7}, false, f, cue, p).destination;
            std::swap(cue.food[0].resource, cue.food[1].resource);
            const auto swapped = choose_behavior(seed, {7}, false, f, cue, p).destination;
            std::swap(cue.food[0], cue.food[1]);
            const auto reordered = choose_behavior(seed, {7}, false, f, cue, p).destination;
            out << "ENGINEERING_FIXTURE,bias," << model << ',' << WorldRuntime::physics_version << ',' << seed << ',' << (rotated ? "north_south" : "east_west")
                << ",equal_food," << selected.x << ',' << selected.z << ',' << swapped.x << ',' << swapped.z << ',' << reordered.x << ',' << reordered.z << ','
                << (selected == swapped) << ',' << (swapped == reordered) << ',' << (selected == a.cell) << ",0,180,0\n";
        }
        for (const std::string_view treatment : {"absent", "fresh", "weak", "blind"}) {
            auto cue = local; auto config = p;
            cue.steps[1].trail_units = treatment == "absent" ? 0 : (treatment == "weak" ? 0.04 : 1);
            if (treatment == "blind") config.trail_weight = 0;
            const auto choice = choose_behavior(seed, {7}, false, f, cue, config);
            out << "ENGINEERING_FIXTURE,response," << model << ',' << WorldRuntime::physics_version << ',' << seed << ",east," << treatment << ','
                << choice.destination.x << ',' << choice.destination.z << ",,,,,,,," << cue.steps[1].trail_units << ',' << config.trail_weight << ','
                << (choice.mode == BehaviorMode::FollowTrail) << '\n';
        }
    }
}
}
int main(int argc, char** argv) {
    try {
        if (argc < 2 || argc > 4) throw std::invalid_argument("usage: antworld_s2_1_experiment OUTPUT_DIR [SEEDS_1_TO_64] [MODEL_LABEL]");
        std::uint64_t seeds = 64;
        if (argc > 2) {
            const std::string_view arg(argv[2]); const auto [end, error] = std::from_chars(arg.data(), arg.data()+arg.size(), seeds);
            if (error != std::errc{} || end != arg.data()+arg.size() || !seeds || seeds > 64) throw std::invalid_argument("invalid seed count");
        }
        const std::string_view compiled = WorldRuntime::physics_version == 3 ? "s2-baseline" : (WorldRuntime::physics_version == 4 ? "s2.1" : "s2.2");
        const std::string_view model = argc > 3 ? argv[3] : compiled;
        if (model != compiled)
            throw std::invalid_argument("model label does not match the compiled physics version");
        const std::filesystem::path root(argv[1]); std::filesystem::create_directories(root);
        std::ofstream rows(root/"social.csv"), fields(root/"fields.csv"), choices(root/"choices.csv");
        for (auto* stream : {&rows, &fields, &choices}) {
            stream->exceptions(std::ios::failbit | std::ios::badbit); stream->imbue(std::locale::classic()); *stream << std::setprecision(17);
        }
        choice_audits(choices, model); social(rows, fields, seeds, model); rows.close(); fields.close(); choices.close(); return 0;
    } catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
