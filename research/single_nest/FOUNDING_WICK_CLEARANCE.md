# Local wick access and sustained founding intake

## Inputs and gates

Keep the physics-93 founding and terminal controls at revision
cbaf3d365fd23cf6d04ddcb5083b04283e33f457. The terminal test starts from the
last positive water uptake on day 61.75 and checks the result at
5,610,240,000 ms. The preserved day-63 cut is a second entry point into
that trajectory. Its paired gate requires a paid movement, available
water, legal ingestion or oral contact, subsequent absorption, and
survival at the old cutoff. Check actual sugar uptake in the same run
and preserve the previous late seed-2 sugar replay.

Run the existing two-year panel with the nearby feeder in seeds 1, 2, 3,
17, and 29 and the absent feeder in seed 2. Match initial stock, release
schedule, environment, queen reserves, and geometry. Keep the original
energy and water expenditure and mortality rules. The combined gate
requires a living founder, an adult emergence in the second year, and
worker growth relative to the day-73 and day-365 observations.

## Paired dehydration failure

The native control exactly reproduces death fact 121,565. From the last
water uptake to that death there are 77 founder decisions and zero
founder moves, drinks, or positive oral receipts. Worker 9 completes real
foraging and carries 575 µg of water at the final living cut. The
same-state probe on day 63 finds 280 µg water offerable from worker 9
after donor restrictions and a corresponding 89 µg founder request. The
mouths are visible and out of reach. The wick has 1,499,975 µg and is
sensed, with the founder outside ingestion reach.

Physics 94 uses a wider deterministic wick search. It preserves the
observed death and zero intake on both entry cuts. An isolated
read-only diagnostic finds a geometrically complete wick route by
omitting the nearby bodies while keeping terrain, posture and mouth
reach. Its first position is (-0.003375, -0.004, -0.0014375) m. The
occupied search finds no complete route. Both output paths are
geometrical proposals. The diagnostic is excluded from the runtime
action path.

## Local clearance under physics 95

A resting worker near a thirsty founder can consider a short, legal
repositioning when her known wick has no current route. The bounded
look-ahead keeps the other bodies fixed and tests whether this worker's
new position and heading can open a route. On the actual movement
boundary the nearby founder wakes and checks the new committed
positions. The look-ahead grants access only to a movement proposal.
Drinking still requires her own paid motion and actual mouth contact
with the funded source. A viable oral route remains eligible and uses
the existing contact and transfer transaction.

Offer selection now requires a complete plan for a local founder
encounter. An isolated step found by a different search previously
occupied the decision slot, even when the executor would reject it.
Releasing that slot lets the actor consider the next local opportunity,
including a real feeder trip or an attainable wick. The geometry
search bounds and the yield decision are engineering fixtures.

The day-63 continuation reaches a paid wick sip of 25 µg, 17.131
simulated seconds after the cut. Its founder first moves through five
committed legs. Worker 9 next offers 74 µg sugar and 26 µg water in one
mouth transaction. The founder receives 752 µg of oral sugar and
199 µg of oral water through the old deadline and absorbs 604 µg of sugar
and 199 µg of water. Starting at day 61.75 gives 1,036 µg of oral sugar,
202 µg of oral water, and survival through the same deadline. The older
seed-2 sugar replay retains worker 8's 358 µg of paid oral sugar and
the founder's 369 µg of sugar uptake.

## Reproduction

Run from the repository root with the native application built in Release.

```powershell
$core = 'build/m0-live/antworld_m0_live.exe'
py -3 -B -m tools.verify_wick_clearance --core $core
py -3 -B -m tools.audit_founding_activity --core $core --verify-archive --stimulus-version 95
py -3 -B -m tools.measure_first_meal --core $core --model wick-clearance --seed 2 --supply nearby --days 730 --feeding-continuity --trace-flux --include-water
```

## From-birth starvation after wick access

The physics-95 seed-2 founder absorbs 1,524 µg water, including an
absorption event on day 81.50. Her last oral sugar receipt is on day
63.26, followed by energy death on day 81.50. At day 64, workers 8 and 9
are in the same navigation cell at two distinct surface positions.
Worker 8 is empty at the connector entrance, while worker 9 carries
282 µg of protein at the mixed feeder. Both positions and both
collection counts persist through the terminal cut. They each commit
720 repeated rest actions in the last six hours. The mixed feeder still
contains 123,719 µg sugar at the terminal cut.

The empty worker blocks the carrier's route to the exact connector
entrance. The carrier occupies the empty worker's intended feeder
stance. A valid support and clearance route in an empty scene therefore
does not make the two opposing moves executable simultaneously. The
same-cargo matched cut retains the original field and water patch.

Physics 96 evaluates an ordinary side-step for an empty worker at the
surface entrance when a nearby loaded worker's return corridor is
blocked by its body. Both geometry sweeps and the shifted body's
clearance are checked. The side-step stays in the same navigation cell
and retains the actual connector and source memory. The carrier still
must enter and move through the existing route, then handle its own
cargo and any offered mouth transfer in the original transactions.

The first prototype reused the underground standing-site predicate
and rejected every surface destination. The measured prototype has
the same terminal death and zero deliveries as the paired control.
The surface step now uses the physical move and swept traffic
validators from foraging. Worker 8 moves first, followed by worker 9
entering and delivering its original load of 282 µg protein. The
founder receives 289 µg sugar and 74 µg water orally, absorbs 248 µg
sugar, and remains alive at the old cutoff. A restart during the
paid side-step reproduces the final frame and canonical facts.
