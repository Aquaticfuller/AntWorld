"""Replay F1 physiological compartments independently from archived facts and daily cuts."""

import argparse
from collections import Counter
import csv
from dataclasses import dataclass, field
from hashlib import sha256
from itertools import groupby
import json
from pathlib import Path
from struct import unpack_from
import zipfile

from analyze_s6_4_wp6b import (BIRTH, CARGO, COLLECTED, DELIVERED, DIED, F_CONVERT, F_EGG,
                              F_RATION, F_SEED, GIFT, MOVED, NEST, OBSERVATION, RECYCLED, STAGE, UPTAKE, check, facts, rows)
from diagnose_s6_4_wp6b_r1 import sheet
from run_s6_4_wp6b import sha, write_json
from wp6a_budget_screen import DAY_MS


SEED_FOOD, REJECTED, START_FORAGE, DECISION, BEHAVIOR, SOIL = 3, 6, 10, 11, 17, 23
PLACE_FOOD, AUTONOMY_DECISION, RELEASE = 28, 31, 37
ADULT, DEAD, ACTIVE = 3, 4, {2, 3, 4}
MEASURED = ("body_nj", "owned_lipid_ug", "spent_lipid_ug", "body_water_ug", "crop_water_ug", "crop_protein_ug",
            "tissue_protein_ug", "crop_carb_ug", "carried_water_ug", "lost_water_ug", "dissipated_nj")


def positions(raw):
    offset = 0
    while offset < len(raw):
        size, = unpack_from("<I", raw, offset)
        yield unpack_from("<Qddd", raw, offset+86)
        offset += size+4


@dataclass
class Individual:
    id: int
    born: int
    stage: int
    queen: bool = False
    mother: int = 0
    at: int = 0
    energy: int = 0
    water: int = 0
    lipid: int = 0
    spent: int = 0
    tissue: int = 0
    crop: list = field(default_factory=lambda: [0]*4)
    cargo_water: int = 0
    spent_water: int = 0
    used_energy: int = 0
    carry_e: int = 0
    carry_w: int = 0
    behavior: int = 0
    energy_exact: bool = True
    enter: dict = field(default_factory=dict)
    marks: dict = field(default_factory=dict)
    counters: Counter = field(default_factory=Counter)
    adult_program_ms: Counter = field(default_factory=Counter)

    def settle(self, time, p):
        if self.stage == DEAD or self.at == time:
            return
        dt = time-self.at
        check(dt >= 0, "individual time moved backwards")
        if self.queen:
            er = p["queen_basal"] + (DAY_MS*p["queen_active"] if self.behavior in ACTIVE else 0)
            wr = p["queen_water_loss"]
        elif self.stage < ADULT:
            stage = ("egg", "larva", "pupa")[self.stage]
            er, wr = p[stage+"_basal"], p[stage+"_water_loss"]
        else:
            er, wr = DAY_MS*(1+int(self.behavior in ACTIVE)), 24
            self.adult_program_ms[self.behavior] += dt
        used, self.carry_e = divmod(er*dt+self.carry_e, DAY_MS)
        lost, self.carry_w = divmod(wr*dt+self.carry_w, DAY_MS)
        used, lost = min(used,self.energy), min(lost,self.water)
        self.energy -= used
        self.water -= lost
        self.used_energy += used
        self.spent_water += lost
        self.at = time

    def snapshot(self):
        return (self.energy if self.energy_exact else None,self.lipid,self.spent,self.water,self.crop[2],self.crop[1],
                self.tissue,self.crop[0],self.cargo_water,self.spent_water,self.used_energy if self.energy_exact else None)

    def absorb(self, mass):
        for i, value in enumerate(mass):
            self.crop[i] -= value
        self.energy += mass[0]*1_000_000
        self.water += mass[2]
        self.tissue += mass[1]

    def add_crop(self, mass, sign=1):
        for i, value in enumerate(mass):
            self.crop[i] += sign*value


def cut_check(people, data, p):
    key_map = ("energy_nj","lipid_ug","spent_lipid_ug","hydration_ug","crop_w","crop_p","tissue_protein_ug","crop_c",
               "carried_w","lost_water_ug","dissipated_nj")
    for row in data:
        if row["enrolled"] != "1":
            continue
        ant = people[int(row["id"])]
        ant.settle(int(row["time_ms"]), p)
        values = ant.snapshot()
        actual = tuple(int(row[k]) for k in key_map)
        check(all(a is None or a==b for a,b in zip(values,actual,strict=True)) and ant.stage == int(row["stage"]) and
              ant.carry_e == int(row["energy_carry"]) and ant.carry_w == int(row["water_carry"]),
              f"individual {ant.id} cut {row['time_ms']} differs: {values} versus {actual}")
        if not ant.energy_exact:
            ant.energy, ant.used_energy = actual[0], actual[-1]
            ant.energy_exact = True


