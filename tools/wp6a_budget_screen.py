"""Check necessary warm-founding budgets with exact arithmetic, without simulating ants."""

import argparse
import csv
from fractions import Fraction
import io
from itertools import product
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "research/s6_4_wp6a"
ENVELOPE = PACKAGE / "FOUNDRESS_PARAMETER_ENVELOPE.csv"
RECEIPT = PACKAGE / "BUDGET_FEASIBILITY.csv"
DAY_MS = 86_400_000
POPULATIONS = ("borisovka", "st_petersburg")
STAGES = ("egg", "larva", "pupa")
PRIMARY_SEEDS = (1, 7, 19, 42, 43, 97)
CHECK_SEEDS = (2, 11, 23, 47, 71, 103)
CHECK_PROFILES = (0, 5, 10, 15, 16, 21, 26, 31)
ORDINARY_FACTORS = {
    "maternal_lipid": (5_000, 7_000),
    "queen_basal": (2_000_000_000, 2_900_000_000),
    "egg_lipid": (11, 16),
    "egg_basal": (10_000_000, 22_000_000),
    "maternal_water": (6_000, 9_000),
}


def read_envelope(path=ENVELOPE):
    result = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            key = row["Key"]
            bounds = tuple(Fraction(row[name]) for name in ("Low", "Nominal", "High"))
            if key in result or not 0 < bounds[0] <= bounds[1] <= bounds[2]:
                raise ValueError(f"invalid or duplicate parameter bounds for {key}")
            if row["ModelEvidenceGrade"] not in ("A", "B", "C", "D") or not all(row.values()):
                raise ValueError(f"incomplete evidence for {key}")
            result[key] = bounds
    for key, levels in ORDINARY_FACTORS.items():
        low, _, high = result[key]
        if not low <= levels[0] < levels[1] <= high:
            raise ValueError(f"ordinary range is outside the envelope for {key}")
    return result


def nominal(envelope):
    return {key: value[1] for key, value in envelope.items()}


def ordinary(envelope):
    """Generate all preregistered corners in factorial order."""
    for values in product(*ORDINARY_FACTORS.values()):
        overrides = dict(zip(ORDINARY_FACTORS, values, strict=True))
        yield nominal(envelope) | overrides


def ordinary_cases(envelope):
    durations_in_days = ("first_lay_delay", "opening_bout_width", "lay_interval", "maternal_floor")
    for pop in POPULATIONS:
        for index, profile in enumerate(ordinary(envelope)):
            validate(profile)
            parameters = {key: int(value) for key, value in profile.items()
                          if not key.startswith((*POPULATIONS, "f2_")) and key not in durations_in_days}
            parameters |= {f"{stage}_ms": int(profile[f"{pop}_{stage}"] * DAY_MS) for stage in STAGES}
            parameters |= {f"{key}_ms": int(profile[key] * DAY_MS) for key in durations_in_days}
            seed_sets = [("primary", PRIMARY_SEEDS)]
            if index in CHECK_PROFILES:
                seed_sets.append(("check", CHECK_SEEDS))
            for group, seeds in seed_sets:
                for seed, care in product(seeds, (True, False)):
                    yield dict(case=f"{pop}-{index:02}-{group}-{seed}-{'on' if care else 'off'}", variant="F1",
                               condition="B06_NOMINAL_25C", population=pop, software_seed=seed, profile_index=index,
                               group=group, care_enabled=care, horizon_ms=90 * DAY_MS, external_food_ug=0,
                               externally_seeded_workers=0, parameters=parameters)


def floor(value):
    return value // 1


def ceil(value):
    return -floor(-value)


def strict_positive_units(demand, unit=1):
    """Whole units to cover demand while retaining a positive remainder."""
    return max(0, floor(Fraction(demand, unit)) + 1)


def accessible_protein(profile, age_days, variant):
    stock = profile["maternal_protein"]
    if variant == "F1":
        return stock
    if variant != "F2":
        raise ValueError("unknown reserve hypothesis")
    locked = floor(Fraction(stock * profile["f2_locked_fraction"], 1000))
    fraction = (age_days - profile["f2_release_onset"]) / profile["f2_release_width"]
    return stock - locked + floor(locked * max(0, min(1, fraction)))


