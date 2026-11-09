"""Deterministic lexical inventory of biological configurations and fixture expressions.

This inventories source expressions, not every possible runtime value. Delimiter-aware
parsing handles comma declarations and nested aggregate initializers. Ambiguous field
owners remain explicit; a separate coverage file retains every configuration use.
"""
import argparse
import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'experiments/s6_3_2'
EXTRA = {'AntSeed', 'PhysiologySeed', 'FoodMass', 'PositionM', 'BoxQ', 'Controls', 'IntegratedOptions'}
TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


def clean(text):
    return TOKEN.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]) if m[0].startswith(('/', '"', "'")) else m[0], text)


def end_group(text, start):
    pairs = {'{': '}', '(': ')', '[': ']'}
    stack = []
    for i in range(start, len(text)):
        if text[i] in pairs:
            stack.append(pairs[text[i]])
        elif stack and text[i] == stack[-1]:
            stack.pop()
            if not stack:
                return i + 1
    raise ValueError('Unbalanced source group')


def split_top(text, sep=','):
    start, i = 0, 0
    result = []
    while i < len(text):
        if text[i] in '{([':
            i = end_group(text, i)
            continue
        if text[i] == sep:
            result.append((start, text[start:i]))
            start = i + 1
        i += 1
    result.append((start, text[start:]))
    return result


def line_at(text, offset):
    return text.count('\n', 0, offset) + 1


def expr_value(expr):
    expr = expr.strip().strip('{}').strip()
    if expr in ('true', 'false'):
        return expr
    if not expr:
        return '0'
    expr = re.sub(r'(?<=\d)(?:ULL|LL|UL|U|u|f)\b', '', expr)
    expr = expr.replace('UINT64_C(', '(').replace('INT64_C(', '(')
    try:
        node = ast.parse(expr, mode='eval').body
        def evaluate(n):
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                return n.value
            if isinstance(n, ast.Name) and n.id in ('hour', 'day'):
                return {'hour': 3600000, 'day': 86400000}[n.id]
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
                return -evaluate(n.operand) if isinstance(n.op, ast.USub) else evaluate(n.operand)
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult)):
                a, b = evaluate(n.left), evaluate(n.right)
                return a+b if isinstance(n.op, ast.Add) else a-b if isinstance(n.op, ast.Sub) else a*b
            raise ValueError('runtime expression')
        return str(evaluate(node))
    except (SyntaxError, ValueError):
        return 'EXPRESSION; see source and scenario'


def schemas():
    result = {}
    for path in sorted([*(ROOT / 'cpp/include/antworld/core').glob('*.hpp'), *(ROOT / 'cpp/apps').glob('*.hpp')]):
        raw = path.read_text(encoding='utf-8'); text = clean(raw)
        for match in re.finditer(r'\bstruct\s+(\w+)\s*\{', text):
            owner = match[1]
            if not owner.endswith('Config') and owner not in EXTRA:
                continue
            start = text.index('{', match.start())
            stop = end_group(text, start)
            fields = []
            for offset, declaration in split_top(text[start+1:stop-1], ';'):
                if 'operator' in declaration or '[[' in declaration or not declaration.strip():
                    continue
                parts = split_top(declaration)
                first = re.match(r'\s*([\w:]+)\s+(\w+)\s*([\s\S]*)$', parts[0][1])
                if not first:
                    raise ValueError(f'Unparsed {owner} declaration: {declaration}')
                dtype = first[1]
                for k, (delta, part) in enumerate(parts):
                    field = first if k == 0 else re.match(r'\s*(\w+)\s*([\s\S]*)$', part)
                    name, initializer = (field[2], field[3]) if k == 0 else (field[1], field[2])
                    pos = start+1+offset+delta+part.index(name)
                    fields.append(dict(owner=owner, name=name, type=dtype, default=initializer.strip() or '{}', path=path.relative_to(ROOT).as_posix(), line=line_at(raw, pos)))
            result[owner] = fields
    return result


