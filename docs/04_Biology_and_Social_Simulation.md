# AntWorld biology and colony society (historical v0.3 with v0.7 updates)

The first species is Lasius niger. Not all candidate mechanisms have been directly demonstrated in this species. Identify cross-species assumptions and distinguish observations, inference and engineering approximations.

## Individual rules

The queen is not a commander. Local perception, response thresholds, individual variation, interaction and environmental change produce colony organization. Each ant retains one identity from egg through death. LLM narration is an interpretation layer, never an ant decision system.

Separate high-level tasks (inactivity, exploration, foraging, return, brood care, cleaning, digging/transport, defense/avoidance) from low-level actions (turn, walk, grip, carry, contact, trophallaxis, pheromone deposition, avoidance). A task composes actions rather than forcing everything into one mutually exclusive enum.

A candidate task score is:

`Score_i(a) = base_species(a) + sum_k(weight(a,k) * sensed_i(k)) + persistence_i(a) - threshold_i(a)`.

Choose probabilistically among legal actions with minimum duration and emergency interruption. This formula is an engineering model, not a proven L. niger neural mechanism.

Perception is limited to reachable sensory distance/contact, local temperature/moisture, walkable-surface pheromone, nearby individuals, food cues, obstacles and learned routes. Never expose all food coordinates. Start pheromones with local deposition and decay, validating whether surface diffusion is needed. Food, existing trails and crowding influence deposition; avoid unconstrained positive feedback. Memory stores limited route/branch/cue associations with reinforcement and forgetting, not exact GPS or language. Species, age and physiology affect tendencies without permanent personality-based occupations.

## Nutrition and life

Separate carbohydrate, protein and water; lipids/micronutrients may follow. Body energy differs from transferable crop contents; carried solid prey is separate. Use consistent units for `dE/dt = P_absorb - P_basal - P_activity`, with explicit absorption efficiency. Hydration follows actual intake/loss; nest humidity is not drinking.

Trophallaxis transfers between contacting individuals, bounded by donor contents and receiver capacity, rather than instantly averaging the colony. Early claustral queens use body reserves; worker provisioning later supports reproduction. Egg, larva, pupa and adult have different nutrition/actions. Development depends on local conditions and intake/reserves. Mortality may depend on age, starvation, dehydration, injury and environment; do not replace it with an unvalidated fixed lifespan timer. Rates and hazards require calibration.

## Nest work and space

Rooms are not predefined functions and workers are not centrally assigned. Local brood, waste, crowding, surfaces, climate and neighbors produce activity zones whose observed use changes over time.

| Task | Cues and actions | Boundary |
|---|---|---|
| Patrol/inactivity | Weak demand, local preference, activity rhythm; short movement, stopping/contact | Inactivity does not automatically mean sleep or laziness |
| Brood care | Nearby brood needs; approach, feed, clean, turn/carry | General ant behavior; calibrate species-specific rates |
| Brood relocation | Unfavorable local climate and a known reachable alternative; carry one individual along a real path | No global optimum coordinates or teleportation |
| Grooming | Contact with contamination/stimuli; clean until contact or need ends | Species mechanisms differ |
| Waste transport | Encounter corpses, leftovers or debris; move to a reachable deposition area | L. niger fecal patches differ from external food/corpse waste |
| Digging/maintenance | Reachable soil, crowding, geometry/climate cues; remove, carry and deposit | Temperature-dependent nest form is evidence; a complete trigger formula is not |
| Defense/avoidance | Local unfamiliar cues, attack or danger; alert, retreat or local fighting | No scripted enemy waves |

Local spaces record geometry, depth, clearance, adjacency, temperature, soil water versus air humidity, water accumulation, optional stability constraints, worker/brood density, food/waste and evidenced construction cues. A brood chamber is a derived usage label; empty geometry and past uses persist.

A candidate brood-location quality is `Q_brood(r,stage)=f(temperature,humidity,crowding,accessibility,hazard)`. Workers compare current and locally visited/remembered places, not the global map. Brood physiology uses its real local environment; relocation requires pickup, connected travel and placement.

