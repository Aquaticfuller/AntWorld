# AntWorld｜设计变更日志

## 2026-11-08 — v0.7 C++ Simulation Core 综合闭环、混合时钟与验收

- 继承 v0.6 全部已确定设计，地下几何方案 A 和 Unity/C++ 单一事实边界不变。
- 新增 `13_Simulation_Runtime_and_Scheduler.md`：统一整数模拟时钟、事件队列/多频积分、阶段屏障、原子事务、LOD、异步 GM 命令、随机与 checkpoint 恢复。
- 新增 `14_Simulation_Contracts_and_Test_Matrix.md`：SCH-01–30，覆盖食物/交哺/挖掘原子性、时间/LOD、状态恢复、命令幂等、跨世界、统计一致性。
- 新增 `15_Minimal_Integrated_Vertical_Slice.md`：一窝蚂蚁的自主觅食→营养→幼体→建巢→事件/统计 P0，无画面先行，给未来 Codex 用。
- 同步修订 README、决策登记册、架构、生物模型、GM、路线图、开放问题和参考资料。
- **状态仍为设计建议**，没有启动 C++/Unity 游戏代码实现，也未验证具体时间步长/性能。


## 2026-11-08 — v0.6 参数化几何方案 A 已确认；细化 C++/Unity 接口

- 用户确认几何路线 **A**：「有序参数化挖掘/回填编辑 + 局部 SDF 缓存」；取代 v0.5 的 A/B 待对照。
- 新增 `10_Parametric_Geometry_Implementation.md`：材料/空腔权威、CSG 顺序编辑、重叠移土防重复、几何版本、连通/净空、房间 ID lineage、压实检查点。
- 新增 `11_Cpp_Unity_Geometry_Interface.md`：类型化查询/命令、C ABI 版本、snapshot handle、dirty batch/mesh packet、Unity 主线程消费与 Game Master 权限边界。
- 新增 `12_Geometry_Prototype_Test_Plan.md`：G0–G5、GEOM-01–15 验收矩阵，明确不启动完整游戏开发。
- 同步修订第 01/03/06/07/08/09 号文档；保留 v0.4/v0.5 历史 ZIP。


## 2026-11-08 — v0.5 自主三维建巢与地下环境专题

- **保留 v0.4 全部内容**，新增 `09_3D_Nest_and_Subsurface_Model.md` 专题，不启动正式代码开发。
- 对真实 3D 建巢明确三个不同过程：地下移土挖掘、土粒运输/弃置、局部材料筑造与回填。
- 把地下材料占用与持久编辑确立为**建议的唯一几何权威**，导航、碰撞和 Unity Mesh 同源派生；参数化编辑+SDF缓存 vs 稀疏占用体积的具体取舍仍待原型对照。
- 引入干土/水质量分账、原子几何编辑、挖掘前缘、动态 portal/巢室判定、温湿度双尺度、风险控制与 X1–X10 验证。
- 新增黑园蚁温度-挖掘/3D巢形直接实验、黑园蚁筑造研究，以及火蚁、切叶蚁跨物种参照并标注限制。
- 同步更新决策登记册、技术架构、生物模型、开放问题、路线图和来源。所有新增数值仍属待验证的工程候选。


## 2026-11-08 — v0.4 结构化归档

- 将此前已确认的全部方向统一归档为 Markdown 可版本管理文档。
- 锁定 C++ Simulation Core + Unity C# 客户端；Game Master Runtime 候选尚未定。
- 锁定首版 24m×24m 温带草地/林缘生态世界，附近多蚁巢、可分块扩展。
- 澄清早期“让 LLM 有限控制工蚁”的方案已被“简单可信生物模型驱动行为、LLM 作为世界级 GM”替代。
- 新增《巢内社会行为与空间组织 v0.1》：空间忠诚与分工、育幼转移、清洁与废物、挖掘/搬运、休息/不活动、分层事件与测试。
- 新增已验证生物学参考资料及物种适用边界。
- 该版本仍属于设计阶段；未实现代码或生物学参数标定。

## v0.8 — Codex 开发前规格与交接（2026-11-08）

- 保留 v0.7 所有正式设计、SCH-01–30 与三维几何验收要求。
- 新增 `16`–`24`：工程默认决议、核心 C++ 数据契约、调度/事务、存档分析、C ABI 与 GM 工具、生物测试场景、S0–S9 分批路线、S0 逐条验收与追溯矩阵。
- 新增仓库级 `AGENTS.md`, `CODEX_START_HERE.md`, `codex_tasks/` 指令，明确**首次只做 S0**。
- 新增 `contracts/antworld_c_api_v1.h`（无函数实现），JSON schema 和工程场景 fixtures。
- 明确 C++ Simulation Core / Unity C# 决定已定，而 GM Harness 仍待测试；不能把 fixture 说成生物实测。
- 这是**规格归档**，尚未执行 Codex 代码开发；所有 PASS/FAIL 只在真正运行测试后填写。
