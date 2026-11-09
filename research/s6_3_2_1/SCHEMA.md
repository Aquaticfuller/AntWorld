# Atlas schema and interpretation contract

CSV/JSON text is UTF-8. SQLite user_version1 uses TEXT values intentionally, preserving original numbers, units, categorical missingness and author-reported inequalities. Numerical analysis must explicitly select valid values and units; never cast UNKNOWN/NA to zero. All dates are acquisition/reading dates, not asserted study dates. Population, caste, stage and sample level are part of every measurement's interpretation.

## Keys and joins

| Table / input | Primary key | Relationships / content |
|---|---|---|
| sources / sources.json | SourceId | DOI unique; title/authors/year, species, conditions, actual reading, pages/figures/tables and limits |
| measurements / measurements.json | RecordId | SourceId FK;292 curated endpoints; includes negative and qualitative records |
| coverage / coverage.json | CoverageId | Frozen84 slots; source join via coverage_sources; explicit missing endpoints |
| behavior_facets / behavior_facets.json | CoverageId | FK to coverage;21 behaviors with trigger/probability/duration/termination/individual-variation distinctions |
| rules / rules.json | RuleId |70 reviewed groups; functions and generated anchors; sources via rules_sources |
| validations / validation.json | ValidationId |20 designs; all DESIGN_ONLY_NOT_RUN; validation_sources |
| parameters / generated matrix | parameter_id |2,559 inventory contexts; parameters_sources links contextual references |
| species | SpeciesId |15 species boundaries; species_sources |
| source_inventory | SourceRuleId | Path,line,function,expression,hash and link precision |
| conversions | ConversionId | Original/derived value/unit, formula, source and uncertainty |
| search_log | search_id | Actual44 searches; query/channel/date and selective leads |
| manual_receipts | ReceiptId | SourceId FK;local document hash,length,actual reading scope; no full text |
| dataset_manifest | CSV | SourceId FK; dataset DOI,source SHA,sheet/header mapping/license |
| raw_n07_survival | RecordId |432 observations; original status,NA and both early-death imputations |
| raw_n10_ctmin | RecordId |289 worker observations, one colony/species |
| raw_n10_lte50 | RecordId |20 published fitted estimates with confidence limits |
| raw_n10_smr | RecordId |57 pooled CO2 metabolic measurements, not individual O2 |
| raw_n10_condition_means | RecordId |20 overlapping summaries; never add as independent replicates |

Raw database rows add SourceId,DatasetDOI,Species,EvidenceGrade,ValueOrigin,License and exact workbook:sheet:row Locator to the unchanged factual CSV columns. The file manifest supplies equivalent traceability for the CSV exports. All cross-reference tables have foreign keys. Indexes support species/stage/measurement, source/locator, parameter family, source path/line and raw species queries. The behavior_evidence, environment_response and physiology_data views partition curated measurements by Domain. unresolved_coverage exposes slots without direct endpoint evidence; direct slots still have a Missing field.

## Grades and origin are independent

- A: quantitative controlled *L. niger* experiment.
- B: direct observational/qualitative *L. niger* evidence.
- C: another *Lasius* species.
- D: other ant species, including Formicinae; mixed-species ant fit.
- E: general physiology/physical theory or other insects.
- F: engineering assumption / unverified model coefficient.

The grade is endpoint-specific. It is not a guarantee of statistical quality or transferability. A published fitted LTe50 may have A-grade study origin while ValueOrigin remains PUBLISHED_FIT. An observational field percentage remains B. Legacy S6.3.2 A–D appears only in explicitly named legacy fields. Current parameter grades are all F; related papers do not calibrate those values.

ValueOrigin differentiates DIRECT_REPORTED_MEASUREMENT, REPOSITORY_MEASUREMENT, PUBLISHED_FIT, PUBLISHED_FIT_CROSS_SPECIES, PRIMARY_QUALITATIVE_RESULT, ABSTRACT_REPORTED_RESULT, TEXT_REPORTED_APPROXIMATION and ENGINEERING_FIXTURE. No DIGITIZED_FROM_FIGURE record exists in this release. If future digitization occurs it needs a new label, method, resolution/error and actual visual inspection.

## Missingness, uncertainty and units

NOT_REPORTED: the extracted endpoint does not provide the field. UNKNOWN: an unresolved quantity or mapping. NOT_APPLICABLE: structurally inapplicable. NOT_STUDIED_IN_RETRIEVED_EVIDENCE: a searched scope has no adopted endpoint. NOT_OBSERVED: no completed endpoint under the source condition; not zero duration. NOT_RECORDED: empty original workbook cell. Literal NA in raw data remains NA. Mean,SD,SE andCI are separate; published unspecified error remains in Uncertainty without relabeling. Approximate source prose remains approximate.

SampleSize may mean ants, colonies, worker pools, repeated exchanges, trajectories or fitted groups; Method and Limitations state the unit. Source rows are not automatically independent samples. Repository condition means are duplicates. Neither simulator random seeds nor repeated observations of the same colony provide independent biological population replication.

Unit conversions live in UNIT_CONVERSIONS separately. No converted quantity overwrites the original. Mass ug, liquid uL, energy J/nJ, power nJ/ms, oxygen uL/h, carbon dioxide uL/h/mg, temperature C and soil quantum volumes must not be mixed. Surface particle size is not soil water potential; RH is not gravimetric moisture. Partial metadata cannot identify missing nutrient composition, absorption efficiency or allometric individual mass.

## Example read-only queries

```sql
SELECT SourceId, ReadingStatus, UsedDataAndLocator FROM sources;
SELECT RecordId, Measurement, Value, Unit, SD, CI, Locator
FROM measurements WHERE SourceId='N27';
SELECT Slot, Status, Missing FROM coverage WHERE Axis='physiology';
SELECT parameter, expression, unit, dimensional_audit
FROM parameters WHERE owner='PhysiologyConfig';
SELECT Species, COUNT(*) FROM raw_n07_survival GROUP BY Species;
SELECT Species, ColonyDormancy, SMR_uL_CO2_per_h_per_mg, Locator
FROM raw_n10_smr WHERE Species='Lasius niger';
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

Numerical grouping or curve fitting requires an additional declared analysis protocol; the examples intentionally do not resolve N07's status conflict or invent unknown error bars.
