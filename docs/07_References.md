# AntWorld｜资料与研究依据（2026-11-08 核对）

> 引用用于帮助未来标定模型。不同物种之间不可直接照搬数值；以下列出已核对的重点来源与适用范围，不代表所有 Game Design 公式已获生物学证明。

## 巢内空间、社会网络与分工

1. Mersch, Crespi, Keller (2013). *Tracking individuals shows spatial fidelity is a key regulator of ant social organization*. Science. **物种：Camponotus fellah**。年龄、巢穴空间与实际接触网络联系。 https://pubmed.ncbi.nlm.nih.gov/23599264/ ; 数据 https://datadryad.org/dataset/doi:10.5061/dryad.8d8h7
2. Ant social network structure is highly conserved across species (2024). **跨 5 蚁种对照**，网络社区与巢内/巢外分工。 https://pubmed.ncbi.nlm.nih.gov/39079671/
3. Biological rhythms and task allocation in ant colonies (2023). 巢内/巢外活动、年龄/位置、日节律综述。 https://www.sciencedirect.com/science/article/pii/S2214574523000597

## 巢穴建造、挖掘与微气候

4. *Experimental evidence that increased surface temperature affects bioturbation by ants* (2023/2024). **物种：Lasius niger**；17 个年轻群落、100 日土柱/X-ray，温度改变巢深、体积及巢室深度。https://pubmed.ncbi.nlm.nih.gov/38155266/ ; https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/1365-2656.14040
5. *Stigmergic construction and topochemical information shape ant nest architecture* (2016). **物种：Lasius niger**；三维建造中的局部物质/化学线索与集体结构生成。注意研究关注某些筑造行为，不能直接推断一切地下挖掘规则。https://pmc.ncbi.nlm.nih.gov/articles/PMC4747701/
6. *Nest enlargement in leaf-cutting ants: relocated brood and fungus trigger the excavation of new chambers* (2014). **物种：Acromyrmex lundi**；幼体/真菌搬运和巢室形成，**不能直接当成 Lasius niger 已证实机制**。https://pubmed.ncbi.nlm.nih.gov/24830633/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC4022738/
7. *Thermoregulation strategies in ants* (2014). **多蚁种综述**，包括 Lasius 属在内的育幼转移与微气候梯度。https://pmc.ncbi.nlm.nih.gov/articles/PMC3962001/
8. *Characteristics of thermal processes in ant nests built under stones* (2022). **物种包含 Lasius niger**，巢址/石块/热环境与育幼关系。https://rosa.uniroma1.it/rosa02/fragmenta_entomologica/article/view/719

## 卫生、低活动与生命周期

9. *Nest Etiquette—Where Ants Go When Nature Calls* (2015). **物种：Lasius niger**；巢内排泄斑块与巢外其他废弃物堆，说明不同垃圾类别位置策略不同。https://pmc.ncbi.nlm.nih.gov/articles/PMC4332866/
10. *Waste management by ants: the enhancing role of larvae* (2020). 清洁与幼体/废物风险。具体物种需要查看原始方法后用于定量标定。https://www.sciencedirect.com/science/article/pii/S0003347220302608
11. *Who Are the “Lazy” Ants? The Function of Inactivity in Social Insects* (2017). **物种：Temnothorax rugatulus**；长期不活跃个体与巢内空间/身体状态，**不等于 Lasius niger 通用比例**。https://pubmed.ncbi.nlm.nih.gov/28957517/
12. *Urban abiotic stressors drive changes in the foraging activity and colony growth of the black garden ant Lasius niger* (2024). **物种：Lasius niger**；温度、夜间活动、育幼发育、工蚁死亡。https://www.sciencedirect.com/science/article/pii/S0048969724002924

## 技术来源（官方）

13. Unity Native Plugins（C# 与 C/C++ C ABI）：https://docs.unity3d.com/Manual/NativePlugins.html
14. Unity User Manual / Burst: https://docs.unity3d.com/Packages/com.unity.burst@latest/
15. OpenClaw GitHub：https://github.com/openclaw/openclaw
16. Hermes Agent GitHub：https://github.com/NousResearch/hermes-agent
17. Microsoft Agent Framework GitHub：https://github.com/microsoft/agent-framework
18. SQLite WAL：https://www.sqlite.org/wal.html

## 待补专项文献

- 黑园蚁精细育幼搬运/清洁行为的量化研究。
- 黑园蚁独立建群产卵、发育时间、工蚁年龄与任务转换参数。
- 黑园蚁捕食/交哺转移时间、糖/蛋白资源利用与具体能量参数。
- 三维挖掘最小物料搬运速度、空间/密度负反馈定量标定。

