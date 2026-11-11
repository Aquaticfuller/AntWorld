#!/usr/bin/env python3
"""Reproduce the isolated RM-01 matrix and its matched-work observer measurements."""

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import struct
import subprocess
import time
from pathlib import Path

from run_s6_3_4 import ROOT, cpu_ticks, cpu_window, file_hash, power_plan, processor, utc_now, write_json
from verify_s6_3_4_archive import audit


BASELINE = "51436048db93da8fbcfe4ff738ff74644bfa1731"
CORE_TREE = "277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69"
PROFILES = ("legacy", "borisovka", "st-petersburg")
SHORT = tuple((profile, arm) for profile in PROFILES for arm in ("seed", "funded", "sentinel"))
SHORT += (("borisovka", "energy-tie"), ("st-petersburg", "energy-tie"),
          ("legacy", "water-tie"), ("legacy", "interrupted"))
ECOLOGY = tuple((profile, f"{supply}-{workers}") for workers in (8, 32)
                for supply in ("ordinary", "scarce", "depot") for profile in PROFILES)
APP = "antworld_s6_4_egg_timing"
CODE_PATHS = (
    "cpp/CMakeLists.txt", "cpp/apps/antworld_s6_4_egg_timing.cpp", "cpp/apps/rm01_egg_timing.hpp",
    "cpp/tests/test_s6_4_egg_timing.cpp", "cpp/tests/test_s6_4_rm01.cmake",
)
PORTABLE = {"configuration.csv", "observations.csv", "eggs.csv", "facts.csv", "summary.csv", "cuts.csv"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_identity(build, configuration):
    require(git("rev-parse", f"{BASELINE}:cpp") == CORE_TREE, "wrong frozen tree")
    subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], cwd=ROOT, check=True)
    paths = set(git("diff", "--name-only", BASELINE, "HEAD", "--", "cpp").splitlines())
    require(paths == set(CODE_PATHS), "C++ changes do not match the authorized app and test paths")
    require(not git("status", "--porcelain", "--", "cpp", "tools/run_s6_4_rm01.py"),
            "commit the implementation before capturing evidence")
    text = (build / "CMakeCache.txt").read_text(encoding="utf-8")
    cache = dict(re.findall(r"^([^/#][^:=\n]*):[^=\n]+=(.*)$", text, re.MULTILINE))
    require(Path(cache["AntWorld_SOURCE_DIR"]).resolve() == ROOT / "cpp", "build is from a different source tree")
    require(not cache["CMAKE_BUILD_TYPE"] or cache["CMAKE_BUILD_TYPE"] == configuration,
            "requested configuration differs from the build")
    if configuration == "Release":
        require(cache["ANTWORLD_SANITIZERS"] == "OFF" and cache["ANTWORLD_PROFILE"] == "OFF",
                "Release evidence requires the uninstrumented build")
    subprocess.run([cache["CMAKE_COMMAND"], "--build", str(build), "--config", configuration,
                    "--target", APP], cwd=ROOT, check=True)
    filename = APP + (".exe" if os.name == "nt" else "")
    candidates = [build / configuration / filename, build / filename]
    binary = next(path for path in candidates if path.is_file())
    compiler_files = list((build / "CMakeFiles").glob("*/CMakeCXXCompiler.cmake"))
    compiler = max(compiler_files, key=lambda path: path.stat().st_mtime_ns).read_text(encoding="utf-8")
    compiler_id, version = [re.search(rf'set\(CMAKE_CXX_COMPILER_{field} "([^"]+)"\)', compiler)[1]
                            for field in ("ID", "VERSION")]
    return binary, {
        "baseline_commit": BASELINE, "baseline_cpp_tree": CORE_TREE, "code_commit": git("rev-parse", "HEAD"),
        "cpp_tree": git("rev-parse", "HEAD:cpp"), "configuration": configuration, "compiler": f"{compiler_id} {version}",
        "generator": cache["CMAKE_GENERATOR"], "sanitizers": cache["ANTWORLD_SANITIZERS"],
        "executable": binary.name, "executable_bytes": binary.stat().st_size, "executable_sha256": file_hash(binary),
        "source_sha256": {path: file_hash(ROOT / path) for path in (*CODE_PATHS, "tools/run_s6_4_rm01.py")},
    }