def rows_inventory(definitions):
    rows, uses = [], []
    fields = defaultdict(list)
    for owner, declarations in definitions.items():
        for field in declarations:
            fields[field['name']].append(owner)
            rows.append(dict(record_kind='DEFAULT', parameter=owner+'.'+field['name'], owner=owner, field=field['name'], path=field['path'], line=field['line'], expression=field['default'], resolution='DECLARED', variable=''))
    names = '|'.join(sorted(definitions, key=len, reverse=True))
    paths = sorted([*((ROOT/'cpp/apps').glob('*.cpp')), *((ROOT/'cpp/apps').glob('*.hpp')), *((ROOT/'cpp/tests').glob('*.cpp'))])
    factories=defaultdict(set)
    for path in paths:
        for match in re.finditer(r'\b('+names+r')\s+(\w+)\s*\(',clean(path.read_text(encoding='utf-8'))):
            factories[match[2]].add(match[1])
    for path in paths:
        raw = path.read_text(encoding='utf-8'); text = clean(raw); relative=path.relative_to(ROOT).as_posix()
        declarations=[]
        for match in re.finditer(r'\bauto\s+(\w+)\s*=\s*(?:[\w]+::)*(\w+)\s*\(',text):
            if len(factories[match[2]])==1:
                declarations.append((match.start(),match[1],next(iter(factories[match[2]]))))
        for match in re.finditer(r'\b('+names+r')\s+(\w+)\s*([=;{(])', text):
            owner, var, next_char = match[1], match[2], match[3]
            declarations.append((match.start(),var,owner))
            uses.append(dict(path=relative,line=line_at(raw,match.start()),owner=owner,variable=var,form='DECLARATION_OR_FUNCTION',source=raw[match.start():match.end()].strip()))
            if next_char != '{':
                continue
            start=match.end()-1; stop=end_group(text,start)
            for ordinal, (offset,value) in enumerate(split_top(raw[start+1:stop-1])):
                if not value.strip(): continue
                if ordinal>=len(definitions[owner]): raise ValueError('aggregate overflow')
                field=definitions[owner][ordinal]['name']
                rows.append(dict(record_kind='AGGREGATE',parameter=owner+'.'+field,owner=owner,field=field,path=relative,line=line_at(raw,start+1+offset),expression=value.strip(),resolution='POSITIONAL_DECLARATION',variable=var))
        for match in re.finditer(r'\b('+names+r')\s*\{', text):
            owner=match[1]; start=match.end()-1; stop=end_group(text,start)
            uses.append(dict(path=relative,line=line_at(raw,match.start()),owner=owner,variable='',form='TYPED_AGGREGATE',source=raw[match.start():stop].strip()))
            for ordinal,(offset,value) in enumerate(split_top(raw[start+1:stop-1])):
                if not value.strip():continue
                if ordinal>=len(definitions[owner]): raise ValueError('aggregate overflow')
                field=definitions[owner][ordinal]['name']
                rows.append(dict(record_kind='AGGREGATE',parameter=owner+'.'+field,owner=owner,field=field,path=relative,line=line_at(raw,start+1+offset),expression=value.strip(),resolution='POSITIONAL_TEMPORARY',variable=''))
        for match in re.finditer(r'\b(\w+)\s*=\s*\{', text):
            var=match[1]; choices=[(pos,own) for pos,v,own in declarations if v==var and pos<match.start()]
            if not choices:continue
            owner=max(choices)[1]; opening=match.end()-1; closing=end_group(text,opening)
            uses.append(dict(path=relative,line=line_at(raw,opening),owner=owner,variable=var,form='WHOLE_ASSIGNMENT',source=raw[match.start():closing]))
            for ordinal,(offset,value) in enumerate(split_top(raw[opening+1:closing-1])):
                if not value.strip():continue
                if ordinal>=len(definitions[owner]):raise ValueError('whole assignment overflow')
                field=definitions[owner][ordinal]['name']
                rows.append(dict(record_kind='WHOLE_ASSIGNMENT',parameter=owner+'.'+field,owner=owner,field=field,path=relative,line=line_at(raw,opening+1+offset),expression=value.strip(),resolution='LEXICAL_TYPED_NAME',variable=var))
        for match in re.finditer(r'\b(\w+)\.(\w+)\s*=(?!=)', text):
            var,field=match[1],match[2]
            if field not in fields:continue
            start=match.end(); i=start
            while i<len(text) and text[i]!=';':
                i=end_group(text,i) if text[i] in '{([' else i+1
            choices=[(pos,own) for pos,v,own in declarations if v==var and pos<match.start() and field in [x['name'] for x in definitions[own]]]
            owners=[max(choices)[1]] if choices else fields[field]
            for owner in owners:
                rows.append(dict(record_kind='ASSIGNMENT',parameter=owner+'.'+field,owner=owner,field=field,path=relative,line=line_at(raw,match.start()),expression=raw[start:i].strip(),resolution='LOCAL_TYPED_NAME' if choices else 'UNIQUE_FIELD_NAME' if len(owners)==1 else 'AMBIGUOUS_OWNER_REVIEW',variable=var))
        # Preserve untyped API aggregate arguments with their declared API types.
        api={'configure_surface':[(0,'SurfaceConfig'),(2,'BehaviorConfig')], 'configure_social':[(0,'SocialConfig')], 'configure_long_term':[(0,'LongTermConfig')], 'configure_geometry':[(0,'GeometryConfig')], 'enable_reproduction':[(1,'ReproductionConfig')], 'configure_resource_cycle':[(1,'ResourceCycleConfig')], 'seed_ant':[(1,'AntSeed')], 'enable_physiology':[(1,'PhysiologySeed'),(2,'PhysiologyConfig')], 'seed_food':[(0,'PositionM'),(1,'FoodMass')], 'seed_colony':[(0,'PositionM')]}
        for match in re.finditer(r'\b('+ '|'.join(api)+r')\s*\(', text):
            start=match.end()-1; stop=end_group(text,start); args=split_top(text[start+1:stop-1])
            for index,owner in api[match[1]]:
                if index>=len(args):continue
                delta,arg=args[index]; begin=start+1+delta
                if not arg.strip().startswith('{'):continue
                opening=begin+arg.index('{'); closing=end_group(text,opening)
                uses.append(dict(path=relative,line=line_at(raw,opening),owner=owner,variable=match[1],form='API_AGGREGATE',source=raw[opening:closing]))
                for ordinal,(offset,value) in enumerate(split_top(raw[opening+1:closing-1])):
                    if not value.strip():continue
                    if ordinal>=len(definitions[owner]):raise ValueError('API aggregate overflow')
                    field=definitions[owner][ordinal]['name']
                    rows.append(dict(record_kind='API_AGGREGATE',parameter=owner+'.'+field,owner=owner,field=field,path=relative,line=line_at(raw,opening+1+offset),expression=value.strip(),resolution='DECLARED_API_POSITION',variable=match[1]))
        # Return aggregates in explicitly typed fixture helpers are retained whole.
        for match in re.finditer(r'\b('+names+r')\s+(\w+)\s*\([^;]*?\)\s*\{',text):
            opening=match.end()-1; closing=end_group(text,opening)
            for ret in re.finditer(r'\breturn\s*\{',text[opening:closing]):
                begin=opening+ret.end()-1; end=end_group(text,begin)
                uses.append(dict(path=relative,line=line_at(raw,begin),owner=match[1],variable=match[2],form='RETURN_AGGREGATE',source=raw[begin:end]))
                for ordinal,(offset,value) in enumerate(split_top(raw[begin+1:end-1])):
                    if not value.strip():continue
                    if ordinal>=len(definitions[match[1]]):raise ValueError('return aggregate overflow')
                    field=definitions[match[1]][ordinal]['name']
                    rows.append(dict(record_kind='RETURN_AGGREGATE',parameter=match[1]+'.'+field,owner=match[1],field=field,path=relative,line=line_at(raw,begin+1+offset),expression=value.strip(),resolution='DECLARED_RETURN_POSITION',variable=match[2]))
    return rows,uses,paths


