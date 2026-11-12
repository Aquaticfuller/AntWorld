"""Generate the approved F1 inputs without simulating any outcomes."""

import argparse
import hashlib
from itertools import product
import json
from pathlib import Path

from wp6a_budget_screen import DAY_MS, POPULATIONS, PRIMARY_SEEDS, STAGES, nominal, ordinary_cases, read_envelope


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "experiments/s6_4_wp6b/freeze"
DAY_PARAMETERS = ("first_lay_delay", "opening_bout_width", "lay_interval", "maternal_floor")


def supplemental(envelope):
    base = nominal(envelope)
    for population in POPULATIONS:
        variants = [("micro", "nominal", {})]
        for key, (low, _, high) in envelope.items():
            if low == high or key.startswith("f2_") or key.startswith(tuple(p for p in POPULATIONS if p != population)):
                continue
            variants.extend(("wider", f"{key}-{level}", {key: value}) for level, value in (("low", low), ("high", high)))
        for basal, lipid, water_loss in product((0, 2), repeat=3):
            variants.append(("wider", f"egg-stock-{basal}-{lipid}-{water_loss}", {
                "egg_basal": envelope["egg_basal"][basal], "egg_lipid": envelope["egg_lipid"][lipid],
                "egg_water_loss": envelope["egg_water_loss"][water_loss], "egg_water": envelope["egg_water"][0],
            }))
        for level in (0, 2):
            keys = ("queen_basal", "queen_water_loss", *(f"{s}_{k}" for s in STAGES for k in ("basal", "water_loss")))
            variants.append(("wider", f"coherent-rates-{level}", {key: envelope[key][level] for key in keys}))
        variants.extend(("micro", label, {}) for label in ("contact-blocked", "care-off"))
        for group, label, overrides in variants:
            profile = base | overrides
            for seed in PRIMARY_SEEDS:
                yield case(population, group, label, seed, profile)
        for workers, label, seed in product((8, 32), ("depot", "blocked", "empty", "low-protein"), PRIMARY_SEEDS):
            yield case(population, "early", label, seed, base, workers)


def case(pop, group, label, seed, profile, workers=0):
    parameters = {key: int(value) for key, value in profile.items()
                  if not key.startswith((*POPULATIONS, "f2_")) and key not in DAY_PARAMETERS}
    parameters.update({f"{s}_ms": int(profile[f"{pop}_{s}"] * DAY_MS) for s in STAGES})
    parameters.update({f"{key}_ms": int(profile[key] * DAY_MS) for key in DAY_PARAMETERS})
    mass = [0, 0, 0, 0]
    if workers and label != "empty":
        mass = [200_000 * workers, (200 if label == "low-protein" else 20_000) * workers, 100_000 * workers, 0]
    return dict(case=f"{pop}-{group}-{label}-{workers}-{seed}", variant="F1", condition="B06_NOMINAL_25C",
                population=pop, software_seed=seed, group=group, arm=label, care_enabled=label != "care-off",
                horizon_ms=90 * DAY_MS, external_food_ug=sum(mass), external_food_components_ug=mass,
                externally_seeded_workers=workers, parameters=parameters)


def encode(cases):
    return "".join(json.dumps(case, sort_keys=True) + "\n" for case in cases).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Create the input files for the initial freeze.")
    args = parser.parse_args()
    envelope = read_envelope()
    for filename, cases in (("ordinary.jsonl", list(ordinary_cases(envelope))),
                            ("supplemental.jsonl", list(supplemental(envelope)))):
        data = encode(cases)
        if args.write:
            FREEZE.mkdir(parents=True, exist_ok=True)
            (FREEZE / filename).write_bytes(data)
        if (FREEZE / filename).read_bytes() != data:
            raise SystemExit(f"Frozen file differs: {filename}")
        print(f"{filename} {len(cases)} {hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
