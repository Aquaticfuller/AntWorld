"""Sample the published ALTAA CSV members over HTTP ranges without storing the ZIP."""

from collections import OrderedDict
from datetime import datetime, timedelta
from hashlib import sha256
from io import SEEK_CUR, SEEK_END, SEEK_SET
from itertools import groupby
from statistics import median, quantiles
from urllib.request import Request, urlopen
from zipfile import ZipFile


URL = "https://zenodo.org/records/16893940/files/ALTAA_data.zip?download=1"
ARCHIVE_BYTES = 2_586_249_758
BLOCK = 1024**2
TRANSFER_LIMIT = 40 * 1024**2
DATES = ("20220904", "20220918", "20220925")
STAMP = "%Y_%m_%d_%H_%M_%S"


class RemoteZip:
    def __init__(self):
        self.cursor = 0
        self.cache = OrderedDict()
        self.received = 0

    def tell(self):
        return self.cursor

    def seekable(self):
        return True

    def seek(self, offset, whence=SEEK_SET):
        self.cursor = {SEEK_SET: 0, SEEK_CUR: self.cursor, SEEK_END: ARCHIVE_BYTES}[whence] + offset
        if self.cursor < 0:
            raise ValueError("Negative file offset")
        return self.cursor

    def block(self, index):
        if index not in self.cache:
            begin = index * BLOCK
            end = min(begin + BLOCK, ARCHIVE_BYTES) - 1
            length = end - begin + 1
            if self.received + length > TRANSFER_LIMIT:
                raise ValueError("Transfer budget exhausted")
            request = Request(URL + f"&range_offset={begin}", headers={"Range": f"bytes={begin}-{end}",
                              "User-Agent": "AntWorld evidence review (bounded transfer)"})
            with urlopen(request, timeout=25) as response:
                if (response.status != 206 or
                        response.headers.get("Content-Range") != f"bytes {begin}-{end}/{ARCHIVE_BYTES}"):
                    raise ValueError("Zenodo did not return the requested range")
                data = response.read(length)
            if len(data) != length:
                raise ValueError("Truncated range reply")
            self.received += length
            self.cache[index] = data
            if len(self.cache) > 8:
                self.cache.popitem(last=False)
        self.cache.move_to_end(index)
        return self.cache[index]

    def read(self, size=-1):
        remaining = ARCHIVE_BYTES - self.cursor
        size = remaining if size < 0 else min(size, remaining)
        if not 0 <= size <= TRANSFER_LIMIT:
            raise ValueError("Unbounded read")
        chunks = []
        while size:
            index, start = divmod(self.cursor, BLOCK)
            chunk = self.block(index)[start:start + size]
            chunks.append(chunk)
            size -= len(chunk)
            self.cursor += len(chunk)
        return b"".join(chunks)


def inspect(path, stream):
    start = datetime.strptime(path.rsplit("/rslt_", 1)[1][:-4], STAMP)
    left, right = [start + timedelta(hours=h) for h in (60, 84)]
    left_text, right_text = [v.strftime(STAMP).encode() for v in (left, right)]
    seconds = set()
    checksum = sha256()
    first = last = b""
    for line in stream:
        checksum.update(line)
        fields = line.split(b",", 3)
        if len(fields) != 4 or fields[2].strip() != b"motionPts" or b"(" not in fields[3]:
            continue
        stamp = fields[1].strip()[:19]
        first, last = first or stamp, stamp
        if left_text <= stamp < right_text:
            seconds.add(int((datetime.strptime(stamp.decode(), STAMP) - left).total_seconds()))
    if not first < left_text < right_text < last:
        raise ValueError("The selected sample does not span the complete window")
    positive = {s // 60 for s in seconds}
    groups = [(flag, sum(1 for _ in group)) for flag, group in groupby(i in positive for i in range(1440))]
    gaps = [n for active, n in groups[1:-1] if not active]
    print(path, "sha256", checksum.hexdigest(), "positive_seconds", len(seconds), "positive_minutes", len(positive),
          "interior_empty_minute_bouts", len(gaps), "median", median(gaps),
          "p90", quantiles(gaps, n=10, method="inclusive")[-1], "max", max(gaps), flush=True)


def main():
    remote = RemoteZip()
    with ZipFile(remote) as archive:
        for date in DATES:
            [path] = [name for name in archive.namelist()
                      if name.startswith(f"202208_3nests/worker01/{date}/rslt_") and name.endswith(".csv")]
            with archive.open(path) as stream:
                inspect(path, stream)
    print("Bytes transferred", remote.received)


if __name__ == "__main__":
    main()
