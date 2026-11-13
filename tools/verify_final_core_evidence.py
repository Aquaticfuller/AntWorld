"""Check the final scientific gate, archived measurements and joint-scope decisions."""

import argparse
from collections import Counter
import csv
from pathlib import Path

from analyze_s6_4_wp6b import check
from final_core_b06_cohorts import analyze
from final_core_integration import PANELS, POPULATIONS, REFERENCE
from final_core_performance_study import historical
from run_s6_4_wp6b import ROOT, write_json
from summarize_final_core_integration import summarize
from verify_final_core_integration import PUBLISHED, jsonl


def records(path):
    with path.open(newline="",encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def compare(output, original):
    for table in output.glob("*.csv"):
        check(table.read_bytes() == (original/table.name).read_bytes(), f"changed derived table: {table.name}")


def verify(output):
    ledger = ROOT/"research/s6_4_final_core_readiness"
    sources = ROOT/"research/s6_4_preflight/UNIFIED_SOURCE_CONTEXT_REGISTER.csv"
    allowed = {r["SourceContextId"] for r in records(sources)}
    br = records(ledger/"S6_4_CORE_READINESS_MATRIX.csv")
    check([r["BR"] for r in br] == [f"BR-{i:02d}" for i in range(1,10)],"missing or duplicated root mechanism")
    check(all(r["ScientificStatus"]=="BIOLOGICAL_BLOCKED" and set(r["SourceContexts"].split(";"))<=allowed and
              r["DirectEvidenceGrade"] in "AB" and r["HypothesisGrade"]=="C" and r["NumericFixturesGrade"]=="D" and
              r["SimulationReadiness"] in ("ENGINEERING_ONLY","NOT_READY") for r in br),"scientific scope or status was promoted")
    output.mkdir(parents=True,exist_ok=True)
    joint, identities, archives = {}, {}, 0
    for panel, (_, _, arms, marked, _) in PANELS.items():
        group = PUBLISHED/("matrix" if panel=="primary" else panel)
        rows = records(group/"worlds.csv")
        collection = list(jsonl(group/"archives.jsonl"))
        check(len(rows)==12*len(arms) and len(collection)==len(rows)+4,"incorrect experiment denominators")
        by_arm = Counter(r["case"].split("-",2)[2] for r in rows)
        check(by_arm==dict.fromkeys(arms,12),"missing adverse worlds")
        by_case = {r["receipt"]["case"]:r["receipt"] for r in collection}
        check(all(int(by_case[r["case"]]["summary"]["events"])==int(r["events"]) for r in rows),"wrong canonical case size")
        check(all(int(r["delivered_c"] or 0)==int(r["delivered_p"] or 0)==int(r["delivered_w"] or 0)==0 for r in rows
                  if r["case"].endswith(("-blocked","-absent"))),"an adverse source delivered")
        joint[panel] = [sum(int(r["joint_chain"]) for r in rows if r["population"]==p and r["case"].endswith("-"+marked))
                        for p in POPULATIONS]
        identities[panel] = len(list(r for r in collection if r["receipt"]["mode"]!="observed"))
        archives += len(collection)
    check(joint=={"primary":[0,0],"shaft":[1,0],"clock":[6,6]} and identities==dict.fromkeys(PANELS,4),
          "a fixed outcome or exact-repeat denominator changed")
    summary = output/"integration-summary"
    summarize(*(PUBLISHED/name for name in ("matrix","shaft","clock")),summary)
    compare(summary,PUBLISHED/summary.name)
    b06 = output/"b06"
    analyze(b06)
    compare(b06,PUBLISHED/b06.name)
    for row in records(b06/"cohort_summary.csv"):
        check(row["all_first_cohort_eclosed"]==row["exact_within_all_reference_ranges"]==row["at_least_within_all_reference_ranges"]=="0",
              "changed B06 endpoint")
    performance = output/"performance"
    performance.mkdir(exist_ok=True)
    old_gate = historical(performance)
    compare(performance,PUBLISHED/performance.name)
    check(old_gate["closure_inherited"]==dict(cells=30,passed=22) and old_gate["closure_v7"]==dict(cells=4,passed=4),
          "changed historical performance decision")
    report = dict(reference=REFERENCE, original_application="FAIL", original_b06="INSUFFICIENT",
                  recruitment="NOT_READY", all_br="BIOLOGICAL_BLOCKED", final_recommendation="FAIL", joint=joint, archives=archives)
    write_json(output/"gate.json",report)
    print(report)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    verify(parser.parse_args().output)
