# S6.3.2 correction proposals: review required

These proposals are frozen before new audit probes. None changes the Simulation Core in S6.3.2. Priorities express readiness risk, not authorization to implement. All cited references resolve in BIOLOGY_REFERENCES.md; the actual current rules are enumerated in BIOLOGY_EVIDENCE_MATRIX.md. Every uncalibrated value remains ENGINEERING_FIXTURE. A future change needs its own frozen controls, event observables, versioned semantic decision and independent review.

## P01 — Founding queen care and reversible worker influence (blocking)

**Evidence and defect.** B01 directly demonstrates Lasius niger queen care before workers, suppression after worker addition and recovery after removal, including older queens. B02 measures retrieval/manipulation, not a nutritional transfer rate. The current adult-Worker-only eligibility check prohibits all queen care. This contradicts a complete founding model; it is more than an uncertain numeric parameter.

**Smallest candidate.** Add a queen-specific local care program, distinct from worker foraging/excavation. Separate measured brood manipulation/grooming from funded feeding. Use remembered recent close worker encounters and local brood encounters as candidate inputs; do not count workers globally or switch irrevocably on the first birth. B01's contact manipulation constrains hypotheses but does not identify a molecular signal or calibrate a decay time. Founding reproductive status must be explicit rather than inferred from global colony size.

**Isolated validation.** Same queens with brood, worker addition/removal, sham handling, and barrier-separated workers; use B01's observation definitions and B02's retrieval conditions. Report care incidence/time and latency, not invented food transfer. Test reversibility, locality, no available caregiver, conservation, identity and save/replay. Fit neither suppression strength nor memory lifetime to queen survival. Missing measured time courses require new data extraction or explicit qualitative status.

## P02 — Caste/stage physiology, reserves and absorption clocks (blocking)

**Evidence and defect.** B04 reports mass-adjusted queen RMR, while B05 reports whole-individual respiration of sexual developmental stages. These are different estimands. A fivefold lower mass-adjusted queen rate does not mean fivefold less whole-queen energy. Current identical queen/worker capacities, homogeneous stage maintenance, unspecified usable reserves and 1 kJ/g carbohydrate yield are not calibrated. The 6-hour pulsed absorption used with microsecond/millisecond action ordering can cause death with usable crop carbohydrate present.

**Smallest candidate.** First specify gross chemical input, assimilated energy, oxidation products/losses, structural biomass and available body reserves with explicit units. Establish a mass/caste/stage parameterization only from compatible measurements. Replace pulsed absorption with an analytically integrated or bounded event-driven uptake process if a dedicated time-step convergence experiment confirms the current artifact. Preserve the ledger and rollback; do not multiply yield by gross combustion energy without specifying assimilation efficiency and additional energetic pools.

**Isolated validation.** Resting, postabsorptive animals of the measured age/mass/temperature; compare oxygen flux before converting to energy with a declared oxycaloric assumption. Matched input with 1/3/6-hour bookkeeping intervals must converge without changing total resources. Distinguish water access, crop stores, tissue and fat reserves. No maintenance or capacity value is selected to achieve 90-day survival.

## P03 — Reproductive allocation and brood feedback (blocking)

**Evidence and defect.** Retain the S6.3.1 maternal reserve guard; its two-day window is D, not a measured constant. B01's larvae suppress laying in founding queens but stimulate it in established queens. B03 shows diet-dependent founding output, not an empirically fixed egg cost. Current constant attempts, Worker-only offspring and direct crop-to-egg funding omit ovarian maturation, maternal reserves and stage-dependent brood feedback.

**Smallest candidate.** After P01/P02, model local maternal condition and ovarian/reproductive state; compare a graded allocation hypothesis against the existing reserve guard. A local brood-encounter signal may modulate propensity only with an explicit founding-state interpretation. Do not add a colony population target, global food estimate, lifespan floor or forced egg schedule. Alates/mating remain a separate scope decision.

**Isolated validation.** Founding and established queens with/without larvae under B01's worker-free five-day assay, plus B03 diet treatments. Measure egg production, maternal reserve changes and actual feeding. Freeze costs and reserve sensitivity before colony experiments; report tradeoffs and zero reproduction honestly. Egg-cost calibration remains pending direct biochemical data.

## P04 — Developmental physiology and temperature (blocking)

**Evidence and defect.** B06 measures roughly 35–71 days from egg to worker over its productive temperature range, population dependent. Current supplied-tissue clocks sum to seven days and contain no temperature input, instars or prepupal mapping. A complete temperature-response validation is currently impossible.

**Smallest candidate.** Introduce an explicit local temperature input and cumulative physiological development, with named egg, larval and prepupal/pupal endpoints. Separate nutritional growth from thermal progress; do not just multiply all times by one fitted factor. Fit population-specific responses only inside the measured range; outside it declare uncertainty. Thermal diapause requires an explicit hypothesis rather than extrapolated negative development rates. This is not authorization for a weather system.

