"""Freeze and collect the RM-02 observer benchmark on the admitted Windows host."""

import argparse
import csv
import ctypes
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

import run_s6_3_3_1_performance as native
from analyze_s6_3_3_1_performance import read, telemetry


CELLS = ("dense512", "dense2048", "depot32")
PROTOCOL = native.ROOT / "research/s6_4_rm02_sprint/FROZEN_ENGINEERING_PROTOCOL.md"
BASE = "6f6a69f45b0fff0ba3227039de36158b0994cbc4"
CONFIRMATION = native.ROOT / "experiments/s6_3_3_1/performance/instrument_v2_confirmation/receipt.json"


def schedule(session):
    rows = []
    cells = CELLS[::-1] if session == 2 else CELLS
    for cell in cells:
        for block in range(-1, 13):
            first, second = ("off-a", "off-b") if block == 0 else ("off", "on")
            order = (first, second, second, first)
            if (session + block) % 2 == 0:
                order = (second, first, first, second)
            for slot, treatment in enumerate(order):
                rows.append(dict(sample=len(rows), session=session, cell=cell, block=block, slot=slot,
                                 treatment=treatment, arm="on" if treatment == "on" else "off"))
    return rows


def sources():
    return {**native.dependencies(), Path(__file__).name: native.digest(Path(__file__))}


def prepare(args):
    assert not native.git("status", "--porcelain", "--", "cpp"), "commit the observer before freezing"
    assert not native.git("diff", "--name-only", BASE, "HEAD", "--", "cpp/src", "cpp/include", "cpp/storage")
    compiler = subprocess.check_output([str(args.compiler), "--version"], text=True).splitlines()
    cache = args.build / "CMakeCache.txt"
    settings = cache.read_text(encoding="utf-8")
    assert "CMAKE_BUILD_TYPE:STRING=Release" in settings and "ANTWORLD_SANITIZERS:BOOL=OFF" in settings
    assert "ANTWORLD_PROFILE:BOOL=ON" not in settings
    args.out.mkdir(parents=True)
    schedules = {}
    for session in range(1, 4):
        folder = args.out / f"session{session}"
        folder.mkdir()
        path = folder / "schedule.csv"
        native.write_rows(path, schedule(session))
        schedules[folder.name] = native.digest(path)
    native.save(args.out / "freeze.json", dict(
        source_commit=native.git("rev-parse", "HEAD"), cpp_tree=native.git("rev-parse", "HEAD:cpp"),
        protocol_sha256=native.digest(PROTOCOL), sensor_mapping_sha256=native.digest(native.MAPPING),
        compiler=compiler, configuration="Release", cache_sha256=native.digest(cache),
        executable=args.binary.name, binary_sha256=native.digest(args.binary), schedules=schedules,
        confirmation_sha256=native.digest(CONFIRMATION), sources=sources(), created_utc_ns=time.time_ns()))


def monitor(process, probe, logical, rows, deadline):
    handle = native.win.open_process(0x1000, False, process.pid)
    try:
        while process.poll() is None:
            wait = deadline - time.perf_counter()
            if wait > 0:
                try:
                    process.wait(timeout=wait)
                    break
                except subprocess.TimeoutExpired:
                    pass
            begin = time.perf_counter_ns()
            row = native.os_row(probe, logical)
            ticks = [native.win.W.FILETIME() for _ in range(4)]
            valid = handle and native.win.get_process_times(handle, *(ctypes.byref(t) for t in ticks))
            row.update(pid=process.pid, benchmark_cpu_ns=100 * sum(native.win.filetime(t) for t in ticks[2:])
                       if valid else "", collector_ns=time.perf_counter_ns() - begin)
            rows.append(row)
            deadline = max(deadline + .1, time.perf_counter())
    finally:
        if handle:
            native.win.close(handle)
    return deadline


def append(stream, writer, rows):
    if not rows:
        return writer
    if writer is None:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator="\n")
        writer.writeheader()
    writer.writerows(rows)
    stream.flush()
    return writer


