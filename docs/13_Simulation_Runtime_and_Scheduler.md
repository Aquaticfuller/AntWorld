# AntWorld｜C++ Simulation Runtime、混合调度与状态事务 v0.1

**归档版本：v0.7（2026-11-08）**  
**设计性质：综合技术规格草案，尚未实现；具体时间步长/物种参数需验证。**  
**承接：** `03_Technical_Architecture.md`、`04_Biology_and_Social_Simulation.md`、`09`–`12` 地下几何专题。

## 0. 本轮任务与约束

**目标：** 将食物/交哺、代谢、发育、工蚁任务、三维挖掘、植物/天气、统计、Game Master 命令连接到同一条**因果一致**的模拟时间线。

**用户已经确认且不可擅改**：C++ 独立 Simulation Core 是世界权威；Unity C# 只读取展示；跨世界单一人格 Game Master 可访问玩家同等游戏功能、但自主环境干预需授权；每只具体模拟蚂蚁保留 ID 与基础生命档案；24m×24m 首版可分块扩展；真实 3D 地下、参数化挖掘编辑+局部 SDF 缓存为权威几何路线。

**本轮新增提议（尚未获得用户逐项确认）**：整数时间戳、混合事件/连续时间调度、统一提交屏障、分级 LOD 的因果同步、快照与日志一致性方案、测试矩阵。不能标成已确定的生物学事实。

## 1. 非功能性不变量（必须测试）

1. **世界独占写入**：只有 C++ Core 的调度器能提交生物/物理世界状态；Unity 和 GM 都不能直接修改。
2. **因果时间不倒退**：事件时间 `t_event >= now`；任何新事件不能影响它之前的状态。
3. **物质收支**：营养/水/土壤的来源、转移、消耗/外排可以在声明的数值容差内核算；模拟代谢的物质汇项必须有记录。
4. **身份与生命唯一性**：一个卵分配一个持久 AntId；羽化不创建替代 ID；死亡事件与人口统计不能重复。
5. **空间一致性**：工蚁位置必须位于权威几何的可达区域；过期导航保守封锁。几何提交与物料账不能部分成功。
6. **跨尺度保真**：L0/L1/L2 转换不重置个体身份、营养、时间、已确认事件和关注状态；L3 背景种群不声称存在可精确回放的逐只个体。
7. **可解释性**：所有事实性世界事件包含 world ID、sim time、entity IDs、来源和关联版本；GM 可追溯、不可虚构事实。
8. **不可重复执行**：同一 `CommandId` 重试最多提交一次物理修改。
9. **视图隔离**：暂停/移动镜头/打开图表/透明剖面/静音或禁用 GM 均不修改模拟规则。
10. **可恢复性**：一份原子一致的 checkpoint 含有未来事件、各实体状态、随机流、几何版本及命令去重记录；恢复不重算已提交动作。

## 2. 三个不同的时间概念

| 时间 | 定义 | 能不能改变游戏事实 |
|---|---|---|
| `SimTime` | 世界内时间，单调递增，所有事件用它标记 | 唯一能决定事实先后顺序 |
| `WallTime` | 现实经过的时间，供UI帧率、离线模式、Agent定时等 | 不能直接更改生态状态；只决定需要推进多少 `SimTime` |
| `RenderTime` | Unity 对最新已提交世界快照的插值显示时间 | 严禁回写生态事实 |

**建议**用 `int64` 整数定点时间戳，例如单位为 1 ms；这只是事件时间分辨率候选，**不是每毫秒遍历所有实体**。首版采用一个世界一个时间线。Game Master 的跨世界记忆另用现实时间和显式 `WorldId` 做索引。

`Speed=1x/12x/120x` 是把现实时间转换为目标模拟时间 `targetSimTime` 的比例；不能乘大个体代谢/繁殖速率，而应推进相应的模拟时间跨度。`Pause` 不推进；离线模式在启动时计算合法目标跨度并交给相同调度器，必要时分段限额。

## 3. 核心设计：离散事件 + 多速率连续状态积分

### 3.1 离散事件（FES / Future Event Set）

事件例子：`AntReachedWaypoint`, `FoodPickupAttempt`, `TrophallaxisRequest`, `BroodStageReady`, `DigProposal`, `ExcavationCommitted`, `FoodDepleted`, `QueenLaysEgg`, `CommandAccepted`, `MortalityCheck`, `MetricWindowBoundary`。

