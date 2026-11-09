# State machine evidence audit

Unchanged source baseline: `2e1a5fa129821176954f26a88f56791635bc8cda`. This audit changes no Core behavior or numerical parameter.

The 54 inherited mechanism records remain linked to their original S6.3.2 assessment, whose **A-D grade namespace is historical**. The atlas uses A-F only in explicit new grade fields. All current numerical coefficients and implicit rules remain F / ENGINEERING_FIXTURE. Biological support for a qualitative mechanism never validates its particular condition or weight.

The source-expression inventory includes every lexical condition, numeric-bearing or enum-state line in the 14 named implementation/helper files. It is not a C++ AST or a claim that every expression is biological. File-group links require surrounding-function review; precise links are labelled FUNCTION. The config inventory separately scans headers, applications and tests. These are complementary completeness checks, not evidence coverage.

70 reviewed mechanism groups; 881 lexical source-expression records. See [SOURCE_RULE_INVENTORY.csv](research/s6_3_2_1/SOURCE_RULE_INVENTORY.csv) and [PARAMETER_PROVENANCE.csv](PARAMETER_PROVENANCE.csv).

## Q01 — Founding queens actively care for brood, and established queens can resume care after worker removal

**Actual rule:** physiology.cpp:change_behavior rejects every non-Paused behavior unless Adult Worker; ecology.cpp:change_autonomy also requires Worker

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp), [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: change_behavior;change_autonomy.

**Verified code anchors:** cpp/src/ecology.cpp:15 (change_autonomy); cpp/src/physiology.cpp:94 (change_behavior).

**Assessment:** CONFLICT. Caste prohibition is a **direct conflict** if used as a complete queen model. Queen care is not worker foraging. Grooming/repositioning/retrieval and maternal feeding are absent

**Evidence:** B01 B02. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ReproductionConfig;PhysiologyConfig;PhysiologySeed;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P01; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## Q02 — Reproduction after mating; founding versus established state matters

**Actual rule:** long_term.cpp:enable_reproduction accepts a live adult queen with physiology; no mating/founding state

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp), [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: enable_reproduction.

**Verified code anchors:** cpp/src/long_term.cpp:39 (enable_reproduction).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Seeded adult queen implicitly means mated and competent; reasonable fixture boundary, not a modeled maturation process

**Evidence:** B01 B03. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ReproductionConfig;PhysiologyConfig;PhysiologySeed;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P01/P03; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## Q03 — Egg production is condition dependent; larvae have opposite observed effects in founding and established queens

**Actual rule:** execute_reproduction attempts one egg at each fixed interval, including after skipped attempts

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp), [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: execute_reproduction.

**Verified code anchors:** cpp/src/long_term.cpp:80 (execute_reproduction).

**Assessment:** CONFLICT. No ovarian maturation, brood feedback or founding history. Fixed attempts are D, and a condition-invariant interpretation conflicts with the experiment

**Evidence:** B01. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ReproductionConfig;PhysiologyConfig;PhysiologySeed;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P03; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## Q04 — Maternal resources fund offspring; feeding alters founding output

**Actual rule:** execute_reproduction requires own crop protein, body water and body energy; transfers actual stores into a new egg

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp), [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: execute_reproduction.

**Verified code anchors:** cpp/src/long_term.cpp:80 (execute_reproduction).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Local and conserved. Specific egg costs and conversion of crop protein directly into egg tissue are D. Lipids, structural reserves and trophic eggs absent

**Evidence:** B03. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ReproductionConfig;PhysiologyConfig;PhysiologySeed;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P02/P03; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## Q05 — Reproductive allocation can depend on body condition (B03; A qualitative)

**Actual rule:** long_term_internal.hpp:reproductive_resources protects basal energy and water for maintenance_horizon; primary fixture uses 2 days

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp), [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: reproductive_resources;has_maternal_reserve.

**Verified code anchors:** cpp/src/long_term_internal.hpp:42 (has_maternal_reserve); cpp/src/long_term_internal.hpp:50 (reproductive_resources).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Retain the validated reserve safety mechanism. Neither a 2-day horizon nor its sharp threshold has direct evidence; it is not fixed lifespan protection

**Evidence:** B03. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ReproductionConfig;PhysiologyConfig;PhysiologySeed;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P03; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## Q06 — Births and identity through development

**Actual rule:** execute_reproduction registers the child only after successful funding and gives it Worker caste; failure leaves stores/IDs/history unchanged

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp), [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: execute_reproduction.

**Verified code anchors:** cpp/src/long_term.cpp:80 (execute_reproduction).

**Assessment:** ENGINEERING_INVARIANT. Correct engineering; all-worker output is an incipient-colony scope assumption. Sex, mating and alate production NOT IMPLEMENTED

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ReproductionConfig;PhysiologyConfig;PhysiologySeed;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** Deferred explicit scope; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## Q07 — Caste and developmental physiology differ

**Actual rule:** Offspring physiology copies the mother's config, resets adult protein target; current queen and workers share most capacities/rates

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp), [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: execute_reproduction.

**Verified code anchors:** cpp/src/long_term.cpp:80 (execute_reproduction).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Inheritance of numerical fixture settings is not biological inheritance. No size, lipid pool or caste scaling. Unjustified homogeneous physiology

**Evidence:** B04 B05. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ReproductionConfig;PhysiologyConfig;PhysiologySeed;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P02; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## L01 — Maintenance and dehydration

**Actual rule:** physiology_internal.hpp:settle/next_physiology consumes linear energy and water continuously between events; death at zero

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: settle;next_physiology.

**Verified code anchors:** cpp/src/physiology_internal.hpp:86 (next_physiology); cpp/src/physiology_internal.hpp:50 (settle).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Conserved phenomenology C; numerical rates D. Constant rates lack temperature, mass, activity intensity and water balance feedback

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig;PhysiologySeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P02/P04; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## L02 — Developmental and activity costs

**Actual rule:** Same basal rate for Egg/Larva/Pupa/Adult; extra rate for Forage/Nurse/Excavate, none for Rest/Paused

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: expenditure.

**Verified code anchors:** cpp/src/physiology_internal.hpp:45 (expenditure).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Active task labels are not actual locomotor activity. No stage-specific growth/respiration. B05 measures differing sexual-stage respiration, not worker calibration

**Evidence:** B05. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig;PhysiologySeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P02; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## L03 — Crop-body separation and assimilation

**Actual rule:** Absorption at next_absorption, after continuous depletion; carbs and water absorbed by Larva/Adult only

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: absorb;next_physiology.

**Verified code anchors:** cpp/src/physiology_internal.hpp:68 (absorb); cpp/src/physiology_internal.hpp:86 (next_physiology).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Separation is reasonable C; instantaneous 6-hour fixture pulses and all-or-nothing death before a due pulse are D. Rates are ug/s multiplied by elapsed time, **not ug/pulse**

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig;PhysiologySeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P02/P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## L04 — Usable energy and tissue growth

**Actual rule:** absorb limits consumed carbohydrate to remaining body energy capacity; unused carbohydrate stays in crop; protein incorporated only by larvae

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: absorb.

**Verified code anchors:** cpp/src/physiology_internal.hpp:68 (absorb).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Conservation is sound. `carbohydrate_yield_nj_per_ug=1000000` means 1 kJ/g. Gross combustion is about 16.49 kJ/g sucrose (B22, C); net/gross meaning and losses must be defined before fitting

**Evidence:** B22. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig;PhysiologySeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P02; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## L05 — Embryogenesis and nutrition-limited growth

**Actual rule:** Egg stage advances for fixed duration without feeding; larval progress is blocked until tissue protein reaches the full threshold

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: developing;stage_duration.

**Verified code anchors:** cpp/src/physiology_internal.hpp:42 (developing); cpp/src/physiology_internal.hpp:36 (stage_duration).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Stage sequence supported A (B06), but an instantaneous protein threshold followed by fixed growth is D; size, instars and gradual nutritional growth absent

**Evidence:** B06. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig;PhysiologySeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P04; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## L06 — Egg-to-worker development

**Actual rule:** Larva then Pupa advance by fixed clocks; 2/3/2 days in long-term fixtures, temperature absent

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: stage_duration.

**Verified code anchors:** cpp/src/physiology_internal.hpp:36 (stage_duration).

**Assessment:** CONFLICT. Serious magnitude mismatch with B06 Table2. Its prepupa+pupa endpoint needs mapping. No temperature input means temperature response is NOT IMPLEMENTED

**Evidence:** B06. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig;PhysiologySeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P04; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## L07 — Continuous individual identity

**Actual rule:** execute_physiology transitions stages on the same EntityId, records facts, activates eligible adult workers

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: execute_physiology.

**Verified code anchors:** cpp/src/physiology.cpp:66 (execute_physiology).

**Assessment:** ENGINEERING_INVARIANT. Engineering support, not measured biological timing. Newly eclosed workers immediately use the same task policy; callow maturation absent (B09/B19 context)

**Evidence:** B09 B19. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig;PhysiologySeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P04/P06; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## L08 — Individual mortality

**Actual rule:** Death from energy depletion/dehydration or explicit fixture command; stops actions/reproduction/contact index; corpse stores remain accounted

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: execute_physiology;stop_physiology.

**Verified code anchors:** cpp/src/physiology.cpp:66 (execute_physiology); cpp/src/physiology.cpp:53 (stop_physiology).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Starvation is possible, but age-, diet- and disease-related mortality absent. Cannot reproduce B10/B19 survival under sustained feeding

**Evidence:** B10 B19. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig;PhysiologySeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P07; retain negative starvation results; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S01 — Limited encounters

**Actual rule:** social.cpp:sample_contacts samples at most 16 ranks from 27 neighboring buckets, then filters identity, life, colony, distance and solid barriers

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: sample_contacts.

**Verified code anchors:** cpp/src/social.cpp:64 (sample_contacts).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Local and bounded; not an empirical contact process. Bucket sampling can spend budget on self or occluded ants. Ants may share a position: soil clearance does not implement inter-ant excluded volume or contact duration. B08 gives real heterogeneous temporal networks, not a 16-sample calibration

**Evidence:** B08. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S02 — Task persistence and safe completion

**Actual rule:** ecology.cpp:resolve_autonomy_wakes switches only at depot or when stationary, unloaded and soil-free; observes minimum task duration except Paused

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_autonomy_wakes.

**Verified code anchors:** cpp/src/ecology.cpp:97 (resolve_autonomy_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Reasonable engineering approximation D; fixed 6-hour minimum and depot constraint not measured. Can delay responding to local demand

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05/P06; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S03 — Hunger/larval demand

**Actual rule:** Need is read from reachable sampled neighbors; signaled_need uses exact receiver stores, capacities and larval protein threshold

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: signaled_need;resolve_autonomy_wakes.

**Verified code anchors:** cpp/src/ecology.cpp:97 (resolve_autonomy_wakes); cpp/src/social_internal.hpp:74 (signaled_need).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Spatially local but physiologically omniscient **within contact**; signal transduction absent. A need proxy, not a demonstrated sensory mechanism

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S04 — Nutrient-responsive task choice

**Actual rule:** At depot, available nutrition includes own crop plus physical depot stock; Nurse eligibility requires compatible sampled need; forage requires a local surface step

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_autonomy_wakes.

**Verified code anchors:** cpp/src/ecology.cpp:97 (resolve_autonomy_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. No global averaging/food oracle. Deposited stock is a point store; quality-specific foraging response absent despite B07 field diet selection

**Evidence:** B07. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05/P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S05 — Self-maintenance

**Actual rule:** Own energy or hydration below one quarter makes Rest urgent if local compatible supplies exist

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_autonomy_wakes.

**Verified code anchors:** cpp/src/ecology.cpp:97 (resolve_autonomy_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Reasonable local priority C/D; 25% and exact sensing D. No satiety, fatigue, sleep pressure or circadian state

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P06; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S06 — Persistent provisioning

**Actual rule:** With local_work_continuation, a nonurgent Nurse holding compatible crop remains Nurse when demand is sampled

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_autonomy_wakes.

**Verified code anchors:** cpp/src/ecology.cpp:97 (resolve_autonomy_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Local minimal S6.1 repair with engineering benefit; no experiment calibrates the hold condition. A sampled absence is not proof that brood demand disappeared

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S07 — Stochastic task allocation

**Actual rule:** Otherwise draw among legal Rest/Forage/Nurse/Excavate with weights 4/8/12/4

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_autonomy_wakes.

**Verified code anchors:** cpp/src/ecology.cpp:97 (resolve_autonomy_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. D. No age/experience/individual thresholds. B20 reports heterogeneous tasks/activity; B09 distinguishes age and social role, not these probabilities

**Evidence:** B09 B20. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P06; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S08 — Unloading and recovery

**Actual rule:** long_term.cpp:notify_return causes Rest/depot visit; no central command

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: notify_return.

**Verified code anchors:** cpp/src/long_term.cpp:241 (notify_return).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Local engineering approximation D; Rest is still an active nutrition service loop, not observed sleep

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P06; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S09 — Social feeding

**Actual rule:** physiology.cpp:resolve_nutrition_wakes permits gift generation only in Nurse, with own urgent deficit priority

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_nutrition_wakes.

**Verified code anchors:** cpp/src/physiology.cpp:237 (resolve_nutrition_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. B08 directly observes food-returning foragers as donors. A Forage label here differs from experimental role, so this is a **restrictive model mismatch**, not proof that all foragers must gift continuously

**Evidence:** B08. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S10 — Local allocation

**Actual rule:** Compatible recipient selected uniformly by reservoir sampling from eligible contacts

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_nutrition_wakes.

**Verified code anchors:** cpp/src/physiology.cpp:237 (resolve_nutrition_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Avoids systematic ID preference; D biology. No queen mandate, global needs or optimal emergence allocation. Physiological state/solicitation/contact duration absent

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S11 — Trophallaxis

**Actual rule:** resolve_nutrition_action validates live entities, colony, proximity, solid clearance, supply and receiver capacity, then atomically transfers actual components

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_nutrition_action.

**Verified code anchors:** cpp/src/physiology.cpp:165 (resolve_nutrition_action).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Oral exchange A (B08); instantaneous ingredient transfer and arbitrary ug limit D. B08 event counts are a proxy, **not measured ug**; queenless sugar trials cannot calibrate queen protein preference

**Evidence:** B08. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S12 — Intake versus provisioning

**Actual rule:** gift_first prioritizes a compatible gift; otherwise cargo/depot intake below half crop capacity

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_nutrition_wakes.

**Verified code anchors:** cpp/src/physiology.cpp:237 (resolve_nutrition_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Local D threshold policy; no globally injected nutrients. Current low-crop gate and eligibility timing can strand resources (S6.3.1 traces)

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S13 — Local load composition

**Actual rule:** Demand-sensitive withdrawal uses componentwise maxima from bounded local contacts, rather than summed/global needs

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_nutrition_wakes.

**Verified code anchors:** cpp/src/physiology.cpp:237 (resolve_nutrition_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Reasonable D proxy; exact requested composition is not experimentally established. Liquid/solid processing and food palatability absent

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05/P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S14 — Contact sequencing

**Actual rule:** continue_nutrition_behavior after a successful depot intake schedules Nurse at +1 ms; otherwise physiological behavior interval

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: continue_nutrition_behavior.

**Verified code anchors:** cpp/src/physiology.cpp:315 (continue_nutrition_behavior).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Preserves a real transaction and avoids a 6-hour wait, but the 1 ms versus 6-hour contrast is an engineering scheduling artifact

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S15 — Surplus recycling

**Actual rule:** Rest returns excess crop protein to depot up to transfer limit; tissue is never magically reclaimed

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: resolve_nutrition_wakes;resolve_nutrition_action.

**Verified code anchors:** cpp/src/physiology.cpp:165 (resolve_nutrition_action); cpp/src/physiology.cpp:237 (resolve_nutrition_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Conserved D abstraction, not demonstrated oral-to-stock processing in L. niger. No corpse/egg cannibalism or larval excretion recycling implemented

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P05; keep SD-04 open; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S16 — Worker provisioning

**Actual rule:** Queen normally remains Paused and receives gifts, but generates neither intake nor solicitation actions

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: change_behavior;resolve_nutrition_wakes.

**Verified code anchors:** cpp/src/physiology.cpp:94 (change_behavior); cpp/src/physiology.cpp:237 (resolve_nutrition_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Worker-dependent mature provisioning is plausible A, permanent maternal passivity is not (B01/B02). Queen can starve beside food; do not solve by forced gifts

**Evidence:** B01 B02. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P01/P05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## S17 — Activity/rest budget

**Actual rule:** Rest/Paused still have basal metabolism; no fatigue oscillator; task dwell is counted as activity

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp), [cpp/src/social_internal.hpp](cpp/src/social_internal.hpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: expenditure;resolve_autonomy_wakes.

**Verified code anchors:** cpp/src/ecology.cpp:97 (resolve_autonomy_wakes); cpp/src/physiology_internal.hpp:45 (expenditure).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Current 97.6% active-task history is a **label occupancy statistic**, not locomotor duty cycle or sleep. No valid equality with B20 observed activity scans

**Evidence:** B20. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P06; SD-07 open; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F01 — Autonomous departure

**Actual rule:** foraging.cpp:start_foraging requires adult worker at nest, no external pending action; local RNG seeded by actor/decision

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: start_foraging.

**Verified code anchors:** cpp/src/foraging.cpp:57 (start_foraging).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Independence and reproducibility are engineering properties. Foraging motivation is supplied by social policy, not a biological departure hazard

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P06/P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F02 — Local senses

**Actual rule:** sense BFS samples food within radius 2 cells and four neighboring trail cells; steps respect solid clearance

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: sense.

**Verified code anchors:** cpp/src/foraging.cpp:85 (sense).

**Assessment:** PARTIAL_OR_UNCALIBRATED. B14/B17 support local trail response A. Food existence and exact first step in a 2 cm reachable radius are D proxy; no odor diffusion, antenna geometry or chemical identity

**Evidence:** B14 B17. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F03 — Central-place foraging and finite memory

**Actual rule:** choose_behavior: carrying at home -> Deliver; carrying away -> Return; full path or trip budget also -> Return

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: choose_behavior.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Reasonable A qualitative/C abstraction. Exact bounded reverse path is a memory, not a food oracle. Fixed trip limit D

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F04 — Homing

**Actual rule:** Return follows the recorded predecessor; blockage leaves Rest/default action rather than inventing a route

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: choose_behavior.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Local evidence only; no path integration, landmark recovery or shortcut learning. Returning by exact trace overstates memory precision

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F05 — Discovery and resource choice

**Actual rule:** Nearest locally sensed food always precedes memory/trails; equal-distance sources chosen uniformly after physical ordering

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: choose_behavior.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Correct ID neutrality; distance-only choice is D. Composition, concentration and learned value absent (B07/B10)

**Evidence:** B07 B10. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F06 — Collection and learning

**Actual rule:** At food -> Collect up to cargo capacity; food competition resolves deterministically; successful collection -> Return and record path

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: choose_behavior;after_action.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior); cpp/src/foraging.cpp:162 (after_action).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Finite resources and acquisition are real facts. Cargo is external to crop; no feeding handling time by food type. Single exposure gives perfect grid memory

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F07 — Private/social information integration

**Actual rule:** Valid unexpired memory absolutely precedes trails; blocked/empty endpoint or age >5 min erases it

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: choose_behavior.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Memory use A (B15/B16); exact precedence/expiry D. Experiments distinguish reassurance and learning, including negative replication (B16)

**Evidence:** B15 B16. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F08 — Persistence and error correction

**Actual rule:** Explore candidates exclude immediate predecessor unless no alternative, or it is the only visible trail cue

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: choose_behavior.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior).

**Assessment:** PARTIAL_OR_UNCALIBRATED. A qualitative U-turn response to missing trail (B15), but categorical veto/one-cue exception D. S2.2 engineering validation does not prove reliable long trails

**Evidence:** B15. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F09 — Local steering

**Actual rule:** Visited weight 1, unvisited 10, heading bonus 20, linear capped trail bonus 180; unbiased weighted draw

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: choose_behavior.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior).

**Assessment:** PARTIAL_OR_UNCALIBRATED. All numeric coefficients D. B14 shows geometry interaction; B17 occupancy changes without necessarily speed/straightness changes. No directional chemical arrow

**Evidence:** B14 B17. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F10 — Trail utilization metric

**Actual rule:** Move to a trail-bearing cell labels the decision FollowTrail regardless of counterfactual choice

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: choose_behavior.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior).

**Assessment:** PARTIAL_OR_UNCALIBRATED. A descriptive trace label, **not causal attribution**. Ablations and continuous occupancy/correction endpoints are required

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** Retain S2.2 negative evidence; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F11 — Recruitment signal production

**Actual rule:** after_action: every loaded successful move deposits 1 unit at destination, capped16; no outward deposits

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: after_action.

**Verified code anchors:** cpp/src/foraging.cpp:162 (after_action).

**Assessment:** CONFLICT. Return marking A, universal loaded-only fixed deposition conflicts with observed conditional/outgoing deposition (B16/B18). No food quality or crowding feedback

**Evidence:** B16 B18. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F12 — Decay

**Actual rule:** trail_at exponential half-life60s, cutoff.001; Environment maintenance5s; local reads do not advance time/RNG

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: trail_at;maintain_trails.

**Verified code anchors:** cpp/src/foraging.cpp:219 (maintain_trails); cpp/src/surface_internal.hpp:56 (trail_at).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Reasonable C kinetics, all values D. Detectability duration and chemical half-life are different endpoints; no measured concentration mapping

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## F13 — Concurrent decisions

**Actual rule:** resolve_wakes freezes perceptions for same-phase individuals, commits proposals then resolutions; finite memories are checkpointed

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/surface_internal.hpp](cpp/src/surface_internal.hpp); functions: resolve_wakes.

**Verified code anchors:** cpp/src/foraging.cpp:124 (resolve_wakes).

**Assessment:** ENGINEERING_INVARIANT. Deterministic engineering guarantee, not synchronized biology. Never use submission order as evidence of preference

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig;SurfaceConfig;WorldConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** Preserve; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## X01 — Crowding-induced work

**Actual rule:** local_space_demand: bounded reachable empty sites versus sampled contacts times4; at least2 contacts for digging eligibility

**Source:** [cpp/src/excavation.cpp](cpp/src/excavation.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/geometry.cpp](cpp/src/geometry.cpp), [cpp/src/geometry_internal.hpp](cpp/src/geometry_internal.hpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp); functions: local_space_demand;resolve_autonomy_wakes.

**Verified code anchors:** cpp/src/ecology.cpp:97 (resolve_autonomy_wakes); cpp/src/long_term.cpp:259 (local_space_demand).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Local D proxy. B21 is fire-ant quasi-2D extrapolation C; B13 is direct L. niger morphology/thermal evidence A. Neither calibrates this threshold

**Evidence:** B13 B21. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig;LongTermConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P09; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## X02 — Local excavation

**Actual rule:** local_frontiers returns adjacent valid cuts; resolve_excavation_wakes randomly selects one

**Source:** [cpp/src/excavation.cpp](cpp/src/excavation.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/geometry.cpp](cpp/src/geometry.cpp), [cpp/src/geometry_internal.hpp](cpp/src/geometry_internal.hpp); functions: local_frontiers;resolve_excavation_wakes.

**Verified code anchors:** cpp/src/excavation.cpp:241 (local_frontiers); cpp/src/excavation.cpp:311 (resolve_excavation_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Actual material removal and bounded perception; not evidence of functional chamber construction. Soil moisture/cohesion and brood-location demand absent

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig;LongTermConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P09; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## X03 — Search for work

**Actual rule:** No frontier -> choose open six-axis step with greatest Manhattan distance from own depot; full trace -> return

**Source:** [cpp/src/excavation.cpp](cpp/src/excavation.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/geometry.cpp](cpp/src/geometry.cpp), [cpp/src/geometry_internal.hpp](cpp/src/geometry_internal.hpp); functions: resolve_excavation_wakes.

**Verified code anchors:** cpp/src/excavation.cpp:311 (resolve_excavation_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Own depot is known, not global food. Outward maximization and axis-only paths are arbitrary D heuristics

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig;LongTermConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P09; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## X04 — Transport/backfill

**Actual rule:** Loaded excavator retraces path, drops soil at depot; Fill action changes geometry and invalidates connectivity

**Source:** [cpp/src/excavation.cpp](cpp/src/excavation.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/geometry.cpp](cpp/src/geometry.cpp), [cpp/src/geometry_internal.hpp](cpp/src/geometry_internal.hpp); functions: resolve_excavation_wakes;resolve_soil_action.

**Verified code anchors:** cpp/src/excavation.cpp:311 (resolve_excavation_wakes); cpp/src/excavation.cpp:64 (resolve_soil_action).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Conserved and spatially validated. Autonomous deposition piles do not become collision geometry; biological disposal/backfill choice absent

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig;LongTermConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P09; TD-04; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## X05 — Excavation mechanics

**Actual rule:** resolve_soil_action validates local reach/clearance/load and debits configured work energy per removed quantum

**Source:** [cpp/src/excavation.cpp](cpp/src/excavation.cpp), [cpp/src/ecology.cpp](cpp/src/ecology.cpp), [cpp/src/geometry.cpp](cpp/src/geometry.cpp), [cpp/src/geometry_internal.hpp](cpp/src/geometry_internal.hpp); functions: resolve_soil_action.

**Verified code anchors:** cpp/src/excavation.cpp:64 (resolve_soil_action).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Engineering material correctness; rate/energy/cubic body D. B12 construction involved sediment pellets, body templates and chemical effects, not rectangular cuts

**Evidence:** B12. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig;LongTermConfig;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** P09; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## E01 — Resource input

**Actual rule:** execute_resource_release moves finite declared reserve into food each day, optionally alternating 15-day productivity spans

**Source:** [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp); functions: execute_resource_release.

**Verified code anchors:** cpp/src/long_term.cpp:198 (execute_resource_release).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Explicit ecological boundary flux, not a biological regeneration model. No plants/aphids/weather; no infinite replenishment

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ResourceCycleConfig;LongTermConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** Retain label; no new ecosystem module; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## E02 — Environmental response

**Actual rule:** No temperature field, seasonal physiology, diapause or humidity response in the audited config families

**Source:** [cpp/src/long_term.cpp](cpp/src/long_term.cpp), [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp); functions: validate_cycle;configure_long_term.

**Verified code anchors:** cpp/src/long_term.cpp:8 (configure_long_term); cpp/src/long_term_internal.hpp:62 (validate_cycle).

**Assessment:** NOT_IMPLEMENTED. NOT IMPLEMENTED; direct B06/B13 experimental responses cannot be reproduced. A cyclic resource schedule is not temperature

**Evidence:** B06 B13. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ResourceCycleConfig;LongTermConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** P04/P09; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## G01 — Fact integrity and spatial continuity

**Actual rule:** world_runtime.cpp:advance_to/resolve_actions, transaction journal, phase watermark, versioned geometry and checkpoints

**Source:** [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp), [cpp/src/geometry.cpp](cpp/src/geometry.cpp); functions: advance_to;resolve_actions.

**Verified code anchors:** cpp/src/world_runtime.cpp:259 (advance_to); cpp/src/world_runtime.cpp:173 (resolve_actions).

**Assessment:** ENGINEERING_INVARIANT. Engineering invariants retained. They do not validate biologically omitted variables

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** WorldConfig;GeometryConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** Preserve all regressions; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## G02 — Evidence-based analytics

**Actual rule:** Query/inspection/history report actual states/actions, including rejected or skipped actions distinctly

**Source:** [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp), [cpp/src/geometry.cpp](cpp/src/geometry.cpp); functions: events_after;snapshot.

**Verified code anchors:** cpp/src/world_runtime.cpp:325 (events_after); cpp/src/world_runtime.cpp:319 (snapshot).

**Assessment:** ENGINEERING_INVARIANT. A decision/proposal is not a completed act; opportunity != selected contact != successful gift != absorption. Maintain these distinctions in validation

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** WorldConfig;GeometryConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** Preserve; P10 observables; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H01 — Morphology and collision

**Actual rule:** Loaded versus unloaded cubic half-extent; all castes share configured collision sizes; absent geometry accepts spatial clearance

**Source:** [cpp/src/geometry.cpp](cpp/src/geometry.cpp), [cpp/src/geometry_internal.hpp](cpp/src/geometry_internal.hpp); functions: body_half;spatially_clear.

**Verified code anchors:** cpp/src/geometry.cpp:82 (body_half); cpp/src/geometry.cpp:67 (spatially_clear).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Uniform body cube is an engineering proxy; caste size and articulated posture absent

**Evidence:** B04 B05 N23. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC07; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H02 — Local contact versus reachable paths

**Actual rule:** Neighbor query uses Euclidean radius plus straight segment clearance; generic queries can contain dead ants and callers must filter

**Source:** [cpp/src/geometry.cpp](cpp/src/geometry.cpp), [cpp/src/geometry_internal.hpp](cpp/src/geometry_internal.hpp); functions: query_neighborhood;spatially_clear.

**Verified code anchors:** cpp/src/geometry.cpp:105 (query_neighborhood); cpp/src/geometry.cpp:67 (spatially_clear).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Straight-line contact is appropriate for direct touch; do not mistake global path reachability for mouth contact

**Evidence:** B08 N01. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC04; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H03 — Navigation engineering

**Actual rule:** Six-axis A* seeks an explicitly supplied goal with node budget and swept-body checks; autonomous workers do not receive global food destinations from this API

**Source:** [cpp/src/geometry.cpp](cpp/src/geometry.cpp); functions: query_route;validate_route.

**Verified code anchors:** cpp/src/geometry.cpp:144 (query_route); cpp/src/geometry.cpp:215 (validate_route).

**Assessment:** PARTIAL_OR_UNCALIBRATED. No food oracle is present in normal autonomy; body clearance remains mandatory; grid anisotropy unresolved

**Evidence:** N11 N25. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC07; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H04 — Geometric evidence

**Actual rule:** Initial solid plus ordered edits is authoritative; caches and portals are versioned derived data

**Source:** [cpp/src/geometry.cpp](cpp/src/geometry.cpp); functions: geometry_edits;query_material;configure_geometry.

**Verified code anchors:** cpp/src/geometry.cpp:10 (configure_geometry); cpp/src/geometry.cpp:232 (geometry_edits); cpp/src/geometry.cpp:41 (query_material).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Exact engineering representation does not establish natural tunnel morphology

**Evidence:** B12 B13 N22. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC07; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H05 — Deterministic competition

**Actual rule:** Competing resource actions rank by resource and deterministic hash of seed,time,resource,actor; duplicate actor proposals keep one

**Source:** [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: resolve_actions;rank.

**Verified code anchors:** cpp/src/world_runtime.cpp:41 (rank); cpp/src/world_runtime.cpp:173 (resolve_actions).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Uniform resource selection is distinct from contention ranking; changing ResourceId can change hash arbitration, not biological preference

**Evidence:** B07 N15. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H06 — Finite physical food

**Actual rule:** Component masses use integer proportional partition with deterministic residual allocation; collection has cargo room and availability bounds

**Source:** [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: resolve_actions;portion.

**Verified code anchors:** cpp/src/world_runtime.cpp:24 (portion); cpp/src/world_runtime.cpp:173 (resolve_actions).

**Assessment:** PARTIAL_OR_UNCALIBRATED. A one-microgram residual tie is numerical, not nutrient preference; mixed liquid/solid handling absent

**Evidence:** N15 B07. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** FoodMass;AntSeed. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC04; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H07 — Action eligibility and temporal concurrency

**Actual rule:** Nonworker/nonadult action actor is rejected; same-time phases batch perception before resolution; rollback and phase watermark protect facts

**Source:** [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp); functions: advance_to;resolve_actions.

**Verified code anchors:** cpp/src/world_runtime.cpp:259 (advance_to); cpp/src/world_runtime.cpp:173 (resolve_actions).

**Assessment:** CONFLICT. Queen care conflict exists in both policy eligibility and action resolution; fixing one gate alone is insufficient

**Evidence:** B01 B02. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC01; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H08 — Ontogeny evidence

**Actual rule:** Explicit stage-change commands are fixture inputs; automatic physiological transition retains entity identity

**Source:** [cpp/src/world_runtime.cpp](cpp/src/world_runtime.cpp), [cpp/src/physiology.cpp](cpp/src/physiology.cpp); functions: schedule_lifecycle;execute_physiology.

**Verified code anchors:** cpp/src/physiology.cpp:66 (execute_physiology); cpp/src/world_runtime.cpp:137 (schedule_lifecycle).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Externally scheduled stage changes cannot validate endogenous development

**Evidence:** B06 N16. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC03; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H09 — Sensory competition and finite memory

**Actual rule:** Nearest local food overrides memory/trails; route memory stores positions; visible trail predecessor exception; cutoff removes weak signals

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp), [cpp/src/foraging.cpp](cpp/src/foraging.cpp); functions: sense;choose_behavior.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior); cpp/src/foraging.cpp:85 (sense).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Exact local food knowledge is a bounded proxy, not odor transport; sensory modalities and reward valuation absent

**Evidence:** B07 B14 B15 B16 N20. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC06; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H10 — Local work and soil disposal

**Actual rule:** Autonomous excavation requires path_size>1; no cut at depot; bounded64-position return path; loaded soil returns to depot

**Source:** [cpp/src/excavation.cpp](cpp/src/excavation.cpp); functions: resolve_excavation_wakes.

**Verified code anchors:** cpp/src/excavation.cpp:311 (resolve_excavation_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Depot exemption and outward Manhattan preference are arbitrary; dropped soil is a conserved pile without solid collision geometry

**Evidence:** B12 B13 N22. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** GeometryConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC07; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H11 — Task termination and rest

**Actual rule:** Payload1 and completed depot visit can force Rest; urgent threshold is quarter capacity; minimum task hold bypass for Paused

**Source:** [cpp/src/ecology.cpp](cpp/src/ecology.cpp); functions: resolve_autonomy_wakes.

**Verified code anchors:** cpp/src/ecology.cpp:97 (resolve_autonomy_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Rest is a nutrition-service label, not a measured inactive or sleep state; fatigue/circadian state absent

**Evidence:** B20 N21. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC05; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H12 — Local encounter process

**Actual rule:** Bounded Floyd rank sampling across27 spatial buckets includes invalid candidates before filtering; exact contacts revalidated at resolution

**Source:** [cpp/src/social.cpp](cpp/src/social.cpp); functions: sample_contacts.

**Verified code anchors:** cpp/src/social.cpp:64 (sample_contacts).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Finite encounter budget is not a measured temporal contact network; valid-exposure and gift counts differ

**Evidence:** B08 N01. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;WorldConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC04; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H13 — Assimilation and development

**Actual rule:** Integer remainder preserves ug/s integration; depletion deadline can precede the next uptake pulse; larval tissue threshold gates progress

**Source:** [cpp/src/physiology_internal.hpp](cpp/src/physiology_internal.hpp); functions: pulse_allowance;absorb;next_physiology.

**Verified code anchors:** cpp/src/physiology_internal.hpp:68 (absorb); cpp/src/physiology_internal.hpp:86 (next_physiology); cpp/src/physiology_internal.hpp:63 (pulse_allowance).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Conservation correctness does not calibrate step size or instantaneous absorption; pulse timing may determine starvation

**Evidence:** B06 B07. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** PhysiologyConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC02;MC03; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H14 — External ecological boundary input

**Actual rule:** Finite reservoir releases components by fixed interval with optional cyclic low-productivity fraction

**Source:** [cpp/src/long_term_internal.hpp](cpp/src/long_term_internal.hpp), [cpp/src/long_term.cpp](cpp/src/long_term.cpp); functions: productivity;release_amount;execute_resource_release.

**Verified code anchors:** cpp/src/long_term.cpp:198 (execute_resource_release); cpp/src/long_term_internal.hpp:72 (productivity); cpp/src/long_term_internal.hpp:78 (release_amount).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Explicit finite input is not plant/aphid regeneration or season physiology; no hidden nutrient source

**Evidence:** UNKNOWN: no biological measurement. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** ResourceCycleConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC08; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H15 — Care and nutritional transport

**Actual rule:** Only Nurse initiates gifts; Rest may withdraw and recycle; Queen remains Paused; actual gifts validate source,target,capacity,need and barriers

**Source:** [cpp/src/physiology.cpp](cpp/src/physiology.cpp); functions: resolve_nutrition_wakes;resolve_nutrition_action.

**Verified code anchors:** cpp/src/physiology.cpp:165 (resolve_nutrition_action); cpp/src/physiology.cpp:237 (resolve_nutrition_wakes).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Demand proxy and task gating need separate controlled tests; no queen-forcing or global optimal allocator

**Evidence:** B01 B02 B08 N01 N14. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** SocialConfig;LongTermConfig;PhysiologyConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC01;MC04; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).

## H16 — Reproducible stochastic choice

**Actual rule:** Food and trail decisions use local per-ant RNG; weights are integerized with precision factor1048576; scale is numerical, not biological

**Source:** [cpp/src/behavior.cpp](cpp/src/behavior.cpp); functions: choose_behavior.

**Verified code anchors:** cpp/src/behavior.cpp:17 (choose_behavior).

**Assessment:** PARTIAL_OR_UNCALIBRATED. Dimensionless weights need assay-specific fitting later; no directional chemical arrows

**Evidence:** B14 B17. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).

**Parameters:** BehaviorConfig. Numerical evidence grade F; no calibration.

**Proposal / validation:** MC06; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).
