# Getting food from the surface to the founder

The original finite-supply nests delivered food while their queens never ingested a meal from the depot. After a worker deposits food it still has to reach the queen's crop and be absorbed. These are distinct committed events with different quantities and times. The paired experiments keep the original budgets, death rules, sealed starting chamber and registered observation days. Physics 39 is the historical default. All ages and masses below describe the simulation.

## What to watch

Run `.\tools\start_m0.cmd`. Under **Colony setup**, choose **Worker food offers · Physics 41**, seed **3**, finite supply, and select **New sealed nest**. Set the event selector to **Worker feeds the queen** and use **Next occurrence** twice. The first transfer contains 20 µg water. At the second, worker 23 transfers 12 µg carbohydrate and 88 µg water to queen 2. The view pauses at event 18,938 and follows the donor. Select the queen or seek **Queen absorbs carbohydrate** to see her side of the exchange. The selected animal's reserve panel reads its current native energy, body water, crop, lipid and mobile protein. A gift and its later uptake can be separated by hours of simulated time. [Actual browser stop](evidence/founder-access/worker-feeds-queen-zh.png) · [Native event identities](evidence/founder-access/local-offer-browser.json)

To see the other route, select **Food access experiment · Physics 40**, finite seed 3. Follow **Food delivery**, **Queen eats from nest stores**, then **Queen absorbs carbohydrate**. The worker delivered at 5,056,972,669 ms and the queen took her first meal at 5,184,000,000 ms. The browser stops at the actual event and returns to 1×. [Uptake screenshot](evidence/founder-access/queen-uptake-zh.png) · [Browser receipt](evidence/founder-access/founder-access-browser.json)

## From mechanism to outcome

For the obstructed carrier, select **Wall-side food delivery · Physics 43**, finite seed **2** and **Worker unloads from a wall → Next occurrence**. Worker 13 deposits its cargo on day 106. The event card links to the individual and lists each resource component, including a measured zero. For a worker-to-queen transfer, selecting the recipient opens her life panel at the same instant. The details disclosure exposes the full event ID and recorded position. [Wall delivery in the observer](evidence/founder-access/worker-unloads-from-wall-zh.png) · [Browser event](evidence/founder-access/wall-delivery-browser.json)

* **Physics 39, schema 32** supplies the historical control. The three finite Windows worlds kept 1,333, 1,333 and 2,655 µg carbohydrate in the nest when the queen died. None recorded a positive queen carbohydrate uptake.
* **Physics 40, schema 33** allows a hungry founder to walk to a locally perceived or personally known depot, around obstacles and occupied berths, and consume from it at actual mouth contact. A worker can eat a bounded part of its own acquired cargo at the source and remember a pantry it has actually used. Each ingestion debits its real source. The movement search also breaks symmetric choices at micrometre resolution with a stable order. [Frozen access test](FOUNDER_ACCESS_PROTOCOL.md)
* **Physics 41, schema 34** permits a stationary worker with surplus crop to approach an eligible, locally visible adult. Exchange requires two aligned, unobstructed mouths, nonoverlapping bodies, a payable donor and recipient crop space. The candidate does not reserve a ration for the queen. Food can reach another worker, a larva or nobody. In seed 3, event 19,427 records positive founder carbohydrate uptake 4.28 hours after the carbohydrate gift. This is temporal and inventory evidence. Individual carbohydrate molecules have no tracer identity. [Frozen offer test](LOCAL_OFFER_CONTROL.md)

