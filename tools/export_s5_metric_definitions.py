"""Export the version-1 metric catalog from the compiled C++ definitions."""
import argparse
import subprocess
from pathlib import Path

PREAMBLE = """# S5 metric definitions (version 1)

The table is exported from `antworld_storage` by `antworld_s5_experiment --metrics`.
All samples carry WorldId, owner, simulation time, generation, world revision,
committed EventId cursor and definition version. Owner zero is the world;
other owners are world-qualified ColonyIds. The world total is not another physical inventory.

Gauges are actual committed-boundary observations. Physiology is analytically
settled to that time using pure queries. Dead inventories remain accounted for.
Program counts include only living adults; unconfigured programs are explicitly unspecified.
Flows sum actual committed events in half-open windows `[begin_ms,end_ms)`.
Rejected actions never produce successful transfers. Internal transfers are not
external intake. Seeded identity creation is not an observed biological birth.

`coverage(world)` exposes the latest durable simulation time and evidence cursor.
Flow queries reject missing-world or future windows rather than assert an unobserved
zero. History pages and sampled series return only existing records; empty sample
ranges are missing observations. The latest durable cursor qualifies all results.

Fixed one-minute buckets retain exact count, sum, min, max, last and evidence bounds.
Gauge means are **sample-weighted**, not time-weighted: irregular save intervals
cannot establish continuous exposure. A bucket may be partial at the current
coverage boundary. No interpolation or biological event is inferred between samples.
Zero-valued gauges are observations; absent flow contributions mean zero only inside
the covered history. Foraging success remains **undefined** without a reviewed
trip-completion denominator. No temperature, humidity or semantic chamber statistics
are invented for unimplemented systems.

Integers use exact uint64 quantities. SQLite stores them as canonical 16-digit hex
text, never signed narrowing or approximate SQL SUM. Accumulator overflow rejects
and rolls back the save; this is a declared host arithmetic bound. The derived mean
is floating point and cannot preserve every integer above 2^53. nJ converts to J by
1e-9; ug to kg by 1e-9. Exact geometry q3 converts to m3 by multiplying by the
cube of `coverage(world).geometry_quantum_m`; every observation also retains its
quantum. Geometry metrics describe the world domain, not a fabricated colony-owned
or semantically identified nest. Fixture box volume is exact, with zero integer
integration residual; this does not calibrate the biological geometry model.

Event flows link to their actual EventId. Soil flows additionally require the matching
GeometryEdit, actual volume, parcel and configured dry/water densities. Restored
current gauges, event flows, identity histories and all stored buckets are reconciled
against checkpoint authority or retained raw observations. Historical observation
checksums detect accidental changes after old checkpoint blobs have been retired;
they are not cryptographic signatures or a way to recover a whole world.

"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('--output', type=Path, default=Path('docs/34_S5_Metric_Definitions.md'))
    args = parser.parse_args()
    table = subprocess.check_output([str(args.executable.resolve()), '--metrics'], text=True, encoding='utf-8')
    args.output.write_text(PREAMBLE + table, encoding='utf-8', newline='\n')
    print(f'Exported metric definitions to {args.output}')

if __name__ == '__main__':
    main()
