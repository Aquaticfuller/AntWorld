"use strict";

const liveView = {state: null, epoch: null, request: 0, timer: null, animation: null, busy: false,
    saves: [], eventsKey: null, actionsKey: null, environmentKey: null, climateKey: null, individualKey: null, shownStop: null,
    groupTargets: []};
const liveMotion = new LiveMotion();
const liveMilestones = {egg: "First egg laid", hatch: "First hatch", worker: "First worker eclosed",
    "brood-moved": "First brood move", "brood-cleaned": "First brood cleaning",
    "queen-meal": "First queen meal from nest stores", "queen-uptake": "First queen carbohydrate uptake",
    "queen-gift": "First transfer from a worker to the queen",
    "wall-delivery": "First food delivery from a wall",
    exit: "First worker leaves the nest", delivery: "First food delivered", excavation: "First excavation",
    water: "First collection from the water source", recruitment: "First worker responds to recruitment",
    patrol: "First entrance patrol", "entrance-contact": "First entrance antennal contact"};
const liveEventNames = Object.fromEntries(Array.from(document.querySelectorAll("#live-target option"),
    option => [option.value, option.textContent]));
const followMilestones = new Set(["exit", "delivery", "excavation", "water", "recruitment", "patrol", "entrance-contact",
    "queen-meal", "queen-uptake", "queen-gift", "wall-delivery"]);
