# AntWorld｜参数化几何编辑与局部 SDF 缓存：详细规格 v0.1

**归档版本：v0.6（2026-11-08）** · **状态：架构设计，未实现、未实测**

## 0. 决策与边界

- **用户已选定方案 A**：权威地下几何为**初始材料体积 + 按顺序提交的参数化挖掘/回填操作**；局部 SDF 只作为可丢弃、可重新生成的计算/渲染缓存。**这取代 v0.5 中“A 或 B 待对照”的提法。**
- 维持 24m×24m 初始世界、可扩展分块、真实三维地下巢穴、C++ 物理/生物权威与 Unity/C# 视图分离。
- 不能将“使用参数化几何”误解为预先规划好隧道和巢室：**局部蚂蚁挖掘事件积累形成形状**；参数化只是保存挖出的体积的工程表示。
- **约束**：只有切除真实材料才产生移土；只有真实回填、沉积操作才增加材料；禁用无依据的平滑使体积/质量在未记账下改变。

## 1. 权威模型：可重演的有序 CSG 记录

初始世界由 `InitialSolid` 定义：地表以下土壤、岩石/根系障碍、初始开巢空腔（设定为 creation-time seed edit），材料属性另按地层与局部采样查询。

对第 k 次已提交编辑，设权威材料集合 `S_k`：

- **Excavate**：`S_(k+1) = S_k \ E_k`，`E_k` 是一次工蚁移除实际土壤所覆盖的三维体积；实际切除量为 `S_k ∩ E_k`，而不是整个工具体积。
- **Fill / Deposit**：`S_(k+1) = S_k ∪ F_k`，但只能在材料账允许、目标可达且不与不可替换物质冲突的地方增加材料。
- **改动顺序重要**：挖掉→回填→再次挖掘和仅用挖掘/回填集合求并不等价。编辑记录保留 `sequence`, `tick`, `edit_id`, `cause`, `ant_id`, `geometry_before/after`, `materials`, `volume_estimate`, `error_bound`。

**权威读接口**是 `EvaluateSolid(p, version)`、`QueryMaterial(p)`、`QuerySurfaceIntersect(...)`、`QueryClearance(...)`。不得以 Unity Mesh、导航图或 SDF 砖单独回答“这里究竟有没有土”。

### 1.1 首版几何原语

| 编辑原语 | 参数 | 适用情形 | 限制 |
|---|---|---|---|
| `ExcavatePatch` | 接触点、表面法向、局部移除形状、尺度 | 单次挖土动作 | 必须从工蚁可触达的土壤界面开始 |
| `ExcavateSweep` | 有序控制点、截面半径沿程变化、端盖 | 多次小挖掘归并的隧道段 | 不能因曲线延长跳过中间挖掘动作 |
| `ExcavateLocalBlob` | 中心、主轴长度/方向、局部外形参数 | 连续侧壁扩挖形成局部大空腔 | 不对应预设“育幼室模板” |
| `FillPatch / Deposit` | 空间形状、材料批次、压实度 | 回填、巢口弃土、封堵 | 真实土粒必须有来源，不能凭空生成 |
| `SeedChamber` | 初始小巢室参数、建群情境 | 初始世界创建 | 初始条件必须可追踪，不冒充新发生挖掘 |

工具形状可采用 capsule、沿折线/Bezier 样条扫掠的可变半径圆截面、局部椭球补丁；**每次编辑规模由蚂蚁工作量和负载约束决定，不是自由画一条长通道**。

### 1.2 数学查询与 SDF 符号

定义 `phi_s(p) < 0` 为实体材料，`phi_s(p)>0` 为空腔；构造切除工具 `phi_E<0` 表示切除体积。若它们是局部隐式形状函数，则材料差可按 `max(phi_old, -phi_E)` 组合；加材料可按 `min(phi_old, phi_F)` 组合。**组合结果的符号可用于 CSG 内外判定，但在交线/接缝处未必仍是严格的欧氏 signed distance**，不可未经重新距离化就把其绝对值当成安全净空。

