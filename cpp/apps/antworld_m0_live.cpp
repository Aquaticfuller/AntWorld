#include "wp6b_fixture.hpp"
#include "r0_diagnostic_history.hpp"
#include "r0r1_fixture.hpp"
#include "traffic_observer_fixture.hpp"
#include "founding_habitat.hpp"
#include "process_memory.hpp"
#include "antworld/storage/store.hpp"

#include <algorithm>
#include <charconv>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <span>
#include <sstream>
#include <string_view>
#include <utility>
#include <vector>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
using namespace antworld;
using namespace antworld::wp6b;

// The same protected, balanced shaft profile as the portable M0 witness.
Case live_case(std::uint64_t id, std::uint64_t seed, std::optional<WorkerActivityTiming> timing = {}) {
    Case c{};
    c.identity = id;
    c.seed = seed;
    c.arm = "balanced";
    c.care = c.integrated_assay = c.micro_world = c.expanded_history = true;
    c.food = {6000, 3000, 18000, 0};
    c.profile = nominal();
    c.profile.worker.absorption_period = {6 * hour_ms};
    c.profile.worker.behavior_interval = {hour_ms};
    c.profile.worker.carbohydrate_yield_nj_per_ug = 8000000;
    c.profile.feeding_persistence = FoundingFeedingPersistence{{2 * day_ms}, 750000};
    c.profile.early_access = FoundingEarlyAccess{true, true};
    c.profile.provisioning = FoundingProvisioning{true};
    c.profile.dietary = FoundingDietaryAccess{true, true, true, true};
    auto& e = c.ecological.emplace();
    e.distance_clock = e.floor_space = e.recruitment = e.activity_cost = true;
    e.portable_field = e.brood_space = e.portable_care_motion = true;
    e.cue_lifetime = {6 * hour_ms};
    e.worker_activity_timing = timing;
    return c;
}

std::string word(std::istringstream& request) {
    std::string result;
    require(static_cast<bool>(request >> result), "Missing live Core argument");
    return result;
}

void end(std::istringstream& request) {
    std::string extra;
    require(!(request >> extra), "Unexpected live Core argument");
}

std::uint64_t number(std::istringstream& request) {
    const auto token = word(request);
    std::uint64_t value{};
    const auto [last, error] = std::from_chars(token.data(), token.data() + token.size(), value);
    require(error == std::errc{} && last == token.data() + token.size(), "Invalid live Core number");
    return value;
}

SimTime read_target(std::istringstream& request) {
    const auto target = number(request);
    require(target <= ((UINT64_C(1) << 53) - 1), "Live time exceeds the observation clock");
    return {static_cast<std::int64_t>(target)};
}

std::filesystem::path staged_save(std::istringstream& request, bool snapshot = false) {
    const auto id = word(request);
    require(id.size() == 32 && id.find_first_not_of("0123456789abcdef") == std::string::npos,
            "Invalid live save staging ID");
    return id + (snapshot?".awstate":".sqlite");
}

std::vector<std::uint8_t> read_snapshot(const std::filesystem::path& path, std::size_t limit) {
    const auto length=std::filesystem::file_size(path);
    require(length>0 && length<=limit,"Invalid continuation snapshot size");
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(length));
    std::ifstream input(path,std::ios::binary);
    require(static_cast<bool>(input.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()))) &&
            input.peek()==std::char_traits<char>::eof(),"Could not read the continuation snapshot");
    return bytes;
}

void message(std::string_view status, std::string_view data = {}) {
    std::cout << status << ' ' << data.size() << '\n' << data << std::flush;
}

void payload(std::span<const std::uint8_t> bytes) {
    message("OK", {reinterpret_cast<const char*>(bytes.data()), bytes.size()});
}

void send_events(std::span<const WorldEvent> events) {
    std::vector<std::uint8_t> bytes;
    for (const auto& fact : events) {
        const auto data = encode_event(fact);
        const auto size = data.size();
        bytes.insert(bytes.end(), {static_cast<std::uint8_t>(size), static_cast<std::uint8_t>(size >> 8),
                                   static_cast<std::uint8_t>(size >> 16), static_cast<std::uint8_t>(size >> 24)});
        bytes.insert(bytes.end(), data.begin(), data.end());
    }
    if (bytes.empty()) message("OK");
    else payload(bytes);
}

void recent(const WorldRuntime& world) {
    constexpr std::uint64_t cap = 120;
    const auto count = world.summary().committed_events;
    send_events(world.events_after({count > cap ? count - cap : 0}, cap));
}

// Sparse read-only projection of a contiguous canonical window. Keep every meal
// and life transition, and the first surface move per actor within the window.
void meal_events(const WorldRuntime& world, EventId after, std::size_t length, bool water) {
    auto page=world.events_after(after,length);
    require(page.size()==length && page.back().id.value==after.value+length,"Incomplete meal evidence window");
    const auto surface=world.surface_snapshot();
    std::set<EntityId> surface_movers;
    std::erase_if(page,[&](const WorldEvent& e) {
        switch (e.kind) {
        case FactKind::AntBorn: case FactKind::StageChanged: case FactKind::AntDied:
        case FactKind::ForagingStarted: case FactKind::FoodCollected: case FactKind::FoodDelivered:
        case FactKind::SoilExcavated: case FactKind::SoilDropped: case FactKind::NutritionTransferred:
        case FactKind::CargoIngested: case FactKind::FoundressNestMeal:
            return false;
        case FactKind::FoundressWaterIngested: case FactKind::WorkerWaterIngested:
            return !water;
        case FactKind::FoundingBoundaryUptake: case FactKind::PhysiologyUpdated:
            return !e.transferred.carbs_ug && (!water || !e.transferred.water_ug);
        case FactKind::BiologicalObservation:
            return e.observation.act!=CareAct::ApproachNestmate ||
                   (e.observation.phase!=ObservationPhase::Selected && e.observation.phase!=ObservationPhase::Completed);
        case FactKind::Moved:
            return !surface.configured || e.stage!=LifeStage::Adult || e.position.y<surface.surface.origin_m.y ||
                   !surface_movers.insert(e.actor).second;
        default: return true;
        }
    });
    send_events(page);
}