| Physics | Supply | Seed | Workers eclosed | Food deliveries | Founder depot meals | Depot carbohydrate ingested (µg) | Positive founder carbohydrate uptakes | Queen death (days) | Living workers at day 150 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 39 | Finite | 1 | 8 | 1 | 0 | 0 | 0 | 69.67 | 0 |
| 39 | Finite | 2 | 5 | 2 | 0 | 0 | 0 | 70.09 | 0 |
| 39 | Finite | 3 | 8 | 2 | 0 | 0 | 0 | 69.11 | 0 |
| 39 | Absent | 2 | 6 | 0 | 0 | 0 | 0 | 70.11 | 0 |
| 40 | Finite | 1 | 5 | 1 | 15 | 1,183 | 15 | 73.12 | 0 |
| 40 | Finite | 2 | 7 | 7 | 0 | 0 | 0 | 68.92 | 1 |
| 40 | Finite | 3 | 7 | 4 | 31 | 1,321 | 28 | 72.55 | 0 |
| 40 | Absent | 2 | 7 | 0 | 0 | 0 | 0 | 68.95 | 0 |
| 41 | Finite | 1 | 5 | 1 | 15 | 1,183 | 15 | 73.12 | 0 |
| 41 | Finite | 2 | 6 | 7 | 0 | 0 | 0 | 69.18 | 2 |
| 41 | Finite | 3 | 7 | 2 | 35 | 2,642 | 36 | 78.18 | 0 |
| 41 | Absent | 2 | 7 | 0 | 0 | 0 | 0 | 68.95 | 0 |
| 42 | Finite | 1 | 5 | 1 | 15 | 1,183 | 15 | 73.12 | 0 |
| 42 | Finite | 2 | 6 | 7 | 0 | 0 | 0 | 69.18 | 2 |
| 42 | Finite | 3 | 7 | 2 | 35 | 2,642 | 36 | 78.18 | 0 |
| 42 | Absent | 2 | 7 | 0 | 0 | 0 | 0 | 68.95 | 0 |
| 43 | Finite | 1 | 5 | 1 | 15 | 1,183 | 15 | 73.12 | 0 |
| 43 | Finite | 2 | 6 | 128 | 0 | 0 | 0 | 69.18 | 2 |
| 43 | Finite | 3 | 7 | 2 | 35 | 2,642 | 36 | 78.18 | 0 |
| 43 | Absent | 2 | 7 | 0 | 0 | 0 | 0 | 68.95 | 0 |
| 44 | Finite | 1 | 5 | 1 | 15 | 1,183 | 15 | 73.12 | 0 |
| 44 | Finite | 2 | 7 | 6 | 0 | 0 | 0 | 69.35 | 1 |
| 44 | Finite | 3 | 7 | 2 | 35 | 2,642 | 36 | 78.18 | 0 |
| 44 | Absent | 2 | 7 | 0 | 0 | 0 | 0 | 68.95 | 0 |

The ordered delivery, depot meal and later uptake endpoint passes its prespecified 2/3 finite and 0/1 absent criteria for both 40 and 41. The additional funded worker-to-founder carbohydrate gift occurred in 1/3 finite worlds with Physics 41. A living queen **and** worker at day 150 occurred in **0/3** for each version. All 20 founder deaths in versions 40–44 were attributed to energy depletion on both platforms. The historical Physics 39 Windows control includes a dehydration death in finite seed 1 at event 20,559. Its living founder still had 365,792,656 nJ and 1 µg of body water one millisecond earlier. The corresponding historical Linux run recorded energy depletion. These are paired software seeds and no species survival probability is estimated. [Historical Windows events](evidence/founder-access/physics39-windows.jsonl) · [Historical Linux events](evidence/founder-access/physics39-linux.jsonl)

## Where the food stopped

Physics 41 seed 2 transferred nutrition 380 times to adult workers and nine times to larvae. Zero transfers went to the queen. Recipient stage is reconstructed at the transfer time. Summed exchanges count material that may circulate more than once. Immediately before death, the queen had 3 nJ body energy, 935 µg body water, empty crop and zero lipid or mobilizable protein. Four adult workers were alive. The depot contained 2,772 µg carbohydrate, 2,001 µg protein and 13,427 µg water. Its distance from her mouth was 5.37 mm. Her body state, death event and colony inventory agree; they do not single out one failed approach as the sole cause. In seeds 1 and 3 the depot instead had zero carbohydrate at founder death. Finite carbohydrate still existed outside in all three cases. The new mechanisms expose distinct failures in delivery continuity and in distribution after delivery. [All Physics 41 cases and pre-death states](evidence/founder-access/physics41-windows.jsonl)

