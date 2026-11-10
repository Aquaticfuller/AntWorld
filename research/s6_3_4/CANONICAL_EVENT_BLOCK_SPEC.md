# Canonical event block specification

Storage schema `PRAGMA application_id=1096234835`, `user_version=2`. All binary integers are little-endian. World identity is two unsigned 64-bit words in high then low order. SQLite keys representing unsigned integers are exact 16-character lowercase hexadecimal text, ordered lexicographically. Simulated time is nonnegative int64 milliseconds. The maximum block contains 4,096 consecutive nonempty records. A publication seals its final partial block. A no-fact publication reuses the previous fact tail.

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 8 | ASCII `AWFACT01` |
| 8 | 2 | Envelope version `1` |
| 10 | 2 | Codec `1`, RFC 1950 zlib stream, writer pinned to zlib 1.3.2 at level 3 |
| 12 | 2 | Canonical fact schema `1`, existing `encode_event` |
| 14 | 2 | Reserved zero |
| 16 | 16 | WorldId |
| 32 | 8 | First EventId, inclusive |
| 40 | 8 | Last EventId, inclusive |
| 48 | 8 | First simulated time |
| 56 | 8 | Last simulated time |
| 64 | 4 | Exact uncompressed length in bytes |
| 68 | 4 | Exact compressed length in bytes |
| 72 | 32 | Previous block SHA-256, all zero for genesis |
| 104 | 32 | SHA-256 of bytes `[0,104)` followed by the compressed stream |
| 136 | variable | The entire zlib stream |

The decoded stream contains repeated `u32 byte_length, canonical_fact[byte_length]`. The current fact bytes are 159 bytes for an ordinary fact and 210 bytes for a biological observation. They carry the fact's EventId, WorldId, time, source ScheduledId, diagnostic fields, revision, kind, actor, colony, food resource, position, nutrient payload, outcome and other existing evidence. The observation extension includes the related target, bout, start and destination. For other two-participant facts the existing canonical payload identifies the related individual. Parametric geometry edit and soil parcel associations come from the unchanged authority/evidence links. The block preserves the exact encoded fact of each original observation, attempt, result and action.

The reader limits encoded bytes, record count and decoded length before allocating. Decompression must consume the entire payload and produce exactly the declared bytes. Each record must consume its length, match its world and next ID, respect nondecreasing time and increasing revision, and preserve exact first and last times. A standalone verifier can hash and decode one block. Verification of its position also checks the previous hash and time. All consecutive blocks through a published cursor are required on recovery.

## Continuation and anchor

The frame begins with `AWSTATE1` and retains the original Core format and variant headers, continuation fields and trailing FNV-1a-64 checksum. The journal length slot now identifies the required external cursor. Journal body bytes are supplied from the block chain. Explicit legacy export writes the original journal body and its original framing and checksum.

Anchor SHA-256 starts with ASCII `AWANCH01`. The seven little-endian u64 words that follow are WorldId high, WorldId low, generation, revision, cursor, FNV-1a-64 of the complete frame and simulated time in milliseconds. Append 32 bytes of parent anchor hash, 32 bytes of fact tail hash and the entire frame. Genesis parent and zero-fact tail use 32 zero bytes. The first migrated anchor may have a generation greater than one if earlier v1 state frames were already pruned. All retained generations thereafter are consecutive.

The SQLite index mirrors envelope identity and bounds. The manifest cursor equals the latest anchor cursor. These index copies accelerate access. During recovery, the authoritative encoded bytes, linked anchor and checked SQL copies must agree. The independent Python checker uses `hashlib`, `zlib` and `sqlite3` to verify wire bytes without the C++ reader.

[C++ block codec](../../cpp/storage/event_block.cpp) · [Core fact and frame codec](../../cpp/src/checkpoint.cpp) · [Python integrity checker](../../tools/verify_s6_3_4_archive.py)