bool in_place_action(const WorldEvent& e) {
    if (e.outcome > Outcome::Partial) return false;
    switch (e.kind) {
    case FactKind::NestIngested: case FactKind::CargoIngested: case FactKind::FoundressNestMeal:
    case FactKind::FoundressWaterIngested: case FactKind::WorkerWaterIngested:
    case FactKind::NutritionTransferred: case FactKind::FoundingRation:
        return e.transferred.total_ug() > 0;
    case FactKind::BiologicalObservation:
        if (e.observation.phase != ObservationPhase::Completed) return false;
        switch (e.observation.act) {
        case CareAct::InspectBrood: case CareAct::ArrangeBrood: case CareAct::CleanBrood:
        case CareAct::PickUpBrood: case CareAct::PlaceBrood: case CareAct::EntranceContact: return true;
        default: return false;
        }
    default: return false;
    }
}

void recent_actions(const WorldRuntime& world, std::uint64_t after) {
    constexpr std::uint64_t page = 512, scan = 4096;
    constexpr std::size_t keep = 12;
    std::vector<WorldEvent> latest;
    auto tip = world.summary().committed_events;
    after = std::max({after,tip > scan ? tip - scan : 0,static_cast<std::uint64_t>(world.first_history_cursor())});
    while (tip > after && latest.size() < keep) {
        const auto count = std::min(page, tip - after);
        const auto events = world.events_after({tip - count}, count);
        for (auto e = events.rbegin(); e != events.rend() && latest.size() < keep; ++e)
            if (in_place_action(*e)) latest.push_back(*e);
        tip -= count;
    }
    std::reverse(latest.begin(), latest.end());
    send_events(latest);
}

enum class Milestone { Egg, Hatch, Worker, Exit, Delivery, Water, Recruitment, Excavation, Patrol, EntranceContact,
                       BroodMoved, BroodCleaned, FounderMeal, FounderUptake, WorkerFeedsQueen, WallDelivery,
                       Death, EggDeath, LarvaDeath, PupaDeath, WorkerDeath, QueenDeath, EnergyDeath, DehydrationDeath };

Milestone parse_milestone(std::string_view name) {
    if (name == "egg") return Milestone::Egg;
    if (name == "hatch") return Milestone::Hatch;
    if (name == "worker") return Milestone::Worker;
    if (name == "exit") return Milestone::Exit;
    if (name == "delivery") return Milestone::Delivery;
    if (name == "water") return Milestone::Water;
    if (name == "recruitment") return Milestone::Recruitment;
    if (name == "excavation") return Milestone::Excavation;
    if (name == "patrol") return Milestone::Patrol;
    if (name == "entrance-contact") return Milestone::EntranceContact;
    if (name == "brood-moved") return Milestone::BroodMoved;
    if (name == "brood-cleaned") return Milestone::BroodCleaned;
    if (name == "queen-meal") return Milestone::FounderMeal;
    if (name == "queen-uptake") return Milestone::FounderUptake;
    if (name == "queen-gift") return Milestone::WorkerFeedsQueen;
    if (name == "wall-delivery") return Milestone::WallDelivery;
    if (name == "death") return Milestone::Death;
    if (name == "egg-death") return Milestone::EggDeath;
    if (name == "larva-death") return Milestone::LarvaDeath;
    if (name == "pupa-death") return Milestone::PupaDeath;
    if (name == "worker-death") return Milestone::WorkerDeath;
    if (name == "queen-death") return Milestone::QueenDeath;
    if (name == "energy-death") return Milestone::EnergyDeath;
    if (name == "dehydration-death") return Milestone::DehydrationDeath;
    throw std::invalid_argument("Unknown live milestone");
}

std::vector<Milestone> read_milestones(std::istringstream& request) {
    std::vector<Milestone> targets;
    for (std::string name; request >> name;) {
        const auto target = parse_milestone(name);
        require(std::find(targets.begin(), targets.end(), target) == targets.end(), "Choose distinct target events.");
        targets.push_back(target);
    }
    require(!targets.empty(), "Choose at least one target event.");
    return targets;
}

bool adult_worker(const WorldRuntime& world, const WorldEvent& fact) {
    if (fact.stage != LifeStage::Adult) return false;
    const auto ant = world.query_ant({fact.world, fact.actor});
    return ant && ant->caste == Caste::Worker;
}

struct MilestoneHit {
    std::size_t index;
    WorldEvent fact;
    std::optional<LifeStage> death_stage;
};

void send_milestone(const MilestoneHit& hit, bool grouped) {
    auto bytes = encode_event(hit.fact);
    if (hit.fact.kind == FactKind::AntDied) {
        const auto stage = hit.death_stage ? static_cast<std::uint8_t>(*hit.death_stage) : std::uint8_t{0xff};
        bytes.insert(bytes.begin(), stage);
    }
    if (grouped) bytes.insert(bytes.begin(), static_cast<std::uint8_t>(hit.index));
    payload(bytes);
}

struct MilestoneSearch {
    std::vector<Milestone> targets;
    EventId cursor{};
    std::optional<SimTime> matched_at;
    std::optional<double> surface_y;
    std::set<EntityId> underground;
    bool track_deaths;
    std::map<EntityId, LifeStage> living_stages;

    explicit MilestoneSearch(std::vector<Milestone> milestones, const WorldRuntime& world)
        : targets(std::move(milestones)), cursor{world.first_history_cursor()},
          track_deaths(std::any_of(targets.begin(), targets.end(), [](Milestone target) { return target >= Milestone::Death; })) {
        if (std::find(targets.begin(), targets.end(), Milestone::Exit) != targets.end()) {
            const auto surface = world.surface_snapshot();
            if (surface.configured) surface_y = surface.surface.origin_m.y;
        }
    }

