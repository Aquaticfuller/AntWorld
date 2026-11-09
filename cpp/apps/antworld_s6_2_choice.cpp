#include "s6_fixture.hpp"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
using namespace antworld;
using s3_fixture::require;

int main(int argc, char **argv) {
  try {
    if (argc < 2 || argc > 3)
      throw std::invalid_argument(
          "usage: antworld_s6_2_choice OUTPUT_DIR [SEEDS=64]");
    const std::filesystem::path dir = argv[1];
    const auto seeds = argc == 3 ? std::stoul(argv[2]) : 64;
    require(seeds && seeds <= 64, "invalid seed count");
    require(!std::filesystem::exists(dir), "refusing existing output");
    std::filesystem::create_directories(dir);
    std::ofstream choices(dir / "choices.csv"), summary(dir / "summary.csv");
    choices.exceptions(std::ios::badbit | std::ios::failbit);
    summary.exceptions(std::ios::badbit | std::ios::failbit);
    choices << std::setprecision(17);
    choices << "seed,permutation,decision,time_ms,event_id,entity_id,id_rank,"
               "logical_slot,x_m,z_m,included,chosen,protein_ug\n";
    summary << "seed,permutation,decisions,gifts,events,state_hash,trace_hash,"
               "continuation_equal\n";
    // ENGINEERING_FIXTURE: document 40 freezes this selection-only assay.
    for (std::uint64_t seed = 1; seed <= seeds; ++seed)
      for (unsigned permutation = 0; permutation < 4; ++permutation) {
        WorldRuntime w({6, 62}, seed, {}, s6_fixture::limits());
        SocialConfig social;
        social.gift_first = social.local_work_continuation = true;
        w.configure_social(social);
        const auto colony = w.seed_colony();
        const auto donor = w.seed_ant(colony, {});
        PhysiologyConfig donor_config;
        donor_config.transfer_limit_ug = 1;
        PhysiologySeed provision;
        provision.crop.protein_ug = 1000;
        w.enable_physiology(donor, provision, donor_config);
        std::map<EntityId, std::pair<unsigned, PositionM>> slots;
        for (unsigned i = 0; i < 16; ++i) {
          const unsigned slot = permutation & 1 ? 15 - i : i;
          const PositionM position{
              (permutation & 2 ? -1.0 : 1.0) *
                  (static_cast<double>(slot % 4) - 1.5) * .0002,
              0, (static_cast<double>(slot / 4) - 1.5) * .0002};
          const auto a = w.seed_ant(colony, {position, LifeStage::Larva});
          slots.emplace(a.id, std::pair{slot, position});
          w.enable_physiology(a, {});
        }
        w.set_behavior(donor, IndividualBehavior::Nurse);
        WorldRuntime restored({9, 9}, 0, {}, s6_fixture::limits());
        restored.restore(w.checkpoint());
        std::uint64_t gifts{};
        for (unsigned decision = 0; decision < 64; ++decision) {
          const auto queue = w.pending_events();
          const auto wake =
              std::find_if(queue.begin(), queue.end(), [&](const auto &e) {
                return e.actor == donor.id &&
                       e.kind == ScheduledEvent::Kind::NutritionWake;
              });
          require(wake != queue.end(), "missing donor wake");
          const auto before = w.checkpoint();
          const auto contacts = w.sample_contacts(donor, decision);
          require(w.checkpoint() == before,
                  "sample query changed canonical state");
          const EventId cursor{w.summary().committed_events};
          w.advance_to(wake->key.time);
          const auto actions = w.pending_events();
          const auto action =
              std::find_if(actions.begin(), actions.end(), [&](const auto &e) {
                return e.actor == donor.id &&
                       e.kind == ScheduledEvent::Kind::Trophallaxis;
              });
          require(action != actions.end(), "no equal-demand proposal");
          const EntityId chosen{action->payload};
          const auto facts = w.events_after(cursor, 1000);
          const auto fact =
              std::find_if(facts.begin(), facts.end(), [&](const auto &e) {
                return e.kind == FactKind::NutritionDecision &&
                       e.actor == donor.id;
              });
          require(fact != facts.end() && fact->payload == decision + 1 &&
                      fact->random_value == contacts.candidates_examined,
                  "sample and actual decision disagree");
          const auto at = action->key.time;
          const EventId gift_cursor{w.summary().committed_events};
          w.advance_to(at);
          const auto transfers = w.events_after(gift_cursor, 1000);
          const auto gift = std::find_if(
              transfers.begin(), transfers.end(), [&](const auto &e) {
                return e.kind == FactKind::NutritionTransferred &&
                       e.actor == donor.id;
              });
          require(gift != transfers.end() && gift->transferred.protein_ug == 1,
                  "equal-demand gift did not commit");
          ++gifts;
          for (const auto &[id, slot] : slots) {
            const bool included =
                std::any_of(contacts.ants.begin(), contacts.ants.end(),
                            [&](auto ref) { return ref.id == id; });
            require(id != chosen || included,
                    "chosen recipient outside local sample");
            const auto p = *w.query_physiology({w.summary().world, id});
            require(p.crop.protein_ug + p.tissue_protein_ug < 100,
                    "assay eligibility became unequal");
            choices << seed << ',' << permutation << ',' << decision << ','
                    << at.milliseconds << ',' << gift->id.value << ','
                    << id.value << ',' << id.value - 3 << ',' << slot.first
                    << ',' << slot.second.x << ',' << slot.second.z << ','
                    << included << ',' << (id == chosen) << ','
                    << (id == chosen ? 1 : 0) << '\n';
          }
          s3_fixture::balanced(w);
        }
        restored.advance_to(w.summary().now);
        require(w.checkpoint() == restored.checkpoint(),
                "choice continuation diverged");
        const auto state = w.snapshot();
        summary << seed << ',' << permutation << ",64," << gifts << ','
                << state.committed_events << ',' << state.state_hash << ','
                << state.trace_hash << ",1\n";
      }
    std::cout << "PASS S6.2 equal-demand choices and restored continuation\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
