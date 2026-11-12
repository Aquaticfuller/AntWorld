"""Audit archive integrity, local repeat witnesses, material budgets and frozen acceptance."""

import argparse
from collections import defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from analyze_s6_4_wp6b import (DAY_MS, DIED, F_RATION, FEED, OBSERVATION, STAGE, assess, check, csv_out, evaluate, facts, rows)
from diagnose_s6_4_wp6b_r1 import CARE_TICK, CARE_WAKE
from run_s6_4_wp6b import input_bytes, schema_rejection, sha, write_json
from run_s6_4_wp6b_r1 import BASE, EXACT, FREEZE, PROTOCOL, enumerate_cases, reference_records


def audit_witnesses(case, summary, raw, max_kind=F_RATION):
    queen, window, strength = int(summary["queen"]), *case["care_memory"]
    memory = wake = None
    local = False
    counts = dict(repeat_selected=0, repeat_unavailable=0, repeat_expired=0,
                  repeated_positive_protein=0, repeated_interrupted=0)
    chosen = set()
    for event, time, source, kind, actor, payload, marker, stage, outcome, mass, obs in facts(raw, max_kind):
        if wake is not None:
            check(kind == OBSERVATION and source == wake and actor == queen, "repeat annotation has no local selection")
            phase, act, target, bout, *_ = obs
            if phase == 0:
                local |= target == memory[0]
            else:
                check(local and (phase, act, target) == (1, FEED, memory[0]), "repeat bypassed local contact")
                chosen.add(bout)
                wake = None
        if kind == CARE_TICK and marker:
            check(strength and actor == queen and payload == CARE_WAKE and marker in (1, 2, 3) and memory and
                  time > memory[1] and (time-memory[1] >= window) == (marker == 1), "invalid repeat chronology")
            if marker == 3:
                wake, local = source, False
                counts["repeat_selected"] += 1
            else:
                memory = None
                counts["repeat_expired" if marker == 1 else "repeat_unavailable"] += 1
        elif kind == F_RATION:
            check(actor == queen, "nonfounder paid a foundress ration")
            if strength:
                memory = (payload, time, event)
        elif kind == OBSERVATION and actor == queen:
            phase, act, target, bout, *_ = obs
            if phase == 3 and act == FEED and bout in chosen:
                counts["repeated_positive_protein"] += bool(mass[1])
                chosen.remove(bout)
            elif phase == 4 and act == FEED:
                if bout in chosen:
                    counts["repeated_interrupted"] += 1
                    chosen.remove(bout)
                if memory and target == memory[0]:
                    memory = None
        elif memory and ((kind == DIED and actor in (queen, memory[0])) or
                         (kind == STAGE and actor == memory[0]) or (kind == 30 and actor == queen and not payload)):
            memory = None
    check(wake is None, "unterminated repeat selection at the terminal cursor")
    return counts, memory or (0, 0, 0)


def audit_waiting_cut(case, data):
    p = case["parameters"]
    waiting = defaultdict(set)
    for row in rows(data):
        if row["stage"] != "1" or row["enrolled"] != "1" or int(row["stage_progress_ms"]) < p["larva_ms"]:
            continue
        ant = int(row["id"])
        water = (p["pupa_water_loss"]*p["pupa_ms"]+int(row["water_carry"]))//DAY_MS
        energy = (p["pupa_basal"]*p["pupa_ms"]+int(row["energy_carry"]))//DAY_MS
        reasons = []
        if int(row["tissue_protein_ug"]) < p["larval_tissue_target"]:
            reasons.append("protein")
        if int(row["hydration_ug"]) <= water:
            reasons.append("water")
        if int(row["energy_nj"]) + int(row["lipid_ug"])*p["lipid_yield"] <= energy:
            reasons.append("energy")
        waiting["any"].add(ant)
        waiting["_".join(reasons) or "none_at_cut"].add(ant)
    return {f"waiting_cut_{key}": len(values) for key, values in sorted(waiting.items())}


