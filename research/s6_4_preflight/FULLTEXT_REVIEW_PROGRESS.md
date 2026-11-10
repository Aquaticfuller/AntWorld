# S6.4 scientific evidence review progress

**Step 1-R1 is complete. Step 2 batch 1 is ready for independent review.** This is an audit of the accepted S6.3.4 Core, whose `cpp` tree is `277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69`. Batch 1 covers brood care, queen provisioning and reproduction, nutrition, physiology, developmental timing, and the perception and observation interfaces used by those mechanisms. The software and its historical scientific results remain at the frozen baseline. [Step 1-R1](STEP_1_R1_RESULTS.md), [accepted storage and recovery baseline](../../S6_3_4_RESULTS.md).

## Scope and current coverage

| Domain | Mechanisms reviewed this batch | Frozen inventory |
|---|---:|---:|
| Perception and information | 2 | 6 |
| Foraging and exploration | 0 | 10 |
| Pheromone and recruitment | 0 | 5 |
| Nutrition and trophallaxis | 8 | 8 |
| Brood care and queen behavior | 12 | 12 |
| Growth and reproduction | 4 | 4 |
| Physiology, energy and water | 5 | 5 |
| Activity, rest and allocation | 0 | 5 |
| Nest and environment | 0 | 8 |
| Lifecycle mortality and colony dynamics | 2 | 6 |
| Shared execution and observation | 6 | 6 |
| Total | 39 | 75 |

The review also covers 53 of 99 frozen transitions and 163 of 249 frozen parameter rows. The parameter scope is the intersection of the Step 1 parameter-to-mechanism links with the 39 selected mechanisms. Shared settings retain their other mechanism IDs. Engineering-only rows cover queue ownership, host limits, observation typing, fixture lifecycle controls and persistence, with no invented biological endpoint. The 36 remaining mechanisms, 46 transitions and 86 parameter rows await later batches. [Mechanism and transition review](MECHANISM_EVIDENCE_REVIEW.csv), [parameter review](PARAMETER_EVIDENCE_REVIEW.csv).

`EvidenceClassification` describes the exact reviewed claim. The 39 mechanisms include 13 `DIRECT_SPECIES_DATA` entries, 18 `MODELING_ASSUMPTION` entries and eight `ENGINEERING_FIXTURE` entries. The 53 transitions include 11, 21 and 21, respectively. Direct entries refer to an observed behavior, contrast, or missing biological state. They do not certify the executable rule. `AtlasSourceGrades` retains the source's A–F grade. `AtlasParameterGrade` retains the separate F grade for current numerical provenance, including where a source is A. The isotope context `B07-X` is separately labeled `CROSS_SPECIES_EXTRAPOLATION`, Atlas C. Of the 163 parameter rows, 82 concern possible biological comparisons and 81 are treated as software representations, inputs, controls or conversions. Seven rows identify condition-specific endpoint comparisons. Zero existing coefficients acquire quantitative calibration.

## Original studies read in this batch

Thirteen original papers were reopened for selected Methods, Results, tables, figures or supporting data. The register has 14 assay contexts because B07 and B07-X use different species. `YES_SELECTED_SECTIONS` identifies reading from the article body and lists the actual scope. It is narrower than cover-to-cover or complete supplement reading.