def mark(ant, key, time, event):
    ant.marks.setdefault(key, (time,event))


def read_case(case, summary, raw, cuts, write):
    p, name, queen = case["parameters"], case["case"], int(summary["queen"])
    people, sources = {}, {}
    food_colony = 0
    cut_groups = iter(groupby(rows(cuts), lambda row: (int(row["cursor"]),int(row["time_ms"]))))
    cut, group = next(cut_groups, (None,None))
    ncuts = 0

    def write_point(ant, point, fact, time, cause="", mass=(0,0,0,0), lipid=0, source=0):
        write["points"](dict(case=name, ant=ant.id, mother=ant.mother, point=point, stage=ant.stage, time_ms=time,
                             event=fact, source=source, cause=cause, dose_c_ug=mass[0],dose_p_ug=mass[1],dose_w_ug=mass[2],
                             dose_lipid_ug=lipid, **dict(zip(MEASURED,ant.snapshot(),strict=True)),
                             env_water_ug=sum(sources.values()), nest_water_ug=food_colony))

    for entry, (resource,x,y,z) in zip(facts(raw),positions(raw),strict=True):
        event,time,source,kind,actor,payload,value,stage,outcome,mass,obs = entry
        while cut is not None and cut[0] < event:
            cut_check(people,group,p)
            ncuts += 1
            cut,group = next(cut_groups,(None,None))
        if kind == F_SEED:
            people[queen] = Individual(queen,0,ADULT,True,water=mass[2],lipid=payload)
        elif kind == BIRTH:
            check(payload==queen and actor not in people, "wrong birth identity")
            people[actor] = Individual(actor,time,0,mother=queen,at=time,water=mass[2],lipid=p["egg_lipid"],tissue=mass[1])
            people[actor].enter[0] = (time,event)
            write_point(people[actor],"BIRTH_PACKET",event,time,mass=mass,lipid=p["egg_lipid"],source=source)
        elif kind in (SEED_FOOD,PLACE_FOOD,RELEASE,COLLECTED):
            sources[resource] = sources.get(resource,0) + (-mass[2] if kind==COLLECTED else mass[2])
            check(sources[resource]>=0,"collected water without a recorded resource")
        if kind == DELIVERED:
            food_colony += mass[2]
        elif kind == NEST:
            food_colony -= mass[2]
        ant = people.get(actor)
        if ant is not None and kind in (F_CONVERT,F_EGG,F_RATION,GIFT,UPTAKE,STAGE,DIED,BEHAVIOR,START_FORAGE,SOIL,
                                         COLLECTED,DELIVERED,NEST,CARGO,RECYCLED):
            ant.settle(time,p)
            if kind == F_CONVERT:
                ant.lipid -= payload
                ant.spent += payload
                ant.energy += value
                check(ant.lipid>=0 and value==payload*p["lipid_yield"],"unfunded lipid conversion")
                if not ant.queen:
                    write_point(ant,"CONVERTED",event,time,lipid=payload,source=source)
                    if "meal" in ant.marks and ant.stage==1:
                        mark(ant,"conversion_after_meal",time,event)
            elif kind == F_EGG:
                ant.lipid -= value
                ant.water -= p["egg_water"]
                ant.energy -= p["lay_overhead"]
                ant.used_energy += p["lay_overhead"]
            elif kind == F_RATION:
                ant.lipid -= value
                ant.water -= mass[2]
                recipient=people[payload]
                recipient.settle(time,p)
                recipient.lipid += value
                recipient.add_crop(mass)
                mark(recipient,"meal",time,event)
                recipient.counters.update(meals=1, maternal_lipid_ug=value, maternal_p_ug=mass[1], maternal_w_ug=mass[2])
                write_point(recipient,"PAID_MATERNAL_RATION",event,time,mass=mass,lipid=value,source=source)
            elif kind == UPTAKE:
                ant.absorb(mass)
                if any(mass) and not ant.queen:
                    write_point(ant,"POSITIVE_UPTAKE",event,time,mass=mass,source=source)
                    if ant.stage==1:
                        if "meal" in ant.marks:
                            mark(ant,"uptake_after_meal",time,event)
                        if mass[1] and ant.tissue>=p["larval_tissue_target"]:
                            mark(ant,"tissue_met",time,event)
                    if ant.stage==ADULT:
                        ant.counters.update(adult_water_absorbed_ug=mass[2], adult_carbs_absorbed_ug=mass[0])
            elif kind == STAGE:
                ant.stage=stage
                ant.enter[stage]=(time,event)
                point=("", "HATCH", "PUPATION", "ECLOSION")[stage]
                write_point(ant,point,event,time,source=source)
                ant.marks[point.lower()]=(time,event)
            elif kind == DIED:
                write_point(ant,"DEATH",event,time,cause=payload,source=source)
                ant.counters["death_cause"]=payload
                ant.stage=DEAD
                mark(ant,"death",time,event)
            elif kind == BEHAVIOR:
                ant.behavior=payload
            elif kind == START_FORAGE:
                ant.behavior=3
            elif kind == SOIL:
                # Soil parcel quantities are absent from this compact fact. Reanchor
                # the affected energy components at the next exact read-only cut.
                ant.energy_exact=False
                ant.counters["dig_energy_unobserved"]+=1
            elif kind == COLLECTED:
                ant.cargo_water+=mass[2]
                ant.counters["collected_water_ug"]+=mass[2]
            elif kind in (DELIVERED,CARGO):
                ant.cargo_water-=mass[2]
                ant.counters["delivered_water_ug" if kind==DELIVERED else "cargo_water_ug"]+=mass[2]
                if kind==CARGO:
                    ant.add_crop(mass)
            elif kind == NEST:
                ant.add_crop(mass)
                ant.counters["nest_water_in_ug"]+=mass[2]
            else:
                ant.add_crop(mass,-1)
        if kind == GIFT and payload in people:
            recipient=people[payload]
            recipient.settle(time,p)
            recipient.add_crop(mass)
            if recipient.stage==ADULT:
                recipient.counters["gift_water_in_ug"]+=mass[2]
            elif recipient.stage==1 and any(mass):
                mark(recipient,"worker_meal",time,event)
                write_point(recipient,"PAID_WORKER_GIFT",event,time,mass=mass,source=source)
        if kind==OBSERVATION:
            phase,act,target,*_ = obs
            if actor==queen and phase==0 and target in people and people[target].stage==1:
                mark(people[target],"first_local_contact",time,event)
                people[target].counters["contact_opportunities"]+=1
            if ant is not None and not ant.queen and ant.stage==ADULT and phase==0:
                ant.counters["observed_care_contacts"]+=1
        if ant is not None and ant.stage==ADULT and not ant.queen:
            if kind==DECISION:
                ant.counters["forage_decisions"]+=1
            elif kind==AUTONOMY_DECISION:
                ant.counters["autonomy_decisions"]+=1
            elif kind==MOVED:
                ant.counters["moves"]+=1
            elif kind==REJECTED:
                ant.counters["rejections"]+=1
            elif kind==GIFT:
                ant.counters["gift_water_out_ug"]+=mass[2]
        if kind==DIED and ant is not None and not ant.queen:
            ant.marks["death_water"]=(sum(sources.values()),food_colony)
            ant.marks["death_pos"] = (x,y,z)
    while cut is not None:
        check(cut[0]==int(summary["events"]),"terminal cut lacks event coverage")
        cut_check(people,group,p)
        ncuts+=1
        cut,group=next(cut_groups,(None,None))
    output=Counter(cuts=ncuts, offspring=len(people)-1)
    for ant in people.values():
        if ant.queen:
            continue
        outcome="DEATH" if ant.stage==DEAD else "RIGHT_CENSORED"
        if ant.stage!=DEAD:
            write_point(ant,outcome,"",case["horizon_ms"])
        output["hatched"]+=1 in ant.enter
        output["eclosed"]+=3 in ant.enter
        output["hatched_no_maternal_meal"]+=1 in ant.enter and "meal" not in ant.marks
        output["adult_dehydration"]+=3 in ant.enter and ant.counters["death_cause"]==2
        output["adult_water_absorbed_ug"]+=ant.counters["adult_water_absorbed_ug"]
        row=dict(case=name,ant=ant.id,mother=ant.mother,outcome=outcome,terminal_stage=ant.stage,death_cause=ant.counters["death_cause"],
                 terminal_ms=ant.marks.get("death",(case["horizon_ms"],None))[0],terminal_event=ant.marks.get("death",(None,None))[1],
                 **dict(zip(MEASURED,ant.snapshot(),strict=True)))
        for key in ("hatch","pupation","eclosion","first_local_contact","meal","worker_meal","conversion_after_meal","uptake_after_meal","tissue_met"):
            row[key+"_ms"],row[key+"_event"]=ant.marks.get(key,(None,None))
        row.update(birth_ms=ant.born,birth_event=ant.enter[0][1],local_contacts=ant.counters["contact_opportunities"],
                   **{key:ant.counters[key] for key in ("meals","maternal_lipid_ug","maternal_p_ug","maternal_w_ug","adult_water_absorbed_ug",
                     "adult_carbs_absorbed_ug","collected_water_ug","delivered_water_ug","cargo_water_ug","nest_water_in_ug","gift_water_in_ug",
                     "gift_water_out_ug","forage_decisions","autonomy_decisions","moves","rejections","observed_care_contacts","dig_energy_unobserved")},
                   **{f"adult_program_{program}_ms":ant.adult_program_ms[program] for program in range(5)})
        row["death_env_water_ug"],row["death_nest_water_ug"]=ant.marks.get("death_water",(None,None))
        row["death_x_m"],row["death_y_m"],row["death_z_m"]=ant.marks.get("death_pos",(None,None,None))
        write["individuals"](row)
    return dict(case=name,population=case["population"],group=case["group"],care=int(case["care_enabled"]),**output)


