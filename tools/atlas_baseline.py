"""Reproduce frozen source audits against their reviewed source, not later biology.

The archive is project-owned English source, not a paper. Its Git revision and
SHA256 manifest are committed. Existing source identities remain independently
checked; later stages must provide a separate current-source audit.
"""
import hashlib
import json
from pathlib import Path
import zipfile

PROJECT=Path(__file__).resolve().parents[1]
def source_root(release='s6_3_2_1'):
    base=PROJECT/'research'/release
    archive=base/'source_baseline.zip'
    record=json.loads((base/'source_baseline.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['sha256'],'frozen source archive changed'
    destination=(PROJECT/'out'/release/'source_baseline').resolve()
    destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for name in source.namelist():
            target=(destination/name).resolve()
            assert target.is_relative_to(destination),'invalid source archive path'
            if name.endswith('/'): continue
            data=source.read(name)
            if not target.exists() or target.read_bytes()!=data:
                target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
    return destination
