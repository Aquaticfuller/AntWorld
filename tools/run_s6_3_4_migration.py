"""Run a verified shadow migration and retain source and canonical checksums."""

import argparse
from pathlib import Path
import subprocess
import time

from run_s6_3_4 import file_hash, write_json
from verify_s6_3_4_archive import audit, legacy_canonical, require


def source_bytes(path):
    files = {"database": file_hash(path)}
    wal = Path(str(path) + "-wal")
    # SQLite may create an empty WAL and a shared-memory coordination file
    # when a read-only connection joins a WAL database. No durable frames
    # exist in an absent or zero-length WAL.
    if wal.is_file() and wal.stat().st_size:
        files["-wal"] = file_hash(wal)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive_executable", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("shadow", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    binary = args.archive_executable.resolve(strict=True)
    source = args.source.resolve(strict=True)
    args.evidence.mkdir(parents=True)
    hashes = source_bytes(source)
    size = source.stat().st_size
    start = time.monotonic()
    with (args.evidence / "console.log").open("wb") as log:
        result = subprocess.run([binary, "migrate", source, args.shadow.resolve()],
                                stdout=log, stderr=subprocess.STDOUT)
    elapsed = time.monotonic() - start
    after = source_bytes(source)
    unchanged = hashes == after
    receipt = {"exit_code": result.returncode, "migration_seconds": elapsed, "source_database_bytes": size,
               "source_before_sha256": hashes, "source_after_sha256": after, "source_unchanged": unchanged,
               "archive_executable_sha256": file_hash(binary)}
    write_json(args.evidence / "migration.json", receipt)
    require(result.returncode == 0 and unchanged, "migration failed or changed the source")
    worlds = audit(args.shadow)
    for world in worlds:
        require(legacy_canonical(source, world["world"]) == (world["facts"], world["canonical_sha256"]),
                "migrated canonical stream differs from v1")
    receipt.update(shadow_database_bytes=args.shadow.stat().st_size, worlds=worlds, canonical_equal=True)
    write_json(args.evidence / "migration.json", receipt)
    print(f"Verified shadow in {elapsed:.3f} s")


if __name__ == "__main__":
    main()