调度键建议：`(SimTime, Phase, SemanticPriority, StableTieKey, SequenceNo)`。同一时间的竞争动作原则上要基于同一观察快照收集 proposals，再统一仲裁；不能仅让低 ID 工蚁永远抢先。可用稳定随机打破平手，但对应流/计数器必须持久化。

对于同一时间内新发起的事件，禁止在提交中随意重入当前阶段；放入规定的后续阶段或下一次安全边界。必须检测零时间自激循环与队列爆炸。

### 3.2 连续过程（只在必要时间跨度积分）

| 过程 | 推进方式候选 | 事件驱动边界 |
|---|---|---|
| 基础代谢/能量 | 在生理速率不变时按 `Δt` 积分 | 行为、温度或摄食变化导致速率变更 |
| 水分状态 | 按局部温湿度和饮水变化积分 | 气候、位置或取水事件 |
| 幼虫发育 | 温湿度/营养积分发育进度 | 营养不足、进入新发育阶段 |
| 蚁后储备和产卵 | 物种和生理参数控制的离散/连续混合 | 产卵、补给、环境变化 |
| 信息素 | 局部沉积增量 + 随时间衰减 | 沉积、环境更新、采样 |
| 地表/地下微气候 | 分块低频积分，需稳定步长 | 降雨、出入口/巢穴结构修改 |
| 近景运动 | 适度固定上限的小时间步 | 接触、障碍、进入路径节点 |
| 远景出行 | 记住路线/路程与到达事件 | 风险、通道变化、需要接触时唤醒 |

例：局部踪迹信息素仅衰减时可使用 `C(t+Δt) = C(t) exp(-λΔt)` 按需更新，避免每毫秒更新全部地表。如果加入空间扩散，显式数值法的稳定步长必须依据网格间距与扩散系数选取，不允许为加速随意增大 `Δt`。

死亡风险不能粗暴地在一个大步长末尾才“掷一次硬币”，否则可能出现工蚁已经死亡却在前面数小时里仍交哺和挖掘。候选做法是按累计风险/阈值在时间线上安排死亡事件；生理阈值跨越要定位到合法事件时间。

### 3.3 时间推进算法草案

```text
AdvanceTo(target):
  assert target >= currentSimTime
  while currentSimTime < target:
    tNext = min(target, nextDiscreteEventTime, nextFieldBoundary,
                nextRequiredNearFieldSubstep)
    IntegrateContinuousProcesses(currentSimTime, tNext)
    currentSimTime = tNext
    GatherDueEventsAndPendingAuthorizedCommands(tNext)
    ResolveAtTimeBarrier(tNext)   // order and atomic commit rules below
    PublishCommittedEventsAndChangedVersions()
    ScheduleFutureEvents()
  PublishReadOnlySnapshotAtCommittedBoundary()
```

这是**架构伪代码**，不是可直接编译/证明准确的求解器。`IntegrateContinuousProcesses` 必须能够发现阈值交叉并在必要时缩小积分终点，不能越过已经发生但尚未入队的临界事件。

## 4. 同一模拟时刻的处理屏障（Barrier）

**建议单写入者（single writer）顺序提交；只读采样和 proposals 生成未来可并行。**

| 阶段 | 目的 | 示例 |
|---|---|---|
| 0 输入冻结 | 把授权命令收进下一个合法边界，校验 `expected_revision`、幂等 `CommandId` | GM 请求放苹果，不直接建 Unity 对象 |
| 1 环境/事实推进 | 应用该边界前已到期天气、资源变化和关键生命转换；刷新被查询区域 | 温度变化、羽化、死亡 |
| 2 局部感知 | 基于同一已提交状态读取各工蚁可感知信息 | 食物、同伴、局部信息素和几何 |
| 3 行为 proposals | 个体提出候选动作，不直接修改世界 | 取食5mg、交哺、挖土、行进 |
| 4 冲突仲裁与事务提交 | 对共享资源和空间做约束/仲裁，提交真实改变 | 资源不得负数，两次重叠挖掘不重复扣土 |
| 5 二次校验 | 检查通行/生命/账本/版本有效性，拒绝或回退失败事务 | 通道几何提交后，旧路径失效 |
| 6 发布事实与统计 | 写出已提交 `WorldEvent`、新 world/geometry revision、原子指标累加 | `FoodTransferred` / `ExcavationCommitted` |
| 7 派生/调度 | 生成下一次触发、脏区、研究事件候选等 | 后续路线选择、字段更新、GM 提醒 |

