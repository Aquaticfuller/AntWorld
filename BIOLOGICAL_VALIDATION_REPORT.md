# S6.3.2 biological validation

## Conclusion and interpretation

The current core is a deterministic, conserved engineering model of selected ecological processes. It is **not a validated Lasius niger life-history model**. Direct evidence supports several qualitative mechanisms, but no current biological coefficient has been quantitatively calibrated by this audit. Queen care prohibition conflicts with direct experiments; temperature-dependent development and several essential observables are absent. Surviving a fixture, passing software tests or citing a plausible mechanism cannot resolve these gaps.

The frozen mappings are in document 49. BIOLOGY_REFERENCES.md contains full species/conditions/locators and access distinctions; BIOLOGY_EVIDENCE_MATRIX.md maps rules, not just topics. PARAMETER_PROVENANCE.csv separates each code expression from related measured evidence. A-grade research does not make a D-grade implementation coefficient A-grade.

## Experimental comparisons

| Endpoint | Experimental evidence | Model observation / limitation | Validation status |
|---|---|---|---|
| Founding queen brood care | B01 care before workers, reversible suppression with workers; B02 retrieval/manipulation | Adult Queen cannot enter Nurse or autonomy. No grooming/repositioning or maternal feeding program | **CONFLICT / NOT IMPLEMENTED** |
| Worker influence on queen | B01 worker addition/removal, close-contact manipulation, older queens recover care | No local worker-history input to queen care or reproductive state | **NOT IMPLEMENTED**; not a missing constant |
| Founding survival/output | B03 240 queens, water, 24.5 C, 49 days, crossed sugar/protein feeding; B06 unfed water-accessible founding | Sealed-resource fixture has different reserves/water, no temperature and no care. Cannot claim empirical survival error | **NOT TESTABLE** as a matched experiment |
| Brood feedback on laying | B01 larvae inhibit founding laying but stimulate established laying in worker-free assays | Constant attempt clock plus maternal resource guard; no founding-state-dependent brood feedback | **CONFLICT if interpreted as complete regulation** |
| Thermal stage development | B06 Table 2, two populations, five temperatures, daily observations | No temperature field; supplied 2/3/2-day clocks do not reproduce empirical magnitude | **NOT IMPLEMENTED** for temperature; severe clock mismatch |
| Queen/worker energy use | B04 mass-adjusted RMR; B05 whole sexual-queen respiration | Same fixture rates/capacities; no body mass, age, oxygen or reserve-compartment matching | **PARTIAL dimensional audit**, no calibrated error |
| Nutrition and survival | B07 diet/frequency-dependent colony growth; B10 worker protein-associated mortality; B11 young-colony diet comparisons | Conserved components, but no diet toxicity, aging, lipid/structural reserve dynamics or quality-sensitive diet choice | **PARTIAL mechanisms; survival response NOT TESTABLE** |
| Local trophallaxis | B08 heterogeneous directed temporal network, contact >5 s; no transferred-mass measurement | Instantaneous committed transfer is real but not the observed duration-defined event; queen absent from paper experiment | **PARTIAL locality**, no event-count or queen-dose calibration |
| Task division/activity | B20 individually heterogeneous participation; B09 age/role associations | Fixed legal-task weights and task duration; task label is not observed movement/care time | **NOT TESTABLE** quantitatively; SD-07 open |
| Trails and route memory | B14 junction geometry; B15/B17 trajectories; B16 context-dependent learning; B18 crowded deposition | Local choice/occupancy/correction verified by S2.2, but grid, dose, turning and observation conditions differ | **PARTIAL**; long-distance following/social recruitment not established |
| Nest morphology | B12 shallow surface building; B13 deep soil excavation/refilling with temperature | Cuboid edits and vacancy/contact proxy, no thermal response, deposited parcels lack full collision shape | **PARTIAL material/space mechanics**; morphology NOT TESTABLE |

## Dimensional and magnitude checks

The core stores energy in nJ and time in ms. **1 nJ/ms = 1 microW**. The original PhysiologyConfig default of 1000 nJ/ms therefore means 1 mW, whereas the long-term fixtures override it to 1 microW. A 1.5 J store lasts 17.361 days at 1 microW in isolation, before crop energy, reproduction, active-program costs or dehydration. These are explicit arithmetic consequences, not measured queen lifetimes.

The carbohydrate yield of 1,000,000 nJ/ug is 0.001 J/ug, or **1 kJ/g**. B22's gross solid-sucrose combustion is about 16.49 kJ/g. The difference demands an explicit chemical/assimilation budget; it does not justify changing the coefficient to the combustion value. The current model has neither lipid fuel nor an experimentally fitted assimilation efficiency. Its energy ledger balances the chosen model, not all biochemical energy of a real ant.

B05 Table 2 measures sexual adult queens at **5.18 +/- 1.06 uL O2/individual/hour (SD, n=20)**, fresh mass 23.63 +/- 4.81 mg, at 20 C. With that paper's declared 20.1 J/mL O2 assumption, the mean is about **28.92 microW**. This is about 28.9 times the long-term fixture's 1 microW, but the animals and physiological states are not matched; it is a magnitude diagnostic, **not a valid prediction error or a recommended replacement**. B04's lower mass-adjusted queen RMR uses a different normalization and much larger queen body mass than a worker. It cannot be interpreted as a fivefold lower whole-queen energy demand. Its pooled-worker and single-queen measurements need careful reconstruction before fitting.

B05's approximately 426 J whole mature-sexual-queen gross energy includes structural material and fuel; it is not interchangeable with 1.5–2 J usable model body energy. Its estimated 689 J cost of producing a mature sexual queen is not the cost of one egg. The source's preliminary lipid estimates do not calibrate founding reserve depletion. The current 20 ug protein, 200 ug water, 0.5 J egg reserve and 0.01 J extra maternal dissipation remain D.

