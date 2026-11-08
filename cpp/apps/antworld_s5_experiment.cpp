#include "antworld/storage/store.hpp"
#include "s3_fixture.hpp"
#include "s5_fixture.hpp"
#include <fstream>

using namespace antworld;
using namespace antworld::storage;
namespace {
void run(const std::filesystem::path &dir, std::ofstream &out, std::uint64_t seed, bool physiology,
         bool frequent) {
    auto build = [&]() {
        if (physiology) {
            s3_fixture::Brood fixture(seed, true, true);
            return std::move(fixture.world);
        }
        s4_fixture::Fixture f(seed, {}, {6, 12, 12}, true);
        f.world.set_behavior(f.worker, IndividualBehavior::Excavate);
        return std::move(f.world);
    };
    auto reference = build(), w = build();
    const std::int64_t end = physiology ? 180000 : 60000;
    const std::int64_t interval = frequent ? 5000 : 30000;
    const auto scenario = physiology ? "physiology" : "excavation";
    const auto path = dir / (std::string(scenario) + "-" + std::to_string(seed) +
                             (frequent ? "-frequent.sqlite" : "-sparse.sqlite"));
    s5_fixture::clean_database(path);
    Store store(path);
    auto token = store.save(w);
    for (std::int64_t t = interval; t <= end; t += interval) {
        w.advance_to({t});
        token = store.save(w, token);
        auto copy = store.load(token.world);
        s4_fixture::require(copy.world.checkpoint() == w.checkpoint(),
                            "intermediate durable restore mismatch");
        w = std::move(copy.world);
    }
    reference.advance_to({end});
    const bool same = reference.checkpoint() == w.checkpoint();
    s4_fixture::require(same, "observation/recovery frequency changed biology");
    const auto n = w.nutrition_snapshot();
    s3_fixture::balanced(w);
    const auto g = w.geometry_snapshot();
    if (g.configured)
        s4_fixture::balanced(w);
    auto value = [&](Metric metric) {
        const auto points = store.series(token.world, {}, metric, {end}, {end + 1}, 0, 100);
        return points.empty() ? 0 : points.back().value;
    };
    const auto deaths = store.flow_total(token.world, {}, Metric::Deaths, {0}, {end + 1});
    s4_fixture::require(deaths == value(Metric::DeadRetained), "death history does not reconcile");
    const auto metadata = w.summary();
    out << "ENGINEERING_FIXTURE," << scenario << ',' << seed << ',' << interval << ',' << end << ','
        << token.generation << ',' << same << ',' << metadata.committed_events << ','
        << metadata.pending_events << ',' << metadata.rng_state << ',' << value(Metric::Alive) << ','
        << value(Metric::WorkerAlive) << ',' << value(Metric::Egg) << ',' << value(Metric::Larva) << ','
        << value(Metric::Pupa) << ',' << deaths << ','
        << store.flow_total(token.world, {}, Metric::Emerged, {0}, {end + 1}) << ','
        << store.flow_total(token.world, {}, Metric::Trophallaxis, {0}, {end + 1}) << ','
        << g.geometry_revision << ',' << g.ledger.excavated_q3 << ',' << g.ledger.deposited_q3 << ','
        << n.introduced.carbs_ug - n.accounted.carbs_ug << ','
        << n.introduced.protein_ug - n.accounted.protein_ug << ','
        << n.introduced.water_ug - n.accounted.water_ug << ','
        << n.energy_input_nj - n.body_energy_nj - n.dissipated_energy_nj << ',' << w.checkpoint().size()
        << ',' << store.database_bytes() << '\n';
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc == 2 && std::string_view(argv[1]) == "--metrics") {
            std::cout << "| ID | Metric | Kind | Stored unit | Definition |\n|---:|---|---|---|---|\n";
            for (const auto &d : metric_definitions())
                std::cout << '|' << static_cast<unsigned>(d.id) << '|' << d.name << '|'
                          << (d.kind == MetricKind::Gauge ? "Gauge" : "Flow") << '|' << d.unit << '|'
                          << d.definition << "|\n";
            return 0;
        }
        if (argc < 2 || argc > 3)
            throw std::invalid_argument("usage: antworld_s5_experiment OUTPUT_DIR [SEEDS]");
        const std::filesystem::path dir = argv[1];
        std::filesystem::create_directories(dir);
        const unsigned seeds = argc == 3 ? static_cast<unsigned>(std::stoul(argv[2])) : 32;
        if (!seeds || seeds > 32)
            throw std::invalid_argument("fixed seed range is 1..32");
        std::ofstream out(dir / "summary.csv");
        out.exceptions(std::ios::badbit | std::ios::failbit);
        out << "scope,scenario,seed,save_interval_ms,simulation_ms,generations,exact_continuation,events,"
               "pending_events,rng_state,alive,adult_workers,eggs,larvae,pupae,deaths,emergences,internal_"
               "transfer_ug,geometry_edits,excavated_q3,deposited_q3,carb_residual_ug,protein_residual_ug,"
               "water_residual_ug,energy_residual_nj,checkpoint_bytes,database_bytes\n";
        for (unsigned seed = 1; seed <= seeds; ++seed)
            for (bool physiology : {true, false})
                for (bool frequent : {false, true})
                    run(dir, out, seed, physiology, frequent);
        std::cout << "PASS S5 " << seeds * 4 << " multi-seed durable comparisons\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL: " << e.what() << '\n';
        return 1;
    }
}
