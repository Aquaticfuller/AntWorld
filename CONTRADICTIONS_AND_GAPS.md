# Contradictions, negative evidence and gaps

These issues constrain interpretation; they are not silently repaired source data. IDs refer to the [source register](research/s6_3_2_1/SOURCE_READING_REGISTER.csv), [measurements](research/s6_3_2_1/MEASUREMENTS.csv) and [code audit](STATE_MACHINE_EVIDENCE_AUDIT.md). `UNKNOWN` means unknown in the retrieved evidence, not proof that nobody has studied the topic.

## Conflicts between model and experiment

| ID | Evidence and location | Actual model restriction | Consequence |
|---|---|---|---|
| C01 | B01 Methods2.2/Results3.1–3.8/Figs1–4; B02 retrieval Methods2.1–2.3 | Q01/S16: Queen cannot activate care/autonomy; normal state Paused | Complete founding queen biology cannot be claimed; worker appearance/removal changes real care |
| C02 | B06 Table2 p169 and Table5, population-specific first brood | L05/L06: supplied tissue followed by2/3/2-day clocks, no temperature | Seven-day development is a fixture, not a real-time calibrated lifecycle |
| C03 | B01 brood effects; B03 pp398–400 diet/condition | Q03/Q05: fixed attempts plus two-day maintenance guard | Guard is a local engineering safeguard, not a measured reproductive response |
| C04 | B18 crowding; N14 pp118–120; N20 Results | F11: every loaded successful move deposits fixed amount; no outward marking | Context-dependent signal production is missing; following a signal is separate from producing it |
| C05 | B04 Table1/Fig1; B05 Table2 p23; N27 Table1 p5 | Q07/L01–L04: shared stage/caste settings and no mass/lipid compartments | No credible homogeneous caste-rate calibration; allometry is not a fixed queen/worker ratio |
| C06 | B08 contact network; N01 Tables1–2; B20 activity | S01/S07/S11/S17: candidate budget, weighted programs and instant transfers | Program residence is not measured active time; contact count is not transferred nutrient mass |

## Within-source or cross-source interpretation problems

| ID | Locator | Preserved problem | Treatment in atlas |
|---|---|---|---|
| U01 | B04 Methods versus Table1 | 6/22 queens/worker-pools in Methods versus8/24 in table | Keep source-specific sample descriptions; do not manufacture a combined N |
| U02 | B04 Fig1/Methods and N27 Results3.2 p6 | Exponents used for normalization are fitted across three species, including pooled workers | Mixed-species fit labelled D; no within-L. niger exponent adopted |
| U03 | B05 Table2 p23; B06 Table2 p169 | Sexual-stage energy is not egg energy; B06 error type not securely established | Preserve endpoint and unspecified error; no egg-cost or invented SE target |
| U04 | N01 hazard table/replicate descriptions | Some printed CI/point estimates and replicate labels conflict | Timing observations retained; problematic fitted hazards not adopted |
| U05 | N04 Results | 21 nests,41 toilets and reported mean2.32 are not mutually arithmetically consistent | Do not derive an exact universal per-nest rate |
| U06 | N09 Results | Reported chi-square,df and p are inconsistent | No exact probability coefficient inferred |
| U07 | N07 Results p7/discussion and viscosity workbook | Least-viscous value labelled mPa*s conflicts with Pa*s elsewhere/raw workbook | No corrected viscosity coefficient silently adopted; solvent/CHC viscosity is not water-loss mass |
| U08 | N07 Dryad README versus survival sheet | README says status1=dead,2=alive; file contains0/1, no2 | Preserve codes; likely right-censor interpretation for0 remains explicitly unresolved; no fitted survival curve |
| U09 | N07 drought Methods | Text lists45+48 wet controls but later uses3/90 | Preserve ambiguity; do not calculate a precise control mortality percentage |
| U10 | N14 Methods p116 versus Table1/Fig2 | Four source colonies versus five nests/arm; observation denominators differ | Use endpoint-specific N; do not merge tables or manufacture independent-colony replication |
| U11 | N14 Methods/Table1 | Drinking<5s assigned zero volume; quoted crop maximum/trail lifetime are secondary citations | Zeros are method-limited; intake distributions are not maximum crop capacity or assimilation |
| U12 | N17 Methods/Results pp630–634 | Red lamp heats arena over longer observation, dark arm briefly lit for sampling | First-minute dispersion and long-duration aggregation have different confounds; no sleep parameter |
| U13 | N25 Methods versus Fig2/3 captions | Fine substrate400–560um versus400–450um | Preserve ambiguity; no exact particle-distribution model; projected speed not actual3D distance |
| U14 | N27 Table1 p5 versus Results3.1 p4 | Worker mean0.99 versus0.98uL/h; listed Clark samples sum65 versus reported66; C.herculeanus queen n6 versus text n7 | Table cells retained, discrepancy flagged; no hidden source correction |
| U15 | N27 Methods2.1 p4 | Stated8.65/0.270=30.58, whereas the stated ratio is about32.04 | Report published outcomes with limitation; instrument conversion cannot be repaired without raw calibration |
| U16 | N27 Fig3/p5 and Results3.3 pp6–7 | Authors exclude grey outliers; devices differ in temperature; RQ unreliable | Source estimates are not an unbiased matched-device comparison; no substrate/energy fitting |
| U17 | N12 bibliographic page versus official DOI | Printed v62i3 identifier differs from official v62i4.818 | Verified official DOI retained; L.japonicus remains separate from target |
| U18 | N26 raw TSV codes | Ln is L.neglectus; Lni is L.niger | Explicit code mapping; never pool target and invasive Lasius |

## Negative results that remain evidence

N08's *L. niger* aggression response is nonsignificant under its treatment while another Lasius response differs. N10 does not establish a universal dormancy metabolic reduction. N14's marking-intensity contrast is nonsignificant despite differences in participation. N25's free-path contrast and tested texture learning/preference are nonsignificant. N27's isolated mixed-worker gas/activity observations show no supported circadian effect. These are assay-limited nulls, not proofs of biological impossibility.

The complete previous simulator archives remain: short initial trail following and weak recruitment; S6.1 scarcity emergence/transfer tradeoffs; high program-active residence; equal excavation under some food contrasts; queen deaths in every ordinary32 and adequate-access8 S6.3.1 seed; and all finite-resource declines. The 32-worker supplied180-day survivor fixture does not rescue those failures. Earlier performance failures6.315x/8.154x and the unexplained24.229x batch remain alongside later controlled qualification. No adverse result is removed or ascribed to an unmeasured cause.

## Major unresolved measurements

The coverage register contains84 explicitly scoped slots. High-priority unknowns are individual egg wet/dry mass and protein/water/net energetic cost; gut absorption and crop-to-body kinetics; queen-directed transferred mass; body lipid mobilization through founding; individual worker mass/age distributions; instar-specific growth, molt and mortality; callow maturation; water ingestion/loss by caste and stage; occupied chamber microclimate and soil water-potential responses; photoperiod/diapause entry in *L. niger*; male postflight hazards; and local triggers/termination distributions for grooming, maintenance, water management and defense.

N03 remains first-page-only. Additional papers may narrow these gaps, but institutional subscription access was not successfully automated; user-provided publisher PDFs resolved the main blocked sources. [Channel access](research/s6_3_2_1/channel_access.json) and44 recorded searches expose that limitation. This is not a PRISMA-complete search, not a claim of database-wide citation exhaustion, and not a reason to invent values. Proposals must isolate mechanisms and freeze independent comparisons before any later fitting.