const liveActionColors = {"Ingest food": "#efd49a", Trophallaxis: "#b0e3cf", "Brood care": "#e1bdd9",
    "Entrance antennal contact": "#b9d6f5"};
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
    updatePresets();
    const s = liveView.state;
    const active = s?.world_id != null;
    document.body.classList.toggle("live-mode", app.live);
    document.body.classList.toggle("sealed-nest", Boolean(app.live && s?.habitat?.sealed_chamber));
    document.body.classList.toggle("anatomical-nest", Boolean(app.live && s?.habitat?.anatomical));
    document.body.classList.toggle("observatory-active", Boolean(app.live && s?.habitat && s.observatory_available));
    const stop = s?.fast_forward, seeking = stop?.state === "seeking";
    put("live-clock", active ? duration(s.time_ms) : "00:00:00");
    const label = active ? (s.running ? "Simulation running" : "Simulation paused") : "No active colony";
    const follow = active && app.follow && app.selected ? " · " + tr("Following ant #{id}", {id: app.selected}) : "";
    put("live-status", tr(label) + (s?.dirty ? " · " + tr("Unsaved progress") : "") +
        (s?.history_floor ? " · " + tr("Recent history only") : "") + follow);
    put("live-pause", tr(seeking ? "Cancel fast-forward" : (s?.running ? "Pause" : "Resume")));
    $("live-rate").value = String(s?.rate || 1);
    $("colony-timing").disabled = $("nest-activity").disabled = $("nest-dynamics").disabled =
        $("new-colony").disabled = liveView.busy || !s?.core_available;
    $("new-habitat").disabled = $("habitat-temperature").disabled = $("habitat-humidity").disabled =
        $("habitat-trails").disabled = $("habitat-plug").disabled = $("habitat-seed").disabled =
        liveView.busy || !s?.habitat_available;
    $("open-nursery").disabled = $("nursery-treatment").disabled = liveView.busy || !s?.nursery_available;
    $("new-single-nest").hidden = !s?.single_nest_available;
    $("new-single-nest").disabled = liveView.busy;
    $("new-single-nest").classList.toggle("primary-button", !active);
    put("find-brood", tr(s?.habitat?.sealed_chamber ? "Locate brood area" : "Locate brood chamber"));
    const preset = $("nursery-treatment");
    for (const option of preset.options) if (option.value.startsWith("ecology")) option.disabled = !s?.ecology_available;
    if (preset.selectedOptions[0]?.disabled) preset.value = "provisioned";
    put("open-nursery", tr(preset.value.startsWith("ecology") ? "Open local ecology" : "Watch the nursery"));
    const locked = liveView.busy || !active;
    $("live-pause").disabled = locked;
    $("live-milestone").hidden = Boolean(s?.seeded_nursery && !s.ecology);
    const target = $("live-target");
    for (const option of target.querySelectorAll("[data-habitat]")) option.hidden = option.disabled = !s?.habitat;
    for (const option of target.querySelectorAll("[data-brood]")) option.hidden = option.disabled = !s?.single_nest_available;
    for (const option of target.querySelectorAll("[data-founder]"))
        option.hidden = option.disabled = !(s?.habitat && s.founder_meals_available);
    for (const option of target.querySelectorAll("[data-offer]"))
        option.hidden = option.disabled = !(s?.habitat && s.queen_gifts_available);
    for (const option of target.querySelectorAll("[data-wall]"))
        option.hidden = option.disabled = !s?.habitat?.wall_handoff;
    if (target.selectedOptions[0]?.disabled) target.value = "egg";
    $("nursery-delivery").hidden = !active || !s.provisioned_nursery;
    $("live-seek-next").hidden = !s?.next_milestone_available;
    $("live-seek-group").hidden = !s?.group_milestones_available;
    $("nursery-next-delivery").hidden = $("nursery-delivery").hidden || $("live-seek-next").hidden;
    $("nursery-delivery").disabled = $("nursery-next-delivery").disabled = locked || seeking;
    $("live-rate").disabled = $("live-target").disabled = $("live-seek").disabled = $("live-seek-next").disabled = locked || seeking;
    $("live-seek-group").disabled = locked || seeking;
    $("live-seek").disabled ||= Boolean(s?.history_floor);
    $("save-name").disabled = $("save-form").querySelector("button").disabled = locked;
    const eventName = stop?.targets && !stop.target
        ? new Intl.ListFormat(language, {type: "disjunction"}).format(stop.targets.map(target => tr(liveEventNames[target])))
        : tr((stop?.occurrence === "next" ? liveEventNames : liveMilestones)[stop?.target]);
    let details = stop ? tr(liveStopLabels[stop.state], {
        event: eventName,
        time: stop.event ? duration(stop.event.time_ms) : ""
    }) : "";
    if (stop?.event && (stop.target === "queen-meal" || stop.target === "queen-uptake")) {
        const [carbs, protein, water] = stop.event.mass_ug;
        details += " · " + (stop.target === "queen-meal"
            ? tr("Into crop: {c} µg carbohydrate, {p} µg protein, {w} µg water", {c: carbs, p: protein, w: water})
            : tr("From crop: {c} µg carbohydrate absorbed", {c: carbs}));
    }
    if (stop?.event && stop.target === "queen-gift") {
        const e = stop.event;
        details += " · " + tr("Worker #{donor} to queen #{queen}: {c} µg carbohydrate, {p} µg protein, {w} µg water",
            {donor: e.actor, queen: e.recipient, c: e.mass_ug[0], p: e.mass_ug[1], w: e.mass_ug[2]});
    }
    if (stop?.event && stop.target === "wall-delivery") {
        const [c, p, w] = stop.event.mass_ug;
        details += " · " + tr("Into nest stores: {c} µg carbohydrate, {p} µg protein, {w} µg water", {c, p, w});
    }
    if ($("live-stop").textContent !== details) put("live-stop", details);
    $("live-stop").hidden = !details;
    if (s?.error) show(tr(s.error), true);
}

function liveVisibility(active) {
    app.live = active;
    document.body.classList.toggle("live-mode", active);
    if (!active) document.body.classList.remove("sealed-nest");
    if (!active) document.body.classList.remove("anatomical-nest");
    if (!active) document.body.classList.remove("nursery-active");
    if (!active) document.body.classList.remove("observatory-active");
    for (const id of ["archive-timeline", "archive-dashboard", "archive-picker", "compare-tab", "event-range"]) $(id).hidden = active;
    $("live-controls").hidden = $("live-event-note").hidden = !active;
    $("live-activity").hidden = !active;
    if (!active) $("live-chronicle").hidden = $("live-life").hidden = true;
    if (!active) {
        $("live-environment").hidden = $("find-pantry").hidden = $("find-brood").hidden =
            $("find-entrance").hidden = $("trail-control").hidden = true;
        put("worker-location", tr("Eclosed and alive"));
    }
    if (active) $("watch-delivery").hidden = true;
    put("view-source", tr(active ? "Live Core" : "Local archive"));
    put("footer-mode", tr(active ? "Live state published by the Simulation Core" : "Read-only replay of Simulation Core facts"));
    toggle("live-tab", active);
}

