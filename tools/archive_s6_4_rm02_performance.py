"""Publish complete timing rows and receipts while keeping unrelated process names local."""

import argparse
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def remove_process_lists(value):
    changed = False
    if isinstance(value, dict):
        if "processes" in value:
            value.pop("processes")
            changed = True
        for item in value.values():
            changed |= remove_process_lists(item)
    elif isinstance(value, list):
        for item in value:
            changed |= remove_process_lists(item)
    return changed


def copy(source, target):
    target.mkdir(parents=True)
    files = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        original = path.read_bytes()
        exported = original
        if path.suffix == ".json":
            value = json.loads(original)
            if remove_process_lists(value):
                exported = (json.dumps(value, indent=2) + "\n").encode()
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(exported)
        files.append(dict(path=relative.as_posix(), source_sha256=sha(original), public_sha256=sha(exported),
                          bytes=len(exported), process_inventory_removed=exported != original))
    if not files:
        raise ValueError("source evidence directory is empty")
    (target / "public_export_manifest.json").write_text(json.dumps(files, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    print(f"Exported {len(files)} evidence files")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    copy(args.source, args.target)


if __name__ == "__main__":
    main()
