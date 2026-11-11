# S6.4 Phase 2 scientific priority assessment

**Phase 2 complete for independent review. Biological readiness remains open under the proposed v1.0 scope.** The evidence baseline is the accepted Phase 1 commit `2fb9da7a602235a33ed11cc96ee54ab64b2f0f2b`. This review uses its accepted literature, source contexts and conflicts, plus archived simulator comparisons. It establishes the scientific questions and their dependencies. It adds no fitted values or observations and closes no biological blocker.

## Decisions for review

- The proposed envelope is controlled, active-season *Lasius niger* founding and early worker cohorts. It retains maternal allocation, measured nutrition, active care, local foraging, a scoped social recruitment claim, stage timing and survival, worker time use and limited autonomous 3D construction. Full winter, sleep physiology, sexual lifecycle, natural disasters and mature nest ecology remain outside the default claim. Controlled conditions and simplifications still need validation. [Proposed scope and conditions](S6_4_PHASE2_READINESS_SCOPE.md)
- All 75 mechanisms have a priority, evidence basis, scope and endpoint. The 21 direct mechanisms form nine open root blockers. The 34 mechanism and 26 transition flags from Phase 1 remain visible, with their original meaning. A supporting, calibration or optional mechanism can affect a root without becoming a separate research task. [Priority rationale and order](BIOLOGICAL_GAP_PRIORITY.md) [Mechanism decisions](S6_4_PHASE2_MECHANISM_PRIORITY.csv) [Blocker register](S6_4_PHASE2_BLOCKER_REGISTER.csv)
- The parameter review assigns 26 fields to matched empirical measurement, 46 to defensible range and sensitivity analysis, 48 to experimental conditions or fixture controls, 91 to engineering or numerical treatment, and 38 to presently unidentified quantities or laws. It retains the 369 accepted use contexts and their distinct judgments for the 25 mixed-applicability keys. All current values retain their Phase 1 provenance. [Parameter dispositions](S6_4_PHASE2_PARAMETER_PRIORITY.csv)
- The surviving quantitative discrepancies are specific to the compared endpoints and model versions. B01 scan-rate and B02 count differences have observed comparators. B02 timing uses nonaligned markers, and the thermal clock comparison is an unmatched scale diagnostic. Ordinary 90-day queen loss and the 8/32-worker 180-day contrast expose delivery and allocation questions inside the archived simulations. They supply no natural survival error. Local trail response has support while the archived naive recruitment effect remains unresolved. [Quantitative gaps and acceptance observations](UNRESOLVED_GAPS.md)

Start with observations that distinguish delivery and uptake, actual activity and power, active care and movement, and local discovery and return. Those measurements also constrain the reproductive, developmental, recruitment and nest questions. Use stage- and cohort-matched risk to interpret survival after these component processes are separated. The 12 accepted cross-domain findings remain linked through the blocker or parameter registers. A plausible aggregate population, traffic or nest result cannot resolve unmeasured compensations. [Dependencies and admissible approximations](BIOLOGICAL_GAP_PRIORITY.md#evidence-dependencies-and-research-order)

## Reproducible evidence checks

The independent verifier checks the frozen Phase 1 files, all mechanism, transition and parameter references, scope and conflict identities, exact original citations and sample units, the acyclic blocker dependencies, and the 25 context-dependent parameter judgments. The mechanism and blocker CSVs are reviewed decisions. The parameter CSV can be regenerated from the accepted integrated matrix and the documented priority groups. The checks require tracked data and the approved Git reference.

```sh
python tools/audit_s6_4_preflight.py --check
python tools/test_s6_4_preflight.py
python research/s6_4_preflight/verify_batch1.py
python research/s6_4_preflight/verify_batch2.py
python research/s6_4_preflight/verify_batch3.py
python research/s6_4_preflight/verify_scientific_integration.py
python research/s6_4_preflight/verify_scientific_priorities.py
```

All seven commands returned exit status 0 locally, including the seven source anchor tests. Six in-memory negative checks rejected a reassigned transition, a missing root link, an invented locator, an unknown conflict, a cycle and an unsupported calibration claim. The Evidence workflow runs the new check after all accepted checks. These checks establish scientific traceability and the integrity of the accepted results. Core CI retains its engineering regression scope. [Verification program](verify_scientific_priorities.py)

Phase 2 ends with review of the proposed scope, root blocker definitions, priority decisions and acceptance observations. Phase 3 requires acceptance of those decisions before it specifies identifiable parameters, calibration and independent validation protocols. Model remediation and final readiness evaluation remain later decisions.