def write_csv(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,list(rows[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    definitions=schemas(); rows,uses,paths=rows_inventory(definitions)
    out=BASE/'inventory'
    out.mkdir(parents=True,exist_ok=True)
    records=sorted(rows,key=lambda r:(r['path'],r['line'],r['parameter'],r['record_kind']))
    for row in records:
        dtype=next(f['type'] for f in definitions[row['owner']] if f['name']==row['field'])
        row['static_numeric_value']='ZERO_INITIALIZED_COMPOSITE' if dtype in ('FoodMass','PositionM','BoxQ') and row['expression']=='{}' else expr_value(row['expression'])
    if args.check:
        with (out/'source_parameters.csv').open(encoding='utf-8',newline='') as f: old=list(csv.DictReader(f))
        assert [{k:str(v) for k,v in r.items()} for r in records]==old,'source inventory drift'
        print(f'PASS: {len(records)} parameter source expressions unchanged')
        return
    write_csv(out/'source_parameters.csv',records)
    write_csv(out/'configuration_uses.csv',uses)
    (out/'schema.json').write_text(json.dumps(definitions,indent=2)+'\n',encoding='utf-8')
    coverage=dict(structs={k:len(v) for k,v in definitions.items()},source_records=len(records),configuration_uses=len(uses),ambiguous=sum(r['resolution']=='AMBIGUOUS_OWNER_REVIEW' for r in records),source_files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],limitations=['Source expressions are not runtime enumeration. Scenario-dependent expressions are retained.', 'Name resolution is lexical; ambiguous ownership is explicit, not inferred as fact.', 'Returned config variables, lambda-built configurations and copies inherit source defaults and assignments; configuration_uses.csv preserves typed anchors.', 'Hard-coded rules, fixture control structs, world seed resources and JSON values require the complementary reviewed registries.'])
    (out/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:coverage[k] for k in ('structs','source_records','configuration_uses','ambiguous')}))


if __name__=='__main__':main()
