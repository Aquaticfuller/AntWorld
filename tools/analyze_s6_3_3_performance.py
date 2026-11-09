"""Apply the unchanged performance qualification analysis to the new frozen binaries."""
import csv,json,statistics as st,sys,shutil,tempfile
from collections import defaultdict
from pathlib import Path
import analyze_s6_3_2_performance as audit
from analyze_s6_3_1 import emit,read
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'experiments/s6_3_3'
if __name__=='__main__':
    audit.BASE=BASE;audit.main()
    folder=BASE/'performance/contacts/session2'
    failures=[json.loads(p.read_text()) for p in sorted(folder.glob('admission*_receipt.json'))]
    status=dict(final_binary_contact_timing='NOT_QUALIFIED' if len(failures)==3 and not any(r['admitted'] for r in failures) else 'SEE status.csv',
        final_binary_birth_timing='NOT_RUN: quiet qualification stopped after three failed admissions',
        rejected_admissions=len(failures),threshold=6,
        preliminary='One earlier observer binary contact session retained separately; never pooled or promoted to final qualification',
        next_step='Review Windows per-core telemetry validity against an independent cumulative-time source; freeze any instrument change and a new quiet interval before retesting. Do not weaken <=6 or discard invalid/slow rows.')
    path=BASE/'performance_analysis/qualification.json';text=json.dumps(status,indent=2)+'\n'
    if '--check' in sys.argv:assert path.read_text()==text
    else:path.write_text(text,encoding='utf-8')
    by=defaultdict(list)
    for folder in sorted((BASE/'performance/contacts').glob('session*')):
        if not (folder/'receipt.json').exists():continue
        runs={r['sample']:r for r in read(folder/'contacts.csv')}
        for r in read(folder/'profile.csv'):
            item=runs.get(r['sample'])
            if item is not None:
                by[item['layout'],item['population'],r['phase'],r['category']].append(r)
    result=[]
    for (layout,population,phase,category),records in sorted(by.items()):
        result.append(dict(layout=layout,population=population,phase=phase,category=category,samples=len(records),calls_p50=st.median(int(r['calls']) for r in records),exclusive_ms_p50=st.median(int(r['exclusive_ns'])/1e6 for r in records),inclusive_ms_p50=st.median(int(r['inclusive_ns'])/1e6 for r in records)))
    if result:emit(BASE/'performance_analysis/profile.csv',result,'--check' in sys.argv)
    # Describe the earlier single session separately. Never pool its binary with final qualification.
    with tempfile.TemporaryDirectory(dir=ROOT/'out') as temporary:
        work=Path(temporary).resolve();assert work.is_relative_to((ROOT/'out').resolve())
        shutil.copytree(BASE/'performance_pre_observer_correction',work/'performance',ignore=shutil.ignore_patterns('*.raw'))
        prior_args=sys.argv;prior_base=audit.BASE
        try:
            sys.argv=[prior_args[0]];audit.BASE=work;audit.main()
        finally:sys.argv=prior_args;audit.BASE=prior_base
        for path in sorted((work/'performance_analysis').glob('*.csv')):
            emit(BASE/'performance_pre_analysis'/path.name,read(path),'--check' in sys.argv)
