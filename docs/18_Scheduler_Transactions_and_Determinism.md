# AntWorld｜统一时钟、动作事务与确定性语义 v0.8

**目标：** 将 v0.7 `13_Simulation_Runtime_and_Scheduler.md` 的概念设计具体化，避免不同模块对同一时间和共享资源采用不同写入路径。P0 使用单写入者执行器；所有其它系统只产生状态更新请求。

## 1. 模拟时间规则

- `SimTime = int64 milliseconds` 为 P0 实施默认；使用强类型封装，所有真实秒数转成毫秒时检查溢出。
- `WallTime` 只决定 `advance_to(target)` 的目标；`RenderTime` 只用于插值，不能反写 Core。
- 无画面、实时、加速和离线使用同一套核心推进逻辑；同种调度与事件种子下，加快运行只改变现实耗时，不修改模拟方程。
- 每个事件具有确定的 `sim_time`；处理未来事件时不能晚于其生效时间；外部命令只能在安全边界提交。

## 2. 事件队列排序

推荐比较键 `EventKey = (time_ms, phase, semantic_priority, stable_tie, event_sequence)`。同刻顺序按明确定义的规则而不是内存地址/多线程竞态。

**阶段定义（P0）**：

| Phase | 含义 | 典型操作 |
|---|---|---|
| 0 | input / command | 将已鉴权命令冻结并验证 revision 与幂等 ledger |
| 1 | environment / lifecycle | 到期天气、发育转换、死亡、资源失效；提交到期连续过程效果 |
| 2 | perception | 每只需唤醒的蚂蚁读取**同一个已提交状态**的局部刺激 |
| 3 | proposals | 生成 Move/Collect/Trophallaxis/Excavate 等不修改世界的意图 |
| 4 | conflict resolution | 批量验证资源量、携带容量、空间净空，确定转移量与冲突处理 |
| 5 | atomic commit | 完成实体/资源/几何的全有或全无变更，校验不变量 |
| 6 | publish | 产生事实性 WorldEvent，增长 revision，累加统计 |
| 7 | reschedule | 调度下次唤醒、阈值到达、缓存失效、观察事件通知 |

同刻 `death` 已生效后，死亡个体在 proposal 阶段不能提出成功动作；先已提交的事实不能由迟来的 command 追溯改变。

## 3. AdvanceTo 的参考规范

```text
AdvanceTo(target):
  require target >= WorldClock.now
  while now < target OR current_boundary_has_due_work:
      next = min(target, earliest_future_event, earliest_rate_boundary,
                 required_near_field_substep)
      next = AdjustForKnownCrossingOfHardThresholds(now, next)
      IntegrateContinuousWorldState(now, next)  // 不得越过新显现的生命阈值
      now = next
      proposals = GatherDueEventsCommandsAndLocalPerceptions(now)
      commit = ResolveAndCommitAtBarrier(proposals)
      AssertInvariants(commit.affectedStores)
      AppendCommittedFacts(commit.events)
      ScheduleNextWakeups(commit)
      DetectZeroTimeLoopAndProtect()
  return immutable read snapshot reference
```

如果一个事件在同一时刻的早期阶段新增同刻的“早期阶段事件”，不能无限重入。规则：推迟到下一个合法提交边界或由明确的同阶段循环/上限处理；连续超限必须报诊断错误，而不是卡死。

## 4. 连续过程的事件化边界

| 连续变量 | 基础积分候选 | 必须截断/重评估的事件 |
|---|---|---|
| 能量 J | `E(t+Δt)=E(t)+∫(P_in-P_out)dt` | 能量耗尽、进食、环境变化、行为切换 |
| 体水 µg | 输入-损失；质量入/出有源汇记录 | 脱水阈值、饮水、湿度变化 |
| 幼体进度 | 依据阶段/温度/营养积分 | 幼虫饥饿、跨发育阈值、死亡 |
| 信息素场 | 稀疏沉积，按需指数衰减；可选扩散由稳定数值步长推进 | 沉积、采样、场更新 |
| 气候 | 地表粗场/地下局部场低频推进 | 下雨、气候变化、巢穴挖通改变边界 |
| 近场运动 | 局部稳定步长、连续可达位置 | 遭遇障碍、个体接触、进入新网格/Portal |
| 远场运动 | 路径与 ETA 事件，按需要唤醒 | 通道几何变更、危险、接触或资源失效 |

不能用 `speedMultiplier` 直接乘生理速率。对于死亡风险，用事件时间上的累计风险或分段抽样处理，避免只在大积分结束时“补一次死亡”而忽略已发生的交互。

## 5. ActionProposal / Commit 细则

一个动作经历 `intent → validation → arbitration → commit → event`；**只有 commit 才创建真实事件**。

- 相同可用食物 4000 µg，两个工蚁各申请 3000 µg：总提交取走不超过 4000 µg；失败或部分成功者有明确 outcome，且各物料成分分别守恒。
- 两只工蚁对同一土壤进行交叠挖掘：移土只算与真实剩余材料集合的有效交集；材料、几何版本、携土批次共事务。不同 actor 的贡献归属按实际提交量记录。
- 交哺：必须满足接触、生命状态、嗉囊存量和接受容量；供者与受者变化一起提交，重复请求不能重复转移。
- 通道封堵：几何 commit 后相关 Portal 应立即标为无效；导航未重算时先封锁通路，不能暂时穿墙。

## 6. 同时竞争的确定性与公平

P0 处理共享资源时，可按 `(seed, sim_time, resource_id, proposal_group_id)` 生成稳定随机打乱顺序，**同一个初始场景与 seed 结果可复现**，又避免永久将低 ID 放在首位。必须使用一个明确实现的 RNG 算法，**不依赖不同标准库 `std::uniform_*` 的跨实现逐位一致性**；保存 RNG 计数器/状态。公平性用不同种子和竞争轮次统计，不以一次随机取舍声称生态公平。

## 7. LOD 与低频模拟

- P0 可先只实现一个固定精度的 reference runner，接口保留 `SimulationLevel`，不必同步开发所有 LOD。
- 一旦引入 L2 远场事件推进，仍保留个体唯一 ID、计划任务、物料账和需要处理的关键事件。
- 与高精度个体发生实际接触之前，恢复兼容的行为/空间精度。
- 重点个体提高历史采样，不应凭空赋予更高智力或运气。回放明确区分真实记录与插值/示意。

## 8. Pause 与外部命令

暂停=不推进模拟时间；只读查询、镜头、历史浏览、聊天继续工作。改变世界的命令进入 `pending` 队列；首版采用“恢复后第一个安全边界生效”的保守规则（除非未来显式设计暂停状态下的 zero-time commit）。接收 pending 不等于已执行成功。

## 9. 确定性验收

- S0：重复运行同二进制、seed、场景和命令时间表，事件序列与关键状态哈希一致。
- 加速：同执行配置只改变现实速度，结果一致。
- 浮点与编译器优化变化：更强的逐位确定性不是未经测量的承诺，应记录浮点约束、平台、版本、允差。
- LOD 与多线程：验证守恒、身份、空间合法性与统计分布；不强制单次随机轨迹完全相同。
- 读取查询不修改 RNG 或下一事件的排列。

详见 `14_Simulation_Contracts_and_Test_Matrix.md`、`24_Traceability_and_Quality_Gates.md`。