def main():
    from contextlib import ExitStack

    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    parser.add_argument("out",type=Path)
    parser.add_argument("--case",action="append",default=[])
    args=parser.parse_args()
    index=json.loads((args.archive/"completed.json").read_text(encoding="utf-8"))
    args.out.mkdir(parents=True)
    fields=dict(points="case ant mother point stage time_ms event source cause dose_c_ug dose_p_ug dose_w_ug dose_lipid_ug " +
                       " ".join(MEASURED)+" env_water_ug nest_water_ug",
                individuals="case ant mother outcome terminal_stage death_cause terminal_ms terminal_event "+" ".join(MEASURED)+" "+
                    " ".join(f"{k}_{v}" for k in ("hatch","pupation","eclosion","first_local_contact","meal","worker_meal","conversion_after_meal",
                        "uptake_after_meal","tissue_met") for v in ("ms","event"))+
                    " birth_ms birth_event local_contacts meals maternal_lipid_ug maternal_p_ug maternal_w_ug adult_water_absorbed_ug adult_carbs_absorbed_ug collected_water_ug delivered_water_ug cargo_water_ug nest_water_in_ug gift_water_in_ug gift_water_out_ug forage_decisions autonomy_decisions moves rejections observed_care_contacts dig_energy_unobserved adult_program_0_ms adult_program_1_ms adult_program_2_ms adult_program_3_ms adult_program_4_ms death_env_water_ug death_nest_water_ug death_x_m death_y_m death_z_m")
    seen, complete, counts = set(),[],Counter()
    target=set(args.case) if args.case else set(index["statuses"])
    with ExitStack() as stack:
        write={key:stack.enter_context(sheet(args.out/f"{key}.csv.gz",columns)) for key,columns in fields.items()}
        for filename,digest in index["archives"].items():
            path=args.archive/filename
            check(sha(path)==digest, f"archive hash changed: {filename}")
            with zipfile.ZipFile(path) as archive:
                for member in archive.namelist():
                    name=member.split("/")[0]
                    if not member.endswith("/receipt.json") or name not in target:
                        continue
                    receipt=json.loads(archive.read(member))
                    check(name not in seen and receipt["status"]==index["statuses"][name],"invalid case receipt")
                    seen.add(name)
                    counts[receipt["status"]]+=1
                    if receipt["status"]!="COMPLETE":
                        continue
                    files={key:archive.read(f"{name}/{key}") for key in ("case.json","facts.bin","individuals.csv")}
                    check(all(sha256(data).hexdigest()==receipt["artifacts"][key]["sha256"] for key,data in files.items()),"member hash changed")
                    try:
                        complete.append(read_case(json.loads(files["case.json"]),receipt["summary"],files["facts.bin"],files["individuals.csv"],write))
                    except ValueError as error:
                        raise ValueError(f"{name}: {error}") from error
            print(f"{len(seen)}/{len(target)} checked {filename}",flush=True)
    check(seen==target,"case coverage differs")
    with (args.out/"cases.csv").open("x",encoding="utf-8",newline="") as stream:
        keys=list(dict.fromkeys(k for row in complete for k in row))
        writer=csv.DictWriter(stream,keys,lineterminator="\n")
        writer.writeheader()
        writer.writerows(complete)
    write_json(args.out/"receipt.json",dict(archive_index_sha256=sha(args.archive/"completed.json"), cases=len(seen),
               status_counts=dict(counts), outputs={p.name:sha(p) for p in sorted(args.out.iterdir())}))


if __name__=="__main__":
    main()