首版保留两种查询路径：
1. `EvaluateSolid`: 基于有序编辑历史/加速索引作权威内外判断与材质查询。
2. `LocalSDFCache`: 对局部活跃 AABB 进行解析函数采样、生成窄带 SDF/occupancy；仅供网格、预筛、近邻表面、细节显示等。**不通过 SDF 缓存直接提交物理编辑。**

## 2. 空间索引、精度与缓存失效

- 全局世界轴：`X=东，Y=上，Z=北`，米制；跨 C++/Unity 的轴映射、旋转约定、三角形绕序必须在 ABI 协议固定；Unity 场景使用同一坐标含义，避免隐式左右手反转。
- 权威几何坐标建议内部 `double`；Unity 当前分块局部渲染位置可用 `float`，便于未来扩大世界。
- `ChunkIndex` 对每个编辑的变更 AABB 建立空间索引。地表 **2m×2m** 为候选调度块；地下独立三维索引，不按地表块的固定高精度体素填满。
- `DirtyAABB = ModifiedAABB ⊕ halo`；halo 至少覆盖几何滤波、网格法线、碰撞净空和导航局部重建所需邻域，必须跨块标记。
- 近挖掘点候选局部采样 **1–2 mm**，砖例如 64mm 边长、2mm 采样约 32³ 单元；只是实验起点。较远巢壁按 LOD 降采样，但所有真实通行判断须以不超过最小蚂蚁净空的保守精度核验。
- SDF、`RenderMesh`、`NavRegion`、`CollisionProxy` 均带 `geometry_revision`/`build_revision`，丢失后可从权威记录重建。
- 布尔组合造成形状退化/薄壁时优先 **保守禁止通行/挖掘**，标记 `UncertainGeometry` 而非假装通过。

### 2.1 编辑历史的长期成本

- 编辑日志一段时间后可能极长，不能每次空间查询线性遍历所有历史编辑。
- 权威编辑可定期做 **版本化检查点/几何压实（compaction）**：保存一份等价的紧凑权威几何加后续编辑尾日志；不得悄悄丢失历史源事件，长期研究历史保存于 WorldEvents。压实前后对占用、质量账、查询边界与连通做回归。
- 原本的 EditId 与关联工蚁事件 ID 保留，压实只改变运行内部表示，不能让历史查询断链。

## 3. 生物驱动的动态挖掘：六步提交

工蚁不能自己生成整段新隧道。实际计算流程：

1. **局部感知**：工蚁接近已连通空腔的土壤界面，`DiscoverFrontier` 返回本地可触达候选点、法向与土质。
2. **生物决策**：个体响应阈值、营养/体力、拥挤、湿度、局部需求决定尝试概率，全部来自可感知条件。
3. **预约工作**：`DigProposal{ant_id, frontier_id, proposed_tool, max_work, carrier_capacity}` 进入确定顺序的调度队列，限制同一材料被并发重复切除。
4. **几何/材料验证**：是否撞到岩石/根；是否移除真实实体；是否与已有空腔重叠；能否真实携带相应干土与水质量；是否会让通路陷入不允许的危险状态。
5. **原子提交**：写入 `GeometryEdit`、产生携带的 `SoilParcelBatch` 与物料账变更；`geometry_revision++`、标记脏区、失效局部导航；一旦校验失败，**几何、材料、事件不发生部分提交**。
6. **导航与渲染更新**：安全核验相关连通路径后发布 `ExcavationCommitted` 和 `GeometryDirty`；网格显示可以稍后，但工蚁运动立刻遵守新几何版本的有效性。

### 3.1 重复挖掘和质量误差

实际切除量应由 `S_before ∩ E_proposal` 计算，不能仅取工具体积。若两只蚂蚁挖同一个位置，第二个提交必须重算当前材料交集；空腔已存在时，移除量为零，不能重复获得土粒或贡献。