    void start_at_tip(const WorldRuntime& world) {
        cursor = {world.summary().committed_events};
        if (!surface_y && !track_deaths) return;
        for (const auto& ant : world.ant_states()) {
            if (track_deaths && ant.stage != LifeStage::Dead) living_stages.emplace(ant.id, ant.stage);
            if (surface_y && ant.stage == LifeStage::Adult && ant.caste == Caste::Worker && ant.position.y < *surface_y)
                underground.insert(ant.id);
        }
    }

    std::optional<LifeStage> remember_life(const WorldEvent& fact) {
        if (!track_deaths) return {};
        if (fact.kind == FactKind::AntDied) {
            // A death fact carries Dead. Recover the last living stage from the prior cut or committed transitions.
            const auto stage = living_stages.extract(fact.actor);
            return stage ? std::optional{stage.mapped()} : std::nullopt;
        }
        if (fact.kind == FactKind::AntSeeded || fact.kind == FactKind::AntBorn || fact.kind == FactKind::StageChanged)
            living_stages.insert_or_assign(fact.actor, fact.stage);
        return {};
    }

    bool matches(Milestone target, const WorldRuntime& world, const WorldEvent& fact, std::optional<LifeStage> death_stage) {
        switch (target) {
        case Milestone::Egg:
            return fact.kind == FactKind::AntBorn && fact.stage == LifeStage::Egg;
        case Milestone::Hatch:
            return fact.kind == FactKind::StageChanged && fact.stage == LifeStage::Larva;
        case Milestone::Worker:
            return fact.kind == FactKind::StageChanged && adult_worker(world, fact);
        case Milestone::Death:
            return fact.kind == FactKind::AntDied;
        case Milestone::EggDeath:
            return death_stage == LifeStage::Egg;
        case Milestone::LarvaDeath:
            return death_stage == LifeStage::Larva;
        case Milestone::PupaDeath:
            return death_stage == LifeStage::Pupa;
        case Milestone::WorkerDeath: case Milestone::QueenDeath: {
            if (fact.kind != FactKind::AntDied || (target == Milestone::WorkerDeath && death_stage != LifeStage::Adult))
                return false;
            const auto ant = world.query_ant({fact.world, fact.actor});
            return ant && ant->caste == (target == Milestone::WorkerDeath ? Caste::Worker : Caste::Queen);
        }
        case Milestone::EnergyDeath:
            return fact.kind == FactKind::AntDied && fact.payload == static_cast<std::uint64_t>(DeathCause::EnergyDepleted);
        case Milestone::DehydrationDeath:
            return fact.kind == FactKind::AntDied && fact.payload == static_cast<std::uint64_t>(DeathCause::Dehydrated);
        case Milestone::WallDelivery:
            if (fact.kind==FactKind::FoodDelivered && fact.payload==wall_delivery_payload && fact.transferred.total_ug()) {
                const auto ecology=world.ecological_closure();
                return ecology && ecology->founding_habitat && ecology->founding_habitat->wall_handoff;
            }
            return false;
        case Milestone::Delivery:
            if (fact.kind != FactKind::FoodDelivered || !fact.transferred.total_ug() || !adult_worker(world,fact))
                return false;
            if (const auto ecology=world.ecological_closure(); ecology && ecology->founding_habitat)
                return fact.transferred.total_ug()!=fact.transferred.water_ug;
            return true;
        case Milestone::Water:
            if (fact.kind != FactKind::FoodCollected || !fact.transferred.water_ug || !adult_worker(world,fact)) return false;
            if (const auto source=world.query_food({fact.world,fact.resource}))
                return source->initial.total_ug()==source->initial.water_ug;
            return false;
        case Milestone::Recruitment:
            return fact.kind==FactKind::RecruitmentActivated && adult_worker(world,fact);
        case Milestone::Excavation:
            return fact.kind == FactKind::SoilExcavated && adult_worker(world, fact);
        case Milestone::BroodMoved:
            return fact.kind==FactKind::BroodMoved;
        case Milestone::FounderMeal:
            return fact.kind==FactKind::FoundressNestMeal && fact.transferred.total_ug();
        case Milestone::WorkerFeedsQueen:
            if (fact.kind!=FactKind::NutritionTransferred || !fact.transferred.total_ug() || !adult_worker(world,fact))
                return false;
            if (const auto recipient=world.query_ant({fact.world,EntityId{fact.payload}}))
                return recipient->caste==Caste::Queen;
            return false;
        case Milestone::FounderUptake:
            if ((fact.kind!=FactKind::PhysiologyUpdated && fact.kind!=FactKind::FoundingBoundaryUptake) ||
                !fact.transferred.carbs_ug || fact.stage!=LifeStage::Adult) return false;
            if (const auto ant=world.query_ant({fact.world,fact.actor})) return ant->caste==Caste::Queen;
            return false;
        case Milestone::BroodCleaned:
            return fact.kind==FactKind::BiologicalObservation && fact.observation.phase==ObservationPhase::Completed &&
                fact.observation.act==CareAct::CleanBrood;
        case Milestone::Patrol: case Milestone::EntranceContact:
            return fact.kind==FactKind::BiologicalObservation && fact.observation.phase==ObservationPhase::Completed &&
                fact.observation.act==(target==Milestone::Patrol?CareAct::EntrancePatrol:CareAct::EntranceContact);
        case Milestone::Exit:
            if (!surface_y) return false;
            if (fact.kind == FactKind::AntDied) underground.erase(fact.actor);
            if (fact.kind != FactKind::Moved && fact.kind != FactKind::AntSeeded && fact.kind != FactKind::StageChanged)
                return false;
            if (!adult_worker(world, fact)) return false;
            // Track the last committed side of the boundary. Only an actual move can cross it.
            if (fact.position.y < *surface_y) {
                underground.insert(fact.actor);
                return false;
            }
            return underground.erase(fact.actor) != 0 && fact.kind == FactKind::Moved;
        }
        return false;
    }

