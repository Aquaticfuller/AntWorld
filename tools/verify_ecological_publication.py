"""Verify the prespecified published witnesses and their reported endpoints."""

import argparse
from collections import Counter
import csv
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from analyze_s6_4_wp6b import check
from diagnose_ecological_care import run as diagnose_care
from ecological_field_precision import original_difference
from founding_qualification_witnesses import COMMAND
from run_ecological_closure import roster
from run_s6_4_wp6b import ROOT, run_one, sha, write_json
from verify_ecological_closure import fixed_witnesses, frozen_names, run
from verify_final_core_integration import check_identity


EVIDENCE = ROOT/"experiments/s6_4_ecological_mechanism_closure"
AUTHORITY = ("initial.chk", "final.frame", "facts.bin")


def csv_rows(path):
    read = gzip.open if path.suffix == ".gz" else open
    with read(path,"rt",encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream))


def manifest(path):
    return [json.loads(line) for line in (path/"archives.jsonl").read_bytes().splitlines()]


def same(expected, actual):
    if expected == actual:
        return True
    try:
        return math.isclose(float(expected),float(actual),rel_tol=1e-13,abs_tol=1e-13)
    except (ValueError,TypeError):
        return False


def compare(path, rebuilt):
    for filename, identity in (("worlds.csv",("case",)),("larvae.csv",("case","ant")),
                               ("receivers.csv",("case","actor")),("stages.csv",("case","ant","stage"))):
        file = rebuilt/filename
        if not file.exists():
            continue
        published = path/"analysis"/filename
        expected = csv_rows(published if published.exists() else published.with_suffix(".csv.gz"))
        expected = {tuple(row[k] for k in identity):row for row in expected}
        for row in csv_rows(file):
            prior = expected[tuple(row[k] for k in identity)]
            check(all(same(prior[k],value) for k,value in row.items()),f"recomputed {filename} differs")
    for filename, identity in (("failures.json","case"),("midpoints.json","case")):
        expected = {r[identity]:r for r in json.loads((path/"analysis"/filename).read_bytes())}
        for row in json.loads((rebuilt/filename).read_bytes()):
            check(row == expected[row[identity]],f"recomputed {filename} differs")


def verify_matrix(path, panel):
    attempts = manifest(path)
    names = frozen_names(panel)
    check([row["case"] for row in attempts] == names,"archived matrix differs from frozen roster")
    by_case = {row["case"]:row["receipt"] for row in attempts}
    worlds = csv_rows(path/"analysis/worlds.csv")
    failures = {r["case"] for r in json.loads((path/"analysis/failures.json").read_bytes())
                if r["status"]!="COMPARISON_NOT_AVAILABLE"}
    check(failures=={row["case"] for row in attempts if row["receipt"]["status"]!="COMPLETE"},
          "a recorded failure is missing from the analysis")
    if panel == "scout":
        observed = {name for name in names if name.endswith("-observed")}
        check({row["case"] for row in worlds} == observed and all(r["status"]=="COMPLETE" for r in by_case.values()),
              "incomplete scout control matrix")
        counts = Counter(r["arm"] for r in worlds if int(r["complete"])>0)
        check(counts["scout"]>=8 and not counts.keys()-{"scout"},"SC-06 delivery decision differs")
        check(all(not int(r["activated"]) for r in worlds if r["arm"] in {"sham","disabled","naive"}) and
              all(not int(r["collections"]) for r in worlds if r["arm"] == "blocked") and
              all(not int(r["deliveries"]) for r in worlds if r["arm"] == "depleted"),
              "adverse scout arm responded")
    else:
        expected = {name for name in names if by_case[name]["mode"]=="observed" and by_case[name]["status"]=="COMPLETE"}
        check({row["case"] for row in worlds} == expected and len(worlds)==len(expected),"incomplete biological denominator")
        check(all(int(by_case[r["case"]]["summary"]["events"])==int(r["source_facts"]) for r in worlds),
              "reported case has a different fact count")
        check(all(not int(r.get(key) or 0) for r in worlds if r["source"] in {"blocked","absent"}
                  for key in ("collection","deliveries")),"food transfer from a blocked or absent source")
        if panel == "care":
            check(all(not int(r["actual_rations"]) for r in worlds if r["treatment"]=="careoff"),
                  "care-off paid a maternal ration")
            check(all(int(r.get("water_sipped_ug") or 0)==int(r["queen_absorbed_w"])==
                      (1200 if r["treatment"]=="water" else 0) for r in worlds),
                  "maternal water control does not match the recorded source and uptake")
            for population in ("borisovka","st_petersburg"):
                first, control = ([int(r["maternal_protein_receivers"]) for r in worlds
                                   if r["population"]==population and r["treatment"]==arm]
                                  for arm in ("first","clock"))
                check(len(first)==len(control)==6 and median(first)>median(control),
                      "first-meal arm does not meet the frozen per-population breadth endpoint")
        else:
            check(all(not int(r["worker_protein_assimilated_lower_bound_ug"]) for r in worlds if r["source"]=="no-protein"),
                  "protein entered the protein-free arm")
    return attempts, worlds