真实空间中复杂交集体积计算可采用自适应积分/局部离散估计并记录误差上界，而非宣称有精确解析解。生产质量账应满足：

`ΔM_dry = ρ_dry_bulk * ΔV_removed + bounded numerical error`

`M_initial + M_import = M_remaining + M_carried + M_deposited + M_export + bounded residual`

水质量与干土质量分开账；回填密度变化允许改变回填体积，但不能增加干土质量。**验收应限定误差容差，并从切除量/物料数量同一估计链生成记录，不能双算不一致。**

## 4. 动态连通：几何判定在先，拓扑在后

**核心原则**：两条通道投影重合，不等于物理连通；中心线相交也不等于工蚁可通过。必须检查三维空腔是否存在**具有足够净空的连续通道**。

1. 以权威几何定义三维空腔 `F=Ω \ S`（Ω 为世界边界）。
2. 给定工蚁碰撞体近似半径/姿态及负载，计算可通行集合 `F_ant`（类似把障碍几何按身体包络扩张后的自由空间）。
3. 在 `F_ant` 中进行局部连接检验，保守识别开口 `Portal`、可行走空间 `NavRegion`，并维护 `NestGraph`。
4. 挖掘**新增**连通时更新连通分量；回填/塌落**删除**连接时，不能只用只能合并的 Union-Find，应对局部连通区执行 BFS/重建，必要时重算受影响组件。
5. 蚂蚁全局寻路先用拓扑图求连接路线，再在当前巢室/隧道局部进行运动与避让；全局图只用于实现已经选择的行为，不给蚂蚁透露未感知远方资源。
6. 若某区域的 `nav_revision < geometry_revision`，则暂时屏蔽受影响路径，先校验或重建，**严禁使用旧路径穿越新实体材料**。

### 4.1 巢室/隧道分类的状态管理

- `Tunnel`、`Chamber` 是**由空腔形态、局部宽度、连通和活动情况派生的语义**，不能决定蚂蚁自动挖出规定形状。
- 原型可用局部骨架/厚度与截面变化作候选：窄长为通道，较宽局部为巢室，真实数据可不完全符合二元分割。
- 防止网格微小改动就导致巢室编号不断跳变：使用持久区域 ID、形态变化滞回阈值；若拆分/合并产生新 ID，保留 `RegionLineage(old_ids, new_ids, tick)`。
- `Portal` 不与固定中心线绑定；必须有真实开口的三维净空几何。可容纳空载工蚁的孔不一定足以通过携带较大食物/土粒的工蚁。

## 5. 几何、物理与渲染的一致性策略

| 表示 | 权威？ | 使用者 | 更新保障 |
|---|---|---|---|
| `BaseSolid + OrderedEdits` | **是** | C++ Core | 原子提交，持久版本 |
| 局部 `SDF/occupancy bricks` | 否 | C++ 查询加速/网格生成 | 脏区失效，版本匹配 |
| `NavRegion/NestGraph` | 否 | C++ 个体运动 | 过期先封锁或重建 |
| `CollisionProxy` | 否 | C++ 局部碰撞 | 必须匹配当前有效几何 |
| Unity `RenderMesh` | 否 | 画面与剖切 | 允许少量延迟，但带版本 |
| Unity `MeshCollider` | **否** | 可选镜头/点击辅助 | 不能负责工蚁的真实碰撞判定 |

建议蚂蚁的实际物理避障由 C++ 自有的局部可行性查询和简化碰撞完成，不强迫几千只蚂蚁使用 Unity Rigidbody 与实时重煮的 MeshCollider。Unity 官方提醒运行时网格碰撞烘焙有成本，适合对照分析。资料： https://docs.unity3d.com/jp/current/Manual/physics-optimization-cpu-mesh-cooking-options.html

### 5.1 分块网格生成

