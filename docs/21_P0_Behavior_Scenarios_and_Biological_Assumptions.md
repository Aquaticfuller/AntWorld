# P0 biological models, fixtures and evidence limits (v0.8)

This translates the biological topics into a minimum implementable reference flow. Fixture numbers are engineering inputs, not calibrated Lasius niger measurements.

## Species and parameter provenance

L. niger is the confirmed first focus species. SpeciesDefinition and BehaviorParameterSet should carry version, units and ParameterSource. ENGINEERING_FIXTURE means correctness-testing inputs; LITERATURE_CALIBRATED requires species, conditions, units, fitting method and evidence; USER_MODIFIED identifies an experimental player variation. Species sensing, pheromone, development and construction parameters do not belong as unqualified constants inside the global scheduler.

## Minimal tasks

| Task | Local input | Actual action / success condition |
|---|---|---|
| Explore | Nearby geometry, food/trail cues, physiology | Legal local search; discovery requires actual encounter |
| CollectFood | Perceived reachable source | Validated stock/capacity/contact; partial success allowed |
| ReturnNest | Limited learned routes, known topology, local cues | Actual travel to a reachable nest region |
| Trophallaxis | Nearby nestmate, crop and life state | Contact-qualified conserved transfer |
| FeedBrood | Nearby brood demand and available food | Actual receipt with nutrition accounting |
| Rest | Weak task stimulus or physiological need | Lower activity expenditure, wake on legal stimulus |
| Excavate | Reachable soil front, material and capacity | Actual bounded removal and material/geometry commit |
| TransportSoil | Carried parcel and reachable destination | Travel and deposition with material identity retained |

No permanent artificial scout occupation. Preferences vary with age, experience and state. Queens do not run worker tasks; eggs/pupae do not perform adult actions.

## Local decision candidate

`S_i(a)=b_species(a)+sum_k(w(a,k)*cue_i(k))+inertia_i(a)-threshold_i(a)`.

Filter legal candidates by distance, caste/stage, energy and resources; choose via defined deterministic randomness or thresholds. Minimum duration, cooldown and emergency interruption limit switching. Sensors query only local information, not all food coordinates. Start Explore/Collect/Return/Rest and add each later task with proposal, actual commit and failure tests.

## Trails, memory, nutrition and geometry

Pheromones occupy walkable surfaces, with candidate local deposition and `C(t+dt)=C(t)*exp(-lambda*dt)` decay. If diffusion is enabled, validate numerical stability. Limited route/landmark associations have strength and age; memory is neither language nor global GPS. Trail/memory influence need not produce universally shortest paths. Congestion feedback and route learning need species-qualified parameter evidence.

Food ingredients are micrograms, including other mass where needed; components sum to total. Body energy is joules, separate from crop contents. Real trophallaxis changes both participants atomically. Identity persists Egg/Larva/Pupa/Adult/Dead. Development/laying/mortality equations are versioned and source-qualified. The suggested 1 queen, 32 workers and 12 brood are coverage inputs, not a natural population claim.

The smallest geometry experiment has a real 3D chamber/entrance/frontier, transport route and deposition site. Digging is a local cut proposal, not BuildRoom. Overlap, transport, fill and connectivity are validated with ledgers and clearance. An axis-aligned soil block and sphere/capsule cuts are suitable engineering fixtures, not a claim that real ants make those primitive shapes.

## Fixtures and experiments

scenarios/p0_smoke.json is the empty infrastructure scenario. scenarios/p0_biology_fixture.json seeds a queen, 32 workers, 12 brood, two resources, nest/frontier hints and an observation window; later stages progressively enable behavior. Outputs retain ENGINEERING_FIXTURE status. Fixed seeds test reproducible mechanisms; biological plausibility needs multi-seed comparisons and suitable literature.

| ID | Experiment | Required observations |
|---|---|---|
| F1 | Search without initial outside trail | Actual discovery time, coverage and discovering IDs |
| F2 | Trails off/on | Returns, route utilization and acquired food |
| F3 | Memory off/on | Revisits, deviations and failures |
| N1 | Sufficient/limited protein | Actual protein inflow and brood state; no unsourced growth |
| N2 | Receiver crop capacity absent/present | Actual transfer and both inventories |
| G1 | Single/overlapping excavation | Intersection removal, dry ledger and revision |
| G2 | Same-depth opening versus projected crossing | Navigation matches real clearance |
| S1 | Controlled development threshold | Same AntId, one transition event and consistent population |

These experiment IDs are local to this document; historical N1/N2 in 04/06 have different meanings. Passing P0 establishes tested mechanisms/conservation/causality/reproduction of results, not species calibration. Visual resemblance is not a substitute for scientific validation.
