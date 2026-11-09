"""Join exhaustive config source expressions to reviewed biological provenance.

No value is silently calibrated. Published endpoints are kept separate from code
coefficients; matching units alone does not establish biological equivalence.
"""
import argparse
import csv
import io
import json
import re
from pathlib import Path

from inventory_s6_3_2 import ROOT, BASE, clean, end_group, expr_value, line_at, split_top

# Each field has an explicit meaning and unit. Group evidence concerns a mechanism,
# never the numerical value of an ENGINEERING_FIXTURE.
GROUPS = {
    'Controls': ('B01 B03 B04', 'Queen contrast arms; not a biological parameter set', 'P01/P02/P03'),
    'IntegratedOptions': ('B07 B08 B20', 'Local nutrition and task sensitivity fixtures', 'P05/P06'),
    'SurfaceConfig': ('B14 B15 B17', 'Paper arena geometry differs from this grid', 'P08'),
    'BehaviorConfig': ('B14 B15 B16 B17 B18', 'Local navigation experiments; chemical doses and observation protocols differ', 'P08'),
    'PositionM': ('', 'Scenario position; no measured-world mapping', 'P10'),
    'FoodMass': ('B03 B07 B10 B11', 'Diet concentrations and wet food are not pure-component depot masses', 'P02/P05'),
    'AntSeed': ('B03 B04 B06 B20', 'Initial population/caste and material carrying assumptions', 'P01/P02'),
    'WorldConfig': ('B08 B14 B17', 'Physical validation bounds and contact geometry are engineering choices', 'P05/P08'),
    'BoxQ': ('B12 B13', 'Quantized cuboid geometry; not a measured nest morphology', 'P09'),
    'GeometryConfig': ('B12 B13 B21', 'B12 surface construction; B13 underground nests; B21 other species', 'P09'),
    'LongTermConfig': ('B07 B08 B12 B13 B20', 'Local feedback hypotheses; no matched parameter measurements', 'P05/P06/P09'),
    'ReproductionConfig': ('B01 B03 B05', 'Founding/established queens; sexual-adult production cost is not egg cost', 'P03'),
    'ResourceCycleConfig': ('', 'Finite external resource bookkeeping; not fitted ecological renewal', 'P10'),
    'PhysiologyConfig': ('B04 B05 B06 B07 B10 B19 B22', 'Caste/stage/temperature and experimental deprivation must be matched', 'P02/P04/P07'),
    'PhysiologySeed': ('B03 B04 B05', 'Available reserves are not whole-body gross combustion energy', 'P02'),
    'SocialConfig': ('B08 B09 B20', 'Temporal local contacts and heterogeneous tasks; no fitted transition hazards', 'P05/P06'),
}