同一时刻的“死亡 vs 交哺”以约定的生命转换优先于行为 proposals 处理。取食失败的工蚁不能因此获得营养；提交失败的挖掘不能产生土粒。潜在环境变化应在接下来的感知之前生效。

**原子事务的作用域应按物料/资源/几何而非一个全世界大锁来设计**：初版串行提交，后续允许独立分块并行提案、确定性归约；跨块编辑必须要么全部提交，要么全部拒绝。

## 5. 具体冲突例子

### 5.1 两只工蚁同时搬取最后一份食物

- 食物源只剩 `4 mg` 可用质量，两只工蚁在同一边界都提出 `3 mg` 取食申请。
- 仲裁器按确定性、不会总是偏袒低 ID 的规则分配，实际取走总质量不超过 `4 mg`。
- 食物源剩余量为 0；两只工蚁的摄取/携带状态之和增加不超过 4mg（考虑分拣损失等需记账）。
- 失败或部分成功动作产生相应响应，下一次决策读取最新资源状态。

### 5.2 两只工蚁挖同一块土

- 两只都提出合法 `DigProposal`，重叠的可挖区域只算实际被移除的材料集合。
- Core 在一组一致的几何事务中计算有效交集、材料账和各个工蚁可承担的工作量。
- 事务成功后递增 `GeometryRevision`，发 `ExcavationCommitted` 并标记受影响通道，旧导航保守无效。
- 土粒搬运消耗时间、能量；不能一次挖掘提议就默认土粒已经到达地表。

### 5.3 两只工蚁交哺

- `TrophallaxisRequest` 必须满足距离、物种/生命阶段、合法生命状态、供者/受者容量。
- 以实际转移量减少供者嗉囊库存，增加受者；不把相同库存再同时计入“蚁群资源池”。
- 交哺后触发营养变化与必要的下一轮行为再评估。

## 6. LOD/距离与重要性不是“恢复时重新生成”

采用 L0-L3，分别管理行为、环境场、渲染、历史记录频率，绝不用一个数字绑定全部精度。

- L0：镜头近处、重要接触/挖掘、长期重点个体；需高精度局部互动。
- L1：附近标准行为，较低频感知和路径推进。
- L2：远处已具体模拟工蚁；ID、年龄、能量、路线、重要事件、下一唤醒时间持续存在；可事件方式推进。
- L3：当前地图之外的背景物种/种群统计；不能虚构完整逐只历史档案。

**接触前提升精度**：两个不同精度的实体接近到需要交互的范围时，必须先汇合到兼容的空间/行为分辨率，再处理交哺、攻击或碰撞。若 L2 无法精确定位中间发生的接触，则标记精度限制，不生成假的逐次接触历史。

**关注与活动分离**：玩家对远处工蚁的“深度追踪”可以提高其轨迹/事件记录精度，但不能赋予它更多能力。世界模拟结果不应因打开人物档案或关闭 GM 而改变；如果 LOD 策略必然产生细节近似，则需量化偏差并告知历史精度。

## 7. Unity、GM 与时间：完全异步于逻辑模拟

- **Unity** 消费已提交的只读 `WorldSnapshot` 和 `GeometryDirtyBatch`；以局部插值显示；镜头、剖面、透明度不得修改 `WorldState`。
- **GM/World API** 将玩家环境指令变为带授权的 `WorldCommand`；排入 `CommandInbox`，在**下一个安全提交边界**正式执行，返回 `accepted / committed / rejected` 和 `CommandId`/事件 ID。
- **统计与观察** 订阅已提交事件/指标；观察器产生解释候选，Agent API 延迟或故障不应停住模拟主循环。
- **暂停**：可以观察、查看历史、移动镜头、继续对话，但影响世界的命令应排队到恢复后合法时刻，或明确定义为暂停状态下的原子操作，绝不绕过提交屏障。
- **历史回放**：只读历史视图独立于当前世界推进；若没有真实轨迹/场景记录，标注为事件摘要/示意重现。

## 8. 快照、日志、崩溃恢复与复现

不可把仅供玩家看见的高层 `WorldEvent` 列表，误当成能完整重放所有个体内部状态的 event sourcing 系统。

**WorldCheckpoint 至少包含：**

