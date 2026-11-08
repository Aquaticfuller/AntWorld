# AntWorld 设计基线与 Codex 交接包 v0.8

**归档日期：2026-11-08** | **状态：开发前规格准备完成，尚未运行游戏代码。**

用户多轮确认了生态模拟、空间、AI Game Master 与技术栈；本版本继承 v0.7 全部专题并补充可执行契约、S0 任务书、测试与交接文件。将**产品需求**、**工程默认值**、**需科学标定的模型假设**严格区分。

## 快速上手

1. 在档案根目录阅读 `../CODEX_START_HERE.md` 与 `../AGENTS.md`。
2. 用户已确认的游戏需求：`01_Decision_Register.md`。
3. 工程默认决策：`16_Implementation_Freeze_and_ADRs.md`。
4. C++ 数据结构：`17_Core_Data_Contracts.md`。
5. 时钟/事务：`18_Scheduler_Transactions_and_Determinism.md`。
6. 存档/统计：`19_Persistence_Analytics_and_Recovery.md`。
7. ABI 与 Game Master：`20_World_API_C_ABI_and_GameMaster_Tools.md`。
8. P0 生物边界与场景：`21_P0_Behavior_Scenarios_and_Biological_Assumptions.md`。
9. 分批开发：`22_Development_Roadmap_and_Execution_Gates.md`。
10. 第一次 Codex 任务：`23_S0_Exact_Tasks_and_Test_Cases.md` + `../codex_tasks/S0_KICKOFF_PROMPT.md`。
11. 追溯与质量门禁：`24_Traceability_and_Quality_Gates.md`。

## v0.7 完整保留的历史专题

- `02_Game_Design.md`：总体游戏设计、观察、生态世界、长期陪伴。
- `03_Technical_Architecture.md`：C++ Core / Unity C# / GM 边界。
- `04_Biology_and_Social_Simulation.md`：觅食、信息素、营养、生命周期、巢内社会。
- `05_Game_Master.md`：持续身份、记忆、主动观察、玩家等价操作权限。
- `06_Roadmap_and_Acceptance.md`：较高层路线与验收目标。
- `07_References.md`：研究和官方技术资料（核验时以原始来源为准）。
- `08_Open_Questions.md`：长期未定问题和科学参数。
- `09_3D_Nest_and_Subsurface_Model.md`：真实三维地下和水热。
- `10_Parametric_Geometry_Implementation.md`：权威参数化几何编辑与局部 SDF。
- `11_Cpp_Unity_Geometry_Interface.md`：动态网格/污区与 C ABI 草案。
- `12_Geometry_Prototype_Test_Plan.md`：几何测试。
- `13_Simulation_Runtime_and_Scheduler.md`：混合事件/连续时间调度。
- `14_Simulation_Contracts_and_Test_Matrix.md`：SCH-01–SCH-30。
- `15_Minimal_Integrated_Vertical_Slice.md`：第一条完整生态闭环。

## 什么已经确定？

用户已确认：Unity + C# 客户端、C++ 独立 Simulation Core；24×24m 的首版可扩展世界；黑园蚁首个重点物种；蚂蚁个体采用局部简单模型，LLM 做 Game Master；三维地下参数化挖掘编辑+局部 SDF 缓存；多蚁群、详细统计、长期生命档案；跨世界唯一人格 GM 等。完整见 `01_Decision_Register.md`。

**尚未确定**：Game Master 使用 Python/Hermes 或 C#/Agent Framework；成熟的蚂蚁生理参数、局部 SDF 砖尺寸、真实 LOD 更新频率、全生态性能指标。工程演示场景参数均不得视为黑园蚁实测数据。

## 对 Codex 的最小授权

**一次只实施 S0**：C++20 + CMake/CTest 的无画面模拟基础，包括时间、RNG、ID、事件调度、内存 checkpoint 与测试；**不**开发 Unity 画面、完整蚂蚁行为、地下 SDF 和 Agent 服务。待通过质量门禁后依次实施 S1–S9。

## 附带可机读文件

- `../contracts/antworld_c_api_v1.h`：待实现 C ABI v1 头文件草案，**没有函数实现**。
- `../schemas/p0_scenario.schema.json`：P0 场景 JSON Schema。
- `../scenarios/p0_smoke.json` 与 `../scenarios/p0_biology_fixture.json`：可复现机制测试输入，**非生物标定数据**。
- `../codex_tasks/`：S0 和后续批次的任务指令；首批只执行 S0。
- `../MANIFEST_SHA256.md`：交接包文件 SHA-256 校验清单。

## 版本规则

保留 v0.4–v0.7 作为历史归档；v0.8 为新的交接基线。任何用户产品需求变更先改 `01_Decision_Register.md`；技术默认值变更更新 `16_Implementation_Freeze_and_ADRs.md`、契约与相关测试。Codex 不得自行改变用户已确认的方向。
