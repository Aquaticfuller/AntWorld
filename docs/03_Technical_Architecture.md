# AntWorld｜系统技术架构（v0.5）

## 1. 已确定总体栈

- **Simulation Core：C++**，真正的世界状态权威，不依赖 Unity，支持 headless 长时模拟、实验与回归。
- **Unity + C# 客户端**，负责 3D/2.5D、渲染、镜头、交互和图表。Unity 是视图，不是生物学事实源。
- **Game Master Agent Runtime：待选**，对照 Python/Hermes、C#/Microsoft Agent Framework、必要时轻量自建；对外只暴露 AntWorld 游戏专用工具。
- **数据库：SQLite 为首版候选**，快照、事件、聚合指标、重点个体历史；跨世界 GM 记忆需独立数据空间。

## 2. 依赖边界

```
 Unity C# Client <-- Render Snapshots/Events --> Application/World API
                                               |
                 Game Master <--- Tool Calls ---+--- Command Validation/Authorization
                                               |
                                      C++ Simulation Core
                                               |
                              Snapshot + Event + Analytics Data
```

- C++ 模拟核心从 UI / GM 直接调用中解耦；所有状态变更通过经过验证的命令进入。
- UI 和 GM 使用同一游戏功能/命令语义；GM 能力与玩家等价，但其*自行使用*高影响工具必须经过授权。
- 游戏事实和 GM 记忆分开；生态世界关闭 GM 也能运行。

## 3. C++ 核心模块建议

```
core/
  world/       WorldState, WorldClock, RandomStreams, EventScheduler
  entities/    Stable IDs, AntStore, OtherSpeciesStore, ColonyStore
  physiology/  Energy, Nutrients, Hydration, Development, Mortality
  perception/  LocalSensorSampling, SpatialIndex
  behavior/    HierarchicalTasks, ResponseThresholds, Actions
  memory/      RouteAssociations, Familiarity, Forgetting
  chemistry/   SurfacePheromoneField, Deposits, Decay
  colony/      ColonySharedResources, Trophallaxis, SocialInteractions
  nest/        ChamberTunnelGraph, Digging, SoilTransport, NestMicroclimate
  environment/ Climate, Food, Plants, Predators, SoilField
  nav/         Local3DMovement, SurfaceAndTunnelRouting
  scheduling/  MultiRateUpdate, EventQueue, LODBehavior
  history/     StructuredEvents, Snapshots, StatEmitters
  api/         C-ABI world handles, commands, queries, batch snapshots
```

## 4. ID 与数据模型

- 强类型命名空间：`WorldId`, `ColonyId`, `AntId`, `NestId`, `ChamberId`, `TunnelId`, `EventId`, `CommandId`。
- 所有世界 ID 必须显式带入跨世界查询；禁止跨世界仅凭 `AntId` 匹配。
- 蚂蚁的持久 ID 从卵阶段建立，个体状态按生理、空间、行为、有限记忆、调度多组件组织，适合 SoA 批处理。
- `ColonyState` 管理共同生物资源/气味及统计，不作为自动分配工蚁职业的中央控制器。
- `FoodSource` 保存真实质量、C/P/W 等营养和腐败；移动/取食/交哺按收支计算。
- `WorldEvent` 至少包含世界、时间、实体、位置、类别、参数、来源（自然/玩家/GM）和证据 ID。

## 5. 空间表示

- 世界坐标真实米制；蚂蚁毫米尺度；视觉放大不影响物理长度。
- 首版 24m × 24m，建议 2m × 2m chunk，共 144 个 chunk，可按空间扩展。
- 地表：高度场 + 独立立体物体/植物/石块/树根及局部可行走表面。
- 地下：粗土壤材料场、局部稀疏体积/SDF、参数化隧道/巢室，动态几何与拓扑图同步。
- 寻路：长距离巢室/隧道/出口网络 + 当前位置局部移动、避障、接触。隧道交叉不代表连通。
- 信息素场沿可通行基底稀疏表达，初版不必把全空间当成高分辨率气体扩散网格。
- 巢穴挖掘更新真实体积、土粒搬运、通行边界和局部温湿度；局部刷新碰撞和渲染网格，不全世界重建。

## 6. LOD 与时间

不同维度分级：行为频率、环境场精度、历史记录精度、渲染细节彼此独立。

| 层级 | 逻辑 |
|---|---|
| L0 | 近景或重要交互：精细感知/局部动作/接触 |
| L1 | 普通近区域：保留个体行为/路径，降低更新频率 |
| L2 | 远处已具体模拟个体：保留 ID、生理、任务、路程、重要事件，稀疏更新 |
| L3 | 地图之外的背景生态：按种群模拟，不冒充每只个体有精细生命历史 |

- 统一整数模拟 Tick；精度与更新频率必须由验证决定。
- 倍速不能只是让所有个体每秒执行更多高精细物理帧；应使用低频状态推进与离散事件。
- 在精度边界发生接触、战斗、食物交换等情境时，恢复兼容的交互精度。
- 多次重复不同速度/步长的统计一致性实验，不要求不同并行顺序下逐位相同。

## 7. C++–Unity 边界

