"""Audit every completed frozen batch into independent reproducible tables."""

import argparse
from pathlib import Path

from analyze_integrated_founding import dump, verify
from package_integrated_founding_archives import sources
from run_s6_4_wp6b import sha


def publish(archive, analysis_roots, published):
    published.mkdir(parents=True, exist_ok=True)
    records = []
    for batch in sources(archive):
        name = f"analysis-{batch.name}"
        source = next(root/name for root in analysis_roots if (root/name/"audit.json").is_file())
        target = published/batch.name
        target.mkdir(exist_ok=True)
        for name in ("audit.json", "worlds.csv", "censuses.csv"):
            (target/name).write_bytes((source/name).read_bytes())
        records.append(dict(batch=batch.name, completed_sha256=sha(batch/"completed.json"),
                            audit_sha256=sha(target/"audit.json"), worlds_sha256=sha(target/"worlds.csv"),
                            censuses_sha256=sha(target/"censuses.csv")))
    dump(published/"audit_index.csv", records)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--existing-audits",type=Path,action="append",default=[])
    parser.add_argument("--publish",type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    roots = (args.output, *args.existing_audits)
    for archive in sources(args.raw):
        name=f"analysis-{archive.name}"
        if any((root/name/"audit.json").is_file() for root in roots):
            continue
        verify(archive,args.output/name)
    if args.publish:
        publish(args.raw, roots, args.publish)


if __name__=="__main__":
    main()
