#include "antworld/core/inspection.hpp"
#include "s6_3_1_fixture.hpp"
#include <iostream>
using namespace antworld;
using s3_fixture::require;
namespace {
void observe() {
  s6_3_1_fixture::World a(1), b(1);
  std::vector<inspection::Decision> observations;
  {
    inspection::Scope scope(a.queen.world, a.queen.id, observations);
    a.world.advance_to({7 * s6_3_fixture::day});
  }
  b.world.advance_to({s6_3_fixture::day});
  b.world.advance_to({7 * s6_3_fixture::day});
  require(!observations.empty(), "observer recorded no decisions");
  require(a.world.checkpoint() == b.world.checkpoint(),
          "observer or partition changed authority");
  require(!inspection::target.output, "observer scope leaked");
  for (const auto &o : observations) {
    require(o.actor != a.queen.id.value, "queen entered worker policy");
    require(o.candidates <= a.world.social_config()->encounter_budget,
            "observer exceeded encounter bound");
  }
  s6_3_1_fixture::World failed(2);
  const auto before = failed.world.checkpoint();
  bool caught = false;
  try {
    inspection::Scope invalid(failed.queen.world, EntityId{99999},
                              observations);
    failed.world.advance_to({s6_3_fixture::day});
  } catch (const std::logic_error &) {
    caught = true;
    observations.clear();
  }
  require(caught && failed.world.checkpoint() == before,
          "observer failure escaped rollback");
  s6_3_fixture::conserved(a.world);
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc != 2 || std::string_view(argv[1]) != "OBSERVER")
      throw std::invalid_argument("unknown S6.3.1 test");
    observe();
    std::cout << "PASS " << argv[1] << '\n';
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
