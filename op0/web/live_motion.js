"use strict";

const LIVE_MOTION_DELAY_MS = 240;

// Browser-only projection of native cuts. A gap in evidence renders a stored pose.
class LiveMotion {
    constructor() { this.clear(); }

    clear() {
        this.cuts = [];
        this.moves = new Map();
    }

    record(data, arrival) {
        const last = this.cuts.at(-1);
        if (!data.seeded_nursery || !data.running || data.rate !== 1 || data.fast_forward?.state === "seeking") {
            this.clear();
            return;
        }
        if (!last || last.epoch !== data.epoch || last.revision !== data.terrain.revision ||
            data.time_ms < last.time || data.time_ms - last.time > 1000) {
            this.clear();
            this.anchorTime = data.time_ms;
            this.anchorWall = arrival;
        }
        const cut = {time: data.time_ms, cursor: BigInt(data.cursor), epoch: data.epoch, revision: data.terrain.revision,
            ants: data.ants, sources: data.sources, colonies: data.colonies};
        if (this.cuts.at(-1)?.time === cut.time) this.cuts.pop();
        this.cuts.push(cut);
        while (this.cuts.length > 2 && (this.cuts.length > 32 || cut.time - this.cuts[1].time > 1000)) this.cuts.shift();
        this.knownFrom = BigInt(data.recent_from_id);
        this.moves.clear();
        const floor = this.cuts[0].cursor;
        for (const event of data.motion) {
            if (BigInt(event.id) <= floor) continue;
            if (!this.moves.has(event.actor)) this.moves.set(event.actor, []);
            this.moves.get(event.actor).push({...event, cursor: BigInt(event.id)});
        }
        this.open = new Map(data.ants.filter(a => a.motion_plan).map(a => [a.id, a.motion_plan]));
    }

    frame(now) {
        if (!this.cuts.length) return null;
        const newest = this.cuts.at(-1);
        const time = Math.min(newest.time, Math.max(this.cuts[0].time,
            this.anchorTime + now - this.anchorWall - LIVE_MOTION_DELAY_MS));
        const base = this.cuts.findLast(c => c.time <= time);
        const complete = this.knownFrom <= base.cursor + 1n;
        const ants = base.ants.filter(a => a.stage !== "Dead").map(ant => {
            let position = ant.position_m, segment = null;
            if (complete) for (const move of this.moves.get(ant.id) || []) {
                if (move.cursor <= base.cursor) continue;
                if (move.time_ms <= time) { position = move.position_m; continue; }
                if (move.motion?.begins_ms <= time) {
                    segment = {...move.motion, from_m: position, to_m: move.position_m,
                        heading: ant.motion_plan?.begins_ms === move.motion.begins_ms ? ant.motion_plan.heading : 0};
                }
                break;
            }
            const open = this.open.get(ant.id);
            if (!segment && open && open.begins_ms <= time && time < open.ends_ms &&
                position.every((v, i) => v === open.from_m[i])) segment = open;
            if (!segment) return {...ant, display_position_m: position, display_motion: null};
            const progress = Math.max(0, Math.min(1, (time - segment.translates_ms) / (segment.ends_ms - segment.translates_ms)));
            return {...ant, display_position_m: segment.from_m.map((v, i) => v + progress * (segment.to_m[i] - v)),
                display_motion: {...segment, progress}};
        });
        return {time, ants, sources: base.sources, colonies: base.colonies};
    }
}