- 本次提交仅更新 `ChangedAABB` 附近几何。建议使用局部 SDF 采样 + Marching Cubes 或 Dual Contouring 生成表面网格，比较薄壁保真、跨块拼缝和法向质量；初版不把算法选择视为已定。
- 网格生成可在 C++ 后台任务完成，Unity 主线程将最新版本网格应用到 Mesh。Unity 6.3 支持 `Mesh.AllocateWritableMeshData` 与 `Mesh.ApplyAndDisposeWritableMeshData` 等运行时网格数据接口；需要正确设置顶点/索引布局与生命周期。官方资料：https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/mesh/applyanddisposewritablemeshdata
- 透明模式与剖切是 Shader/相机/视图层功能，**不修改权威世界几何，不创建新的模拟连通通道**。

## 6. C++ 模块与类职责

```text
sim/spatial/
  WorldCoordinate.h, MaterialField.h, InitialSolid.h, EditSpatialIndex.h
sim/nest/geometry/
  GeometryPrimitive.h, GeometryEdit.h, GeometryHistory.h
  ConstructiveSolid.h, GeometryQuery.h, GeometryTransaction.h
  SdfBrickCache.h, DirtyRegionTracker.h, MeshRebuilder.h
sim/nest/navigation/
  ClearanceQuery.h, NavRegion.h, Portal.h, NestGraph.h
  ConnectivityValidator.h, LocalNavRebuilder.h, RegionLineage.h
sim/nest/digging/
  DigProposal.h, DiggingScheduler.h, SoilParcelLedger.h
  DepositAction.h, DiggingEventWriter.h
sim/nest/environment/
  SoilMaterial.h, SoilHeatField.h, SoilWaterField.h, ChamberClimate.h
sim/api/
  AntWorldNativeApi.h, GeometryDeltaDto.h, WorldCommandDto.h
```

核心职责界面（逻辑而非已经实现的 C++ API）：

| 类型 | 职责 |
|---|---|
| `ConstructiveSolid` | 基于初始材料与有序 edits，回答任意版本材料/空腔查询 |
| `GeometryTransaction` | 预约、校验、实际切除体积、土壤账、原子提交 |
| `EditSpatialIndex` | AABB 查询与跳过不相关的旧编辑 |
| `SdfBrickCache` | 活跃空间的窄带字段和可重建缓存 |
| `ClearanceQuery` | 按蚂蚁体型/负载进行三维可通行核验 |
| `ConnectivityValidator` | 派生 portal 与 graph，处理断连/打通 |
| `DirtyRegionTracker` | 将几何版本变化映射到网格、导航、环境脏区 |
| `MeshRebuilder` | 生成 Unity 可消费的网格更新包，不依赖 UnityEngine |
| `SoilParcelLedger` | 统计被挖、携带、弃置与回填的干土/水质量 |

## 7. 升级、存档与追溯

权威存档至少包括：`world_id`, `schema_version`, `geometry_revision`, 基础材料版本/地形、初始空腔、压实检查点、压实后 ordered edits、未完成挖掘/运输任务、材料账、所有个体状态、事件日志引用、随机状态。SDF/bricks/mesh/nav 可在加载后重建，不作为唯一可信存档。

每个挖掘事件有 `event_id`, `edit_id`, `ant_id`, `world_id`, `sim_tick`, `before_version`, `after_version`, `affected_aabb`, `removed_dry_mass`, `removed_water_mass`, `soil_parcel_id`, `connectivity_delta` 等字段。暴露供统计和跨世界 Game Master 查询，但它不能绕过正常工具操作直接编辑土壤记录。

## 8. 已确定、工程建议和待验证

- **确定**：方案 A 的几何权威；参数化有序切除/回填；SDF/渲染/导航皆为可再生派生物；C++ 核心独立、Unity C# 展示。
- **工程建议**：上述原语、事务/检查点和查询接口、保守净空判定、局部 SDF/网格方案。
- **待验证**：具体几何原语组合、切除体积积分的性能和误差、如何稳健从几何派生房间与门户、最小精度、重建频率、算法库依赖。
