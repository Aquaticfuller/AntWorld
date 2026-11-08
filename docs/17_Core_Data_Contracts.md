# AntWorld｜C++ Simulation Core 数据契约 v0.8

**性质：Codex 实施前的规范性草案。** 本文确定 P0 内部概念、类型、单位、所有权和最小接口语义；字段是实现契约，不等于已完成代码。除用户确认的产品决定外，详细类型采用 v0.8 参考实现默认值，可通过 ADR 变更。

## 1. 单位、坐标与身份

| 对象 | 类型候选 | 单位或规则 |
|---|---|---|
| `SimTime` | `int64_t` 强类型 | P0 每 tick = 1 ms。时间值表示历史位置，非更新频率 |
| `WorldId` | `(uint64_t high, uint64_t low)` | 跨世界全局唯一；不存在只用 `AntId` 的跨世界查询 |
| `EntityId` | `uint64_t` + 类型语义封装 | 世界内单调分配、永不重用；工蚁/幼体共用稳定个体 ID |
| `ColonyId`, `ResourceId`, `RegionId` | `uint64_t` 强类型 | 世界内 ID；序列化时带 world ID |
| `EventId` | `uint64_t` 或事件复合键 | 每个世界单调递增；只分配给**已提交**事实事件 |
| `CommandId` | 128-bit 外部唯一标识 | 重试幂等及审计；命令和事件不是同一个 ID |
| 坐标 | `double x,y,z` | 米；X 东方、Y 向上、Z 北方。地表常在 Y≈0，地下 Y<0 |
| 长度 | `double` | 米；外观需要的毫米单位只作转换 |
| 可守恒质量 | P0 `int64_t` | 微克 `µg`；正库存/正流量，非负，注意数值溢出 |
| 身体可用能量 | `double` | 焦耳 J；必须通过质量到能量的明确变换才可增加 |
| 温度 | `double` | 摄氏度，热传导等公式使用温差时与 K 等价；需要绝对温度公式时转 K |
| 时间间隔 | `int64_t` | ms；积分功率按秒换算 |
| 概率 | `double` | [0,1]，非法参数拒绝 |

**嵌套引用示例**：`EntityRef = { WorldId, EntityId, EntityKind }`。不可把 `A-017` 这种展示名称当作数据库主键。

## 2. WorldState 唯一写入者

`WorldState` 属于一个 `WorldRuntime` 实例，含：

- `WorldIdentity`: `WorldId`, `worldSeed`, `schemaVersion`, `physicsVersion`。
- `WorldClock`: `simTimeMs`, `worldRevision`, `phase`, `eventSequence`。
- `EntityStores`: `AntStore`, `ColonyStore`, `ResourceStore`, `BroodStore`（幼体若共享 AntStore 则只保留专用组件，不复制身份）。
- `SpatialWorld`: 初始土壤，按序应用的参数化编辑，局部 SDF/导航派生 cache 及 `geometryRevision`。
- `Environment`: 只存实际需要的资源、局部场状态与下一次更新时刻。
- `FutureEventQueue`, `PendingActionProposals`, `CommandInbox`, `IdempotencyLedger`。
- `RngState`, `MetricsAccumulators`, `EventJournalCursor`。

仅 `WorldRuntime` 的提交路径能够修改这些数据。`Query` 必须只读，不消耗 RNG、也不安排新的生物事件。

## 3. AntStore：一个 ID，多个组件

逻辑级 AntState 由下列组件组成；高频数据按 SoA（Struct of Arrays）实现，记录中用 Stable ID→密集槽映射寻址。密集槽可以因压缩改变，`EntityId` 绝不能改变。

| 组件 | 字段（候选） | 约束 |
|---|---|---|
| `AntIdentity` | `entityId`, `colonyId`, `speciesId`, `caste`, `birthTick` | 从卵起始终不变；为出生已在初始世界的个体记录 `seeded=true` |
| `AntLife` | `stage`, `stageProgress`, `alive`, `developmentVersion`, `deathCause` | 阶段有序，`Dead` 为终态；死亡事件幂等 |
| `AntPhysiology` | `bodyEnergyJ`, `hydrationUg`, `health`, `injury`, `cropCarbUg`, `cropWaterUg`, `carriedResourceId` | 数值带单位；身体能量不等同于嗉囊食品质量 |
| `AntSpatial` | `positionM`, `orientation`, `regionId`, `currentPortal`, `pathRef` | position 在权威空间可达区域（幼体固定在合法位置） |
| `AntBehavior` | `highLevelTask`, `actionState`, `targetEntity`, `taskEnteredTick`, `cooldownUntil`, `responseThresholdsRef` | 任务和动作可组合，不把运动/搬运等全塞一个互斥 enum |
| `AntPerception` | `localCues`, `sampleTick`, `sensoryBudget` | 一次采样只包含局部可获得的信息，禁止全局食物坐标泄漏 |
| `AntMemory` | 少量 `RouteMemory`/气味关联、强度、最近强化时间 | 不存语言故事，强化/衰减按规则；历史数据库独立 |
| `AntScheduler` | `simLod`, `nextWakeupTick`, `plannedEventIds` | L0/L1/L2 变更不重建生物身份 |

生命周期枚举 P0：`Egg → Larva → Pupa → Adult → Dead`，成年品级（Queen/Worker/Male）作为独立字段；已明确死亡原因可以在任何阶段进入 Dead。**羽化绝不创建一个新的 AntId。**

P0 可只实作 Worker/Queen 和被预置的幼体；婚飞与多蚁后按物种规则后续扩展。不要因此修改上层生命周期契约。

## 4. ColonyStore 不得变成工蚁指挥器

