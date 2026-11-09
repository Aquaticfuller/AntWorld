"""Read-only institutional/public source retrieval; licensed bodies stay ignored."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('requests', type=Path)
    p.add_argument('--workers', type=int, default=2, choices=range(1, 5))
    args = p.parse_args()
    folder = ROOT/'out/s6_3_2_1/sources'
    folder.mkdir(parents=True, exist_ok=True)
    def fetch(entry):
        target = folder/entry['filename']
        assert target.parent == folder and entry['url'].startswith('https://')
        record = dict(entry, accessed_utc=datetime.now(timezone.utc).isoformat())
        try:
            cached = target.exists()
            if not cached:
                request = urllib.request.Request(entry['url'], headers={'User-Agent': 'AntWorldEvidenceAtlas/1.0 (academic source verification)'})
                with urllib.request.urlopen(request, timeout=45) as response:
                    content = response.read()
                    record.update(resolved_url=response.url, content_type=response.headers.get('Content-Type', ''))
                target.write_bytes(content)
            data = target.read_bytes()
            record.update(status='CACHED_NOT_REVALIDATED' if cached else 'FETCHED_NOT_YET_READ', bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        except Exception as error:
            record.update(status='ACCESS_FAILED', error=str(error))
        return record
    entries = json.loads(args.requests.read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(fetch, entries))
    args.requests.with_name(args.requests.stem+'_receipts.json').write_text(json.dumps(records, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
    for record in records:
        print(record['filename'], record['status'], record.get('bytes', record.get('error', '')))

if __name__ == '__main__':
    main()