def joint_cells(worlds):
    groups = Counter((r["population"],r["layout"],int(r["reserve"])) for r in worlds
                     if r["treatment"]=="joint" and r["source"]=="balanced" and int(r["joint"]))
    return [{"population":population,"layout":layout,"reserve_ug":reserve,
             "passed":groups[population,layout,reserve],"denominator":6}
            for population in ("borisovka","st_petersburg")
            for layout in ("shaft","dogleg") for reserve in (5500,5250)]


def verify_timing(path):
    timings = csv_rows(path/"measurements.csv")
    expected = {(r["case"],int(r["pair"]),r["mode"]):r for r in timings}
    check(len(timings)==len(expected)==18,"fixed timing sample was omitted")
    for case in {r["case"] for r in timings}:
        for pair in range(1,4):
            authorities = []
            for mode in ("observed","buffered"):
                row = expected[case,pair,mode]
                saved = path/f"{case}-{pair}-{mode}"
                receipt = json.loads((saved/"receipt.json").read_bytes())
                check(receipt["status"]=="COMPLETE" and float(row["wall_ms"])==receipt["elapsed_ms"] and
                      int(row["slot"])==int((mode=="buffered")!=(pair==2)), "diagnostic order or elapsed identity changed")
                required = ["case.json","parameters.txt","program.log","phases.csv","timings.csv","summary.csv"]
                if "total_ms" in row:
                    required.append("profile.csv")
                for name in required:
                    check(sha(saved/name)==receipt["artifacts"][name]["sha256"],f"changed diagnostic sample: {name}")
                check(float(row["max_cut_ms"])==max(float(r["cut_ms"]) for r in csv_rows(saved/"timings.csv")) and
                      all(row[k]==v for k,v in csv_rows(saved/"phases.csv")[0].items()),"reported diagnostic differs")
                if "total_ms" in row:
                    check(all(row[k]==v for k,v in csv_rows(saved/"profile.csv")[0].items()),"changed output sync timing")
                authorities.append([receipt["artifacts"][k] for k in (*AUTHORITY,"cuts.csv","individuals.csv")])
            check(authorities[0]==authorities[1],"row writer changed authority or observations")


def verify_original_portability_failure(precision):
    root = EVIDENCE/"portable-physics/original-linux-divergence"
    digests = json.loads((root/"digests.json").read_bytes())
    check(set(digests)=={"first-observed.zip","first-durable-split.zip"},"original Linux failure modes missing")
    windows = EVIDENCE/"joint-repaired/borisovka-1-shaft-joint-balanced-5500.zip"
    with ZipFile(windows) as archive:
        expected = archive.read("facts.bin")
    for name,digest in digests.items():
        archive = root/name
        check(sha(archive)==digest,"original Linux divergence archive changed")
        with ZipFile(archive) as data:
            for key,prior in precision["old"]["linux"].items():
                raw = data.read(key)
                check(sha256(raw).hexdigest()==prior["sha256"] and len(raw)==prior["bytes"],
                      "original Linux authority differs")
            if name=="first-observed.zip":
                check(original_difference(expected,data.read("facts.bin"))==precision["original_difference"],
                      "original native replay discrepancy changed")


def exe_path(path):
    if not path.is_file():
        path = path.parent/"Release"/(path.stem+".exe")
    return path.resolve(strict=True)


