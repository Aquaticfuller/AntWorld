"""Preserve the first raw Linux replay difference and the portable byte comparison."""

import argparse
import csv
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
from zipfile import ZipFile

from analyze_s6_4_wp6b import check
from run_s6_4_wp6b import sha, write_json


FILES = ("initial.chk","final.frame","facts.bin")


def signatures(directory):
    return {k:{"sha256":sha(directory/k),"bytes":(directory/k).stat().st_size} for k in FILES}


def original_difference(a, b):
    check(len(a)==len(b),"different old event record lengths")
    offset, count, changes, first = 0,0,0,None
    while offset<len(a):
        length, = unpack_from("<I",a,offset)
        end = offset+length+4
        count += 1
        if a[offset:end]!=b[offset:end]:
            check(a[offset:offset+154]==b[offset:offset+154] and a[offset+162:end]==b[offset+162:end] and
                  a[offset+69]==4,"old histories differ beyond committed trail concentrations")
            changes += 1
            if first is None:
                first = dict(event=count, fact_start=offset, deposit_offset=offset+154,
                             windows=unpack_from("<d",a,offset+154)[0], linux=unpack_from("<d",b,offset+154)[0])
        offset = end
    check(first and first["event"]==421676,"did not reproduce the original Linux mismatch")
    return {"facts":count,"different_deposits":changes,"first":first}


def compare(directory, output, native_archives):
    initial = directory/"reference/borisovka-1-shaft-joint-balanced-5500"
    old_observed,old_durable = (directory/x for x in ("first-observed","first-durable-split"))
    before = dict(windows=signatures(initial),linux=signatures(old_durable))
    check(before["linux"]==signatures(old_observed),"old Linux save was inconsistent within Linux")
    after = {}
    for label in ("portable","portable-scout"):
        native = {host:signatures(directory/f"{label}-{host}") for host in ("windows","linux")}
        check(native["windows"]==native["linux"],"portable outputs differ")
        after[label]=native
    for folder,case,label in (
        ("joint","st_petersburg-1-dogleg-joint-balanced-5500","portable-dogleg-linux"),
        ("care","borisovka-1-shaft-water-absent-5500","water-portable-linux"),
        ("care","borisovka-1-shaft-wallwater-absent-5500","wallwater-portable-linux"),
    ):
        with ZipFile(native_archives/folder/(case+".zip")) as archive:
            original={key:{"bytes":len(raw),"sha256":sha256(raw).hexdigest()}
                      for key in FILES for raw in (archive.read(key),)}
        linux=signatures(directory/label)
        check(original==linux,f"{case}: portable files differ")
        after[case]={"windows":original,"linux":linux}
    with (directory/"portable-linux/summary.csv").open(encoding="utf-8",newline="") as stream:
        portable_state=next(csv.DictReader(stream))
    old_difference=original_difference((initial/"facts.bin").read_bytes(),(old_observed/"facts.bin").read_bytes())
    write_json(output,dict(old=before,original_difference=old_difference,portable=after,
                           final_facts=int(portable_state["events"]),time_ms=int(portable_state["time_ms"]),
                           comparison_source="ca9f931b620f6febf236d90714af1bb588190cba",
                           commands=dict(old_linux_observed="antworld_s6_4_wp6b parameters.txt out observed 172800000 750000 0 3 1 8000000 15",
                               old_linux_durable="antworld_s6_4_wp6b parameters.txt out durable-split 172800000 750000 0 3 1 8000000 15",
                               portable_joint="replace ecology4- with ecology5-; antworld_s6_4_wp6b parameters.txt out durable-split 172800000 750000 0 3 1 8000000 15",
                               portable_scout="antworld_ecological_recruitment 1 scout out durable portable")))
    print(old_difference)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("native_archives",type=Path)
    args=parser.parse_args()
    compare(args.directory,args.output,args.native_archives)
