# AntWorld｜S0 首批开发的精确任务与测试 v0.8

**此页唯一授权范围：C++ 工程基础，无画面运行，确定性时间与事件存档。** 不开始写任何工蚁行为、信息素、SDF、Game Master 或 Unity 项目代码。

## 1. 预期可运行仓库结构（Codex 可以在此基础上细化）

```text
AntWorld/
  AGENTS.md
  CODEX_START_HERE.md
  docs/                  # 本档案全部设计文件
  contracts/antworld_c_api_v1.h  # 边界草案，不在 S0 实现
  schemas/
  scenarios/
  cpp/
    CMakeLists.txt
    include/antworld/core/{world_id,sim_time,event,rng,world_runtime}.hpp
    src/{world_clock,event_queue,rng,world_runtime}.cpp
    apps/antworld_headless.cpp
    tests/{test_clock,test_events,test_rng,test_checkpoint}.cpp
  unity/                 # 后续创建，S0 不要求
  gamemaster/            # 后续创建，S0 不要求
```

## 2. 必须完成的接口行为

**World creation**：`WorldId + Seed` 创建空世界，`now=0`, `revision=0`，建立不与 Unity 关联的 `WorldRuntime`。

**Event scheduling**：禁止过去时间、禁止非法 phase；同一时间的事件稳定排序，支持取消/失效、可诊断的同刻递归保护。

**AdvanceTo**：推进到目标时间，返回精确 now；对重复相同目标调用 no-op；读取不消耗随机状态。允许执行 mock/test scheduled events，但不能伪称已有蚂蚁行为。

**RNG**：选择明确、单一的可移植 PRNG 实现，固化版本与至少 5 个固定 seed 的测试向量；不能依赖 `std::uniform_*` 获得跨平台逐位一致。要能从状态恢复下一次生成序列。

**Snapshot**：能够读取 worldId、now、revision、事件数量；只读快照拥有明确的生命周期，取快照不改变真实世界。

**Checkpoint**：将所有 S0 必需数据序列化为明确版本格式，并恢复 future event queue、RNG、ID allocator、event seq、当前时间。内存 round-trip 必须可测；S0 无需 SQLite 持久化。

**Headless CLI**：示例命令建议 `antworld_headless --scenario scenarios/p0_smoke.json --advance-ms 60000 --output out/smoke.json`，打印 worldId、simTime、revision、event counts、RNG 版本和输出文件路径。场景未知字段应按 schema 规则报错或进行明确诊断，不静默忽略。

## 3. S0 不可跳过的测试

| Test ID | 测试输入 | 期望 |
|---|---|---|
| T00 | 创建 `p0_smoke.json` | worldId/seed 正确，now=0 |
| T01 | `AdvanceTo(100)`→`AdvanceTo(100)` | 第二次不变、无额外 RNG 消耗 |
| T02 | `AdvanceTo(100)`→`AdvanceTo(99)` | 拒绝倒退，revision 不变 |
| T03 | 同一时间、不同 phase、相同 seq 的有序事件 | 执行顺序稳定、符合 Phase 顺序 |
| T04 | 十个同刻事件同 priority | 重复运行输出完全相同顺序 |
| T05 | 事件在自身同刻无限递归调度 | 报有限、可读的错误，不无限运行 |
| T06 | 读 snapshot、重复读 snapshot | 不推进时间、不改变随机流、状态哈希相同 |
| T07 | RNG seed A/B + 回放 | 相同 seed 序列一致，不同 seed 一般不同；保存恢复后后续值一致 |
| T08 | 检查点前有未来事件 | 恢复后事件仍在正确时间执行 |
| T09 | checkpoint 往返 | worldId/time/revision/queue/nextId/RNG 全部一致 |
| T10 | 不兼容 schema version / 截断存档 | 拒绝加载，无部分状态修改 |
| T11 | 空场景 headless | 不依赖 Unity 或 LLM，能输出可解析 JSON |
| T12 | 修改世界仅能走合法提交入口 | 普通 query 没有可写 world 指针 |
| T13 | 同种输入重复两次 CLI | `trace_hash` 和 state summary 一致；输出不包含不可复现绝对路径 |

这些测试中 SCH-01、02、12、19、20、22 的适用部分可以映射到 S0；其它 SCH 项随着功能实现逐批纳入。

## 4. S0 完成定义

- 从干净仓库的 `cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Debug`、`cmake --build build`、`ctest --test-dir build --output-on-failure` 可以运行。
- 提供 Windows x64 可复现的生成器/preset 或 Visual Studio CMake 说明；如果在 Linux 环境实现，写明 Windows 尚未实测。
- `docs/` 和 `AGENTS.md` 保持可追溯；README 简述如何运行 headless 和 test。
- 提交 `S0_RESULTS.md`，按测试 ID 列出 PASS/FAIL/NOT RUN、示例 CLI 输出和已知限制。
- 不增加云模型依赖或 Unity 运行依赖；不私自下载/启动通用 Agent 服务。

## 5. S0 门禁之后的下一阶段

S0 必须由用户审查并确认，再按 `22_Development_Roadmap_and_Execution_Gates.md` 开始 S1。即使整体开发已获授权，Codex 也不能在同一次任务里静默跳过多个门禁。