def facts_csv(path, published):
    digest = hashlib.sha256()
    prefix = None
    count = 0
    previous_time = 0
    for count, row in enumerate(csv_rows(path), 1):
        canonical = bytes.fromhex(row["canonical_hex"])
        identity, _, _, time_ms, source = struct.unpack_from("<5Q", canonical)
        require(identity == count == int(row["event_id"]) and previous_time <= time_ms == int(row["time_ms"])
                and source == int(row["source_id"]) and canonical[65] == int(row["kind_code"]),
                "event CSV disagrees with its ordered canonical payloads")
        previous_time = time_ms
        digest.update(struct.pack("<I", len(canonical)))
        digest.update(canonical)
        if count == published["facts"]:
            prefix = digest.hexdigest()
    require(prefix == published["canonical_sha256"], "event CSV prefix differs from SQLite canonical bytes")
    return count, digest.hexdigest()


def run_trial(binary, root, identity, label, profile, arm, observe):
    evidence = root / "evidence" / label
    evidence.mkdir()
    raw = root / "raw" / label
    command = [binary, raw, profile, arm, "1"] + ([] if observe else ["quiet"])
    begin = utc_now()
    cpu_begin = cpu_ticks()
    start = time.monotonic()
    with (evidence / "console.log").open("wb") as log:
        run = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    native_seconds = time.monotonic() - start
    finish = utc_now()
    receipt = dict(identity, profile=profile, arm=arm, seed=1, observer=observe, started_utc=begin, finished_utc=finish,
                   native_wall_seconds=native_seconds, exit_code=run.returncode,
                   system_cpu_during_process=cpu_window(cpu_begin, cpu_ticks()),
                   biological_status="BIOLOGICAL_NOT_VALIDATED")
    if raw.exists():
        receipt["outputs"] = {path.name: {"bytes": path.stat().st_size, "sha256": file_hash(path)}
                              for path in sorted(raw.iterdir()) if path.is_file()}
        for path in raw.iterdir():
            if path.name in PORTABLE:
                shutil.copyfile(path, evidence / path.name)
    status = "ENGINEERING_FAIL"
    if run.returncode == 0:
        try:
            published, = audit(raw / "world.sqlite")
            summary, = csv_rows(raw / "summary.csv")
            if (raw / "facts.csv").exists():
                count, sha = facts_csv(raw / "facts.csv", published)
                require(count == int(summary["facts"]), "full short trace count differs from summary")
            else:
                count, sha = published["facts"], published["canonical_sha256"]
                require(count == int(summary["facts"])
                        and published["frames"][-1]["frame_sha256"] == file_hash(raw / "final.frame"),
                        "ecology final frame or cursor differs from the durable tip")
            receipt["canonical_sha256"] = sha
            receipt["published_canonical_sha256"] = published["canonical_sha256"]
            receipt["published_frame_count"] = len(published["frames"])
            receipt["fact_count"] = count
            status = "ENGINEERING_PASS"
        except (OSError, ValueError, KeyError, sqlite3.Error, struct.error) as error:
            receipt["audit_error"] = str(error)
    receipt["engineering_status"] = status
    write_json(evidence / "receipt.json", receipt)
    print(f"{label} {status}", flush=True)
    return receipt


def admission(root):
    windows = []
    for _ in range(2):
        first = cpu_ticks()
        start = time.monotonic()
        time.sleep(5)
        window = cpu_window(first, cpu_ticks())
        if window is not None:
            windows.append(dict(window, seconds=time.monotonic()-start))
    accepted = len(windows) == 2 and all(w["busy_percent"] <= 25 for w in windows)
    write_json(root / "evidence" / "admission.json", {
        "recorded_utc": utc_now(), "operating_system": platform.platform(), "processor": processor(),
        "logical_cpus": os.cpu_count(), "power_plan": power_plan(), "windows": windows,
        "temperature": "NOT MEASURED", "clock": "NOT MEASURED", "package_power": "NOT MEASURED",
        "status": "ADMITTED" if accepted else "REJECTED",
    })
    return accepted