def verify(root, output=None, subset=()):
    index = json.loads((root / "completed.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
    check(manifest["frozen"] == FREEZE and manifest["protocol_sha256"] == sha(PROTOCOL), "run did not bind the frozen protocol")
    check(index["reference_archive_index_sha256"] == sha(BASE / "completed.json"), "reference archive identity changed")
    cases = {c["case"]: (identity, c) for identity, c in enumerate_cases(manifest["model"])}
    ids = set(manifest["cases"])
    check(ids <= cases.keys() and (manifest["selected_subset"] or ids == cases.keys()) and
          len(manifest["cases"]) == index["attempts"] == len(ids) and ids == index["statuses"].keys(), "run denominator changed")
    if manifest["model"] == "v1":
        refs = reference_records()
        for name in sorted(ids):
            result = index["statuses"][name]
            reference = refs[name]
            check(result["exact"] and result["exit_code"] == reference["exit_code"] and
                  result["signature"] == {key: reference["artifacts"].get(key) for key in EXACT}, f"v1 replay differs: {name}")
        print(f"{len(ids)} exact F1 v1 replay receipts")
        return

    wanted = set(subset) if subset else ids
    check(wanted <= ids, "unknown representative case")
    results, timeline, paths, censuses, costs = [], [], [], [], []
    seen, member_count, fact_count = set(), 0, 0
    for filename, digest in index["archives"].items():
        archive = root / filename
        with zipfile.ZipFile(archive) as reader:
            records = [name for name in reader.namelist() if name.endswith("/receipt.json") and name.split("/")[0] in wanted]
            if not records:
                check(bool(subset), f"archive has no indexed case: {filename}")
                continue
            check(sha(archive) == digest, f"archive digest differs: {filename}")
            names = set(reader.namelist())
            if not subset:
                check(len(names) == len(reader.namelist()) and {name.split("/")[0] for name in names} ==
                      {name.split("/")[0] for name in records}, "archive has duplicate or unidentified members")
            for receipt in records:
                name = receipt.split("/")[0]
                record = json.loads(reader.read(receipt))
                identity, case = cases[name]
                status = "INPUT_REJECTED" if schema_rejection(case) else "COMPLETE"
                check(name == record["case"] and name not in seen and record["identity"] == identity and
                      record["status"] == index["statuses"][name] == status, f"bad case receipt: {name}")
                seen.add(name)
                expected_members = {f"{name}/{item}" for item in (*record["artifacts"], "receipt.json")}
                check({item for item in names if item.startswith(name+"/")} == expected_members, "unindexed archive member")
                data = {}
                for item, info in record["artifacts"].items():
                    content = reader.read(f"{name}/{item}")
                    check(len(content) == info["bytes"] and sha256(content).hexdigest() == info["sha256"], f"bad archive member: {name}/{item}")
                    member_count += 1
                    if item in (*EXACT, "program.log"):
                        data[item] = content
                check(json.loads(reader.read(f"{name}/case.json")) == case, "frozen case identity differs")
                check(data["parameters.txt"] == input_bytes(identity, case), "unfrozen input bytes")
                row = dict(case=name, group=case["group"], population=case["population"], care=int(case["care_enabled"]),
                           arm=case.get("arm", "ordinary"), workers=case["externally_seeded_workers"], seed=case["software_seed"],
                           profile=case.get("profile_index"), status=status, sensitivity=case.get("sensitivity"))
                if status == "INPUT_REJECTED":
                    check(record["exit_code"] and record["summary"] is None and data["program.log"].startswith(b"invalid F1 material"),
                          f"unexpected failure instead of the frozen rejection: {name}")
                else:
                    initial, frame, raw = data["initial.chk"], data["final.frame"], data["facts.bin"]
                    check(initial[:16] == frame[8:24] == b"AWCKPTG\x00\x10\x00\x00\x00\x12\x00\x00\x00", "wrong R1 checkpoint marker")
                    summary = record["summary"]
                    check(record["exit_code"] == 0 and int(summary["trace_hash"]) == int.from_bytes(frame[-40:-32], "little"),
                          "frame did not bind the recorded history")
                    try:
                        metrics, life, workers, counts = assess(case, summary, raw, data["cuts.csv"], data["individuals.csv"], profile_version=2)
                        repeat, memory = audit_witnesses(case, summary, raw)
                        check(tuple(int.from_bytes(frame[i:i+8], "little") for i in range(len(frame)-32, len(frame)-8, 8)) == memory,
                              "frame memory differs from committed facts")
                    except ValueError as exc:
                        raise ValueError(f"{name}: {exc}") from exc
                    fact_count += int(summary["events"])
                    row.update(metrics, **repeat, **audit_waiting_cut(case, data["individuals.csv"]))
                    timeline.extend(life)
                    paths.extend(workers)
                    censuses.extend(counts)
                    costs.append(dict(case=name, process_wall_ms=record["elapsed_ms"], **summary))
                results.append(row)
        print(f"{len(seen)}/{len(wanted)} checked {filename}", flush=True)
    check(seen == wanted, "incomplete case coverage")
    if output:
        output.mkdir(parents=True)
        for filename, entries in (("cases.csv", results), ("stage_exposure.csv", timeline), ("offspring.csv", paths),
                                  ("daily_count_timing.csv", censuses), ("assay_costs.csv", costs)):
            csv_out(output / filename, entries)
        if not subset and not manifest["selected_subset"]:
            evaluate(output, results, timeline, censuses)
        write_json(output / "archive_verification.json", dict(archive_index_sha256=sha(root / "completed.json"),
                   run_manifest_sha256=sha(root / "run.json"), case_receipts=len(seen), member_files=member_count,
                   canonical_facts=fact_count, completed=len(costs), verifier_sha256=sha(Path(__file__)),
                   outputs={p.name: sha(p) for p in sorted(output.iterdir())}))
    print(f"{len(seen)} R1 case receipts, {member_count} file hashes and {fact_count} canonical facts verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    verify(args.archive, args.out, args.case)


if __name__ == "__main__":
    main()