def replay(output, joint_executable, scout_executable):
    binary = exe_path(joint_executable)
    for panel,observed in (
        ("joint","borisovka-1-shaft-joint-balanced-5500"),
        ("joint","st_petersburg-1-dogleg-joint-balanced-5500"),
        ("care","borisovka-1-shaft-water-absent-5500"),
        ("care","borisovka-1-shaft-wallwater-absent-5500"),
    ):
        identity,case,_ = next((i,c,m) for i,c,m in roster(panel) if c["case"]==observed)
        original = next(r["receipt"] for r in manifest(EVIDENCE/"portable-physics"/panel) if r["case"]==observed)
        case = case | {"arm":case["arm"].replace("ecology-","ecology5-",1)}
        durable = run_one(binary,output/observed,identity,case,"durable-split",COMMAND)
        check(durable["status"]=="COMPLETE","fresh ecological recovery failed")
        check_identity(original,durable,observed)
    scout = output/"fresh-scout"
    subprocess.run([exe_path(scout_executable),"1","scout",scout,"durable","portable"],check=True)
    source = EVIDENCE/"portable-physics/scout"
    reference = next(r["receipt"] for r in manifest(source) if r["case"]=="scout-1-observed")
    check(all(sha(scout/k)==reference["artifacts"][k]["sha256"] for k in AUTHORITY),
          "fresh scout recovery changed canonical authority")