**Isolated validation.** B06's constant-temperature, water-accessible, unfed founding chambers and daily observations. Match first egg/first worker and stage boundaries; preserve censoring at 17 C and nest-level replication. Extract published dispersion as reported, not an invented standard error. Cross-validate held-out temperatures/populations; compare counts and timing separately.

## P05 — Local provisioning, recipient signals and temporal contact (high)

**Evidence and defect.** SD-04 and SD-08 stay open. B08 measures highly heterogeneous temporal trophallaxis networks; it does not provide transferred mass, queen provisioning or a 16-contact sampling budget. Current exact neighbor-store inspection is a local proxy, not a measured sensory mechanism. Task holding, sparse sampled opportunities and delayed absorption can obstruct a resource-conserving supply chain.

**Smallest candidate.** Instrument contact opportunity -> eligible sampled donor -> recipient selection -> committed transfer -> absorption. Compare a bounded persistent encounter/need signal with the present instantaneous signal, without queen privilege or global deficit allocation. Recipient saturation and donor self-maintenance must remain physical. Evaluate post-intake contact timing independently of task duration. Avoid changing sampling and nutrient transfer simultaneously.

**Isolated validation.** Reproduce B08's queenless/broodless group size, deprivation and sugar access before adding queen/brood contrasts. Match event definition (>5 s contact), observation cadence and donor/receiver roles; report that the current instantaneous event cannot match this duration. Then use existing S6.3.1 ordinary32 and positive8 failures with matched seed/resource ledgers, contact yields and crop-to-body time. Scarcity tradeoffs need not maximize emergence.

## P06 — Actual activity, rest and individual task history (high)

**Evidence and defect.** B20 measures heterogeneous participation and reserve workers; B09 separates age from role. A worker assigned Nurse for six hours need not be moving or caring for six hours. Current fixed task weights and program labels cannot validate observed activity budgets, sleep or circadian rest (SD-07).

**Smallest candidate.** First separate program assignment from executed action duration and immobility. Only then compare local physiological demand, recent work and individual experience as task inputs. Do not introduce centralized quotas or force an empirical inactive fraction. Age-role associations alone do not establish a causal switch rule.

**Isolated validation.** Use B20 observation categories and sampling windows, including manipulations as separate conditions. Test identical food with different local brood demand, contact density and empty space. Compare per-individual distributions and transitions, not only population means. Sleep/circadian claims require additional direct Lasius evidence.

## P07 — Mortality beyond resource exhaustion (high; explicit readiness scope)

B10 shows diet effects on worker survival; B19 shows cohort-specific longevity under supplied conditions. Current deaths only from depleted energy/water cannot reproduce those endpoints. A later stochastic hazard requires measured age/cohort/environment inputs and independent survival validation; do not assign a fixed lifespan or infer a universal hazard from a mean. Brood, queen, worker, and sexual cohorts must not share fitted longevity. Infection and multispecies are outside this proposal.

## P08 — Sensing, memory and context-dependent trails (high scientific debt)

B14 constrains junction geometry; B15/B17 constrain trajectory following; B16 shows context and replication limits for learning; B18 shows crowding-dependent deposition. Current four-neighbor scalar field, destination deposition, short average uninterrupted following, perfect one-visit memory and simplified food perception remain approximations. Preserve S2.2 negative recruitment results. First add matched observation geometry and identifiable chemical-dose units; then compare local orientation/turn persistence and conditional deposition, one mechanism at a time. No global food coordinates, directional chemical arrows, inflated trail weights or selected successful seeds. Full long-distance social recruitment remains unvalidated.

## P09 — Functional nest feedback and construction material (high scientific debt)

B12 tests surface construction on a shallow substrate that prevents tunnels; B13 measures underground nests and temperature-related excavation/refilling. These are not interchangeable validation targets. Current cuboid edits, six-axis travel, local contact-density vacancy proxy and noncolliding deposited parcels do not implement either full morphology. First define parcel collision/material geometry and match measured substrate, ant clearance and observation scale. Evaluate local crowding/brood microclimate hypotheses separately; no prescribed nest shape or global desired volume. SD-06 and TD-04 stay open.

## P10 — Measurement contract before biological fitting (blocking process)

Add observational outputs with paper-compatible endpoints: care acts and time, contact duration, crop volume versus nutrient mass, individual body mass/reserve compartments, stage boundaries, temperature and actual activity. Facts must arise from committed state/actions; missing observables are NOT TESTABLE. Pre-register fitting/validation splits and nested colony replicates. Preserve all previous model versions and negative datasets. Evidence grade describes the origin of a measurement, not the validity of a code coefficient.

## Readiness decision

Do not enter S6.4 on the basis of engineering tests or survival in an adequate-access fixture. P01–P04 and P10 expose fundamental founding/lifecycle/physiology gaps. P05–P09 require explicit review decisions about acceptable bounded readiness and scientific debt. Performance is an independent gate; its outcome cannot validate biology. No proposal is implemented by this audit.
