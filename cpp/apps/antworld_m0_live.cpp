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
#include <iostream>
#include <limits>
#include <set>
#include <span>
#include <sstream>
#include <string_view>
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

std::filesystem::path staged_save(std::istringstream& request) {
    const auto id = word(request);
    require(id.size() == 32 && id.find_first_not_of("0123456789abcdef") == std::string::npos,
            "Invalid live save staging ID");
    return id + ".sqlite";
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

bool in_place_action(const WorldEvent& e) {
    if (e.outcome > Outcome::Partial) return false;
    switch (e.kind) {
    case FactKind::NestIngested: case FactKind::CargoIngested: case FactKind::FoundressNestMeal:
    case FactKind::FoundressWaterIngested: case FactKind::NutritionTransferred: case FactKind::FoundingRation:
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
    after = std::max(after, tip > scan ? tip - scan : 0);
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

enum class Milestone { Egg, Hatch, Worker, Exit, Delivery, Water, Recruitment, Excavation, Patrol, EntranceContact };

Milestone read_milestone(std::istringstream& request) {
    const auto name = word(request);
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
    throw std::invalid_argument("Unknown live milestone");
}

bool adult_worker(const WorldRuntime& world, const WorldEvent& fact) {
    if (fact.stage != LifeStage::Adult) return false;
    const auto ant = world.query_ant({fact.world, fact.actor});
    return ant && ant->caste == Caste::Worker;
}

struct MilestoneSearch {
    Milestone target;
    EventId cursor{};
    std::optional<double> surface_y;
    std::set<EntityId> underground;

    explicit MilestoneSearch(Milestone milestone, const WorldRuntime& world) : target(milestone) {
        if (target == Milestone::Exit) {
            const auto surface = world.surface_snapshot();
            if (surface.configured) surface_y = surface.surface.origin_m.y;
        }
    }

    bool matches(const WorldRuntime& world, const WorldEvent& fact) {
        switch (target) {
        case Milestone::Egg:
            return fact.kind == FactKind::AntBorn && fact.stage == LifeStage::Egg;
        case Milestone::Hatch:
            return fact.kind == FactKind::StageChanged && fact.stage == LifeStage::Larva;
        case Milestone::Worker:
            return fact.kind == FactKind::StageChanged && adult_worker(world, fact);
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

    std::optional<WorldEvent> scan(const WorldRuntime& world) {
        constexpr std::size_t page = 512;
        while (true) {
            const auto events = world.events_after(cursor, page);
            for (const auto& fact : events) {
                cursor = fact.id;
                if (matches(world, fact)) return fact;
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

void advance_until(WorldRuntime& world, SimTime target, MilestoneSearch& search, LiveHistory& history) {
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
            if (const auto hit = search.scan(world)) { payload(encode_event(*hit)); return; }
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
                message("OK", "antworld.m0.live.v9");
            } else if (command=="NEW_HABITAT") {
                const auto id=number(request), seed=number(request), temperature=number(request), humidity=number(request);
                const auto access=word(request);
                request >> std::ws;
                const auto half_life=request.eof() ? 60 : number(request);
                end(request);
                require(id && (access=="open" || access=="blocked" || access=="plugged"),"invalid founding habitat");
                require(half_life==60 || half_life==1955,"unsupported founding trail half-life");
                auto c=live_case(id,seed);
                if (access!="open") c.arm=access;
                c.habitat_trail_half_life_s=static_cast<double>(half_life);
                auto scene=founding_habitat::setup(c,limits,temperature,humidity);
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
            } else if (command == "LOAD") {
                const auto path = staged_save(request);
                const auto id = WorldId::parse(word(request));
                end(request);
                require(std::filesystem::is_regular_file(path), "Live load snapshot is missing");
                storage::Store store(path, limits);
                require(store.format() == storage::StoreFormat::Segmented, "Live load needs a segmented save");
                auto loaded = store.load(id);
                const auto model = loaded.world.ecological_closure();
                require(model && model->brood_space, "Live load needs a MicroWorld save");
                const auto frame = loaded.world.checkpoint_frame();
                world.emplace(std::move(loaded.world));
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
                } else if (command == "FIND_MILESTONE") {
                    const auto milestone = read_milestone(request);
                    end(request);
                    search.emplace(milestone, *world);
                    if (const auto hit = search->scan(*world)) payload(encode_event(*hit));
                    else message("OK");
                } else if (command == "ADVANCE_UNTIL") {
                    const auto target = read_target(request);
                    const auto milestone = read_milestone(request);
                    end(request);
                    require(search && search->target == milestone, "Choose a live milestone before fast-forwarding");
                    advance_until(*world,target,*search,history);
                } else if (command == "FRAME") {
                    end(request);
                    payload(world->checkpoint_frame());
                } else if (command=="INITIAL") {
                    end(request);
                    require(world->summary().now==SimTime{},"Initial frame is available only at time zero");
                    payload(world->checkpoint());
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
                } else if (command == "FACTS_AFTER") {
                    const auto cursor = EventId{number(request)};
                    end(request);
                    send_events(world->events_after(cursor, 512));
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
                } else if (command == "SAVE") {
                    const auto path = staged_save(request);
                    end(request);
                    require(!std::filesystem::exists(path), "Live save staging path already exists");
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
