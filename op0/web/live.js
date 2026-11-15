"use strict";

const liveView = {state: null, epoch: null, request: 0, timer: null, busy: false, saves: [], eventsKey: null, actionsKey: null, shownStop: null};
const liveMilestones = {egg: "First egg laid", hatch: "First hatch", worker: "First worker eclosed",
    exit: "First worker leaves the nest", delivery: "First food delivered", excavation: "First excavation"};
const followMilestones = new Set(["exit", "delivery", "excavation"]);
const liveActionColors = {"Ingest food": "#efd49a", Trophallaxis: "#b0e3cf", "Brood care": "#e1bdd9"};
const liveStopLabels = {
    seeking: "Fast-forwarding to {event}…",
    reached: "Reached {event} at {time}. Resume at 1×.",
    already: "{event} already happened at {time}.",
    exhausted: "The colony has no future activity that can reach {event}.",
    cancelled: "Fast-forward cancelled."
};

function duration(ms) {
    if (ms == null) return tr("Not recorded");
    return day(Math.floor(ms / DAY) * DAY) + " · " + clockTime(ms).slice(0, 8);
}

function liveControls() {
    const s = liveView.state;
    const active = s?.world_id != null;
    const stop = s?.fast_forward, seeking = stop?.state === "seeking";
    put("live-clock", active ? duration(s.time_ms) : "00:00:00");
    const label = active ? (s.running ? "Simulation running" : "Simulation paused") : "No active colony";
    const follow = active && app.follow && app.selected ? " · " + tr("Following ant #{id}", {id: app.selected}) : "";
    put("live-status", tr(label) + (s?.dirty ? " · " + tr("Unsaved progress") : "") + follow);
    put("live-pause", tr(seeking ? "Cancel fast-forward" : (s?.running ? "Pause" : "Resume")));
    $("live-rate").value = String(s?.rate || 1);
    $("colony-timing").disabled = $("nest-activity").disabled = $("new-colony").disabled = liveView.busy || !s?.core_available;
    const locked = liveView.busy || !active;
    $("live-pause").disabled = locked;
    $("live-rate").disabled = $("live-target").disabled = $("live-seek").disabled = locked || seeking;
    $("save-name").disabled = $("save-form").querySelector("button").disabled = locked;
    const details = stop ? tr(liveStopLabels[stop.state], {
        event: tr(liveMilestones[stop.target]), time: stop.event ? duration(stop.event.time_ms) : ""
    }) : "";
    if ($("live-stop").textContent !== details) put("live-stop", details);
    $("live-stop").hidden = !details;
    if (s?.error) show(tr(s.error), true);
}

function liveVisibility(active) {
    app.live = active;
    for (const id of ["archive-timeline", "archive-dashboard", "archive-picker", "compare-tab", "event-range"]) $(id).hidden = active;
    $("live-controls").hidden = $("live-event-note").hidden = !active;
    $("live-activity").hidden = !active;
    if (active) $("watch-delivery").hidden = true;
    put("view-source", tr(active ? "Live Core" : "Local archive"));
    put("footer-mode", tr(active ? "Live state published by the Simulation Core" : "Read-only replay of Simulation Core facts"));
    toggle("live-tab", active);
}

function liveIndividual() {
    const ant = liveView.state?.ants?.find(a => a.id === app.selected);
    if (!ant) { renderAnt(null); return; }
    const events = liveView.state.events.filter(e => e.actor === ant.id || e.related === ant.id);
    const death = events.find(e => e.kind === "AntDied" && e.actor === ant.id);
    renderAnt({...ant, status: ant.stage === "Dead" ? "Dead" : "Alive", died_ms: death?.time_ms,
        sample: ant.energy_nj == null ? null : {...ant, time_ms: ant.updated_ms}, activity: events});
}

