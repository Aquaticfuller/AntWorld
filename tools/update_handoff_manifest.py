#!/usr/bin/env python3
"""Regenerate hashes of the maintained English handoff and implementation ADRs."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
paths = [ROOT / name for name in (
    'AGENTS.md', 'CODEX_START_HERE.md', 'README_HANDOFF.md', 'tools/verify_handoff.py'
)]
for directory, pattern in [('docs', '*.md'), ('codex_tasks', '*.md'),
                           ('contracts', '*.h'), ('schemas', '*.json'), ('scenarios', '*.json')]:
    paths.extend((ROOT / directory).glob(pattern))
lines = ['# AntWorld English handoff: SHA-256 manifest', '',
         'This manifest covers maintained English design files, contracts and fixtures.',
         'It does not describe the original untranslated archive. Regenerate after design changes.',
         '', f'Files: {len(paths)} (excluding the manifest itself).', '',
         '| Path | SHA-256 | Bytes |', '|---|---|---:|']
for path in sorted(paths):
    data = path.read_bytes()
    lines.append(f'| `{path.relative_to(ROOT).as_posix()}` | `{hashlib.sha256(data).hexdigest()}` | {len(data)} |')
(ROOT / 'MANIFEST_SHA256.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
print(f'Updated English handoff manifest: {len(paths)} files')
