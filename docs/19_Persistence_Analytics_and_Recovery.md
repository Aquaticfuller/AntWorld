# AntWorld｜存档、世界历史、统计定义与崩溃恢复 v0.8

## 1. 三份数据不是同一回事

**权威世界状态（Checkpoint）**：包含当前实体、生理、记忆、几何、资源、未来事件、RNG、命令 ledger；用于继续相同世界。

**事实事件（Event Journal）**：只保存已经提交的出生、死亡、食物转移、挖掘、人工操作等；服务个体档案、因果证据和长期历史。不保证从全部高层事件重新演化出同一个世界。

**指标时间序列（Metrics）**：根据事实状态/事件定义生成的聚合统计；服务图表与 Game Master 分析；可以有降采样与历史分辨率。

跨世界 GM Identity/Memory 属于第四个独立数据空间，**不是**世界事实权威。

## 2. Checkpoint 内容契约

| 类别 | 必须保存 |
|---|---|
| Header | magic、schemaVersion、physicsVersion、worldId、seed、checkpointRevision、创建时程序版本、哈希 |
| Time | simTimeMs、Phase、每个子系统下次触发时间 |
| Entities | 所有已实例化个体的身份、生理、任务、有限记忆、位置、nextWakeup |
| Spatial | InitialSolid version、有序编辑检查点+增量、material ledger、geometryRevision、派生缓存失效标志 |
| Resources | 食物各质量组分、工蚁携带量、嗉囊、土粒批次与源汇 |
| Scheduler | 未来事件队列、稳定 sequence、外部命令 pending 队列 |
| Random | 明确 PRNG 算法/版本，每流状态或 counter |
| Authority | CommandId → payload hash → execution receipt，已提交 revision/event cursor |
| Analytics | 统计累加器、时间窗边界、持久化 cursor |

**重要**：不保留 `FutureEventQueue` 或 RNG 状态的文件不能标成可完整恢复的存档。检查点必须在已提交屏障创建，不能序列化提交到一半的状态。

## 3. 最初实现分两步

**S0/S1**：内存 checkpoint round-trip（Serialize→Deserialize→Advance），只测结构、身份、时间、队列和 RNG 的复现；不需要引入数据库。

**持久化里程碑**：`AntWorld.Persistence` 将 checkpoint blob、对应 `event_cursor`、需持久的命令 ledger 和相关事件/聚合结果写入**同一个 SQLite 事务**，成功提交后才标记 durable。大型场景的独立二进制文件 + manifest/恢复协议是未来优化，不应在 S0 提前复杂化。

如果使用数据库与文件混合，必须引入 generation 标识及明确的两阶段恢复协议，不能声称跨文件 `rename` 与 SQLite commit 天然原子。

崩溃模拟至少包括：存档前、写入中、commit 前、commit 后、恢复校验失败、执行命令后重复接收。恢复只使用最后一个完整已提交的 checkpoint。

## 4. P0 数据库逻辑表

| 表名 | 关键列 | 约束 |
|---|---|---|
| `world_meta` | world_id PK, seed, sim_time, physics_version | 不跨世界共享状态 |
| `checkpoints` | world_id, checkpoint_rev, blob, hash, event_cursor | 联合唯一；完整 blob 与 cursor 同事务 |
| `committed_events` | world_id, event_id, sim_time, type, payload, source_command | (world_id, event_id) 唯一；只存已提交事实 |
| `metrics` | world_id, owner_type/id, metric_id, window_start/end, value, unit | 指标定义有版本，禁止混单位 |
| `command_receipts` | world_id, command_id, payload_hash, status, applied_revision | 相同 command 重试幂等 |
| `tracked_trajectories` | world_id, entity_id, tick, pos, precision | 保留精度标签；高频只给重点个体 |

GM 在独立逻辑数据库中存 `identity`, `relationship_memory`, `episode`, `research_goal`, `observation_task`, `tool_audit`，但 GM 对实际工蚁出生日期/库存的回答每次仍查世界事实。

