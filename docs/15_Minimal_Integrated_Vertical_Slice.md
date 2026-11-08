# AntWorld｜第一条可执行生态闭环规格（P0 Vertical Slice）v0.1

**v0.7（2026-11-08） · 这是一份后续 Codex 任务依据，不是已开发软件。**

## 1. P0 解决的问题

检验一个世界能否**不依赖 Unity / LLM**自主演化，围绕少量独立工蚁真实完成“觅食 → 营养进入巢穴 → 交哺/照顾幼体 → 生理变化/发育 → 空间变化 → 事实事件与统计”。必须具备一条可验证的小型三维挖掘事务，证明生物行为与几何权威相通。

**P0 不是**24m×24m 完整生态地图，不是美术 demo，不是复杂全物种生态，也不是完整的 Hermes/OpenClaw Agent。

## 2. 初始条件（可配置场景建议，而非真实生物定量标定）

- 一窝黑园蚁；1 只蚁后、约 32 只工蚁、若干卵/幼虫（例如 12 只幼体作为压力测试输入）。
- 一个初始三维建群巢室与地表入口，外部 2 处食物资源，代表碳水/蛋白、水源的基本供应。
- 局部土壤界面至少一个可挖掘前缘；不需整个 24m 地图、植被模型或全地表微气候。
- 保存所有 AntId，至少一只重点追踪工蚁记录精细事件。
- 运行真实三维导航，非真实微距动画。

## 3. 单个循环的必经事实链

```text
WorldClock
 -> AntExplorer locally encounters FoodSource
 -> FoodPickupProposal -> Commit (source mass decreases)
 -> Ant returns through real navigable path
 -> TrophallaxisProposal -> Commit (donor crop decreases, receiver increases)
 -> Individual metabolism / brood nutrition integrator advances
 -> Brood growth or status change according to model
 -> Local nest space pressure may trigger DigProposal
 -> Excavation transaction changes actual material + soil batch
 -> Nav/Geometry revision updates; soil is transported later
 -> Structured events + metrics aggregate
 -> Headless query and World API can explain what actually occurred
```

必须允许自然波动；测试用固定场景、随机种子或事件注入来覆盖每种操作，并**不能**要求每一次完全随机模拟都在固定时间内遇到恰好相同的生物学情节。

## 4. P0 最小 C++ 接口（仅功能契约）

- `CreateWorld(ScenarioConfig, Seed)` → world handle。
- `AdvanceTo(SimTime)` → 只推进到合法时间边界。
- `EnqueueCommand(WorldCommand)` → receipt/待执行状态；幂等。
- `QueryAnt(AntId, WorldId)` / `QueryColony(ColonyId, WorldId)`。
- `QueryMetrics(WorldId, Range, MetricIds)`。
- `DrainCommittedEvents(cursor, limit)` / `AcquireSnapshot()`。
- `SaveCheckpoint()` / `LoadCheckpoint()`。

首版可通过 Headless CLI 输出 JSON/CSV；与 Unity 适配需遵守 v0.6 `11_Cpp_Unity_Geometry_Interface.md` 的 C ABI 原则，但 P0 不应依赖 Unity 打包才能运行。

## 5. Codex 交付顺序（未来阶段）

| 批次 | 依赖 | 核心工作 | 退出条件 |
|---|---|---|---|
| S0 | 无 | WorldClock、ID、固定种子 RNG、事件队列、Headless CLI | `SCH-01/02/12/19` 测试 |
| S1 | S0 | 个体 SoA、食物实体、基础移动与事件 proposals | 食物不为负、ID 连续 |
| S2 | S1 | 局部感知、任务、觅食/回巢、简单路径记忆/信息素 | 觅食实验 F1–F3 可反复运行 |
| S3 | S2 | 能量/水分、交哺、生命阶段与营养分配 | E1–E4 与守恒测试 |
| S4 | S2/S3 | 初始三维巢室、挖掘提交、材料批次、连通 | GEOM-01/02/06/07/09 |
| S5 | S0–S4 | Snapshot、指标聚合、命令 API、checkpoint | SCH-10/17/19/20/25/27 |
| S6 | S5 | 最小 C# Unity 只读状态查看或数据查询连接 | 不改写 Core 状态 |
| S7 | S5 | 简单 GM read-only 主动观察 demo（Harness 另议） | 证据可追溯、API 失败不影响模拟 |

**重要：** S7 可与 S6 并行研发，但这不表示 GM 实现选型已确认。只有产品开发明确启动后，才交给 Codex 执行代码任务；当前不开始写软件。

## 6. 最初的可视化不是最终美术

- 优先支持两张结构化曲线：工蚁人口、巢穴营养收支；和一张二维位置路径/信息素图（供调试）。
- 一张“事件链表”：食物源减少 → 工蚁取食 → 交哺 → 幼体营养变化 → 生物状态改变。
- 后续 Unity 只读渲染真实三维巢穴、可切换剖视和个体跟随；不以 60 FPS 作为 P0 的生物模型测试指标。

## 7. P0 验收故事与失败定义

**成功演示：** 在可复现 seed 或受控测试条件下，工蚁无需中央 AI 即可完成至少一次实际探索/取食和返巢；交哺双方资源账一致；幼体营养/发育按模型变更；一只工蚁能在可达前缘进行真实挖掘；C++ 输出带因果与 ID 关联的事件和统计；保存与恢复不会改变已提交历史。

**强制失败条件：** 蚂蚁穿墙/瞬移、同一资源重复获取、假交哺、土量复制、重复死亡/羽化、打开 UI/GM 影响随机轨迹、checkpoint 后事件丢失、世界接口绕过规则直接修改状态。

**P0 未承诺：** 生物参数已完全标定、长年稳定生态、复杂昆虫生态、逼真动作、完整大模型人格成长、上万只蚂蚁性能。

## 8. 下一轮最有价值的未决项

1. 世界事件 `SimTime` 单位与 Tick/Phase 的具体 ABI 数据类型。
2. `ActionProposal` 的最小合法类型、资源仲裁公平性、同刻优先级。
3. C++ `SoA` 布局和 entity lifecycle 的完整状态转换表。
4. P0 持久化格式：稳定 schema、checkpoint/日志原子恢复策略。
5. 首批科学参数来源；哪些行为先使用工程近似，哪些需要黑园蚁文献标定。
