#!/usr/bin/env python3
"""Catch untranslated CJK text in tracked UTF-8 files and commit messages.

This is a migration guard, not an automatic proof of English prose quality.
Binary assets are reported separately and require human metadata review.
"""
import json
from pathlib import Path
from string import Formatter
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TRANSLATION_VALUES = {"op0/locales/zh-CN.json"}

def untranslated(text):
    return any(0x3400 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF
               or 0x20000 <= ord(c) <= 0x323AF for c in text)


def translation_errors(name, text):
    """Allow localized message values, with English keys and matching placeholders."""
    try:
        messages = json.loads(text)
        if not isinstance(messages, dict):
            raise ValueError("a translation catalogue must be an object")
        errors = []
        for key, value in messages.items():
            if untranslated(key) or not isinstance(value, str) or not value.strip():
                errors.append(f"Invalid translation entry: {name}: {key!r}")
                continue
            source_fields = sorted(field for _, field, _, _ in Formatter().parse(key) if field is not None)
            translated_fields = sorted(field for _, field, _, _ in Formatter().parse(value) if field is not None)
            if source_fields != translated_fields:
                errors.append(f"Translation placeholders differ: {name}: {key!r}")
        return errors
    except ValueError as error:
        return [f"Invalid translation catalogue: {name}: {error}"]

names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
errors, binaries, checked = [], [], 0
for name in filter(None, names):
    path = ROOT / name
    if not path.is_file():
        errors.append(f'Tracked file missing (stage deletions first): {name}')
        continue
    if untranslated(name):
        errors.append(f'Untranslated path: {name}')
    data = path.read_bytes()
    try:
        text = data.decode('utf-8')
        if '\0' in text:
            binaries.append(name)
            continue
    except UnicodeDecodeError:
        binaries.append(name)
        continue
    checked += 1
    if name in TRANSLATION_VALUES:
        errors.extend(translation_errors(name, text))
        continue
    if text.isascii():
        continue
    for number, line in enumerate(text.splitlines(), 1):
        if untranslated(line):
            errors.append(f'Untranslated content: {name}:{number}')
messages = subprocess.check_output(['git', 'log', '--format=%h %s%n%b'], cwd=ROOT).decode('utf-8')
if untranslated(messages):
    errors.append('Untranslated Git commit message')
for error in errors:
    print(f'FAIL: {error}')
for name in binaries:
    print(f'BINARY: review language-bearing metadata manually: {name}')
if not errors:
    print(f'PASS: English source policy checked in {checked} tracked UTF-8 files and commit messages; {len(binaries)} binaries')
sys.exit(bool(errors))
