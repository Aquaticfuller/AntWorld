# Stage A observer and sidecar

The read path is implemented as `antworld_rm02_observer` and used by the isolated `antworld_s6_4_rm02` assay. The constructor takes a lineage, explicit focal IDs and scope, and an owner-thread `const WorldRuntime&`. `capture()` copies and encodes an eligible cut. `publish()` writes the cut outside the Core transaction and updates its own cursor only after SQLite commits. The assay records failed reads or writes and continues the authoritative world. Observer capture does not call `sample_contacts` or `capture_history`. The latter can seal Core journal buffers. [Observer implementation](../../cpp/apps/rm02_observer.cpp) [Assay](../../cpp/apps/antworld_s6_4_rm02.cpp)

## Sidecar v1

The separate SQLite file has application ID `1096241714` and user version `1`. The manifest gives the exact scope, lineage, world and seed. Its origin cursor is zero for a normal run or the explicitly uncovered history prefix when starting a replacement sidecar. Cut sequence starts at one, with time, revision, cursor, RNG identity, examined/selected/written/lost counts and pending/neighbor coverage. Coverage values are 0 not requested, 1 complete within the declared scope, 2 over query limit and 3 missing subject. The cut's loss count applies independently. A completed capture can contain no observed counterpart for an underlying simulated choice.

The first digest is SHA-256 of the UTF-8 manifest identity plus the little-endian uint64 origin cursor. Each next digest covers the preceding 32-byte digest, then 14 little-endian uint64 values and the cut payload. The values are sequence, WorldId high/low, simulation milliseconds, revision, cursor, RNG, prior cursor, examined, selected, records, dropped, pending coverage and neighbor coverage. Every payload record uses one tag byte and a little-endian uint32 body length. Numeric fields below are little-endian uint64 except the existing canonical fact codec and doubles represented by their IEEE binary64 bits.

| Tag | Origin | Body in wire order |
| --- | --- | --- |
| 1 | COMMITTED_FACT | Exact `encode_event` payload, including source and observation fields when applicable |
| 2 | CUT_SNAPSHOT | Entity ID, ant/physiology presence flags. If ant present, colony, birth time, stage, caste, position xyz and carried component vector. If physiology present, crop vector, mother, body energy, water, tissue protein, oxidized carbohydrate, lost water, dissipated and exported energy, program, death cause, next absorption time, progress, physiology and behavior schedule IDs, decision count and carbohydrate yield |
| 3 | CUT_SNAPSHOT | Four-component introduced, accounted, crop, available, carried and depot vectors, followed by hydration, tissue protein, oxidized carbohydrate, lost water, energy input, body and dissipated energy, tracked physiology count, living and total individuals |
| 4 | CUT_SNAPSHOT | Exact pending trophallaxis schedule ID, donor, target, requested amount, issue and execution times, and donor position revision |
| 5 | CUT_SNAPSHOT | Focal actor, living same-colony neighbor, stage and caste from the declared geometry query at the cut |

Mass vectors are carbohydrate, protein, water and other in ug. Time is simulated ms, energy nJ, conversion yield nJ/ug, and coordinates m. An anchor stores SHA-256 of the caller-owned authoritative checkpoint export at the current published sidecar cut. On restore, the app supplies the bytes just restored, verifies the world boundary and checks the entire sidecar digest chain and exact terminal anchor before appending. No checkpoint is copied by the observer on every cut. The existing authoritative store and codec are used as before. Unanchored, missing, corrupted or ahead-of-world logs require a distinct lineage or a separate repair proposal.

The app keeps one capture buffer at a time. Its reserved payload is at most 3 MiB, with one 256-fact page and a pending snapshot only below the fixed queue cap. SQLite uses a bounded page cache and a 64 MiB database cap. SQLite transaction journal bytes and process peaks belong to the Stage B measurement. SQLite, file size, digest and ledger errors are surfaced to the application. A duplicate current cut leaves its record count unchanged. A positive transfer is stored once as its committed fact. Optional care records retain context and are never added again as dose.

## Stage A verification

The Release build of the app and its six focused CTests verifies role-specific partial and actual gifts, uptake and return, no selection, capacity and reach failures, same-tick hatch and death, exact separate-store recovery, digest and foreign-anchor rejection, explicit lost rows, invalid output destinations, transactional sidecar write failure and failed Core advancement. Checkpoint equality includes canonical history and the simulation RNG. Stage B adds the full inherited configurations, controlled timing and cross-platform checks.

The Release suite passed all six tests. A separate 48-hour smoke run with 8 initial workers and seed 17 wrote and reopened the anchored sidecar, matched the uninterrupted observer-off checkpoint and finished with 279 authoritative facts. The smoke run is outside the frozen experiment and timing samples.

```powershell
cmake --build build/s6_3_4-release --target antworld_s6_4_rm02 antworld_s6_4_rm02_tests --parallel 4
ctest --test-dir build/s6_3_4-release --output-on-failure -L RM02
build/s6_3_4-release/antworld_s6_4_rm02 out/s6_4_rm02_sprint/a-smoke window ordinary 8 17
```
