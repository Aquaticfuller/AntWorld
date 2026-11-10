# S6.4 Preflight Step 1 source coverage

**Submitted for source-inventory review.** The work is on `codex/s6.4-scientific-evidence-audit`, based on the accepted S6.3.4 commit. The Core, scenarios, inherited tests, research data, protocols and negative results match the baseline.

## Coverage and denominators

| Inventory | Coverage | Meaning |
|---|---:|---|
| Compiled `antworld_core` translation units | 18 / 18 | Read by execution role. Behavior and physiology rules, shared phase ordering, checkpoint validation and observational boundaries have different roles. |
| C++ and scenario source files in the file ledger | 160 | Baseline C++ sources, headers, build/test files and two JSON fixtures. Primary-anchor counts distinguish authored entries from scan coverage. |
| Reviewed source mechanism groups | 75 | 68 implemented groups including engineering and observation mechanisms, and seven explicit gaps. |
| Current source transition rows | 99 | Guarded branches and their effects. Some rows document internal state, while others identify proposal, ownership, interruption or observation transitions. |
| Declared state and outcome symbols | 180 across 20 enums | Includes metadata and observer-only labels. The symbol count is separate from the transition count. |
| Parameter rows | 249 | 185 declarations in 26 schemas and 64 reviewed hardcoded values, formulas and guards. |
| Fixture expressions | 4,252 | Typed and symbolic C++ sources plus JSON source lines. Eleven member writes retain multiple candidate owners. |
| Additional numeric candidate lines | 3,910 | Lexical inventory including structural arithmetic, sample inputs and host limits. Counts do not measure calibrated coefficients. |
| Historical Atlas rules | 70 / 70 | 33 retained, 25 extended and 12 clarified after current source review. |
| Historical anchor references | 103 / 103 | All named functions located. Sixty-six references have moved declarations, counting repeated references in different rules. |

The ten domains contain 6 perception, 10 foraging, 5 pheromone, 8 nutrition, 12 brood-care, 4 growth, 5 task, 5 physiology, 8 nest/environment and 6 population groups. Six additional groups cover the execution and observation boundary. [Mechanisms](CURRENT_CORE_MECHANISM_INVENTORY.csv) · [Transitions](STATE_MACHINE_TRANSITION_EVIDENCE.csv) · [Source files](SOURCE_FILE_COVERAGE.csv)

## Source findings that change the next evidence comparison

