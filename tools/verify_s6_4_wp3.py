"""Independently verify WP-3 raw archives, selected fact bytes and state-cut joins."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing, contextmanager
import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
import tarfile
from tempfile import TemporaryDirectory

from read_s6_4_rm02_sidecar import decode_fact, numbers, open_sidecar, require
from run_s6_4_rm02 import sha256
from run_s6_4_wp3 import LIVE, PREPARED, PROTOCOL, BASE
from s6_4_wp3_cases import matrix


SELECTED = frozenset("""
    ColonySeeded AntSeeded FoodSeeded Moved FoodCollected ActionRejected StageChanged AntDied
    SurfaceConfigured ForagingStarted ForagingDecision FoodDelivered Rested TrailMaintenance
    PhysiologyEnabled PhysiologyUpdated BehaviorChanged NutritionDecision CargoIngested NestIngested
    NutritionTransferred GeometryConfigured SoilExcavated SoilDropped SoilPickedUp SoilFilled
    FoodPlaced AutonomyChanged AutonomyDecision ReproductionEnabled ReproductionAttempt AntBorn
    ResourceCycleConfigured ResourceReleased ProteinRecycled
""".split())
VIEWS = ("actors.csv", "routes.csv", "local_steps.csv", "food_cues.csv", "field.csv", "resources.csv")
DIRECTIONS = ((0, 1), (1, 0), (0, -1), (-1, 0))
U32 = struct.Struct("<I")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        require(reader.fieldnames and len(set(reader.fieldnames)) == len(reader.fieldnames), f"invalid header in {path.name}")
        result = list(reader)
        require(all(None not in row and None not in row.values() for row in result), f"ragged {path.name}")
        return result


def row(path):
    data = rows(path)
    require(len(data) == 1, f"expected one row in {path.name}")
    return data[0]


def sequence(data, key):
    entries = {}
    for item in data:
        index = key(item)
        require(index not in entries, f"duplicate identity {index}")
        entries[index] = item
    return entries


@contextmanager
def extracted(root, case):
    folder = root / "raw" / case.key
    receipt = load(folder / "receipt.json")
    require(receipt["case"] == case.key and all(receipt[k] == v for k, v in asdict(case).items()),
            f"misbound case {case.key}")
    require(receipt["exit_code"] == receipt["program_exit_code"] == 0, f"failed frozen case {case.key}")
    expected = set(PREPARED if case.family == "prepared" else LIVE)
    require(set(receipt["artifacts"]) == expected, "artifact set differs")
    path = folder / "raw.tar.gz"
    require(path.stat().st_size == receipt["archive_bytes"] and sha256(path) == receipt["archive_sha256"],
            "archive integrity failure")
    with TemporaryDirectory(prefix="wp3-verify-") as temporary, tarfile.open(path, "r:gz") as bundle:
        dest = Path(temporary)
        members = sequence(bundle, lambda item: item.name)
        require(set(members) == expected, "tar entry set differs")
        for name, entry in members.items():
            source = receipt["artifacts"][name]
            require(entry.isfile() and entry.size == source["bytes"] <= 64 * 1024 * 1024, "invalid tar member")
            data = bundle.extractfile(entry).read()
            require(hashlib.sha256(data).hexdigest() == source["sha256"], f"artifact integrity failure: {name}")
            (dest / name).write_bytes(data)
        yield dest


def canonical(path, world):
    result = []
    with path.open("rb") as source:
        previous = (0, 0)
        while prefix := source.read(U32.size):
            require(len(prefix) == U32.size, "truncated canonical length")
            length = U32.unpack(prefix)[0]
            require(0 < length <= 1024, "invalid canonical length")
            data = source.read(length)
            require(len(data) == length, "truncated canonical fact")
            fact = decode_fact(data, world)
            require(fact.event == len(result) + 1 and fact.time >= previous[0]
                    and fact.revision >= previous[1], "canonical order differs")
            previous = (fact.time, fact.revision)
            result.append((fact, data))
    return result


def check_configuration(case, config):
    require(all(config[key] == str(value) for key, value in asdict(case).items()), "configuration differs")
    require(config["classification"] == "ENGINEERING_FIXTURE", "missing fixture provenance")
    require(int(config["age_ms"]) == {"fresh": 0, "aged": 120000, "expired": 600000}[case.age], "bad assay age")


def verify_prepared(case, dest):
    config = row(dest / "configuration.csv")
    check_configuration(case, config)
    trajectory = rows(dest / "prepared.csv")
    require(len(trajectory) == 24, "prepared trajectory incomplete")
    previous = (40, 20)
    for i, item in enumerate(trajectory, 1):
        start = (int(item["from_x"]), int(item["from_z"]))
        end = (int(item["to_x"]), int(item["to_z"]))
        require(int(item["step"]) == i and start == previous and math.dist(start, end) == 1
                and int(item["marked_line"]) == (end[0] == 40), "invalid detached step")
        require(item["provenance"] == "DETACHED_ENGINEERING_FIXTURE" and
                int(item["age_ms"]) == int(config["age_ms"]) + (i - 1) * 1101, "unbound prepared input")
        require(case.signal != "absent" or (float(item["max_visible_units"]) == 0 and int(item["chosen_mode"]) != 1),
                "blank substrate yielded trail")
        previous = end
    return trajectory


def coordinates(item):
    return (int(item["cell_x"]), int(item["cell_z"]))


def check_views(tables, cut, state, ledger, config):
    current = {}
    for name in VIEWS:
        current[name] = tables[name].pop(cut["seq"], [])
        require(all(int(r["cursor"]) == cut["cursor"] and int(r["sim_ms"]) == cut["time"] for r in current[name]),
                f"unbound observation row in {name}")
    actors = sequence(current["actors.csv"], lambda r: int(r["actor"]))
    require(actors.keys() == state.keys(), "focal cut coverage differs")
    field = sequence(current["field.csv"], lambda r: (int(r["colony"]), coordinates(r)))
    for item in field.values():
        require(0 < float(item["effective_trail_units"]) <= 16 and config["signal"] != "absent", "invalid field entry")
    resources = sequence(current["resources.csv"], lambda r: int(r["resource"]))
    actual_stock = [sum(int(item[k]) for item in resources.values()) for k in
                    ("carbs_ug", "protein_ug", "water_ug", "other_ug")]
    require(tuple(actual_stock) == ledger[12:16], "resource stocks differ from ledger")
    by_actor = {}
    for name in ("local_steps.csv", "food_cues.csv", "routes.csv"):
        by_actor[name] = defaultdict(list)
        for item in current[name]:
            by_actor[name][int(item["actor"])].append(item)
        require(by_actor[name].keys() <= actors.keys(), f"unknown actor in {name}")
    for actor, item in actors.items():
        words = state[actor]
        steps, cues, routes = (by_actor[name][actor] for name in ("local_steps.csv", "food_cues.csv", "routes.csv"))
        require(item["sensing_status"] == ("NOT_APPLICABLE_DEAD" if words[5] == 4 else "CUT_SNAPSHOT"),
                "life stage and sense coverage differ")
        require(len(steps) == int(item["steps"] or 0) and len(cues) == int(item["food_cues"] or 0)
                and len({coordinates(step) for step in steps}) == len(steps), "local view count differs")
        for step in steps:
            dx, dz = DIRECTIONS[int(step["direction"])]
            require(coordinates(step) == (int(item["cell_x"]) + dx, int(item["cell_z"]) + dz), "nonlocal step")
            mapped = field.get((words[3], coordinates(step)))
            require(float(step["effective_trail_units"]) == (float(mapped["effective_trail_units"]) if mapped else 0),
                    "cut trail exposure differs from same-cut field")
        for cue in cues:
            stock = resources[int(cue["resource"])]
            require(0 <= int(cue["distance_cells"]) <= int(config["sensing_cells"]) and
                    any(int(stock[k]) for k in ("carbs_ug", "protein_ug", "water_ug", "other_ug")),
                    "nonlocal or depleted cut cue")
        route_counts = Counter()
        for cell in routes:
            name = cell["route"]
            require(name in ("trace", "learned") and int(cell["ordinal"]) == route_counts[name], "invalid route cells")
            route_counts[name] += 1
        require(route_counts["trace"] == int(item["path_cells"] or 0)
                and route_counts["learned"] == int(item["memory_cells"] or 0), "route count differs")
        require(config["memory"] == "1" or not route_counts["learned"], "memory-off cut retained a route")


def verify_live(case, dest):
    config, summary = row(dest / "configuration.csv"), row(dest / "summary.csv")
    check_configuration(case, config)
    end, release = int(summary["horizon_ms"]), int(summary["release_ms"])
    require(summary["status"] == "PASS" and summary["exact_off"] == summary["sqlite_midpoint_exact"] == "1"
            and end - release == int(config["window_ms"]), "unqualified case receipt")
    raw_cuts = sequence(rows(dest / "cuts.csv"), lambda r: int(r["cut"]))
    tables = {}
    for name in VIEWS:
        tables[name] = defaultdict(list)
        for item in rows(dest / name):
            tables[name][int(item["cut"])].append(item)
    with open_sidecar(dest / "observer.sqlite") as (manifest, cuts):
        require(manifest["foraging"] and manifest["world_id"] == config["world_id"] and
                manifest["seed"] == case.seed and not manifest["origin"], "wrong sidecar identity")
        truth = canonical(dest / "canonical.bin", manifest["world"])
        require(len(truth) == int(summary["events"]), "canonical history incomplete")
        for cut in cuts:
            source = raw_cuts.pop(cut["seq"])
            require(int(source["sim_ms"]) == cut["time"] and all(int(source[k]) == cut[k] for k in
                    ("cursor", "examined", "selected", "records", "dropped")) and not cut["dropped"], "cut mismatch")
            require(int(source["canonical_payload_bytes"]) == cut["raw_bytes"] <= 3 * 1024 * 1024 and
                    int(source["view_bytes"]) <= 2 * 1024 * 1024, "cut exceeded a budget")
            require(int(source["soil_initial_q3"]) == sum(int(source[k]) for k in
                    ("soil_remaining_q3", "soil_carried_q3", "soil_deposited_q3")), "soil imbalance")
            authoritative = truth[cut["start"]:cut["cursor"]]
            require(not authoritative or authoritative[-1][0].time <= cut["time"], "future canonical fact")
            expected = [data for fact, data in authoritative if fact.kind in SELECTED]
            facts = [bytes(data) for tag, data in cut["payload"] if tag == 1]
            require(expected == facts, "projected bytes or coverage differ from canonical history")
            state = sequence((numbers(data) for tag, data in cut["payload"] if tag == 2), lambda v: v[0])
            ledgers = [numbers(data) for tag, data in cut["payload"] if tag == 3]
            require(len(ledgers) == 1 and ledgers[0][:4] == ledgers[0][4:8] and
                    ledgers[0][28] == ledgers[0][29] + ledgers[0][30], "material or energy imbalance")
            check_views(tables, cut, state, ledgers[0], config)
            if cut["time"] == release + (end - release) // 2:
                require(manifest["anchors"].get(cut["seq"]) == sha256(dest / "midpoint.chk"), "bad midpoint anchor")
        require(not raw_cuts and not any(tables.values()) and cut["cursor"] == len(truth)
                and cut["time"] == end and cut["seq"] == int(summary["cuts"]), "trailing or incomplete cuts")
        require(manifest["anchors"].get(cut["seq"]) == sha256(dest / "final.chk"), "bad final anchor")
    require(int(summary["peak_queue_bytes"]) <= 4 * 1024 * 1024 and
            (dest / "observer.sqlite").stat().st_size == int(summary["observer_bytes"]) <= 64 * 1024 * 1024,
            "observer durability budget exceeded")
    require((dest / "midpoint.sqlite").stat().st_size == int(summary["midpoint_sqlite_bytes"]), "wrong store size")
    uri = (dest / "midpoint.sqlite").resolve().as_uri() + "?immutable=1"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        require(db.execute("PRAGMA quick_check").fetchall() == [("ok",)], "damaged authoritative SQLite save")
    return config, summary, [fact for fact, _ in truth]


def select(root, chosen):
    freeze, completed = load(root / "freeze.json"), load(root / "completed.json")
    require(freeze["baseline"] == BASE and freeze["protocol_sha256"] == sha256(PROTOCOL)
            and freeze["case_matrix_sha256"] == sha256(Path(__file__).with_name("s6_4_wp3_cases.py"))
            and freeze["runner_sha256"] == sha256(Path(__file__).with_name("run_s6_4_wp3.py")), "case freeze differs")
    cases = list(matrix())
    frozen = {item["case"]: item for item in freeze["cases"]}
    expected = {case.key for case in cases}
    require(set(frozen) <= expected and (freeze["selection"] == "smoke" or set(frozen) == expected)
            and set(frozen) == completed["exit_codes"].keys()
            and {path.name for path in (root / "raw").iterdir()} == set(frozen), "frozen matrix coverage differs")
    require(not set(chosen) - frozen.keys(), "requested case is absent")
    result = [case for case in cases if case.key in frozen and (not chosen or case.key in chosen)]
    for case in result:
        require(completed["exit_codes"][case.key] == 0 and
                frozen[case.key] == dict(case=case.key, **asdict(case)), "failed or invalid declared case")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    total = Counter()
    identities = set()
    for case in select(args.root, args.case):
        with extracted(args.root, case) as dest:
            if case.family == "prepared":
                total["detached_steps"] += len(verify_prepared(case, dest))
            else:
                config, summary, facts = verify_live(case, dest)
                require(config["world_id"] not in identities, "case WorldId collision")
                identities.add(config["world_id"])
                total["canonical_facts"] += len(facts)
                total["cuts"] += int(summary["cuts"])
            total[case.family] += 1
    print(dict(total))


if __name__ == "__main__":
    main()