def verify(output, joint_executable, scout_executable):
    output.mkdir(parents=True)
    summary = {}
    matrix = csv_rows(ROOT/"research/s6_4_ecological_mechanism_closure/BR_READINESS_MATRIX.csv")
    contexts = {r["SourceContextId"] for r in csv_rows(ROOT/"research/s6_4_preflight/UNIFIED_SOURCE_CONTEXT_REGISTER.csv")}
    check([r["BR"] for r in matrix]==[f"BR-{i:02d}" for i in range(1,10)] and
          all(r["ScientificStatus"]=="BIOLOGICAL_BLOCKED" and r["FixtureGrade"]=="D" and
              r["DirectGrade"] in {"A","B"} and r["HypothesisGrade"]=="C" and
              set(r["SourceContexts"].split(";")) <= contexts and
              r["Readiness"] in {"ENGINEERING_ONLY","NOT_READY"} for r in matrix),"biological gate changed")
    panels = (("scout","scout"),("care","care"),("joint-original","joint"),
              ("joint-expanded","joint"),("joint-repaired","joint"),
              *((f"portable-physics/{panel}",panel) for panel in ("scout","care","joint")))
    archive_audit = json.loads((EVIDENCE/"local_archive_hash_audit.json").read_bytes()) | json.loads(
        (EVIDENCE/"portable-physics/local_archive_hash_audit.json").read_bytes())
    precision = json.loads((EVIDENCE/"portable-physics/platform_comparison.json").read_bytes())
    check(precision["original_difference"]["different_deposits"]==1 and
          precision["original_difference"]["first"]["event"]==421676 and
          all(d["windows"]==d["linux"] for d in precision["portable"].values()),
          "old numerical failure or new byte comparison changed")
    verify_original_portability_failure(precision)
    tests = json.loads((EVIDENCE/"tests/receipt.json").read_bytes())
    for name,entry in tests["local_ctest"].items():
        log = EVIDENCE/"tests"/name
        check(sha(log)==entry["sha256"] and entry["exit_code"]==0 and
              "100% tests passed, 0 tests failed out of 286" in log.read_text(encoding="utf-8"),
              "local CTest receipt does not match the raw log")
    check(len(tests["local_ctest"])==3 and tests["core_ci"]["status"]=="success" and
          len(tests["core_ci"]["jobs"])==5 and all(r["conclusion"]=="success" for r in tests["core_ci"]["jobs"]),
          "test receipt has an incomplete matrix")
    new_tests = EVIDENCE/"portable-physics/tests"
    portable_ctest = json.loads((new_tests/"receipt.json").read_bytes())["local_ctest"]
    check({k:v["tests"] for k,v in portable_ctest.items()}=={"portable-linux-tests.log":6,
          "portable-debug-tests.log":287,"portable-release-tests.log":287,"portable-sanitizer-tests.log":287},
          "portable local test matrix is incomplete")
    for name,entry in portable_ctest.items():
        log = new_tests/name
        count = entry["tests"]
        check(sha(log)==entry["sha256"] and entry["exit_code"]==0 and
              f"100% tests passed, 0 tests failed out of {count}" in log.read_text(encoding="utf-8"),
              "portable local test receipt differs from the raw log")
    with TemporaryDirectory(dir=output) as temp:
        scratch = Path(temp)
        for name,panel in panels:
            path = EVIDENCE/name
            attempts,worlds = verify_matrix(path,panel)
            check(archive_audit[name]=={"manifest_sha256":sha(path/"archives.jsonl"),"verified_archives":len(attempts)},
                  "local digest receipt differs from the complete published manifest")
            failures = [r["case"] for r in attempts if r["receipt"]["status"]!="COMPLETE"]
            selection = (fixed_witnesses(panel) if name in {"scout","care","joint-repaired"} or
                         name.startswith("portable-physics/") else set(failures[:1]) if name=="joint-original" else set())
            summary[name] = dict(attempts=len(attempts),observed=len(worlds),failures=len(failures),public_witnesses=len(selection))
            if panel == "joint":
                cells = joint_cells(worlds)
                summary[name].update(joint_cells=cells,joint_gate="PASS" if all(r["passed"]>=4 for r in cells) else "FAIL")
            if selection:
                run(panel,path,scratch/name,True,selection)
                compare(path,scratch/name)
        check(summary["joint-original"]["failures"]==17 and summary["joint-expanded"]["joint_gate"]=="FAIL",
              "preserved engineering failures changed")
        check(all(summary[name]["failures"]==0 and summary[name]["joint_gate"]=="PASS"
                  for name in ("joint-repaired","portable-physics/joint")),"corrected joint matrix fails the frozen gate")
        diagnosis = scratch/"founder-feeding"
        diagnose_care(EVIDENCE/"care",diagnosis,True)
        table = "founder_feeding_by_larva.csv"
        by_id = {(r["case"],r["ant"]):r for r in csv_rows(EVIDENCE/"care/analysis"/table)}
        for row in csv_rows(diagnosis/table):
            check(all(by_id[row["case"],row["ant"]][k]==v for k,v in row.items()),
                  "first feeding diagnosis differs from raw public witness")
        for panel in ("joint","scout","care"):
            directory = EVIDENCE/"portable-physics"/panel
            comparisons = csv_rows(directory/"comparison/policy_comparison.csv")
            check([r["case"] for r in comparisons]==frozen_names(panel),"portable policy comparison omits a case")
            data = json.loads((directory/"comparison/policy_summary.json").read_bytes())
            changed = Counter(key for row in comparisons
                              for key in (row.get("changed_observed_endpoints") or "").split(";") if key)
            check(data["attempts"]==len(comparisons) and
                  data["old_failures"]==sum(r["before_status"]!="COMPLETE" for r in comparisons) and
                  data["new_failures"]==sum(r["after_status"]!="COMPLETE" for r in comparisons) and
                  data["raw_facts_equal"]==sum(int(r.get("raw_facts_sha_equal") or 0) for r in comparisons) and
                  data["frame_equal"]==sum(int(r.get("final_frame_sha_equal") or 0) for r in comparisons) and
                  data["aligned_only_trail"]==sum(r.get("aligned")=="True" and
                      not int(r.get("other_different_facts") or 0) for r in comparisons) and
                  data["non_trail_fact_difference"]==sum(bool(int(r.get("other_different_facts") or 0)) or
                      r.get("aligned")=="False" for r in comparisons) and
                  data["changed_observed_endpoints"]==changed,"portable comparison totals differ")
        dogleg="st_petersburg-1-dogleg-joint-balanced-5500"
        water="borisovka-1-shaft-water-absent-5500"
        wallwater="borisovka-1-shaft-wallwater-absent-5500"
        for panel,label,case in (("joint","portable","borisovka-1-shaft-joint-balanced-5500"),
                                 ("scout","portable-scout","scout-1-durable"),("joint",dogleg,dogleg),
                                 ("care",water,water),("care",wallwater,wallwater)):
            collected = next(r["receipt"] for r in manifest(EVIDENCE/"portable-physics"/panel) if r["case"]==case)
            check(all(collected["artifacts"][k]==precision["portable"][label]["windows"][k] for k in AUTHORITY),
                  "portable platform comparison differs from formal archive authority")
        verify_timing(EVIDENCE/"timing")
        if joint_executable and scout_executable:
            replay(scratch,joint_executable,scout_executable)
    write_json(output/"public_verification.json",summary | {"fresh_replay":bool(joint_executable),"timing_processes":18})
    print(summary)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--joint-binary",type=Path)
    parser.add_argument("--scout-binary",type=Path)
    args=parser.parse_args()
    if bool(args.joint_binary)!=bool(args.scout_binary):
        parser.error("provide both replay executables")
    verify(args.output,args.joint_binary,args.scout_binary)