function liveIndividual() {
    const ant = liveView.state?.ants?.find(a => a.id === app.selected);
    const events = ant ? liveView.state.events.filter(e => e.actor === ant.id || e.related === ant.id || e.recipient === ant.id) : [];
    const key = JSON.stringify([language, ant, events.map(e => e.id)]);
    if (liveView.individualKey === key) return;
    liveView.individualKey = key;
    if (!ant) { renderAnt(null); return; }
    const death = events.find(e => e.kind === "AntDied" && e.actor === ant.id);
    renderAnt({...ant, status: ant.stage === "Dead" ? "Dead" : "Alive", died_ms: death?.time_ms,
        sample: ant.energy_nj == null ? null : {...ant, time_ms: ant.updated_ms}, activity: events});
}

function liveEnvironment(data) {
    $("live-environment").hidden = !(data.ecology || data.habitat);
    if ($("live-environment").hidden) return;
    const total = (items, field) => [0, 1, 2].map(i => items.reduce((n, row) => n + row[field][i], 0));
    const level = data.surface.origin_m[1];
    const chamber = data.sources.filter(s => s.position_m[1] < level);
    const stocks = [
        ["External stock", total(data.sources.filter(s => s.position_m[1] >= level), "stock_ug")],
        ["Nest stock", total(data.colonies, "stock_ug"), data.colonies[0].position_m],
        ...chamber.map(s => ["Water in the brood chamber", s.stock_ug, s.position_m]),
        ["Unreleased feeder reserve", data.feeder_reserve_ug?.slice(0, 3)]
    ];
    const key = JSON.stringify([language, stocks]);
    if (liveView.environmentKey !== key) {
        liveView.environmentKey = key;
        $("live-resources").replaceChildren(...stocks.map(([label, values, position]) => {
            const card = node("div");
            card.append(node("strong", tr(label)), keyValues([
                ...["Carbohydrates", "Protein", "Water"].map((name, i) => [name, withUnit(values?.[i], "µg")]),
                ...(position ? [["Location", coords(position)]] : [])
            ]));
            if (position) card.append(button("Locate on map", () => locateLiveSite(position).catch(report)));
            return card;
        }));
    }
    const climate = data.climate;
    $("live-climate").hidden = !climate;
    const climateKey = JSON.stringify([language, climate, data.worker_activity_timing?.check_ms, data.surface.trail_half_life_s]);
    if (climate && climateKey !== liveView.climateKey) {
        liveView.climateKey = climateKey;
        $("live-climate").replaceChildren(...[
            ["Temperature", withUnit(climate.temperature_c, "°C")],
            ["Relative humidity", withUnit(climate.humidity_percent, "%")],
            ["Larval development target", withUnit(climate.larva_ms / DAY, "days")],
            ["Larval water loss", withUnit(climate.larva_loss_ug_day, "µg/day")],
            ["Worker decision interval", withUnit(data.worker_activity_timing.check_ms / MINUTE, "min")],
            ["Surface trail half-life", withUnit(Math.round(data.surface.trail_half_life_s / 6) / 10, "min")]
        ].map(([name, value]) => {
            const card = node("div");
            card.append(node("span", tr(name), "metric-label"), node("strong", value));
            return card;
        }));
    }
}

async function locateLiveSite(position) {
    if (!position || !app.live) return;
    app.follow = false;
    app.selectedFact = null;
    app.location = null;
    toggle("follow", false);
    $("axis").value = "y";
    preferView(position);
    if (app.section === "nest") {
        app.layer = null;
        nestView.focus = position;
        nestView.x = nestView.y = 0;
        $("nest-depth").value = 0;
    }
    app.map = {zoom: 1, x: 0, y: 0};
    await refreshLive();
    $("space-title").scrollIntoView({block: "nearest"});
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
    if (event.action?.act === "Entrance antennal contact") return event.action.act;
    if (event.action || event.kind === "FoundingRation") return "Brood care";
    return "Ingest food";
}

