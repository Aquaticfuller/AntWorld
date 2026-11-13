"""Collect and assess admitted F1 v1 and R1 application observer overhead."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
from random import Random
import shutil
from statistics import median
import subprocess
from tempfile import TemporaryDirectory
import time

from analyze_s6_3_3_1_performance import read, telemetry
from profile_s6_4_wp6b import percentile
import run_s6_3_3_1_performance as native
from run_s6_4_rm02_performance import CONFIRMATION, append, monitor
from run_s6_4_wp6b import frozen_cases, git, input_bytes, sha
from run_s6_4_wp6b_r1 import NOMINAL, PROTOCOL


MODEL_ARGUMENTS = {"v1": (0, 0, 0), "r1": (*NOMINAL, 0)}
MODEL_VERSIONS = {"v1": 1, "r1": 2}
ADDITIONAL_SOURCES = ()


def workload():
    cases = {case["case"]: (identity, case) for identity, case in frozen_cases() if case["software_seed"] == 1 and
             ((case["group"] == "micro" and case["arm"] == "nominal") or
              (case["group"] == "early" and case["arm"] in ("depot", "empty")))}
    assert len(cases) == 10
    return cases


def schedule(session):
    rows = []
    cells = list(workload())
    for case in cells[::-1] if session == 2 else cells:
        models = tuple(MODEL_ARGUMENTS)
        for model in models[::-1] if session == 2 else models:
            for block, (a, b) in enumerate((("off-a", "off-b"), ("off", "on"))):
                order = (a, b, b, a) if (session+block) % 2 else (b, a, a, b)
                for slot, treatment in enumerate(order):
                    rows.append(dict(sample=len(rows), session=session, model=model, case=case, block=block, slot=slot,
                                     treatment=treatment, observation="observed" if treatment == "on" else "unobserved"))
    return rows


def source_hashes():
    names = (Path(__file__).name, "run_s6_4_rm02_performance.py", "analyze_s6_3_3_1_performance.py",
             "profile_s6_4_wp6b.py", "run_s6_4_wp6b_r1.py", "run_s6_4_wp6b.py", *ADDITIONAL_SOURCES)
    return native.dependencies() | {name: sha(native.ROOT / "tools" / name) for name in names}


def prepare(args):
    assert not git("status", "--porcelain", "--", "cpp", "tools")
    cache = args.build / "CMakeCache.txt"
    config = cache.read_text(encoding="utf-8")
    assert "CMAKE_BUILD_TYPE:STRING=Release" in config and "ANTWORLD_SANITIZERS:BOOL=OFF" in config
    assert "ANTWORLD_PROFILE:BOOL=ON" not in config
    args.out.mkdir(parents=True)
    sessions = {}
    for number in range(1, 4):
        folder = args.out / f"session{number}"
        folder.mkdir()
        plan = folder / "schedule.csv"
        native.write_rows(plan, schedule(number))
        sessions[folder.name] = sha(plan)
    native.save(args.out / "freeze.json", dict(source=git("rev-parse", "HEAD"), cpp_tree=git("rev-parse", "HEAD:cpp"),
                protocol_sha256=sha(PROTOCOL), binary_sha256=sha(args.binary), cache_sha256=sha(cache),
                compiler=subprocess.check_output([args.compiler, "--version"], text=True).splitlines(),
                mapping_sha256=sha(native.MAPPING), confirmation_sha256=sha(CONFIRMATION), sources=source_hashes(),
                schedules=sessions, created_utc_ns=time.time_ns()))


def collect(args, folder, archive, probe, logical, admission):
    archive.mkdir()
    before = archive / "hwinfo_before.raw"
    shutil.copyfile(args.hwinfo_csv, before)
    cases = workload()
    os_rows, recorded, code, error = [], 0, 0, ""
    probe.sample()
    started = time.time_ns()
    deadline = time.perf_counter() + .1
    with ((folder / "samples.csv").open("x", encoding="utf-8", newline="") as samples,
          (folder / "cuts.csv").open("x", encoding="utf-8", newline="") as cuts,
          (folder / "program.log").open("xb") as log):
        sample_writer = cuts_writer = None
        try:
            for item in read(folder / "schedule.csv"):
                identity, case = cases[item["case"]]
                window, strength, access, *additional = MODEL_ARGUMENTS[item["model"]]
                with TemporaryDirectory(dir=archive) as temp:
                    location = Path(temp)
                    params, output = location / "parameters.txt", location / "assay"
                    params.write_bytes(input_bytes(identity, case))
                    cmd = [args.binary, params, output, "profile-" + item["observation"],
                           str(window), str(strength), str(1 << logical)]
                    if access:
                        cmd.append(str(access))
                    cmd.extend(map(str, additional))
                    log.write(f"{item['sample']} {item['case']} {item['model']} {item['treatment']}\n".encode())
                    log.flush()
                    launch = time.perf_counter_ns()
                    with subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT) as process:
                        deadline = monitor(process, probe, logical, os_rows, deadline)
                        code = process.wait()
                    total = (time.perf_counter_ns() - launch)/1_000_000
                    if code:
                        break
                    summary, = read(output / "summary.csv")
                    costs, = read(output / "profile.csv")
                    row = item | summary | costs | dict(process_ms=total, parameters_sha256=sha(params),
                           midpoint_sqlite_bytes=(output / "midpoint.sqlite").stat().st_size,
                           **{label+"_sha256": sha(output/file) for label, file in
                              (("initial", "initial.chk"), ("frame", "final.frame"), ("facts", "facts.bin"))})
                    sample_writer = append(samples, sample_writer, [row])
                    cuts_writer = append(cuts, cuts_writer, [item | cut for cut in read(output / "timings.csv")])
                    recorded += 1
        except (OSError, ValueError, AssertionError) as exc:
            error = repr(exc)
    receipt = dict(exit_code=code, collector_error=error, rows=recorded, telemetry_rows=len(os_rows),
                   started_utc_ns=started, ended_utc_ns=time.time_ns(), admission_attempt=admission["attempt"],
                   binary_sha256=sha(args.binary), telemetry_uncompressed_sha256=native.telemetry_file(folder, os_rows),
                   hwinfo_before_sha256=sha(before))
    native.save(folder / "receipt.json", receipt)
    time.sleep(5)
    after = archive / "hwinfo_after.raw"
    try:
        shutil.copyfile(args.hwinfo_csv, after)
        native.save(archive / "receipt.json", receipt)
        native.extract(archive.parent, native.MAPPING)
        for name in ("hwinfo.csv", "hwinfo_provenance.json"):
            shutil.copyfile(archive / name, folder / name)
        receipt["hwinfo_after_sha256"] = sha(after)
    except (OSError, ValueError, AssertionError, UnicodeError) as exc:
        receipt["sensor_error"] = repr(exc)
    receipt["host_after"] = native.host()
    receipt["telemetry_qualified"] = telemetry(folder, receipt)[1]
    native.save(folder / "receipt.json", receipt)
    required = len(schedule(int(folder.name[-1])))
    print(f"{folder.name}: {recorded}/{required} samples, qualified telemetry {receipt['telemetry_qualified']}", flush=True)
    return not code and not error and recorded == required and receipt["telemetry_qualified"]


def run(args, first_attempt=1):
    freeze = native.load(args.out / "freeze.json")
    assert freeze["sources"] == source_hashes() and freeze["protocol_sha256"] == sha(PROTOCOL)
    assert freeze["mapping_sha256"] == sha(native.MAPPING) and freeze["confirmation_sha256"] == sha(CONFIRMATION)
    assert freeze["cpp_tree"] == git("rev-parse", "HEAD:cpp") and freeze["binary_sha256"] == sha(args.binary)
    assert not git("status", "--porcelain", "--", "cpp") and not (args.out / "batch_result.json").exists()
    for folder, digest in freeze["schedules"].items():
        assert digest == sha(args.out / folder / "schedule.csv")
    fields = native.header(args.hwinfo_csv)
    assert hashlib.sha256(json.dumps(fields, ensure_ascii=True).encode()).hexdigest() == native.load(native.MAPPING)["source_header_sha256"]
    topology = native.win.topology()
    core = native.selected_core(topology)
    logical = min(core["logical"])
    confirmation = native.load(CONFIRMATION)
    assert (topology, logical) == (confirmation["topology"], confirmation["selected_logical"])
    observer_mask = sum(c["mask"] for c in topology) & ~core["mask"]
    assert native.win.affinity(native.win.current_process(), observer_mask)
    args.archive.mkdir(parents=True)
    start = time.time_ns()
    native.save(args.out / "batch_start.json", dict(started_utc_ns=start, freeze_sha256=sha(args.out / "freeze.json")))
    configuration = dict(before=native.host(), topology=topology, selected_logical=logical, observer_affinity_mask=observer_mask,
                         affinity_mask=1 << logical, binary_sha256=freeze["binary_sha256"])
    for folder in (args.archive, args.out):
        native.save(folder / "configuration.json", configuration)
    completed, outcome = [], "INTERRUPTED"
    try:
        for session in freeze["schedules"]:
            folder = args.out / session
            probe = native.Sampler(topology, (logical,))
            try:
                for attempt in range(first_attempt if not completed else 1, 4):
                    admitted = native.admission(probe, logical, folder, args.hwinfo_csv, fields, attempt)
                    if admitted["admitted"]:
                        break
                    if attempt < 3:
                        time.sleep(300)
                if not admitted["admitted"]:
                    outcome = "ADMISSION_EXHAUSTED"
                    return
                if not collect(args, folder, args.archive/session, probe, logical, admitted):
                    outcome = "STARTED_SESSION_INCOMPLETE"
                    return
                completed.append(session)
            finally:
                probe.close()
        outcome = "COLLECTION_FINISHED"
    finally:
        native.save(args.out / "batch_result.json", dict(outcome=outcome, completed=completed,
                    started_utc_ns=start, ended_utc_ns=time.time_ns()))
        print(outcome, flush=True)


def analyze(raw, output):
    freeze, batch = native.load(raw / "freeze.json"), native.load(raw / "batch_result.json")
    start = native.load(raw / "batch_start.json")
    assert start["freeze_sha256"] == sha(raw / "freeze.json") and start["started_utc_ns"] == batch["started_utc_ns"]
    samples, cuts, sessions = [], [], []
    for name, digest in freeze["schedules"].items():
        folder = raw / name
        plan = read(folder / "schedule.csv")
        assert sha(folder / "schedule.csv") == digest
        assert plan == [{key: str(value) for key, value in row.items()} for row in schedule(int(name[-1]))]
        attempts = [native.load(path) for path in sorted(folder.glob("admission*_receipt.json"))]
        assert len(attempts) <= 3 and all(not a["admitted"] for a in attempts[:-1])
        for i, admission in enumerate(attempts, 1):
            checks = admission["checks"]
            passed = all(checks[k] for k in ("native_intervals_valid", "power_valid", "sensors_valid")) and all(
                checks[k+"_complete"] and checks[k+"_p50"] <= 10 and checks[k+"_p95"] <= 20
                for k in ("system_busy_pct", "processor_busy_pct"))
            assert admission["admitted"] == passed and len(read(folder/f"admission{i}.csv")) == 60
        if not (folder / "receipt.json").exists():
            continue
        receipt = native.load(folder / "receipt.json")
        measured = read(folder / "samples.csv")
        assert attempts[-1]["admitted"] and attempts[-1]["attempt"] == receipt["admission_attempt"]
        assert len(measured) == receipt["rows"] and receipt["binary_sha256"] == freeze["binary_sha256"]
        assert all(all(m[k] == p[k] for k in p) for m, p in zip(measured, plan))
        stats, qualified = telemetry(folder, receipt)
        assert receipt["telemetry_qualified"] == qualified
        sessions.append(dict(session=name, rows=len(measured), qualified=qualified, **stats))
        samples.extend(measured)
        cuts.extend(read(folder / "cuts.csv"))
    rng = Random(640601)
    results = []
    for case, (_, inputs) in workload().items():
        for model in MODEL_ARGUMENTS:
            group = [r for r in samples if r["case"] == case and r["model"] == model]
            capture = [float(r["cut_ms"]) for r in cuts if r["case"] == case and r["model"] == model and r["treatment"] == "on"]
            if len(group) != 24:
                results.append(dict(case=case, model=model, rows=len(group), status="NOT_RUN" if not group else "INCONCLUSIVE"))
                continue
            signatures = ("parameters_sha256", "initial_sha256", "frame_sha256", "facts_sha256", "events", "rng")
            assert len({tuple(r[k] for k in signatures) for r in group}) == 1
            assert len(capture) == 6*(inputs["horizon_ms"]//86_400_000+1) and all(
                int(r["model_version"]) == MODEL_VERSIONS[model] for r in group)
            on = [r for r in group if r["treatment"] == "on"]
            off = [r for r in group if r["treatment"] == "off"]
            rss = [median(int(r["peak_rss_bytes"]) for r in on if r["session"] == s) -
                   median(int(r["peak_rss_bytes"]) for r in off if r["session"] == s) for s in ("1", "2", "3")]
            row = dict(case=case, model=model, rows=len(group), events=group[0]["events"], facts_bytes=group[0]["facts_bytes"],
                       cut_p95_ms=percentile(capture,.95), cut_max_ms=max(capture), rss_increment_mib=max(rss)/1048576)
            passes = row["cut_p95_ms"] <= 5 and row["cut_max_ms"] <= 20 and row["rss_increment_mib"] <= 16
            for metric in ("total_ms", "process_ms"):
                a, b = ([float(r[metric]) for r in g] for g in (on, off))
                aa = [float(r[metric]) for r in group if r["treatment"] == "off-a"]
                bb = [float(r[metric]) for r in group if r["treatment"] == "off-b"]
                ratios = [median(float(r[metric]) for r in on if r["session"] == s)/
                          median(float(r[metric]) for r in off if r["session"] == s) for s in ("1", "2", "3")]
                bounds = [median(rng.choices(ratios, k=3)) for _ in range(4096)]
                p50, p95, aabb = median(a)/median(b), percentile(a,.95)/percentile(b,.95), median(aa)/median(bb)
                row.update({metric+"_p50_ratio":p50, metric+"_p95_ratio":p95, metric+"_off_off":aabb,
                            metric+"_paired_ci_lo":percentile(bounds,.025), metric+"_paired_ci_hi":percentile(bounds,.975)})
                passes &= p50 <= 1.10 and p95 <= 1.20 and .90 <= aabb <= 1.10
            row["status"] = ("PASS" if passes else "FAIL") if len(sessions) == 3 and all(r["qualified"] for r in sessions) else "INCONCLUSIVE"
            results.append(row)
    output.mkdir(parents=True)
    for filename, entries in (("cells.csv", results), ("telemetry_summary.csv", sessions)):
        if entries:
            with (output/filename).open("x", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, list(dict.fromkeys(k for r in entries for k in r)), lineterminator="\n")
                writer.writeheader()
                writer.writerows(entries)
    required = sum(len(schedule(i)) for i in range(1, 4))
    verdict = "NOT_RUN" if not samples else "INCONCLUSIVE" if len(samples) != required or any(r["status"] == "INCONCLUSIVE" for r in results) else (
        "FAIL" if any(r["status"] == "FAIL" for r in results) else "PASS")
    native.save(output / "decision.json", dict(status=verdict, rows=len(samples), required=required, collection=batch["outcome"]))
    print(verdict, f"{len(samples)}/{required} samples", flush=True)


def main(on_prepare=prepare, on_run=run):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "binary", "build", "compiler", "archive", "hwinfo-csv", "analysis"):
        parser.add_argument("--" + name, type=lambda value: Path(value).resolve())
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    if args.analysis:
        analyze(args.out, args.analysis)
    elif args.prepare:
        on_prepare(args)
    else:
        on_run(args)


if __name__ == "__main__":
    main()