The high event volume in Physics 41 seed 2 has a separate cause. Of its 854,074 facts through day 150, 452,587 fall in days 120–150. One loaded worker, 13, made 86,397 unsuccessful foraging decisions during that interval and never moved. All were classified by the Core as `No legal step`. Worker 13 was attached to a wall, carrying 3,900 µg, with its mouth 0.45 mm from the depot. Physics 40 seed 2 recorded 156,417 facts through day 150. These are counts of different realized workloads; they cannot be used as a fixed-workload CPU benchmark. [Physics 41 interval profile](evidence/founder-access/workload41-seed2.json) · [Physics 40 profile](evidence/founder-access/workload40-seed2.json) · [Prespecified wall-side unloading test](WALL_HANDOFF_CONTROL.md)

## Berth access and worker outcomes

Physics 42, schema 35, required both the old 2 mm center distance and anatomical mouth contact for a wall handoff. Zero qualifying wall deliveries occurred. Its event prefixes match Physics 41 at all 36 cuts. In the failing seed-2 world the loaded worker's center was 2.25 mm from the depot and its mouth was 0.45 mm away. [Physics 42 receipts](evidence/founder-access/physics42-windows.jsonl)

Physics 43, schema 36, uses the real worker mouth for the wall-side transaction, keeps the existing terrain and peer checks, and preserves the worker's own connector. At event 196,147 worker 13 unloaded 1,302 µg carbohydrate, 667 µg protein and 1,931 µg water. Its next committed movement, event 196,155, took 210 ms and ended 211 ms after the handoff. It delivered at the wall 121 times by day 150. The independent depot ledger reconciled. Releasing the loaded worker **passes**. The late activity endpoint **fails**. The same worker was empty and registered 86,398 no-legal-step decisions and zero moves in days 120–150. Its queen had already died. [Frozen oral handoff](MOUTH_HANDOFF_CONTROL.md) · [Every marked delivery and following movement](evidence/founder-access/workload43-seed2.json)

Physics 44, schema 37, tests whether an unloaded returner can recognize a locally accessible waypoint on its own practiced connector and use the existing autonomy review. The finite seed-2 histories agree through day 30. At 3,966,699,773 ms worker 6 reached the same position in both worlds. Reassessment changed the schedule there, before the eventual Physics 43 wall delivery. The prespecified same-worker test **fails**. Worker 13 made two funded deliveries, died of energy depletion on day 75.65 at event 137,021, and supplied no late work. Worker 12 survived and paid for 972 pantry intakes in days 120–150. There were zero explicit blocked-inward-to-outward decisions or wall deliveries in this seed and zero no-legal-step decisions in that late interval. The changed survival and absence of the original carrier account for the lower counter. Keep 44 available for comparison. The three finite worlds still had zero living queens at day 150. [Prespecified empty-return test](EMPTY_RETURN_CONTROL.md) · [First divergence](evidence/founder-access/empty-return-fork.json) · [Worker outcomes and late activity](evidence/founder-access/workload44-seed2.json)

Seed 2 produced 883,417 facts in 43 and 243,408 in 44. The native Windows process reported peak working sets of 26.76 and 17.39 MiB respectively in the registered runs. The workloads have different workers, events and survival. These measurements cannot qualify an observer overhead ratio. A discriminating follow-up would branch from just before the same unloaded worker faces the blocked inward step, with identical position, heading, inventory, peers and scheduler. That comparison needs an explicit treatment activation at that boundary. For founder survival, measure the unserved queen's eligible offers and simultaneously reachable donors and stock before altering resource budgets.

## Biological scope

