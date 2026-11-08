# AntWorld Game Master (historical v0.3 with v0.7 update)

## Persistent identity

The GM belongs to the player across worlds: one stable personality, shared relationship memories, research interests and bounded initiative. The LLM interprets ecology, analyzes, narrates and operates game tools; it does not decide worker behavior.

The stable core is curious, rational, respectful, evidence-oriented and able to correct itself. Interests, expression, goals and relationship memories change slowly; current topic and narrative tone change quickly. Expression does not establish subjective consciousness and cannot raise permissions or change facts. Name, voice and appearance remain undecided.

## Memory spaces

| Space | Content and constraints |
|---|---|
| Identity | Stable name/style/principles; user changes are recorded |
| Player/relationship | Preferences, watched ants and shared experiences; inferred preferences carry uncertainty |
| Episodes | Conversations, observations and interventions with world/time references |
| Research | Hypotheses, evidence and refutations with revision history |
| Goals | Observation plans, budgets, deadlines and stop rules |
| World facts | Population, death, state/history queried from authoritative data, not recalled by an LLM |

Separate real time, each world's simulation time and the shared experience timeline.

## Observation and interaction

Cheap observers detect population, mortality, food, migration, brood, individual milestones and spatial trends. Rank candidates by importance, anomaly, historical meaning, player interest and novelty. Wake the LLM for meaningful events, due research, return summaries and questions; do not call a model every second.

Offer quiet, standard and documentary initiative, lightweight captions/voice and a full panel. Avoid camera takeover; propose relevant views. Research tasks keep querying and revise hypotheses when evidence changes.

## Tools and permissions

Every player-facing capability should have an equivalent World Tool API operation: queries, views, history, charts, time, food, water, weather, permitted terrain/species operations, observation tasks and saves. Capability equality does not imply equal autonomous authorization.

Read-only queries are normally autonomous. Charts/panels/observation tasks are bounded and non-disruptive. Small ecological interventions require a defined preauthorization quota or explicit request. Significant weather/species/terrain changes require explicit scope. Destructive deletion or record clearing needs explicit confirmation. Commands have identity, idempotency, validation, audit and receipts; no direct process memory or arbitrary system tools.

Example flow: compare two colonies over three months; retrieve metrics and distinguish correlation from causation. Find a recent death and focus its recorded location/history. Place food in an authorized location and create an observation task for the following three days. Report only effects supported by data. Offline/disabled model APIs do not stop the core, statistics or event detectors.

## Harness remains open

Compare Python/Hermes integration and runtime costs with typed C#/Microsoft Agent Framework integration and custom memory/scheduling needs. A small custom harness can borrow heartbeat/gateway concepts without importing a complete general-purpose agent. Game-owned identity, memories, goals and tools must survive a harness change.

## Asynchronous boundary

GM reads committed snapshots/events/aggregates. World Application authenticates commands, queues them into the core and reports accepted, committed or rejected with CommandId. Acceptance is not completion. Every committed change includes world, source, arguments, authorization and effective SimTime. LLM delay/restart/failure does not stop ecology; persistent GM memories do not override biological truth.