    std::optional<MilestoneHit> scan(const WorldRuntime& world) {
        constexpr std::size_t page = 512;
        matched_at.reset();
        while (true) {
            const auto events = world.events_after(cursor, page);
            for (const auto& fact : events) {
                cursor = fact.id;
                const auto death_stage = remember_life(fact);
                std::optional<std::size_t> match;
                // The exit detector must also see a worker's emergence when it is a hit for another target.
                for (std::size_t index = 0; index < targets.size(); ++index) {
                    if (matches(targets[index], world, fact, death_stage) && !match) match = index;
                }
                if (match) {
                    matched_at = fact.time;
                    return MilestoneHit{*match, fact, death_stage};
                }
            }
            if (events.size() < page) return {};
        }
    }
};

class LiveHistory {
public:
    void attach(WorldRuntime& world, bool assay = false) {
        packed_.reset();
        assay_ = assay;
        if (!assay_) world.limit_unpublished_history(hot_limit);
    }

    void advance(WorldRuntime& world, SimTime target) {
        auto now = world.summary().now;
        require(target >= now, "simulation time cannot move backwards");
        if (assay_ || target == now) {
            world.advance_to(target);
            if (world.unpublished_history() >= (assay_ ? hot_limit : packing_threshold)) compact(world);
            return;
        }

        // Group consecutive timestamps. If a dense interval exceeds the hot
        // allowance, advance_to rolls it back and a shorter cut can be retried.
        std::int64_t span = 30 * 60 * 1000;
        while (now < target) {
            require(encoded_bytes() < memory_budget,
                    "Live history memory limit reached. Save and reopen the world to continue.");
            const auto step = std::min(span, target.milliseconds - now.milliseconds);
            const SimTime next{now.milliseconds + step};
            try {
                world.advance_to(next);
            } catch (const std::length_error& error) {
                if (std::string_view(error.what()) != "unpublished history backpressure") throw;
                if (step > 1) span = step / 2;
                else if (world.unpublished_history()) compact(world);
                else throw;
                continue;
            }
            now = next;
            if (world.unpublished_history() >= packing_threshold) compact(world);
        }
    }

    [[nodiscard]] std::size_t encoded_bytes() const noexcept { return packed_ ? packed_->encoded_bytes() : 0; }
    static constexpr std::size_t memory_budget = 192 * 1024 * 1024;

private:
    static constexpr std::size_t hot_limit = 65'536, packing_threshold = 16'384;
    void compact(WorldRuntime& world) { packed_ = r0::DiagnosticHistory::publish(world); }
    std::shared_ptr<const r0::DiagnosticHistory> packed_;
    bool assay_{};
};