Gösswald and Kloft describe food exchange between first workers and founding *Lasius niger* queens in tracer experiments. Both castes gave and received food. This is direct species evidence for the possibility and direction of exchange. The report does not supply a matched donor–queen dose distribution, contact radius or post-transfer oxidation curve. See printed pp. 30–31. [IAEA symposium paper](https://www.iaea.org/sites/default/files/18/03/ipc-rad-insects-agr-imp-1963-1-frontcvr-full.pdf)

The 2019 worker-network experiment observed oral contact, direction and food dissemination in five queenless, broodless groups from separate source colonies after food deprivation. The worker endpoints do not identify founder intake. Majidifar et al. used contact and mesh treatments to measure queen brood care. Their manipulation does not establish the amount of food actually transferred to the queen. [Worker network, Methods and Fig. S2](https://www.nature.com/articles/s41598-019-52019-6) · [Queen contact manipulation, Fig. 2](https://doi.org/10.1111/1365-2435.14536)

Local search and offer initiation are bounded modeling hypotheses. The 0.65 mm mouth allowance, orientation tolerance, donor floor, dose, absorption clock and founder budgets remain engineering fixtures. Independent synchronized observations would need identified colony, donor and recipient, food exposure, approach attempts including zeros, and crop and body measurements after a measured dose. No default model promotion or biological calibration follows from these worlds. B06 remains `INSUFFICIENT`, the historical application performance remains `FAIL` and all nine BR findings remain `BIOLOGICAL_BLOCKED`.

## Reproduction and integrity

The assay uses the three finite seeds and one absent-supply case from one sealed queen at 25 °C and 80% RH. It reads every canonical event in bounded pages, checks continuous IDs, reconstructs the depot ledger by component, and compares it with the live native ledger at each of nine observation times. For a founder death it reruns the same input to one millisecond before the event. Worker stage, directed exchanges, the four ingredient masses, and exact milestone events are recorded. Full and compact saves are exercised both before a paid exchange and across the later uptake. Native data constitute the sole source of world state.

Windows LLVM/MinGW and Linux GCC agree at all 36 cuts in each of Physics 40, 41, 42, 43 and 44, for both frame bytes and canonical event prefixes (180/180). Historical Physics 39 agrees at 10/36. The first traced historical discrepancy on seed 2 occurs on day 4.25, at event 143. An exploratory Physics 40 build also had a symmetric peer-choice divergence in seed 3. Both first differences and the intervening exploratory outcomes are retained. [First differences](evidence/founder-access/first-differences.json) · [Intermediate cuts](evidence/founder-access/development-cuts.json.gz)

Full SQLite replay exposed an independent engineering defect. After a legal change of floor berth, the verifier compared an earlier committed journey with the final shortened connector. The verifier now reconstructs the discarded prefix from committed adjacent outward steps and checks the paid local handoff, surviving suffix, cursor and actual subsequent moves. On seed 2, the compact snapshot one millisecond before the first wall delivery and the full archive just after it both reproduce the same native frame and subsequent facts as uninterrupted execution. Neither format or its history was rewritten. Event seeking advances in cancellable native timestamp batches. Actual playback resumes at 1× and the event panels report a committed transfer even when some of its components are zero.

From a full Windows checkout use the following commands. Build first. The live observers and assays share the resulting binary. A Linux CMake build can supply its executable with `--core`. Only compact receipts are written by the unattended assay.

~~~powershell
py -3 -B -m tools.build_m0_live --jobs 4
$data = 'research/single_nest/evidence/founder-access'
foreach ($v in 39,40,41,42,43,44) {
    py -3 -B -m tools.qualify_founder_access --physics $v --output "out/founder-$v.jsonl"
}
foreach ($v in 40,41,42,43,44) {
    py -3 -B -m tools.qualify_founder_access --compare "out/founder-$v.jsonl" "$data/physics$v-linux.jsonl"
}
py -3 -B -m tools.profile_founder_activity "$data/physics41-windows.jsonl" --seed 2 --output out/workload41.json
py -3 -B -m tools.profile_founder_activity "$data/physics44-windows.jsonl" --seed 2 --output out/workload44.json
py -3 -B -m tools.qualify_founder_access --fork "$data/physics43-windows.jsonl" "$data/physics44-windows.jsonl" --seed 2 --output out/empty-return-fork.json
py -3 -B -m tools.test_m1_browser --mode founder-access --browser 'C:\Program Files\Google\Chrome\Application\chrome.exe' --output out/founder-browser
~~~
