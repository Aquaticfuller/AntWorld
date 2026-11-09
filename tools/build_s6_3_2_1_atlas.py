"""Build and validate the review-only ant biology atlas using Python stdlib.

No network, parameter fitting, simulator execution or C++ modification occurs.
Curated JSON is authoritative. CSV and SQLite are reproducible projections.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import csv
import hashlib
import io
import json
import re
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path

from inventory_s6_3_2 import clean, end_group

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'research/s6_3_2_1'
LEGACY = ROOT / 'experiments/s6_3_2/PARAMETER_PROVENANCE_S6_3_2.csv'
BASELINE = '2e1a5fa129821176954f26a88f56791635bc8cda'
SOURCE_FILES = [f'cpp/src/{name}' for name in (
    'behavior.cpp', 'ecology.cpp', 'social.cpp', 'physiology.cpp',
    'long_term.cpp', 'excavation.cpp', 'geometry.cpp', 'world_runtime.cpp',
    'foraging.cpp', 'surface_internal.hpp', 'social_internal.hpp',
    'physiology_internal.hpp', 'long_term_internal.hpp', 'geometry_internal.hpp')]


def digest(value):
    return hashlib.sha256(value.encode('utf-8') if isinstance(value, str) else value).hexdigest()


def read_json(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def csv_text(rows, fields=None):
    if fields is None:
        fields = list(dict.fromkeys(k for row in rows for k in row))
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def source_ids(text):
    return sorted(set(re.findall(r'\b[BN]\d\d\b', text)))


def source_inventory(rules):
    rows = []
    for relative in SOURCE_FILES:
        path = ROOT / relative
        raw = path.read_text(encoding='utf-8')
        masked = clean(raw)
        spans = []
        # Lexical function candidates, not a C++ AST. Every selected source line
        # remains available even when its function cannot be resolved.
        pattern = r'\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?(?:noexcept\s*)?\{'
        for match in re.finditer(pattern, masked):
            if match[1] in {'if', 'for', 'while', 'switch', 'catch'}:
                continue
            start = masked.index('{', match.start(), match.end())
            spans.append((match.start(), end_group(masked, start), match[1]))
        offset = 0
        all_rules = [r['RuleId'] for r in rules if relative in r['SourceFiles'].split(';')]
        for number, (line, visible) in enumerate(zip(raw.splitlines(True), masked.splitlines(True)), 1):
            condition = re.search(r'\b(?:if|else|switch|case|while)\b|\?.*:', visible)
            numeric = re.search(r'(?<![A-Za-z_])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', visible)
            state = re.search(r'\b(?:IndividualBehavior|LifeStage|Caste|ForagingMode|NutritionAction)::', visible)
            if condition or numeric or state:
                active = [s for s in spans if s[0] <= offset < s[1]]
                function = min(active, key=lambda s: s[1]-s[0])[2] if active else 'FILE_SCOPE_OR_UNRESOLVED_LEXICAL'
                specific = [r['RuleId'] for r in rules if relative in r['SourceFiles'].split(';') and function in r.get('Functions', '').split(';')]
                rows.append(dict(SourceRuleId='I-' + digest(relative + ':' + str(number) + ':' + line.strip())[:16],
                    Path=relative, Line=str(number), Function=function, Expression=line.strip(),
                    Kind=';'.join(k for k, present in [('CONDITION',condition),('NUMERIC',numeric),('STATE',state)] if present),
                    RuleIds=' '.join(specific or all_rules), LinkPrecision='FUNCTION' if specific else 'FILE_GROUP_REQUIRES_CONTEXT',
                    EvidenceGrade='F', Classification='SOURCE_EXPRESSION_NOT_AN_EMPIRICAL_PARAMETER',
                    NormalizedLineSHA256=digest(line.rstrip('\r\n'))))
            offset += len(visible)
    return rows


DIMENSIONS = {
 'carbohydrate_yield_nj_per_ug': '1,000,000 nJ/ug = 1 kJ/g. Gross sucrose reference is about16.49 kJ/g; net uptake/oxidation and losses undefined. Do not replace by gross value.',
 'basal_nj_per_ms': '1 nJ/ms = 1 uW. Caste/stage/mass and temperature absent; oxygen-normalized RMR cannot be inserted directly.',
 'active_nj_per_ms': 'nJ/ms is power, applied to task label rather than measured motion. No activity-energy calibration.',
 'energy_capacity_nj': 'nJ/1e9 gives joules. Usable reserve is not gross whole-body combustion energy; missing lipid/body mass compartments.',
 'body_energy_nj': 'Initial usable nJ must be traced to explicit fixture input or maternal transfer; no empirical reserve distribution.',
 'egg_energy_nj': 'Transferred initial offspring reserve in nJ, not the whole metabolic production cost or sexual-adult production energy.',
 'dissipated_energy_nj': 'Maternal nJ/egg dissipated separately from exported egg reserve; no measured L. niger value extracted.',
 'egg_protein_ug': 'Pure protein ug/egg, not wet egg mass; direct egg composition UNKNOWN.',
 'egg_water_ug': 'Water ug/egg; direct egg water composition UNKNOWN.',
 'maintenance_horizon': 'ms multiplies maternal maintenance power/water flux; two-day fixture is not a measured biological reserve horizon.',
 'egg_duration': 'ms converted by86,400,000/day; default30s and long-term2d are fixture scales. B06 durations temperature/population dependent.',
 'larva_duration': 'ms after full tissue-protein threshold; not complete larval duration from hatching and not an instar model.',
 'pupa_duration': 'ms for pupa; B06 prepupa+pupa endpoint cannot be mapped without defining the stage boundary.',
 'absorption_period': 'ms between uptake pulses; ug/s is integrated over elapsed milliseconds. Pulse spacing is not physiological absorption half-time.',
 'water_loss_ug_per_period': 'ug per water_loss_period, not automatically ug/s; humidity/temperature/caste dependence absent.',
 'water_loss_period': 'ms denominator for water-loss quantity; preserve ratio when comparing rates, but schedule can still matter.',
 'crop_capacity_ug': 'Total wet-component mass ug; measured drink volume uL requires density/composition. Intake load does not identify maximum capacity.',
 'carrying_capacity_ug': 'External cargo mass, distinct from crop. Do not use liquid intake capacity as cargo mass without a handling model.',
 'carb_absorption_ug_per_s': 'ug/s integrated with integer remainder; no directly measured gut-to-body rate.',
 'water_absorption_ug_per_s': 'ug/s integrated with integer remainder; no measured caste/stage-specific water uptake curve.',
 'protein_absorption_ug_per_s': 'ug/s to larval tissue only; rate and nutritional threshold are separate uncalibrated quantities.',
 'transfer_limit_ug': 'ug/action cap; oral contact duration in seconds and event counts do not identify this mass.',
 'adult_protein_target_ug': 'Adult crop protein target ug, not a measured solicitation signal or tissue requirement.',
 'larval_protein_requirement_ug': 'Threshold tissue ug for growth permission, not measured growth rate or instar-specific demand.',
 'behavior_interval': 'Decision ms; primary fixtures can be hours while transfers resolve at+1ms. Do not interpret as measured bout duration.',
 'decision_interval': 'Autonomy interval ms; task sampling is not an empirical continuous-time transition hazard.',
 'minimum_program_time': 'Minimum dwell ms; engineering persistence may postpone response to demand. No measured hazard.',
 'trail_half_life_s': 'Exponential field half-life seconds. Physical deposit volume, active chemical and detectable behavior have different decay curves.',
 'deposit_units': 'Arbitrary field units/deposit; no mapping from gland extract or optical picolitres.',
 'trail_cap_units': 'Arbitrary field-unit cap; signal saturation is not measured.',
 'trail_weight': 'Dimensionless decision weight; assay-specific geometry/dose must be matched before fitting.',
 'sensing_radius_cells': 'Cells times surface cell_size_m defines local reach; not an olfactory diffusion or antennal span measurement.',
 'route_capacity': 'Positions, not physical memory duration. Capacity64 and position fidelity are engineering limits.',
 'memory_lifetime': 'ms expiry; current fixed5min fixture is not measured forgetting.',
 'max_speed_m_per_s': 'Movement validation bound m/s, not an observed free-walking speed distribution.',
 'contact_distance_m': 'Euclidean meters plus straight solid clearance; not actual body overlap or mouth contact duration.',
 'body_half_q': 'Geometry quanta times quantum_m; common cubic body across castes is not measured ant morphology.',
 'loaded_half_q': 'Loaded cubic clearance; load shape/orientation and individual body sizes absent.',
 'dry_ug_per_q3': 'ug per geometric quantum cubed. Physical g/cm3 = value *1e-12 / quantum_m^3; do not compare ug/q3 directly to soil bulk density.',
 'water_ug_per_q3': 'ug water/q3; gravimetric moisture is water/dry mass, distinct from volumetric fraction and water potential.',
 'dig_energy_nj_per_q3': 'Energy/removed volume; force, substrate hardness, particle size and moisture response unmeasured.',
 'empty_sites_per_contact': 'Empty sites per sampled contact; not actual chamber area per ant or brood demand.',
 'encounter_budget': 'Candidates/decision, includes rejected contacts; not contact frequency or degree.',
 'productive_span': 'ms external-source schedule; alternating availability is not season, weather or diapause.',
 'low_productivity_permille': 'Fraction/1000 of finite release limit, not autonomous resource production.',
 'interval': 'ms event spacing, interpreted by owner; egg attempt or finite external release, not guaranteed event success.'
}


def parameters(implicit):
    with LEGACY.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    for index, row in enumerate(rows, 1):
        # Preserve multiplicity in the immutable legacy scanner output (a line
        # can contain repeated aggregate expressions); do not deduplicate facts.
        row['parameter_id'] = f'P-{index:05}-' + digest('|'.join(row[k] for k in ['record_kind','parameter','path','line','expression','variable']))[:12]
        row['legacy_evidence_grade'] = row['evidence_grade']
        row['legacy_related_evidence_grade'] = row['related_evidence_grade']
        row['legacy_grade_namespace'] = 'S6_3_2_A_D'
        row['evidence_grade'] = 'F'
        row['related_evidence_grade'] = 'Endpoint-specific A-F in evidence records; does not calibrate this coefficient'
        row['value_origin'] = 'ENGINEERING_FIXTURE'
        row['dimensional_audit'] = DIMENSIONS.get(row['field'],
            'Declared unit: '+row['unit']+'. '+row['biological_meaning']+'. No matched empirical coefficient; categorical switches, probabilities and scenario bounds remain engineering choices.')
        row['numerical_calibration_status'] = 'NOT_CALIBRATED; no value changed'
        row['parameter_range_status'] = 'UNKNOWN biological range; code validation limits are engineering limits'
        row['audit_scope'] = 'CONFIG_EXPRESSION' if index <= 1209 else 'LEGACY_SUPPLEMENTAL_CONTEXT'
    for item in implicit:
        row = {key: '' for key in rows[0]}
        row.update(parameter_id=item['SourceRuleId'],record_kind='IMPLICIT_SOURCE_CONTEXT',parameter='Implicit.'+item['Path']+':'+item['Line'],owner='ImplicitSource',field=item['Function'],path=item['Path'],line=item['Line'],expression=item['Expression'],resolution='LEXICAL_EXPRESSION; see surrounding function',static_numeric_value='SOURCE_EXPRESSION',unit='MIXED_EXPRESSION; typed field units in config records',biological_meaning='Implicit condition, state gate or numeric literal; includes engineering-only checks',evidence_grade='F',related_evidence_grade='Rule/source links are not coefficient calibration',adopted_reason='Existing unchanged code; reviewed mechanism groups in rule inventory',sensitivity='NOT MEASURED; isolate a biological hypothesis before fitting',modification_status='PROPOSAL ONLY',context='CORE_IMPLICIT_SOURCE',value_origin='ENGINEERING_FIXTURE',dimensional_audit='Expression-level record, not a scalar. Numerical precision factors and validation constants must not be fitted as biology.',numerical_calibration_status='NOT_CALIBRATED',parameter_range_status='NOT_APPLICABLE to composite expression',audit_scope='IMPLICIT_LEXICAL_INVENTORY')
        rows.append(row)
    assert len({r['parameter_id'] for r in rows}) == len(rows), 'Parameter identifier collision'
    return rows


def species_rows(sources):
    # Species records are evidence-specific boundaries, not an encyclopedia of
    # unverified caste or reproductive claims.
    entries = [
      ('Lasius niger','TARGET','B01 B03 B04 B05 N03 N05 N23','Queen, worker, male and premating gyne have distinct records. No discrete soldier assumed.','Claustral founding studied; solitary and facultative cofounding contexts kept distinct.'),
      ('Lasius japonicus','OTHER_LASIUS','N12','Queen and first worker brood studied; other castes UNKNOWN here.','Founding/photoperiod study; historical Japanese L. niger naming must not be pooled.'),
      ('Lasius neoniger','OTHER_LASIUS','B07','Queen, worker and brood nutrient allocation; no imported caste morphology.','Separate isotope species;30 C rearing differs from L. niger.'),
      ('Lasius platythorax','OTHER_LASIUS','N07 N08','Workers in acclimation/recognition assays.','Founding strategy NOT_STUDIED_IN_RETRIEVED_EVIDENCE.'),
      ('Lasius brunneus','OTHER_LASIUS','N07','Workers; full physiological evidence pending.','Reproductive strategy NOT_STUDIED_IN_RETRIEVED_EVIDENCE.'),
      ('Lasius flavus','OTHER_LASIUS','N10 N13','Workers in dormancy assays; alate field identifications.','No L. niger coefficient inherited.'),
      ('Lasius neglectus','OTHER_LASIUS','N18 N26','Workers and infected pupae; competitive fragments.','Colony social structure not inferred from contest fragments.'),
      ('Formica fusca','OTHER_FORMICINAE','N10','Workers in dormancy assay.','Species-specific response; no universal metabolic multiplier.'),
      ('Myrmica rubra','OTHER_ANT','N10','Workers in dormancy assay.','Other subfamily; no transfer without explicit hypothesis.'),
      ('Leptothorax acervorum','OTHER_ANT','N10','Workers in dormancy assay.','One source colony in this experiment.'),
      ('Solenopsis invicta','OTHER_ANT','B21','Workers in quasi-2D digging assay; morph distribution not extracted.','Do not transfer fire-ant task/size structure to L. niger.'),
      ('Pheidole morrisi','OTHER_ANT','N23','Minor and soldier morphology in this species only.','Soldier/minor developmental findings are not L. niger castes.'),
      ('Linepithema humile','OTHER_ANT','N26','Workers in100-worker competition fragments.','TSV actor Lh; opponent Ln=L. neglectus and Lni=L. niger.'),
      ('Camponotus herculeanus','OTHER_FORMICINAE','N27','Queens and workers in respirometry.','Large-ant respiration and mixed-species allometry are not L. niger coefficients.'),
      ('Formica rufibarbis','OTHER_FORMICINAE','N27','Queens and workers in respirometry.','Device and temperature confounded; no caste rates transferred.'),
    ]
    by_id = {r['SourceId']:r for r in sources}
    return [dict(SpeciesId='SP'+str(i).zfill(2),Species=species,Scope=scope,SourceIds=refs,CastesAndStages=castes,TransferBoundary=boundary,
        DOI='; '.join(by_id[s]['DOI'] for s in refs.split()),Locator='; '.join(s+': '+by_id[s]['UsedDataAndLocator'] for s in refs.split()),
        Unknowns='Unlisted ages, caste durations and reproductive strategies are UNKNOWN; this row is not a complete species natural history')
        for i,(species,scope,refs,castes,boundary) in enumerate(entries,1)]


def raw_datasets():
    manifest = read_json('raw/manifest.json')
    result = {}
    names = {'niger':'Lasius niger','platythorax':'Lasius platythorax','brunneus':'Lasius brunneus'}
    for item in manifest:
        path = DATA/'raw'/item['CSV']
        content = path.read_text(encoding='utf-8')
        assert digest(content) == item['CSVNormalizedSHA256'], path
        rows = list(csv.DictReader(io.StringIO(content)))
        assert len(rows) == item['Rows']
        for row in rows:
            species = names[row['SpeciesCode']] if 'SpeciesCode' in row else row['Species']
            row.update(RecordId=path.stem+'-'+row['SourceRow'],SourceId=item['SourceId'],
                DatasetDOI=item['DatasetDOI'],Species=species,License=item['License'],
                Locator=item['SourceFile']+':'+item['SourceSheet']+':row'+row['SourceRow'],
                EvidenceGrade='A' if species=='Lasius niger' else ('C' if species.startswith('Lasius ') else 'D'),
                ValueOrigin='PUBLISHED_FIT' if 'lte50' in path.stem else ('DUPLICATE_CONDITION_SUMMARY' if 'condition_means' in path.stem else 'REPOSITORY_MEASUREMENT'),
                Limitation='README status1/2 disagrees with raw0/1; early deaths interval-uncertain; do not fit exact event times' if item['SourceId']=='N07' else 'One source colony/species; SMR is pooled CO2, not O2; condition means duplicate raw outcomes')
        result['raw_'+path.stem.lower()] = rows
    return manifest, result


def validate(sources, measurements, coverage, rules, validations, params, conversions):
    ids = {s['SourceId'] for s in sources}
    assert len(ids) == len(sources)
    assert len({s['DOI'].lower() for s in sources}) == len(sources)
    assert all(s['Title'] and s['Authors'] and s['Year'] and s['DOI'] and s['UsedDataAndLocator'] for s in sources)
    assert len({m['RecordId'] for m in measurements}) == len(measurements)
    source_map = {s['SourceId']:s for s in sources}
    for m in measurements:
        assert m['SourceId'] in ids
        assert m['DOI'].lower() == source_map[m['SourceId']]['DOI'].lower()
        assert m['Locator'] and m['Method'] and m['Unit'] and m['Conditions']
        assert m['EvidenceGrade'] in 'ABCDEF' and len(m['EvidenceGrade']) == 1
        if m['EvidenceGrade'] == 'A':
            assert m['Species'] == 'Lasius niger', m['RecordId']
            assert m['StudyDesign'] == 'CONTROLLED_LABORATORY', m['RecordId']
        if m['EvidenceGrade'] == 'C':
            assert m['Species'].startswith('Lasius ') and m['Species'] != 'Lasius niger'
        if 'ABSTRACT' in m['ValueOrigin'] or 'ABSTRACT' in m['ExtractionConfidence']:
            assert m['EvidenceGrade'] != 'A', m['RecordId']
        assert 'DIGITIZED' not in m['ValueOrigin'], 'No figure digitization was performed in this release'
    for rows, key in [(coverage,'SourceIds'),(rules,'RelatedSourceIds'),(validations,'SourceIds')]:
        for row in rows:
            assert set(source_ids(row[key])) <= ids, row
    for rule in rules:
        assert rule['NumericEvidenceGrade'] == 'F'
        assert all((ROOT/p).is_file() for p in rule['SourceFiles'].split(';')), rule['RuleId']
    for item in conversions:
        assert item['SourceId'] in ids or not item['SourceId']
    assert all(p['evidence_grade'] == 'F' for p in params)
    for row in coverage:
        assert row['DOI'] and row['Locator']
    schema = json.loads((ROOT/'experiments/s6_3_2/inventory/schema.json').read_text(encoding='utf-8'))
    expected = {owner+'.'+f['name'] for owner, fields in schema.items() for f in fields}
    assert len(expected) == 119
    assert expected <= {p['parameter'] for p in params}
    # Existing complete immutable source identity check includes headers/apps/tests.
    manifest = json.loads((ROOT/'experiments/s6_3_2/core_and_tests_identity.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        assert digest((ROOT/item['path']).read_bytes().replace(b'\r\n',b'\n')) == item['normalized_sha256'], item['path']


def table(db, name, rows, primary, references=None):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    cols = [f'"{f}" TEXT' + (' PRIMARY KEY' if f == primary else '') for f in fields]
    for field, parent, target in references or []:
        cols.append(f'FOREIGN KEY("{field}") REFERENCES "{parent}"("{target}")')
    db.execute(f'CREATE TABLE "{name}" (' + ','.join(cols) + ')')
    sql = f'INSERT INTO "{name}" VALUES (' + ','.join('?' for _ in fields) + ')'
    db.executemany(sql, [[str(row.get(f,'')) for f in fields] for row in rows])


def build_db(path, data):
    with closing(sqlite3.connect(path)) as db:
        populate_db(db, data)


def populate_db(db, data):
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA user_version=1')
    table(db,'sources',data['sources'],'SourceId')
    table(db,'measurements',data['measurements'],'RecordId',[('SourceId','sources','SourceId')])
    for name, key in [('coverage','CoverageId'),('rules','RuleId'),('validations','ValidationId'),('parameters','parameter_id'),('species','SpeciesId'),('source_inventory','SourceRuleId'),('search_log','search_id'),('conversions','ConversionId')]:
        table(db,name,data[name],key)
    table(db,'manual_receipts',data['manual_receipts'],'ReceiptId',[('SourceId','sources','SourceId')])
    table(db,'behavior_facets',data['behavior_facets'],'CoverageId',[('CoverageId','coverage','CoverageId')])
    table(db,'dataset_manifest',data['dataset_manifest'],'CSV',[('SourceId','sources','SourceId')])
    for name, rows in data['raw_datasets'].items():
        table(db,name,rows,'RecordId',[('SourceId','sources','SourceId')])
        db.execute(f'CREATE INDEX "{name}_species" ON "{name}"(Species)')
    for name, key, column in [('coverage','CoverageId','SourceIds'),('rules','RuleId','RelatedSourceIds'),('validations','ValidationId','SourceIds'),('species','SpeciesId','SourceIds'),('parameters','parameter_id','references')]:
        link=name+'_sources'
        db.execute(f'CREATE TABLE "{link}" (record_id TEXT REFERENCES "{name}"("{key}"),source_id TEXT REFERENCES sources(SourceId),PRIMARY KEY(record_id,source_id))')
        db.executemany(f'INSERT INTO "{link}" VALUES (?,?)',[(r[key],s) for r in data[name] for s in source_ids(r[column])])
    db.execute('CREATE INDEX measurement_species ON measurements(Species,LifeStage,Measurement)')
    db.execute('CREATE INDEX measurement_source ON measurements(SourceId,Locator)')
    db.execute('CREATE INDEX parameter_field ON parameters(owner,field,path)')
    db.execute('CREATE INDEX source_lines ON source_inventory(Path,Line)')
    for domain, view in [('behavior','behavior_evidence'),('environment','environment_response'),('physiology','physiology_data')]:
        db.execute(f"CREATE VIEW {view} AS SELECT * FROM measurements WHERE Domain='{domain}'")
    db.execute("CREATE VIEW unresolved_coverage AS SELECT * FROM coverage WHERE Status NOT IN ('DIRECT_QUANTITATIVE','DIRECT_OBSERVATIONAL','DIRECT_QUALITATIVE')")
    db.execute("CREATE TABLE release_metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.executemany('INSERT INTO release_metadata VALUES (?,?)',[('baseline',BASELINE),('grade_namespace','S6_3_2_1_A_F'),('calibration','NONE; review-only'),('source_reading','Source-specific selected sections; see sources table')])
    db.commit()
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()


def db_logical_dump(path):
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        return list(db.iterdump())


def bibtex(sources):
    result = ['% Verified metadata; original articles are not distributed with this atlas.']
    def escape(s):
        return str(s).replace('\\','\\textbackslash{}').replace('&','\\&').replace('%','\\%').replace('_','\\_')
    for s in sources:
        result += ['@article{'+s['SourceId']+',', '  title = {'+escape(s['Title'])+'},',
            '  author = {'+escape(s['Authors'].replace('; ',' and '))+'},',
            '  year = {'+s['Year']+'},', '  journal = {'+escape(s['Journal'])+'},',
            '  doi = {'+s['DOI']+'},', '  url = {'+s['URL']+'},',
            '  note = {'+escape(s['ReadingStatus']+'; '+s['PeerReview'])+'}', '}', '']
    return '\n'.join(result)


def render_audit(rules, source_inventory_rows):
    lines=['# State machine evidence audit', '',f'Unchanged source baseline: `{BASELINE}`. This audit changes no Core behavior or numerical parameter.',
        '', 'The 54 inherited mechanism records remain linked to their original S6.3.2 assessment, whose **A-D grade namespace is historical**. The atlas uses A-F only in explicit new grade fields. All current numerical coefficients and implicit rules remain F / ENGINEERING_FIXTURE. Biological support for a qualitative mechanism never validates its particular condition or weight.',
        '', 'The source-expression inventory includes every lexical condition, numeric-bearing or enum-state line in the 14 named implementation/helper files. It is not a C++ AST or a claim that every expression is biological. File-group links require surrounding-function review; precise links are labelled FUNCTION. The config inventory separately scans headers, applications and tests. These are complementary completeness checks, not evidence coverage.',
        '', f'{len(rules)} reviewed mechanism groups; {len(source_inventory_rows)} lexical source-expression records. See [SOURCE_RULE_INVENTORY.csv](research/s6_3_2_1/SOURCE_RULE_INVENTORY.csv) and [PARAMETER_PROVENANCE.csv](PARAMETER_PROVENANCE.csv).', '']
    for r in rules:
        lines += ['## '+r['RuleId']+' — '+r['Interpretation'], '',
            '**Actual rule:** '+r['ActualRule'], '',
            '**Source:** '+', '.join('['+p+']('+p+')' for p in r['SourceFiles'].split(';'))+('; functions: '+r['Functions'] if r.get('Functions') else '')+'.', '',
            '**Verified code anchors:** '+r['CodeAnchors']+'.', '',
            '**Assessment:** '+r['Assessment']+'. '+r['LocalityAndMissingState'], '',
            '**Evidence:** '+(r['RelatedSourceIds'] or 'UNKNOWN: no biological measurement')+'. Source locators and conditions are in [SOURCE_READING_REGISTER.csv](research/s6_3_2_1/SOURCE_READING_REGISTER.csv).', '',
            '**Parameters:** '+r['ParameterFamilies']+'. Numerical evidence grade F; no calibration.', '',
            '**Proposal / validation:** '+r['Proposal']+'; see [correction roadmap](MODEL_CORRECTION_ROADMAP.md) and [validation catalog](MODEL_VALIDATION_CATALOG.md).', '']
    return '\n'.join(lines)


def render_validations(rows, sources):
    by_id={s['SourceId']:s for s in sources}
    lines=['# Model validation catalog', '', 'These are proposed replications, not executed biological validation or newly fitted parameters. Existing synthetic simulator experiments remain engineering evidence. READY is deliberately not awarded when the original observation protocol cannot be reproduced.', '', 'Calibration and validation are distinct data roles. A proposed holdout must be frozen before fitting. If the same colonies or observations are reused, report internal fit only, not independent validation. No statistical equivalence margin is invented where the source supplies only a qualitative result.', '']
    for v in rows:
        lines += ['## '+v['ValidationId']+' — '+v['Experiment'], '', '**Capability:** '+v['Capability']+'. **Execution:** '+v['Execution']+'.', '',
            '**Original sources:** '+', '.join('['+s+']('+by_id[s]['URL']+')' for s in v['SourceIds'].split())+'. Exact pages/figures, population, samples and controls are in the source register and measurement records.', '']
        for title,key in [('Data separation','DataRole'),('Procedure','Procedure'),('Endpoints','Measurements'),('Missing mechanisms','MissingMechanisms'),('Comparison','Comparison'),('Uncertainty and limits','Uncertainty')]:
            lines += ['**'+title+':** '+v[key]+'.','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--check',action='store_true'); args=parser.parse_args()
    sources=read_json('sources.json'); measurements=read_json('measurements.json'); coverage=read_json('coverage.json')
    rules=read_json('rules.json'); validations=read_json('validation.json'); conversions=read_json('conversions.json')
    implicit=source_inventory(rules); params=parameters(implicit); species=species_rows(sources)
    manifest, raw = raw_datasets()
    for r in rules:
        anchors=sorted({(s['Path'],s['Function']) for s in implicit if s['Path'] in r['SourceFiles'].split(';') and s['Function'] in r['Functions'].split(';')})
        assert anchors, 'No actual source function for '+r['RuleId']
        assert set(r['Functions'].split(';')) <= {f for _,f in anchors}, r['RuleId']
        r['CodeAnchors']='; '.join(f'{p}:{min(int(s["Line"]) for s in implicit if s["Path"]==p and s["Function"]==f)} ({f})' for p,f in anchors)
    validate(sources,measurements,coverage,rules,validations,params,conversions)
    outputs={
      'SPECIES_DATABASE.csv':csv_text(species),
      'CASTE_LIFE_STAGE_MATRIX.csv':csv_text([r for r in coverage if r['Axis']=='life_stage']),
      'BEHAVIOR_EVIDENCE_DATABASE.csv':csv_text([r for r in measurements if r['Domain']=='behavior']),
      'ENVIRONMENT_RESPONSE_DATABASE.csv':csv_text([r for r in measurements if r['Domain']=='environment']),
      'PHYSIOLOGY_DATA.csv':csv_text([r for r in measurements if r['Domain']=='physiology']),
      'PARAMETER_PROVENANCE.csv':csv_text(params),
      'BIBLIOGRAPHY.bib':bibtex(sources),
      'STATE_MACHINE_EVIDENCE_AUDIT.md':render_audit(rules,implicit),
      'MODEL_VALIDATION_CATALOG.md':render_validations(validations,sources),
      'research/s6_3_2_1/SOURCE_READING_REGISTER.csv':csv_text(sources),
      'research/s6_3_2_1/MEASUREMENTS.csv':csv_text(measurements),
      'research/s6_3_2_1/COVERAGE.csv':csv_text(coverage),
      'research/s6_3_2_1/SOURCE_RULE_INVENTORY.csv':csv_text(implicit),
      'research/s6_3_2_1/UNIT_CONVERSIONS.csv':csv_text(conversions),
      'research/s6_3_2_1/MANUAL_ACCESS_RECEIPTS.csv':csv_text(read_json('manual_receipts.json')),
      'research/s6_3_2_1/RULES.csv':csv_text(rules),
      'research/s6_3_2_1/BEHAVIOR_FACETS.csv':csv_text(read_json('behavior_facets.json')),
    }
    counts={axis:dict(sorted(Counter(r['Status'] for r in coverage if r['Axis']==axis).items())) for axis in sorted({r['Axis'] for r in coverage})}
    summary=dict(baseline=BASELINE,sources=len(sources),reading_status=dict(sorted(Counter(s['ReadingStatus'] for s in sources).items())),measurement_records=len(measurements),measurement_grades=dict(sorted(Counter(m['EvidenceGrade'] for m in measurements).items())),species=len(species),coverage=counts,reviewed_rule_groups=len(rules),implicit_source_expressions=len(implicit),config_fields=119,legacy_source_expressions=1209,legacy_supplemental=469,parameter_records=len(params),calibrated_parameters=0,validation_designs=len(validations),validation_executed=0)
    summary['raw_dataset_rows']={k:len(v) for k,v in raw.items()}
    summary['raw_dataset_rows_total']=sum(len(v) for v in raw.values())
    outputs['research/s6_3_2_1/summary.json']=json.dumps(summary,sort_keys=True,indent=2)+'\n'
    for relative,content in outputs.items():
        path=ROOT/relative
        if args.check:
            assert path.read_text(encoding='utf-8')==content, 'Generated artifact drift: '+relative
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content,encoding='utf-8',newline='')
    data=dict(sources=sources,measurements=measurements,coverage=coverage,rules=rules,validations=validations,parameters=params,species=species,source_inventory=implicit,search_log=read_json('search_log.json'),conversions=conversions)
    data.update(manual_receipts=read_json('manual_receipts.json'),dataset_manifest=manifest,raw_datasets=raw)
    data['behavior_facets']=read_json('behavior_facets.json')
    assert len(data['behavior_facets'])==21
    for facet in data['behavior_facets']:
        assert set(source_ids(facet['SourceIds'])) <= {s['SourceId'] for s in sources}
        assert facet['Locator'] and facet['DOI']
    scratch=(ROOT/'out/s6_3_2_1/build').resolve()
    scratch.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='atlas-',dir=scratch) as temp:
        assert Path(temp).resolve().is_relative_to(scratch)
        generated=Path(temp)/'atlas.sqlite'; build_db(generated,data)
        target=ROOT/'ANT_BIOLOGY_EVIDENCE.sqlite'
        if args.check:
            assert db_logical_dump(target)==db_logical_dump(generated),'SQLite logical content drift'
        else:
            target.write_bytes(generated.read_bytes())
    print(('PASS' if args.check else 'WROTE')+': '+json.dumps(summary,sort_keys=True))


if __name__=='__main__': main()
