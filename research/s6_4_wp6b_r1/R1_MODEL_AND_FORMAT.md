# Local feeding persistence and version isolation

The candidate is enabled only through `FoundingProfile::feeding_persistence`. The application passes a window in milliseconds and a propensity in parts per million. It retains the v1 profile and canonical bytes with no option. A zero-propensity candidate still has the R1 format and exercises ordinary choice with no additional effective preference. The operational model is immutable after enrollment. A separate world or a baseline checkpoint provides the control.

| Concern | Authority |
|---|---|
| Local opportunity and selection | `cpp/src/care.cpp::resolve_care_wakes` uses the existing neighbor query and local contact list. The candidate can change an admitted selection only within the current brood set, inside the shelter envelope, with lawful custody and a payable protein dose. Existing retrieval and return retain their own branches. |
| Actual transfer | `cpp/src/founding.cpp::resolve_founding_feed` and `cpp/src/founding_internal.hpp::founding_ration` use the same payment, crop, receiver demand and donor maintenance guards in both versions. Existing action begin, handling duration and outcome facts remain in force. A demand-clipped positive dose is visible in the payload. |
| Last paid recipient | `cpp/src/founding_memory.hpp::update_founding_meal_memory` uses only facts emitted by the transaction. It records the latest positive maternal ration and clears the witness on relevant death, stage change, interrupted feed, autonomy stop or a committed local invalidation. |
| Atomic state | `WorldRuntime::State::Metadata` owns the three-field witness. The existing transaction snapshot and journal truncation cover it alongside the queued care state. It is not a lock. Any actual custody or act ownership stays in the care subsystem. |
| Repeat selection evidence | `CareTick` with `FoundingCareWake::Repeat` records selection intent in its previously zero scalar. `BiologicalObservation` gives its same-source opportunity and selected act. A `FoundingRation` and completed bout establish payment. Interrupted acts and unsuccessful ordinary actions remain visible. |
| Replay | `FoundingReplay::review_care` verifies age, origin and same-source local selection against history. The ordinary physiology and care replays still independently validate funding, locality, clocks, outcome and resource ledgers. The independent Python reader reconciles the frame witness from the same ordered canonical evidence. |

The ordinary actor decision stream uses the unchanged admissions, competition and fallback draws. The additional draw is derived from the founder's world seed, identity, decision counter and a separate domain constant. It has no separate mutable RNG or queue. A witness can remain in a save between care decisions even after its nominal expiry. It cannot influence a decision at or beyond that boundary. The next applicable wake expires it before selection. This makes advancing through a time cut observationally neutral.

| Format | Legacy | F1 v1 | F1-R1 |
|---|---|---|---|
| Founding profile version | No founding section | 1 | 2 |
| Checkpoint | Existing feature-specific versions | `AWCKPTF`, schema 15, physics 17 | `AWCKPTG`, schema 16, physics 18 |
| Frame | `AWSTATE1` plus underlying checkpoint header | Same envelope | Same envelope |
| Canonical history blocks | `AWFACT01` | `AWFACT02` | `AWFACT03` |
| Fact widths | Existing 159 or 210 bytes | Same | Same |

R1 appends 12 profile bytes and 24 witness bytes relative to a structurally identical v1 frame. The existing F1 trace fingerprint and the outer checkpoint integrity footer remain in place. The witness follows the trace in a frame. A standalone checkpoint includes full facts. A segmented save hashes the versioned blocks and checkpoint anchor before normal SQLite publication. The SQLite schema and transaction publication sequence are unchanged. An R1 world cannot append to an earlier model's published history under the same identity. A previous reader cannot decode an R1 checkpoint or block by treating it as v1.

The repeat draw and horizon have no quantitative species calibration. Care support from B01, founding output from B03 and warm development from B06 are development constraints. The model does not establish that a queen recognizes an individual larva by identity. Possible biological interpretations include recontact with a locally persistent larva or repeated feeding in the same brood patch. Discriminating these alternatives needs independently recorded maternal contact sequences and dose-resolved recipient histories. [Source and condition audit](F1_V1_LARVAL_PATH_DIAGNOSIS.md)