## 自主三维建巢补充文献（v0.5 新增）

19. Garcia Ibarra et al. (2023/2024). *Experimental evidence that increased surface temperature affects bioturbation by ants.* **Lasius niger**，17个年轻群落、温度处理、100日土柱、X-ray 3D 巢形。DOI 10.1111/1365-2656.14040. https://pubmed.ncbi.nlm.nih.gov/38155266/。对应数据清单 https://doi.org/10.23708/ZJTSDI —— 原始文件目前标记为 restricted，未下载或拟合。
20. Khuong et al. (2016). *Stigmergic construction and topochemical information shape ant nest architecture.* **Lasius niger**，筑造物料沉积/顶盖与局部化学线索，不能当成地下挖掘参数。DOI 10.1073/pnas.1509829113. https://pmc.ncbi.nlm.nih.gov/articles/PMC4747701/
21. *Agitated ants: regulation and self-organization of incipient nest excavation via collisional cues* (2023). **火蚁、准二维**；局部碰撞可解释部分挖掘参与调节，不能直接转成黑园蚁定量规则。DOI 10.1098/rsif.2022.0597. https://pmc.ncbi.nlm.nih.gov/articles/PMC10189599/
22. *Soil Moisture and Excavation Behaviour in the Chaco Leaf-Cutting Ant* (2014). **Atta vollenweideri**，土壤湿度与挖掘/洪水回避的实验；其湿度阈值不适用于黑园蚁直接标定。DOI 10.1371/journal.pone.0095658. https://pmc.ncbi.nlm.nih.gov/articles/PMC3991694/
23. Tschinkel (2005). *The nest architecture of the ant, Camponotus socius.* 铸模巢室、通道、深度；其他物种仅作形态结构参考。DOI 10.1093/jis/5.1.9. https://pmc.ncbi.nlm.nih.gov/articles/PMC1283890/
24. Tschinkel (2004). *The nest architecture of the Florida harvester ant, Pogonomyrmex badius.* 三维深度、螺旋/倾斜通道；其他物种参考。DOI 10.1093/jis/4.1.21. https://pubmed.ncbi.nlm.nih.gov/15861237/
25. USGS, Healy (2008). *Simulating water, solute, and heat transport in the subsurface with the VS2DI software package.* 物理上土壤水热模拟可使用非饱和输运/扩散方程，但本项目第一版只采用简化守恒近似。https://www.usgs.gov/publications/simulating-water-solute-and-heat-transport-subsurface-vs2di-software-package

## v0.6 几何与 Unity 工程资料

- Unity 6.3 Native Plugins / PInvoke / marshalling: https://docs.unity.com/en-us/engine/6000.3/manual/programming-environment/plug-ins/native/overview 。**支持 C ABI 集成**，不自动提供几何/世界一致性。
- Unity 6.3 ApplyAndDisposeWritableMeshData: https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/mesh/applyanddisposewritablemeshdata 。**支持批量运行时网格写入**，需自行确保布局有效。
- Unity runtime Mesh Collider guidance: https://docs.unity3d.com/jp/current/Manual/physics-optimization-cpu-mesh-cooking-options.html 。说明运行时 mesh cooking 的潜在成本与简化代理建议。
- OpenVDB 官方文档：https://www.openvdb.org/documentation/doxygen/overview.html ；提供稀疏体积、窄带 level-set 和 CSG 相关工具。**可研究为缓存层候选，不等于必须使用，也不能取代参数化权威。**
- CGAL Polygon Mesh Processing / Boolean operations: https://doc.cgal.org/6.1.1/Polygon_mesh_processing/index.html 。可参考几何鲁棒性/布尔操作与数值精度问题；首版不预先绑定 CGAL。

## v0.7：事件调度与 Unity 技术依据

- OMNeT++ Simulation Manual，Future Event Set、严格时间序列、同一时间事件优先级与整数定点时间表示：https://doc.omnetpp.org/omnetpp/manual/index.html 。**这是离散事件算法的技术参照，并非本项目直接使用 OMNeT++**。
- Unity 6 Native Plug-ins：C/C++ 插件经 C 接口及 P/Invoke 与 Unity C# 交互：https://docs.unity.com/en-us/engine/6000.6/manual/programming-environment/plug-ins/native/overview 。版本选择仍以项目锁定的 Unity LTS 为准。
- 混合连续/离散调度、屏障顺序、LOD/TimeScale、物料事务与存档协议，是本项目提出的**工程候选方案**；必须由自动测试和数值验证确定，不能视为已经被论文验证的生物模型。
