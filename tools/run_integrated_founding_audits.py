"""Audit every completed frozen batch into independent reproducible tables."""

import argparse
from pathlib import Path

from analyze_integrated_founding import verify
from package_integrated_founding_archives import sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--existing-audits",type=Path,action="append",default=[])
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    for archive in sources(args.raw):
        name=f"analysis-{archive.name}"
        if any((root/name/"audit.json").is_file() for root in (args.output,*args.existing_audits)):
            continue
        verify(archive,args.output/name)


if __name__=="__main__":
    main()
