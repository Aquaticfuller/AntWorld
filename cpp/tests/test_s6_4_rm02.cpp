#include "rm02_observer.hpp"

#include "antworld/storage/store.hpp"
#include "sqlite_internal.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>

namespace {
using namespace antworld;
using namespace antworld::rm02;
using antworld::storage::detail::require;
using Path = std::filesystem::path;

template<class Operation>
void rejects(Operation operation) {
    bool threw = false;
    try { operation(); }
    catch (const std::exception&) { threw = true; }
    require(threw, "expected failure was absent");
}

struct Fixture {
    WorldRuntime world;
    ColonyRef colony;
    explicit Fixture(bool observed_care = false, RuntimeLimits limits = {}) : world({51, 4}, 17, {}, limits) {
        world.configure_long_term();
        world.configure_social();
        if (observed_care)
            world.configure_biology();
        colony = world.seed_colony();
    }
    AntRef ant(FoodMass crop = {}, Caste caste = Caste::Worker, LifeStage stage = LifeStage::Adult,
               std::uint64_t room = 1000, std::uint64_t energy = 1000000000, PositionM position = {}) {
        const auto a = world.seed_ant(colony, {position, stage, caste});
        PhysiologyConfig p;
        p.basal_nj_per_ms = 1;
        p.crop_capacity_ug = room;
        p.adult_protein_target_ug = caste == Caste::Queen ? 20 : 0;
        p.egg_duration = {500};
        world.enable_physiology(a, {crop, energy, 1000, 0}, p);
        return a;
    }
    ScheduledId gift(AntRef donor, AntRef receiver, std::int64_t time, std::uint64_t amount = 100) {
        return world.submit_nutrition({donor, {time}, NutritionAction::Trophallaxis, receiver, amount});
    }
};

struct Decoded {
    std::vector<WorldEvent> facts;
    std::vector<ScheduledId> pending;
    unsigned states{}, ledgers{}, neighbors{};
};

std::uint64_t number(std::span<const std::uint8_t> bytes) {
    std::uint64_t value{};
    for (std::size_t i = 0; i < bytes.size(); ++i)
        value |= static_cast<std::uint64_t>(bytes[i]) << (8 * i);
    return value;
}

Decoded decode(const Cut& cut) {
    Decoded result;
    auto bytes = std::span(cut.payload);
    while (!bytes.empty()) {
        require(bytes.size() >= 5, "truncated observer record");
        const auto kind = static_cast<Record>(bytes.front());
        const auto length = static_cast<std::size_t>(number(bytes.subspan(1, 4)));
        bytes = bytes.subspan(5);
        require(length <= bytes.size(), "truncated observer payload");
        const auto row = bytes.first(length);
        switch (kind) {
        case Record::Fact: result.facts.push_back(decode_event(row)); break;
        case Record::State: ++result.states; break;
        case Record::Ledger: ++result.ledgers; break;
        case Record::Pending: result.pending.push_back({number(row.first<8>())}); break;
        case Record::Neighbor: ++result.neighbors; break;
        }
        bytes = bytes.subspan(length);
    }
    require(result.facts.size() + result.states + result.ledgers + result.neighbors + result.pending.size()
                == cut.records, "observer record counts differ");
    return result;
}

const WorldEvent& fact(const Decoded& rows, ScheduledId source, FactKind kind) {
    const auto i = std::ranges::find_if(rows.facts, [&](const auto& e) { return e.source == source && e.kind == kind; });
    require(i != rows.facts.end(), "missing committed observation fact");
    return *i;
}

bool has(const Decoded& rows, const auto& condition) {
    return std::ranges::any_of(rows.facts, condition);
}

Plan scope(std::initializer_list<AntRef> actors) {
    Plan p{"test-run", {}, {}, true, true};
    for (const auto actor : actors)
        p.focal.push_back(actor.id);
    return p;
}

void transfers(const Path& dir) {
    Fixture f;
    const auto a = f.ant({150, 80, 150, 0}), b = f.ant({150, 80, 150, 0}), c = f.ant({100, 100, 100, 0});
    const auto worker = f.ant(), queen = f.ant({}, Caste::Queen, LifeStage::Adult, 70);
    const auto larva = f.ant({}, Caste::Worker, LifeStage::Larva);
    const auto ws = f.gift(a, worker, 10), qs = f.gift(b, queen, 10), ls = f.gift(c, larva, 10);
    const auto before = f.world.checkpoint();
    Observer observer(dir / "trace.sqlite", f.world, scope({a, b, c, worker, queen, larva}));
    const auto initial = observer.capture();
    const auto initial_rows = decode(initial);
    require(initial_rows.pending.size() == 3 && initial_rows.states == 6 && initial_rows.ledgers == 1,
            "missing initial pending selection or ledger");
    observer.publish(initial);
    require(f.world.checkpoint() == before, "initial observation changed the world");
    f.world.advance_to({10});
    const auto gifts = observer.capture();
    const auto rows = decode(gifts);
    const auto& w = fact(rows, ws, FactKind::NutritionTransferred);
    const auto& q = fact(rows, qs, FactKind::NutritionTransferred);
    const auto& l = fact(rows, ls, FactKind::NutritionTransferred);
    require(w.payload == worker.id.value && w.outcome == Outcome::Success && w.transferred.total_ug() == 100,
            "worker gift is missing or incorrect");
    require(q.payload == queen.id.value && q.outcome == Outcome::Partial && q.transferred.total_ug() == 70,
            "queen partial gift is missing or incorrect");
    require(l.payload == larva.id.value && l.transferred.protein_ug > 0, "larval protein gift absent");
    for (const auto* e : {&w, &q, &l}) {
        const auto after = f.world.query_physiology({e->world, {e->payload}});
        require(after && after->crop == e->transferred, "recipient crop disagrees with actual gift");
    }
    observer.publish(gifts);
    f.world.advance_to({1000});
    const auto pulses = observer.capture();
    const auto p = decode(pulses);
    require(has(p, [&](const WorldEvent& e) {
        return e.kind == FactKind::PhysiologyUpdated && e.actor == larva.id && e.transferred.protein_ug > 0;
    }), "larval absorbed protein absent");
    require(has(p, [&](const WorldEvent& e) {
        return e.kind == FactKind::PhysiologyUpdated && e.actor == queen.id && e.transferred.carbs_ug > 0;
    }), "queen carbohydrate conversion absent");
    require(f.world.query_physiology(larva)->tissue_protein_ug > 0 &&
                f.world.query_physiology(queen)->oxidized_carbs_ug > 0, "body stores did not reflect uptake");
    observer.publish(pulses);
    const auto recycled = f.world.submit_nutrition({b, {1001}, NutritionAction::ReturnProtein, {}, 5});
    f.world.advance_to({1001});
    const auto reuse = observer.capture();
    require(fact(decode(reuse), recycled, FactKind::ProteinRecycled).transferred.protein_ug == 5,
            "protein redeposit was not observed");
    observer.publish(reuse);
}

void failures(const Path& dir) {
    Fixture f;
    const auto a = f.ant({200, 0, 0, 0}), b = f.ant({200, 0, 0, 0});
    const auto receiver = f.ant({}, Caste::Worker, LifeStage::Adult, 50);
    const auto far = f.ant({}, Caste::Worker, LifeStage::Adult, 1000, 1000000000, {.02, 0, 0});
    const auto empty = f.ant(), only_protein = f.ant({0, 100, 0, 0}), egg = f.ant({}, Caste::Worker, LifeStage::Egg);
    const auto first = f.gift(a, receiver, 10), second = f.gift(b, receiver, 10);
    const auto reach = f.gift(a, far, 20), supply = f.gift(empty, receiver, 20);
    const auto stage = f.gift(only_protein, egg, 20), incompatible = f.gift(only_protein, empty, 30);
    const auto before = f.world.checkpoint();
    rejects([&] { f.gift(a, receiver, 10, 0); });
    require(f.world.checkpoint() == before, "invalid zero request changed the world");
    Observer observer(dir / "trace.sqlite", f.world, scope({a, receiver, b, far, empty, only_protein, egg}));
    observer.publish(observer.capture());
    f.world.advance_to({30});
    const auto c = observer.capture();
    const auto rows = decode(c);
    unsigned wins{}, full{};
    for (const auto& e : rows.facts) {
        if (e.source != first && e.source != second)
            continue;
        wins += e.kind == FactKind::NutritionTransferred && e.transferred.total_ug() == 50;
        full += e.kind == FactKind::ActionRejected && e.outcome == Outcome::Capacity && !e.transferred.total_ug();
    }
    require(wins == 1 && full == 1 && f.world.query_physiology(receiver)->crop.total_ug() == 50,
            "competing donors failed exact capacity accounting");
    require(fact(rows, reach, FactKind::ActionRejected).outcome == Outcome::OutOfReach &&
                fact(rows, supply, FactKind::ActionRejected).outcome == Outcome::Capacity &&
                fact(rows, stage, FactKind::ActionRejected).outcome == Outcome::InvalidStage &&
                fact(rows, incompatible, FactKind::ActionRejected).outcome == Outcome::EmptyInventory,
            "negative transfer causes were not retained");
    observer.publish(c);
}

void lifecycle(const Path& dir) {
    Fixture f;
    const auto donor = f.ant({100, 100, 100, 0});
    const auto egg = f.ant({}, Caste::Worker, LifeStage::Egg);
    const auto dying = f.ant({}, Caste::Worker, LifeStage::Adult, 1000, 1000);
    const auto at_hatch = f.gift(donor, egg, 500), at_death = f.gift(donor, dying, 1000);
    Observer observer(dir / "trace.sqlite", f.world, scope({egg, donor, dying}));
    observer.publish(observer.capture());
    f.world.advance_to({1000});
    const auto c = observer.capture();
    const auto rows = decode(c);
    const auto& gift = fact(rows, at_hatch, FactKind::NutritionTransferred);
    require(has(rows, [&](const WorldEvent& e) {
        return e.kind == FactKind::StageChanged && e.actor == egg.id && e.stage == LifeStage::Larva &&
            e.time == gift.time && e.id < gift.id;
    }), "same-time hatch order or recipient identity lost");
    const auto& rejected = fact(rows, at_death, FactKind::ActionRejected);
    require(rejected.outcome == Outcome::DeadActor && !rejected.transferred.total_ug() &&
                has(rows, [&](const WorldEvent& e) {
                    return e.kind == FactKind::AntDied && e.actor == dying.id && e.time == rejected.time &&
                        e.id < rejected.id;
                }), "same-time death did not precede donation");
    require(!has(rows, [&](const WorldEvent& e) {
        return e.kind == FactKind::PhysiologyUpdated && e.actor == dying.id && e.time == rejected.time;
    }), "depleted receiver incorrectly recorded an uptake pulse");
    observer.publish(c);
}

void opportunities(const Path& dir) {
    Fixture f(true);
    const auto donor = f.ant({0, 100, 0, 0}), near = f.ant();
    f.world.set_behavior(donor, IndividualBehavior::Nurse);
    auto plan = scope({donor, near});
    plan.neighbor_actor = near.id;
    Observer observer(dir / "trace.sqlite", f.world, plan);
    const auto initial = observer.capture();
    require(decode(initial).neighbors == 1 && initial.neighbors == Coverage::Complete, "geometry snapshot missing");
    observer.publish(initial);
    f.world.advance_to({1000});
    const auto c = observer.capture();
    const auto rows = decode(c);
    const auto opportunity = [&](const WorldEvent& e) {
        return e.kind == FactKind::BiologicalObservation && e.actor == donor.id &&
            e.observation.phase == ObservationPhase::Opportunity && e.observation.target == near.id;
    };
    require(has(rows, opportunity) && has(rows, [&](const WorldEvent& e) {
        return e.kind == FactKind::BiologicalObservation && e.actor == donor.id &&
            e.observation.phase == ObservationPhase::Selected && e.observation.act == CareAct::Inactive &&
            !e.observation.target.value;
    }), "known no-selection was conflated with a sampled opportunity");
    require(!has(rows, [](const WorldEvent& e) { return e.kind == FactKind::NutritionTransferred; }),
            "an opportunity became a fictitious gift");
    observer.publish(c);
}

void recovery(const Path& dir) {
    Fixture f;
    const auto donor = f.ant({100, 50, 80, 0}), receiver = f.ant({}, Caste::Queen);
    f.gift(donor, receiver, 10);
    const auto future = f.gift(donor, receiver, 1500);
    const auto initial = f.world.checkpoint();
    const auto plan = scope({donor, receiver});
    const auto sidecar = dir / "trace.sqlite";
    const auto db_path = dir / "world.sqlite";
    {
        Observer observer(sidecar, f.world, plan);
        observer.publish(observer.capture());
        f.world.advance_to({10});
        const auto c = observer.capture();
        const auto rows = decode(c);
        require(std::ranges::find(rows.pending, future) != rows.pending.end(), "unresolved future request absent");
        observer.publish(c);
        storage::Store db(db_path, {}, storage::StoreFormat::Segmented);
        const auto token = db.save(f.world);
        require(token.cursor == observer.cursor(), "observer and authoritative cut differ");
        observer.anchor(f.world.checkpoint());
        require(observer.publish(c) == Publish::Duplicate && observer.committed_cuts() == 2, "duplicate cut was appended");
    }
    storage::Store db(db_path);
    auto restored = db.load(f.world.summary().world);
    const auto checkpoint = restored.world.checkpoint();
    require(checkpoint == f.world.checkpoint(), "authoritative recovery differs");
    Observer reopened(sidecar, restored.world, plan, checkpoint);
    require(reopened.publish(reopened.capture()) == Publish::Duplicate, "restored cut duplicated");
    restored.world.advance_to({1000});
    reopened.publish(reopened.capture());
    restored.world.advance_to({2500});
    reopened.publish(reopened.capture());
    WorldRuntime off({1, 1}, 9);
    off.restore(initial);
    off.advance_to({2500});
    require(restored.world.checkpoint() == off.checkpoint() && restored.world.pending_events() == off.pending_events() &&
                restored.world.snapshot() == off.snapshot(), "observer or advancement partition changed canonical history or state");
}

void fault_cases(const Path& dir) {
    Fixture f;
    const auto a = f.ant({200, 0, 0, 0}), b = f.ant();
    f.gift(a, b, 10);
    const auto plan = scope({a, b});
    const auto initial = f.world.checkpoint();
    const auto path = dir / "trace.sqlite";
    {
        Observer o(path, f.world, plan);
        o.publish(o.capture());
        f.world.advance_to({10});
        const auto c = o.capture();
        const auto before = f.world.checkpoint();
        rejects([&] { o.publish(c, PublicationFault::BeforeCommit); });
        require(f.world.checkpoint() == before && o.committed_cuts() == 1, "observer failure affected authority or cursor");
        o.publish(c);
        o.anchor(before);
        require(o.committed_cuts() == 2, "failed publication did not roll back its database row");
    }
    const auto checkpoint = f.world.checkpoint();
    auto wrong = plan;
    wrong.lineage = "different";
    rejects([&] { Observer other(path, f.world, wrong, checkpoint); });
    rejects([&] { Observer other(path, f.world, plan, initial); });
    rejects([&] { Observer absent(dir / "missing.sqlite", f.world, plan, checkpoint); });
    rejects([&] { Observer bad_destination(path / "invalid.sqlite", f.world, plan); });
    const auto damaged = dir / "damaged.sqlite";
    std::filesystem::copy_file(path, damaged);
    sqlite3* db{};
    const auto utf8 = damaged.u8string();
    const int rc = sqlite3_open_v2(reinterpret_cast<const char*>(utf8.c_str()), &db, SQLITE_OPEN_READWRITE, nullptr);
    if (rc != SQLITE_OK) {
        sqlite3_close(db);
        throw std::runtime_error("cannot open damaged-sidecar fixture");
    }
    const int update = sqlite3_exec(db, "UPDATE cuts SET payload=zeroblob(length(payload)) WHERE seq=2",
                                   nullptr, nullptr, nullptr);
    sqlite3_close(db);
    require(update == SQLITE_OK, "sidecar corruption injection failed");
    rejects([&] { Observer corrupt(damaged, f.world, plan, checkpoint); });
    auto loss = plan;
    loss.lineage = "explicit-gap";
    loss.start_at_current = true;
    loss.payload_limit = 1;
    Observer bounded(dir / "gap.sqlite", f.world, loss);
    const auto lost = bounded.capture();
    require(lost.from == f.world.summary().committed_events && lost.dropped > 0 && !lost.records,
            "quota loss or observation gap was hidden");
    bounded.publish(lost);
    f.world.advance_to({2000});
    WorldRuntime off({2, 3}, 7);
    off.restore(initial);
    off.advance_to({2000});
    require(f.world.checkpoint() == off.checkpoint(), "sidecar errors changed later simulation");

    Observer grouped(dir / "grouped.sqlite", f.world, plan);
    grouped.publish(grouped.capture());
    const auto durable = grouped.cursor();
    f.world.advance_to({2500});
    require(grouped.publish(grouped.capture(), PublicationFault::None, PublicationMode::Buffered) == Publish::Staged &&
            grouped.committed_cuts() == 1, "staged cut appeared durable");
    rejects([&] { grouped.anchor(f.world.checkpoint()); });
    f.world.advance_to({3000});
    rejects([&] { grouped.publish(grouped.capture(), PublicationFault::BeforeCommit, PublicationMode::Buffered); });
    require(grouped.committed_cuts() == 1 && grouped.capture().from == durable, "group fault lost the durable tail");
    grouped.publish(grouped.capture(), PublicationFault::None, PublicationMode::Buffered);
    grouped.flush();
    require(grouped.committed_cuts() == 2 && grouped.cursor() == f.world.summary().committed_events,
            "group retry did not publish the recovered interval");
    grouped.anchor(f.world.checkpoint());

    RuntimeLimits limits;
    limits.events_per_timestamp = 1;
    WorldRuntime faulted({7, 8}, 8, {}, limits);
    faulted.schedule({{10}, Phase::Environment});
    faulted.schedule({{10}, Phase::Environment});
    Observer boundary_reader(dir / "rollback.sqlite", faulted, Plan{"rollback", {}, {}});
    boundary_reader.publish(boundary_reader.capture());
    const auto before = faulted.checkpoint();
    rejects([&] { faulted.advance_to({10}); });
    require(faulted.checkpoint() == before && boundary_reader.publish(boundary_reader.capture()) == Publish::Duplicate,
            "rolled-back world output became new observer data");
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument("RM-02 test requires a mode and a new output directory");
        const std::string_view mode{argv[1]};
        const Path dir(argv[2]);
        require(std::filesystem::create_directories(dir), "test requires a fresh directory");
        if (mode == "transfers") transfers(dir);
        else if (mode == "failures") failures(dir);
        else if (mode == "lifecycle") lifecycle(dir);
        else if (mode == "opportunities") opportunities(dir);
        else if (mode == "recovery") recovery(dir);
        else if (mode == "faults") fault_cases(dir);
        else throw std::invalid_argument("unknown RM-02 test mode");
        std::cout << "PASS RM-02 " << mode << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "RM-02 test failure: " << e.what() << '\n';
        return 1;
    }
}
