"""Verify the paired social-crop receipts and summarize their prespecified endpoints."""

from collections import Counter, defaultdict
import json
from csv import DictReader

from tools.verify_protected_habitat import DAY, ROOT, SEEDS, check, rows


def require(value, message):
    if not value:
        raise ValueError(message)


def oral_receipts(row):
    totals = defaultdict(lambda: [0, 0, 0, 0])
    source = Counter()
    loads = Counter()
    for key, flow in row["flows"].items():
        parts = key.split("/")
        amounts = flow["mass_ug"]
        require(len(amounts) == 4 and min(amounts) >= 0 and sum(amounts) > 0, key)
        require(flow["events"] >= 1 and 0 < flow["first"][0] <= flow["last"][0] <= row["committed_facts"], key)
        if parts[0] == "collection":
            source[tuple(parts[1:])] += amounts[0]
        elif parts[0] == "social-load":
            require(int(parts[2]) > 0 and amounts[1] == amounts[3] == 0, key)
            loads[tuple(parts[1:])] += amounts[0]
        elif parts[0] == "oral":
            require(parts[1] != parts[2], key)
            for i, amount in enumerate(amounts):
                totals[parts[-1]][i] += amount
    for path, sugar in loads.items():
        require(sugar <= source[path], f"Unfunded social load {path}")
    for role, route in (("Queen", "queen_worker"), ("Larva", "worker_larva")):
        require(totals[role][:3] == row["nutrition_cpw_ug"][route], f"Unmatched mouth flows for {role}")
    for path, (minimum, maximum) in row.get("first_mouth_direct_source_sugar_bounds_ug", {}).items():
        require(0 <= minimum <= maximum <= row["flows"]["oral/" + path]["mass_ug"][0], path)
    if row["supply"] == "absent":
        require(not source and not loads, "An external meal was collected in the absent control")
    return totals


def sustained_growth(row):
    census = {c["day"]: c for c in row["census"]}
    return (census[730]["queen_alive"] and row["transitions"].get("eclosions_after_year_one", 0) > 0
            and census[730]["workers"] > max(census[d]["workers"] for d in (73, 365)))


def later_survival(row):
    first_ids = set(row["first_brood_lives"])
    first_alive = sum(any(stage[-1] == "Adult" for stage in life["stages"]) and not life.get("death")
                      for life in row["first_brood_lives"].values())
    emerged = row["transitions"]["eclosed_workers"] - row["first_brood_eclosed"]
    alive = row["workers_still_alive"] - first_alive
    require(0 <= alive <= emerged, "Invalid later-brood survival count")
    if "worker_eclosion_ms" in row:
        later = set(row["worker_eclosion_ms"]) - first_ids
        dead = {str(d[0]) for d in row["deaths_with_depot"] if d[1] == "Adult"}
        require((len(later), len(later - dead)) == (emerged, alive), "Later worker identities disagree")
    return emerged, alive


def check_last_approaches(chamber):
    cuts = json.loads((ROOT / "SOCIAL_CROP_CONTACT_CUTS.json").read_text(encoding="utf-8"))
    require(cuts["command"] == chamber["command"] and cuts["day"] == 69, "Different contact witness world")
    death = chamber["queen_death"]
    require(cuts["death_time_ms"] == death["time_ms"] and cuts["last_doses"] == {},
            "Death or oral receipts differ in the last observation window")
    poses = cuts["completed_approach_cuts"]
    completed = {int(k.split("/")[0]): v for k, v in cuts["actions_targeting_queen"].items()
                 if k.endswith("/Completed/Approach a nestmate")}
    require(Counter(p["donor"] for p in poses) == completed and len(poses) == 62, "Missing approach cuts")
    previous_event, previous_time = cuts["cursor"], cuts["day"] * DAY
    for p in poses:
        require(previous_event < p["event"] <= p["cursor"] < int(death["event_id"])
                and previous_time <= p["time_ms"] < death["time_ms"] and p["duration_ms"] > 0
                and p["donor_crop_ug"][0] > 0, "Unordered or unfunded approach cut")
        previous_event, previous_time = p["event"], p["time_ms"]
    within_reach = [p for p in poses if p["mouth_gap_m"] <= .00065]
    require(len(within_reach) == 1 and within_reach[0]["donor_forward_m"] < -.00012,
            "Close approach no longer fails the donor's anatomical reach")
    stocks = {i: a["crop_ug"][0] for i, a in cuts["adults_at_death"].items() if a["crop_ug"][0]}
    require(stocks == chamber["other_worker_crop_sugar_at_death_ug"][str(death["event_id"])],
            "Worker crop event ledger differs from exact death snapshot")
    with (ROOT / "SOCIAL_CROP_CONTACT_TRACE.txt").open(encoding="utf-8") as src:
        trace = [{k: int(v) for k, v in record.items()} for record in DictReader(src, delimiter=" ")]
    require([(p["time_ms"], p["donor"]) for p in poses] == [(p["time_ms"], p["donor"]) for p in trace],
            "The diagnostic replay and native poses differ")
    missed = [p for p in trace if not p["centers_in_range"] and p["mouths_in_range"] and p["mouths_visible"]
              and p["possible_step"] and not p["chosen_recipient"] and p["payable_ug"] and p["free_crop_ug"]]
    require(len(missed) == 26, "The center-distance exclusions do not reproduce")


