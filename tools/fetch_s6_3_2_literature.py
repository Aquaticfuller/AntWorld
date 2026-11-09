"""Cache licensed research locally; never publish the downloaded article bodies."""
import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('requests', type=Path)
    args = parser.parse_args()
    folder = ROOT / 'out/s6_3_2/literature'
    folder.mkdir(parents=True, exist_ok=True)
    entries = json.loads(args.requests.read_text(encoding='utf-8'))

    def fetch(entry):
        dest = folder / entry['filename']
        assert dest.parent == folder and entry['url'].startswith('https://')
        record = dict(entry, accessed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        try:
            if not dest.exists():
                request = urllib.request.Request(entry['url'], headers={'User-Agent': 'AntWorldResearchAudit/1.0 (academic literature verification)'})
                with urllib.request.urlopen(request, timeout=45) as response:
                    data = response.read()
                    record['resolved_url'] = response.url
                    record['content_type'] = response.headers.get('Content-Type', '')
                dest.write_bytes(data)
            data = dest.read_bytes()
            record.update(status='FETCHED_REQUIRES_CONTENT_INSPECTION', bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        except Exception as error:
            record.update(status='ACCESS_FAILED', error=str(error))
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, entries))
    receipt = args.requests.with_name(args.requests.stem + '_access.json')
    receipt.write_text(json.dumps(records, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    for record in records:
        print(record['filename'], record['status'], record.get('bytes', record.get('error', '')))


if __name__ == '__main__':
    main()
