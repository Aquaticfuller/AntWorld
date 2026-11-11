# RM-02 Phase 0 evidence readiness and observability

| Decision | Status |
| --- | --- |
| Phase 0 design | **RM02_OBSERVER_PROPOSAL_READY** for independent design review. The proposed first implementation is a read-only host reader. |
| BR-02 evidence | **RM02_EVIDENCE_INSUFFICIENT** for identification, fitting or adoption of a new model. BR-02 remains BLOCKED. |
| RM-01 | Complete engineering acceptance at `c9065759bed1b324d99cc606015d59601ac97b0a` is retained. BR-04 remains BIOLOGICAL_NOT_VALIDATED and BLOCKED. |

## Baseline and scope

The reviewed C++ tree is `2b9d475fdb0d657dc87e46755d6511779da0c8b4`. The accepted RM-01 functional and performance evidence, Core CI and original tests apply to this tree. TD-01 measured 5.4193707895× and TD-08 measured 4.2430342161× under the inherited ≤6× gate. Phase 2 identifies BR-02 as a gap between access, selection, delivery and assimilation. Phase 3 defines the independent `VAL-BR-02` data gate. Phase 4 marks RM-02 `HOLD_FOR_EVIDENCE_AND_APPROVAL` and biological adoption `BLOCKED`. The present authorization covers research, analysis and design. The branch's only tracked additions are this research package. [Accepted Core CI](https://github.com/Aquaticfuller/AntWorld/actions/runs/43069249853) [RM-01-R1 results](../s6_4_rm01/RM01_R1_PERFORMANCE_QUALIFICATION.md) [Phase 2](../s6_4_preflight/S6_4_PHASE2_PRIORITY_REPORT.md) [Phase 3](../s6_4_preflight/S6_4_PHASE3_RESULTS.md) [Phase 4](../s6_4_preflight/S6_4_PHASE4_RESULTS.md) [Authorization matrix](../s6_4_preflight/S6_4_PHASE4_IMPLEMENTATION_AUTHORIZATION_MATRIX.csv)

## Findings and review material

- The Core grants local reach and then evaluates exact modeled recipient stores. It selects among sampled eligible recipients. A scheduled action is followed by a second set of contact, stage, capacity and demand checks. The 100 ug fixture request is a ceiling. Successful gifts credit the crop and periodic assimilation credits energy, body water or larval tissue. These are separately observable quantities. The audit and matrix cover 27 source transitions and observation boundaries. [Core audit](CORE_SOURCE_AUDIT.md) [Source–model–evidence matrix](SOURCE_MODEL_EVIDENCE_MATRIX.csv)
- The 50 parameter rows copy the accepted source values, units and provenance and link their RM-02 roles to the source matrix. The rule-basis labels in the source matrix annotate the audited substeps. Accepted mechanism, source and parameter classifications are taken from their original registers. [Parameter crosswalk](PARAMETER_EVIDENCE_CROSSWALK.csv) [Accepted evidence](../s6_4_preflight/README.md)
- B08 and N01 support measured worker oral contacts under their specific methods. The B08 workbook scan count is 1,324 and the published Table S1 reports 495 events. The descriptive collapses give 492 or 493, depending on retained duplicate onset rows. N01's 0.6 uL measures a separate forager meal. B07's focal data measure offered diet and colony outcomes. Its pooled tracer assay is in `L. neoniger` and lacks individual crop-to-body timing. No reviewed focal asset links available alternatives, actual positive and zero transfer amounts and body uptake. [Data review](DATA_READINESS.md) [Reproducible input receipt](PRIMARY_ASSET_RECEIPT.json)
- The proposal reuses committed facts and detached queries, retains exact timestamps and source IDs, and labels reconstruction or missing fields. A small engineering assay can test read-only invariance, recovery and zero/rejected outcomes. Complete risk sets and precise sub-cut snapshots in all profiles would need further review of narrowly bounded diagnostics. [Observer design and budgets](OBSERVER_DESIGN.md)
- The prospective protocol specifies separate opportunity, positive-dose and uptake endpoints, source-colony splits, assay calibration, failure retention and validation decisions. No currently reviewed dataset meets the full independent specification. [Validation protocol](VALIDATION_PROTOCOL.md)