FIELDS = {
    'Controls': '''reserve_mode|category|Maternal maintenance guard arm
laying|boolean|Enable funded reproduction
exchange|boolean|Enable social nutritional exchange
positive|boolean|Adequate-access finite food scenario
absorption_hours|h|Assimilation event spacing
behavior_hours|h|Task decision and holding scale
reproduction_days|d|Egg attempt spacing
lineage_basal|nJ/ms|Queen and inherited offspring maintenance''',
    'IntegratedOptions': '''workers|individuals|Initial worker count
source_protein_ug|ug|Initial available food protein
gift_first|boolean|Prioritize funded donation before depot intake
local_work_continuation|boolean|Maintain Nurse with sampled compatible demand
minimum_program_time|ms|Minimum task holding time''',
    'SurfaceConfig': '''origin_m|m vector|Surface grid origin
width|cells|Surface grid east-west count
height|cells|Surface grid north-south count
cell_size_m|m|Surface cell width''',
    'BehaviorConfig': '''trails_enabled|boolean|Enable pheromone response and deposition
memory_enabled|boolean|Enable experienced food-route memory
sensing_radius_cells|cells|Local food search graph radius
route_capacity|positions|Bound on stored route
max_trip_moves|moves|Trip return cutoff
step_duration|ms|Local movement duration
decision_delay|ms|Delay between movement decision and action
memory_lifetime|ms|Route memory expiry
field_interval|ms|Pheromone field update spacing
trail_half_life_s|s|Scalar field exponential half-life
deposit_units|arbitrary field units|Deposit per loaded movement
trail_cap_units|arbitrary field units|Cell concentration ceiling
trail_cutoff_units|arbitrary field units|Sparse field deletion threshold
explore_weight|dimensionless weight|Unvisited direction baseline
persistence_weight|dimensionless weight|Heading persistence addition
trail_weight|dimensionless weight|Linear response to concentration divided by trail cap''',
    'PositionM': '''x|m|East coordinate
y|m|Up coordinate
z|m|North coordinate''',
    'FoodMass': '''carbs_ug|ug|Explicit carbohydrate component
protein_ug|ug|Explicit protein component
water_ug|ug|Explicit water component
other_ug|ug|Inert other material component''',
    'AntSeed': '''position|m vector|Initial individual position
stage|category|Initial life stage
caste|category|Initial caste
carrying_capacity_ug|ug|Cargo capacity separate from crop''',
    'WorldConfig': '''min_m|m vector|World lower bound
max_m|m vector|World upper bound
max_speed_m_per_s|m/s|Validated movement speed limit
contact_distance_m|m|Maximum candidate contact distance before barrier test''',
    'BoxQ': '''min|geometry quanta vector|Lower cuboid edit bound
max|geometry quanta vector|Upper cuboid edit bound''',
    'GeometryConfig': '''origin_m|m vector|Geometry coordinate origin
quantum_m|m|Geometry length quantum
initial_solid|geometry quanta box|Initial authoritative solid
dry_ug_per_q3|ug/q^3|Dry material density
water_ug_per_q3|ug/q^3|Soil water density
body_half_q|q|Unloaded collision half-extent
loaded_half_q|q|Loaded collision half-extent
reach_q|q|Local excavation and space sensing reach
max_patch_extent_q|q|Maximum edit patch extent
brick_q|q|Derived cache brick size
sample_step_q|q|Derived SDF sample spacing
sdf_band_q|q|Derived SDF band
work_duration|ms|Excavation action duration
move_duration|ms|Underground movement duration
decision_delay|ms|Excavation decision spacing
dig_energy_nj_per_q3|nJ/q^3|Digging energy per volume''',
    'LongTermConfig': '''demand_feedback|boolean|Enable local space demand feedback
protein_recycling|boolean|Return adult crop protein surplus to depot
empty_sites_per_contact|sites/contact|Vacancy demand coefficient
complete_depot_visits|boolean|Force completion of local unloading/recovery visit
post_intake_contact|boolean|Wake donor after funded intake''',
    'ReproductionConfig': '''interval|ms|Spacing of egg attempts
egg_protein_ug|ug/egg|Transferred egg tissue protein
egg_water_ug|ug/egg|Transferred egg body water
egg_energy_nj|nJ/egg|Transferred egg energy reserve
dissipated_energy_nj|nJ/egg|Additional maternal energy dissipation
offspring_carrying_capacity_ug|ug|Offspring adult cargo capacity
maintenance_horizon|ms|Retained maternal maintenance window''',
    'ResourceCycleConfig': '''reserve|ug component vector|Explicit finite unreleased resource reserve
release_limit|ug component vector/pulse|Maximum finite resource release
interval|ms|Resource availability pulse spacing
productive_span|ms|Alternating productivity phase length
cyclic|boolean|Enable alternating release rate
low_productivity_permille|per mille|Low-phase release fraction''',
    'PhysiologyConfig': '''absorption_period|ms|Crop-to-body uptake event spacing
egg_duration|ms|Embryonic progress threshold
larva_duration|ms|Larval progress threshold after protein requirement
pupa_duration|ms|Pupal progress threshold
crop_capacity_ug|ug|Combined crop component capacity
hydration_capacity_ug|ug|Body water capacity
energy_capacity_nj|nJ|Usable body energy capacity
carbohydrate_yield_nj_per_ug|nJ/ug|Energy credited per oxidized carbohydrate
basal_nj_per_ms|nJ/ms|Continuous maintenance rate
active_nj_per_ms|nJ/ms|Extra rate while an active program is assigned
water_loss_ug_per_period|ug/period|Body water loss amount
carb_absorption_ug_per_s|ug/s|Carbohydrate uptake rate ceiling
water_absorption_ug_per_s|ug/s|Water uptake rate ceiling
protein_absorption_ug_per_s|ug/s|Larval tissue protein incorporation ceiling
larval_protein_requirement_ug|ug|Tissue threshold allowing larval progress
transfer_limit_ug|ug/action|Nutritional transfer mass ceiling
behavior_interval|ms|Individual nutrition behavior wake spacing
water_loss_period|ms|Water loss reference period
adult_protein_target_ug|ug|Adult retained crop protein target''',
    'PhysiologySeed': '''crop|ug component vector|Initial explicit crop stores
body_energy_nj|nJ|Initial usable body energy
hydration_ug|ug|Initial body water
tissue_protein_ug|ug|Initial incorporated tissue protein''',
    'SocialConfig': '''demand_sensitive|boolean|Use contact-compatible nutritional need
bounded_contacts|boolean|Use bounded rather than exhaustive encounter candidates
exchange_enabled|boolean|Enable local trophallaxis
encounter_budget|candidates/decision|Maximum sampled contact ranks
decision_interval|ms|Autonomy decision spacing
minimum_program_time|ms|Minimum task duration
rest_weight|dimensionless weight|Eligible Rest draw weight
forage_weight|dimensionless weight|Eligible Forage draw weight
nurse_weight|dimensionless weight|Eligible Nurse draw weight
excavate_weight|dimensionless weight|Eligible Excavate draw weight
gift_first|boolean|Offer compatible crop before intake
local_work_continuation|boolean|Continue funded local nursing''',
}

