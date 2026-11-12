"""Cause-specific cohort endpoints reconstructed in EventId order."""

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from random import Random
from statistics import mean

from read_s6_4_rm02_sidecar import CASTES, DEATHS, STAGES, require
from s6_4_wp4_budget import ZERO, components, death_code


DAY = 86_400_000
LANDMARK = 21 * DAY
OUTCOMES = ("transition", "death", "right_censored")
STOCKS = ("energy_nj", "hydration_ug", "tissue_ug", "crop_carbs_ug", "crop_protein_ug", "crop_water_ug")


def run_cohort(run, budget, states, all_facts, tables):
    """The budget has already independently replayed births, deaths and uptake."""
    outcomes = []
    exposure = defaultdict(lambda: [0, Counter()])
    gifts = defaultdict(list)
    for f, _ in budget.gifts:
        gifts[f.payload].append(f)
    for actor, q in sorted(budget.individuals.items()):
        snaps = states[actor]
        cursors = [v["cursor"] for v in snaps]
        spec = q.spec
        caste = CASTES[snaps[0]["caste"]]
        entries = (q.entry, *q.transitions)
        for i, origin in enumerate(entries):
            terminal = entries[i + 1] if i + 1 < len(entries) else q.death
            status = "right_censored" if terminal is None else "death" if terminal.kind == "AntDied" else "transition"
            stop = run.horizon if terminal is None else terminal.time
            cap = len(all_facts) + 1 if terminal is None else terminal.event
            require(stop >= origin.time and cap > origin.event, "cohort interval reverses order")
            hits = [f for f in budget.uptake[actor] if origin.event < f.event < cap and any(f.mass)]
            received = [f for f in gifts[actor] if origin.event < f.event < cap]
            applied = tuple(sum(f.mass[j] for f in hits) for j in range(len(ZERO)))
            transferred = tuple(sum(f.mass[j] for f in received) for j in range(len(ZERO)))
            pre_index = bisect_left(cursors, cap) - 1
            last = snaps[pre_index] if pre_index >= 0 and snaps[pre_index]["stage"] == origin.stage else None
            if status == "death":
                post = snaps[bisect_left(cursors, cap)]
                require(post["stage"] == 4 and post["death_cause"] == death_code(terminal), "wrong terminal cut")
            else:
                post = None
            if origin.stage == 1 and last:
                observed_larval_status = "BELOW_FIXTURE_PROTEIN_TARGET" if last["tissue_ug"] < spec["larva_target_ug"] \
                    else "AT_OR_ABOVE_FIXTURE_PROTEIN_TARGET"
            else:
                observed_larval_status = "UNOBSERVED" if origin.stage == 1 else "NOT_APPLICABLE"
            record = dict(entity=actor, mother=spec["mother"], caste=caste, stage=STAGES[origin.stage],
                          entry_ms=origin.time, entry_event=origin.event, exit_ms=stop,
                          endpoint_event=terminal.event if terminal else "", duration_ms=stop - origin.time,
                          endpoint=status, death_cause=DEATHS[death_code(terminal)] if status == "death" else "",
                          time_origin="SINCE_REGISTRATION" if origin.kind == "AntSeeded" else "SINCE_COMMITTED_STAGE_ENTRY",
                          natural_death_risk="UNOBSERVED", first_uptake_event=hits[0].event if hits else "",
                          first_uptake_ms=hits[0].time if hits else "", positive_uptake_pulses=len(hits),
                          first_received_event=received[0].event if received else "", received_gifts=len(received),
                          **components(transferred, "received"), **components(applied, "uptake"),
                          larval_protein_target_ug=spec["larva_target_ug"] if origin.stage == 1 else "",
                          larval_status_at_last_cut=observed_larval_status,
                          progress_ms=last["progress_ms"] if last else "", pre_cut_ms=last["sim_ms"] if last else "",
                          pre_cut_event=last["cursor"] if last else "", post_death_cut_ms=post["sim_ms"] if post else "",
                          **{f"pre_{k}": last[k] if last else "" for k in STOCKS},
                          **{f"post_death_{k}": post[k] if post else "" for k in STOCKS})
            tables.add("cohort_intervals", run, **record)
            outcomes.append(record)
            first = hits[0].time if hits else stop
            before = exposure[caste, STAGES[origin.stage], "before_positive_uptake"]
            before[0] += first - origin.time
            before[1]["segments"] += 1
            current = before
            if hits:
                current = exposure[caste, STAGES[origin.stage], "after_positive_uptake"]
                current[0] += stop - first
                current[1]["segments"] += 1
            current[1][status] += 1
    for (caste, stage, window), (time, totals) in sorted(exposure.items()):
        tables.add("uptake_risk_time", run, caste=caste, stage=stage, window=window, person_ms=time,
                   segments=totals["segments"], **{label: totals[label] for label in OUTCOMES})
    return outcomes


