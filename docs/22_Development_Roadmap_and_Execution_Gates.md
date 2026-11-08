# AntWorld｜Codex 分批开发路线与退出门禁 v0.8

**实施原则**：一次只授权一个阶段。每阶段必须提交源代码、可运行的自动测试、运行命令、文档变更及结果摘要；未通过门禁前不开始下一阶段。长期产品需求不等于 P0 同期实现需求。

## S0 — C++ 核心工程基础（**首次 Codex 任务**）

- CMake / C++20 / CTest；独立 `antworld_core` 库和 `antworld_headless` CLI。
- WorldId/EntityId 强类型；WorldClock/WorldRevision；固定算法 PRNG 和可复现测试向量；按时间/phase/seq 排序的 FutureEventQueue。
- 空世界创建、AdvanceTo、只读 Snapshot、简单已提交 WorldEvent、最小 JSON/CSV 诊断输出（可先只导出 JSON）。
- 内存 checkpoint round-trip：时间、ID 分配器、RNG、未来事件、revision 全部恢复。
- 强制测试：SCH-01、02、12、19、20（S0 能实现的部分）、22；同 seed 同 trace hash。
- **不做**蚂蚁行为、Unity、SDF、SQLite 或 Agent；`contracts/antworld_c_api_v1.h` 留作后期 ABI 规范，不要求 S0 导出 DLL。

## S1 — 实体与行为提议事务

- AntStore/ColonyStore/ResourceStore 最小 SoA、生命周期 ID、对象查询、Move/CollectFood ActionProposal。
- 同刻资源仲裁、明确提交/拒绝事件、守恒账本及公平 tie break。
- 门禁：SCH-03/06/07/08，读取不影响结果；初步资源 ledger。

## S2 — 局部感知、探索与信息素

- 局部可达地图、简单导航；探索、发现、采集、返巢；稀疏表面信息素和简单记忆。
- 多 seed、关闭/开启功能的对照输出；不能提供上帝视角食物坐标。
- 门禁：F1/F2/F3；关键事件可追溯，禁用功能后统计合理改变而不保证最优路线。

## S3 — 生理、营养、交哺与幼体

- 代谢/水分积分、Crop 与 BodyEnergy 分开、真实交哺事务、幼体阶段进度与事件。
- 门禁：SCH-05/07/23、N1/N2、营养账/水账、不同时间步长误差在明确范围内。

## S4 — 三维挖掘及动态连通

- 最小 InitialSolid、局部 `ExcavatePatch`、材料账、土粒运输状态、参数化编辑历史、局部 SDF 缓存（可逐步实现）。
- 真实的 3D 净空与 Portal 判定；几何更新后相关路径失效；可回填封堵。
- 门禁：SCH-04/09/16/26、G1/G2、此前 `12_Geometry_Prototype_Test_Plan.md`。先保证数值/拓扑正确，不要求半写实渲染。

## S5 — 持久存档、分析与统计

- Core 结构化事件、指标定义、Checkpoint serializer；Application/Persistence SQLite 原子写入与恢复；命令 ledger。
- 事件和统计可根据实际实体一致交叉检验，不会将历史事件冒充完整 event sourcing。
- 门禁：SCH-10/17/19/20/21/25/27，读取/写入耗时报告，恢复后关键状态一致。

## S6 — 小型生态闭环验收

- 引入 `p0_biology_fixture`，至少一次自主探索→取食→返回→交哺→幼体营养/发育变化→可达界面挖掘→事实/统计，运行多个 seed。
- P0 机制可信 + 可追溯，不要求所有 seed 在相同日程产生全部故事；在测试 fixture 下明确覆盖每种动作。
- 门禁：所有适用 P0 机制与 SCH-01–23、25–27、29/30 中**已实现功能相关项**通过；尚未开发 LOD 的 SCH-14/15 明确标成 later gate，不虚报完成。

## S7 — C ABI / Unity 只读验证

- 版本化 snapshot/dirtied geometry 批量接口、C# P/Invoke 绑定和 3D 几何可视演示；只读状态、近景观察、局部网格版本检查。
- 门禁：跨语言 struct 偏移与所有权测试、旧包不得覆盖新版本、镜头切换不改变世界。

## S8 — Game Master 工具最小链路

- 先完成 typed World API、统计查询、授权的 `PlaceFood` 和追踪任务；可用简易 fake Agent 验证协议。
- Agent Harness（Python/Hermes 或 C#/Agent Framework）经独立对照后决策；无须在 S0–S6 锁定。
- 门禁：查询证据真实、CommandId 幂等、LLM API 失败世界不停、未授权世界修改拒绝；之后逐步加入长记忆、主动观察与语音。

## S9 — LOD/时间/压力与 24×24m 扩展

- 从 P0 局部场景逐步扩展到多蚁群、24×24 米真实物理地图、2m 分块默认假设测试、近远行为分级与性能测试。
- 门禁：SCH-13–15、24、28–30；比较多个随机种子、同模拟时长的统计差异和空间/身份连续性。

## 绝不可跨越的边界

1. 不以“先搞定画面”代替生物机制正确性。
2. 不把 24×24 米全生态世界、上万工蚁、AI 语音等未来目标混入 S0。
3. 不更改用户已决定的 C++ Core + Unity C#、真三维地下、参数化编辑权威、长期 GM 人格。
4. 参数缺文献时使用明确的 `ENGINEERING_FIXTURE` 标签，不得宣称真实标定。
5. 遇到设计缺口先提出 ADR，在允许的阶段采用最小合理默认，并记录与测试。

## 每个批次 Codex 必须返回

- 文件与接口变更说明、构建与测试命令、测试结果原始摘要、已知问题、下一阶段依赖。
- 对每个声称已实现的功能给出自动化验收测试 ID 和结果；没有运行测试就标 `NOT RUN`，禁止伪报 `PASS`。
- 涉及算法或模型变更时说明设计文件章节以及 `physicsVersion`/schema 影响。
- 代码应可以从干净 checkout 构建，不依赖用户机器上的隐秘绝对路径。
