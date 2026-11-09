"""Verify the audit's no-Core-change claim and raw probe artifact hashes."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'experiments/s6_3_2'
from atlas_baseline import source_root
SOURCE=source_root()
source=json.loads((BASE/'core_and_tests_identity.json').read_text())
for item in source['files']:
    assert hashlib.sha256((SOURCE/item['path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==item['normalized_sha256'],item['path']
for name,item in json.loads((BASE/'probes/archive.json').read_text()).items():
    data=(BASE/'probes'/name).read_bytes();assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],name
print(f"PASS: {len(source['files'])} unchanged Core/test sources and complete raw probe hashes")
