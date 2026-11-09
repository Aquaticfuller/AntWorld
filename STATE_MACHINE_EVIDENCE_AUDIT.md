# State machine evidence audit: S6.3.3

The70-rule historical audit is preserved in [baseline](research/s6_3_2_1/baseline/STATE_MACHINE_EVIDENCE_AUDIT.md). Its old source locators refer to the verified project archive, not current code. P01/P10 only are implemented; other proposals and biological debts remain open. New constants have no quantitative calibration.

|Rule|Current source/function|Actual condition|Evidence and interpretation|Limits|
|---|---|---|---|---|
|C01|cpp/src/care.cpp:8 `configure_biology`|Opt-in unexecuted social/long-term world; profile validation; no legacy activation|F; Engineering version/rollback boundary|No species claim|
|C02|cpp/src/care.cpp:38 `enable_brood_care`|Live adult Queen or Worker, physiological, paused, local familiar shelter; no Male or immature caregiver|B01 B02; B01/B02 maternal capability; exact enrollment interface is engineering|No queen Forage/Excavate; chronological maturity not implemented|
|C03|cpp/src/care.cpp:110 `resolve_care_wakes`|Same-colony live neighbors inside radius and actual spatial visibility; no global population count|B01; Locality-constrained approximation|Sensory6mm range unmeasured; colony recognition assumed|
|C04|cpp/src/care.cpp:110 `resolve_care_wakes`|Own body energy/hydration >=quarter capacity; otherwise inactive|F; Existing urgency proxy, not matched physiology|Threshold and baseline/activity metabolism uncalibrated; P02 remains open|
|C05|cpp/src/care.cpp:110 `resolve_care_wakes`|Queen may select close-worker bout first; only completed bout refreshes finite fading cue|B01; B01 social plasticity supports direction, not this memory law|Time occupancy and memory inhibition distinguished by inhibition0 control|
|C06|cpp/src/care.cpp:110 `resolve_care_wakes`|Uniform local brood selection; approach if outside reach; retrieve if outside familiar shelter; else inspect/arrange/clean/feed|B01 B02; B01 manipulation; B02 retrieval capability|Priority/equal probabilities F; local brood may divert continued searching|
|C07|cpp/src/care.cpp:185 `execute_care_action`|Finite inspection and cleaning require target lock, living brood and physical contact|B01; Explicit motor-bout definitions; B01 active manipulation composite|No direct cleaning duration/frequency estimate; no pathogen benefit|
|C08|cpp/src/care.cpp:185 `execute_care_action`|Arrange same-ID brood locally; transport caregiver plus same-ID brood through swept loaded clearance|B02; B02 actual retrieval, not instantaneous completion|Discrete geometry and known shelter approximate arena/odor; rate F|
|C09|cpp/src/care.cpp:185 `execute_care_action`|Feed only actual larval demand/crop, existing transfer-limit transaction, finite attempted bout|B01 B02; Maternal nutritional capability; no new physiological law|No flight-muscle/lipid mobilization, egg feeding or queen provision update|
|C10|cpp/src/care.cpp:110 `resolve_care_wakes`|No local brood ->bounded random cardinal walk; no coordinate oracle|F; Minimal engineering local search|Search/navigation geometry not quantitatively validated by B02|
|C11|cpp/src/care.cpp:66 `interrupt_care`|Movement/death/maturation/pause/blocked geometry cancels invalid act and releases ownership|F; Committed physical causality|Interrupted duration distinguished from success|
|C12|cpp/src/care.cpp:250 `observe_legacy_action`|Legacy committed action classified; unknown physical duration stays unknown|F; P10 observation completeness boundary|No retrospective invention of grooming or motor duration|
|C13|cpp/src/observations.cpp:5 `behavior_window`|Half-open clipped intervals; active/inactive/unknown separate from task residence; reads pure|B01 B02; Experiment-compatible observer|B01 scan presence differs from time budget; B02 count differs from retrieval rate|
|C14|cpp/src/checkpoint_care.hpp:58 `validate_care_evidence`|Evidence-backed decisions, contact cue, selected/start/terminal matching, schedule ownership and locks|F; Engineering restore audit|Scalar ENGINEERING_FIXTURE parameters are not empirical facts|
|C15|cpp/storage/analytics.cpp:204 `contributions`|Append seven flow metrics; target participant histories; completion-time duration flow|F; Historical evidence from committed events|Flow buckets are not interval-overlap activity estimates|
|C16|cpp/src/care.cpp:110 `resolve_care_wakes`|Founding/established age labels do not change coefficients; queen-specific inhibition absent in worker policy|B01 B02; Caste difference retained without unsupported age curve|No callow maturation, genotype or parent-offspring correlation|

B01 locator: DOI10.1111/1365-2435.14536, Methods2.1.4,2.2.4-5,2.2.12; Figs1c-d/2c. B02: DOI10.1002/ece3.4475, pp10411-10412, Methods2.2-2.3, Figs1-2. These links support endpoint capabilities; they do not turn engineering probabilities or durations into measured parameters.

All current typed configuration/default/fixture expressions are rescanned. New implicit source expressions are retained verbatim with source hashes. Unknown-range and ambiguity labels are retained, never silently resolved as empirical values. The geometry/time/identity/resource mechanisms and inherited70-rule audit retain their earlier limitations.
