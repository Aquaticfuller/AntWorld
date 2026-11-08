# AntWorld｜C++ ↔ Unity/C# 地下几何接口设计 v0.1

**归档版本：v0.6（2026-11-08）** · **状态：ABI/数据契约草案，非可编译实现**

## 0. 单一事实与边界

- `AntWorld.SimulationCore`（C++）持有三维材料、蚂蚁位置、挖掘和连通的唯一事实。
- Unity 只能通过受限命令查询/控制世界、消费只读快照和几何差分，不直接编辑土壤、网格来代表真实行为。
- 游戏 UI 和 Game Master 使用同一条 `World Application → Command Validation → Simulation Core` 命令通路。Game Master 具有玩家可调用的游戏工具能力，但自主执行受授权与审计约束。
- 原生插件通过 **C ABI** 导出，C# 用 P/Invoke 调用；原生 C++ 不跨 ABI 暴露 STL 对象、C++ 异常或引用。Unity 6 官方资料：https://docs.unity.com/en-us/engine/6000.3/manual/programming-environment/plug-ins/native/overview

## 1. 六种消息

| 消息 | 生产者→消费者 | 目的 | 是否可改变世界 |
|---|---|---|---|
| `WorldCommand` | UI/GM→Application→C++ | 创建食物、修改天气、时间控制等合法命令 | 仅引擎校验后可以 |
| `WorldQuery` | UI/GM→Application/C++ | 搜索实体、统计与历史 | 否 |
| `WorldSnapshot` | C++→Unity/分析 | 动物位置、生命状态、地形版本 | 否 |
| `GeometryDirtyBatch` | C++→Unity | 哪些 AABB/chunk 的网格版本变脏 | 否 |
| `GeometryMeshPacket` | C++→Unity | 顶点、法线、索引、材料组等只读几何结果 | 否 |
| `WorldEventBatch` | C++→EventStore/GM | 挖掘、打通、封堵、运土、出生/死亡等事实证据 | 否 |

**禁止**：AI/Unity 向 C++ 发送一份 Mesh 来替换真实土壤；不要让 AI 自由调用无约束 `SetGeometry()`。

## 2. 批量同步与线程模型

建议首版同进程：C++ 原生 DLL + Unity C#，C++ 由模拟线程或受调度串行 Tick 提交几何；Unity 主线程消费已完成的只读快照。Game Master 是独立 Agent 服务，经 World Application 层进行命令与查询（具体语言尚未锁定）。

推荐批次流程：

```text
[TICK N: C++ Core]
   处理 DigProposal → GeometryCommit(new_rev=R)
       → geometry_dirty(AABB, R)
       → mark nav stale / block affected edges
       → rebuild/validate affected nav
       → emit ExcavationCommitted(R)
       → queue MeshBuild(R)

[Unity frame]
   acquire immutable snapshot(handle, R or later)
   fetch dirty regions / mesh packets in batches
   discard out-of-order packets older than applied revision
   apply mesh update on Unity main thread
   update ant instancing and selected-ant overlay
   release snapshot
```

- **原子版本**：`geometry_revision` 单调递增，网格包带 `source_geometry_revision`，每个 chunk 维护 `applied_revision`。
- **不要拿过期 Mesh 作为物理真相**：C++ 运动应依赖权威几何/有效的保守导航。
- **跨块修改**：dirty batch 携带受影响的所有 chunk IDs 和 AABB halo，避免拼缝、法线断裂和漏刷邻块。
- **不提供每只蚂蚁每帧一个 P/Invoke 调用**；通过 contiguous/packed arrays 批量快照/网格读取。

## 3. C ABI 草案（示意性签名）

```c
/* Illustrative only: details, calling convention, alignment
   and ownership must be fixed and tested before implementation. */
typedef struct AW_WorldOpaque* AW_WorldHandle;
typedef struct AW_SnapshotOpaque* AW_SnapshotHandle;

typedef struct {
    uint32_t struct_size;
    uint32_t api_version;
    uint64_t chunk_id;
    uint64_t source_geometry_revision;
    double aabb_min_xyz[3];
    double aabb_max_xyz[3];
    uint32_t dirty_flags; /* mesh, nav, environment, etc. */
} AW_GeometryDirty;

typedef struct {
    uint32_t struct_size;
    uint32_t api_version;
    uint64_t chunk_id;
    uint64_t source_geometry_revision;
    uint32_t vertex_count;
    uint32_t index_count;
    uint32_t vertex_stride_bytes;
    uint32_t index_element_bytes;
} AW_MeshMetadata;

/* All functions return a stable AW_Result enum (int32).
   No C++ exception may escape; null/invalid handle returns an error. */
int32_t aw_snapshot_acquire(AW_WorldHandle world,
                            AW_SnapshotHandle* out_snapshot);
int32_t aw_snapshot_copy_dirty(AW_SnapshotHandle snapshot,
                               AW_GeometryDirty* out_array,
                               uint32_t capacity,
                               uint32_t* out_required);
int32_t aw_snapshot_get_mesh_meta(AW_SnapshotHandle snapshot,
                                  uint64_t chunk_id,
                                  AW_MeshMetadata* out_meta);
int32_t aw_snapshot_copy_mesh(AW_SnapshotHandle snapshot,
                              uint64_t chunk_id,
                              void* vertex_buffer, uint32_t vertex_bytes,
                              void* index_buffer, uint32_t index_bytes);
void aw_snapshot_release(AW_SnapshotHandle snapshot);
```

