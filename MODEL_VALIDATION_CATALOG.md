# Model validation catalog

These are proposed replications, not executed biological validation or newly fitted parameters. Existing synthetic simulator experiments remain engineering evidence. READY is deliberately not awarded when the original observation protocol cannot be reproduced.

Calibration and validation are distinct data roles. A proposed holdout must be frozen before fitting. If the same colonies or observations are reused, report internal fit only, not independent validation. No statistical equivalence margin is invented where the source supplies only a qualitative result.

## V01 — Founding queen care and worker removal

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [B01](https://doi.org/10.1111/1365-2435.14536), [B02](https://doi.org/10.1002/ece3.4475). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Calibration candidate B01; independent retrieval B02.

**Procedure:** Repeat paper-specific worker addition/removal and six-item displaced-brood assays; use each source conditions, do not pool.

**Endpoints:** Care time, brood retrieval latency, laying by founding state.

**Missing mechanisms:** Queen active care and social-stage state.

**Comparison:** Compare care categories and worker manipulation effects; retrieval is a separate endpoint.

**Uncertainty and limits:** Qualitative sign only where exact numbers not extracted; colony-level bootstrap later.

## V02 — Founding feeding factorial

**Capability:** PARTIAL. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [B03](https://doi.org/10.1093/biolinnean/blad149). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Independent holdout after mechanism design.

**Procedure:** 240 foundresses; eight30-queen arms;24.5+/-0.5 C;49d; original single/weekly diet doses.

**Endpoints:** Survival, eggs, larvae, pupae, workers, body condition.

**Missing mechanisms:** Queen care, body mass/lipids, real food composition, temperature.

**Comparison:** Do not convert wet cricket portion into pure protein without assay.

**Uncertainty and limits:** Source effects and exclusions; simulator cannot currently reproduce full conditions.

## V03 — Constant-temperature first brood

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [B06](https://doi.org/10.1023/b:joey.0000033808.45455.75). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Calibration: two populations; validation: withheld population/temperature after preregistration.

**Procedure:** Use all extracted Table2 temperatures with unfed queens/water; retain censored cold arms.

**Endpoints:** Egg,larva,prepupa+pupa duration.

**Missing mechanisms:** Temperature, continuous growth, instars and endpoint distinction.

**Comparison:** Stage-specific likelihood including censored individuals; no pooled universal Q10.

**Uncertainty and limits:** Reported error type unresolved; raw colony structure needed before fitted CI.

## V04 — Caste and stage oxygen budget

**Capability:** NOT_TESTABLE. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [B04](https://doi.org/10.1111/mec.70127), [B05](https://doi.org/10.1007/bf00299234), [N10](https://doi.org/10.1111/1365-2435.70359), [N27](https://doi.org/10.1016/j.jinsphys.2024.104698). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Calibration B04 source dataset; B05 sexual-stage external check.

**Procedure:** 20 C unrestrained queens and worker pools; separate sexual-stage respiration; dormancy SMR18 C.

**Endpoints:** O2 rate, mass, caste/stage, movement.

**Missing mechanisms:** Mass, oxygen observable, substrate respiratory quotient, dormancy.

**Comparison:** Convert only with justified O2 energy equivalent; pool exponent is not individual exponent.

**Uncertainty and limits:** B04 sample-count conflict; N27 mixed-species allometry and device/temperature confounding, stated conversion arithmetic conflict; no J/ms target fabricated.

## V05 — Local exchange timing and contact network

**Capability:** PARTIAL. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N01](https://doi.org/10.1007/s00040-010-0133-y), [B08](https://doi.org/10.1038/s41598-019-52019-6). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Calibration N01 timing; independent network validation B08.

**Procedure:** N01 20fed+20starved after4d;30min; B08 distinct90min sugar-return assay.

**Endpoints:** Direction-specific duration, exchange count, degree concentration.

**Missing mechanisms:** Contact duration, continuous location and measured transferred mass.

**Comparison:** Fit duration hazard only after source CI problems resolved; compare graph temporal statistics separately.

**Uncertainty and limits:** Exchanges nested in ants/colonies; event count is not mass.

## V06 — Partial food load and brood-dependent recruitment

**Capability:** PARTIAL. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N15](https://doi.org/10.1016/j.crvi.2008.10.005), [N14](https://doi.org/10.1016/s0003-3472(04)00107-1). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** N15 calibration candidate; N14 brood manipulation independent validation, after preventing reused-colony leakage.

**Procedure:** N14 4d starvation,3uL1M sugar or maggot homogenate,+/-brood;Table1 subgroup-specific Ns;record exploring/returning/marking independently.

**Endpoints:** Load volume, subsequent marking, satiation.

**Missing mechanisms:** Crop-volume observation, food quality, optional marking.

**Comparison:** Use observed volumes separately from maximum crop capacity.

**Uncertainty and limits:** N15 All and TL groups overlap; N14 table and figure denominators differ; food volume is not pure nutrient mass.

## V07 — Mirrored Y trail choice

**Capability:** PARTIAL. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [B14](https://doi.org/10.1111/eth.12248), [B17](https://doi.org/10.1007/s00040-026-01106-9). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Calibrate on B14 only; hold out B17 geometry/dose.

**Procedure:** Artificial chemical trails; branch angle and mirror controls as source.

**Endpoints:** Choice proportion, initial direction, paths.

**Missing mechanisms:** Physical chemical concentration and continuous sensory geometry.

**Comparison:** Compare binomial choice with colony-cluster uncertainty; no current weight fitting.

**Uncertainty and limits:** 398 choices not398colonies; dose not simulator field units.

## V08 — Memory, reassurance and incorrect trails

**Capability:** PARTIAL. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [B15](https://doi.org/10.1098/rsbl.2011.0067), [B16](https://doi.org/10.1371/journal.pone.0149720), [N20](https://doi.org/10.1007/s00040-024-00995-y). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Independent validation including negative replication.

**Procedure:** 21cm walkway and7cm gap; separately complex maze repeated7visits; erroneous line trial.

**Endpoints:** U-turns, straightness, learning, deposition positions.

**Missing mechanisms:** Continuous movement and conditional deposition.

**Comparison:** Keep negative replication and difference in task demands; simulator S2 results remain separate.

**Uncertainty and limits:** Do not claim long-distance social recruitment from local occupancy.

## V09 — Rest aggregation and time budgets

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N21](https://doi.org/10.1007/s00040-004-0739-z), [B20](https://doi.org/10.1111/j.1439-0310.1983.tb00088.x). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** N21 calibration; B20 independent activity observation.

**Procedure:** Clean/marked tubes,20workers,20trials,5/60min; separate daytime scans.

**Endpoints:** Rest-site counts, inactivity bout duration.

**Missing mechanisms:** Rest location behavior, fatigue/circadian categories.

**Comparison:** Map observations to true motion, not task names; winner labels are post hoc.

**Uncertainty and limits:** Daytime7.5h cannot identify24h duty cycle.

## V10 — Thermal and substrate nest architecture

**Capability:** PARTIAL. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [B13](https://doi.org/10.1111/1365-2656.14040), [N22](https://doi.org/10.1098/rspb.2010.0176), [B12](https://doi.org/10.1073/pnas.1509829113). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** N22 separate substrate calibration; B13 true3D validation; B12 surface-only.

**Procedure:** Match worker count,soil water,density,temperature profiles and CT days.

**Endpoints:** Excavated volume,depth,connectivity,morphology.

**Missing mechanisms:** Thermal fields,soil cohesion,body/pellet geometry,brood placement.

**Comparison:** Compare distributions by colony; never pool surface pillars with underground chambers.

**Uncertainty and limits:** N22 transition subset censored; fixed density is not a density-response curve.

## V11 — Waste compartment and founding hygiene

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N04](https://doi.org/10.1371/journal.pone.0118376), [N05](https://doi.org/10.1186/s12862-017-1062-4). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Independent validation proposals.

**Procedure:** 21 colored-diet nests; separately open/closed founding corpse assays.

**Endpoints:** Fecal location,external waste,biting/burial/removal.

**Missing mechanisms:** Waste classes,defecation,pathogen/corpse actions.

**Comparison:** Qualitative location and count targets; keep nonsignificant infection contrasts.

**Uncertainty and limits:** N04 arithmetic discrepancy prevents uncritical mean-patch target.

## V12 — Local recognition and defense

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N08](https://doi.org/10.1111/1365-2435.14104), [N09](https://doi.org/10.1155/2012/383757), [N26](https://doi.org/10.3390/ani10122451). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Independent validation; no multi-species implementation in this stage.

**Procedure:** Match within-colony acclimation and3min dead-opponent assay; separate T-bridge and1h contests.

**Endpoints:** Aggression,local aggregation,arrival,mortality.

**Missing mechanisms:** Recognition cues,defense actions and multi-species state.

**Comparison:** Use species-specific tests; do not assign pooled significance to L. niger.

**Uncertainty and limits:** Single/repeated colony stocks; field competition not established by arena fights.

## V13 — Acclimation, water balance and dormancy

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N07](https://doi.org/10.1242/jeb.243847), [N10](https://doi.org/10.1111/1365-2435.70359). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** N07 reserve whole colonies before calibration; N10 one-colony comparison cannot validate across populations.

**Procedure:** 3-week20/28C acclimation; separate active/dormant10d8C crossed test.

**Endpoints:** Desiccation survival,CTmin,LTe50,SMR.

**Missing mechanisms:** Temperature,humidity,CHC/dormancy and actual water balance.

**Comparison:** Survival censoring; stage-specific curves; preserve Ln SMR null result.

**Uncertainty and limits:** N07 432 raw rows include uncertain early deaths and README status-code conflict; N10 289 CTmin,20 fittedLTe50,57 pooledSMR and20 duplicate condition means; no universal coefficient.

## V14 — Nuptial flight and climate

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N02](https://doi.org/10.1007/bf00348045), [N13](https://doi.org/10.1111/ecog.03140). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Observational external validation only.

**Procedure:** Species-confirmed local field flights versus mixed citizen-science series.

**Endpoints:** Flight dates,time,weather,sex.

**Missing mechanisms:** Alates,mating/readiness and environmental cycle.

**Comparison:** Probabilistic association; observed extrema never hard release thresholds.

**Uncertainty and limits:** Species verification only subset; observer effort and spatial weather mismatch.

## V15 — Other-species photoperiod and first brood

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N12](https://doi.org/10.13102/sociobiology.v62i4.818). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Separate L. japonicus future database; never Ln calibration.

**Procedure:** 21queens/temperature/light arm;15/20/25C;16:8versus12:12.

**Endpoints:** Firstlaying,firstpupation,100dqueen survival.

**Missing mechanisms:** Photoperiod,diapause,species-specific development.

**Comparison:** Species-isolated comparison; no current simulator run.

**Uncertainty and limits:** Collection-to-pupation differs from egg/pupa duration; cannibalism only hypothesized.

## V16 — Adult survival and diet

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [B19](https://doi.org/10.1016/j.exger.2016.09.008), [B10](https://doi.org/10.1098/rspb.2012.0051), [B11](https://doi.org/10.1038/s41598-025-06406-x). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Independent validation after reserve model calibration.

**Procedure:** Common-garden worker cohorts; separate diet studies and queen survival exclusions.

**Endpoints:** Censored survival,age/diet hazards.

**Missing mechanisms:** Ageing,diet toxicity,disease and reproductive cost physiology.

**Comparison:** Kaplan-Meier and cause-specific hazard; compare at matched observation windows.

**Uncertainty and limits:** Natural/experimental lifespan differ; no fitted fixed maximum lifespan.

## V17 — Physical deposit imaging

**Capability:** NOT_TESTABLE. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N19](https://doi.org/10.48550/arXiv.2610.18079). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Exploratory preprint, not independent benchmark.

**Procedure:** Glass bridge;same-ant example deposits;25-26C;quantitative phase imaging.

**Endpoints:** Volume/time,spatial deposit layout.

**Missing mechanisms:** Physical chemical mixture and optical observable.

**Comparison:** No conversion to arbitrary field amplitude or behavioral half-life.

**Uncertainty and limits:** Refractive-index uncertainty; two examples not population fit; preprint.

## V18 — Worker diversity and brood production

**Capability:** PARTIAL. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N16](https://doi.org/10.1186/s12862-021-01890-x). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Independent validation; no genetics implementation.

**Procedure:** 30pupaeoneoriginversus3x10origins withunrelatedqueen;41analyzedcolonies.

**Endpoints:** Larvae,eggs,foraging,emergence.

**Missing mechanisms:** Individual response heterogeneity,callow maturation,queen care.

**Comparison:** Retain nonsignificant foraging and no new-egg adults during window.

**Uncertainty and limits:** Excluded failed colonies must not become silent simulator exclusions.

## V19 — Light-dependent aggregation by worker role

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N17](https://doi.org/10.1016/j.jinsphys.2004.04.009). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Independent validation candidate; no fitting performed.

**Procedure:** Two roles,20 ants,6 replicates;red-only90min versusdark90min followedred90min at source spectrum/lux.

**Endpoints:** Fraction aggregated,cluster size and first-minute dispersal.

**Missing mechanisms:** Light sensing,role-observable aggregation,temperature confound control.

**Comparison:** Reproduce source observation protocol and compare distributions; no invented equivalence margin.

**Uncertainty and limits:** Approximate published fractions only; tenders not known-age cohort.

## V20 — Substrate kinematics and null preference

**Capability:** NOT_IMPLEMENTED. **Execution:** DESIGN_ONLY_NOT_RUN; no biology modification or fitting authorized.

**Original sources:** [N25](https://doi.org/10.1016/j.jinsphys.2007.12.001). Exact pages/figures, population, samples and controls are in the source register and measurement records.

**Data separation:** Independent validation candidate; no fitting performed.

**Procedure:** 25 ants/substrate120s5Hz trajectories;6pairs26 choices;40ants20conditioning trials.

**Endpoints:** Projected speed,directionality,free-path and choice/learning probability.

**Missing mechanisms:** Substrate microtexture,continuous locomotion,perceptual cue representation.

**Comparison:** Reproduce source observation protocol and compare distributions; no invented equivalence margin.

**Uncertainty and limits:** 95%CI retained; repeated decisions not independent; fine-grain caption mismatch.