def main():
    panel = rows("SOCIAL_CROP_TRIALS.jsonl")
    expected = {(p, s, "nearby") for p in (50, 52, 53, 54) for s in SEEDS}
    expected.update((p, 2, "absent") for p in (50, 52, 53, 54))
    require(len(panel) == len(expected) and {(r["physics"], r["seed"], r["supply"]) for r in panel} == expected,
            "Missing or duplicated two-year paired world")
    references = {(r["seed"], r["supply"]): r for r in rows("PROTECTED_WATER_TRIALS.jsonl") if r["physics"] == 50}
    witness = json.loads((ROOT / "SOCIAL_CROP_MOUTH_WITNESS.json").read_text(encoding="utf-8"))
    parent, = [r for r in panel if r["command"] == witness["command"]]
    require(parent["initial_sha256"] == witness["initial_sha256"], "Independent mouth witness starts elsewhere")
    check(witness)
    oral_receipts(witness)
    require(witness["census"][-1] in parent["census"] and witness["census"][-1]["day"] == 90,
            "Independent day-90 reproduction disagrees")
    for path in ("oral/9/2/Queen", "oral/9/21/Larva", "oral/9/11/Callow"):
        require(witness["flows"][path]["first"] == parent["flows"][path]["first"], "Individual receipt differs")
    chamber = json.loads((ROOT / "SOCIAL_CROP_CHAMBER_WITNESS.json").read_text(encoding="utf-8"))
    parent, = [r for r in panel if r["command"] == chamber["command"]]
    check(chamber)
    paid = oral_receipts(chamber)
    check_last_approaches(chamber)
    require(all(paid[role][0] > 0 for role in ("Queen", "Larva", "Callow")), "Missing a positive oral route")
    require(parent["queen_death"] == chamber["queen_death"] and chamber["census"][-1] in parent["census"] and
            parent["initial_sha256"] == chamber["initial_sha256"], "Death cut differs in the two-year continuation")
    screen = rows("SOCIAL_CROP_MOUTH_RANGE_SCREEN.jsonl")
    require([(r["physics"], r["seed"], r["supply"], r["census"][-1]["day"]) for r in screen] ==
            [(55, 2, "nearby", 90), (55, 2, "absent", 730)], "Incomplete mouth-range screen")
    for r in screen:
        check(r)
        oral_receipts(r)
    tested = screen[0]
    latest_gift = max(v["last"][1] for k, v in tested["flows"].items() if k.endswith("/Queen"))
    require(not tested["census"][-1]["queen_alive"] and latest_gift < chamber["queen_death"]["time_ms"],
            "Mouth-range rejection disagrees with the frozen endpoints")
    window = json.loads((ROOT / "SOCIAL_CROP_MOUTH_RANGE_DEATH.json").read_text(encoding="utf-8"))
    require(window["command"] == tested["command"] and window["death_time_ms"] == tested["queen_death"]["time_ms"]
            and latest_gift < window["day"] * DAY < window["death_time_ms"] and not window["last_doses"]
            and not window["actions_targeting_queen"], "The exact death window disagrees with the oral history")
    exact_stocks = {i: ant["crop_ug"][0] for i, ant in window["adults_at_death"].items()}
    sampled_stocks = tested["other_worker_crop_sugar_at_death_ug"][str(tested["queen_death"]["event_id"])]
    require(all(exact_stocks[i] == amount for i, amount in sampled_stocks.items()) and sum(exact_stocks.values()) == 1727,
            "Exact terminal crop stock differs from the streamed census for workers present in both")
    meals = window["other_transfers"].values()
    require(sum(m["events"] for m in meals) == 80 and sum(m["mass_ug"][0] for m in meals) == 1294
            and all(k.split("/")[1] != "2" for k in window["other_transfers"]),
            "The competing oral transactions disagree with the source replay")
    samples = window["daily_worker_gap_mm_and_crop_sugar_ug"]
    require([s["time_ms"] for s in samples] == [d * DAY for d in range(66, 83)] and
            all(s["worker_mouths"]["10"][0] > 0.65 and s["worker_mouths"]["10"][1] > 0 for s in samples),
            "A daily mouth cut is missing or disagrees with the contact interpretation")
    require(window["focal_worker"] == 10 and window["focal_fact_counts"].get("Moved", 0) == 0 and
            window["focal_actions"]["Selected/Feed brood"] == window["focal_actions"]["Interrupted/Feed brood"] ==
            sum(window["focal_rejections_by_payload"].values()) == 1039 and
            all(k.endswith("/Out of reach") for k in window["focal_rejections_by_payload"]),
            "Worker 10's completed and rejected actions differ from the recorded failure")
    offer_screen = rows("SOCIAL_CROP_OFFER_SCREEN.jsonl")
    require([(r["physics"], r["seed"], r["supply"], r["census"][-1]["day"]) for r in offer_screen] ==
            [(56, 2, "nearby", 90), (56, 2, "absent", 90)], "Missing a larval offer eligibility control")
    for r in offer_screen:
        check(r)
        oral_receipts(r)
    checked = offer_screen[0]
    require(checked["queen_death"]["time_ms"] == tested["queen_death"]["time_ms"] and
            oral_receipts(checked) == oral_receipts(tested) and checked["census"][-1] == tested["census"][-1],
            "Corrected larval eligibility screen differs in its reported survival or recipient intake")
    first_meal = checked["flows"]["oral/8/16/Larva"]["first"]
    require(checked["recipient_subsequent_uptake"]["16"]["first_pair"][:2] == first_meal,
            "Identified larval uptake lacks its preceding paid meal")
    corrected = json.loads((ROOT / "SOCIAL_CROP_OFFER_DEATH.json").read_text(encoding="utf-8"))
    require(corrected["command"] == checked["command"] and corrected["death_time_ms"] == checked["queen_death"]["time_ms"]
            and corrected["focal_worker"] == window["focal_worker"] and not corrected["focal_rejections_by_payload"]
            and corrected["focal_actions"].get("Selected/Feed brood", 0) == 0
            and corrected["focal_actions"]["Opportunity/Feed brood"] == window["focal_actions"]["Opportunity/Feed brood"]
            and corrected["other_transfers"] == window["other_transfers"]
            and corrected["daily_worker_gap_mm_and_crop_sugar_ug"] == window["daily_worker_gap_mm_and_crop_sugar_ug"]
            and not corrected["actions_targeting_queen"] and not corrected["last_doses"],
            "The independently replayed focal worker does not reproduce the mechanism comparison")
    for r in panel:
        check(r)
        require(r["wick"] == "wet-wick" and r["census"][-1]["day"] == 730, r["command"])
        totals = oral_receipts(r)
        emerged, alive = later_survival(r)
        if r["physics"] == 50:
            old = references[r["seed"], r["supply"]]
            for field in ("command", "initial_sha256", "final_sha256", "committed_facts"):
                require(r[field] == old[field], f"Historical {field} changed")
        print(r["physics"], r["seed"], r["supply"], "queen, larva, callow sugar (ug)",
              *(totals[k][0] for k in ("Queen", "Larva", "Callow")), "730-day workers",
              r["workers_still_alive"], "later cohort emerged/alive", emerged, alive, "sustained growth", sustained_growth(r))


if __name__ == "__main__":
    main()
