"""Derive motion and morphology CSVs from the retained native assay cuts."""

from argparse import ArgumentParser
import csv
import gzip
import json
from pathlib import Path
from statistics import median


def motion_row(case, data, census):
    individual = data["individuals"]
    life = sum(a["elapsed_alive_ms"] for a in individual)
    return dict(layout=case["layout"], physics=case["physics"], day=census["day"],
                queen_alive=census["queen_alive"], living_workers=census["living_workers"],
                exact_worker_pairs=census["exact_worker_pairs"],
                body_pairs_excluding_soil_load=census["worker_envelope_pairs_without_soil_load"],
                translating_pct=100*sum(a.get("translation_ms",0) for a in individual)/life if life else None,
                median_longest_no_position_change_h=median(a["longest_no_move_ms"]/3_600_000 for a in individual) if individual else None,
                worker_distance_m=census["cumulative_distance_m"],
                turns=sum(a.get("turns",0) for a in individual), moves_last_day=sum(a.get("last_day_moves",0) for a in individual),
                deliveries=census["exterior_food_deliveries"], transfers=census["transfers"],
                arrangements=census["brood_arrangements"], excavations=census["excavations"])


def dig_rows(case, data):
    for census in data["census"]:
        soil = census["soil"]
        activity = census["activity"]
        yield dict(workers_initialized=case["initialized_workers"], shield=case["shield"], mode=case["mode"],
                   hour=census["time_ms"]/3_600_000, workers_alive=census["living_workers"],
                   same_coordinate_pairs=census["exact_worker_pairs"], floor_mm2=census["area_mm2"],
                   perimeter_mm=census["perimeter_mm"], loaded_floor_mm2=census["loaded_floor_mm2"],
                   wide_cores=len(census["rooms"]), narrow_junctions=len(census["junctions_q"]),
                   narrow_neck_points=len(census["necks_q"]), reachable_workers=census["supported_workers"],
                   clips_section=census["window_contact"], net_soil_q3=soil[4]-soil[5],
                   carried_soil_q3=soil[2], deposited_soil_q3=soil[3], worker_distance_m=activity.get("distance_m",0),
                   excavations=activity.get("SoilExcavated",0), deposits=activity.get("SoilDropped",0),
                   rejected_actions=activity.get("ActionRejected",0), facts=census["facts"])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    motion, shapes, costs = [], [], []
    for path in sorted(args.input.glob("*/*.json.gz")):
        with gzip.open(path,"rt",encoding="utf-8") as f:
            data = json.load(f)
        receipt = data["receipt"]
        case = receipt["case"]
        row = dict(batch=path.parent.name,case=case["case"],seed=case["seed"],
                   error=receipt.get("error"),end_ms=receipt["last_valid_ms"],
                   elapsed_s=receipt["elapsed_s"],native_advance_ms=receipt["advance_ms"],
                   peak_rss_bytes=receipt["memory"]["peak_bytes"],
                   facts=receipt["last_cursor"],frame_bytes=receipt["frame_bytes"],
                   sqlite_bytes=receipt.get("sqlite",{}).get("bytes"),sqlite_save_ms=receipt.get("sqlite",{}).get("save_ms"),
                   sqlite_restore_ms=receipt.get("sqlite",{}).get("restore_ms"),canonical_sha256=receipt["canonical_sha256"])
        costs.append(row)
        common = {k:row[k] for k in ("batch","case","seed")}
        if case["kind"] == "dig":
            shapes.extend(common | cut for cut in dig_rows(case,data))
        else:
            motion.append(common | motion_row(case,data,data["census"][-1]))
    for name, rows in (("motion",motion),("shape_cuts",shapes),("costs",costs)):
        if rows:
            with (args.output/(name+".csv")).open("w",encoding="utf-8",newline="") as stream:
                writer = csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)


if __name__ == "__main__":
    main()
