#!/usr/bin/env python3
"""Verify SHA256 file list for the exported AntWorld design handoff archive."""
from pathlib import Path
import hashlib, sys
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'MANIFEST_SHA256.md'

def main():
    if not MANIFEST.exists():
        print('ERROR: missing MANIFEST_SHA256.md')
        return 2
    checked = 0
    for line in MANIFEST.read_text(encoding='utf-8').splitlines():
        if not line.startswith('| `') or ' | `' not in line:
            continue
        try:
            items = line.split('|')
            relative = items[1].strip().strip('`')
            expected = items[2].strip().strip('`')
            if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
                continue
            target = (ROOT / relative).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                raise ValueError('path escapes root')
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != expected:
                print(f'FAIL: {relative}  expected {expected} actual {actual}')
                return 1
            checked += 1
        except (OSError, ValueError, IndexError) as e:
            print(f'FAIL: {line}: {e}')
            return 1
    print(f'PASS: verified {checked} files')
    return 0 if checked else 2

if __name__ == '__main__':
    sys.exit(main())