*此例不是已实现接口*。正式接口还需提供世界创建/销毁、时间推进、命令执行、事件批量读取、坐标/几何查询和快照查询。`struct_size/api_version` 用于向前兼容，不在 ABI 中返回由 Unity 随意释放的内存。

**并发竞态**：两阶段 `get_meta→copy_mesh` 必须绑定同一个 immutable snapshot handle；若取出元数据后原世界变化，也不会导致拷贝缓冲长度变动。允许两次查询后获得 `BUFFER_TOO_SMALL` 并重试。`snapshot_release` 后指针/handle 禁止继续访问。

### 3.1 网格顶点布局与坐标

建议在版本化规范中固定 packed interleaved vertex（position float3 / normal float3 / uv float2 或其他），索引使用 uint32；包含明确的 `vertex_stride`, `endianness`, `triangle_winding`, `chunk_origin_m` 和材料分组范围。`WorldCoord` 的 `X=东/Y=上/Z=北` 在 C++ 和 Unity 一致；对于三角形法向与绕序，必须以真实 Unity 画面进行左右手/三角形方向测试，不依赖外部库默认轴约定。

- 模拟采用 double 米制坐标；Unity 顶点在 chunk 局部位置用 float，chunk origin 为 double。
- 形状有版本：网格异步更新晚于逻辑几何时，Unity 应提示正在同步（必要时隐藏细节或使用保守代理），不能让视图假装已经通行。
- Unity 不在高频循环频繁替换 MeshCollider；蚂蚁寻路与碰撞均在 C++ 查询。如果镜头拾取/可视交互需要 collider，优先使用低频/简化代理或自定义 raycast。
- Unity 6.3 `Mesh.AllocateWritableMeshData` / `ApplyAndDisposeWritableMeshData` 可用于渲染网格更新，需正确管理 Unity 的 native buffer 生命周期： https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/mesh/applyanddisposewritablemeshdata

## 4. 世界命令与权限

World Application 定义游戏操作规范，例如 `PlaceFood`, `ScheduleWeather`, `FocusCamera`, `SetSectionPlane`, `SetTimeScale`, `FollowAnt`, `TrackAnt`, `SaveWorld`。前五类需要区分：

- **WorldMutation**：影响世界物理/生物状态，例如食物与天气；必须校验并记录来源。`GeometryEdit` 不能当作自由修改入口，玩家通常只能间接影响自然建巢。
- **ViewMutation**：移动镜头/剖切或显示热力图，完全不修改土壤几何和蚂蚁可达性。
- **ObservationTask**：建立追踪、统计查询、历史回放等持久任务。

建议命令字段：`command_id`（幂等）、`world_id`, `actor`, `authorization`, `operation`, `args`, `expected_world_revision`（适用时）、`requested_at_sim_tick`。所有工具结果以 `executed / rejected / pending + reason + affected_event_ids` 呈现，不能在工具成功前提前汇报已完成。

## 5. GM 能调用什么？

首批 Game Master 工具：

| 工具 | 只读或写 | 所属层 |
|---|---|---|
| `get_nest_geometry_summary` | 只读 | 统计/空间查询 |
| `query_excavation_history` | 只读 | 事件与历史 |
| `get_soil_ledger` | 只读 | 材料统计 |
| `compare_nest_depth` | 只读 | 多蚁巢统计 |
| `focus_nest` | 只改显示 | Unity 命令 |
| `set_section_plane` | 只改显示 | Unity 命令 |
| `track_excavating_ant` | 只改观察设置 | 追踪服务 |
| `place_food` / `schedule_weather` | 修改世界 | 受授权控制 |

**不提供**可绕过生物/空间规则的 `ForceBuildRoom`, `MoveAntDirectlyToRoom`, `SetPopulation` 作为正常玩家/GM工具。

## 6. 验收与版本迁移

- 同一 edit commit 的 `GeometryDirty`, `WorldEvent`, `SoilLedger` 必须具有一致版本/ID。
- 旧 Mesh 更新包不能覆盖新 revision；跨块接缝必须验证；剖面切换绝不改变模拟几何。
- 同一份 headless 存档在 Unity 重建后，空间查询和连通与 C++ 一致。
- ABI 版本更改需明确 schema migration；不能直接改变原有公开 struct 字段布局。
- Agent/Unity 都不能使世界发生未经校验的几何编辑。
