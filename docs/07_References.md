# Research and technical references

These references were collected in the original handoff dated 2026-11-08. This English migration preserves the references and evidence boundaries; it is not a new independent verification of every paper, API version or dataset access status. Consult primary methods/data before calibration. Other species cannot provide unqualified Lasius niger constants.

## Colony space, networks and work

1. Mersch, Crespi and Keller (2013), Tracking individuals shows spatial fidelity is a key regulator of ant social organization. Science. Camponotus fellah; age, space and actual contact networks. https://pubmed.ncbi.nlm.nih.gov/23599264/ ; https://datadryad.org/dataset/doi:10.5061/dryad.8d8h7
2. Ant social network structure is highly conserved across species (2024). Five-species comparison of network communities and inside/outside work. https://pubmed.ncbi.nlm.nih.gov/39079671/
3. Biological rhythms and task allocation in ant colonies (2023). Review of activity, age, space and daily rhythms. https://www.sciencedirect.com/science/article/pii/S2214574523000597

## Construction, excavation and microclimate

4. Experimental evidence that increased surface temperature affects bioturbation by ants (2023/2024). Lasius niger, 17 young colonies, roughly 100-day soil-column/X-ray study. Supports temperature-related nest form; not a complete individual digging algorithm. https://pubmed.ncbi.nlm.nih.gov/38155266/ ; https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/1365-2656.14040
5. Stigmergic construction and topochemical information shape ant nest architecture (2016). L. niger deposition construction and local cues; do not generalize directly to all underground removal. https://pmc.ncbi.nlm.nih.gov/articles/PMC4747701/
6. Nest enlargement in leaf-cutting ants: relocated brood and fungus trigger the excavation of new chambers (2014). Acromyrmex lundi, not direct L. niger evidence. https://pubmed.ncbi.nlm.nih.gov/24830633/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC4022738/
7. Thermoregulation strategies in ants (2014). Multi-species review including Lasius-related brood relocation and climate strategies. https://pmc.ncbi.nlm.nih.gov/articles/PMC3962001/
8. Characteristics of thermal processes in ant nests built under stones (2022). Includes L. niger; nest location, thermal environment and brood. https://rosa.uniroma1.it/rosa02/fragmenta_entomologica/article/view/719

## Hygiene, inactivity and life

9. Nest Etiquette--Where Ants Go When Nature Calls (2015). L. niger fecal patches versus other waste; distinct material categories and deposition patterns. https://pmc.ncbi.nlm.nih.gov/articles/PMC4332866/
10. Waste management by ants: the enhancing role of larvae (2020). Check original species/methods before quantitative use. https://www.sciencedirect.com/science/article/pii/S0003347220302608
11. Who Are the Lazy Ants? The Function of Inactivity in Social Insects (2017). Temnothorax rugatulus; not a universal L. niger inactive fraction. https://pubmed.ncbi.nlm.nih.gov/28957517/
12. Urban abiotic stressors drive changes in the foraging activity and colony growth of the black garden ant Lasius niger (2024). Temperature, nocturnal activity, brood and mortality. https://www.sciencedirect.com/science/article/pii/S0048969724002924

## Initial technical sources

13. Unity native plugins / C ABI: https://docs.unity3d.com/Manual/NativePlugins.html
14. Unity Burst: https://docs.unity3d.com/Packages/com.unity.burst@latest/
15. OpenClaw: https://github.com/openclaw/openclaw
16. Hermes Agent: https://github.com/NousResearch/hermes-agent
17. Microsoft Agent Framework: https://github.com/microsoft/agent-framework
18. SQLite WAL: https://www.sqlite.org/wal.html

The Agent projects are comparison references, not chosen dependencies. Missing research includes L. niger brood/grooming rates, founding/laying/development, age/task transitions, predation/trophallaxis/energy parameters, and small-scale excavation/transport feedback.

## Underground additions

19. Garcia Ibarra et al., the temperature/bioturbation study above, DOI 10.1111/1365-2656.14040. Data listing: https://doi.org/10.23708/ZJTSDI . The imported handoff described raw data as restricted and did not download or fit them.
20. Khuong et al., the construction study above, DOI 10.1073/pnas.1509829113. Deposition/roof building cannot directly calibrate underground excavation. https://pmc.ncbi.nlm.nih.gov/articles/PMC4747701/
21. Agitated ants: regulation and self-organization of incipient nest excavation via collisional cues (2023). Fire ants in quasi-2D, DOI 10.1098/rsif.2022.0597. Cross-species hypothesis only. https://pmc.ncbi.nlm.nih.gov/articles/PMC10189599/
22. Soil Moisture and Excavation Behaviour in the Chaco Leaf-Cutting Ant (2014). Atta vollenweideri, DOI 10.1371/journal.pone.0095658. Moisture thresholds are not L. niger measurements. https://pmc.ncbi.nlm.nih.gov/articles/PMC3991694/
23. Tschinkel (2005), The nest architecture of the ant, Camponotus socius. DOI 10.1093/jis/5.1.9, cross-species 3D form. https://pmc.ncbi.nlm.nih.gov/articles/PMC1283890/
24. Tschinkel (2004), The nest architecture of the Florida harvester ant, Pogonomyrmex badius. DOI 10.1093/jis/4.1.21, cross-species architecture. https://pubmed.ncbi.nlm.nih.gov/15861237/
25. Healy/USGS (2008), Simulating water, solute, and heat transport in the subsurface with the VS2DI software package. Physical-model reference; the first game model uses a simpler conserved approximation. https://www.usgs.gov/publications/simulating-water-solute-and-heat-transport-subsurface-vs2di-software-package

## Geometry and scheduling engineering

- Unity native ownership/marshalling: https://docs.unity.com/en-us/engine/6000.3/manual/programming-environment/plug-ins/native/overview
- Writable mesh data: https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/mesh/applyanddisposewritablemeshdata
- Mesh collider cooking costs: https://docs.unity3d.com/jp/current/Manual/physics-optimization-cpu-mesh-cooking-options.html
- OpenVDB sparse volumes/level sets/CSG: https://www.openvdb.org/documentation/doxygen/overview.html . Possible cache reference, not an authority replacement or required dependency.
- CGAL geometric robustness: https://doc.cgal.org/6.1.1/Polygon_mesh_processing/index.html . Not a selected first-version dependency.
- OMNeT++ future-event sets and ordering: https://doc.omnetpp.org/omnetpp/manual/index.html . Algorithmic reference, not a framework dependency.
- Another historical Unity native reference: https://docs.unity.com/en-us/engine/6000.6/manual/programming-environment/plug-ins/native/overview . Actual Unity version must later be pinned.

Mixed scheduling, commit barriers, LOD and checkpoint protocols remain AntWorld engineering designs to verify, not biological conclusions established by these technical sources.