## Risk and blocker register

| Risk | Consequence | Current disposition and next evidence |
| --- | --- | --- |
| Exact internal recipient signal | Apparent preference can come from access, donor state, crop room or an untested cue. | BLOCKED for biological inference. Obtain time-aligned available alternatives and independently measured state/cues in matched contrasts. |
| Contact denominator and dose | B08/N01 oral bouts, repeated scan rows, work counters and actual gifts have different denominators. An absent event cannot be scored as a measured zero. | BLOCKED for choice/transfer fit. Retain unknown categories and acquire measured positive, zero and failed cases. Reconcile author annotations before quantitative B08 event matching. |
| Mixed crop, pulse and expenditure | A later pulse can use older or mixed stores. Crop decline can reflect onward transfer or other loss. Cohort enrichment and final colony size can mask mismatched mechanisms. | BLOCKED for uptake fit. Use verified delivered dose and separate timed crop/body measurements with independent loss and metabolic controls. |
| Same-time resolution, cancellation and care duplication | A final cut can hide competing actions and repeated use of a source ID. A generic rejection may lack the target. | Design covers order and coverage. Require exact canonical parity and replay, retain unknown terminal provenance and count each actual gift once. |
| Observer failure, memory and export cost | Existing targeted inspection can throw before a commit. Unbounded logs can change resource pressure and lose evidence. | Design proposes paged host reads and bounded sidecar capacity. The on/off, fault, restore and overhead tests await implementation approval and measurement. |
| Independent holdout missing | Current source comparisons cannot establish BR-02 biological validity. | `VAL-BR-02` is prospective. Register complete independent source-colony blocks and freeze margins and data splits before analysis. |

## Executed verification

The local pinned primary-asset audit was reproduced against its tracked receipt. Targeted Release regression reruns passed 15/15 on the existing reviewed build. They covered contact and walls, competing transfers, gift priority and self-maintenance, deterministic partitioning, exchange and rollback, and the existing S6.2/S6.3.1 observers. The original RM-01 read-only verifier reproduced SHA-256 `04557bb0b28ed057692bc832f769a9387f18b62e6f7262a91ffd65f2bf8cc68e`. Source anchors, related transition/parameter IDs and protected baseline paths were verified. New observer engineering trials and independent biological validation are `NOT_RUN`.

Run from the repository root with Python 3 and the previously downloaded assets. The asset audit uses the standard library and prints only aggregate receipt fields.

```powershell
python research/s6_4_rm02/audit_primary_assets.py out/s6_4_preflight/batch1 out/s6_3_2_1/sources/trophallaxis_2011.pdf --check
python tools/verify_s6_4_rm01_results.py experiments/s6_4_rm01/assay --observer experiments/s6_4_rm01/observer
ctest --test-dir build/s6_3_4-release --output-on-failure --parallel 3 -R '^(S3_(EXCHANGE|CONSTRAINTS|REPLAY|ROLLBACK)|S6_(DEMAND|CONCURRENT|CONTACTS|CONTACT_WALL)|S6_1_(GIFT_PRIORITY|SELF_MAINTENANCE|PARTITION|CONTACT_LINKS)|S6_2_(NUTRITION|CHOICE)_OBSERVER|S6_3_1_OBSERVER)$'
git rev-parse 'HEAD:cpp'
git diff --exit-code c9065759bed1b324d99cc606015d59601ac97b0a HEAD -- . ':(exclude)research/s6_4_rm02/**'
```

The decision requested is independent review of the Phase 0 proposal. Observer implementation and any later biological change require their own authorization. The existing independent validation gate remains in force.