function renderLiveEvents() {
    const key = liveView.state.events.map(e => e.id).join(",");
    if (liveView.eventsKey === key) return;
    liveView.eventsKey = key;
    $("event-list").replaceChildren(...liveView.state.events.map(e => eventButton(e, true)));
    if (!liveView.state.events.length) $("event-list").append(node("p", tr("No matching recent events."), "muted"));
    $("more-events").hidden = true;
}

function liveActionGroup(event) {
    if (event.kind === "NutritionTransferred") return "Trophallaxis";
    if (event.action || event.kind === "FoundingRation") return "Brood care";
    return "Ingest food";
}

function renderLiveActions() {
    const actions = liveView.state.actions ?? [];
    const key = language + ":" + actions.map(e => e.id).join(",");
    if (liveView.actionsKey === key) return;
    liveView.actionsKey = key;
    const groups = new Set();
    const latest = [];
    for (const event of actions) {
        const group = liveActionGroup(event);
        if (groups.has(group)) continue;
        groups.add(group);
        const entry = eventButton(event, true);
        entry.dataset.activity = group;
        latest.push(entry);
    }
    $("live-action-list").replaceChildren(...(latest.length ? latest : [node("p", tr("No in-place actions recorded yet."), "muted")]));
}

function drawLiveActions(ctx, point, fits) {
    const actions = liveView.state?.actions ?? [];
    const cells = new Set();
    ctx.save();
    ctx.font = '600 11px "Cascadia Mono", "Microsoft YaHei", monospace';
    for (const event of actions) {
        if (app.time - event.time_ms > 8000 || !fits(event.position_m)) continue;
        const [x, y] = point(event.position_m);
        const cell = `${Math.floor(x / 85)},${Math.floor(y / 25)}`;
        if (cells.has(cell)) continue;
        cells.add(cell);
        const group = liveActionGroup(event);
        const label = tr(group) + " #" + event.actor;
        const width = ctx.measureText(label).width + 12;
        circle(ctx, x, y, 9, "transparent", liveActionColors[group]);
        ctx.fillStyle = "#263327";
        ctx.fillRect(x + 10, y - 23, width, 19);
        ctx.fillStyle = liveActionColors[group];
        ctx.fillText(label, x + 16, y - 10);
    }
    ctx.restore();
}

function chooseLiveAnt(id) {
    const ant = liveView.state?.ants?.find(a => a.id === id);
    if (!ant) throw Error("This individual is not in the live colony.");
    app.selected = ant.id;
    $("ant-id").value = ant.id;
    if (ant.stage !== "Dead") preferView(ant.position_m);
    inspect(false);
    return refreshLive();
}

function showLiveFact(id) {
    const fact = liveView.state.events.find(e => e.id === id);
    if (!fact) throw Error("This event has left the recent list.");
    inspect(true);
    showEvent(fact);
}