The two-day reserve guard retains **0.1728 J** basal maintenance at 1 microW and 48 ug water at one ug/hour; a successful default egg therefore needs more than 0.6828 J, plus the corresponding own stores. This is a conservative local allocation hypothesis, not an empirically established maintenance window. Offspring receive actual exported energy; it is not all maternal heat loss.

Absorption rates are ug/second multiplied by elapsed time; a six-hour absorption interval is **not** a rate of 10 ug per six hours. In these small-crop fixtures the amount is generally constrained by crop contents/body capacity. Unconsumed carbohydrate remains in crop. Nevertheless, continuous maintenance can reach zero before the next absorption event; timescale sensitivity is real and cannot be dismissed by the mass ledger.

At approximately 25 C, B06's egg-to-worker means are **41.1 days (Borisovka)** and **39.9 days (St Petersburg)**, versus a seven-day fully supplied model clock. Ratios of 5.87 and 5.70 expose a magnitude mismatch, but are not temperature-matched relative errors: the model has no temperature, its artificial diagnostic egg already has the full larval tissue threshold, and prepupal endpoints differ. Table 2 contains non-emergence at the coldest treatment; no missing-data zero is substituted. Published dispersion is retained as reported rather than relabeled a 95% interval.

The long-term decision/holding interval is six hours while surface moves take 1.1 seconds and post-intake contact can occur after 1 ms. These clocks influence encounter supply and program statistics. A high fraction of time assigned an active program does not establish a high measured locomotor activity fraction. A point depot shared by co-located individuals likewise is not an empirical contact network.

## Retained queen failures and alternative causes

All S6.3.1 outcomes remain authoritative evidence of that version, including 0/6 ordinary balanced 32-worker queens surviving to day 90, 0/6 adequate-access eight-worker queens surviving to day 180, and 6/6 adequate-access 32-worker queens sustaining reproduction to day 180. The last group demonstrates that the bookkeeping permits sustained reproduction in a bounded fixture; it does not validate real founding or nutritional physiology.

Existing traces already distinguish abundant resource stock from successful delivery. In corrected ordinary32 seed 2, the last 48 hours contained 782 physical opportunities, only four sampled compatible Nurse/queen encounters and zero selected/committed gifts; 712 ug depot carbohydrate and 1,788 ug in living workers remained at queen death. These categories are not interchangeable. The zero-gift interval does not imply zero food in the colony, and opportunities alone do not prove the queen received a viable dose. Existing seed 5 ordinary8 death with 34,662 ug depot carbohydrate provides another access/scheduling failure, not evidence of disappearing mass.

The old model's seed 1 ordinary8 egg at day 10 left only 16 million nJ after spending from 526 million nJ: 4.444 hours of basal energy before a six-hour uptake pulse. A subsequent 55 ug carbohydrate gift could remain unusable until death. The S6.3.1 reserve gate removed the audited unsafe egg debits, so this historical mechanism must not be claimed as the sole cause of corrected deaths.

The evidence supports interacting limitations: sparse effective provisioning after task/contact selection, own-store reproduction, crop-to-body timing, uncalibrated demand and caste reserves, and missing founding care/feedback. It does **not** uniquely identify a calibrated queen requirement, a correct worker count, or an optimal egg policy. Paper conditions also differ from the compact depot and ordinary surface source. No additional food, queen priority, lifespan floor or fitted survival threshold is introduced in S6.3.2.

## Quantitative calibration opportunities and limits

The new unchanged-core probes contain 18 queen-care eligibility worlds and 30 trajectories over all six frozen seeds. Queen Nurse and autonomy requests reject in every 0/1/5-worker care world, with exact rollback; available worker controls enter Nurse. At 24 hours both resting castes have exactly 1.4136 J and 1576 ug water from identical starting profiles. The supplied-tissue individual changes stage at days 2, 5 and 7 while retaining its identity. The sealed-resource queen dies at 19.675926 days with laying suppressed, or 7.870370 days after two births with laying enabled. All six seeds give the same endpoints in these nonstochastic diagnostics; no artificial between-seed confidence interval is reported. All trajectories preserve exact single-advance versus observation-cadence execution, midpoint restore, nutrient and energy accounting, and canonical event sequences. These are **measured software outcomes**, not empirical founding results.

At the current yield, basal queen maintenance requires 86.4 ug carbohydrate/day; successful default laying every two days would additionally export/dissipate energy equivalent to 255 ug/day. These are model-budget equivalents, not measured diets. Real sustained laying is conditional, and initial reserves subsidize early output. A large food stock does not imply either this assimilation rate or timely delivery. The 18-run historical comparison and its seed-level uncertainty are in `analysis/queen_contrasts.csv` and `queen_contrast_summary.csv`; those uncertainty intervals concern simulator seeds, not natural populations or experimental calibration.

- B06 offers stage/population/temperature endpoints suitable for a future explicit development model, with nest-level uncertainty and endpoint mapping addressed first.
- B05 and B04 offer respiration/mass constraints after matching age, activity, temperature and normalization; they do not currently calibrate queen/worker fixture rates or available reserves.
- B14/B17 offer junction-choice and trajectory endpoints after matching geometry, chemical dose and experience. A trail-choice probability is not the linear trail-weight coefficient.
- B08 offers temporal network and role distributions after adding duration-compatible observations; it supplies no queen-specific transfer mass.
- B13 offers actual nest morphology/material endpoints after implementing matching substrate and local thermal conditions; B12 is a different construction assay.

No numeric fixture is promoted to A/B/C calibration by this audit. All proposed changes require independent approval and isolated validation. SD-04, SD-06, SD-07, SD-08, SD-01/02 and storage/performance debts remain open.
