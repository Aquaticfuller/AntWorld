# S6.3.3.1 care state and observation audit

The reviewed Atlas and S6.3.3 audit cover inherited care and other programs. This table adds the opt-in retrieval transitions and the observable distinction between picking a task, reaching brood, carrying it, and revisiting its former location. The new rules use grade F `ENGINEERING_FIXTURE` until task-specific experiments identify their parameters.

| Boundary | C++ implementation and condition | Committed evidence | Biological interpretation and limit |
| --- | --- | --- | --- |
| Observe | `care.cpp`, `resolve_care_wakes`: query current local range, same colony, living immature brood, and unobstructed line. Existing reachable-target opportunities are emitted before retrieval eligibility filters. | Opportunity records and a Selected action. First in-range brood in the study is reconstructed at the decision from positions and the fixture range. | The observation is a spatial proxy. Brood recognition modalities, sensitivity and true encounter duration remain open. |
| Start a retrieval episode | `resolve_care_wakes`: original reserve, social-contact and care propensity checks apply. Locally seen displaced brood precedes manipulation of settled items. An item visibly held by a different caregiver is ineligible for a new displaced target. | Selected, and then Started if revalidation succeeds. | Lenoir documents repeated carrying by workers. Displaced-first priority and the starting lottery are fixture rules. |
| Approach or continue | `resolve_care_wakes`: one previously selected identity persists while locally visible, reachable in the decision query and still displaced. After an eligible start the active episode avoids another care lottery. Approach uses the old bounded swept step. | Separate approach start and terminal, and a movement fact at successful completion. The current target must be physically reachable for handling to start. | Candidate mechanism for task persistence. It retains the established step and duration. Closed paths stop movement instead of supplying a shortcut. |
| Pick up and carry | `execute_care_action`: live, local and caste/stage-valid target, contact at start, transactional lock, and revalidation at completion. Carrier and brood sweeps must be clear. | Started contact, one valid movement of each identity, Completed, or an Interrupted reason. Target conflicts still emit facts. | B02 measures contact and deposition in its specific apparatus. The model commits positions at the terminal and cannot reconstruct within-step trajectories. |
| Record the pickup area | Successful nonzero joint motion associates the first carrier position with its started transport bout. An in-shelter terminal releases the focus. | Durable `BroodMoved` and carrier movement, followed by Completed. The stored anchor links to a Started and nonzero Completed transport. | A visited site is an engineering memory proxy. A familiar shelter coordinate was already part of S6.3.3 and approximates the habituated tube. |
| Revisit or terminate | A caregiver with a pickup anchor can approach a newly eligible displaced target or take one swept return to the prior pickup position. Arrival, loss of focus, blocked or rejected action, interruption and incapacity clear the appropriate episode. | `RevisitBroodSite` uses the ordinary Selected/Started/Completed/Interrupted chain with an empty entity target. It records motion as carrier motion. | Returning to a prior pickup area is consistent with repeated trips. B02 and Lenoir do not identify the cue, exact route or memory span. |
| Restore or roll back | `checkpoint.cpp`, `checkpoint_care.hpp` and the existing transaction journal. Opt-in worlds store target and pickup-bout IDs plus an optional pickup position in schema 12 / physics 14. | The current care plan and stored anchors are checked against committed evidence. Legacy schema 11 / physics 13 retains its byte layout. | Versioning and atomicity are engineering contracts. The fixture is opt-in. |

The Species profile holds the opt-in switch. The Individual profile retains the role and declared age context, and retrieval memory is per caregiver. The Environment profile carries the inherited assay metadata. Temperature and relative humidity remain metadata in this care study. The evidence grade for observed persistence is independent of the grade for the implemented policy.

Links to full-text scope, data, negative controls and the source for each inherited fixture are in [Evidence](EVIDENCE.md) and [Parameter provenance](PARAMETER_PROVENANCE.csv).

## Native change list

| Files | Scope |
| --- | --- |
| `cpp/include/antworld/core/care.hpp`, `world_runtime.hpp` | False-by-default Species switch, individual retrieval state, appended act ID and version constants. |
| `cpp/src/care.cpp`, `care_internal.hpp` | Bounded local eligibility, continuation, pickup evidence, transactional movement and invalidation. |
| `cpp/src/checkpoint.cpp`, `checkpoint_care.hpp` | Opt-in codec, legacy compatibility and committed-memory audit. |
| `cpp/apps/antworld_s6_3_3_experiment.cpp` | Predeclared layout and policy arms with the original assays preserved. |
| `cpp/apps/antworld_s6_3_3_1_density.cpp` | TD-11 diagnostic and full post-phase checkpoint and trace verification. |
| `cpp/tests/test_s6_3_3_1.cpp`, `test_allocation_failure.cpp`, `cpp/CMakeLists.txt` | Six targeted care contracts, one allocation rollback suite and fixture/test registration. |

The source files for metabolism, reproductive allocation and thermal development are outside the change. The legacy timing benchmark source, executable targets and profile compile switches retain their existing behavior.
