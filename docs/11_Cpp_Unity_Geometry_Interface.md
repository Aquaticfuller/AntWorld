# C++ / Unity geometry interface (v0.6 draft)

This is an ABI/data contract, not an implemented native plugin. C++ owns materials, individual positions, digging and connectivity. Unity consumes snapshots/differences and submits validated requests. GM and UI share Application authorization and core commands. No mesh replacement can masquerade as an ecological event.

## Message families

| Message | Direction / role |
|---|---|
| WorldCommand | UI/GM through Application to validated C++ mutation |
| WorldQuery | Read-only search, metrics/history |
| WorldSnapshot | Committed animal/location/life/geometry state to clients |
| GeometryDirtyBatch | Affected AABBs/chunks and flags |
| GeometryMeshPacket | Read-only vertices, normals, indices and materials |
| WorldEventBatch | Committed digging/connectivity/material/life evidence |

## Batches, versions and threading

Initial integration can use a C++ DLL in the Unity process, with one simulation writer and immutable published snapshots. GM can remain a separate runtime. C++ validates proposals, atomically updates geometry/materials, blocks stale routes, verifies/rebuilds navigation, publishes events and schedules mesh work. Unity acquires a snapshot, reads batches, discards older geometry versions, applies meshes on its main thread and releases the snapshot.

Every dirty/mesh record has source_geometry_revision; every client region tracks applied revision. Changes include neighboring halo/chunks. Avoid per-ant per-frame P/Invoke. A late mesh never becomes collision truth.

## Illustrative C ABI

Use opaque world/snapshot handles and fixed-width result codes. Structures include struct_size and api_version. GeometryDirty contains chunk_id, source_geometry_revision, AABB min/max doubles and dirty_flags. MeshMetadata contains chunk_id/revision, vertex/index counts, vertex stride and index element width.

Operations: acquire/release snapshot; copy dirty records into caller buffers; query mesh metadata; copy vertex/index bytes; and later create/destroy, advance, command, events and geometry queries. No STL containers, C++ exceptions, references, ambiguous owned allocations or compiler-dependent booleans cross the ABI.

Metadata and copying bind to the same immutable snapshot so intervening world changes cannot invalidate capacity assumptions. BUFFER_TOO_SMALL supports a safe size-query/retry. Define null/invalid handle behavior and disallow use after release. The concrete draft header is in ../contracts/antworld_c_api_v1.h; geometry-specific signatures remain proposals.

Version layouts explicitly: packed/interleaved position/normal/UV candidates, uint32 indices, stride, endianness, triangle winding, chunk origin and material groups. Simulation uses double world meters; rendering can use float chunk-local positions. Confirm handedness/winding visually in Unity. Keep ownership, lifetime, capacity, calling convention and alignment testable.

If mesh synchronization lags, a client may show a pending state or conservative proxy, not claim new passability. Avoid frequent MeshCollider rebuilding; use low-frequency proxies or picking queries where appropriate. Runtime mesh reference: https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/mesh/applyanddisposewritablemeshdata .

## Commands and GM

World Application separates WorldMutation (food/weather/permitted environmental edits), ViewMutation (camera/section/overlay), and ObservationTask (tracking/research). Requests include command_id, world_id, actor, authorization, operation/args, expected_revision where applicable, and requested SimTime. Return pending/committed/rejected, reason and evidence IDs. A pending receipt is not success.

Initial GM tools query morphology, excavation history, material ledgers and colony comparisons; focus a nest/section; track an excavator; and place food or schedule weather when authorized. Do not provide unrestricted ForceBuildRoom, MoveAntDirectlyToRoom or SetPopulation as ordinary ecological tools.

## Acceptance

Dirty packets, facts and ledgers from a commit agree on IDs/revisions. Reject stale packets; check cross-chunk seams. Sections/transparency leave state unchanged. A headless save reconstructed in Unity retains geometry/queries/connectivity. ABI changes require versioning/migration, not silent struct replacement. No client can bypass core validation. See document 20 for the v0.8 World API and document 12 for geometry tests.

Native plugin reference: https://docs.unity.com/en-us/engine/6000.3/manual/programming-environment/plug-ins/native/overview .