def validate(profile):
    if sum(profile[name] for name in ("maternal_lipid", "maternal_protein", "maternal_water",
                                      "structural_minimum")) > profile["foundress_wet_mass"]:
        raise ValueError("initial compartments exceed wet mass")
    if profile["larva_basal"] < max(profile["egg_basal"], profile["pupa_basal"]):
        raise ValueError("stage rates violate the candidate ordering")
    if profile["larval_lipid_capacity"] < profile["egg_lipid"]:
        raise ValueError("larval lipid capacity excludes a possible hatch")
    if profile["larval_tissue_target"] <= profile["egg_protein"]:
        raise ValueError("no-feeding control has no protein requirement")
    duration_keys = ("first_lay_delay", "opening_bout_width", "lay_interval", "maternal_floor")
    if any((profile[key] * DAY_MS) % 1 for key in duration_keys):
        raise ValueError("schedule cannot be represented in whole milliseconds")
    for pop in POPULATIONS:
        if any((profile[f"{pop}_{stage}"] * DAY_MS) % 1 for stage in STAGES):
            raise ValueError("clock cannot be represented in whole milliseconds")


def screen(profile, pop, variant="F1", care=True):
    """Compute margins for one offspring with ideal timed resource access.

    This lower bound omits competing siblings, action/assimilation delays and
    optional activity costs. Positive margins cannot certify actual emergence.
    """
    validate(profile)
    e_day, l_day, p_day = (profile[f"{pop}_{stage}"] for stage in STAGES)
    p = profile
    y = p["lipid_yield"]
    lay = p["first_lay_delay"]
    pupa = lay + e_day + l_day
    emergence = pupa + p_day
    e_at_hatch = p["egg_lipid"] * y - p["egg_basal"] * e_day
    w_at_hatch = p["egg_water"] - p["egg_water_loss"] * e_day
    minimum = (strict_positive_units(p["larva_basal"] * l_day + p["pupa_basal"] * p_day - e_at_hatch, y),
               p["larval_tissue_target"] - p["egg_protein"],
               strict_positive_units(p["larva_water_loss"] * l_day + p["pupa_water_loss"] * p_day - w_at_hatch))
    limits = tuple(p[f"ration_{material}_limit"] for material in ("lipid", "protein", "water"))
    min_acts = max(ceil(Fraction(needed, cap)) for needed, cap in zip(minimum, limits, strict=True))
    energy0 = p["maternal_lipid"] * y
    energy_debit = (p["egg_lipid"] + minimum[0]) * y + p["lay_overhead"]
    water_debit = p["egg_water"] + minimum[2]
    lay_p = accessible_protein(p, lay, variant)
    bout_end = lay + p["opening_bout_width"]
    opening_slots = ceil(Fraction(p["opening_bout_width"] * DAY_MS, p["opening_lay_spacing"]))
    lay_energy = p["egg_lipid"] * y + p["lay_overhead"]
    headroom_days = lay + p["maternal_floor"]
    headroom_energy = energy0 - headroom_days * p["queen_basal"]
    headroom_water = p["maternal_water"] - headroom_days * p["queen_water_loss"]
    opening_egg_upper_bound = max(0, min(opening_slots, ceil(Fraction(headroom_energy, lay_energy)) - 1,
                                        ceil(Fraction(headroom_water, p["egg_water"])) - 1,
                                        floor(Fraction(accessible_protein(p, bout_end, variant), p["egg_protein"]))))
    lay_fundable = (headroom_energy > lay_energy and headroom_water > p["egg_water"] and
                    lay_p >= p["egg_protein"])
    p_margin = accessible_protein(p, pupa, variant) - p["egg_protein"] - minimum[1]
    queen_energy_pupa = energy0 - p["queen_basal"] * pupa - energy_debit
    queen_water_pupa = p["maternal_water"] - p["queen_water_loss"] * pupa - water_debit
    queen_energy_end = energy0 - p["queen_basal"] * emergence - energy_debit
    queen_water_end = p["maternal_water"] - p["queen_water_loss"] * emergence - water_debit
    # The larval body buffer can carry one conversion quantum above its target.
    pulse_target = Fraction(2 * p["refill_period"] * p["larva_basal"], DAY_MS)
    maximum_pupal_energy = (p["larval_lipid_capacity"] + ceil(pulse_target / y) + 1) * y
    hatch_fundable = e_at_hatch > 0 and w_at_hatch > 0
    nutrient_available = p_margin >= 0 and (care or min_acts == 0)
    pupal_capacity_possible = maximum_pupal_energy > p["pupa_basal"] * p_day
    through_pupa = (lay_fundable and hatch_fundable and nutrient_available and pupal_capacity_possible and
                    queen_energy_pupa > 0 and queen_water_pupa > 0)
    return dict(opening_opportunities=opening_slots, optimistic_opening_eggs_upper_bound=opening_egg_upper_bound,
                lay_available_protein_ug=lay_p, optimistic_lay=int(lay_fundable),
                hatch_energy_margin_nj=e_at_hatch, hatch_water_margin_ug=w_at_hatch,
                optimistic_hatch=int(lay_fundable and hatch_fundable),
                minimum_brood_lipid_ug=minimum[0], minimum_brood_protein_ug=minimum[1],
                minimum_brood_water_ug=minimum[2], minimum_local_rations=min_acts,
                maternal_protein_margin_at_pupation_ug=p_margin, optimistic_pupal_capacity=int(pupal_capacity_possible),
                maternal_energy_margin_at_pupation_nj=queen_energy_pupa,
                maternal_water_margin_at_pupation_ug=queen_water_pupa,
                maternal_energy_margin_at_emergence_nj=queen_energy_end,
                maternal_water_margin_at_emergence_ug=queen_water_end,
                ideal_path_with_mother_alive_to_pupation=int(through_pupa),
                ideal_path_with_mother_alive_to_emergence=int(through_pupa and queen_energy_end > 0 and queen_water_end > 0))


