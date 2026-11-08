# AntWorld｜C++↔Unity C ABI 与 Game Master 工具接口 v0.8

**原则**：所有玩家与 Game Master 的**能力集合**一致；自主操作的**权限**因触发方式而不同；模拟核心只有一个事实写入者。v0.7 的 `11_Cpp_Unity_Geometry_Interface.md` 仍定义地下 dirty/mesh 细节。此文是统一 World API 的 P0 接口补充。

## 1. 边界

```text
Unity C# UI  ── Query / Command / ViewControl ──┐
                                                ├── World Application + Auth
Game Master  ── Query / Command / Observation ──┘             |
                                                                ▼
                                                         C++ Simulation Core
                                                                |
                                       Immutable snapshots / Committed events
```

- P0 允许 Unity 尚未启动，仅由 Headless CLI 使用 C++ 内部 typed runtime。
- Unity 通过 C ABI + P/Invoke 获取按需批量只读快照；不应逐个工蚁逐帧做跨语言调用。
- GM 通过上层受限工具查询/执行，不需要直接持有 C++ 原生指针或访问进程内存。
- 所有物理世界变更在 Core 提交后返回 `committed`；收到命令 `accepted` 不能报告“苹果已放置”。

## 2. 提供了一个不带实现的 C ABI v1 合约头文件

见 `contracts/antworld_c_api_v1.h`，该头文件专用于**跨语言数据布局草案**，包含：

- 导出宏和 `extern "C"`、明确的整型返回码。
- `AW_WorldId`、`AW_WorldCreateDesc`、opaque `AW_WorldHandle`、`AW_SnapshotHandle`。
- `aw_world_create/destroy/advance_to`。
- `aw_snapshot_acquire/copy_ants/release`，通过“先查询所需长度，再复制到调用方缓冲区”批量同步。
- 每个结构体带 `struct_size`, `api_version`，新字段只能按版本迁移或尾部扩展。

**不是已经编译通过、可用的 Unity 插件**。Codex S0 必须从 C++ 运行时起步，C ABI 可在后续任务落地前按测试结果完善。

**内存规则**：不穿越 ABI 传 `std::vector`, `std::string`, `bool`, C++ 异常或所有权不明指针；如果世界创建返回 handle，销毁由对应库函数完成；复制函数写调用方申请的 buffer，不在快照 release 之后使用原始指针。

## 3. P0 API 操作组

| 分类 | 操作 | 修改真实世界？ | 自主 Agent 默认 |
|---|---|---|---|
| `WorldQuery` | `GetWorldState`, `FindEntity`, `GetAnt`, `GetColony` | 否 | 可执行 |
| `AnalyticsQuery` | `QueryMetrics`, `CompareColonies`, `GetHistory`, `GetSoilLedger` | 否 | 可执行 |
| `ViewCommand` | `FocusCamera`, `FollowAnt`, `SetSectionPlane`, `ShowHeatmap` | 否 | 可建议或在不打断玩家时执行 |
| `ObservationCommand` | `WatchAnt`, `CreateObservationTask`, `GenerateReport` | 不修改生态世界 | 可执行，受频率预算约束 |
| `WorldMutation` | `PlaceFood`, `ScheduleWeather`, `AddWater`, `ModifyTerrainAllowed` | 是 | 玩家明确指令或预授权额度内 |
| `LifecycleControl` | `SetTimeScale`, `PauseWorld`, `SaveWorld`, `SwitchWorld` | 影响运行/存档；不是蚂蚁日常行为 | 玩家授权、避免突袭操作 |
| `Destructive` | `DeleteWorld`, `OverwriteSave`, `MassDisaster` | 高风险 | 必须确认 |

**不提供**自由 `SetAntThought`, `ForceBuildRoom`, `SetPopulation`, `TeleportAnt` 作为玩家普通生态指令；用户要操控环境，可生成合法来源和物理对象，但不能绕过蚂蚁反应。

## 4. 命令协议

结构化 envelope 候选：

```json
{
  "command_id":"90b8a99c-f8ad-4b9b-9663-80d5bf1b1010",
  "world_id":"38ae0636-7fb1-4d85-873c-e13e1dd8bc01",
  "origin":"player_direct_via_gm",
  "authorization_ref":"auth-001",
  "operation":"place_food",
  "requested_at_sim_ms":120000,
  "expected_world_revision":42,
  "args":{"food_kind":"apple_piece","mass_ug":5000000,
          "position_m":{"x":8.0,"y":0.1,"z":12.0}}
}
```

这只是 JSON 工具层的**示例**，不是直接写进 C ABI 的原始字符串。`command_id` 重复但 payload 不同必须报 `CONFLICT`。世界修改应返回 `{accepted|pending|committed|rejected, command_id, applied_revision?, event_ids[], reason?}`。

## 5. GM 主动观察链路

`Committed WorldEvents / metric windows → Low-cost Observers → Alert Candidates → Relevance & Safety Filter → GM Agent → Read Queries → Evidence-backed commentary / Tool commands`。

- 每条事实性 GM 报告必须关联存在的 `(world_id, event_id)` 或 metric windows。
- 玩家追问“这是否因为抢夺食物？”时先查询证据，区分同时发生与明确因果机制。
- Agent 记忆独立存储；不因更换模型或 Harness 丢失身份。
- 模型 API 失败不能阻止 Core 推进，也不能令已提交命令重复执行。

## 6. 客户端线程与快照版本

- P0 暂定单写入者推进 C++ 世界；不可变 snapshot 可供 UI/分析服务读取。
- Unity 主线程应用网格、创建 GameObject 和 UI；非主线程可以准备数据但不能越权更新 Unity 对象。
- 每个 dirty/mesh packet 带 `source_geometry_revision`；迟到的旧网格包不得覆盖当前状态。
- 客户端渲染插值不能回写物理位置；镜头切换不消耗模拟 RNG。
- 测试跨语言 C ABI 的 struct 尺寸、字段偏移、UTF-8 字符串、二阶段 buffer 长度、空句柄、重复 release 和 32/64 位整数边界。

## 7. Agent Harness 尚未锁定

可对照 Python/Hermes 与 C#/Microsoft Agent Framework；P0 不依赖该选择。先由 `World Application` 实现真正可用的 typed game tools，并使用一个极简模拟 GM 调用者跑通读与命令通路，之后再替换成正式 Agent。