1. **Cue use and recruitment have different endpoints.** `choose_behavior` gives carrying and home-return requirements precedence. Reachable local food then precedes a remembered route and weighted exploration. A chosen signal-bearing edge receives `FollowTrail` even in a zero-response configuration with trails enabled. A matching cue label cannot establish its causal effect. Deposits are capped scalar increments on successful loaded surface moves, with no diffusion. [Choice](../../cpp/src/behavior.cpp#L48) · [Deposit](../../cpp/src/foraging.cpp#L260) · [Readiness record](../s6_3_4/BIOLOGY_MODEL_READINESS_MATRIX.md)
2. **The model has several distinct local contact paths.** Ordinary nutrition samples bounded candidate ranks before life, colony, distance and material filtering. Care enumerates eligible nearby candidates and records contact opportunities independently of selection. Recipient choice, a completed bout, actual ingredient transfer into crop and later body assimilation are separate events or states. An adult recipient may be the queen. There is no autonomous queen solicitation program. [Ordinary sample](../../cpp/src/social.cpp#L63) · [Care observation](../../cpp/src/care.cpp#L199) · [Transfer](../../cpp/src/physiology.cpp#L159) · [Absorption](../../cpp/src/physiology_internal.hpp#L62)
3. **Integrated care and dedicated assays follow different program boundaries.** Timed integration explicitly leases the motor, preserving ordinary autonomy. Dedicated mode can use random empty-view motion and a single visited pickup-site revisit. An integrated lease clears retrieval memory and tries to return after terminal handling or failure. A blocked return releases the motor. Only a completed close-worker contact refreshes the time used to inhibit new queen care. The individual founding/established context and enrollment age supply metadata. The integrated queen is initialized as `FoundingQueen` and has no automatic transition to `EstablishedQueen`. [Enrollment](../../cpp/src/care.cpp#L76) · [Integration](../../cpp/src/care.cpp#L106) · [Choice](../../cpp/src/care.cpp#L234) · [Completion](../../cpp/src/care.cpp#L423)
4. **Maternal funding debits crop protein.** The protected energy and hydration window uses the mother's own basal rates and current reserves. A funded attempt exports protein from crop, water from hydration and energy from the body store, with separate recorded dissipation. The child inherits the maternal physiology configuration except for the adult protein target. A deferred attempt still records an attempt. The default maintenance horizon is zero. The two-day setting comes from a specific reserve arm. This resolves the ambiguity in the older readiness table's shorthand about maternal tissue. [Funding](../../cpp/src/long_term.cpp#L76) · [Maintenance gate](../../cpp/src/long_term_internal.hpp#L41) · [Defaults](../../cpp/include/antworld/core/long_term.hpp#L12) · [Assay override](../../cpp/apps/s6_3_1_fixture.hpp#L64)
5. **Program tenure, observed activity and energy charge are distinct clocks.** Basal cost applies to every living stage with its individual configuration. The active cost applies to adult `Forage`, `Nurse` and `Excavate` program tenure. Known timed bouts, inactive bouts and unknown time are reported independently of ordinary task residence. Temperature and relative humidity in the care profile are contextual metadata. Larval development is gated by tissue protein and advances on a configured clock. There is no thermal rate, instar state, sleep model or age-specific mortality hazard. [Expenditure and development](../../cpp/src/physiology_internal.hpp#L35) · [Observation window](../../cpp/src/observations.cpp#L5) · [Care environment](../../cpp/include/antworld/core/care.hpp#L35)
6. **Spatial and ecological information boundaries are explicit.** Foragers obtain out-of-contact food cues through a bounded reachable surface scan and use exact food position to sense or approach eligible local targets. Model code also reads exact own nest positions and local recipient deficits. Those are information proxies. Mixed-space foragers can use a bounded geometry-derived connector searched from the depot and retained as a finite path. The public route query accepts a supplied destination and is separate from individual policy. Excavation uses local material and a reachable-site count. Configured resource pulses move declared reserve into an existing food source. [Sensing](../../cpp/src/foraging.cpp#L81) · [Connector](../../cpp/src/spatial_navigation.cpp#L10) · [Public route](../../cpp/src/geometry.cpp#L189) · [Reserve and space demand](../../cpp/src/long_term.cpp#L169)

## Defaults, overrides and source-level scale checks

| Example | Source interpretation |
|---|---|
| Carbohydrate energy credit | The declared `1,000,000 nJ/ug` converts to `1,000 J/g` by multiplying by `10^-9 J/nJ` and `10^6 ug/g`. This is a simulator credit per oxidized mass. |
| Basal and stage clocks | The header's `1,000 nJ/ms` converts to `1 mW`. The long-term lineage fixture can use `1 nJ/ms` or `1 uW`. The 30/60/30 s header development clocks and the 2/3/2 day ecological override remain distinct. |
| Timed care motion | Worker unloaded preference is `0.020 m/s` in the optional motion profile. The default world speed cap is `0.010 m/s`. Timed segments use the lesser of preference and cap, plus the actual distance and action-specific duration rules. The worker loaded preference is an independently configured `0.004 m/s`. |
| Care and continuous spatial activation | Retrieval defaults off and the timed profile is disengaged. Integration and continuous spatial motion each require explicit opt-in. Dedicated assay arena/foreign-brood flags are separate from ordinary integrated care. |
| Earthwork volumes and loads | Quantized lengths multiply `quantum_m`. Dry mass and water are expressed in `ug/q^3`, with `q` one coordinate quantum. The cubic load envelope, local reach and discrete slab choices are separate from a species body-length or soil-density measurement. |

The calculations above are dimensional identities applied to code values. Literature support, comparable units, study conditions, sample counts and quantitative differences remain pending. [Parameter matrix](PARAMETER_EVIDENCE_MATRIX.csv) · [Default physiology](../../cpp/include/antworld/core/physiology.hpp#L8) · [Long-term override](../../cpp/apps/s6_3_1_fixture.hpp#L51) · [Care timing](../../cpp/src/care_internal.hpp#L92)

## Historic source and evidence boundaries

The Atlas rules originate at source commit `2e1a5fa129821176954f26a88f56791635bc8cda`. For example, `WorldRuntime::snapshot` moved from `world_runtime.cpp` to `checkpoint.cpp`. The relocation ledger traces symbols while the crosswalk documents semantic changes. A retained historical rule can still require a different source line or a new full-text check. [Historical crosswalk](HISTORICAL_RULE_CROSSWALK.csv) · [Anchor relocation](HISTORICAL_ANCHOR_RELOCATION.csv) · [Historical source audit](../s6_3_2_1/baseline/STATE_MACHINE_EVIDENCE_AUDIT.md)

Carry forward the B01/B02 quantitative discrepancies, the short initial trail-following runs and unestablished recruitment benefit, SD-04 scarcity allocation, SD-08 queen provisioning, SD-06 construction feedback and SD-07 activity/rhythm limits. The opt-in R1 spatial model retains a flat plane, cubic clearance, no orientation or load posture, bounded connectors and no alternate-route search after permanent blockage. TD-11 opportunity enumeration and larger cold histories remain open beyond the measured storage workload. The prior engineering and storage gates retain their accepted scope. [Brood comparison](../s6_3_3_3/BIOLOGICAL_VALIDATION_AND_UNCERTAINTY.md) · [R1 spatial validation](../s6_3_3_3_r1/SURFACE_3D_CONNECTIVITY_VALIDATION.md) · [Technical debt](../../docs/08_Open_Questions.md) · [Accepted storage and biology results](../../S6_3_4_RESULTS.md)

The first source pass is static. The fixture index covers current C++ and JSON declarations and call expressions. Runtime-specific overrides and CLI-selected assay axes can be traced from the archived protocols and runners, including the reserve comparison, B01/B02 assays and R1 ecological cases. The design JSON is distinct from the S0 headless diagnostic parser, which creates a world from the parsed identity and seed. [Reserve fixture](../../cpp/apps/s6_3_1_fixture.hpp) · [Brood runner](../../tools/run_s6_3_3_3_assays.py) · [R1 runner](../../tools/run_s6_3_3_3_r1.py) · [Headless entry](../../cpp/apps/antworld_headless.cpp#L34)

Full-text requalification, identification of supported numerical values, prioritization of scientific blockers and independent validation design belong to later review steps. The source classifications in this delivery preserve prior engineering provenance and leave scientific assessments pending.

## Verification executed

The frozen Windows S6.3.4 build directories were checked with the existing LLVM-MinGW toolchain. All three build invocations returned success with no rebuild required. Each configuration then ran the complete existing suite.

| Build directory | Local CTest result |
|---|---:|
| `build/s6_3_4-debug` | 212 / 212 |
| `build/s6_3_4-release` | 212 / 212 |
| `build/s6_3_4-sanitizer` with ASan/UBSan | 212 / 212 |

For each directory, the commands were `cmake --build <directory> --parallel 4` and `ctest --test-dir <directory> --output-on-failure --parallel 4`. The source audit verifier, local documentation links and frozen baseline scope also passed. Cross-platform CI and measured performance remain the prior S6.3.4 evidence. No new biological experiment was run in the source-inventory step. [Audit reproduction](README.md#reproduce-the-checks) · [Accepted cross-platform baseline](../../S6_3_4_RESULTS.md#verification-and-remaining-work)