def legacy_warm(envelope, population):
    """Original RM-01 engineering budget at the conditional B06 clock."""
    duration_ms = envelope[f"{population}_egg"][1] * DAY_MS
    energy = 500_000_000  # nJ, with the original 1 nJ/ms cost.
    water = 200         # µg, with the original 1 µg/h cost.
    return dict(legacy_energy_exhaustion_ms=energy, legacy_water_exhaustion_ms=water * 3_600_000,
                legacy_hatch_clock_ms=duration_ms, optimistic_hatch=int(duration_ms < min(energy, water * 3_600_000)))


def results(envelope):
    base = nominal(envelope)
    for pop in POPULATIONS:
        yield dict(case="original_warm_budget", population=pop, variant="LEGACY", care_enabled="", profile_index="",
                   **legacy_warm(envelope, pop))
        cases = [
            ("nominal", "F1", True, base), ("nominal", "F2", True, base),
            ("no_care", "F1", False, base),
            ("egg_fuel_stress", "F1", True, base | {"egg_lipid": 6, "egg_basal": 30_000_000}),
            ("egg_water_stress", "F1", True, base | {"egg_water": 35, "egg_water_loss": 5}),
            ("maternal_fuel_stress", "F1", True, base | {"maternal_lipid": 3_000, "lipid_yield": 30_000_000,
                                                        "queen_basal": 3_200_000_000}),
        ]
        for name, variant, care, profile in cases:
            yield dict(case=name, population=pop, variant=variant, care_enabled=int(care), profile_index="",
                       **screen(profile, pop, variant, care))
        for index, profile in enumerate(ordinary(envelope)):
            for care in (True, False):
                yield dict(case="ordinary", population=pop, variant="F1", care_enabled=int(care), profile_index=index,
                           **screen(profile, pop, "F1", care))


def csv_bytes(records):
    records = list(records)
    fields = list(dict.fromkeys(key for row in records for key in row))
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return text.getvalue().encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--write", action="store_true", help="Refresh the proposed budget receipt from the declared ranges.")
    output.add_argument("--emit-cases", type=Path, metavar="FILE",
                        help="Write ordinary and check-seed assay inputs as reproducible JSON lines.")
    args = parser.parse_args()
    envelope = read_envelope()
    if args.emit_cases:
        cases = list(ordinary_cases(envelope))
        data = "".join(json.dumps(case, sort_keys=True) + "\n" for case in cases).encode("utf-8")
        args.emit_cases.write_bytes(data)
        print(f"Wrote {len(cases)} prospective F1 cases")
        return
    records = list(results(envelope))
    data = csv_bytes(records)
    if args.write:
        RECEIPT.write_bytes(data)
    elif RECEIPT.read_bytes() != data:
        raise SystemExit("WP-6A budget receipt differs")
    print(f"Checked {len(records)} exact budget rows. These are necessary-condition screens, not simulated outcomes.")


if __name__ == "__main__":
    main()