REFS = {
 'B01': ('10.1111/1365-2435.14536','Methods 2.1-2.2; Results 3.1-3.8; Figs 1-4','A'),
 'B03': ('10.1093/biolinnean/blad149','pp 397-401; Methods; Figs 1-3','A'),
 'B04': ('10.1111/mec.70127','Methods 2.2-2.4; Table 1; Fig 1','A'),
 'B05': ('10.1007/BF00299234','pp 21-25; Table 2 p 23; Table 3','A'),
 'B06': ('10.1023/B:JOEY.0000033808.45455.75','Table 2 p 169; Methods pp 166-168','A'),
 'B07': ('10.1002/ece3.6520','Methods 2.1-2.4; Results 3.1-3.4','A/B; isotope transfer is L. neoniger'),
 'B08': ('10.1038/s41598-019-52019-6','Methods; Figs 2-5; Results','A'),
 'B09': ('10.1038/s41598-022-26515-1','Methods; Fig 1; Results','A'),
 'B10': ('10.1098/rspb.2012.0051','Methods; Figs 1-4','A'),
 'B11': ('10.1038/s41598-025-06406-x','Methods; Figs 2-5','A'),
 'B12': ('10.1073/pnas.1509829113','Figs 1-3; Materials and Methods','A'),
 'B13': ('10.1111/1365-2656.14040','Methods 2.1-2.4; Figs 2-5','A'),
 'B14': ('10.1111/eth.12248','Methods; Figs 2-3','A'),
 'B15': ('10.1098/rsbl.2011.0067','Methods; Fig 1; Results','A'),
 'B16': ('10.1371/journal.pone.0149720','Methods; Figs 2-6','A'),
 'B17': ('10.1007/s00040-026-01106-9','PDF pp 3-5; Figs 2-3','A'),
 'B18': ('10.1098/rsif.2012.1009','pp 2-4; Figs 1-2','A'),
 'B19': ('10.1016/j.exger.2016.09.008','Methods; Fig 2; Results','A'),
 'B20': ('10.1111/j.1439-0310.1983.tb00088.x','pp 214-216; Fig 6 p 226; pp 229-230','A'),
 'B21': ('10.1098/rsif.2022.0597','Methods; Figs 1-3','C; Solenopsis invicta'),
 'B22': ('10.1021/ja01876a028','NIST sucrose condensed-phase thermochemistry entry; original pp 1720-1723 not accessed','C; chemistry compilation'),
}

