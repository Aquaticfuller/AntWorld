"""Independently verify published protected-founding receipts and print per-seed outcomes."""

import json
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1] / "research/single_nest"
DAY = 86_400_000
SEEDS = (1, 2, 3, 17, 29)


def rows(filename):
    return [json.loads(line) for line in (ROOT / filename).read_text(encoding="utf-8").splitlines()]


def check(row):
    for name in ("binary_sha256", "initial_sha256", "final_sha256"):
        digest = row[name]
        if len(digest) != 64 or len(bytes.fromhex(digest)) != 32:
            raise ValueError(f"Invalid {name}")
    census = row["census"]
    days = [c["day"] for c in census]
    if sorted(set(days)) != days:
        raise ValueError("Invalid census order")
    changes = row["transitions"]
    deaths = row["offspring_deaths"]
    lost = lambda stage: sum(n for label, n in deaths.items() if label.startswith(stage + ":"))
    laid, hatch, pupae, workers = (changes.get(k, 0) for k in ("eggs_laid", "hatched", "pupated", "eclosed_workers"))
    expected = [laid - hatch - lost("Egg"), hatch - pupae - lost("Larva"),
                pupae - workers - lost("Pupa"), workers - lost("Adult")]
    if expected != [census[-1][stage] for stage in ("eggs", "larvae", "pupae", "workers")]:
        raise ValueError(f"Individual fates disagree with the terminal census: {row['command']}")
    if any(sum(group.values()) != row["first_brood_eclosed"] for group in row["first_brood_worker_survival"].values()):
        raise ValueError("First-brood age counts disagree with the cohort denominator")
    for c in census:
        death = row["queen_death"]
        if c["queen_alive"] != (death is None or c["day"] * DAY < death["time_ms"]):
            raise ValueError("Founder census disagrees with death time")
    if row["supply"] == "absent" and any(row["delivered_cpw_ug"]):
        raise ValueError("Observed a delivery without external supply")
    if "first_brood_lives" in row:
        lives = list(row["first_brood_lives"].values())
        if len(lives) != row["first_brood_eggs"] or sum(bool(life["feeds"]) for life in lives) != row["first_brood_fed"]:
            raise ValueError("The identified cohort disagrees with its feeding denominator")
        adults = 0
        for life in lives:
            previous_id, previous_time = life["birth_fact"], life["born_ms"]
            stage_times = {}
            for transition, expected_stage in zip(life["stages"], ("Larva", "Pupa", "Adult"), strict=False):
                event, time, stage = transition
                if stage != expected_stage or event <= previous_id or time < previous_time:
                    raise ValueError("Invalid individual stage sequence")
                stage_times[stage] = time
                previous_id, previous_time = event, time
            if len(life["stages"]) > 3:
                raise ValueError("Duplicate individual stage transition")
            adults += int("Adult" in stage_times)
            death = life.get("death")
            if death and (death[0] <= previous_id or death[1] < previous_time):
                raise ValueError("Death precedes the last living stage")
            for event, time, donor, *mass in life["feeds"]:
                if (donor <= 0 or min(mass) < 0 or not any(mass) or "Larva" not in stage_times
                        or time < stage_times["Larva"] or time > stage_times.get("Pupa", time)
                        or (death and event >= death[0])):
                    raise ValueError("Invalid positive larval feeding witness")
        if adults != row["first_brood_eclosed"]:
            raise ValueError("Individual emergence records disagree with the cohort total")


def main():
    experiments = rows("PROTECTED_HABITAT_RECEIPTS.jsonl")
    previous = [r for r in rows("SUSTAINED_FOUNDING_RECEIPTS.jsonl") if r["run"] == "sustained_candidate"]
    for row in experiments + previous:
        check(row)
    for group, group_rows in (
            ("P47", previous),
            ("P48", [r for r in experiments if r["run"] == "protected"]),
            ("P49", [r for r in experiments if r["run"] == "local_dig"]),
            ("P48 nearby", [r for r in experiments if r["run"] == "nearby"])):
        if sorted(r["seed"] for r in group_rows) != list(SEEDS):
            raise ValueError(f"Incomplete or duplicated paired seeds in {group}")
        if any(r["census"][-1]["day"] != 730 for r in group_rows):
            raise ValueError(f"Incomplete follow-up in {group}")
        for r in sorted(group_rows, key=lambda r: r["seed"]):
            by_day = {c["day"]: c for c in r["census"]}
            q = r["queen_death"]
            print(group, r["seed"], f"{r['first_brood_eclosed']}/{r['first_brood_eggs']}",
                  by_day[49]["workers"], by_day.get(73, {}).get("workers", "NA"), by_day[365]["workers"],
                  by_day[730]["workers"], round(q["time_ms"]/DAY, 1) if q else "alive", sep=" | ")
        print("Median living workers at day 49:", median(next(c["workers"] for c in r["census"] if c["day"] == 49)
                                                         for r in group_rows))


if __name__ == "__main__":
    main()
