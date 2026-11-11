#!/usr/bin/env python3
"""Check the portable RM-01 matrix against committed events and historical controls."""

import argparse
import json
from collections import Counter
from math import isclose
from pathlib import Path
from statistics import median

from analyze_s6_3_4 import quantile
from run_s6_4_rm01 import BASELINE, ECOLOGY, ROOT, SHORT, csv_rows, facts_csv, require
from run_s6_3_4 import cpu_window, file_hash


CLOCKS = {"legacy": 172800000, "borisovka": 1442880000, "st-petersburg": 1356480000}
HOUR = 3600000
DAY = 24 * HOUR
ORIGINAL_ENERGY = 500000000
ANT_SEEDED, STAGE_CHANGED, ANT_DIED, ANT_BORN = 2, 7, 8, 35


def short_result(directory, receipt, profile, arm, eggs):
    duration = CLOCKS[profile]
    energy, water = ORIGINAL_ENERGY, 200
    elapsed, cause = duration, 0
    if arm in {"seed", "funded"}:
        if duration > ORIGINAL_ENERGY:
            elapsed, cause = ORIGINAL_ENERGY, 1
    else:
        energy, water = duration + 4, (duration + 1) // HOUR + 1
        if arm == "energy-tie":
            energy, cause = duration, 1
        elif arm == "water-tie":
            water, cause = duration // HOUR, 2
        elif arm == "interrupted":
            elapsed, cause = duration - 1, 3

    egg = eggs[0]
    actor = egg["egg_id"]
    entry = int(egg["entry_ms"])
    require(entry == (2 * DAY if arm == "funded" else 0), "unexpected focal entry time")
    require((int(egg["mother_id"]) != 0) == (arm == "funded"), "wrong maternal identity")
    require(int(egg["initial_energy_nj"]) == energy and int(egg["initial_water_ug"]) == water,
            "original or sentinel budget changed")
    outcome = entry + elapsed
    facts = {row["event_id"]: row for row in csv_rows(directory / "facts.csv")}
    start = facts[egg["entry_event_id"]]
    end = facts[egg["outcome_event_id"]]
    require(start["actor_id"] == end["actor_id"] == actor and int(start["time_ms"]) == entry
            and int(start["kind_code"]) == (ANT_BORN if arm == "funded" else ANT_SEEDED)
            and int(end["time_ms"]) == outcome and int(end["kind_code"]) == (ANT_DIED if cause else STAGE_CHANGED)
            and int(end["stage_code"]) == (4 if cause else 1), f"unexpected focal event for {profile}/{arm}")
    hatches = [fact for fact in facts.values()
               if fact["actor_id"] == actor and fact["kind_code"] == str(STAGE_CHANGED) and fact["stage_code"] == "1"]
    require(len(hatches) == int(not cause), "unexpected number of focal hatches")

    ticks = {int(row["time_ms"]): row for row in csv_rows(directory / "observations.csv")}
    for tick in (outcome - 1, outcome, entry + duration - 1, entry + duration, entry + duration + 1):
        row = ticks[tick]
        require(row["egg_id"] == actor and int(row["stage_code"]) == (0 if tick < outcome else (4 if cause else 1)),
                "focal boundary stage or identity changed")
    terminal = ticks[outcome]
    require(int(terminal["death_cause_code"]) == cause and int(terminal["energy_nj"]) == energy - elapsed
            and int(terminal["water_ug"]) == water - elapsed // HOUR, "focal death cause or reserves changed")
    mid, cut = csv_rows(directory / "cuts.csv")
    require(int(mid["time_ms"]) < outcome == int(cut["time_ms"])
            and all(float(row["restore_ms"]) >= 0 for row in (mid, cut))
            and receipt["published_frame_count"] == 2, "missing mid-egg or terminal restore")
    count, digest = facts_csv(directory / "facts.csv", {
        "facts": int(cut["cursor"]), "canonical_sha256": receipt["published_canonical_sha256"],
    })
    require(count == receipt["fact_count"] and digest == receipt["canonical_sha256"], "short trace receipt mismatch")
    return {"profile": profile, "arm": arm, "elapsed_ms": elapsed, "death_cause_code": cause,
            "remaining_energy_nj": int(terminal["energy_nj"]), "remaining_water_ug": int(terminal["water_ug"])}


def legacy_regression(arm, summary, eggs):
    supply, workers = arm.split("-")
    depot = supply == "depot"
    archive = ROOT / "experiments/s6_3_1/ecology/corrected" / ("positive" if depot else "historical")
    name = f"1_{workers}_{'scarce' if supply == 'scarce' else 'balanced'}_constant_{'positive' if depot else 'full'}_6"
    old = next(row for row in csv_rows(archive / "summary.csv") if row["run"] == name)
    queen = csv_rows(archive / name / "queen_daily.csv")[-1]
    require((summary["living"], str(len(eggs)), summary["queen_alive"], summary["facts"],
             summary["state_hash"], summary["trace_hash"]) ==
            (old["alive"], old["births"], queen["alive"], old["events"], old["state_hash"], old["trace_hash"]),
            "legacy ecology differs from the frozen S6.3.1 archive")
    return (archive / name).relative_to(ROOT).as_posix()


def verify(evidence):
    identity = json.loads((evidence / "build.json").read_text(encoding="utf-8"))
    require(identity["baseline_commit"] == BASELINE, "unexpected baseline")
    matrix = json.loads((evidence / "matrix.json").read_text(encoding="utf-8"))
    require(tuple((row["profile"], row["arm"]) for row in matrix) == SHORT + ECOLOGY, "assay matrix changed")
    shorts, ecology = [], []
    for result in matrix:
        profile, arm = result["profile"], result["arm"]
        directory = evidence / f"{profile}-{arm}"
        receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
        require(all(receipt[key] == value for key, value in identity.items())
                and all(receipt[key] == value for key, value in result.items())
                and receipt["engineering_status"] == "ENGINEERING_PASS"
                and receipt["biological_status"] == "BIOLOGICAL_NOT_VALIDATED", "invalid run receipt")
        for file in directory.glob("*.csv"):
            expected = receipt["outputs"][file.name]
            require(file.stat().st_size == expected["bytes"] and file_hash(file) == expected["sha256"],
                    f"wrong portable payload: {file}")
        config, = csv_rows(directory / "configuration.csv")
        summary, = csv_rows(directory / "summary.csv")
        eggs = csv_rows(directory / "eggs.csv")
        require(config["profile"] == profile and config["mode"] == arm and int(config["clock_ms"]) == CLOCKS[profile]
                and int(summary["facts"]) == receipt["fact_count"] and summary["replay"] == "exact"
                and all(int(egg["clock_ms"]) == CLOCKS[profile] for egg in eggs), "wrong profile, facts or replay status")
        require(all(summary[f"{name}_in_ug"] == summary[f"{name}_accounted_ug"] for name in ("carb", "protein", "water"))
                and int(summary["energy_input_nj"]) == int(summary["body_energy_nj"]) + int(summary["dissipated_energy_nj"])
                and int(summary["soil_initial_q3"]) == sum(int(summary[f"soil_{name}_q3"])
                                                          for name in ("remaining", "carried", "deposited")),
                "conservation check failed")
        if (profile, arm) in SHORT:
            shorts.append(short_result(directory, receipt, profile, arm, eggs))
        else:
            counts = Counter(row["outcome"] for row in eggs)
            item = dict(profile=profile, arm=arm, births=len(eggs), hatches=counts["hatch"], egg_deaths=counts["death"],
                        censored=counts["censored"], facts=receipt["fact_count"], queen_alive=bool(int(summary["queen_alive"])),
                        living=int(summary["living"]))
            if profile == "legacy":
                item["historical_exact"] = legacy_regression(arm, summary, eggs)
            else:
                require(not counts["hatch"] and all(
                    int(row["outcome_or_censor_ms"]) - int(row["entry_ms"]) ==
                    min(ORIGINAL_ENERGY, int(summary["now_ms"]) - int(row["entry_ms"]))
                    and row["outcome"] == ("death" if int(row["entry_ms"]) + ORIGINAL_ENERGY <= int(summary["now_ms"]) else "censored")
                    for row in eggs), "warm ecology changed the original depletion boundary")
            ecology.append(item)
    return {"assay": "ENGINEERING_PASS", "biology": "BIOLOGICAL_NOT_VALIDATED",
            "source_commit": identity["code_commit"], "short": shorts, "ecology": ecology}


def verify_observer(evidence):
    host = json.loads((evidence / "admission.json").read_text(encoding="utf-8"))
    windows = host["windows"]
    require(host["status"] == "ADMITTED" and len(windows) == 2 and all(
        window["seconds"] >= 5 and window["busy_percent"] <= 25
        and window["busy_percent"] == cpu_window(window["start_ticks_100ns"], window["end_ticks_100ns"])["busy_percent"]
        for window in windows), "observer host admission failed")
    pairs = csv_rows(evidence / "observer_pairs.csv")
    require([row["pair"] for row in pairs] == [f"{phase}-{n:02}" for phase in ("baseline", "observer")
                                               for n in range(6)], "observer schedule changed")
    envelope = json.loads((evidence / "baseline_envelope.json").read_text(encoding="utf-8"))
    samples = {False: [], True: []}
    publications = {False: [], True: []}
    ratios = {"baseline": [], "observer": []}

    def run(name):
        root = evidence / name
        receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
        require(receipt["engineering_status"] == "ENGINEERING_PASS", "unsuccessful observer sample")
        for filename in ("summary.csv", "cuts.csv"):
            require(file_hash(root / filename) == receipt["outputs"][filename]["sha256"], f"changed {name}/{filename}")
        return receipt, csv_rows(root / "summary.csv")[0], csv_rows(root / "cuts.csv")

    for pair in pairs:
        name = pair["pair"]
        phase, repeat = name.split("-")
        n = int(repeat)
        a, b = [run(f"{name}-{leg}") for leg in ("a", "b")]
        enabled = (phase == "observer" and n % 2 == 1, phase == "observer" and n % 2 == 0)
        require((a[0]["observer"], b[0]["observer"]) == enabled and pair["role"] == ("retained" if n else "warmup")
                and (pair["first_observer_enabled"] == "True") == enabled[0], "observer order changed")
        require(a[0]["canonical_sha256"] == b[0]["canonical_sha256"] == pair["canonical_sha256"]
                and a[0]["fact_count"] == b[0]["fact_count"] == int(pair["facts"])
                and a[0]["outputs"]["final.frame"]["sha256"] == b[0]["outputs"]["final.frame"]["sha256"],
                "observer changed world facts or the final frame")
        times = [float(row["advance_ms"]) + float(row["observer_ms"]) for _, row, _ in (a, b)]
        reference, comparison = reversed(times) if enabled[0] else times
        ratio = comparison / reference
        require(isclose(ratio, float(pair["ratio"])), "reported paired ratio changed")
        if phase == "observer":
            # The producer writes the envelope first. The recorded UTC timestamps can share a millisecond.
            require(all(item[0]["started_utc"] >= envelope["recorded_before_observer_pairs_utc"] for item in (a, b)),
                    "observer ran before the baseline envelope was recorded")
            if n:
                for item in (a, b):
                    samples[item[0]["observer"]].append(item[1])
                    publications[item[0]["observer"]].extend(item[2])
        if n:
            ratios[phase].append(ratio)
    require((envelope["retained_pairs"], envelope["min_ratio"], envelope["max_ratio"]) ==
            (len(ratios["baseline"]), min(ratios["baseline"]), max(ratios["baseline"])),
            "baseline envelope differs from retained off/off pairs")

    def percentiles(rows, metric):
        values = [float(row[metric]) for row in rows if float(row[metric]) >= 0]
        return {f"p{p}": quantile(values, p) for p in (50, 95, 99)}

    return {
        "status": "ENGINEERING_PASS", "baseline_envelope": envelope, "observer_pair_ratios": ratios["observer"],
        "median_on_off": median(ratios["observer"]),
        "run_percentiles": {
            mode: {metric: percentiles(samples[enabled], metric) for metric in
                   ("advance_ms", "observer_ms", "query_ms", "scoped_query_ms", "online_peak_rss_bytes", "database_bytes")}
            for mode, enabled in (("off", False), ("on", True))
        },
        "publication_percentiles": {
            mode: {metric: percentiles(publications[enabled], metric) for metric in
                   ("checkpoint_ms", "foreground_ms", "background_ms", "restore_ms")}
            for mode, enabled in (("off", False), ("on", True))
        },
        "warm_horizon": [run(f"horizon-{profile}")[1] for profile in ("borisovka", "st-petersburg")],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--observer", type=Path, help="Admitted observer measurement evidence")
    args = parser.parse_args()
    results = verify(args.evidence)
    if args.observer is not None:
        results["observer"] = verify_observer(args.observer)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