def collect(args, directory, archive, probe, logical, admitted):
    archive.mkdir()
    before = archive / "hwinfo_before.raw"
    shutil.copyfile(args.hwinfo_csv, before)
    rows = []
    error = ""
    observed = 0
    probe.sample()
    started = time.time_ns()
    deadline = time.perf_counter() + .1
    with ((directory / "native.log").open("xb") as log,
          (directory / "samples.csv").open("x", encoding="utf-8", newline="") as samples,
          (directory / "captures.csv").open("x", encoding="utf-8", newline="") as captures):
        sample_writer = capture_writer = None
        code = 0
        try:
            for item in read(directory / "schedule.csv"):
                scratch = archive / f"sample-{item['sample']}"
                command = [str(args.binary), str(scratch), item["cell"], item["arm"], str(1 << logical)]
                log.write(f"sample {item['sample']}: {item['cell']} {item['treatment']}\n".encode())
                log.flush()
                with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT) as process:
                    deadline = monitor(process, probe, logical, rows, deadline)
                    code = process.wait()
                if code:
                    break
                sample, = read(scratch / "sample.csv")
                detail = read(scratch / "captures.csv")
                sample_writer = append(samples, sample_writer, [item | sample])
                capture_writer = append(captures, capture_writer, [item | cut for cut in detail])
                observed += 1
                # The three sample files were created by this child in a new folder.
                # Keep the receipt and timings above and discard only the closed scratch database.
                if item["arm"] == "on":
                    (scratch / "observer.sqlite").unlink()
        except Exception as exc:
            error = repr(exc)
    ended = time.time_ns()
    receipt = dict(exit_code=code, started_utc_ns=started, ended_utc_ns=ended, rows=observed,
                   telemetry_rows=len(rows), binary_sha256=native.digest(args.binary),
                   admission_attempt=admitted["attempt"], collector_error=error,
                   telemetry_uncompressed_sha256=native.telemetry_file(directory, rows),
                   hwinfo_before_sha256=native.digest(before))
    native.save(directory / "receipt.json", receipt)
    time.sleep(5)
    after = archive / "hwinfo_after.raw"
    try:
        shutil.copyfile(args.hwinfo_csv, after)
        native.save(archive / "receipt.json", receipt)
        native.extract(archive.parent, native.MAPPING)
        for name in ("hwinfo.csv", "hwinfo_provenance.json"):
            shutil.copyfile(archive / name, directory / name)
        receipt["hwinfo_after_sha256"] = native.digest(after)
    except (OSError, ValueError, AssertionError, UnicodeError) as exc:
        receipt["sensor_error"] = repr(exc)
    receipt["host_after"] = native.host()
    _, valid = telemetry(directory, receipt)
    receipt["telemetry_qualified"] = valid
    native.save(directory / "receipt.json", receipt)
    print(f"{directory.name}: exit={code}, rows={observed}, telemetry qualified={valid}", flush=True)
    return code == 0 and observed == 168 and not error and valid


def run(args):
    freeze = native.load(args.out / "freeze.json")
    assert freeze["protocol_sha256"] == native.digest(PROTOCOL) and freeze["sources"] == sources()
    assert freeze["sensor_mapping_sha256"] == native.digest(native.MAPPING)
    assert freeze["confirmation_sha256"] == native.digest(CONFIRMATION)
    assert freeze["binary_sha256"] == native.digest(args.binary)
    assert freeze["cpp_tree"] == native.git("rev-parse", "HEAD:cpp")
    assert not native.git("status", "--porcelain", "--", "cpp")
    for session, value in freeze["schedules"].items():
        assert value == native.digest(args.out / session / "schedule.csv")
    fields = native.header(args.hwinfo_csv)
    header = hashlib.sha256(json.dumps(fields, ensure_ascii=True).encode()).hexdigest()
    assert header == native.load(native.MAPPING)["source_header_sha256"], "sensor layout differs"
    topology = native.win.topology()
    core = native.selected_core(topology)
    logical = min(core["logical"])
    confirmed = native.load(CONFIRMATION)
    assert topology == confirmed["topology"] and logical == confirmed["selected_logical"]
    mask = sum(c["mask"] for c in topology) & ~core["mask"]
    assert native.win.affinity(native.win.current_process(), mask)
    args.archive.mkdir(parents=True)
    started = time.time_ns()
    with (args.out / "batch_start.json").open("x", encoding="utf-8") as marker:
        json.dump(dict(started_utc_ns=started, freeze_sha256=native.digest(args.out / "freeze.json")), marker)
    configuration = dict(before=native.host(), topology=topology, selected_logical=logical, affinity_mask=1 << logical,
                         observer_affinity_mask=mask, target_interval_ms=100, binary_sha256=freeze["binary_sha256"])
    for folder in (args.archive, args.out):
        native.save(folder / "configuration.json", configuration)
    finished = []
    outcome = "INTERRUPTED"
    try:
        for name in freeze["schedules"]:
            folder = args.out / name
            probe = native.Sampler(topology, (logical,))
            try:
                for number in range(1, 4):
                    admitted = native.admission(probe, logical, folder, args.hwinfo_csv, fields, number)
                    if admitted["admitted"]:
                        break
                    if number < 3:
                        time.sleep(300)
                if not admitted["admitted"]:
                    outcome = "ADMISSION_EXHAUSTED"
                    return
                if not collect(args, folder, args.archive / name, probe, logical, admitted):
                    outcome = "STARTED_SESSION_INCOMPLETE"
                    return
                finished.append(name)
            finally:
                probe.close()
        outcome = "COLLECTION_FINISHED"
    finally:
        native.save(args.out / "batch_result.json", dict(outcome=outcome, completed=finished,
                                                        started_utc_ns=started, ended_utc_ns=time.time_ns()))
        print(outcome, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--compiler", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--hwinfo-csv", type=Path)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    for key in ("out", "binary", "build", "compiler", "archive", "hwinfo_csv"):
        value = getattr(args, key)
        if value:
            setattr(args, key, value.resolve())
    if args.prepare:
        if not args.build or not args.compiler:
            parser.error("--prepare requires --build and --compiler")
        prepare(args)
    else:
        if not args.archive or not args.hwinfo_csv:
            parser.error("collection requires --archive and --hwinfo-csv")
        run(args)


if __name__ == "__main__":
    main()