SPECIAL = {
 'PhysiologyConfig.egg_duration': ('B06', 'L. niger population-specific means 14.1-53.7 d across 17.1-26.8 C; see measurements.csv', 'High: fixed threshold; current seven-day aggregate is outside measured magnitude'),
 'PhysiologyConfig.larva_duration': ('B06', 'Larval means 8.4-23.3 d across productive treatments; no workers at 17 C', 'High: full-protein gate and clock confound growth and temperature'),
 'PhysiologyConfig.pupa_duration': ('B06', 'Prepupa+pupa means 12.3-26 d; current stage boundary not identical', 'High: stage endpoint mapping required'),
 'PhysiologyConfig.basal_nj_per_ms': ('B04 B05', 'Sexual adult queen 5.18 +/- 1.06 uL O2/individual/h at 20 C; mass-adjusted RMR is a different endpoint', 'High: depletion time inversely proportional at fixed reserve; S6.3.1 rate arms retained'),
 'PhysiologyConfig.carbohydrate_yield_nj_per_ug': ('B22', 'Gross solid sucrose combustion about 16.49 kJ/g; not measured net ant assimilation', 'High: current 1000000 nJ/ug = 1 kJ/g; no automatic 16.49x replacement'),
 'PhysiologyConfig.energy_capacity_nj': ('B04 B05', 'Mature sexual queen gross body energy about 426 J; NOT available metabolic reserve', 'High: reserve compartment missing; 2 J cannot be calibrated from whole-body calorimetry'),
 'ReproductionConfig.maintenance_horizon': ('B01 B03', 'No measured two-day maintenance window identified', 'S6.3.1 compares zero / interval / absorption / twice interval; survival sensitivity is not calibration'),
 'ReproductionConfig.egg_energy_nj': ('B05', '689 J reported cost of producing a mature sexual queen is NOT cost of one egg', 'High: maternal depletion and offspring energy coupled; retain conservation'),
 'BehaviorConfig.trail_half_life_s': ('B14 B17', 'No matched measured concentration half-life extracted; gland extract dose is not field units', 'Uncalibrated; test spatial decay and direction separately before fitting'),
 'SocialConfig.encounter_budget': ('B08', '53.4 +/- 5.2 workers/group; 99 +/- 17.4 observed events/group; event definition >5 s', 'Computational budget, not observed contact rate; heterogeneous local network missing'),
}


def metadata():
    out = {}
    for owner, block in FIELDS.items():
        for line in block.splitlines():
            field, unit, meaning = line.split('|')
            key = owner+'.'+field
            refs, conditions, proposal = GROUPS[owner]
            measured = 'No directly matching numerical measurement extracted'
            sensitivity = 'NOT MEASURED for this coefficient; freeze isolated variation before fitting'
            if key in SPECIAL:
                refs, measured, sensitivity = SPECIAL[key]
            out[key] = dict(unit=unit, biological_meaning=meaning, references=refs,
                doi='; '.join(REFS[r][0] for r in refs.split()),
                page_figure='; '.join(r+': '+REFS[r][1] for r in refs.split()),
                experimental_conditions=conditions+'; full conditions in BIOLOGY_REFERENCES.md',
                measured_value_or_range=measured, evidence_grade='D',
                related_evidence_grade='; '.join(r+': '+REFS[r][2] for r in refs.split()) or 'D',
                adopted_reason='ENGINEERING_FIXTURE; bounded reproducible implementation, not biological calibration',
                sensitivity=sensitivity, modification_status='PROPOSED REVIEW ONLY: '+proposal)
    return out