async function refreshLive(alignSection = true) {
    if (!app.live) return;
    const request = ++liveView.request;
    const data = await api("live/view", {axis: $("axis").value, layer_q: app.layer,
        clearance: app.section === "slice" && $("clearance").checked ? 1 : null, group: $("filter").value});
    if (!app.live || request !== liveView.request) return;
    liveView.state = data;
    if (!data.world_id) {
        liveControls();
        $("viewer").hidden = true;
        put("subtitle", tr(data.core_available ? "Create a colony to start the simulation." : "Build the live Core to start a colony. Archive replay is available."));
        return;
    }
    app.meta = {settings: {geometry: data.geometry}, surface: data.surface, bounds_m: data.bounds_m,
        colonies: data.colonies, milestones: [], surface_entrances_m: []};
    if (liveView.epoch !== data.epoch) {
        liveView.epoch = data.epoch;
        liveView.eventsKey = null;
        liveView.actionsKey = null;
        liveView.shownStop = null;
        app.selected = data.ants.find(a => a.caste === "Queen")?.id ?? null;
        app.follow = false;
        app.location = app.selectedFact = null;
        app.map = {zoom: 1, x: 0, y: 0};
        app.layer = null;
        $("axis").value = "y";
        $("ant-id").value = app.selected || "";
        toggle("follow", false);
        $("action-replays").replaceChildren();
        $("action-replays").hidden = true;
        $("event-detail").hidden = true;
        setSection("slice");
        inspect(false);
    }
    app.time = data.time_ms;
    app.geometry = data.terrain;
    app.state = {ants: data.ants.filter(a => a.stage !== "Dead"), sources: data.sources};
    app.recentMotion = {points: data.motion.filter(event => event.time_ms >= data.time_ms - 5 * MINUTE)};
    const stop = data.fast_forward;
    const key = stop?.event ? `${stop.state}:${stop.event.id}` : null;
    if (key && liveView.shownStop !== key) {
        liveView.shownStop = key;
        if (stop.state === "reached" && followMilestones.has(stop.target)) {
            const worker = app.state.ants.find(a => a.id === stop.event.actor && a.caste === "Worker");
            if (worker) {
                app.selected = worker.id;
                app.follow = true;
                app.map.x = app.map.y = 0;
                $("ant-id").value = worker.id;
                toggle("follow", true);
            }
        }
        inspect(true);
        showEvent(stop.event);
    }
    const tracked = app.state.ants.find(a => a.id === app.selected);
    app.path = app.follow ? app.recentMotion.points.filter(e => e.kind === "Moved" && e.actor === app.selected) : [];
    if (app.follow && tracked) {
        preferView(tracked.position_m);
        if (alignSection && app.section === "slice" && app.geometry.slice?.plane_q !== app.layer) return refreshLive(false);
    }
    liveControls();
    const ants = app.state.ants;
    const p = {queens_alive: ants.filter(a => a.stage === "Adult" && a.caste === "Queen"),
        workers: ants.filter(a => a.stage === "Adult" && a.caste === "Worker").length,
        eggs: ants.filter(a => a.stage === "Egg").length, larvae: ants.filter(a => a.stage === "Larva").length,
        pupae: ants.filter(a => a.stage === "Pupa").length};
    const queen = p.queens_alive[0];
    updatePopulation(p, queen && {...queen, time_ms: queen.updated_ms});
    put("map-time", duration(data.time_ms));
    const timing = data.worker_activity_timing;
    const description = timing ? tr("Worker checks every {minutes} min · experimental", {minutes: timing.check_ms / MINUTE}) :
        tr("Standard worker timing");
    put("subtitle", tr("Live Core · Physics {physics} · Seed {seed}", data) + " · " + description + " · ENGINEERING_ONLY");
    updateGeometryControls(app.geometry);
    $("viewer").hidden = false;
    liveIndividual();
    renderLiveActions();
    if (!$("event-panel").hidden) renderLiveEvents();
    drawMap();
}

function scheduleLiveView() {
    clearTimeout(liveView.timer);
    if (!app.live) return;
    liveView.timer = setTimeout(async () => {
        try { if (!liveView.busy) await refreshLive(); }
        catch (error) { if (app.live) report(error); }
        finally { scheduleLiveView(); }
    }, liveView.state?.running ? 200 : 1000);
}

async function openLiveView() {
    ++app.openVersion;
    ++app.referenceVersion;
    ++app.compareVersion;
    ++app.seekVersion;
    ++app.activityVersion;
    ++app.eventListVersion;
    stopPlay();
    delete document.documentElement.dataset.ready;
    app.meta = app.state = app.geometry = null;
    app.path = [];
    app.layer = liveView.epoch = null;
    $("axis").value = "y";
    liveVisibility(true);
    setMode(false);
    $("viewer").hidden = true;
    put("title", "MicroWorld");
    show();
    await refreshLive();
    scheduleLiveView();
}

function leaveLiveView() {
    clearTimeout(liveView.timer);
    ++liveView.request;
    if ($("save-manager").open) $("save-manager").close();
    liveVisibility(false);
    app.state = app.meta = null;
    $("viewer").hidden = true;
}