def incidence(records):
    """Discrete Aalen-Johansen, with tied observed outcomes preceding horizon censoring."""
    endpoints = defaultdict(Counter)
    for item in records:
        endpoints[item["duration_ms"]][item["endpoint"]] += 1
    risk = len(records)
    survival, death, transition = 1.0, 0.0, 0.0
    for at, counts in sorted(endpoints.items()):
        death += survival * counts["death"] / risk
        transition += survival * counts["transition"] / risk
        survival *= 1 - (counts["transition"] + counts["death"]) / risk
        yield at, risk, death, transition, survival
        risk -= sum(counts.values())


def summarize(run, outcomes, states, facts, config, tables):
    bins = defaultdict(list)
    for item in outcomes:
        bins[item["caste"], item["stage"], item["time_origin"]].append(item)
    for (caste, stage, origin), records in sorted(bins.items()):
        points = list(incidence(records))
        for at in sorted({t * DAY for t in (1, 2, 4, 7, 14, 21, 90, 180) if t * DAY <= run.horizon}):
            used = bisect_right(points, at, key=lambda p: p[0])
            last = points[used - 1] if used else (0, len(records), 0, 0, 1)
            # Censoring can exhaust follow-up earlier than the nominal world horizon.
            supported = points[-1][0] >= at or all(item["endpoint"] != "right_censored" for item in records)
            tables.add("cohort_incidence", run, caste=caste, stage=stage, time_origin=origin, followup_ms=at,
                       entered=len(records), risk_at_ms=sum(item["duration_ms"] >= at for item in records),
                       observable=int(supported), death_cif=round(last[2], 8) if supported else "",
                       transition_cif=round(last[3], 8) if supported else "",
                       in_stage_probability=round(last[4], 8) if supported else "")
    by_kind = Counter(f.kind for f in facts)
    ages = [x for x in outcomes if x["caste"] == "worker" and x["stage"] == "adult" and x["entry_ms"] == 0]
    attained = sum(r["duration_ms"] >= LANDMARK and (r["endpoint"] != "death" or r["duration_ms"] > LANDMARK) for r in ages)
    queen = next((r for r in outcomes if r["caste"] == "queen"), None)
    deaths = Counter(r["death_cause"] for r in outcomes if r["endpoint"] == "death")
    cutoff = LANDMARK if run.horizon >= LANDMARK else run.horizon
    birth_ids = {f.actor for f in facts if f.kind == "AntBorn" and f.time <= cutoff}
    first_worker = next((f for f in facts if f.kind == "StageChanged" and f.stage == 3 and f.actor in birth_ids), None)
    care = Counter((f.care[0], f.care[1]) for f in facts if f.kind == "BiologicalObservation"
                   and f.actor == int(config["queen"]) and f.time <= cutoff)
    obs = dict(initial_workers=len(ages), survival_workers_day21=attained if run.horizon >= LANDMARK else "",
               queen_at_day21=int(queen["endpoint"] != "death" or queen["exit_ms"] > LANDMARK)
               if queen and run.horizon >= LANDMARK else "", queen_endpoint=queen["endpoint"] if queen else "",
               queen_terminal_ms=queen["exit_ms"] if queen else "", birth_by_cutoff=len(birth_ids),
               deaths_by_cutoff=sum(f.kind == "AntDied" and f.time <= cutoff for f in facts),
               worker_emergence_ms=first_worker.time if first_worker else "",
               queen_actual_care_completed=sum(care[3, act] for act in (3, 4, 5, 6, 7, 16, 17)),
               queen_care_started=sum(care[2, act] for act in (3, 4, 5, 6, 7, 16, 17)),
               queen_care_interrupted=sum(care[4, act] for act in (3, 4, 5, 6, 7, 16, 17)))
    tables.add("cohort_runs", run, family=config["family"], arm=config["arm"], seed=config["seed"], horizon_ms=run.horizon,
               cutoff_ms=cutoff, identities=len(states), interval_count=len(outcomes), deaths=sum(deaths.values()),
               **{name: deaths[name] for name in DEATHS[1:]}, positive_gifts=by_kind["NutritionTransferred"],
               observed_rejections=by_kind["ActionRejected"], **obs)
    return obs


def paired(values):
    require(len(values) == 6, "paired contrast is missing a frozen seed")
    rng = Random(640505)
    samples = sorted(mean(rng.choices(values, k=6)) for _ in range(4096))
    return round(mean(values), 8), round(samples[102], 8), round(samples[3993], 8)