void advance_until(WorldRuntime& world, SimTime target, MilestoneSearch& search, LiveHistory& history, bool grouped) {
    auto cut = world.summary();
    require(target >= cut.now, "simulation time cannot move backwards");
    require(search.cursor.value == cut.committed_events, "Live milestone search does not match the current history");
    // Finish each timestamp atomically before allowing the viewer to pause.
    // Bound the number of timestamps in one reply so the user can also cancel.
    for (int slice = 0; slice < 256; ++slice) {
        const auto next = world.next_scheduled_time();
        if (cut.living_ants == 0 || !next) { message("OK", "exhausted"); return; }
        if (*next > target) { history.advance(world,target); break; }
        history.advance(world,*next);
        cut = world.summary();
        if (cut.committed_events != search.cursor.value) {
            if (const auto hit = search.scan(world)) { send_milestone(*hit, grouped); return; }
        }
    }
    message("OK");
}
} // namespace

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdout), _O_BINARY) == -1) return 1;
#endif
    auto limits = assay_limits(live_case(1, 1));
    limits.committed_events = std::numeric_limits<std::size_t>::max();
    std::optional<WorldRuntime> world;
    std::optional<MilestoneSearch> search;
    LiveHistory history;
    std::string line;
    while (std::getline(std::cin, line)) {
        try {
            std::istringstream request(line);
            const auto command = word(request);
            if (command == "HELLO") {
                end(request);
                message("OK", "antworld.m0.live.v48");
            } else if (command=="NEW_HABITAT" || command=="NEW_OBSERVATORY" || command=="NEW_SINGLE_NEST" ||
                       command=="NEW_ANATOMICAL_NEST" || command=="NEW_ORAL_NEST" || command=="NEW_OFFER_NEST" ||
                       command=="NEW_WALL_HANDOFF_NEST" || command=="NEW_MOUTH_HANDOFF_NEST" ||
                       command=="NEW_FAMILIAR_RETURN_NEST" || command=="NEW_VARIABLE_NEST" || command=="NEW_PROVISIONED_NEST") {
                const auto id=number(request), seed=number(request), temperature=number(request), humidity=number(request);
                const auto access=word(request);
                request >> std::ws;
                const auto half_life=request.eof() ? 60 : number(request);
                bool alternate_berth=false, external_supply=true;
                const bool provisioned=command=="NEW_PROVISIONED_NEST";
                const bool variable=command=="NEW_VARIABLE_NEST" || provisioned;
                const bool familiar=command=="NEW_FAMILIAR_RETURN_NEST";
                const bool mouth_handoff=command=="NEW_MOUTH_HANDOFF_NEST" || familiar || variable;
                const bool wall=command=="NEW_WALL_HANDOFF_NEST" || mouth_handoff;
                const bool offers=command=="NEW_OFFER_NEST" || wall;
                const bool oral=command=="NEW_ORAL_NEST" || offers;
                const bool anatomical=command=="NEW_ANATOMICAL_NEST" || oral;
                const bool sealed=command=="NEW_SINGLE_NEST" || anatomical;
                std::optional<TrailExposure> exposure;
                auto nutrition=FoundingNutrition::Original;
                bool extended_supply=false, nearby_feeder=false;
                bool wet_wick=false;
                bool nursery_wick=false;
                if (command=="NEW_OBSERVATORY" || sealed) {
                    const auto policy=word(request), supply=word(request);
                    require(policy=="reference" || policy=="reachable","invalid depot policy");
                    require(supply=="finite" || supply=="absent" || (variable && supply=="extended") ||
                            (provisioned && supply=="nearby"),"invalid supply setting");
                    alternate_berth=policy=="reachable";
                    external_supply=supply!="absent";
                    nearby_feeder=supply=="nearby";
                    extended_supply=supply=="extended" || nearby_feeder;
                }
                if (variable) {
                    const auto ventilation=word(request), substrate=word(request);
                    require((ventilation=="sheltered" || ventilation=="ventilated") &&
                            (substrate=="mineral" || substrate=="porous"),"invalid surface trail exposure");
                    exposure=TrailExposure{ventilation=="ventilated",substrate=="porous"};
                }
                if (provisioned) {
                    const auto treatment=word(request);
                    require(treatment=="feeding" || treatment=="budget" || treatment=="sustained" ||
                            treatment=="protected" || treatment=="local-dig" || treatment=="callow" || treatment=="meal-search" ||
                            treatment=="social-crop" || treatment=="crop-exchange" || treatment=="chamber-return" || treatment=="mouth-range" || treatment=="checked-offer" ||
                            treatment=="local-departure" || treatment=="meal-rendezvous" || treatment=="first-meal" || treatment=="responsive-meal" || treatment=="work-face" || treatment=="local-crop-return" || treatment=="worked-exit" || treatment=="sustained-contact" || treatment=="yielding-return" || treatment=="chamber-handoff" || treatment=="body-orientation" || treatment=="local-solicitation" || treatment=="source-refill" || treatment=="founder-appetite" || treatment=="trip-load" || treatment=="founder-route" || treatment=="exit-attachment" || treatment=="confirmed-meal-route" || treatment=="stationary-body" || treatment=="feeding-stance" || treatment=="founder-wick" || treatment=="repeat-collection" || treatment=="work-face-detour" || treatment=="familiar-site-detour" || treatment=="nursery-arrival",
                            "invalid founding nutrition treatment");
                    nutrition=treatment=="feeding" ? FoundingNutrition::LocalFeeding :
                        treatment=="budget" ? FoundingNutrition::BroodBudget :
                        treatment=="protected" ? FoundingNutrition::ProtectedFounding :
                        treatment=="nursery-arrival" ? FoundingNutrition::NurseryArrival :
                        treatment=="familiar-site-detour" ? FoundingNutrition::FamiliarSiteDetour :
                        treatment=="work-face-detour" ? FoundingNutrition::WorkFaceDetour :
                        treatment=="repeat-collection" ? FoundingNutrition::RepeatCollection :
                        treatment=="founder-wick" ? FoundingNutrition::FounderWickRoute :
                        treatment=="feeding-stance" ? FoundingNutrition::FeedingStance :
                        treatment=="stationary-body" ? FoundingNutrition::StationaryBodyClearance :
                        treatment=="confirmed-meal-route" ? FoundingNutrition::ConfirmedMealRoute :
                        treatment=="exit-attachment" ? FoundingNutrition::ExitAttachment :
                        treatment=="founder-route" ? FoundingNutrition::FounderRoute :
                        treatment=="trip-load" ? FoundingNutrition::TripLoad :
                        treatment=="founder-appetite" ? FoundingNutrition::FounderAppetite :
                        treatment=="source-refill" ? FoundingNutrition::SourceRefill :
                        treatment=="local-solicitation" ? FoundingNutrition::LocalSolicitation :
                        treatment=="body-orientation" ? FoundingNutrition::BodyOrientation :
                        treatment=="chamber-handoff" ? FoundingNutrition::ChamberHandoff :
                        treatment=="yielding-return" ? FoundingNutrition::YieldingReturn :
                        treatment=="sustained-contact" ? FoundingNutrition::SustainedContact :
                        treatment=="worked-exit" ? FoundingNutrition::WorkedExit :
                        treatment=="local-crop-return" ? FoundingNutrition::LocalCropReturn :
                        treatment=="work-face" ? FoundingNutrition::WorkFaceSearch :
                        treatment=="responsive-meal" ? FoundingNutrition::ResponsiveMeal :
                        treatment=="first-meal" ? FoundingNutrition::FirstMeal :
                        treatment=="meal-rendezvous" ? FoundingNutrition::MealRendezvous :
                        treatment=="local-departure" ? FoundingNutrition::LocalDeparture :
                        treatment=="checked-offer" ? FoundingNutrition::CheckedLarvalOffer :
                        treatment=="mouth-range" ? FoundingNutrition::MouthRange :
                        treatment=="chamber-return" ? FoundingNutrition::ChamberReturn :
                        treatment=="crop-exchange" ? FoundingNutrition::CropExchange :
                        treatment=="social-crop" ? FoundingNutrition::SocialCrop :
                        treatment=="meal-search" ? FoundingNutrition::MealSearch :
                        treatment=="callow" ? FoundingNutrition::CallowHydration :
                        treatment=="local-dig" ? FoundingNutrition::LocalExcavation : FoundingNutrition::SustainedSupply;
                    request >> std::ws;
                    if (!request.eof()) {
                        const auto wick=word(request);
                        nursery_wick=wick=="nursery-wick";
                        require(wick=="small-wick" || wick=="wet-wick" ||
                                (nursery_wick && nutrition==FoundingNutrition::ProtectedFounding),
                                "invalid founding water fixture");
                        wet_wick=wick!="small-wick";
                    }
                }
                end(request);
                require(id && (access=="open" || access=="blocked" || access=="plugged"),"invalid founding habitat");
                require(!sealed || access=="plugged","Single-nest founding begins inside a sealed chamber");
                require(half_life==60 || half_life==1955,"unsupported founding trail half-life");
                auto c=live_case(id,seed);
                if (access!="open") c.arm=access;
                if (extended_supply) c.release_days=730;
                require(!nearby_feeder || nutrition>=FoundingNutrition::ProtectedFounding,"nearby feeder requires protected founding");
                c.nearby_surface_feeder=nearby_feeder;
                c.nursery_wick=nursery_wick;
                // 1.5 mL of water behind cotton in the protected founding
                // protocol (Turi et al., doi:10.1111/imb.12809). The spatial
                // wick is an ENGINEERING_FIXTURE. No automatic hydration.
                if (wet_wick) c.habitat_wick_ug=1'500'000;
                c.habitat_trail_half_life_s=static_cast<double>(half_life);
                auto scene=founding_habitat::setup(c,limits,temperature,humidity,external_supply,alternate_berth,sealed,
                    anatomical,oral,offers,wall,mouth_handoff,familiar,exposure,nutrition);
                auto frame=scene.world.checkpoint_frame();
                world.emplace(std::move(scene.world));
                search.reset();
                history.attach(*world);
                payload(frame);
            } else if (command=="NEW_NURSERY") {
                const auto id=number(request), seed=number(request), treatment=number(request);
                end(request);
                require(id && treatment<=static_cast<unsigned>(traffic_observer::Nursery::DryEcology),"invalid nursery options");
                auto scene=traffic_observer::nursery(id,seed,static_cast<traffic_observer::Nursery>(treatment),limits);
                auto frame=scene.checkpoint_frame();
                world.emplace(std::move(scene));
                search.reset();
                history.attach(*world);
                payload(frame);
            } else if (command=="NEW_R1_DIG") {
                const auto id=number(request), seed=number(request), group=number(request), mode=number(request);
                const auto shield=number(request);
                end(request);
                require(id && group>=1 && group<=300 && mode<=3 && shield<=1,"invalid R0-r1 digging fixture");
                auto case_limits=limits;
                case_limits.committed_events=20'000'000;
                auto scene=r0r1::digging(id,seed,static_cast<unsigned>(group),static_cast<NestScoring>(mode),case_limits,shield!=0);
                auto frame=scene.world.checkpoint_frame();
                world.emplace(std::move(scene.world));
                search.reset();
                history.attach(*world,true);
                payload(frame);
            } else if (command == "NEW" || command == "NEW_NEST" || command=="NEW_MOTOR" || command == "NEW_R0_ASSAY") {
                const auto id = number(request), seed = number(request);
                auto c = live_case(id,seed);
                if (command == "NEW_R0_ASSAY") {
                    const auto physics=number(request);
                    const auto supply=word(request), layout=word(request);
                    require(physics==29 || physics==32 || physics==33,"invalid R0 trial physics");
                    require(layout=="shaft" || layout=="dogleg","invalid R0 trial geometry");
                    require(supply=="continued" || supply=="limited" || supply=="water-restricted" ||
                            supply=="seasonal" || supply=="blocked","invalid R0 trial supply");
                    c.ecological->local_nest_activity=physics>=32;
                    if (physics==33) c.ecological->nest_dynamics=NestDynamics{true};
                    c.dogleg=layout=="dogleg";
                    c.release_days=supply=="limited" || supply=="blocked" ? 120U : 730U;
                    if (supply=="water-restricted") c.food.water_ug/=4;
                    if (supply=="seasonal") c.seasonal_supply=true;
                    if (supply=="blocked") c.arm="blocked";
                    request >> std::ws;
                    if (!request.eof()) c.ecological->worker_activity_timing=WorkerActivityTiming{read_target(request),read_target(request)};
                } else {
                    c.ecological->local_nest_activity=command!="NEW";
                    if (command=="NEW_MOTOR") c.ecological->nest_dynamics=NestDynamics{true,NestScoring::SpatialDemand};
                    request >> std::ws;
                    if (!request.eof()) c.ecological->worker_activity_timing=WorkerActivityTiming{read_target(request),read_target(request)};
                }
                end(request);
                require(id != 0, "A live colony needs a world ID");
                auto case_limits=limits;
                if (command == "NEW_R0_ASSAY") case_limits.committed_events=20'000'000;
                auto scene = setup(c, case_limits);
                const auto frame = scene.world.checkpoint_frame();
                world.emplace(std::move(scene.world));
                search.reset();
                history.attach(*world,command=="NEW_R0_ASSAY");
                payload(frame);
            } else if (command == "LOAD" || command == "LOAD_SNAPSHOT") {
                const bool snapshot=command=="LOAD_SNAPSHOT";
                const auto path = staged_save(request,snapshot);
                const auto id = WorldId::parse(word(request));
                end(request);
                require(std::filesystem::is_regular_file(path), "Live load snapshot is missing");
                auto candidate=[&] {
                    if (snapshot) {
                        WorldRuntime state(id,1,{},limits);
                        state.restore_snapshot(read_snapshot(path,limits.checkpoint_bytes));
                        require(state.summary().world==id,"Continuation snapshot belongs to another world");
                        return state;
                    }
                    storage::Store store(path,limits);
                    require(store.format()==storage::StoreFormat::Segmented,"Live load needs a segmented save");
                    return std::move(store.load(id).world);
                }();
                const auto model = candidate.ecological_closure();
                require(model && model->brood_space, "Live load needs a MicroWorld save");
                const auto frame = candidate.checkpoint_frame();
                world.emplace(std::move(candidate));
                search.reset();
                history.attach(*world);
                payload(frame);
            } else {
                require(world.has_value(), "Create or load a colony first");
                if (command == "ADVANCE" || command=="ADVANCE_STEP") {
                    const auto target = read_target(request);
                    end(request);
                    history.advance(*world,target);
                    search.reset();
                    if (command=="ADVANCE") payload(world->checkpoint_frame());
                    else message("OK");
                } else if (command == "FIND_MILESTONE" || command == "FIND_NEXT_MILESTONE" || command == "FIND_NEXT_MILESTONES") {
                    const bool grouped = command == "FIND_NEXT_MILESTONES";
                    const bool next = command != "FIND_MILESTONE";
                    const EventId group_after{grouped ? number(request) : 0};
                    auto targets = grouped ? read_milestones(request) : std::vector{parse_milestone(word(request))};
                    const EventId after = next && !grouped ? EventId{number(request)} : group_after;
                    end(request);
                    require(next || !world->first_history_cursor(),"Earlier milestones precede the saved history window");
                    if (after.value) {
                        // Preserve the detector state at a hit within an atomic timestamp.
                        require(search && search->targets == targets && search->cursor == after &&
                                search->matched_at == world->summary().now, "Cannot continue this milestone search");
                    } else {
                        search.emplace(std::move(targets), *world);
                        if (next) search->start_at_tip(*world);
                    }
                    if (const auto hit = search->scan(*world)) send_milestone(*hit, grouped);
                    else message("OK");
                } else if (command == "ADVANCE_UNTIL" || command == "ADVANCE_UNTIL_ANY") {
                    const auto target = read_target(request);
                    const bool grouped = command == "ADVANCE_UNTIL_ANY";
                    const auto targets = grouped ? read_milestones(request) : std::vector{parse_milestone(word(request))};
                    end(request);
                    require(search && search->targets == targets, "Choose a live milestone before fast-forwarding");
                    advance_until(*world, target, *search, history, grouped);
                } else if (command == "FRAME") {
                    end(request);
                    payload(world->checkpoint_frame());
                } else if (command=="INITIAL") {
                    end(request);
                    require(world->summary().now==SimTime{},"Initial frame is available only at time zero");
                    payload(world->checkpoint());
                } else if (command=="FOUNDING_BALANCE") {
                    const auto cut=world->summary();
                    const AntRef ref{cut.world,EntityId{number(request)}};
                    end(request);
                    require(world->query_ant(ref).has_value(),"Unknown ant in the founding colony");
                    const auto reserve=world->query_founding(ref);
                    const auto p=world->query_physiology(ref);
                    if (!reserve || !p) { message("OK"); continue; }
                    std::ostringstream data;
                    data << cut.now.milliseconds << ' ' << p->body_energy_nj << ' ' << p->hydration_ug
                         << ' ' << reserve->lipid_ug << ' ' << reserve->mobile_protein_ug;
                    for (const auto amount:p->crop.components()) data << ' ' << amount;
                    message("OK",data.str());
                } else if (command=="MEAL_ACCESS" || command=="MEAL_ACCESS_WIDE") {
                    end(request);
                    std::ostringstream rows;
                    const auto id=world->summary().world;
                    for (const auto& ant:world->ant_states()) {
                        const auto d=world->query_meal_access({id,ant.id},command=="MEAL_ACCESS_WIDE");
                        if (!d) continue;
                        rows << ant.id.value << ' ' << d->depot_visible << ' ' << d->at_berth << ' ' << d->route
                             << ' ' << d->care_busy << ' ' << d->active << ' ' << d->needs_carbs << ' ' << d->needs_water
                             << ' ' << d->depot_step << ' ' << d->wick << ' ' << d->at_wick << ' ' << d->clear_steps
                             << ' ' << d->sensed_cap_stances << ' ' << d->direct_cap_stances << ' ' << d->payable_sugar_ug << '\n';
                    }
                    message("OK",rows.str());
                } else if (command=="ORAL_ACCESS" || command=="ORAL_ALIGNMENT_PROBE") {
                    end(request);
                    std::ostringstream rows;
                    const auto id=world->summary().world;
                    for (const auto& ant:world->ant_states()) {
                        const auto d=world->query_oral_access({id,ant.id},command=="ORAL_ALIGNMENT_PROBE");
                        if (d) rows << ant.id.value << ' ' << d->visible << ' ' << d->at_mouth << ' '
                                    << d->queen_can_approach << ' ' << d->worker_can_approach << ' '
                                    << d->offered_carbs_ug << ' ' << d->requested_carbs_ug << '\n';
                    }
                    message("OK",rows.str());
                } else if (command=="BODY_STATES") {
                    end(request);
                    std::ostringstream data;
                    data.precision(17);
                    const auto point=[&](PositionM v){ data << ' ' << v.x << ' ' << v.y << ' ' << v.z; };
                    const auto id=world->summary().world;
                    for (const auto& ant:world->ant_states()) {
                        const AntRef ref{id,ant.id};
                        const auto pose=world->query_body(ref);
                        if (!pose) continue;
                        const auto care=world->query_care(ref);
                        data << ant.id.value << ' ' << pose->segment_count
                             << ' ' << (care && care->carrying_brood?care->retrieval.target.value:0)
                             << ' ' << (care && care->active?static_cast<unsigned>(care->act):0)
                             << ' ' << (care && care->active?care->target.value:0)
                             << ' ' << (care && care->active?care->began_at.milliseconds:0);
                        point(pose->forward); point(pose->up);
                        point(pose->mouth_m); point(pose->abdomen_tip_m);
                        for (unsigned i=0;i<pose->segment_count;++i) {
                            const auto& segment=pose->segments[i];
                            data << ' ' << segment.forward_offset_m;
                            point(segment.half_axes_m);
                        }
                        data << '\n';
                    }
                    message("OK",data.str());
                } else if (command=="WORKER_MOTION") {
                    end(request);
                    std::ostringstream data;
                    data.precision(17);
                    const auto id=world->summary().world;
                    for (const auto& ant:world->ant_states()) {
                        const AntRef who{id,ant.id};
                        if (const auto move=world->query_worker_motion(who))
                            data << ant.id.value << ' ' << move->begins.milliseconds << ' ' << move->translates.milliseconds << ' '
                                 << move->ends.milliseconds << ' ' << unsigned(move->facing) << ' ' << unsigned(move->target_facing)
                                 << ' ' << move->from.x << ' ' << move->from.y << ' ' << move->from.z
                                 << ' ' << move->to.x << ' ' << move->to.y << ' ' << move->to.z << '\n';
                    }
                    message("OK",data.str());
                } else if (command=="COMPACT_HISTORY") {
                    end(request);
                    // The caller has already consumed the older facts. Keep
                    // simulation authority and a contiguous continuation tail.
                    world->restore_snapshot(world->resume_snapshot());
                    history.attach(*world);
                    search.reset();
                    message("OK");
                } else if (command=="MEMORY") {
                    end(request);
                    const auto [current,peak]=performance::memory();
                    message("OK",std::to_string(current)+' '+std::to_string(peak)+' '+std::to_string(world->resident_history_bytes()));
                } else if (command=="HISTORY_STORAGE") {
                    end(request);
                    std::ostringstream data;
                    data << world->summary().committed_events << ' ' << world->unpublished_history() << ' '
                         << history.encoded_bytes() << ' ' << LiveHistory::memory_budget;
                    message("OK",data.str());
                } else if (command=="RESOURCE_RESERVES") {
                    end(request);
                    const auto mass=world->resource_reserves();
                    std::ostringstream data;
                    data << mass.carbs_ug << ' ' << mass.protein_ug << ' ' << mass.water_ug << ' ' << mass.other_ug;
                    message("OK",data.str());
                } else if (command=="SURFACE_TRAILS") {
                    end(request);
                    std::ostringstream data;
                    data.precision(17);
                    for (const auto& sample:world->trails())
                        data << sample.cell.x << ' ' << sample.cell.z << ' ' << sample.units << '\n';
                    message("OK",data.str());
                } else if (command=="HABITAT_PARAMETERS") {
                    end(request);
                    const auto environment=world->care_environment();
                    const auto profile=world->founding_profile();
                    const auto ecology=world->ecological_closure();
                    require(ecology && ecology->founding_habitat && environment && profile,"No founding habitat");
                    std::ostringstream data;
                    data.precision(17);
                    data << environment->temperature_c << ' ' << environment->relative_humidity << ' '
                         << profile->brood[0].duration.milliseconds << ' ' << profile->brood[1].duration.milliseconds << ' '
                         << profile->brood[2].duration.milliseconds << ' ' << profile->brood[1].water_ug_per_day << ' '
                         << profile->water_ug_per_day << ' ' << profile->worker.water_loss_ug_per_period *
                            static_cast<std::uint64_t>(day_ms/profile->worker.water_loss_period.milliseconds);
                    message("OK",data.str());
                } else if (command == "RECENT") {
                    end(request);
                    recent(*world);
                } else if (command == "RECENT_ACTIONS") {
                    const auto cursor = number(request);
                    end(request);
                    recent_actions(*world, cursor);
                } else if (command == "MEAL_EVENTS") {
                    const EventId after{number(request)};
                    const auto length=number(request);
                    request >> std::ws;
                    const bool water=!request.eof();
                    if (water) require(word(request)=="include-water","Invalid meal projection");
                    end(request);
                    require(length>0 && length<=8192,"Invalid meal evidence window");
                    meal_events(*world,after,static_cast<std::size_t>(length),water);
                } else if (command == "FACTS_AFTER") {
                    const auto cursor = EventId{number(request)};
                    request >> std::ws;
                    const auto limit = request.eof() ? 512 : number(request);
                    end(request);
                    require(limit>=1 && limit<=512,"invalid observation page size");
                    send_events(world->events_after(cursor, static_cast<std::size_t>(limit)));
                } else if (command == "CHECK_LEDGERS") {
                    end(request);
                    check_ledgers(*world);
                    message("OK");
                } else if (command == "R0_BALANCES") {
                    const AntRef queen{world->summary().world,{number(request)}};
                    end(request);
                    const auto p=world->query_physiology(queen);
                    const auto reserves=world->query_founding(queen);
                    require(p && reserves,"No founding physiology for this actor");
                    const auto stock=world->resource_reserves();
                    std::ostringstream data;
                    data << p->body_energy_nj << ' ' << p->hydration_ug << ' ' << p->crop.carbs_ug << ' '
                         << p->crop.protein_ug << ' ' << p->crop.water_ug << ' ' << reserves->lipid_ug << ' '
                         << reserves->mobile_protein_ug << ' ' << stock.carbs_ug << ' ' << stock.protein_ug << ' '
                         << stock.water_ug << ' ' << world->resident_history_bytes() << ' '
                         << history.encoded_bytes();
                    message("OK",data.str());
                } else if (command == "SAVE_SNAPSHOT") {
                    const auto path=staged_save(request,true);
                    end(request);
                    require(!std::filesystem::exists(path),"Live save staging path already exists");
                    const auto bytes=world->resume_snapshot();
                    std::ofstream output(path,std::ios::binary);
                    output.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
                    output.close();
                    require(static_cast<bool>(output),"Could not write the continuation snapshot");
                    message("OK");
                } else if (command == "SAVE") {
                    const auto path = staged_save(request);
                    end(request);
                    require(!std::filesystem::exists(path), "Live save staging path already exists");
                    require(!world->first_history_cursor(),"Full history is unavailable for this colony");
                    {
                        storage::Store store(path, limits, storage::StoreFormat::Segmented);
                        store.save(*world);
                        store.checkpoint_wal();
                    }
                    message("OK");
                } else {
                    throw std::invalid_argument("Unknown live Core command");
                }
            }
        } catch (const std::exception& error) {
            message("ERR", error.what());
        }
        if (!std::cout) return 1;
    }
    return 0;
}