async function liveCommand(resource, data = {}) {
    if (liveView.busy) return;
    liveView.busy = true;
    liveControls();
    try {
        const result = await fetch("/api/v1/live/" + resource, {method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)});
        const payload = await result.json();
        if (!result.ok || payload.schema !== "antworld.observation.v1") throw Error(payload.error || "The live Core command failed.");
        if (app.live) {
            show();
            if (resource === "new" || resource === "load") { $("axis").value = "y"; app.layer = null; }
            await refreshLive();
        }
        scheduleLiveView();
    } finally {
        liveView.busy = false;
        if (app.live) liveControls();
    }
}

function fileSize(bytes) {
    if (bytes < 1024) return decimal.format(bytes) + " B";
    if (bytes < 1024 ** 2) return decimal.format(bytes / 1024) + " KiB";
    if (bytes < 1024 ** 3) return decimal.format(bytes / 1024 ** 2) + " MiB";
    return decimal.format(bytes / 1024 ** 3) + " GiB";
}

function saveNotice(message = "") {
    put("save-notice", message);
    $("save-notice").hidden = !message;
}

async function refreshSaves() {
    const data = await api("live/saves");
    liveView.saves = data.entries;
    put("save-folder", data.folder);
    const list = $("saved-colonies");
    list.replaceChildren();
    for (const save of data.entries) {
        const row = node("tr");
        const date = new Date(save.modified_ms).toLocaleString(language);
        row.append(node("td", save.name), node("td", duration(save.time_ms)), node("td", fileSize(save.size_bytes)), node("td", date));
        const actions = node("td");
        const load = button("Load", async () => {
            if (liveView.state?.dirty && !confirm(tr("Load this save and replace the current unsaved progress?"))) return;
            load.disabled = true;
            try { await liveCommand("load", {name: save.name}); $("save-manager").close(); }
            catch (error) { saveNotice(tr(error.message)); load.disabled = false; }
        });
        load.disabled = !save.loadable || !liveView.state?.core_available;
        actions.append(load);
        row.append(actions);
        list.append(row);
    }
    if (!data.entries.length) {
        const row = node("tr"), cell = node("td", tr("No saved colonies yet."), "muted");
        cell.colSpan = 5;
        row.append(cell);
        list.append(row);
    }
}

function bindLive() {
    const click = (id, action) => $(id).addEventListener("click", () => Promise.resolve().then(action).catch(report));
    click("live-tab", openLiveView);
    click("new-colony", () => {
        if (liveView.state?.dirty && !confirm(tr("Create a colony and replace the current unsaved progress?"))) return;
        return liveCommand("new", {timing: $("colony-timing").value, local_nest_activity: $("nest-activity").checked});
    });
    click("live-pause", () => liveCommand("clock", {running: !liveView.state.running}));
    click("live-seek", () => {
        liveView.shownStop = null;
        return liveCommand("seek", {target: $("live-target").value});
    });
    $("live-rate").addEventListener("change", () => liveCommand("clock", {rate: Number($("live-rate").value)}).catch(report));
    click("open-saves", async () => {
        $("save-name").value = liveView.state?.saved_name || "";
        saveNotice();
        $("save-manager").showModal();
        try { await refreshSaves(); } catch (error) { saveNotice(tr(error.message)); }
    });
    click("close-saves", () => $("save-manager").close());
    click("refresh-saves", () => refreshSaves().catch(error => saveNotice(tr(error.message))));
    click("open-save-folder", () => liveCommand("folder").catch(error => saveNotice(tr(error.message))));
    $("save-form").addEventListener("submit", async event => {
        event.preventDefault();
        const name = $("save-name").value.trim();
        const overwrite = liveView.saves.some(save => save.name.toLowerCase() === name.toLowerCase());
        if (overwrite && !confirm(tr("Replace the existing save {name}?", {name}))) return;
        saveNotice(tr("Saving colony…"));
        try {
            await liveCommand("save", {name, overwrite});
            await refreshSaves();
            saveNotice(tr("Colony saved."));
        } catch (error) { saveNotice(tr(error.message)); }
    });
}