字段：`colonyId`, `speciesId`, `foundationTick`, `queenEntityIds`, `nestIds`, `nestmateCue`, `resourceStorageRefs`, `broodDemandDerived`。

蚁群人口、任务比例、总储备等以实体/资源数据聚合，是统计缓存，不是可以被 Game Master 直接修改的魔法数值。`ColonyStore` 不提供 `AssignWorkersToTask(n)` 这种中央分配能力。

## 5. ResourceStore：食品可用质量与搬运账

建议 P0 以统一 `ResourceParcel` 表示一包食物/土粒；食品与土壤**类型分开**，不能互相转换。食品：

```text
FoodSource { resourceId, positionM, totalMassUg,
             carbsUg, proteinUg, waterUg, otherMassUg,
             decayState, foodKind, ownerEntityId? }
```

**约束**：各组成质量之和 = 总质量；取走的是对应成分的一个可追溯转移，不允许从 `totalMassUg` 和 `carbsUg` 分别扣掉同一份物质两次。所有库存使用整数微克；能量改变另外记代谢与转化账。

`CropContents` 是成年工蚁可转运液体营养的一部分，**属于工蚁持有库存**，不能同时再计入一个并行的“全蚁群食物池”。固体 `CarriedFoodParcel` 单独表示。

土粒使用 `SoilParcel { parcelId, sourceEditId, dryMassUg, waterMassUg, carrierId?, location, state }`，其质量来源必须对应实际被切出的土壤交集。

## 6. 参数化地下几何

`InitialSolid` + `GeometryEditLog` 是权威几何；编辑记录候选：

```text
GeometryEdit {
  editId, worldId, operationKind [Excavate|Fill],
  geometryPrimitiveType, primitiveParameters,
  requestedByEntityId, simTimeMs,
  expectedRevision, committedRevision,
  affectedAabbM, materialDeltaDryUg, materialDeltaWaterUg
}
```

物理编辑只有验证/事务完成后才成为 `GeometryEdit`；未提交的 `DigProposal` 不得改变几何。

`SdfBrickCache`, `NavGraph`, `CollisionProxy`, `RenderMesh` 都有源版本与失效状态。跨越不同高度的通道在俯视交叉不自动连通；只有真实几何连通、达到相应个体净空，才建立可通行 Portal。回填必须支持删除连通。

详见 `10_Parametric_Geometry_Implementation.md`、`11_Cpp_Unity_Geometry_Interface.md`。

## 7. ActionProposal 是意图；WorldEvent 是事实

建议 P0：

```text
ActionProposal {
  proposalId, actorId, actionKind, targetId?,
  proposedAt, requestedQuantities, preconditionRevision,
  localEvidence, requestedRegion
}
```

候选类型 `Move / Explore / FollowTrail / CollectFood / ReturnNest / Trophallaxis / FeedBrood / Rest / Excavate / PickUpSoil / DropSoil`。具体模块按实现批次逐步加入，不得一开始创建伪造的完成事件。

`WorldEvent` 是**已提交事实**：

```text
WorldEvent {
  eventId, worldId, simTimeMs, eventType,
  actorEntityId?, relatedEntityIds[], targetResourceId?,
  positionM?, worldRevision, geometryRevision?,
  origin [Natural|Player|GameMaster|ScenarioSeed],
  commandId?, eventPayload, evidenceReferences[]
}
```

情绪解说与推测不属于 WorldEvent；Game Master 生成的文字应挂在事件引用之上，不能作为生态真相覆盖它。

## 8. Runtime 内部 API 语义（C++ 强类型）

```cpp
struct SimTime { std::int64_t milliseconds; };
struct AdvanceResult { SimTime reached; std::uint64_t committed_revision; };

class ISimulationRuntime {
public:
    virtual AdvanceResult advance_to(SimTime target) = 0;
    virtual CommandReceipt enqueue_command(const WorldCommand& command) = 0;
    virtual ReadOnlySnapshot acquire_snapshot(const SnapshotFilter&) const = 0;
    virtual EventBatch read_committed_events(EventCursor, std::size_t limit) const = 0;
    virtual ~ISimulationRuntime() = default;
};
```

这是契约示意，并非编译代码；所有具体类型都要在 P0 合约中定义并提供测试。`advance_to` 不允许目标时间倒退。`enqueue_command` 返回 *accepted/pending/rejected*；只有相应事实事件提交后，才能声称世界操作成功。

## 9. 所有权与并发边界

- `WorldRuntime` 唯一拥有活跃世界；工蚁/资源 stores 的密集槽仅内部可访问。
- 写入只发生在统一提交屏障；只读查询返回带 `worldRevision` 的**不可变**快照或拷贝。
- `WorldSnapshot` 的内存生命周期明确：引用计数句柄或调用者缓冲区，不暴露长期可变内部指针。
- Unity/C# 使用已发布快照；Game Master 对外 API 只接受 typed query/command，不可将代码注入模拟器。
- 使用 `WorldId + EntityId` 进行多世界引用解析。统一日志使用 `SimTime`，GM 另外标记现实时间。

## 10. 代码/存档版本升级

- 类型变更必须标记 `schemaVersion` 和对应迁移/拒绝规则。
- 生物参数要带 `modelVersion`、`parameterSource`（`ENGINEERING_FIXTURE` 或确实有文献校准时才 `LITERATURE_CALIBRATED`）。
- 修改 Core 行为不能使旧存档被静默按新规则解释：可拒绝不兼容版本或提供明确迁移，并记录 `physicsVersion`。
- 明确端序、整数宽度、结构布局、序列化字段名；ABI 不允许暴露 STL 或 C++ 异常。