| Topic | Primary studies and evidence actually used |
|---|---|
| Queen and worker care | B01 Majidifar et al., social manipulations, active-care ethogram and founding-stage egg counts. B02 Walsh et al., retrieval apparatus, cohorts and deposited origin trials. R1L Lenoir, repeated transport, worker role overlap and origin/adoption tests. R1C Carthy, trained loaded return paths and orientation manipulations. [B01](https://doi.org/10.1111/1365-2435.14536), [B02](https://doi.org/10.1002/ece3.4475), [R1L](https://www.dictionnaire-amoureux-des-fourmis.fr/Publications/1981-Lenoir-Sociobiol.pdf), [R1C](https://doi.org/10.1163/156853951X00304) |
| Founding, egg allocation and stored resources | B03 Szabó et al., diet and disturbance controls, first-brood productivity. FT01 Matte and Billen, post-flight histology and sampling schedule. B05 Boomsma and Isaaks, dry tissue calorimetry and developmental oxygen use of sexuals. [B03](https://doi.org/10.1093/biolinnean/blad149), [FT01](https://doi.org/10.20362/am.013003), [B05](https://doi.org/10.1007/BF00299234) |
| Nutrition and trophallaxis | B07 Gutiérrez et al., species-specific colony diet experiments and a separate congener tracer context. B08 Planckaert et al., worker event network and supplementary observations. N01 Buffin et al., defined worker oral contacts under deprivation and different diets. [B07](https://doi.org/10.1002/ece3.6520), [B08](https://doi.org/10.1038/s41598-019-52019-6), [N01](https://doi.org/10.1007/s00040-010-0133-y) |
| Rest physiology and development | B04 Kervella et al., normalized resting oxygen endpoint and table sample sizes. N27 Kervella et al., chamber-specific caste oxygen flux. B06 Kipyatkov et al., controlled founding at different temperatures and stage times in two populations. [B04](https://doi.org/10.1111/mec.70127), [N27](https://doi.org/10.1016/j.jinsphys.2024.104698), [B06](https://doi.org/10.1023/B:JOEY.0000033808.45455.75) |

The ETH Zurich institution-marked publisher PDF of B02, previously supplied by the user, was reopened along with other local original PDFs and current publisher or repository text. ETH and UZH swisscovery lookup attempts returned discovery responses without article content. This record does not count them as newly authenticated downloads. The B01 and B02 deposited data were opened. B08 publisher supplement PDF and workbook were opened. B01 publisher Data S1, B04 and B07 publisher attachments, B03 appendices and separate FT01 electronic material were not verified. B07's Dryad Methods were readable but selected raw downloads did not open. Each access attempt records the route, outcome, scope and hash where local bytes were available. Original papers and supplemental downloads remain outside Git. [Full-text register](SOURCE_FULLTEXT_REGISTER.csv), [access and reading log](SOURCE_ACCESS_AND_READING_LOG.csv).

## Measurements and implications for the source

| Direct quantitative measurement or conditional reference | Source comparison and remaining limit |
|---|---|
| B01 per-queen active-care scans, 6.500%, 0.125% and 6.250% in the three focal conditions. B01 also found opposite effects of larvae on egg counts by founding stage. | Current care matches the direction of social suppression and reversal. Frozen scan residuals persist, and the model lacks the measured stage-dependent reproductive feedback. Neither outcome identifies the contact-memory kernel or a birth threshold. [B1-C01](EVIDENCE_CONFLICTS.md#b1-c01--queen-care-changes-with-worker-access-with-residual-scan-errors), [B1-C03](EVIDENCE_CONFLICTS.md#b1-c03--brood-dependent-egg-production-differs-by-founding-stage) |
| B02 600 s count means 3.772 per queen and 4.850 per first-worker trio, with contact and retrieval markers retained even at the 600 s cap. | The archived line-layout model returned all six items in both arms. Cohort-label and observation-marker discrepancies are retained. This development dataset does not determine pickup or search timing and remains separate from independent validation. [B1-C02](EVIDENCE_CONFLICTS.md#b1-c02--brood-retrieval-count-error-and-marker-alignment) |
| R1C two trained loaded workers, 12 complete normal-light paths, 11.75–29.89 mm/s after recomputing from raw distance and elapsed time. | The 4 mm/s worker target is below that selected range. The comparison does not identify population speed, queen speed, sensory range, or a load ratio. [B1-C09](EVIDENCE_CONFLICTS.md#b1-c09--transport-preference-orientation-and-route-timing) |
| B06 at nominal 25 C, 16.7/15.7 days for eggs and 41.1/39.9 days for complete first-brood development in Borisovka/St Petersburg. | The reviewed long-term fixture uses a 2-day egg timer. There is no temperature or diapause law, and larval and pupal endpoints have explicit definition gaps. Stage-by-population data are available for a future condition-matched comparison. [B1-C05](EVIDENCE_CONFLICTS.md#b1-c05--development-time-and-diapause) |
| N27 at 20 C, 6.15/0.99 uL O2/h for queen/worker by Clark respirometry. B05 supplies a conditional oxygen-to-power assumption. | Conditional 34.34/5.53 uW bounds the scale of adult rest only. Current shared configurable basal and program premiums do not reproduce caste, age, stage or activity dependence. The chemical energy check supplies no absorbed carbohydrate yield. [B1-C07](EVIDENCE_CONFLICTS.md#b1-c07--respiration-chemical-energy-and-the-source-cost-model) |
| N01 29/31 s mean worker contacts under sucrose/protein. B08 99.0 ± 17.4 observed events per group/run. | These endpoints support contact-based exchange, but do not estimate per-act component mass, recipient crop deficits, local candidate count, queen/larva supply, or seconds-to-micrograms conversion. [B1-C06](EVIDENCE_CONFLICTS.md#b1-c06--oral-contact-and-resource-transfer-measure-different-quantities) |
| B03 diet-dependent productivity and FT01 tissue changes over the first 24 days. | The model does not represent usable reserves mobilized from flight muscle. Diet offered, body composition, cumulative sexual development cost and net egg allocation are distinct. Per-egg mass/energy and worker-to-queen flux remain unresolved. [B1-C04](EVIDENCE_CONFLICTS.md#b1-c04--founding-reserve-remobilization-and-single-egg-budgets) |

The first-batch results preserve unresolved B01/B02 validation, SD-04 and SD-08, along with absent water loss and stage-specific assimilation data. Activity and rest, SD-06 construction feedback, SD-01/02 recruitment, broader colony dynamics and durability debt retain their existing status. [Technical debt](../../docs/08_Open_Questions.md), [full conflict register](EVIDENCE_CONFLICTS.md).

## Verification and review boundary

```sh
python tools/audit_s6_4_preflight.py --check
python tools/test_s6_4_preflight.py
python research/s6_4_preflight/verify_batch1.py
python tools/check_repository.py
git diff --exit-code b35b988ecf1b92f7bac3c00af393b88ab8330d67 -- cpp scenarios experiments docs .github
```

The batch checker joins evidence to verified source ranges and reading entries, checks evidence labels and local document links, and recomputes B01, B02 and R1C reference statistics from inherited observations. CI Run 68 passed on the original inventory. CI Run 69 passed on Step 1-R1. Those runs test the frozen Core and its existing tooling. [Run 68](https://github.com/Aquaticfuller/AntWorld/actions/runs/42841055275), [Run 69](https://github.com/Aquaticfuller/AntWorld/actions/runs/42850102141).

Batch 2 remains pending for foraging, exploration, recruitment and the remaining perception rules. Batch 3 remains pending for activity, rest, task allocation, construction, environmental responses, and broader mortality and colony dynamics. This checkpoint awaits independent review before those batches. Species-level calibration and S6.4 Core Readiness have no passing decision in this checkpoint.
