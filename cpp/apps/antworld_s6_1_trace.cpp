#include "s6_fixture.hpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>

using namespace antworld;
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      throw std::invalid_argument("usage: antworld_s6_1_trace OUTPUT_DIR");
    const std::filesystem::path dir = argv[1];
    if (std::filesystem::exists(dir / "facts.bin"))
      throw std::invalid_argument("refusing to overwrite trace");
    std::filesystem::create_directories(dir);
    std::ofstream facts(dir / "facts.bin", std::ios::binary),
        decisions(dir / "autonomy.csv"), summary(dir / "summary.csv");
    for (auto *f : {&facts, &decisions, &summary})
      f->exceptions(std::ios::badbit | std::ios::failbit);
    decisions << "event_id,source_id,time_ms,actor,program_before,program_"
                 "after,program_age_ms,at_depot,ready,"
                 "crop_protein_ug,sampled_contacts,sampled_needy_larvae,"
                 "compatible_crop_protein_ug,nest_protein_ug\n";
    s6_fixture::Integrated f(7);
    auto &w = f.world;
    EventId cursor;
    auto export_facts = [&] {
      for (const auto &e : w.events_after(cursor, 1000000)) {
        const auto bytes = encode_event(e);
        facts.write(reinterpret_cast<const char *>(bytes.data()),
                    static_cast<std::streamsize>(bytes.size()));
        cursor = e.id;
      }
    };
    export_facts();
    while (w.summary().now.milliseconds < 1800000) {
      const auto pending = w.pending_events();
      const auto at = pending.empty() ? SimTime{1800000}
                                      : std::min(pending.front().key.time,
                                                 SimTime{1800000});
      std::map<EntityId, std::pair<IndividualBehavior, SimTime>> previous;
      for (const auto &ant : w.ant_states()) {
        const auto a = w.query_autonomy({w.summary().world, ant.id});
        if (a)
          previous.emplace(
              ant.id,
              std::make_pair(
                  w.query_physiology({w.summary().world, ant.id})->behavior,
                  a->last_program_change));
      }
      w.advance_to(at);
      for (const auto &e : w.events_after(cursor, 1000000)) {
        if (e.kind != FactKind::AutonomyDecision)
          continue;
        const AntRef ref{w.summary().world, e.actor};
        const auto p = *w.query_physiology(ref);
        const auto ant = *w.query_ant(ref);
        const auto colony = *w.query_colony({ref.world, ant.colony});
        const auto sample = w.sample_contacts(
            ref, (e.payload - 1) ^ UINT64_C(0x45434f4c4f4759));
        std::uint64_t needy = 0, compatible = 0;
        for (const auto other : sample.ants) {
          const auto q = w.query_physiology(other);
          if (!q || w.query_ant(other)->stage != LifeStage::Larva)
            continue;
          const auto retained = q->crop.protein_ug + q->tissue_protein_ug;
          if (retained >= q->config.larval_protein_requirement_ug ||
              q->crop.total_ug() >= q->config.crop_capacity_ug)
            continue;
          ++needy;
          compatible +=
              std::min(p.crop.protein_ug,
                       q->config.larval_protein_requirement_ug - retained);
        }
        const auto old = previous.at(e.actor);
        const auto age = at.milliseconds - old.second.milliseconds;
        decisions << e.id.value << ',' << e.source.value << ','
                  << at.milliseconds << ',' << e.actor.value << ','
                  << static_cast<unsigned>(old.first) << ','
                  << static_cast<unsigned>(p.behavior) << ',' << age << ','
                  << (ant.position == colony.nest_position) << ','
                  << (old.first == IndividualBehavior::Paused || age >= 10000)
                  << ',' << p.crop.protein_ug << ',' << sample.ants.size()
                  << ',' << needy << ',' << compatible << ','
                  << colony.nest_food.protein_ug << '\n';
      }
      export_facts();
    }
    s6_fixture::balanced(w);
    const auto snapshot = w.snapshot();
    summary << "events,state_hash,trace_hash,final_crop_protein_ug\n"
            << snapshot.committed_events << ',' << snapshot.state_hash << ','
            << snapshot.trace_hash << ','
            << w.nutrition_snapshot().crop.protein_ug << '\n';
    std::cout << "PASS complete seed-7 observer replay: "
              << snapshot.committed_events << " facts\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