## 5. 指标必须先定义再画图

| Metric ID（候选） | 精确定义 | 单位 |
|---|---|---|
| `colony.worker_alive` | 当前 `stage=Adult,caste=Worker,alive=true,colonyId=X` 的不重复实体数 | 只 |
| `colony.queen_alive` | 当前活着的成虫蚁后数 | 只 |
| `colony.brood_egg` | 当前存活 `stage=Egg` 的个体数 | 只 |
| `colony.brood_larva` | 当前存活 `stage=Larva` 的个体数 | 只 |
| `colony.brood_pupa` | 当前存活 `stage=Pupa` 的个体数 | 只 |
| `colony.emerged_count` | 时间窗内 `Pupa→Adult` 的去重事实事件数 | 次 |
| `colony.death_count` | 时间窗内唯一 `AntDied` 事件数 | 只 |
| `colony.food_collected_carb_ug` | 时间窗内通过合法采集事务真正进入个体/蚁巢的碳水质量 | µg |
| `colony.food_collected_protein_ug` | 同上蛋白质质量 | µg |
| `colony.food_collected_water_ug` | 同上水质量（不包含环境未摄取水） | µg |
| `colony.food_consumed_carb_ug` | 时间窗内实际代谢/消化的碳水质量 | µg |
| `colony.trophallaxis_transfer_ug` | 时间窗内两工蚁之间实际转移的总质量；这是内流，不能当作新获得资源 | µg |
| `colony.excavated_dry_soil_ug` | 已提交真实材料切除的干土质量总和 | µg |
| `nest.volume_m3` | 权威几何在选定巢穴中经采样/解析得到的空腔体积，标记数值误差 | m³ |
| `colony.foraging_success_rate` | 成功完成并带回有效食物的出行次数 / 以对应规则完结的有效觅食出行次数 | [0,1] |

所有指标都有明确**抽样时间与时间窗语义**：人口是 snapshot gauge，出生死亡是 window event count；`foraging_success_rate` 需先在 P0 固定“出行开始/结束”的事件定义，不可用“接近食物源”充当成功。

## 6. 物料账本与数值误差

P0 物料账按 `ingredient`/`kind` 和 `source/sink` 单独分类，例如：

`InitialFood + SpawnedByAuthorizedCommand + Regeneration = RemainingFood + Carrying + Crop + Consumed/Metabolized + Discarded + OtherExplicitSinks`。

**注意**：交哺是内部转移，不能在群体总营养收支中再额外增加一次摄入量；身体能量 J 的变化应由转化效率与代谢提供，不能误把 J 当作 µg 加减。

土壤账独立于食物账：`initialDrySoil = remainingSolidDrySoil + carriedDrySoil + depositedDrySoil + exportedDrySoil`，另计含水量。实际几何交叠体积的近似误差必须有可测上限。

## 7. 事件证据与 Game Master

- `WorldEvent` 含 world_id、时间、相关 ID、origin、source_command、position、版本和 payload。
- AI 的“相关性 / 因果假设 / 叙事情绪”存单独 commentary 记录，并引用事件或指标 ID，不得写回 `committed_events` 冒充物理事实。
- 跨世界引用必须是 `(world_id, entity_id)`；复制世界形成实验分支时新 world_id 并记录 `parent_world_id + parent_revision`。
- 恢复较早时间线后 GM 仍保留共同记忆，但必须明确这是历史分支，禁止把未来事件当作当前事实。

## 8. 性能与存储规划

- 普通蚂蚁只保留基础档案、累计工作统计和重要事实事件。
- 重点蚂蚁保留更细致的轨迹采样，记录 `sample_precision` 与 `observed_or_interpolated`。
- 历史数据按时窗汇总，避免每只蚂蚁每秒永久写数据库。
- 记录 checkpoint 大小、写入时间、恢复时间、日志膨胀、压缩收益与数据正确性，性能优化不得移除关键事实。