function renderLiveActions() {
    const actions = (liveView.state.actions ?? []).filter(e => !liveView.state.seeded_nursery || liveView.state.time_ms - e.time_ms <= 8000);
    $("live-activity").hidden = liveView.state.seeded_nursery && !actions.length;
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

function drawLiveActions(ctx, point, fits, time) {
    const actions = liveView.state?.actions ?? [];
    const cells = new Set();
    ctx.save();
    ctx.font = '600 11px "Cascadia Mono", "Microsoft YaHei", monospace';
    for (const event of actions) {
        if (event.time_ms > time || time - event.time_ms > 8000 || !fits(event.position_m)) continue;
        const [x, y] = point(event.position_m);
        const cell = `${Math.floor(x / 85)},${Math.floor(y / 25)}`;
        if (cells.has(cell)) continue;
        cells.add(cell);
        const group = liveActionGroup(event);
        const label = tr(event.action?.act ?? group) + " #" + event.actor;
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

async function showLiveFact(id) {
    const epoch = liveView.epoch;
    const fact = await api("live/fact", {epoch, id});
    if (!app.live || epoch !== liveView.epoch) return;
    inspect(true);
    showEvent(fact);
    drawMap();
}

async function refreshLive(alignSection = true) {
    if (!app.live) return;
    const request = ++liveView.request;
    const data = await api("live/view", {axis: $("axis").value, layer_q: app.layer,
        trails: app.section === "surface" && $("show-trails").checked ? 1 : null,
        clearance: app.section === "slice" && $("clearance").checked ? 1 : null, group: $("filter").value});
    if (!app.live || request !== liveView.request) return;
    liveView.state = data;
    document.body.classList.toggle("nursery-active", Boolean(data.seeded_nursery));
    if (!data.world_id) {
        liveMotion.clear();
        liveControls();
        $("live-environment").hidden = true;
        $("viewer").hidden = true;
        put("subtitle", tr(data.core_available ? "Create a colony to start the simulation." : "Build the live Core to start a colony. Archive replay is available."));
        return;
    }
    app.meta = {world_id: data.world_id, settings: {geometry: data.geometry}, surface: data.surface, bounds_m: data.bounds_m,
        colonies: data.colonies, milestones: [], surface_entrances_m: []};
    if (liveView.epoch !== data.epoch) {
        $("colony-settings").open = !(data.seeded_nursery || data.habitat);
        liveView.epoch = data.epoch;
        liveView.eventsKey = null;
        liveView.actionsKey = null;
        liveView.individualKey = null;
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
        setSection(data.habitat && (data.habitat.sealed_chamber || liveView.nextNest || app.section === "nest") ? "nest" : "slice");
        inspect(false);
    }
    app.time = data.time_ms;
    const chamberTitle = data.terrain?.openings?.length ? "Founding nest with an open entrance" : "Sealed founding chamber";
    put("title", data.habitat?.sealed_chamber ? tr(chamberTitle) : data.habitat ? tr("Single-queen ecology") : data.ecology ? tr("Local ecology") :
        data.seeded_nursery ? tr("Nursery experiment") : "MicroWorld");
    app.geometry = data.terrain;
    app.state = {ants: data.ants.filter(a => a.stage !== "Dead"), sources: data.sources, trails: data.trails, soil_piles: data.soil_piles};
    app.recentMotion = {points: data.motion.filter(event => event.time_ms >= data.time_ms - 5 * MINUTE)};
    const stop = data.fast_forward;
    const key = stop?.event ? `${stop.state}:${stop.event.id}` : null;
    if (key && liveView.shownStop !== key) {
        liveView.shownStop = key;
        if (stop.state === "reached" && followMilestones.has(stop.target)) {
            const actor = app.state.ants.find(a => a.id === stop.event.actor);
            if (actor) {
                app.selected = actor.id;
                app.follow = true;
                app.map.x = app.map.y = 0;
                $("ant-id").value = actor.id;
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
    const outside = ants.filter(a => a.stage === "Adult" && a.caste === "Worker" &&
        a.position_m[1] >= data.surface.origin_m[1]).length;
    put("worker-location", tr("{count} on surface", {count: outside}));
    put("map-time", duration(data.time_ms));
    const timing = data.worker_activity_timing;
    const description = data.habitat ? tr(data.external_supply ? "Independent food and water sources" : "No external supply") :
        data.ecology ? tr(data.ecology === "water-fed" ? "Finite food and water" : "Finite food · no external water") :
        data.seeded_nursery ? tr(data.provisioned_nursery ? "Nursery · finite food supply" :
        data.local_traffic ? "Nursery · previous traffic model" : "Nursery · R0-r1 reference") :
        timing ? tr("Worker checks every {minutes} min · experimental", {minutes: timing.check_ms / MINUTE}) : tr("Standard worker timing");
    put("subtitle", tr("Live Core · Physics {physics} · Seed {seed}", data) + " · " + description + " · ENGINEERING_ONLY");
    updateGeometryControls(app.geometry);
    $("viewer").hidden = false;
    liveEnvironment(data);
    liveIndividual();
    renderLiveActions();
    if (!$("event-panel").hidden) renderLiveEvents();
    liveMotion.record(data, performance.now());
    drawMap();
    updateObservatory();
    if (liveMotion.cuts.length && liveView.animation == null) liveView.animation = requestAnimationFrame(animateLiveMotion);
}

function animateLiveMotion() {
    liveView.animation = null;
    if (!app.live || !liveMotion.cuts.length) return;
    drawMap(true);
    liveView.animation = requestAnimationFrame(animateLiveMotion);
}

function scheduleLiveView() {
    clearTimeout(liveView.timer);
    if (!app.live) return;
    liveView.timer = setTimeout(async () => {
        try { if (!liveView.busy) await refreshLive(); }
        catch (error) { if (app.live) report(error); }
        finally { scheduleLiveView(); }
    }, liveView.state?.running ? ((liveView.state.seeded_nursery || liveView.state.habitat) && liveView.state.rate === 1 ? 65 : 200) : 1000);
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
    cancelAnimationFrame(liveView.animation);
    liveView.animation = null;
    liveMotion.clear();
    ++liveView.request;
    if ($("save-manager").open) $("save-manager").close();
    liveVisibility(false);
    app.state = app.meta = null;
    $("viewer").hidden = true;
}

async function liveCommand(resource, data = {}) {
    if (liveView.busy) return;
    liveView.busy = true;
    liveView.nextNest = resource === "observatory" || resource === "single-nest";
    liveControls();
    try {
        await postLive(resource, data);
        if (app.live) {
            show();
            if (resource === "new" || resource === "load") { $("axis").value = "y"; app.layer = null; }
            await refreshLive();
        }
        scheduleLiveView();
    } finally {
        liveView.nextNest = false;
        liveView.busy = false;
        if (app.live) liveControls();
    }
}

function seekLiveEvent(target, occurrence) {
    liveView.shownStop = null;
    return liveCommand("seek", {target, occurrence});
}

function selectedLiveGroup() {
    return Array.from($("live-group-options").querySelectorAll("input:checked"), input => input.value);
}

function updateLiveGroupCount() {
    const count = selectedLiveGroup().length;
    put("live-group-count", tr("{count} selected", {count}));
    $("live-group-start").disabled = count === 0;
}

function openLiveGroup() {
    const available = Array.from($("live-target").options).filter(option => !option.disabled && !option.hidden);
    $("live-group-options").replaceChildren(...available.map(option => {
        const input = node("input");
        input.type = "checkbox";
        input.value = option.value;
        input.checked = liveView.groupTargets.includes(option.value);
        const label = node("label");
        label.append(input, tr(liveEventNames[option.value]));
        return label;
    }));
    updateLiveGroupCount();
    $("live-group-picker").showModal();
    ($("live-group-options").querySelector("input:checked") ?? $("live-group-options").querySelector("input"))?.focus();
}

async function postLive(resource, data) {
    const result = await fetch("/api/v1/live/" + resource, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)});
    const payload = await result.json();
    if (!result.ok || payload.schema !== "antworld.observation.v1") throw Error(payload.error || "The live Core command failed.");
    return payload.data;
}

async function replaySave(save) {
    const {archive} = await postLive("replay", {name: save.name});
    if (liveView.state?.running) await liveCommand("clock", {running: false});
    leaveLiveView();
    app.catalog = await api("catalog");
    setOptions($("archive"), app.catalog, archive);
    await openArchive(archive);
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
        row.append(node("td", save.name), node("td", tr(save.mode === "snapshot" ? "Compact save" : "Full replay archive")),
            node("td", duration(save.time_ms)), node("td", fileSize(save.size_bytes)), node("td", date));
        const actions = node("td");
        const load = button("Load", async () => {
            if (liveView.state?.dirty && !confirm(tr("Load this save and replace the current unsaved progress?"))) return;
            load.disabled = true;
            try { await liveCommand("load", {name: save.name, mode: save.mode}); $("save-manager").close(); }
            catch (error) { saveNotice(tr(error.message)); load.disabled = false; }
        });
        load.disabled = !save.loadable || !liveView.state?.core_available;
        const replay = button("Replay", () => replaySave(save).catch(error => saveNotice(tr(error.message))));
        replay.disabled = !save.loadable;
        actions.append(load);
        if (save.mode !== "snapshot") actions.append(replay);
        row.append(actions);
        list.append(row);
    }
    if (!data.entries.length) {
        const row = node("tr"), cell = node("td", tr("No saved colonies yet."), "muted");
        cell.colSpan = 6;
        row.append(cell);
        list.append(row);
    }
}

function bindLive() {
    bindObservatory();
    const click = (id, action) => $(id).addEventListener("click", () => Promise.resolve().then(action).catch(report));
    click("live-tab", openLiveView);
    click("new-single-nest", () => {
        if (!$("sealed-seed").reportValidity()) return;
        if (liveView.state?.dirty && !confirm(tr("Create a colony and replace the current unsaved progress?"))) return;
        return liveCommand("single-nest", {seed: $("sealed-seed").valueAsNumber,
            model: $("sealed-model").value, supply: $("sealed-supply").value});
    });
    click("new-colony", () => {
        if (liveView.state?.dirty && !confirm(tr("Create a colony and replace the current unsaved progress?"))) return;
        return liveCommand("new", {timing: $("colony-timing").value, local_nest_activity: $("nest-activity").checked,
            nest_dynamics: $("nest-dynamics").checked});
    });
    click("new-habitat", () => {
        if (!$('habitat-seed').reportValidity()) return;
        if (liveView.state?.dirty && !confirm(tr("Create a colony and replace the current unsaved progress?"))) return;
        return liveCommand("habitat", {temperature: Number($("habitat-temperature").value),
            humidity: Number($("habitat-humidity").value), trail_half_life: Number($("habitat-trails").value),
            soil_plug: $("habitat-plug").checked, seed: $("habitat-seed").valueAsNumber});
    });
    click("find-pantry", () => locateLiveSite(liveView.state?.colonies?.[0]?.position_m));
    click("find-brood", () => locateLiveSite(liveView.state?.habitat?.brood_site_m));
    click("find-entrance", () => locateLiveSite(liveView.state?.terrain?.openings?.[0]));
    $("show-trails").addEventListener("change", () => refreshLive().catch(report));
    click("open-nursery", () => {
        if (liveView.state?.dirty && !confirm(tr("Create a colony and replace the current unsaved progress?"))) return;
        return liveCommand("nursery", {treatment: $("nursery-treatment").value});
    });
    $("nursery-treatment").addEventListener("change", liveControls);
    click("live-pause", () => liveCommand("clock", {running: !liveView.state.running}));
    click("live-seek", () => seekLiveEvent($("live-target").value, "first"));
    click("live-seek-next", () => seekLiveEvent($("live-target").value, "next"));
    click("live-seek-group", openLiveGroup);
    $("live-group-options").addEventListener("change", updateLiveGroupCount);
    $("live-group-form").addEventListener("submit", event => {
        event.preventDefault();
        const targets = selectedLiveGroup();
        if (!targets.length) return;
        liveView.groupTargets = targets;
        liveView.shownStop = null;
        $("live-group-picker").close();
        liveCommand("seek", {targets}).catch(report);
    });
    click("nursery-delivery", () => seekLiveEvent("delivery", "first"));
    click("nursery-next-delivery", () => seekLiveEvent("delivery", "next"));
    $("live-rate").addEventListener("change", () => liveCommand("clock", {rate: Number($("live-rate").value)}).catch(report));
    click("open-saves", async () => {
        $("save-name").value = liveView.state?.saved_name || "";
        const modes = $("save-mode");
        modes.options[0].disabled = !liveView.state?.single_nest_available;
        modes.options[1].disabled = Boolean(liveView.state?.history_floor);
        modes.value = modes.options[0].disabled ? "archive" : "snapshot";
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
        const mode = $("save-mode").value;
        const overwrite = liveView.saves.some(save => save.mode === mode && save.name.toLowerCase() === name.toLowerCase());
        if (overwrite && !confirm(tr("Replace the existing save {name}?", {name}))) return;
        saveNotice(tr("Saving colony…"));
        try {
            await liveCommand("save", {name, overwrite, mode});
            await refreshSaves();
            saveNotice(tr("Colony saved."));
        } catch (error) { saveNotice(tr(error.message)); }
    });
}
