"""Audit the frozen S6.3.4 evidence and derive performance and ecology tables."""

import argparse
import csv
import io
import json
import math
from pathlib import Path

from run_s6_3_4 import PERFORMANCE, ROOT, cpu_window, file_hash, schedule, write_json
from verify_s6_3_4_archive import audit, require


DAY_MS = 86400000
MIB = 1024**2
PERCENTILES = (50, 95, 99)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def json_bytes(data):
    return (json.dumps(data, indent=2) + "\n").encode("utf-8")


def quantile(values, percentile):
    values = sorted(values)
    rank = (len(values) - 1) * percentile / 100
    left = math.floor(rank)
    right = math.ceil(rank)
    return values[left] + (values[right] - values[left]) * (rank - left)


def collect(data, mode, scratch):
    directory = data / ("primary" if mode == "performance" else "ecology")
    host = load_json(directory / "host.json")
    plan = read_csv(directory / "schedule.csv")
    frozen = tuple(schedule(mode))
    require(host["mode"] == mode and host["cpp_matches_commit"] and len(plan) == len(frozen), "batch mismatch")
    if mode == "performance":
        windows = host["pre_run_windows"]
        require(host["admission"] == "ADMITTED" and len(windows) == 2 and
                all(row["busy_percent"] <= 25 and row["seconds"] >= 5 and row["busy_percent"] ==
                    cpu_window(row["start_ticks_100ns"], row["end_ticks_100ns"])["busy_percent"]
                    for row in windows), "failed admission")
    results = []
    for index, (role, repetition, case, seed) in enumerate(frozen):
        require(plan[index] == dict(index=str(index), role=role, repetition=str(repetition), case=case, seed=str(seed)),
                "frozen schedule was changed")
        run_id = f"{index:02d}-{case}-{seed}"
        path = directory / run_id
        receipt = load_json(path / "attempt.json")
        require((receipt["id"], receipt["index"], receipt["role"], receipt["repetition"], receipt["case"],
                 receipt["seed"], receipt["exit_code"]) == (run_id, index, role, repetition, case, seed, 0),
                f"failed or misidentified sample: {run_id}")
        require(set(receipt["files"]) == {"sample.csv", "cuts.csv", "console.log"} and all(
            file_hash(path / name) == digest for name, digest in receipt["files"].items()), f"raw hash: {run_id}")
        sample, = read_csv(path / "sample.csv")
        cuts = read_csv(path / "cuts.csv")
        require(sample["case"] == case and int(sample["seed"]) == seed and sample["exact"] == "1", "bad sample")
        digest_path = path / "integrity.json"
        if scratch:
            worlds = audit(scratch / run_id / "world.sqlite")
            write_json(digest_path, {"worlds": worlds})
        else:
            worlds = load_json(digest_path)["worlds"]
        world, = worlds
        frames = world["frames"]
        require(all(int(sample[key]) == world[key] for key in ("facts", "blocks", "raw_bytes", "packed_bytes"))
                and len(cuts) == len(frames) == int(sample["frames"]), "state and archive totals differ")
        cursor = 0
        for cut, frame in zip(cuts, frames):
            require(all(int(cut[key]) == frame[key] for key in ("generation", "time_ms", "cursor"))
                    and int(cut["new_facts"]) == frame["cursor"] - cursor, "invalid cut or incremental work")
            cursor = frame["cursor"]
        require(cursor == world["facts"] and frames[-1]["time_ms"] == int(sample["sim_ms"]), "invalid final cut")
        results.append((sample, cuts, world, receipt))
    return host, results


