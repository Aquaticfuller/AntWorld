# S6.3.1 observer contracts and pre-execution clarification

Recorded after frozen protocol 44, before any S6.3.1 diagnostic/control outcome measurement. This document does not authorize a biological correction.

## ADR-631-01: observational decision records

Actual perception decisions can share a timestamp with absorption, birth, death and later action resolution. A snapshot taken one millisecond before/after the whole timestamp is not necessarily the decision's input. Add an optional thread-local host recorder that receives copied scalar diagnostics at the actual autonomy/nutrition/withdrawal decision boundary. It has no callback into the world, no authority to mutate simulation state, and no serialized fields. Disabled recording does no extra perception. Enabled inspection may query the designated queen and physical contact for diagnostics only; those observations never enter choices or RNG.

The harness buffers a whole AdvanceTo call's observations and emits them only after that call commits, joined to actual source scheduled IDs/fact IDs. On failure it discards that call's diagnostic records. These records are marked observer evidence rather than simulated fact events. The full native journal and world byte hashes must be unchanged with observation enabled. No lifetime/caste/fertility rule changes in the diagnostic implementation.

Maternal accounts can be independently reconstructed from the fixed fact codec: start from explicit initialization, settle actual elapsed basal/water expenditure, apply recorded absorption, received gifts, egg tissue/water/energy exports and reproductive dissipation in fact order. Same-time physiological updates precede reproduction. Compare reconstructed reserves with query snapshots at every observed boundary and daily endpoint, rather than inventing unrecorded transfers.

## ADR-631-02: inherited physiology in the metabolic control

Source inspection shows that S6.3 newborns inherit their mother's physiology configuration, including basal metabolism. Protocol 44's wording that the queen-only 2 nJ/ms arm could leave offspring metabolism unchanged is not implementable in the unchanged model. Before running this arm, clarify it as **queen-and-descendant basal metabolism 2 nJ/ms, initial workers 1 nJ/ms**. Preserve the original inheritance rule; do not alter Core merely to make a counterfactual look more selective. Label this arm `lineage_basal_2` and report its coupled offspring effect. The other five sensitivity arms and all numeric amounts/seeds/windows remain unchanged.

This clarification prevents claiming a queen-specific causal estimate from a lineage intervention. No outcome has been inspected to make it, and no rate is selected to improve survival. All rates remain ENGINEERING_FIXTURE.
