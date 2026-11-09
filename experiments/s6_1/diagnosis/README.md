# S6.1 baseline diagnosis before corrections

Frozen protocol: document 37, commit `03ae833`. Original biological source: reviewed S6 `2505f53` (C++ identical to `3636f22`). This directory preserves a reconstruction of every canonical 159-byte fact from the original seed-7 SQLite databases. The 63,143-fact 600 s history is an exact binary prefix of the 66,658-fact 1,800 s history. `baseline_trace.json` records SHA-256 hashes, all fact-kind counts, donor totals and reconciled inventories. `seed7_complete_events.csv` has every decoded fact, including failures and decisions. `seed7_nursing_timeline.csv` adds observer-reconstructed inventory and program age; these fields are never policy inputs.

The original result is reproduced: 45 deaths, five cumulative brood emergences, seven original brood without emergence, 1,549 ug retained crop protein and 651 ug tissue protein. All 2,200 introduced protein micrograms remain accounted for; 200 ug was declared initial pupal tissue.

## Established event sequence

- Workers 19 and 20 become Nurses at 15,000 ms after Rest, then switch to Forage at 25,000 ms, exactly the 10,000 ms minimum. Each has made ten nest intakes starting at 14,009 ms, holds 222 ug crop protein at departure, has made no gift, and retains that protein at death.
- Worker 21 becomes Nurse at 15,000 ms; workers 30 and 31 at 20,000 and 15,000 ms. All switch to Forage at 35,000 ms. They make 19/19/18 nest intakes and only one protein gift each (54/55/53 ug), retaining 368/368/347 ug crop protein respectively at departure and death.
- The nurse wake's existing half-crop refill branch precedes encounter sampling. Water/carbohydrate absorption continually frees crop capacity, so possessing substantial protein does not stop repeated mixed-food intake. A NutritionDecision does not prove that a recipient was sampled or fed.
- The original autonomous decision resamples Rest/Forage/Nurse/Excavate after the minimum duration. A local demand cue adds a Nurse option but does not preserve existing compatible nursing work. Forage/excavation travel ownership then requires an actual depot return for a routine change, which can delay renewed feeding. No global deficit or hidden food source is involved.

These facts justify separate gift-priority and local-work-continuation ablations, not an arbitrary increase in a nursing weight. Observer replay will additionally expose the actual deterministic local sample at each autonomy timestamp and verify that observation leaves the complete fact stream unchanged. Sampling limitations and unreachable demand remain possible contributing mechanisms; the baseline event journal alone does not encode every contact candidate.

The high active-program fraction and identical resource-treatment excavation volumes will be analyzed through program residence, legal reconsideration opportunities and timing of actual initial excavation. They are not assumed to be a physiology defect, nor evidence of biological nest-demand regulation.