def same_original_work(performance, ecology):
    r1 = ROOT / "experiments/s6_3_3_3_r1"
    density = {(r["mode"], r["motor"]): r for r in read_csv(r1 / "density_summary.csv")
               if r["layout"] == "dense" and r["workers"] == "128"}
    original = {r["case"]: r for r in read_csv(ROOT / "experiments/s6_3_3_3/density/archive_compression.csv")
                if r["codec"] == "zlib6"}
    for sample, cuts, world, _ in performance:
        case = sample["case"]
        if case.startswith("facts-"):
            facts = int(case.split("-")[1])
            require(world["facts"] == facts and int(sample["sim_ms"]) == facts + 1 and
                    [int(cut["new_facts"]) for cut in cuts] == [10000] * (facts // 10000) + [0],
                    "diagnostic workload changed")
        else:
            mode, motor = case.split("-")
            source = density[mode, motor]
            require(int(sample["sim_ms"]) == (600000 if mode == "timed" else 2 * DAY_MS) and
                    all(sample[key] == source[key] for key in ("facts", "opportunities", "trace_hash", "state_hash")),
                    "protected density identity changed")
            if motor == "legacy":
                require(world["canonical_sha256"] == original[f"{mode}_dense_128"]["raw_sha256"],
                        "legacy density canonical stream changed")
    long_reference = ROOT / "experiments/s6_3_1/ecology/corrected/positive/summary.csv"
    previous_long = {r["run"]: r for r in read_csv(long_reference)}
    outputs = []
    for sample, cuts, world, _ in ecology:
        case, seed, workers = sample["case"], sample["seed"], sample["workers"]
        if case.startswith("ecology-"):
            _, _, food, policy = case.split("-")
            reference = r1 / "ecology" / f"{seed}_{workers}_underground_{food}_{policy}"
            source, = read_csv(reference / "runs.csv")
            expected = load_json(reference / "attempt.json")
            require(source["events"] == sample["facts"] and
                    all(sample[key] == source[key] for key in ("trace_hash", "state_hash")) and
                    world["canonical_sha256"] == expected["canonical"]["raw_sha256"],
                    "R1 ecological canonical stream changed")
            require([int(cut["time_ms"]) // DAY_MS for cut in cuts] == [10, 21], "wrong R1 cuts")
            baseline = "R1 state, trace and canonical bytes"
        else:
            reference = long_reference
            source = previous_long[f"{seed}_{workers}_balanced_constant_positive_6"]
            require(all(sample[key] == source[key] for key in ("births", "emerged", "deaths"))
                    and sample["living"] == source["alive"], "long control demographic outcome changed")
            require([int(cut["time_ms"]) // DAY_MS for cut in cuts] == list(range(10, 181, 10)), "wrong long cuts")
            require([int(cut["time_ms"]) // DAY_MS for cut in cuts if float(cut["restore_ms"]) >= 0] == [90, 180],
                    "long restore boundaries differ")
            baseline = "S6.3.1 demographic outcomes"
        outputs.append(dict(sample, original_comparison=baseline,
                            reference=reference.relative_to(ROOT).as_posix(), canonical_sha256=world["canonical_sha256"]))
    return outputs


def performance_table(rows):
    outputs = []
    for case in PERFORMANCE:
        trials = [(sample, cuts) for sample, cuts, _, receipt in rows
                  if sample["case"] == case and receipt["role"] == "retained"]
        require(len(trials) == 5, "missing retained replicate")
        runs = [sample for sample, _ in trials]
        cuts = [cut for _, history in trials for cut in history]
        published = [cut for cut in cuts if int(cut["new_facts"])]
        require(len({(s["state_hash"], s["trace_hash"], s["facts"]) for s in runs}) == 1,
                "replicates performed different work")
        first = runs[0]
        fields = {key: [float(sample[key]) for sample in runs] for key in (
            "advance_ms", "restore_ms", "history_page_ms", "scoped_history_ms", "online_peak_bytes",
            "explicit_export_peak_bytes", "database_bytes")}
        for key in ("checkpoint_ms", "capture_ms", "foreground_ms", "background_ms", "ready_wait_ms", "ack_ms",
                    "wal_flush_ms", "captured_bytes", "wal_before_flush_bytes"):
            fields[key] = [float(cut[key]) for cut in cuts]
        fields["durable_facts_per_second"] = [int(cut["new_facts"]) * 1000 / float(cut["background_ms"])
                                              for cut in published]
        summary = {"case": case, "replicates": len(trials), "publications": len(cuts),
                   **{key: first[key] for key in ("facts", "opportunities", "raw_bytes", "packed_bytes", "frames")},
                   "block_compression_ratio": round(int(first["raw_bytes"]) / int(first["packed_bytes"]), 6),
                   "database_bytes_per_1000_facts": round(int(first["database_bytes"]) * 1000 / int(first["facts"]), 6),
                   "foreground_max_ms": max(fields["foreground_ms"]),
                   "online_peak_max_bytes": int(max(fields["online_peak_bytes"])),
                   "database_max_bytes": int(max(fields["database_bytes"]))}
        for key, values in fields.items():
            for level in PERCENTILES:
                summary[f"{key}_p{level}"] = round(quantile(values, level), 6)
        outputs.append(summary)
    return outputs


def qualify(summaries):
    results = []

    def budget(case, metric, value, maximum):
        results.append({"case": case, "metric": metric, "observed": value, "maximum": maximum,
                        "result": "PASS" if value <= maximum else "FAIL"})

    for row in summaries:
        case = row["case"]
        timed = case.startswith("timed-")
        if timed or case.startswith("integrated-"):
            budget(case, "foreground_ms_p95", row["foreground_ms_p95"], 25)
            budget(case, "foreground_max_ms", row["foreground_max_ms"], 100)
            budget(case, "online_peak_max_bytes", row["online_peak_max_bytes"], 512 * MIB)
        if timed:
            budget(case, "background_ms_p95", row["background_ms_p95"], 12000)
            budget(case, "restore_ms_p95", row["restore_ms_p95"], 8000)
            budget(case, "database_max_bytes", row["database_max_bytes"], 128 * MIB)
        if case == "facts-1000000":
            budget(case, "restore_ms_p95", row["restore_ms_p95"], 15000)
            budget(case, "online_peak_max_bytes", row["online_peak_max_bytes"], 768 * MIB)
        if not case.startswith("facts-") or case == "facts-1000000":
            for key in ("history_page_ms_p95", "scoped_history_ms_p95"):
                budget(case, key, row[key], 2000)
    return {"result": "PASS" if all(r["result"] == "PASS" for r in results) else "FAIL", "budgets": results}


def archive_identities(rows):
    return [(sample["case"], sample["seed"], world) for sample, _, world, _ in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--performance-scratch", type=Path)
    parser.add_argument("--ecology-scratch", type=Path)
    parser.add_argument("--compare-baseline", type=Path, help="Earlier batch for bytewise block and frame parity")
    parser.add_argument("--check", action="store_true", help="Compare regenerated reports with the recorded directory")
    args = parser.parse_args()
    if args.check and (args.performance_scratch or args.ecology_scratch):
        parser.error("--check verifies recorded evidence without writing archive receipts")
    host, performance = collect(args.evidence, "performance", args.performance_scratch)
    science_host, ecology = collect(args.evidence, "science", args.ecology_scratch)
    require(host["cpp_tree"] == science_host["cpp_tree"] and
            host["executable_sha256"] == science_host["executable_sha256"], "different builds in the evidence")
    science = same_original_work(performance, ecology)
    phases = performance_table(performance)
    gate = qualify(phases)
    parity = None
    if args.compare_baseline:
        earlier, pre = collect(args.compare_baseline, "performance", None)
        _, eco_pre = collect(args.compare_baseline, "science", None)
        require(archive_identities(pre + eco_pre) == archive_identities(performance + ecology),
                "canonical facts, blocks or frames differ between batches")
        parity = {
            "status": "PASS", "earlier_cpp_tree": earlier["cpp_tree"], "current_cpp_tree": host["cpp_tree"],
            "earlier_executable": earlier["executable_sha256"], "current_executable": host["executable_sha256"],
            "performance_attempts": len(performance), "ecology_worlds": len(ecology)}
    outputs = {"performance_summary.csv": csv_bytes(phases), "ecology_summary.csv": csv_bytes(science),
               "qualification.json": json_bytes(gate)}
    if parity:
        outputs["portability_parity.json"] = json_bytes(parity)
    if not args.check:
        args.report.mkdir(parents=True, exist_ok=True)
    for filename, data in outputs.items():
        path = args.report / filename
        if args.check:
            require(path.read_bytes() == data, f"recorded summary differs: {filename}")
        else:
            path.write_bytes(data)
    print(f"{len(performance)} performance attempts and {len(ecology)} ecology worlds verified. Gate {gate['result']}.")


if __name__ == "__main__":
    main()
