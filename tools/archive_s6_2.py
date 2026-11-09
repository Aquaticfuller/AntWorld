"""Archive unchanged S6.2 host evidence, excluding localized raw sensor prefixes."""
import argparse
import hashlib
import json
from pathlib import Path

from archive_s6_1 import archive


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('target', type=Path)
    p.add_argument('--append-corrected-sensors', action='store_true')
    args = p.parse_args()
    if args.append_corrected_sensors:
        for source in sorted(args.source.glob('session*/hwinfo_corrected*')):
            target = args.target/source.parent.name/source.name
            assert not target.exists(), 'refusing to overwrite sensor evidence'
            target.write_text(source.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    else:
        archive(args.source, args.target)
        for source in sorted(args.source.glob('session*')):
            if source.is_dir():
                archive(source, args.target/source.name)
    manifest = {path.relative_to(args.target).as_posix():
                hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(args.target.rglob('*')) if path.is_file() and path.name != 'files.json'}
    (args.target/'files.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
