# S6.2 measurement and observer implementation

Frozen protocol: document 39, commit `3f6d1a9`. No Core behavior or parameter change is authorized by host instrumentation alone. Schema 8 / physics 9 remain unchanged. All fixtures and biological rules remain ENGINEERING_FIXTURE.

## Hardware acquisition

The user installed HWiNFO and enabled sensors, shared memory and a CSV logger after the initial preflight. Windows reports ten physical cores / sixteen logical processors: six efficiency-class-1 SMT cores and four efficiency-class-0 cores. The frozen selector chooses logical CPU 0, pins the benchmark to mask 1 and excludes its whole physical core (logical 0/1) from the observer process. This is process-local affinity, not a global power or scheduling change.

The available source is the user-provided HWiNFO CSV. The shared-memory reader currently reports Windows error 2 (mapping not found); no value is invented from that interface. CPU/package temperatures, actual/effective frequencies, CPU package and IA power, thermal/power-limit flags and PL1/PL2 limits are selected by a reviewed index-to-English-label map. The original localized log and immutable prefix snapshots remain local and untracked, as required by the English repository policy. Tracked exports contain every selected CPU sample in each session window plus 3 s of bracketing, raw numeric/Boolean values, source line numbers, source-prefix SHA-256 and per-column label hashes. Non-CPU/network/drive details are not needed for the experiment.

Windows PDH and system time/power APIs are sampled at a target 100 ms interval. HWiNFO retains its actual independent polling cadence; multiple short phases can share the same bracketing sensor observations. These readings must not be advertised as instantaneous 100 ms temperature/power measurements. Logger flush delay, actual sample gaps, the 12-hour free shared-interface limit, unavailable readings and timestamp coverage are reported. CSV fallback does not rely on bypassing that shared-interface limit.

The telemetry-disabled control disables only the new Python/PDH sampler. HWiNFO continues unchanged in all runs, so that control estimates the additional collector cost, not total HWiNFO overhead. No driver, fan, voltage, battery-saver or global power-plan setting is modified.

## Timers and semantic checks

`antworld_s6_2_benchmark` reuses the exact S6 fixture inputs in a separate application. The old benchmark remains intact. Each sample independently reports setup, ten advances, checkpoint encode and restore. A stamp records steady-clock duration, UTC endpoints, process CPU time, cycle count and processor index. The stamp/API overhead remains part of the small timing uncertainty; all explicit file output, integrity checks, subsequent continuation and destruction are outside the four phases. The existing optional nine-category profiler reports each phase separately. Normal builds remain uninstrumented.

Every sample verifies checkpoint equality and a further 1 s restored continuation. Baseline state/trace/work counts must match S6.1, across order/affinity, normal/profile builds and all repetitions. Warmups and every unfavorable timing are retained. Existing power policy, background process CPU snapshots and all available telemetry are recorded, not silently controlled or filtered after the fact.

## Nutritional evidence

The new host observer uses immutable copies of public individual state and ordered committed facts. It applies real intake, transfer and absorption amounts, real stage/death facts, and actual geometry-edit energy expenditure. It compares reconstructed crop, tissue, body energy, hydration, program and stage with authoritative queries after every event timestamp. Private contact ranks and uniform eligible-recipient selection are reconstructed from copied spatial buckets and the existing deterministic RNG; actual candidate work and surviving scheduled recipient must agree. Same-time competition is read in actual committed order. Observer-only exhaustive contacts remain outside the Core and cannot become ant knowledge.

The observer separately marks decisions whose next action was canceled by a later same-time program change; those are not failed gifts or transferred nutrients. Threshold time is cumulative retained crop plus tissue reaching the unchanged 100 ug fixture requirement, not an immediate emergence. Initial pupal tissue is explicitly retained as initial input. Every 30 s, observation, accelerated execution and checkpoint/restored continuation must match byte for byte. Each full case is also compared with the immutable S6.1 raw case before its diagnosis is accepted.
