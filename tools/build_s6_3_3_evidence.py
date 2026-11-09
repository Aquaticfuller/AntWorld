"""Extend the immutable biology atlas with source-addressed, uncalibrated P01/P10 records."""
import argparse,csv,hashlib,io,json,re,sqlite3,tempfile
from contextlib import closing
from pathlib import Path
import inventory_s6_3_2 as inventory
from atlas_baseline import source_root
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/s6_3_2_1/baseline';OUT=ROOT/'research/s6_3_3'
def sha(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def read(path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def csv_text(data):
    out=io.StringIO(newline='');w=csv.DictWriter(out,list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data);return out.getvalue()
UNITS={'decision_interval':'ms','bout_duration':'ms','worker_contact_duration':'ms','social_memory_horizon':'ms','care_probability':'probability per eligible decision','worker_contact_probability':'probability per decision','maximum_inhibition':'dimensionless fraction','perception_radius_m':'m','step_m':'m per completed bout','arrangement_m':'m per completed bout','temperature_c':'degC (metadata only)','relative_humidity':'fraction (metadata only)','age_at_enrollment':'ms (declared age metadata)','context':'caste/founding context enum'}
RULES=[
('C01','cpp/src/care.cpp','configure_biology','Opt-in unexecuted social/long-term world; profile validation; no legacy activation','Engineering version/rollback boundary','F','No species claim'),
('C02','cpp/src/care.cpp','enable_brood_care','Live adult Queen or Worker, physiological, paused, local familiar shelter; no Male or immature caregiver','B01/B02 maternal capability; exact enrollment interface is engineering','B01 B02','No queen Forage/Excavate; chronological maturity not implemented'),
('C03','cpp/src/care.cpp','resolve_care_wakes','Same-colony live neighbors inside radius and actual spatial visibility; no global population count','Locality-constrained approximation','B01','Sensory6mm range unmeasured; colony recognition assumed'),
('C04','cpp/src/care.cpp','resolve_care_wakes','Own body energy/hydration >=quarter capacity; otherwise inactive','Existing urgency proxy, not matched physiology','F','Threshold and baseline/activity metabolism uncalibrated; P02 remains open'),
('C05','cpp/src/care.cpp','resolve_care_wakes','Queen may select close-worker bout first; only completed bout refreshes finite fading cue','B01 social plasticity supports direction, not this memory law','B01','Time occupancy and memory inhibition distinguished by inhibition0 control'),
('C06','cpp/src/care.cpp','resolve_care_wakes','Uniform local brood selection; approach if outside reach; retrieve if outside familiar shelter; else inspect/arrange/clean/feed','B01 manipulation; B02 retrieval capability','B01 B02','Priority/equal probabilities F; local brood may divert continued searching'),
('C07','cpp/src/care.cpp','execute_care_action','Finite inspection and cleaning require target lock, living brood and physical contact','Explicit motor-bout definitions; B01 active manipulation composite','B01','No direct cleaning duration/frequency estimate; no pathogen benefit'),
('C08','cpp/src/care.cpp','execute_care_action','Arrange same-ID brood locally; transport caregiver plus same-ID brood through swept loaded clearance','B02 actual retrieval, not instantaneous completion','B02','Discrete geometry and known shelter approximate arena/odor; rate F'),
('C09','cpp/src/care.cpp','execute_care_action','Feed only actual larval demand/crop, existing transfer-limit transaction, finite attempted bout','Maternal nutritional capability; no new physiological law','B01 B02','No flight-muscle/lipid mobilization, egg feeding or queen provision update'),
('C10','cpp/src/care.cpp','resolve_care_wakes','No local brood ->bounded random cardinal walk; no coordinate oracle','Minimal engineering local search','F','Search/navigation geometry not quantitatively validated by B02'),
('C11','cpp/src/care.cpp','interrupt_care','Movement/death/maturation/pause/blocked geometry cancels invalid act and releases ownership','Committed physical causality','F','Interrupted duration distinguished from success'),
('C12','cpp/src/care.cpp','observe_legacy_action','Legacy committed action classified; unknown physical duration stays unknown','P10 observation completeness boundary','F','No retrospective invention of grooming or motor duration'),
('C13','cpp/src/observations.cpp','behavior_window','Half-open clipped intervals; active/inactive/unknown separate from task residence; reads pure','Experiment-compatible observer','B01 B02','B01 scan presence differs from time budget; B02 count differs from retrieval rate'),
('C14','cpp/src/checkpoint_care.hpp','validate_care_evidence','Evidence-backed decisions, contact cue, selected/start/terminal matching, schedule ownership and locks','Engineering restore audit','F','Scalar ENGINEERING_FIXTURE parameters are not empirical facts'),
('C15','cpp/storage/analytics.cpp','contributions','Append seven flow metrics; target participant histories; completion-time duration flow','Historical evidence from committed events','F','Flow buckets are not interval-overlap activity estimates'),
('C16','cpp/src/care.cpp','resolve_care_wakes','Founding/established age labels do not change coefficients; queen-specific inhibition absent in worker policy','Caste difference retained without unsupported age curve','B01 B02','No callow maturation, genotype or parent-offspring correlation'),
]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args();OUT.mkdir(exist_ok=True)
    old=read(BASE/'PARAMETER_PROVENANCE.csv');fields=list(old[0])+['release_namespace','source_sha256']
    legacy=[]
    for r in old:legacy.append(dict(r,release_namespace='HISTORICAL_S6_3_2_1',source_sha256='Verified project archive at65e7875; see source_baseline.json'))
    lookup={(r['owner'],r['field']):r for r in old if r['record_kind']!='IMPLICIT_SOURCE_CONTEXT'}
    reviewed=source_root('s6_3_3')
    inventory.ROOT=reviewed;inventory.EXTRA|={'SpeciesCareProfile','IndividualCareProfile','EnvironmentCareProfile'}
    definitions=inventory.schemas();source,uses,_=inventory.rows_inventory(definitions);current=[]
    for index,r in enumerate(sorted(source,key=lambda x:(x['path'],x['line'],x['parameter'],x['record_kind'])),1):
        row={f:'' for f in fields};row.update(lookup.get((r['owner'],r['field']),{}));row.update(r)
        care=r['owner'].endswith('CareProfile');row.update(parameter_id=f'S633-P{index:05}',static_numeric_value=inventory.expr_value(r['expression']),release_namespace='CURRENT_S6_3_3',source_sha256=sha(reviewed/r['path']),modification_status='P01/P10 only; legacy coefficients unchanged',evidence_grade='F',value_origin='ENGINEERING_FIXTURE',numerical_calibration_status='NOT_CALIBRATED',audit_scope='CURRENT_CONFIG_EXPRESSION')
        row['context']='TEST_FIXTURE' if '/tests/' in r['path'] else 'APPLICATION_FIXTURE' if '/apps/' in r['path'] else 'RUNTIME_DEFAULT'
        if 'Fixture invalid' in (reviewed/r['path']).read_text().splitlines()[int(r['line'])-1]:row['context']='INTENTIONAL_INVALID_INPUT_TEST; rejected configuration, not a model setting'
        if care:
            row.update(unit=UNITS[r['field']],biological_meaning='P01 '+r['field']+'; definitions and limitations in document53',references='B01 B02',doi='10.1111/1365-2435.14536;10.1002/ece3.4475',page_figure='B01 Methods2.1.4/2.2.4-5/2.2.12, Figs1c-d/2c; B02 pp10411-10412, Methods2.2-2.3',experimental_conditions='L. niger; B01 21C/80%RH, 5larvae, worker removal or3-worker mesh; B02 50mm,6brood,600s,queen or3workers',measured_value_or_range='NO MATCHED NUMERICAL COEFFICIENT; 21C/80%RH are assay conditions only',related_evidence_grade='A for source manipulation endpoints; F for this coefficient',adopted_reason='Frozen unfit mechanism hypothesis in document52',sensitivity='Predeclared memory1/6/24h; inhibition0/.4/.8; decision15/60/240s; other values not varied',dimensional_audit='Unit '+UNITS[r['field']]+'; probability bounds0..1; movement speed bounded by world max; thermal/age metadata inert',parameter_range_status='UNKNOWN biological interval; code limits are engineering safeguards')
        current.append(row)
    # Include every new implicit conditional/numeric line, not just named defaults.
    implicit=[]
    for path in (reviewed/name for name in ('cpp/src/care.cpp','cpp/src/care_internal.hpp','cpp/src/observations.cpp',
                                          'cpp/src/checkpoint_care.hpp','cpp/apps/antworld_s6_3_3_experiment.cpp','cpp/apps/s6_3_3_fixture.hpp')):
        for line,text in enumerate(path.read_text().splitlines(),1):
            if not re.search(r'\b(if|else|case)\b|\d',inventory.clean(text)):continue
            item=dict(path=path.relative_to(reviewed).as_posix(),line=line,expression=text.strip(),source_sha256=sha(path));implicit.append(item)
            row={f:'' for f in fields};row.update(parameter_id=f'S633-I{len(implicit):05}',record_kind='IMPLICIT_SOURCE_CONTEXT',parameter='Implicit.'+item['path']+':'+str(line),owner='ImplicitSource',field='SourceExpression',unit='MIXED; see typed configuration and document53',biological_meaning='Hard-coded condition, categorical policy or numeric expression; includes nonbiological limits',evidence_grade='F',references='B01 B02',doi='10.1111/1365-2435.14536;10.1002/ece3.4475',page_figure='Mechanism association only; document53 and current rule audit',value_origin='ENGINEERING_FIXTURE',numerical_calibration_status='NOT_CALIBRATED',dimensional_audit='Composite expression; RNG salts, enum values and serialization sizes are not biological coefficients',release_namespace='CURRENT_S6_3_3',audit_scope='CURRENT_IMPLICIT_LEXICAL_INVENTORY',**item);current.append(row)
    rules=[]
    for rid,path,function,condition,interpretation,sources,gap in RULES:
        text=(reviewed/path).read_text();match=re.search(r'\b'+re.escape(function)+r'\s*\(',text)
        # Analytics is a file-level mapping, not a claimed function locator.
        line=text.count('\n',0,match.start())+1 if match else 1
        rules.append(dict(rule_id=rid,path=path,line=line,function=function if match else 'FILE_LEVEL',actual_condition=condition,interpretation=interpretation,sources=sources,mechanism_grade='A endpoint; F implementation' if sources!='F' else 'F',numeric_grade='F',limitations=gap,source_sha256=sha(reviewed/path)))
    merged=legacy+current
    audit=['# State machine evidence audit: S6.3.3','','The70-rule historical audit is preserved in [baseline](research/s6_3_2_1/baseline/STATE_MACHINE_EVIDENCE_AUDIT.md). Its old source locators refer to the verified project archive, not current code. P01/P10 only are implemented; other proposals and biological debts remain open. New constants have no quantitative calibration.','','|Rule|Current source/function|Actual condition|Evidence and interpretation|Limits|','|---|---|---|---|---|']
    for r in rules:audit.append('|'+ '|'.join([r['rule_id'],f"{r['path']}:{r['line']} `{r['function']}`",r['actual_condition'],r['sources']+'; '+r['interpretation'],r['limitations']])+'|')
    audit+=['','B01 locator: DOI10.1111/1365-2435.14536, Methods2.1.4,2.2.4-5,2.2.12; Figs1c-d/2c. B02: DOI10.1002/ece3.4475, pp10411-10412, Methods2.2-2.3, Figs1-2. These links support endpoint capabilities; they do not turn engineering probabilities or durations into measured parameters.','','All current typed configuration/default/fixture expressions are rescanned. New implicit source expressions are retained verbatim with source hashes. Unknown-range and ambiguity labels are retained, never silently resolved as empirical values. The geometry/time/identity/resource mechanisms and inherited70-rule audit retain their earlier limitations.','']
    summary=dict(historical_parameter_records=len(legacy),current_parameter_records=len(current),current_typed_expressions=len(source),current_implicit_expressions=len(implicit),new_rule_groups=len(rules),calibrated_behavioral_coefficients=0,profile_fields={k:len(v) for k,v in definitions.items() if k.endswith('CareProfile')})
    products={ROOT/'PARAMETER_PROVENANCE.csv':csv_text(merged),ROOT/'STATE_MACHINE_EVIDENCE_AUDIT.md':'\n'.join(audit),OUT/'CURRENT_RULES.csv':csv_text(rules),OUT/'CURRENT_IMPLICIT.csv':csv_text(implicit),OUT/'CURRENT_CONFIGURATION_USES.csv':csv_text(uses),OUT/'summary.json':json.dumps(summary,indent=2)+'\n'}
    for path,text in products.items():
        if a.check:assert path.read_text(encoding='utf-8')==text,str(path)+' drift'
        else:path.write_text(text,encoding='utf-8',newline='\n')
    def populate(db):
        db.execute('PRAGMA foreign_keys=ON')
        tables=[('current_parameters',current),('care_rules',rules),('care_validation_catalog',read(OUT/'VALIDATION_CATALOG.csv'))]
        tables.extend(('care_'+name,read(ROOT/'experiments/s6_3_3/analysis'/(name+'.csv'))) for name in ['source_endpoints','comparisons','matched_sensitivity'])
        tables.extend(('care_raw_'+path.stem,read(path)) for path in sorted((ROOT/'experiments/s6_3_3/literature').glob('*.csv')))
        for name,data in tables:
            keys=list(data[0]);db.execute('CREATE TABLE "'+name+'" ('+','.join('"'+k+'" TEXT'+(' PRIMARY KEY' if k in ['parameter_id','rule_id'] else '') for k in keys)+')');db.executemany('INSERT INTO "'+name+'" VALUES ('+','.join('?' for _ in keys)+')',[[str(r[k]) for k in keys] for r in data])
        db.execute('CREATE TABLE current_parameter_sources (parameter_id TEXT REFERENCES current_parameters(parameter_id),source_id TEXT REFERENCES sources(SourceId),PRIMARY KEY(parameter_id,source_id))')
        db.executemany('INSERT INTO current_parameter_sources VALUES (?,?)',[(r['parameter_id'],s) for r in current for s in sorted(set(re.findall(r'\b[BN]\d\d\b',r['references'])))])
        db.execute('CREATE INDEX current_parameter_source ON current_parameters(path,line)')
        db.execute("INSERT INTO release_metadata VALUES ('current_extension','S6.3.3; current_parameters/care_rules; baseline tables immutable')")
        db.commit();assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not db.execute('PRAGMA foreign_key_check').fetchall()
    with tempfile.TemporaryDirectory(dir=ROOT/'out') as temporary:
        assert Path(temporary).resolve().is_relative_to((ROOT/'out').resolve())
        path=Path(temporary)/'atlas.sqlite';path.write_bytes((BASE/'ANT_BIOLOGY_EVIDENCE.sqlite').read_bytes())
        with closing(sqlite3.connect(path)) as db:populate(db);dump=list(db.iterdump())
        target=ROOT/'ANT_BIOLOGY_EVIDENCE.sqlite'
        if a.check:
            with closing(sqlite3.connect(target)) as db:assert list(db.iterdump())==dump,'current atlas database drift'
        else:target.write_bytes(path.read_bytes())
    print(json.dumps(summary))
if __name__=='__main__':main()
