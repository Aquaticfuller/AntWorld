import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const file = new URL("../web/live_motion.js", import.meta.url);
const motion = vm.runInNewContext(readFileSync(file, "utf8") + "\nnew LiveMotion();");
function cut(time, cursor, position, extra = {}) {
    return {seeded_nursery: true, running: true, rate: 1, epoch: 1, terrain: {revision: 1}, time_ms: time,
        cursor: String(cursor), recent_from_id: "1", motion: [], sources: [], colonies: [],
        ants: [{id: "8", stage: "Adult", position_m: position}], ...extra};
}
function x(now) { return motion.frame(now).ants[0].display_position_m[0]; }

const start = cut(0, 0, [0, 0, 0]);
const moved = {id: "1", actor: "8", time_ms: 80, position_m: [4, 0, 0],
    motion: {begins_ms: 20, translates_ms: 40, ends_ms: 80}};
const end = cut(100, 1, [4, 0, 0], {motion: [moved]});
motion.record(start, 0);
motion.record(end, 100);
assert.equal(x(265), 0, "Turning leaves the center unchanged");
assert.equal(x(290), 1, "Draw a segment completed entirely between two snapshots");
assert.equal(x(306), 2.6, "The pose advances without a new snapshot");
assert.equal(x(330), 4, "Hold the confirmed endpoint after the action");
assert.equal(motion.frame(2000).time, 100, "Never advance beyond the latest Core cut");
assert.deepEqual(start.ants[0].position_m, [0, 0, 0]);

motion.clear();
motion.record(start, 0);
motion.record({...end, recent_from_id: "2"}, 100);
assert.equal(x(290), 0, "A missing canonical range prevents reconstruction");
motion.record({...end, time_ms: 200, terrain: {revision: 2}}, 200);
assert.equal(x(291), 4, "A terrain edit invalidates previously displayed motion");
motion.record({...end, running: false}, 250);
assert.equal(motion.frame(310), null, "Pause shows the exact published state");

motion.record(start, 0);
motion.record(cut(115, 1, [0, 0, 0], {ants: [{...start.ants[0], motion_plan: {
    begins_ms: 60, translates_ms: 90, ends_ms: 190, from_m: [0, 0, 0], to_m: [10, 0, 0]
}}]}), 115);
assert.equal(x(350), 2, "An already started native motion can be drawn before arrival");
assert.equal(x(400), 2.5, "A slow connection holds the last validated time");
motion.record(cut(120, 2, [0, 0, 0]), 120);
assert.equal(x(355), 0, "An interrupted motion with no committed displacement is discarded");

console.log("PASS: live segment rendering, turns, delay, missing evidence, interruption and pause");
