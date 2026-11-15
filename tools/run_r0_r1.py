"""Run the R0-r1 comparisons from the native Core and export bounded witnesses."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from contextlib import closing
import gzip
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from subprocess import check_output
from tempfile import TemporaryDirectory
from time import perf_counter
from zipfile import ZIP_DEFLATED, ZipFile

from op0 import DAY
from op0.archive import PUBLISHED, file_hash, json_bytes
from op0.codec import KINDS, checkpoint
from op0.live import NativeCore, core_path
from op0.morphology import floor_shape
from tools.run_r0_diagnostics import Traffic, journal


HOUR = 3_600_000
MODES = ("r0", "hex", "feedback", "full")


def motion_cases():
    for layout in ("shaft", "dogleg"):
        for physics in (32, 33):
            yield dict(case=f"motion-{layout}-{'motor' if physics==33 else 'r0'}", kind="motion",
                       identity=331001 if layout=="shaft" else 332001, layout=layout, physics=physics,
                       seed=1, supply="limited", days=90, archive=True)


def long_cases():
    for physics in (32,33):
        yield dict(case=f"motion-shaft-continued-730-p{physics}", kind="motion", identity=320001, layout="shaft",
                   physics=physics,seed=1,supply="continued",days=730,archive=False)


def cadence_cases():
    for c in motion_cases():
        if c["layout"]=="shaft":
            yield c | dict(case=c["case"]+"-shorter", identity=333001, short_clock=True, archive=True)


def dig_cases():
    for count in (15, 50, 100, 300):
        for seed in (1, 7):
            for mode in MODES:
                days90h = count in (50, 300) and mode in ("r0", "full")
                yield dict(case=f"dig-{count:03}-s{seed}-{mode}", kind="dig", identity=340000+count*10+seed,
                           seed=seed, initialized_workers=count, mode=mode,
                           hours=24,
                           archive=seed==1 and days90h, shield=False)
    for mode in ("r0", "full"):
        yield dict(case=f"dig-050-s1-shield-{mode}", kind="dig", identity=349501, seed=1, initialized_workers=50,
                   mode=mode, hours=24, archive=False, shield=True)


def dig_extended_cases():
    for case in dig_cases():
        if not case["shield"] and case["initialized_workers"] in (50,300) and case["mode"] in ("r0","full"):
            yield case | dict(case=case["case"]+"-90h", hours=90, archive=False)


class Witness:
    def __init__(self, writer):
        self.digest = sha256()
        self.writer = writer

    def update(self, data):
        self.digest.update(data)
        if self.writer:
            self.writer.write(data)


class MotionTraffic(Traffic):
    def __init__(self, queen, surface, geometry, end_ms):
        super().__init__(queen, surface)
        self.chamber = geometry["voids"][0]
        self.scale = geometry["quantum_m"]
        self.origin = geometry["origin_m"]
        self.last_day = end_ms-DAY
        self.extra = defaultdict(Counter)

    def zone(self, p):
        if p[1] >= self.surface:
            return "surface"
        q = [(v-origin)/self.scale for v, origin in zip(p,self.origin,strict=True)]
        if all(self.chamber[i] <= q[i] < self.chamber[i+3] for i in range(3)):
            return "founding_chamber"
        return "other_underground"

    def commit(self, fact):
        actor = fact.actor
        was = self.position.get(actor)
        previous = self.workers.get(actor)
        timed_before = previous["move_ms"] if previous else 0
        super().commit(fact)
        if fact.kind!=4 or fact.outcome or not previous or fact.position==was:
            return
        data = self.extra[actor]
        elapsed = previous["move_ms"]-timed_before
        if fact.aux:
            duration, turning = fact.aux>>32, fact.aux & 0xffffffff
            if duration != elapsed:
                raise ValueError("Native motion time disagrees with actual paid work")
            data["turns"] += bool(turning)
            data["turn_ms"] += turning
            elapsed -= turning
        data["translation_ms"] += elapsed
        old, new = self.zone(was), self.zone(fact.position)
        if old!=new:
            data[f"{old}_to_{new}"] += 1
        if fact.time>=self.last_day:
            data["last_day_moves"] += 1
            data["last_day_distance_m"] += dist(was,fact.position)
            data["last_day_translation_ms"] += min(elapsed,fact.time-self.last_day)


def parameter_record(case):
    if case["kind"]=="motion":
        return dict(arm=f"r0r1-motion-{case['layout']}-{case['supply']}", layout=case["layout"], source=case["supply"],
                    population="borisovka", care_enabled=True, externally_seeded_workers=0,
                    parameters=dict(maternal_lipid=5500, worker_check_ms=(HOUR//4 if case.get("short_clock") else 6*HOUR),
                                    reserve_days=120 if case["supply"]=="limited" else 730))
    return dict(arm="r0r1-dig-shielded" if case["shield"] else "r0r1-dig",
                layout="compact-shaft", source="no-external-food", population="seeded Lasius niger fixture",
                care_enabled=False, externally_seeded_workers=case["initialized_workers"],
                parameters=dict(work_ms=1800000, decision_ms=60000, adult_energy_nj=1500000000,
                                adult_body_water_ug=1600, scoring=case["mode"]))


def census(frame):
    ants = [a for a in frame["ants"].values() if a["stage"]==3 and a["caste"]==0]
    points = Counter(a["position_m"] for a in ants)
    body = frame["geometry"]["body_half_q"]
    loaded = frame["geometry"]["loaded_half_q"]
    q = frame["geometry"]["quantum_m"]
    width = [(loaded if any(a["carried_ug"]) else body)*q for a in ants]
    overlaps = sum(all(abs(x-y)<width[i]+width[j]-1e-12 for x,y in zip(ants[i]["position_m"],ants[j]["position_m"]))
                   for i in range(len(ants)) for j in range(i))
    return dict(living_workers=len(ants), exact_worker_pairs=sum(n*(n-1)//2 for n in points.values()),
                worker_envelope_pairs_without_soil_load=overlaps)


def shape(frame):
    geometry = frame["geometry"]
    depot = next(iter(frame["colonies"].values()))["position_m"]
    x,y,z = [round((v-o)/geometry["quantum_m"]) for v,o in zip(depot,geometry["origin_m"],strict=True)]
    return floor_shape(geometry, frame["edits"], y, (x-64,z-64,x+64,z+64), (x,z), frame["ants"].values())


def write_archive(data, directory, destination, facts, frames, case):
    entries = {name:dict(sha256=sha256(value).hexdigest(),bytes=len(value)) for name,value in frames.items()}
    entries["facts.bin"] = dict(sha256=facts.digest.hexdigest(),bytes=(directory/"facts.bin").stat().st_size)
    signed = dict(status="COMPLETE", artifacts=entries, identity=data["identity"])
    with ZipFile(destination, "x", ZIP_DEFLATED, compresslevel=4) as f:
        for name, value in frames.items():
            f.writestr(name,value)
        f.write(directory/"facts.bin","facts.bin")
        f.writestr("receipt.json",json_bytes(signed))
    return dict(archive=destination.name, sha256=file_hash(destination), case=case["case"])


def save_roundtrip(core, directory, frame, raw):
    token = "b" * 32
    before = perf_counter()
    core.call("SAVE "+token)
    save_ms = (perf_counter()-before)*1000
    size = (directory/(token+".sqlite")).stat().st_size
    before = perf_counter()
    restored = core.call("LOAD "+token+" "+frame["world"])
    restore_ms = (perf_counter()-before)*1000
    if restored != raw:
        raise ValueError("SQLite round trip changed the committed frame")
    core.call("CHECK_LEDGERS")
    return dict(save_ms=save_ms,restore_ms=restore_ms,bytes=size,time_ms=frame["time_ms"],
                frame_sha256=sha256(raw).hexdigest())


def run(case, binary, output, identity, *, durable=False, quick=False, skip_archive=False):
    start = perf_counter()
    digging = case["kind"]=="dig"
    if digging:
        command = (f"NEW_R1_DIG {case['identity']} {case['seed']} {case['initialized_workers']} "
                   f"{MODES.index(case['mode'])} {int(case['shield'])}")
        cut_step = 6*HOUR
        end = case["hours"]*HOUR
    else:
        command = f"NEW_R0_ASSAY {case['identity']} {case['seed']} {case['physics']} {case['supply']} {case['layout']}"
        if case.get("short_clock"):
            command += f" {HOUR//4} {HOUR}"
        cut_step = DAY
        end = case["days"]*DAY
    if quick:
        end=min(end,cut_step)
    archive=case["archive"] and not quick and not skip_archive
    receipt = dict(case=case,command=command,end_ms=end,advance_ms=0,identity=identity)
    rows, deaths, cuts = [], [], []
    temp_dir = output/"temporary"
    temp_dir.mkdir(exist_ok=True)
    with (TemporaryDirectory(dir=temp_dir) as temp,
          closing(NativeCore(binary, temp)) as core):
        work = Path(temp)
        raw = core.call(command)
        frame = checkpoint(raw)
        initial = core.call("INITIAL") if archive else None
        if digging:
            movements = Counter()
            positions = {}
            traffic = None
        else:
            queen = next(key for key,row in frame["ants"].items() if row["caste"]==1)
            traffic = MotionTraffic(queen,frame["surface"]["origin_m"][1],frame["geometry"],end)
        cursor=0
        last_valid=0
        save_requested = durable or digging and case["seed"]==1 and case["mode"]=="full" and not case["shield"]
        save_at = (end//(2*cut_step))*cut_step
        with ((work/"facts.bin").open("xb") if archive else TemporaryDirectory(dir=work)) as store:
            of = Witness(store if archive else None)
            for at in range(0,end+1,cut_step):
                try:
                    if at:
                        t = perf_counter()
                        if digging:
                            for when in range(at-cut_step+HOUR//4,at,HOUR//4):
                                core.call(f"ADVANCE_STEP {when}")
                        raw = core.call(f"ADVANCE {at}")
                        receipt["advance_ms"]+=(perf_counter()-t)*1000
                        frame=checkpoint(raw)
                    for e in journal(core,cursor,frame["cursor"],of):
                        if traffic:
                            traffic.commit(e)
                        elif e.kind in (2,4) and e.outcome==0:
                            if e.kind==4:
                                movements["distance_m"]+=dist(positions[e.actor],e.position)
                                movements["moves"]+=1
                            positions[e.actor]=e.position
                        elif digging and e.kind in (6,23,24,26):
                            movements[KINDS[e.kind]]+=1
                    cursor=frame["cursor"]
                    last_valid=at
                    row = census(frame)
                    if digging:
                        row |= shape(frame) | dict(soil=frame["soil"], activity=dict(movements))
                    else:
                        row |= traffic.cut(core,frame)
                        deaths.extend(traffic.death_rows)
                        traffic.death_rows.clear()
                    rows.append(dict(time_ms=at,facts=cursor,**{k:v for k,v in row.items() if k!="facts"}))
                    core.call("CHECK_LEDGERS")
                    if digging and at:
                        print(case["case"], f"{at // HOUR} h", cursor, flush=True)
                    if save_requested and at and at==save_at:
                        receipt["sqlite"]=save_roundtrip(core,work,frame,raw)
                    if at in (365*DAY,450*DAY,730*DAY) or at==end:
                        cuts.append(dict(time_ms=at,cursor=cursor,frame_sha256=sha256(raw).hexdigest(),
                                         canonical_sha256=of.digest.hexdigest()))
                except (ValueError, RuntimeError) as error:
                    receipt["error"] = str(error)
                    break
            if archive:
                store.flush()
            receipt |= dict(cuts=cuts,last_valid_ms=last_valid,last_cursor=cursor,elapsed_s=perf_counter()-start,
                            frame_bytes=len(raw),canonical_sha256=of.digest.hexdigest())
            current,peak,hot = map(int,core.call("MEMORY").split())
            receipt["memory"] = dict(current_bytes=current,peak_bytes=peak,resident_history_bytes=hot)
            if traffic:
                people = [dict(row,**traffic.extra[row["ant"]]) for row in traffic.individual_results(last_valid)]
            else:
                people = []
            if archive and "error" not in receipt:
                outputs = dict(zip(PUBLISHED[:2],(initial,raw),strict=True))
                outputs["case.json"]=json_bytes(parameter_record(case))
                manifest=write_archive(receipt,work,output/(case["case"]+".zip"),of,outputs,case)
            else:
                manifest=None
        prefix = dict(receipt=receipt,census=rows,individuals=people,deaths=deaths,geometry_edits=frame["edits"])
        with gzip.open(output/(case["case"]+".json.gz"),"wb",compresslevel=4) as f:
            f.write(json_bytes(prefix))
        print(case["case"], receipt.get("error","COMPLETE"),last_valid,cursor,flush=True)
        return receipt,manifest


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("output",type=Path)
    p.add_argument("--core",type=Path,default=core_path())
    p.add_argument("--kind",choices=("motion","dig","dig90","long","cadence"),required=True)
    p.add_argument("--case",action="append",default=[])
    p.add_argument("--durable",action="store_true")
    p.add_argument("--quick",action="store_true")
    p.add_argument("--skip-archive",action="store_true")
    args=p.parse_args()
    dest=args.output.resolve()
    dest.mkdir(parents=True,exist_ok=False)
    binary=args.core.resolve(strict=True)
    cases=list({"motion":motion_cases,"dig":dig_cases,"dig90":dig_extended_cases,
                "long":long_cases,"cadence":cadence_cases}[args.kind]())
    available={r["case"] for r in cases}
    if set(args.case)-available:
        p.error("Unknown case")
    cases=[r for r in cases if not args.case or r["case"] in args.case]

    def git(*command):
        return check_output(["git",*command],text=True).strip()

    identity=dict(source=git("rev-parse","HEAD"),cpp_tree=git("rev-parse","HEAD:cpp"),
                  dirty=git("status","--porcelain","--","cpp","tools/run_r0_r1.py","op0"),
                  binary_sha256=file_hash(binary),protocol_sha256=file_hash(Path("research/r0_r1/PROTOCOL.md")),
                  quick=args.quick,cases=[r["case"] for r in cases])
    (dest/"run.json").write_bytes(json_bytes(identity))
    failed=False
    with ((dest/"runs.jsonl").open("x",encoding="utf-8",newline="\n") as runs,
          (dest/"archives.jsonl").open("x",encoding="utf-8",newline="\n") as archives):
        for case in cases:
            receipt,manifest=run(case,binary,dest,identity,durable=args.durable,quick=args.quick,skip_archive=args.skip_archive)
            print(json.dumps(receipt),file=runs,flush=True)
            failed |= "error" in receipt
            if manifest:
                print(json.dumps(manifest),file=archives,flush=True)
    return int(failed)


if __name__=="__main__":
    raise SystemExit(main())