def supplemental():
    """Retain fixture defaults/constants, numeric declaration contexts and JSON leaves.

    This deliberately includes non-biological controls. They are labelled as such,
    rather than pretending every integer in a benchmark is a species parameter.
    """
    rows=[]
    rules=[
        ('behavior.cpp','const bool allow_correction', 'sole_predecessor_signal', '1 visible signal', 'Signals', 'Reverse-step exception only for a sole visible predecessor signal', 'P08'),
        ('behavior.cpp','auto weight = (visited', 'visited_weight', '1', 'dimensionless weight', 'Visited site baseline before heading and normalized trail additions', 'P08'),
        ('behavior.cpp','scale = UINT64_C(1) << 20', 'weight_fixed_point', '1048576', 'integer scale', 'Deterministic weight precision; computational not biological', 'P08'),
        ('ecology.cpp','p.body_energy_nj < p.config.energy_capacity_nj / 4', 'urgent_fraction', '0.25', 'fraction', 'Energy or hydration threshold for urgent Rest', 'P06'),
        ('ecology.cpp','sample.ants.size() >= 2', 'space_contact_threshold', '2', 'contacts', 'Minimum sampled neighbors for space demand feedback', 'P09'),
        ('long_term.cpp','after(s.m.now, 1)', 'post_intake_delay', '1', 'ms', 'Post-intake contact scheduling delay', 'P05'),
        ('long_term.cpp','contacts < 2', 'vacancy_contact_threshold', '2', 'contacts', 'Local vacancy feedback activation threshold', 'P09'),
        ('social.cpp','for (int x = -1;', 'contact_bucket_cube', '27', 'buckets', 'Three by three by three spatial candidate buckets', 'P05'),
        ('physiology.cpp','p.crop.total_ug() < p.config.crop_capacity_ug/2', 'intake_fraction', '0.5', 'fraction', 'Depot/cargo intake eligibility below half crop capacity', 'P05'),
    ]
    for filename,anchor,name,value,unit,meaning,proposal in rules:
        path=ROOT/'cpp/src'/filename; raw=path.read_text(encoding='utf-8'); assert anchor in raw,anchor
        rows.append(dict(parameter='Hardcoded.'+name,owner='Hardcoded',field=name,path=path.relative_to(ROOT).as_posix(),line=line_at(raw,raw.index(anchor)),record_kind='HARDCODED_RULE',expression=anchor,static_numeric_value=value,resolution='REVIEWED_EXACT_ANCHOR',variable='',_unit=unit,_meaning=meaning,_proposal=proposal))
    header_rules=[
        ('behavior.hpp','route_storage_capacity = 64','route_storage_capacity','64','positions','Absolute finite route buffer limit','P08'),
        ('behavior.hpp','perception_storage_capacity = 25','perception_storage_capacity','25','cells','Maximum local Manhattan perception buffer','P08'),
        ('geometry.hpp','std::array<PointQ, 64> path','excavation_trace_capacity','64','positions','Finite underground return trace storage','P09'),
        ('physiology.hpp','requested_ug{100}','default_proposed_transfer','100','ug/action','Default externally proposed nutrition amount; actual transfer validates demand and stores','P05'),
    ]
    for filename,anchor,name,value,unit,meaning,proposal in header_rules:
        path=ROOT/'cpp/include/antworld/core'/filename;raw=path.read_text(encoding='utf-8');assert anchor in raw
        rows.append(dict(parameter='Hardcoded.'+name,owner='Hardcoded',field=name,path=path.relative_to(ROOT).as_posix(),line=line_at(raw,raw.index(anchor)),record_kind='HARDCODED_RULE',expression=anchor,static_numeric_value=value,resolution='REVIEWED_EXACT_ANCHOR',variable='',_unit=unit,_meaning=meaning,_proposal=proposal))
    for path in sorted((ROOT/'cpp/apps').glob('*')):
        if path.suffix not in ('.cpp','.hpp'): continue
        raw=path.read_text(encoding='utf-8'); text=clean(raw)
        # Defaults and literal declaration/loop control contexts; source is retained.
        for i,line in enumerate(raw.splitlines(),1):
            masked=text.splitlines()[i-1]
            if re.search(r'\b\d+(?:\.\d+)?\b',masked) and re.search(r'\b(?:constexpr|const|unsigned|int64_t|uint64_t|for|double|float|int|size_t|bool|auto)\b',masked):
                rows.append(dict(parameter='FixtureContext.'+path.stem+'.L'+str(i),owner='FixtureContext',field='source_context',path=path.relative_to(ROOT).as_posix(),line=i,record_kind='FIXTURE_CONTEXT',expression=line.strip(),static_numeric_value='CONTEXT; not a resolved scalar',resolution='MANUAL_CONTEXT_REQUIRED',variable=''))
    def leaves(value,prefix):
        if isinstance(value,dict):
            for k,v in value.items(): yield from leaves(v,prefix+'.'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value): yield from leaves(v,prefix+'['+str(i)+']')
        else: yield prefix,value
    for path in sorted((ROOT/'scenarios').glob('*.json')):
        for key,value in leaves(json.loads(path.read_text(encoding='utf-8')),'Scenario'):
            rows.append(dict(parameter=key,owner='Scenario',field=key,path=path.relative_to(ROOT).as_posix(),line=0,record_kind='JSON_LEAF',expression=json.dumps(value,ensure_ascii=True),static_numeric_value=str(value),resolution='EXACT_JSON_PATH',variable=''))
    return rows