def paired_observation(binary, root, identity):
    pairs = []
    for phase in ("baseline", "observer"):
        for repeat in range(6):
            prefix = f"{phase}-{repeat:02}"
            names = [prefix + "-a", prefix + "-b"]
            on = phase == "observer"
            flags = [on and repeat % 2 == 1, on and repeat % 2 == 0]
            a, b = [run_trial(binary, root, identity, name, "legacy", "depot-32", flag)
                    for name, flag in zip(names, flags)]
            require(a["engineering_status"] == b["engineering_status"] == "ENGINEERING_PASS", "paired run failed")
            require(a["canonical_sha256"] == b["canonical_sha256"] and a["fact_count"] == b["fact_count"]
                    and a["outputs"]["final.frame"]["sha256"] == b["outputs"]["final.frame"]["sha256"],
                    "observer pairing changed the facts or final frame")
            first, second = [csv_rows(root / "evidence" / name / "summary.csv")[0] for name in names]
            cost_a, cost_b = (float(sample["advance_ms"]) + float(sample["observer_ms"])
                              for sample in (first, second))
            if flags[0]:
                cost_a, cost_b = cost_b, cost_a
            pairs.append({"pair": prefix, "role": "warmup" if repeat == 0 else "retained",
                          "first_observer_enabled": flags[0], "facts": a["fact_count"],
                          "canonical_sha256": a["canonical_sha256"],
                          "reference_work_ms": cost_a, "comparison_work_ms": cost_b, "ratio": cost_b / cost_a})
        if phase == "baseline":
            retained = [row["ratio"] for row in pairs if row["role"] == "retained"]
            write_json(root / "evidence" / "baseline_envelope.json", {
                "recorded_before_observer_pairs_utc": utc_now(), "retained_pairs": len(retained),
                "min_ratio": min(retained), "max_ratio": max(retained),
                "work": "advance_ms plus observer_ms on the legacy depot-32 horizon",
            })
    write_rows(root / "evidence" / "observer_pairs.csv", pairs)
    for profile in PROFILES[1:]:
        trial = run_trial(binary, root, identity, f"horizon-{profile}", profile, "depot-32", True)
        require(trial["engineering_status"] == "ENGINEERING_PASS", "warm horizon case failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("output", type=Path, help="New directory for results and unpublished checkpoints")
    parser.add_argument("--mode", choices=("assay", "observer"), default="assay")
    parser.add_argument("--configuration", choices=("Debug", "Release"), default="Release")
    args = parser.parse_args()
    if args.mode == "observer" and args.configuration != "Release":
        parser.error("observer measurements require Release")
    binary, identity = build_identity(args.build.resolve(strict=True), args.configuration)
    args.output.mkdir(parents=True)
    (args.output / "raw").mkdir()
    (args.output / "evidence").mkdir()
    write_json(args.output / "evidence" / "build.json", identity)
    if args.mode == "observer":
        if not admission(args.output):
            print("NOT_RUN: frozen observer host admission rejected", flush=True)
            return 2
        paired_observation(binary, args.output, identity)
        return 0
    trials = [run_trial(binary, args.output, identity, f"{profile}-{arm}", profile, arm, True)
              for profile, arm in SHORT + ECOLOGY]
    write_json(args.output / "evidence" / "matrix.json", [
        {key: trial.get(key) for key in ("profile", "arm", "engineering_status", "fact_count", "canonical_sha256")}
        for trial in trials])
    return 0 if all(trial["engineering_status"] == "ENGINEERING_PASS" for trial in trials) else 1


if __name__ == "__main__":
    raise SystemExit(main())