## Digging and material transport

Candidate stimulus: `DigStimulus_i(x)=f(available_soil,local_crowding,nearby_brood,microclimate,structure_cue,prior_activity)`; candidate start probability: `sigmoid(a_i*DigStimulus_i-threshold_i)`.

Reach an actual soil interface, remove a small amount of material, enlarge the void, create a carried soil parcel/batch, travel and deposit, then update navigation and derived mesh. Respect capacity, effort, energy and negative feedback as space becomes sufficient or demand declines. Do not provide colony-wide room blueprints. Test material conservation and legal reachability.

Acromyrmex lundi brood/fungus relocation experiments are hypotheses for comparison, not direct evidence of L. niger excavation triggers. L. niger has independent local construction and temperature/nest studies. Deposition construction and underground removal are distinct processes.

## Cleaning, inactivity and networks

Corpses, leftovers, soil and fecal patches are different material types. A minimal cleaning loop discovers, transports and changes local contamination state. Do not mandate that every excretion leaves the nest. Pathogen spread requires a separate validated model; an arbitrary dirty-equals-death rule is insufficient.

Inactive ants still metabolize and respond locally. Age, nutrition, position and stimuli affect activity; other species' persistent inactive fractions are not universal L. niger constants. Circadian/seasonal patterns must not force synchronized schedules on every ant.

Record actual antennal contact, trophallaxis, care or cooperation. Co-location is a different statistic. Spatial fidelity affects encounters and opportunities. The well-known large contact-tracking study concerns Camponotus fellah, not direct L. niger evidence.

## Example 3D scenario

A young colony has brood, workers and reachable soil. Local temperature becomes unfavorable; workers carry brood through real tunnels to a known better location. Local demand/crowding may then trigger digging (a model hypothesis), soil is transported and spaces gradually expand. Geometry and activity determine usage labels. Population and seasonal changes may later reorganize use.

## Initial experiments (local identifiers from this document)

| ID | Manipulation | Measurements / prohibited shortcut |
|---|---|---|
| N1 | Local temperature/moisture | Relocation fraction, latency and destination; no global optimum oracle |
| N2 | Brood count | Contact, feeding and transport frequency; no fixed centrally assigned carers |
| N3 | Active workers and void volume | Soil moved and volume per ant; no unlimited linear digging |
| N4 | Geometry/local cues at fixed soil front | Clustering and tunnel form; no room blueprint |
| N5 | Leftovers/corpses | Cleaning latency and deposition; no teleporting waste |
| N6 | Crowding/connectivity | Contact networks, allocation and bottlenecks |
| N7 | No new stimuli | Inactivity, energy and later response; no forced universal labor/sleep |

Run multiple seeds and check identity, material balance, connectivity and time acceleration. Without quantitative evidence, test directional responses without claiming calibrated rates. These historical N labels differ from document 21; always include source context.

## Observations and unknown parameters

Expose space users, active workers, brood density, local climate, excavation/transport mass, task-duration fractions, relocation routes, seasonal depth/use and flows/bottlenecks. GM may report that brood care concentrated deeper; attributing this to temperature requires supporting observations and a stronger causal design.

Uncalibrated quantities include sensory range, stage-specific environmental preferences, thresholds and their dependence on age/nutrition, transfer/cleaning/carrying/digging duration and cost, soil rates and density feedback, task-switch inhibition, heat/moisture transport, flooding and structural stability. Every number needs source and unit metadata.

Document 09 defines how a biological digging request changes physical space. L. niger deposition studies do not establish a universal digging formula; soil-column studies support climate-related form and possible backfill but not a complete individual algorithm. Fire-ant collisions and leaf-cutter soil preferences are cross-species candidates. Biology emits proposals, never Unity mesh calls.

v0.7 unifies proposals and commits, physical-time integration with threshold boundaries, stable diffusion steps where applicable, persistent L2 identity and honest sparse history. Test mechanism, direction and conservation first; species calibration remains separate.