def rendered(rows):
    stream=io.StringIO(newline=''); writer=csv.DictWriter(stream,list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows);return stream.getvalue()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    meta=metadata(); schema=json.loads((BASE/'inventory/schema.json').read_text())
    expected={owner+'.'+f['name'] for owner,fields in schema.items() for f in fields}
    assert set(meta)==expected,(set(meta)-expected,expected-set(meta))
    with (BASE/'inventory/source_parameters.csv').open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    for row in rows:
        row.update(meta[row['parameter']])
        row['context']='REGRESSION_FIXTURE' if '/tests/' in row['path'] else 'APPLICATION_FIXTURE' if '/apps/' in row['path'] else 'CORE_DEFAULT_OR_RULE'
    extras=supplemental()
    for row in extras:
        unit=row.pop('_unit','MIXED; inspect named source expression or JSON key')
        meaning=row.pop('_meaning','Scenario/fixture context; includes algorithm and measurement controls')
        proposal=row.pop('_proposal','Reconcile fixture context before biological use')
        row.update(dict(unit=unit,biological_meaning=meaning,references='',doi='',page_figure='',experimental_conditions='ENGINEERING_FIXTURE or draft scenario metadata; not empirical data',measured_value_or_range='NOT CALIBRATED',evidence_grade='D',related_evidence_grade='D',adopted_reason='Explicit fixture or rule; no biological calibration',sensitivity='NOT MEASURED; do not fit benchmark controls',modification_status='REVIEW: '+proposal,context='FIXTURE_CONTEXT_OR_DRAFT_METADATA'))
        # Match the source-inventory column order.
        rows.append({k:row.get(k,'') for k in rows[0]})
    output=rendered(rows)
    target=ROOT/'PARAMETER_PROVENANCE.csv'
    if args.check:
        assert target.read_text(encoding='utf-8')==output,'provenance drift'
    else:
        target.write_text(output,encoding='utf-8',newline='')
        (BASE/'inventory/fixture_contexts.csv').write_text(rendered(extras),encoding='utf-8',newline='')
    print(f'{"PASS" if args.check else "WROTE"}: {len(expected)} configuration fields; {len(rows)-len(extras)} source expressions; {len(extras)} supplemental fixture/JSON contexts')


if __name__=='__main__': main()
