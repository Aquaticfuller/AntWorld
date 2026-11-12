"""Plot frozen R2 first-meal and finite-water diagnostic endpoints."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from summarize_s6_4_wp6b_r2 import number, read


def plot(root, output):
    rows = list(read(root / "groups.csv"))
    founder = {r["model"]: r for r in rows if r["group"] == "primary" and r["care"] == "1" and r["high_risk"] == "1"}
    water = [r for r in rows if r["group"] == "water"]
    figure, (left, right) = plt.subplots(1, 2, figsize=(11.3, 4.2), layout="constrained")
    labels = ["R1", "H1", "H2", "H1 + H2"]
    modes = ("r1", "h1", "h2", "both")
    heights = [100 * number(founder[m], "maternal_first_meals") / number(founder[m], "hatches") for m in modes]
    bars = left.bar(labels, heights, color="#517e8d", width=.6)
    left.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
    left.set_ylim(0, max(1.0, max(heights) * 1.22))
    left.set_ylabel("Hatched larvae with a paid first meal (%)")
    left.set_title("Borisovka short-energy window\n48 paired worlds per model")
    conditions = ["Reachable", "Blocked", "Absent"]
    scope = [[r for r in water if r["arm"] == f"water-{name.lower()}"] for name in conditions]
    for index, (metric, label, color) in enumerate((("adults", "Eclosed", "#97aab3"),
            ("adults_with_water_uptake", "Absorbed water", "#087d75"),
            ("adults_at_least_7d", "Observed ≥7 days", "#c47534"))):
        bars = right.bar([x + (index - 1) * .25 for x in range(3)],
                         [sum(number(r, metric) for r in records) for records in scope], .23, label=label, color=color)
        right.bar_label(bars, padding=2, fontsize=8)
    right.set_xticks(range(3), conditions)
    right.set_ylabel("Individuals")
    right.set_title("Finite-water treatment\n24 worlds per treatment, both models pooled")
    right.margins(y=.20)
    right.legend(frameon=False, fontsize=8, loc="upper right")
    for axis in (left, right):
        axis.spines[["right", "top"]].set_visible(False)
        axis.set_axisbelow(True)
        axis.grid(axis="y", color="#dddddd", linewidth=.7)
    figure.savefig(output, dpi=170, metadata={"Title": "R2 observed meals and worker hydration"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plot(args.comparison, args.output)
