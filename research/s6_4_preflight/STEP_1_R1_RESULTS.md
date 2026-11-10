# S6.4 Preflight Step 1-R1

The corrections retain the source inventory and the 70-rule historical crosswalk from reviewed commit `e16ccabaf7ad458dd77f35f3f4f1f247e19bd2f5`. The frozen `cpp` tree remains `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. The change is limited to audit code and evidence tables.

## Source anchors

Each mechanism, transition and reviewed Core rule has a primary anchor and can list additional fragments. The 238 primary and 303 supporting anchors name a single function, type, enum or constant per row. Older multi-function ranges are split. General file pointers were replaced with relevant declarations or removed where they added no evidence. The authoritative fragment identifies its owning symbol, precise interval and SHA-256 of the normalized fragment and the whole file. [Anchor registry](SOURCE_ANCHORS.csv)

The validator finds lexical declarations and checks that each fragment lies inside exactly one matching named definition. Missing or ambiguous definitions fail with the anchor and matches in the diagnostic. The first anchor must match the source projection in the owning record. Every supporting reference is verified through the same content and declaration checks. Each semantic relationship is labeled `MANUAL_REVIEW` because membership of a source fragment in a function does not prove a call path or behavioral interpretation.

## Numeric candidate review

The original 3,910 candidate lines, literal tokens, and 220 prior associations are retained. The counts below use one category per candidate **source line**. When a line contains mixed tokens, a behavior-changing modeled value takes precedence and the reason identifies its role. `BIOLOGICAL_PARAMETER` describes how the model uses the value. Scientific support and the existing `ENGINEERING_FIXTURE` provenance are separate fields.

| Category | Lines | Classification boundary |
|---|---:|---|
| `BIOLOGICAL_PARAMETER` | 26 | Includes choice weights, reserve thresholds, the contact-memory function and environmental pulse alternation. Each line links to at least one parameter matrix record with a verified anchor over the line. |
| `ENGINEERING_CONSTANT` | 116 | Admission limits, scheduling floors, indexing envelopes and numerical tolerances. |
| `STRUCTURAL_OR_ALGORITHMIC_CONSTANT` | 398 | Array, geometry, RNG, state encoding and arithmetic conventions. Geometry or algorithm assumptions remain visible in the mechanism inventory. |
| `UNIT_CONVERSION` | 10 | Milliseconds/seconds or permille arithmetic. |
| `FIXTURE_OR_TEST_VALUE` | 3,360 | Application and test source lines. Where lexical binding is available, the ledger links candidate keys while retaining fixture context. |
| `UNRESOLVED` | 0 | The frozen candidate set is fully classified. Runtime resolution of ambiguous fixture expressions remains separate. |

The 249 parameter records already account for all 26 biological candidate lines, so no additional nominal coefficients were required. Eleven fixture member writes still have multiple candidate owners. The lexical candidate set is the one frozen in Step 1. It does not enumerate each possible value of a configuration expression at runtime. [Classified candidates](SOURCE_NUMERIC_CANDIDATES.csv) · [Core classification basis](CORE_NUMERIC_REVIEW.csv) · [Parameter matrix](PARAMETER_EVIDENCE_MATRIX.csv)

## Verification

- GitHub Actions Run 68 completed successfully for `e16ccab`, with five successful jobs covering Windows and Linux Debug/Release and Linux sanitizers. [GitHub Actions Run 68](https://github.com/Aquaticfuller/AntWorld/actions/runs/42841055275)
- The local source audit regenerated the six derived tables and verified the frozen scope, hashes, references and candidate classifications. Seven targeted regression checks passed, including a wrong-function range with a valid recomputed hash, a span crossing functions, ambiguous definitions, missing code and supporting-anchor tampering.

The original inventory report, experiments, scientific judgments and negative results remain in place. The next review step concerns original-paper evidence and keeps mechanism support separate from quantitative calibration.