- C ABI：版本化消息结构、`World_Create`, `World_Advance`, `World_QueryBatch`, `World_Execute`, `World_Save` 等（仅接口草案）。
- Unity 使用 P/Invoke 与 native 库，批量拉取可见/关注的 ant render snapshots。
- 不逐个工蚁每帧跨语言调用；数据缓冲按明确的 ownership、capacity、layout、alignment 和版本处理。
- 允许独立 C++ 无画面 runner 在不使用 Unity 的情况下进行生态研究与 benchmark。
- 渲染插值只改变画面，不回写 Simulation Core 真实坐标。

## 8. API 与 Agent

- `QueryWorld`, `QueryAnt`, `QueryColonyMetrics`, `GetHistory`, `FocusCamera`, `PlaceFood`, `ScheduleWeather`, `SetTimeScale`, `WatchAnt`, `SaveWorld` 等是统一应用工具接口候选。
- 区分只读数据、客户端镜头命令、世界环境修改、存档/删除等高影响动作。
- 操作：授权→实体/空间/参数校验→幂等执行→审计→通知界面/GM。
- GM 不拥有直接系统命令、随意改磁盘文件或绕过引擎内部状态的权限。
- 事件检测器/研究任务调度器可以低成本持续运行，LLM 仅在重要事件/玩家对话/定期分析时调用。

## 9. 存储建议

分三个逻辑空间：世界快照、结构化事件+时间序列、Game Master 跨世界持久记忆。

数据类型示例：`world_snapshots`, `entities`, `life_events`, `world_events`, `metric_samples`, `tracked_trajectories`, `gm_identity`, `gm_memories`, `gm_goals`, `tool_audit`。

- 保存世界快照以避免从创世时刻重放全部事件。
- 常规工蚁的高频位置不全部永久保存；重点个体高频采样，普通个体记重要事件和汇总。
- 指标有稳定定义（工蚁数是否包括蛹等），每个统计点带世界时间和种群 ID。
- 存档恢复后检查活体 ID 总数与统计、营养收支、巢穴连通与队列状态。

## 10. 性能目标与不确定性

- **最早可玩原型**：2 窝黑园蚁、约 50–200 个体、一个动态三维巢穴，完整查询/GM 链路。
- **后续压力测试**：500–2,000 个体；成熟版本 20,000+ 是目标而非已实现能力。
- **画面目标**：正常观察争取 60fps；应分别量化模拟、渲染、数据库、动态网格更新成本。
- 技术风险：密集局部交互、挖掘碰撞/寻路更新、高频表面信息素、长期日志体积、跨精度连续性。
- 需要尽早原型验证，不预先声称这些目标已可达到。

## 11. 三维建巢补充（详见 09 专题）

- 统一几何真相：材料占用 + 持久化局部编辑；不要让 `NestGraph`、Unity Mesh 和独立体素各自成为可修改的真相。
- 掘进原子提交：验证可达界面、材料、净空与版本 → 扣除土壤/生成运输批次 → 更新权威几何 → 局部失效导航 → 重建 → 发布事件与渲染脏区。
- 保留 `GeometryVersion`, `GeometryEditId`, `FrontierId`, `SoilParcelBatch`, `NestMorphometry`；土壤干质量、水分账和通道连通必须能被测试。
- 微气候分离：土壤含水率 ≠ 巢室空气相对湿度；首版热传导与保守水量模型采用低频多精度，而非全3D微尺度高成本水热耦合。
- 技术对照：参数化切除编辑与局部 SDF 缓存 vs 稀疏占用体积为权威；尚未确定具体算法。

## v0.6：参数化地下几何与 Unity 接口已确定的细化

用户已选择参数化挖掘/回填编辑为几何权威、局部 SDF 为加速缓存（不再对 A/B 同等候选）。C++ 内 `InitialSolid + OrderedGeometryEdits` 负责世界的物理事实，`SdfBrickCache/RenderMesh/CollisionProxy/NestGraph` 均为版本化派生；应用层禁止 Unity/Agent 自由覆盖几何。`GeometryTransaction` 绑定真实移土体积、土粒搬运、材料账和 `geometry_revision` 进行原子提交。

C++↔C# 使用受版本管理的 C ABI；推荐 immutable snapshot + 两阶段 mesh metadata/copy 到调用方缓冲区、dirty batch、严格生命周期和 `struct_size/api_version`，不暴露 STL/异常，不逐蚂蚁逐帧调用 P/Invoke。Unity 网格由 dirty region 局部重建，模拟碰撞/净空留在 C++，Unity 的网格碰撞不能反向决定可通行性。详见专题 `10_...` / `11_...` / `12_...`。

## v0.7：混合事件调度与世界事务（参见 `13`）

- 世界内部：`int64 SimTime`、FutureEventSet、连续积分过程和按事件/LOD的多频率唤醒；**不等于每毫秒更新全部个体**。
- 对共享状态：个体局部感知 → ActionProposal → 确定性仲裁 → 单写入事务 commit → WorldEvent/统计/几何版本。所有改变要在同一世界提交屏障发生。
- 外部命令（UI/GM）排入 CommandInbox，校验 world、权限、幂等，未来安全边界执行。GM 模型延迟/失效不阻塞模拟。
- 存档包含 FutureEventSet、随机流、队列序号、实体状态、时间积分进度、几何/物料状态及已执行命令 ledger，不允许“只有高层历史日志”却宣称完整恢复。
- 核心强制测试 `SCH-01`–`SCH-30`，首个整体 P0 见 `15_Minimal_Integrated_Vertical_Slice.md`。
- 这些是**拟采用的工程规范**，时间频率、数据结构、存档协议待实际原型验证。
