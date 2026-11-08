# S5 metric definitions (version 1)

The table is exported from `antworld_storage` by `antworld_s5_experiment --metrics`.
All samples carry WorldId, owner, simulation time, generation, world revision,
committed EventId cursor and definition version. Owner zero is the world;
other owners are world-qualified ColonyIds. The world total is not another physical inventory.

Gauges are actual committed-boundary observations. Physiology is analytically
settled to that time using pure queries. Dead inventories remain accounted for.
Program counts include only living adults; unconfigured programs are explicitly unspecified.
Flows sum actual committed events in half-open windows `[begin_ms,end_ms)`.
Rejected actions never produce successful transfers. Internal transfers are not
external intake. Seeded identity creation is not an observed biological birth.

`coverage(world)` exposes the latest durable simulation time and evidence cursor.
Flow queries reject missing-world or future windows rather than assert an unobserved
zero. History pages and sampled series return only existing records; empty sample
ranges are missing observations. The latest durable cursor qualifies all results.

Fixed one-minute buckets retain exact count, sum, min, max, last and evidence bounds.
Gauge means are **sample-weighted**, not time-weighted: irregular save intervals
cannot establish continuous exposure. A bucket may be partial at the current
coverage boundary. No interpolation or biological event is inferred between samples.
Zero-valued gauges are observations; absent flow contributions mean zero only inside
the covered history. Foraging success remains **undefined** without a reviewed
trip-completion denominator. No temperature, humidity or semantic chamber statistics
are invented for unimplemented systems.

Integers use exact uint64 quantities. SQLite stores them as canonical 16-digit hex
text, never signed narrowing or approximate SQL SUM. Accumulator overflow rejects
and rolls back the save; this is a declared host arithmetic bound. The derived mean
is floating point and cannot preserve every integer above 2^53. nJ converts to J by
1e-9; ug to kg by 1e-9. Exact geometry q3 converts to m3 by multiplying by the
cube of `coverage(world).geometry_quantum_m`; every observation also retains its
quantum. Geometry metrics describe the world domain, not a fabricated colony-owned
or semantically identified nest. Fixture box volume is exact, with zero integer
integration residual; this does not calibrate the biological geometry model.

Event flows link to their actual EventId. Soil flows additionally require the matching
GeometryEdit, actual volume, parcel and configured dry/water densities. Restored
current gauges, event flows, identity histories and all stored buckets are reconciled
against checkpoint authority or retained raw observations. Historical observation
checksums detect accidental changes after old checkpoint blobs have been retired;
they are not cryptographic signatures or a way to recover a whole world.

| ID | Metric | Kind | Stored unit | Definition |
|---:|---|---|---|---|
|0|population.alive|Gauge|individuals|All living identities, any stage/caste|
|1|population.worker_alive|Gauge|individuals|Living adult workers|
|2|population.queen_alive|Gauge|individuals|Living adult queens|
|3|population.male_alive|Gauge|individuals|Living adult males|
|4|population.egg|Gauge|individuals|Living eggs|
|5|population.larva|Gauge|individuals|Living larvae|
|6|population.pupa|Gauge|individuals|Living pupae|
|7|population.dead_retained|Gauge|individuals|Retained terminal identities; not a window flow|
|8|cargo.carbs|Gauge|ug|Actual cargo including retained dead inventories|
|9|cargo.protein|Gauge|ug|Actual cargo including retained dead inventories|
|10|cargo.water|Gauge|ug|Actual cargo including retained dead inventories|
|11|cargo.other|Gauge|ug|Actual cargo including retained dead inventories|
|12|nest_food.carbs|Gauge|ug|Physical nest stock, excluding crops/cargo|
|13|nest_food.protein|Gauge|ug|Physical nest stock, excluding crops/cargo|
|14|nest_food.water|Gauge|ug|Physical nest stock, excluding crops/cargo|
|15|nest_food.other|Gauge|ug|Physical nest stock, excluding crops/cargo|
|16|crop.carbs|Gauge|ug|Actual crops including dead inventories|
|17|crop.protein|Gauge|ug|Actual crops including dead inventories|
|18|crop.water|Gauge|ug|Actual crops including dead inventories|
|19|crop.other|Gauge|ug|Actual crops including dead inventories|
|20|body.energy|Gauge|nJ|Analytically settled body energy at observation time|
|21|body.water|Gauge|ug|Analytically settled hydration including dead inventory|
|22|body.tissue_protein|Gauge|ug|Retained actual tissue protein|
|23|sink.oxidized_carbs|Gauge|ug|Cumulative actual carbohydrate oxidation|
|24|sink.lost_water|Gauge|ug|Cumulative actual body water loss|
|25|sink.dissipated_energy|Gauge|nJ|Cumulative basal/activity/dig expenditure|
|26|coverage.physiology|Gauge|individuals|Identities with enabled physiology, including dead|
|27|behavior.paused|Gauge|individuals|Living adults with explicit Paused program|
|28|behavior.rest|Gauge|individuals|Living adults with explicit Rest program|
|29|behavior.nurse|Gauge|individuals|Living adults with explicit Nurse program|
|30|behavior.forage|Gauge|individuals|Living adults with enabled foraging program|
|31|behavior.excavate|Gauge|individuals|Living adults with explicit Excavate program|
|32|behavior.unspecified|Gauge|individuals|Living adults without an explicit program|
|33|environment_food.carbs|Gauge|ug|World-only source inventory|
|34|environment_food.protein|Gauge|ug|World-only source inventory|
|35|environment_food.water|Gauge|ug|World-only source inventory|
|36|environment_food.other|Gauge|ug|World-only source inventory|
|37|soil.remaining|Gauge|q3|World-only exact remaining soil volume|
|38|soil.carried|Gauge|q3|World-only actual carried soil volume|
|39|soil.deposited|Gauge|q3|World-only loose deposited soil volume|
|40|nest.void_volume|Gauge|q3|Void inside InitialSolid; m3 = q3 * quantum_m^3; not colony ownership|
|41|geometry.edit_count|Gauge|edits|Complete authoritative edit log length|
|42|life.seeded|Flow|events|Actual AntSeeded facts; not biological births|
|43|life.emerged|Flow|events|Actual Pupa to Adult transitions|
|44|life.deaths|Flow|events|Unique committed deaths|
|45|food.collected_carbs|Flow|ug|External food actually collected|
|46|food.collected_protein|Flow|ug|External food actually collected|
|47|food.collected_water|Flow|ug|External food actually collected|
|48|food.delivered_carbs|Flow|ug|Actual cargo to physical nest stock|
|49|food.delivered_protein|Flow|ug|Actual cargo to physical nest stock|
|50|food.delivered_water|Flow|ug|Actual cargo to physical nest stock|
|51|food.metabolized_carbs|Flow|ug|Carbohydrate actually absorbed/oxidized|
|52|nutrition.internal_transfer|Flow|ug|Actual internal transfer; never counted as external intake|
|53|excavation.dry|Flow|ug|Actual removed dry soil, including repeated remove/fill work|
|54|excavation.water|Flow|ug|Actual removed soil water|
|55|fill.dry|Flow|ug|Actual supplied dry soil filled|
|56|fill.water|Flow|ug|Actual supplied soil water filled|
|57|behavior.moves|Flow|events|Committed moves, not intentions|
|58|behavior.rejected|Flow|events|Rejected outcomes, not ecological success|
|59|behavior.changes|Flow|events|Explicit recorded program changes|
