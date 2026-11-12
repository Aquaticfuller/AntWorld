# F1 checkpoint and fact contract

F1 enrollment is atomic at simulation setup. A single immutable version 1 `FoundingProfile` admits one living adult queen in an integrated-care world. A separately journaled reserve record belongs to that identity and each funded offspring. The five 64-bit values store owned lipid, spent lipid, mobile maternal protein, energy carry and water carry. The fixed denominator is 86,400,000 ms per day. `WorldRuntime::query_founding` projects the carries at the requested cut without creating a refill, drawing a random number or changing the world.

F1 uses `AWCKPTF\0`, schema 15, physics 17 and RNG version 1. After that header it records the exact legacy feature discriminator, including the optional continuous-spatial discriminator. Its ordinary world fields retain their existing meanings. A suffix after the connector section encodes profile version, population, founder ID, stage schedules and inputs, then sorted reserve rows. An `AWSTATE1` frame also contains a canonical prefix digest. The simulation updates that digest on commits and rolls it back with the owning transaction. SQLite still links the frame to a SHA-256-verified chain, publishes it atomically and retains prior anchors.

| Fact | Actor | `payload` | `random_value` | FoodMass |
|---|---|---|---|---|
| `FoundingConfigured` | None | Digest of exact immutable setup | Profile version | Empty |
| `FoundingReserveSeeded` | Foundress | Introduced lipid µg | Zero | Mobile protein and body water µg |
| `FoundingEggFunded` | Foundress | Offspring ID | Transferred lipid µg | Empty. Protein and water are carried by the matching `AntBorn`. |
| `FoundingLipidConverted` | Fuel owner | Spent lipid µg | Credited nJ | Empty |
| `FoundingRation` | Foundress | Larva ID | Transferred lipid µg | Actual protein and water delivered to crop |

No new field extends the 159-byte canonical payload. The existing 210-byte observation layout remains intact. A candidate `AntBorn` has zero `random_value`. Its initial energy is reconstructed from the immediately following conversion of the transferred lipid. A positive maternal ration precedes its matching `FeedBrood` completion observation. The observation reports action evidence and does not introduce a second material credit. A zero/rejected act uses the ordinary failure outcome. `PhysiologyUpdated` can witness a capped developmental wait at a non-pulse boundary with zero crop uptake. At a coincident live pulse and stage transition, the pulse and its positive conversion precede `StageChanged` under the same scheduled source. Death takes priority over either.

The segmented archive emits `AWFACT02` blocks for F1 publications, with block version 2, zlib codec 1 and fact schema 2. Historical `AWFACT01` blocks remain readable and byte-identical. The old flat SQLite writer rejects F1. Typed participant extraction indexes both mother and child for egg and ration records. The frame verifier reconstructs real input, payouts, refills, absorption, stage margins and the history of spatial obstructions, and compares the result to the stored reserve and ordinary physiology rows. New typed events require the corresponding committed action or pulse and legal endpoints. Old readers reject the new frame or block discriminators. No SQLite table or existing payload semantics change.

## Technical wall probe note

The first pre-collection engineering probe attempted to walk the foundress around the test wall after egg laying. The existing external movement contract rejects that caste. The runnable probe uses two explicitly seeded legacy assay larvae at the same 1.5 mm distance, one reachable and one occluded. It checks reach and recorded care opportunities without moving the mother or changing a caste rule. Neither larva has a maternal birth ID or contributes to the F1 founding denominator. The probes retain the original experimental egg placement at the actual mother's position. This tests the existing wall mechanism, with F1-specific dosing checked separately on actual funded offspring. The failed engineering probe and its command inputs are retained with the new results. No ordinary case or acceptance rule changed.