| 数据类别 | 必须保留 |
|---|---|
| 时间 | `SimTime`、时间基准版本、系统下一更新时刻 |
| 身份 | 世界 ID、实体 ID 分配器与已死亡身份索引 |
| 个体 | 生理、行为、任务、记忆、路径、携带资源、LOD/下一唤醒时刻 |
| 环境 | 食物质量、信息素状态/惰性衰减时间戳、气候、水热状态 |
| 空间 | 参数化几何检查点+待应用编辑、geometry revision、物料账、导航有效性 |
| 调度 | FES 未来事件及稳定 sequence，活动连续速率/阈值积分进度 |
| 随机数 | world seed、每系统/每实体 RNG 流状态或计数器 |
| 命令 | 幂等命令日志/已提交 CommandId、执行回执与授权来源 |
| 存储 | checkpoint ID、事件持久化 cursor、schema/physics version |

**原子可恢复原则**：checkpoint 文件与数据库提交进度要么一起作为完整一致的恢复点被承认，要么整体无效；异步写盘时需要写前日志/事务清单和安全文件替换策略。内存世界可继续前进，但对外不能把尚未持久化的进度误报为已耐久保存。定期快照 + 增量事务日志/状态增量可以作为后续优化；首版先验证“一次同步一致快照→重新加载→继续运行”正确性。

**重现目标分层：**

1. 相同二进制、配置、初始种子、单线程顺序、操作日志 → 尽量做到同样的关键事件与数值结果。
2. 使用不同时间步长/LOD/并行后端 → 保证守恒、合法性和统计分布在明确误差内，而非强求每次随机轨迹完全一致。
3. Game Master 使用随机 LLM 输出时，只有其已**授权并实际提交**的环境命令才改变世界；固定运行时复现须记录这些外部命令及生效时间。

## 9. C++ 模块、数据接口与服务边界

```text
SimulationCore/
  clock/       SimTime, ClockMode, TargetTimePolicy
  scheduler/   FutureEventQueue, MultiRateScheduler, SystemWakeups
  barriers/    PhaseController, ActionProposal, TransactionResolver
  state/       WorldState, AntSoA, ColonyStore, ResourceStore
  physiology/  EnergyIntegrator, HydrationIntegrator, DevelopmentIntegrator
  behavior/    PerceptionSampler, TaskDecision, ActionIntents
  chemistry/   SurfacePheromone, DecayFields
  ecology/     Weather, Food, Plants, PredatorCoarseModel
  spatial/     ConstructiveGeometry, DynamicNav, PositionIndex
  history/     EventEmitter, MetricsAggregator, SnapshotCodec
  commands/    CommandInbox, AuthorizationToken, IdempotencyLedger
  rng/         StreamFactory, StableCounterRng
  api/         VersionedWorldCAbi, ImmutableSnapshot
```

建议接口草案（类型由后续 Contracts 定义；示意非可编译实现）：

```cpp
struct SimTime { std::int64_t ticks; };
struct ActionProposal { EntityId actor; ActionType action; TargetId target; };
struct WorldCommand { CommandId id; WorldId world; /* typed payload */ };

class ISimulationRuntime {
public:
    virtual AdvanceResult advanceTo(SimTime target) = 0;
    virtual CommandReceipt enqueueCommand(const WorldCommand&) = 0;
    virtual SnapshotHandle acquireSnapshot() const = 0;
    virtual ~ISimulationRuntime() = default;
};
```

- 只有调度器可以触发状态写入；查询返回不可变快照或只读视图。
- 不在 C ABI 中暴露 C++ 容器、引用或异常；Unity/Python 工具通过 World Application 间接访问。
- 复杂异步操作（如网格重建）标记源版本，迟到结果不得覆盖当前权威状态。

## 10. 需要定量研究后才能锁定的数值

- 模拟时间单位：1ms 是候选，不是承诺。
- 近场运动、感知、拥挤、交互的最优推进步长。
- 信息素/温度/水分稳定数值步长、误差界与空间边界条件。
- L2 远场运动与偶发风险的正确抽样机制。
- 积分跨越死亡、能量见底、羽化等阈值时的事件时间定位误差。
- 批量 proposals、分块调度、历史写入及 checkpoint 的性能预算。

**技术参考：** OMNeT++ 官方手册关于 Future Event Set、simTime 与同时间事件优先级：https://doc.omnetpp.org/omnetpp/manual/index.html ；Unity Native Plug-in / PInvoke：https://docs.unity.com/en-us/engine/6000.6/manual/programming-environment/plug-ins/native/overview 。本项目混合连续/离散调度结构为工程设计提议，不是直接复用两者现成的游戏实现。
