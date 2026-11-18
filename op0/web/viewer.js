"use strict";

const DAY = 86_400_000;
const HOUR = DAY / 24;
const MINUTE = HOUR / 60;
const $ = id => document.getElementById(id);
let language = "en", messages = {};
let decimal = new Intl.NumberFormat("en", {maximumFractionDigits: 3});
let languageChange = 0;
let chineseCatalog;
const colors = {worker: "#b7d98c", egg: "#f4e5b2", larva: "#eab17e", pupa: "#ccb1e5",
    queen: "#f2bf7d", food: "#83d4b7", entrance: "#bddba0", soil: "#a17c55", rock: "#899088",
    void: "#252f25", trace: "#baa6ef", Nurse: "#d5a7ce", Forage: "#86d6b4", Excavate: "#edb485", Rest: "#c5c8aa"};
const mapStages = [["queen", "Queens"], ["worker", "Workers"], ["egg", "Eggs"], ["larva", "Larvae"],
    ["pupa", "Pupae"], ["adult", "Other adults"]];
const columns = {births: "Eggs laid", collections: "Collections", deliveries: "Deliveries",
    trophallaxis: "Trophallaxis", excavations: "Excavations", soil_drops: "Soil placements",
    maternal_rations: "Maternal rations", signals: "Scout cues", exposures: "Local exposures", activations: "Recruitment activations"};
const names = {physics: "Physics version", inner_physics: "Inner physics", seed: "Software seed", geometry: "Initial 3D geometry",
    initial_maternal: "Maternal and brood inputs", initial_external_ug: "Scheduled external inputs (µg)",
    initial_sources: "Sources at initial checkpoint", ecological: "Ecological switches and parameters",
    care_enabled: "Care enabled", initial_workers: "Seeded workers", population: "Population", layout: "Layout", supply: "Supply"};
const app = {
    meta: null, series: [], state: null, geometry: null, catalog: [], time: 0, selectedFact: null, selected: null,
    path: [], recentMotion: null, follow: false, section: "surface", hits: [], visible: [], location: null,
    visibleSummary: null,
    map: {zoom: 1, x: 0, y: 0}, drag: null, activity: null, activityVersion: 0, playVersion: 0, playingDelivery: false,
    eventAfter: null, eventListVersion: 0, seekVersion: 0, openVersion: 0, playback: null,
    compare: false, reference: null, referenceSeries: [], compareVersion: 0, referenceVersion: 0, live: false
};

function tr(message, values = {}) {
    if (message == null) return messages["Not recorded"] || "Not recorded";
    if (typeof message !== "string") return message;
    const translated = Object.hasOwn(messages, message) ? messages[message] : message;
    return translated.replace(/\{(\w+)\}/g, (whole, key) => Object.hasOwn(values, key) ? values[key] : whole);
}
function preference() {
    try { return localStorage.getItem("antworld.op0.language") === "zh-CN" ? "zh-CN" : "en"; }
    catch { return "en"; }
}
const staticStrings = [];
function captureStaticStrings() {
    const selectors = "[data-i18n],button,option,small,.local-state span:nth-child(2),h2,#day-title,.panel-head p,.eyebrow,.metric-label,label,.world-select summary";
    const dynamic = new Set(["space-caption", "queen-mass", "play", "compare-play", "watch-delivery", "live-pause",
        "open-nursery", "view-source", "footer-mode"]);
    for (const e of document.querySelectorAll(selectors)) {
        if (!dynamic.has(e.id) && e.children.length === 0 && e.textContent.trim() && !e.closest("#locale")) {
            staticStrings.push([e, null, e.textContent.trim()]);
        }
    }
    for (const e of document.querySelectorAll("[aria-label],[placeholder]")) {
        for (const attribute of ["aria-label", "placeholder"]) {
            if (e.hasAttribute(attribute)) staticStrings.push([e, attribute, e.getAttribute(attribute)]);
        }
    }
}
async function setLanguage(next, refresh = true) {
    const version = ++languageChange;
    if (next === "zh-CN" && !chineseCatalog) {
        const response = await fetch("/locale/zh-CN.json");
        if (!response.ok) throw Error(tr("Language catalogue could not be loaded"));
        chineseCatalog = await response.json();
    }
    if (version !== languageChange) return;
    messages = next === "zh-CN" ? chineseCatalog : {};
    language = next;
    decimal = new Intl.NumberFormat(language, {maximumFractionDigits: 3});
    document.documentElement.lang = next;
    document.title = tr("AntWorld · Observation Preview");
    $("locale").value = next;
    try { localStorage.setItem("antworld.op0.language", next); } catch { /* The current tab still remembers the selection. */ }
    if (refresh) stopPlay();
    for (const [element, attribute, message] of staticStrings) {
        if (attribute) element.setAttribute(attribute, tr(message));
        else element.textContent = tr(message);
    }
    replaySettings();
    if (!refresh) return;
    if (app.live) {
        liveVisibility(true);
        liveView.eventsKey = null;
        await refreshLive();
        if (app.selectedFact && !$('event-detail').hidden) showEvent(app.selectedFact);
        if ($("save-manager").open) await refreshSaves();
        return;
    }
    liveVisibility(false);
    if (!app.catalog.length) {
        showEmptyCatalog();
        return;
    }
    if (!app.meta || !app.state) {
        show(tr("Verifying the archive and opening its history index…"));
        return;
    }
    const active = $("archive").value, prior = $("reference").value, saved = $("archived-world").value;
    setOptions($("archive"), app.catalog, active);
    for (const id of ["archived-world", "reference-world"]) {
        for (const option of $(id).options) option.textContent = tr(option.dataset.title);
    }
    $("archived-world").value = saved;
    configure(app.meta, prior);
    if (app.reference) $("compare-time").max = Math.max(app.meta.end_ms, app.reference.end_ms);
    await seek(app.time, app.selectedFact);
    if (!app.compare && !$("event-panel").hidden) {
        if (app.selectedFact) showEvent(app.selectedFact);
        await loadEvents(false);
    }
}

function node(tag, value, className) {
    const element = document.createElement(tag);
    if (value != null) element.textContent = value;
    if (className) element.className = className;
    return element;
}
function button(value, action, title) {
    const element = node("button", tr(value));
    element.type = "button";
    element.addEventListener("click", action);
    if (title) element.title = title;
    return element;
}
function put(id, value) { $(id).textContent = value; }
function toggle(id, pressed) {
    $(id).classList.toggle("active", pressed);
    $(id).setAttribute("aria-pressed", String(pressed));
}
function show(message, error = false) {
    const target = $("notice");
    target.hidden = !message;
    target.classList.toggle("error", error);
    target.textContent = message || "";
}
function report(err) { show(tr(err.message || String(err)), true); }
function day(ms) { return ms == null ? tr("Not recorded") : tr("Day {number}", {number: decimal.format(ms / DAY)}); }
function clockTime(ms) {
    const t = ms % DAY, hh = Math.floor(t / HOUR), mm = Math.floor(t % HOUR / MINUTE), ss = Math.floor(t % MINUTE / 1000);
    return [hh, mm, ss].map(n => String(n).padStart(2, "0")).join(":") + "." + String(t % 1000).padStart(3, "0");
}
function exactTime(ms) {
    return day(Math.floor(ms / DAY) * DAY) + " · " + clockTime(ms) + " · " + ms.toLocaleString(language) + " ms";
}
function withUnit(value, unit) { return value == null ? tr("Not recorded") : decimal.format(value) + " " + tr(unit); }
function mass(value) {
    return value ? "[" + value.map(v => v == null ? "?" : decimal.format(v)).join(" / ") + "] µg" : tr("Not recorded");
}
function coords(p) { return p ? "(" + p.map(v => decimal.format(v * 1000)).join(", ") + ") mm" : tr("Not recorded"); }
function truth(value) { return value == null ? tr("Not recorded") : typeof value === "object" ? JSON.stringify(value) : String(value); }
function keyValues(rows) {
    const dl = node("dl", null, "key-value");
    for (const [key, value] of rows) {
        const dd = node("dd");
        if (value instanceof Node) dd.append(value);
        else dd.textContent = value ?? tr("Not recorded");
        dl.append(node("dt", tr(key)), dd);
    }
    return dl;
}
async function api(path, options = {}) {
    const query = new URLSearchParams(Object.entries(options).filter(([, value]) => value != null));
    const result = await fetch("/api/v1/" + path + (query.size ? "?" + query : ""));
    const data = await result.json();
    if (data.schema !== "antworld.observation.v1") throw Error("Unsupported observation API");
    if (!result.ok) throw Error(data.error || "The archive query failed");
    return data.data;
}
function world(operation, options) { return api("world/" + app.meta.key + "/" + operation, options); }
function cut() { return app.selectedFact ? {event: app.selectedFact.id} : {time_ms: app.time}; }
function geometryOptions() {
    return {...cut(), axis: $("axis").value, layer_q: app.layer,
        clearance: app.section === "slice" && $("clearance").checked ? 1 : null};
}
function setOptions(select, entries, value) {
    select.replaceChildren(...entries.map(e => {
        const option = new Option(tr(e.title), e.key);
        option.dataset.title = e.title;
        return option;
    }));
    if (value) select.value = value;
}

function configure(meta, referenceKey = null) {
    $("watch-delivery").hidden = !firstDelivery(meta);
    playbackControls(Boolean(app.playback));
    put("title", tr(meta.title));
    put("subtitle", [meta.population, meta.layout, meta.supply].filter(Boolean).map(value => tr(value).replaceAll("_", " "))
        .concat(tr("Physics {version}", {version: meta.settings.physics}), tr("Seed {seed}", {seed: meta.settings.seed}), meta.readiness).join("  ·  "));
    const hashes = node("details");
    hashes.append(node("summary", tr("Member SHA-256")), node("pre", JSON.stringify(meta.member_sha256, null, 2)));
    const setup = node("details");
    setup.append(node("summary", tr("Effective experiment settings")), node("pre", JSON.stringify(meta.settings, null, 2)));
    const p = meta.final_population;
    $("identity-content").replaceChildren(node("p", tr(meta.description || "User-imported Core archive."), "muted"),
        keyValues([["World ID", meta.world_id], ["Scenario", meta.scenario || meta.name], ["Condition", meta.settings.condition],
            ["Valid time interval", day(meta.start_ms) + " – " + day(meta.end_ms)],
            ["Recorded end", tr(p.queens_alive.length ? "Queen alive" : "No live queen") + " · " + tr("{count} live workers", {count: p.workers})],
            ["Checkpoint / physics", meta.settings.checkpoint_schema + " / " + meta.settings.physics],
            ["Canonical facts", meta.facts.toLocaleString(language)], ["Integrity", meta.integrity], ["Archive SHA-256", meta.archive_sha256],
            ["Producer commit", meta.producer?.source], ["Producer binary SHA-256", meta.producer?.binary_sha256],
            ["Archive type", meta.archive_kind], ["Scope", meta.readiness + " · B06 " + meta.b06 + " · " + tr("Release") + " " + meta.release],
            ["Biological validation", meta.biological_status]]), setup, hashes);
    for (const id of ["time", "compare-time"]) $(id).max = meta.end_ms;
    $("days").replaceChildren(...[0, 1, 20, 45, 90, 120, 150].filter(d => d * DAY <= meta.end_ms)
        .map(d => button(language === "en" ? "D" + d : tr("Day {number}", {number: d}),
            () => { stopPlay(); return seek(d * DAY).catch(report); }, tr("Jump to day {number}", {number: d}))));
    const labels = {"First egg laid": "First eggs", "First hatch": "Hatch", "First worker eclosed": "First worker", "First food collection": "First collection",
        "First food delivered": "First delivery",
        "First excavation": "First excavation", "First recruitment activation": "Recruitment", "First larval death": "Larval death",
        "First brood arrangement": "Brood arranged", "First timed feeding": "Brood fed", "First trophallaxis": "Trophallaxis",
        "First soil placement": "Soil placed", "Queen died": "Queen death"};
    $("milestones").replaceChildren(...meta.milestones.filter(m => labels[m.label]).map(m =>
        button(labels[m.label], () => jumpEvent(m.id, m.ant).catch(report), tr(m.label) + " · " + exactTime(m.time_ms))));
    const replays = {"First egg laid": "Watch egg placement", "First brood arrangement": "Watch brood arrangement",
        "First timed feeding": "Watch brood feeding", "First move to a resting site": "Watch a worker settle",
        "Resting site with 10 or more workers": "Watch movement in an established nest"};
    const available = meta.milestones.filter(m => replays[m.label]);
    $("action-replays").hidden = !available.length;
    $("action-replays").replaceChildren(...available.map(m => button(replays[m.label], () => watchAction(m).catch(report))));
    setOptions($("reference"), app.catalog.filter(e => e.key !== $("archive").value));
    const referenceTitle = meta.title.startsWith("R0-r1 · ") ?
        (meta.title.includes(" · motor") ? meta.title.replace(" · motor", " · reference") :
         meta.title.includes(" · reference") ? meta.title.replace(" · reference", " · motor") :
         meta.title.includes(" · dig score") ? meta.title.replace(" · dig score", " · random boundary") :
         meta.title.replace(" · random boundary", " · dig score")) :
        meta.title.startsWith("R0 · ") ? (meta.settings.physics === 32 ?
        meta.title.replace("local nest activity", "matched reference") : meta.title.replace("matched reference", "local nest activity")) :
        meta.scenario?.startsWith("micro-m0-") ? "MicroWorld · reference placement" : "Before the feeding correction";
    const prior = app.catalog.find(e => e.title === referenceTitle && e.key !== $("archive").value);
    if (referenceKey || prior) $("reference").value = referenceKey || prior.key;
}

async function openArchive(key, preferred) {
    const version = ++app.openVersion;
    ++app.referenceVersion;
    ++app.compareVersion;
    ++app.seekVersion;
    ++app.eventListVersion;
    delete document.documentElement.dataset.ready;
    stopPlay();
    show(tr("Verifying the archive and opening its history index…"));
    const result = await api("archive/" + key);
    if (version !== app.openVersion) return;
    const entry = result.worlds.find(w => w.key === preferred) || result.worlds[0];
    setOptions($("archived-world"), result.worlds, entry.key);
    $("archived-world").hidden = result.worlds.length < 2;
    const [meta, series] = await Promise.all([api("world/" + entry.key + "/meta"), api("world/" + entry.key + "/series")]);
    if (version !== app.openVersion) return;
    app.meta = meta;
    app.series = series;
    app.time = 0;
    app.selectedFact = null;
    app.selected = meta.initial_queens[0] || meta.milestones.find(m => m.label === "Queen died")?.ant || null;
    app.follow = false;
    app.reference = null;
    app.path = [];
    app.recentMotion = null;
    app.activity = null;
    ++app.activityVersion;
    app.location = null;
    app.visibleSummary = null;
    $("show-largest").hidden = true;
    $("hour-bins").replaceChildren();
    app.state = null;
    app.geometry = null;
    app.layer = null;
    app.map = {zoom: 1, x: 0, y: 0};
    $("replay-mode").value = meta.scenario?.startsWith("micro-m0-") ? "scenes" : "overview";
    setSection(meta.settings.geometry && meta.settings.physics >= 36 ? "nest" :
        meta.settings.geometry && (meta.initial_queens.length || meta.scenario?.startsWith("r0r1-dig")) ? "slice" : "surface");
    $("axis").value = /^(micro-m0-|r0r1-)/.test(meta.scenario || "") ? "y" : "z";
    if (app.section === "slice" && $("axis").value === "y" && meta.colonies.length) preferView(meta.colonies[0].position_m);
    $("ant-id").value = app.selected || "";
    toggle("follow", false);
    configure(meta);
    setMode(false);
    inspect(false);
    await seek(0);
    if (version === app.openVersion) {
        show();
        document.documentElement.dataset.ready = "true";
        performance.mark("op0-world-ready");
    }
}

function setMode(compare) {
    app.compare = compare;
    $("viewer").hidden = compare;
    $("comparison").hidden = !compare;
    toggle("compare-tab", compare);
    toggle("observe-tab", !compare && !app.live);
    replaySettings();
    if (!compare) requestAnimationFrame(draw);
}

async function seek(ms, exact = null) {
    if (app.live) return refreshLive();
    if (!app.meta) return;
    const version = ++app.seekVersion;
    const previous = app.time;
    const end = app.compare && app.reference ? Math.max(app.meta.end_ms, app.reference.end_ms) : app.meta.end_ms;
    app.time = Math.max(0, Math.min(end, Math.round(ms)));
    app.selectedFact = exact;
    if ($("event-detail").dataset.event !== exact?.id) $("event-detail").hidden = true;
    $("time").value = app.time;
    $("compare-time").value = app.time;
    updateClock();
    if (app.compare && app.reference) {
        await updateComparison();
        return;
    }
    const [state, initialGeometry, ant, track, motion] = await Promise.all([
        world("state", cut()),
        world("geometry", geometryOptions()),
        app.selected ? world("ant", {...cut(), id: app.selected}) : null,
        app.selected ? world("path", {...cut(), id: app.selected, limit: 120}) : null,
        world("motion", {...cut(), window_ms: 5 * MINUTE, limit: 144})
    ]);
    if (version !== app.seekVersion) return;
    let geometry = initialGeometry;
    if (app.follow && !exact && ant?.status === "Alive") {
        preferView(ant.position_m);
        if (app.section === "slice" && (geometry.slice?.plane_q !== app.layer ||
            ($("clearance").checked && !geometry.slice?.unloaded_body_clear))) {
            geometry = await world("geometry", geometryOptions());
            if (version !== app.seekVersion) return;
        }
    }
    app.state = state;
    app.geometry = geometry;
    app.path = track ? track.points : [];
    app.recentMotion = motion;
    updateGeometryControls(geometry);
    updateState(state);
    renderAnt(ant);
    draw();
    await loadActivity();
    if (version !== app.seekVersion) return;
    const eventWindow = $("event-range").value === "hour" ? HOUR : DAY;
    if (!$("event-panel").hidden && (($("event-range").value !== "all" &&
        Math.floor(previous / eventWindow) !== Math.floor(app.time / eventWindow)) || !$("event-list").childElementCount)) {
        await loadEvents(false);
    }
}

function updateClock() {
    const grain = app.selectedFact ? tr("Event #{id} cut", {id: app.selectedFact.id}) : tr("Committed through this time");
    put("time-note", exactTime(app.time) + " · " + grain + (app.selectedFact ? " · " + eventLabel(app.selectedFact) : ""));
    put("map-time", day(Math.floor(app.time / DAY) * DAY) + " · " + clockTime(app.time) +
        (app.selectedFact ? " · " + eventLabel(app.selectedFact) : ""));
    put("compare-stamp", day(app.time));
    const partial = Math.floor(app.time / DAY) * DAY;
    const until = Math.min(DAY - 1, app.meta.end_ms - partial);
    $("day-time").max = Math.max(0, until);
    $("day-time").value = app.time - partial;
    $("day-time").disabled = until <= 0;
    $("day-time").setAttribute("aria-valuetext", clockTime(app.time));
    put("day-time-value", clockTime(app.time));
    if (app.activity?.day === Math.floor(app.time / DAY)) markHour();
}

function markHour() {
    const hour = Math.floor(app.time % DAY / HOUR);
    for (const [index, bin] of Array.from($("hour-bins").children).entries()) {
        bin.setAttribute("aria-pressed", String(index === hour));
    }
}
function renderActivity(activity) {
    const t = activity.totals;
    put("day-counts", tr("{facts} committed records · {moves} movements · {collections} collections · {deliveries} deliveries",
        Object.fromEntries(Object.entries(t).map(([key, value]) => [key, decimal.format(value)]))));
    put("hour-note", tr("Bright cells mark recorded movement. Readings cover the selected day, including events after the cursor."));
    const bins = activity.hours.map((hour, i) => {
        const stamp = activity.start_ms + i * HOUR;
        const tip = tr("{clock} · {facts} records · {moves} movements", {clock: clockTime(stamp).slice(0, 5), ...hour});
        const bin = button("", () => { stopPlay(); return seek(stamp).catch(report); }, tip);
        bin.setAttribute("aria-label", tip);
        bin.className = hour.moves ? "moved" : hour.facts ? "recorded" : "";
        bin.disabled = stamp > activity.end_ms;
        return bin;
    });
    $("hour-bins").replaceChildren(...bins);
    markHour();
}
async function loadActivity() {
    const at = Math.floor(app.time / DAY);
    if (app.activity?.day === at) {
        if (app.activityLanguage !== language || !$("hour-bins").childElementCount) {
            app.activityLanguage = language;
            renderActivity(app.activity);
        }
        return;
    }
    const version = ++app.activityVersion;
    put("day-counts", tr("Reading recorded activity…"));
    $("hour-bins").replaceChildren();
    const result = await world("activity", {day: at});
    if (version !== app.activityVersion || Math.floor(app.time / DAY) !== at) return;
    app.activity = result;
    app.activityLanguage = language;
    renderActivity(result);
}

function updatePopulation(p, s) {
    put("queen-state", tr(p.queens_alive.length ? "Alive" : "Absent"));
    put("queen-mass", s ? tr("{water} · sampled on {day}", {water: withUnit(s.hydration_ug, "µg water"), day: day(s.time_ms)}) :
        tr(p.queens_alive.length ? "Physiology unavailable at this cut" : "No live queen at this cut"));
    for (const name of ["workers", "eggs", "larvae", "pupae"]) put(name, p[name].toLocaleString(language));
}

function updateState(state) {
    updatePopulation(state.population, state.queens_last_sample);
    const totals = state.cumulative;
    const net = withUnit(state.net_removed_m3 == null ? null : state.net_removed_m3 * 1e9, "mm³");
    const rows = [["External stock", mass(state.external_ug)], ["Nest stock", mass(state.nest_ug)],
        ["Collections / deliveries", (totals.collections || 0) + " / " + (totals.deliveries || 0)],
        ["Trophallaxis / rations", (totals.trophallaxis || 0) + " / " + (totals.maternal_rations || 0)],
        ["Recorded deaths", String(Object.values(state.deaths).reduce((a, b) => a + b, 0))],
        ["Net soil removed", net], ["Scout cues / exposures", (totals.signals || 0) + " / " + (totals.exposures || 0)],
        ["Recruitment activations", String(totals.activations || 0)]];
    $("ledger").replaceChildren(...rows.map(([label, value]) => {
        const tile = node("div");
        tile.append(node("small", tr(label), "muted"), node("strong", value));
        return tile;
    }));
}

function eventLabel(e) {
    const labels = {AntSeeded: "Placed at initialization", AntBorn: "Egg laid", AntDied: "Death",
        FoodCollected: "Food collected", FoodDelivered: "Food delivered", NutritionTransferred: "Trophallaxis",
        CargoIngested: "Ingest food", NestIngested: "Ingest food", FoundressWaterIngested: "Drink water",
        FoundingRation: "Maternal ration", SoilExcavated: "Soil excavated", SoilDropped: "Soil placed",
        RecruitmentObserved: "Scout cue sensed", RecruitmentActivated: "Recruitment activated"};
    if (e.kind === "StageChanged") return tr({Larva: "Hatched", Pupa: "Pupated", Adult: "Eclosed"}[e.stage] || e.stage);
    if (e.action) return tr(e.action.act) + " · " + tr(e.action.phase);
    return tr(labels[e.kind] || (Object.hasOwn(messages, e.kind) ? e.kind : e.kind.replace(/([a-z])([A-Z])/g, "$1 $2")));
}
function eventButton(e, extra = false) {
    const b = button("", () => {
        if (app.live) showLiveFact(e.id).catch(report);
        else jumpEvent(e.id).catch(report);
    });
    b.className = "event-row";
    b.dataset.event = e.id;
    b.append(node("span", eventLabel(e)), node("span", app.live ? duration(e.time_ms) : day(e.time_ms)));
    if (extra) b.append(node("small", "#" + e.id + (e.actor ? " · " + tr("Ant #{id}", {id: e.actor}) : "") +
        (e.related ? " → #" + e.related : "") + (e.death_cause ? " · " + tr(e.death_cause) : "")));
    return b;
}
function renderAnt(ant) {
    const panel = $("individual-content");
    if (!ant) {
        panel.replaceChildren(node("p", tr("Select an individual on the map or enter its ID."), "muted"));
        return;
    }
    const title = node("div", null, "animal-head");
    const headline = node("div");
    headline.append(node("h3", tr(ant.stage === "Adult" ? ant.caste : ant.stage) + " #" + ant.id),
        node("small", ant.program === "Not recorded" ? tr("Task state not recorded") : tr("Program · {name}", {name: tr(ant.program)})));
    title.append(headline, node("span", tr(ant.status), "pill" + (ant.status === "Dead" ? " dead" : "")));
    const mother = ant.mother ? button("#" + ant.mother, () => selectAnt(ant.mother).catch(report)) : null;
    const s = ant.sample;
    const plan = showLiveMotor() ? ant.motion_plan : null;
    const work = showLiveMotor() && ant.active_work != null && ant.status === "Alive";
    panel.replaceChildren(title, keyValues([["Mother", mother], ["Born", ant.born_ms == null ? null : day(ant.born_ms)],
        ["Last position at cut", coords(ant.position_m)], ...(plan ? [["Current motion", tr(app.time < plan.translates_ms ? "Turning" : "Moving")],
            ["Position on motion segment", coords(motorPose(ant))], ["Destination", coords(plan.to_m)]] : []),
        ...(work && !plan ? [["Current action", tr(ant.active_work === "0" ? "No action in progress" : "Action in progress")]] : []),
        ...(ant.died_ms == null ? [] : [["Died", exactTime(ant.died_ms)], ["Cause", tr(ant.death_cause)]])]),
        node("h4", s ? tr("Physiology · sample on {day}", {day: day(s.time_ms)}) : tr("Physiology · not recorded"), "subhead"));
    if (s) panel.append(keyValues([["Body energy", withUnit(s.energy_nj, "nJ")], ["Body water", withUnit(s.hydration_ug, "µg")],
        ["Tissue protein", withUnit(s.tissue_protein_ug, "µg")], ["Crop C/P/W/other", mass(s.crop_ug)],
        ["Carried C/P/W/other", mass(s.carried_ug)]]));
    if (app.live) {
        if (s) panel.append(keyValues([
            ["Physiology last updated", exactTime(s.updated_ms)],
            ["Next scheduled absorption", ant.status === "Alive" && s.next_absorption_ms > app.time ? exactTime(s.next_absorption_ms) : null],
            ["Recorded water loss", withUnit(s.lost_water_ug, "µg")],
            ["Energy dissipated", withUnit(s.dissipated_nj, "nJ")]
        ]));
        if (ant.activity.length) panel.append(node("h4", tr("Recent Core events"), "subhead"), ...ant.activity.map(e => eventButton(e)));
        return;
    }
    if (ant.status !== "Not yet present") {
        const detail = node("details", null, "individual-window");
        const detailBody = node("div");
        const actions = node("div", null, "location-list");
        for (const [days,label] of [[1,"Selected day"],[3,"Three-day window"]])
            actions.append(button(label, () => showIndividualWindow(ant, days, detailBody).catch(report)));
        detail.append(node("summary",tr("Individual time budget and physiology")),actions,detailBody);
        panel.append(detail);
    }
    panel.append(node("h4", tr("Lifetime · includes later recorded events"), "subhead"),
        ...ant.life_events.map(e => eventButton(e)), node("h4", tr("Recent facts through cursor"), "subhead"),
        ...ant.activity.slice(0, 12).map(e => eventButton(e, true)));
    if (!ant.activity.length) panel.append(node("p", tr("No matching actions by this time."), "muted"));
}
async function showIndividualWindow(ant, days, panel) {
    const observed = ant.died_ms == null ? ant.time_ms : Math.min(ant.time_ms, ant.died_ms);
    const begin = Math.floor(observed / DAY) * DAY;
    const data = await world("individual-window", {id: ant.id, begin_ms: begin, end_ms: Math.min(app.meta.end_ms,begin+days*DAY)});
    if (!panel.isConnected) return;
    const interval = ms => withUnit(ms/1000,"s");
    panel.replaceChildren(node("p",tr("Window starts on {day}. Task time and paid work are separate measurements.",{day:day(begin)}),"muted"),
        keyValues([["Alive in window", interval(data.elapsed_alive_ms)],
            ["Paid work",data.work_clock_recorded ? interval(data.paid_work_ms) : null],
            ["Committed movement",withUnit(data.completed_distance_m*1000,"mm")],
            ["Timed part of movement",interval(data.timed_move_ms)],["Moves without a time interval",data.untimed_moves],
            ["Nutrition received",mass(data.nutrition_in_ug)],["Nutrition sent",mass(data.nutrition_out_ug)],
            ...Object.entries(data.programs_ms).filter(([,value]) => value).map(([program,value]) => [program,interval(value)]),
            ...Object.entries(data.event_counts)]));
    for (const [field,label,unit,color] of [["energy_nj","Body energy","nJ","queen"],["hydration_ug","Body water","µg","food"]]) {
        const points = data.physiology_samples.filter(p => p[field] != null);
        if (!points.length) continue;
        const chart = node("canvas",null,"physiology-mini");
        chart.id = "ant-"+field;
        chart.setAttribute("aria-label",tr(label));
        panel.append(node("h4",tr(label)+" ("+unit+")"),chart,
            node("p",points.map(p => day(p.time_ms)+" · "+withUnit(p[field],unit)).join(" / "),"muted"));
        graph(chart.id,[{values:points.map(p => [p.time_ms-begin,p[field]]),color:colors[color]}],data.end_ms-begin,
            Math.max(0,Math.min(data.end_ms,ant.time_ms)-begin),null,begin);
    }
}
function inspect(events) {
    $("individual-panel").hidden = events;
    $("event-panel").hidden = !events;
    toggle("events-tab", events);
    toggle("individual-tab", !events);
}
async function selectAnt(id) {
    if (app.live) return chooseLiveAnt(id);
    stopPlay();
    const version = app.openVersion;
    const p = await world("ant", {...cut(), id});
    if (version !== app.openVersion) return;
    app.selected = p.id;
    $("ant-id").value = p.id;
    if (p.position_m) preferView(p.position_m);
    inspect(false);
    await seek(app.time, app.selectedFact);
}
function showEvent(e) {
    if (app.live) app.selectedFact = e;
    const container = $("event-detail");
    const editList = [];
    for (const edit of e.geometry_edits || []) {
        const target = app.meta.settings.geometry;
        const actor = button(tr("Ant #{id}", {id: edit.actor}), () => selectAnt(edit.actor).catch(report));
        editList.push(["Excavator / filler", actor], ["Quantized box", edit.box_q.join(", ")],
            ["Material edited", withUnit(edit.volume_q3 * target.quantum_m ** 3 * 1e9, "mm³")]);
    }
    const antLink = id => id ? button(tr("Ant #{id}", {id}), () => selectAnt(id).catch(report)) : null;
    container.replaceChildren(node("h3", eventLabel(e)), keyValues([["Fact ID", "#" + e.id], ["Canonical event name", e.kind],
        ["Simulation time", exactTime(e.time_ms)], [e.kind === "BroodMoved" ? "Brood" : "Actor", antLink(e.actor)],
        [e.kind === "BroodMoved" ? "Handler" : "Participant", antLink(e.related)],
        ["Resource / parcel", [e.resource, e.parcel].filter(Boolean).map(s => "#" + s).join(" / ") || null],
        ["Outcome", tr(e.outcome)], ["Recorded position", coords(e.position_m)], ["Transferred C/P/W/other", mass(e.mass_ug)],
        ...(e.origin_fact ? [["Preceding committed fact", button("#" + e.origin_fact, () => jumpEvent(e.origin_fact).catch(report))]] : []),
        ...(e.death_cause ? [["Death cause", tr(e.death_cause)]] : []),
        ...(e.mode ? [["Foraging mode", tr(e.mode)], ["Decision label", tr(e.reason)]] : []),
        ...(e.trail_deposited_units ? [["Deposited trail units", decimal.format(e.trail_deposited_units)]] : []), ...editList]));
    container.hidden = false;
    container.dataset.event = e.id;
}
async function jumpEvent(id, ant = null) {
    if (app.live) return showLiveFact(id);
    stopPlay();
    const version = app.openVersion;
    const e = await world("event", {id});
    if (version !== app.openVersion) return;
    if (ant) {
        app.selected = ant;
        $("ant-id").value = ant;
    }
    if (app.section !== "nest" && ["SoilExcavated", "SoilFilled"].includes(e.kind) && e.geometry_edits?.length) {
        setSection("slice");
        const edit = e.geometry_edits.at(-1);
        const axis = {x: 0, y: 1, z: 2}[$("axis").value];
        const solid = app.meta.settings.geometry.solid;
        app.layer = Math.max(solid[axis], Math.min(solid[axis + 3] - 1, Math.floor((edit.box_q[axis] + edit.box_q[axis + 3]) / 2)));
    } else if (ant && e.actor && e.stage) preferView(e.position_m);
    inspect(true);
    await seek(e.time_ms, e);
    if (app.selectedFact !== e) return;
    showEvent(e);
    await loadEvents(false);
}
async function loadEvents(more) {
    if (app.live) return refreshLive();
    if (!app.meta || app.compare) return;
    const request = ++app.eventListVersion;
    const low = Math.floor(app.time / DAY) * DAY;
    const from = $("event-range").value;
    const hour = Math.floor(app.time / HOUR) * HOUR;
    const range = from === "all" ? {} : from === "hour" ? {since_ms: hour, until_ms: Math.min(hour + HOUR - 1, app.meta.end_ms)} :
        {since_ms: low, until_ms: Math.min(low + DAY - 1, app.meta.end_ms)};
    const data = await world("events", {...range, after: more ? app.eventAfter : 0, group: $("filter").value, limit: 16,
        ...(app.follow && app.selected ? {ant: app.selected} : {})});
    if (request !== app.eventListVersion) return;
    app.eventAfter = data.next_after;
    const list = $("event-list");
    list.replaceChildren(...data.events.map(e => eventButton(e, true)));
    if (!data.events.length) list.append(node("p", tr("No matching facts in this window."), "muted"));
    $("more-events").hidden = !app.eventAfter;
}

function setSection(section) {
    const changed = app.section !== section;
    app.section = section;
    if (changed) {
        app.map = {zoom: 1, x: 0, y: 0};
        app.location = null;
    }
    toggle("surface-button", section === "surface");
    toggle("slice-button", section === "slice");
    toggle("nest-button", section === "nest");
    $("nest-button").disabled = !app.meta?.settings.geometry;
    $("nest-controls").hidden = section !== "nest";
    $("plane-controls").hidden = section !== "slice" || !app.meta?.settings.geometry;
    $("clearance-control").hidden = $("plane-controls").hidden;
    $("view-controls").hidden = section !== "surface";
}
function preferView(p) {
    if (!p || !app.meta || app.section === "nest") return;
    const terrain = app.meta.settings.geometry;
    const surfaceY = planeSurface();
    if (terrain && p[1] < surfaceY - 1e-10) {
        const n = {x: 0, y: 1, z: 2}[$("axis").value];
        const q = Math.floor((p[n] - terrain.origin_m[n]) / terrain.quantum_m + 1e-9);
        app.layer = Math.max(terrain.solid[n], Math.min(terrain.solid[n + 3] - 1, q));
        setSection("slice");
    } else setSection("surface");
}
function planeSurface() {
    const terrain = app.meta?.settings.geometry;
    return app.meta?.surface?.origin_m[1] ?? (terrain ? terrain.origin_m[1] + terrain.quantum_m * terrain.solid[4] : 0);
}
function updateGeometryControls(g) {
    const slice = g.slice;
    $("slice-button").disabled = !slice;
    if (!slice) return;
    const n = slice.axes[2], s = g.geometry_bounds_q;
    $("layer").min = s[n];
    $("layer").max = s[n + 3] - 1;
    $("layer").value = slice.plane_q;
    put("layer-value", withUnit((slice.origin_m[n] + slice.plane_q * slice.quantum_m) * 1000, "mm"));
}

function canvasContext(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (width <= 0 || height <= 0) return null;
    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
    }
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    return {ctx, width, height};
}
function projection(width, height, bounds, focus = null, view = app.map) {
    const [u0, v0, u1, v1] = bounds;
    const unit = Math.max(1, Math.min((width - 68) / (u1 - u0 || .01), (height - 58) / (v1 - v0 || .01))) * view.zoom;
    const dx = width / 2 + view.x - (focus?.[0] ?? (u0 + u1) / 2) * unit;
    const dy = height / 2 + view.y + (focus?.[1] ?? (v0 + v1) / 2) * unit;
    return {unit, point: (u, v) => [dx + u * unit, dy - v * unit]};
}
function rect(ctx, p, x, y, w, h, fill, stroke = null) {
    const [a, b] = p.point(x, y + h);
    ctx.fillStyle = fill;
    ctx.fillRect(a, b, w * p.unit + .18, h * p.unit + .18);
    if (stroke) {
        ctx.strokeStyle = stroke;
        ctx.strokeRect(a, b, w * p.unit, h * p.unit);
    }
}
function circle(ctx, x, y, radius, fill, stroke) {
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) { ctx.strokeStyle = stroke; ctx.stroke(); }
}
function legend(id, entries) {
    $(id).replaceChildren(...entries.map(([key, label]) => {
        const row = node("span");
        row.append(node("i", null, key), document.createTextNode(tr(label)));
        return row;
    }));
}
function scaleMark(ctx, width, height, p, label) {
    const mm = 1000 * 73 / p.unit;
    const step = 10 ** Math.floor(Math.log10(mm));
    const value = Math.max(1, Math.floor(mm / step)) * step;
    const px = value / 1000 * p.unit;
    ctx.font = '11px "Cascadia Mono", "Microsoft YaHei", monospace';
    ctx.fillStyle = "#b9c8b1";
    ctx.fillText(tr(label), 13, 19);
    ctx.fillText(decimal.format(value) + " mm", width - px - 15, height - 18);
    ctx.fillRect(width - px - 15, height - 13, px, 1);
}
function antTone(a) {
    return a.stage === "Adult" ? (a.caste === "Queen" ? colors.queen : colors[a.program] || colors.worker) :
        colors[a.stage.toLowerCase()] || colors.worker;
}
function stageKey(ant) {
    if (ant.stage !== "Adult") return ant.stage.toLowerCase();
    if (ant.caste === "Queen") return "queen";
    return ant.caste === "Worker" ? "worker" : "adult";
}
function stageCounts(ants) {
    const counts = new Map(mapStages.map(([key]) => [key, 0]));
    for (const ant of ants) {
        const key = stageKey(ant);
        counts.set(key, (counts.get(key) || 0) + 1);
    }
    return counts;
}
function stageSummary(ants) {
    const counts = stageCounts(ants);
    return mapStages.filter(([key]) => counts.get(key)).map(([key, message]) =>
        tr(message) + " " + decimal.format(counts.get(key))).join(" · ");
}
function markerShape(ctx, ant, x, y, selected) {
    const tone = antTone(ant);
    if (ant.stage === "Adult") {
        if (ant.caste === "Queen") {
            ctx.fillStyle = tone;
            for (const [dx, dy, radius] of [[-4, 2, 4.7], [0, 0, 3.6], [4, -2, 3.0]]) {
                circle(ctx, x + dx, y + dy, radius, tone, "#1c251d");
            }
        } else circle(ctx, x, y, 5, tone, "#1c251d");
    } else {
        ctx.beginPath();
        ctx.ellipse(x, y, ant.stage === "Egg" ? 3.0 : 5, ant.stage === "Pupa" ? 2.8 : 2.2, -.65, 0, Math.PI * 2);
        ctx.fillStyle = tone;
        ctx.fill();
        ctx.strokeStyle = "#1c251d";
        ctx.stroke();
    }
    if (selected) {
        ctx.strokeStyle = "#fffbd3";
        ctx.beginPath();
        ctx.arc(x, y, 10, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = "#fffbd3";
        ctx.font = "11px monospace";
        ctx.fillText("#" + ant.id, x + 13, y - 4);
    }
}
function motorPose(ant) {
    if (ant.display_position_m) return ant.display_position_m;
    const plan = showLiveMotor() ? ant.motion_plan : null;
    return plan ? plan.from_m.map((start, i) => start + plan.progress*(plan.to_m[i]-start)) : ant.position_m;
}

function planAngle(plan, point, time) {
    const origin = point(plan.from_m), goal = point(plan.to_m);
    const next = Math.atan2(goal[1] - origin[1], goal[0] - origin[0]);
    if (!plan.heading || time >= plan.translates_ms) return next;
    const compass = (plan.heading - 1) * Math.PI / 4;
    const v = plan.heading > 8 ? [0, plan.heading === 9 ? 1 : -1, 0] : [Math.cos(compass), 0, Math.sin(compass)];
    const projected = point(plan.from_m.map((n, i) => n + 0.001 * v[i]));
    const du = projected[0] - origin[0], dv = projected[1] - origin[1];
    if (Math.hypot(du, dv) < 1e-6) return next;
    const before = Math.atan2(dv, du);
    const turn = Math.atan2(Math.sin(next - before), Math.cos(next - before));
    return before + turn * (time - plan.begins_ms) / (plan.translates_ms - plan.begins_ms);
}

function drawAdult(ctx, ant, x, y, radius, heading, selected, progress, time, footprint = 0) {
    const queen = ant.caste === "Queen";
    ctx.save();
    ctx.translate(x,y);
    if (footprint && $("body-envelopes").checked) {
        ctx.fillStyle = "#a6de9b24";
        ctx.strokeStyle = "#a6de9b90";
        ctx.fillRect(-footprint,-footprint,2*footprint,2*footprint);
        ctx.strokeRect(-footprint,-footprint,2*footprint,2*footprint);
    }
    ctx.rotate(heading);
    ctx.scale(radius,radius);
    const gait = progress > 0 ? Math.sin(time * .038) * .19 : 0;
    ctx.strokeStyle="#281d17";
    ctx.lineWidth=.092;
    ctx.lineCap="round";
    for (const side of [-1,1]) {
        for (const [index, hip] of [-.19,.00,.19].entries()) {
            const span=(index-1)*.50+gait*side*(index===1?-1:1);
            ctx.beginPath();
            ctx.moveTo(hip,side*.13);
            ctx.quadraticCurveTo(hip+span*.58,side*.44,hip+span,side*.48);
            ctx.lineTo(hip+span*.90,side*.68);
            ctx.stroke();
        }
        ctx.beginPath();
        ctx.moveTo(.62,side*.12);
        ctx.quadraticCurveTo(.97,side*.13,.91,side*.37);
        ctx.stroke();
    }
    const shells=[[-.58,queen ? .42 : .31,queen ? .33 : .23],[-.23,.12,.10],[.02,.29,.19],[.52,.24,.18]];
    const light=ctx.createLinearGradient(0,-.3,0,.33);
    light.addColorStop(0,queen?"#b37e51":"#806446");
    light.addColorStop(.38,queen?"#704230":"#50382a");
    light.addColorStop(1,"#251c18");
    for (const [offset,w,h] of shells) {
        ctx.beginPath();
        ctx.ellipse(offset,0,w,h,0,0,Math.PI*2);
        ctx.fillStyle=light;
        ctx.fill();
        ctx.strokeStyle="#bf997750";
        ctx.lineWidth=.025;
        ctx.stroke();
    }
    if (ant.loaded) circle(ctx,.82,0,.16,"#c89b5b","#e4c89a");
    ctx.restore();
    if (selected) {
        ctx.lineWidth=1.25;
        ctx.strokeStyle="#ffe1a3";
        ctx.beginPath();
        ctx.arc(x,y,radius+4,0,Math.PI*2);
        ctx.stroke();
        ctx.lineWidth=1;
        ctx.fillStyle="#fffbd3";
        ctx.font="11px monospace";
        ctx.fillText("#"+ant.id,x+radius+8,y-4);
    }
}

function displayedMotion(ant) {
    return ant.display_position_m ? ant.display_motion : ant.motion_plan;
}

function adultGlyphSize(ant, terrain, pixelsPerMeter) {
    const workerSize = Math.max(4, (terrain?.body_half_q || 1) * (terrain?.quantum_m || .0005) * pixelsPerMeter);
    return workerSize * (ant.caste === "Queen" ? 1.65 : 1);
}

function adultHeading(ant, point, time) {
    const motion = displayedMotion(ant);
    if (motion) return planAngle(motion, point, time);
    const habitat = app.live && liveView.state?.habitat;
    if (ant.caste !== "Queen" || !habitat?.sealed_chamber) return 0;
    // The laying layout uses the direction of the familiar brood area.
    const from = motorPose(ant), nursery = habitat.brood_site_m;
    const dx = nursery[0] - from[0], dz = nursery[2] - from[2];
    const head = [...from];
    if (Math.abs(dx) >= Math.abs(dz)) head[0] += dx > 0 ? .001 : -.001;
    else head[2] += dz > 0 ? .001 : -.001;
    const [x, y] = point(from), [tx, ty] = point(head);
    return Math.atan2(ty - y, tx - x);
}

function drawSoilParcels(ctx, piles, point, visible, pixelsPerMeter) {
    const deposits = new Map();
    for (const pile of piles || []) {
        if (!visible(pile.position_m)) continue;
        const key = pile.position_m.join(",");
        const previous = deposits.get(key);
        deposits.set(key, {position: pile.position_m, volume: pile.volume_mm3 + (previous?.volume || 0)});
    }
    for (const {position, volume} of deposits.values()) {
        const [x, y] = point(position);
        const radius = Math.max(2, Math.min(13, Math.cbrt(volume) * pixelsPerMeter / 2300));
        ctx.save();
        ctx.translate(x, y);
        ctx.fillStyle = "#d0a16a";
        ctx.strokeStyle = "#68452d";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.ellipse(0, 0, radius, radius * .65, 0, 0, Math.PI * 2);
        ctx.fill(); ctx.stroke();
        ctx.fillStyle = "#f5cd8e";
        ctx.fillRect(-radius * .3, -radius * .25, Math.max(1, radius * .24), 1);
        ctx.restore();
    }
}

function drawOccupants(ctx, visible, point, pixelsPerMeter, terrain, time) {
    const markers = new Map();
    for (const ant of visible) {
        const [x, y] = point(motorPose(ant));
        // Only merge coincident projections. Membership retains original 3D coordinates.
        const key = x + "," + y;
        if (!markers.has(key)) markers.set(key, {x, y, ants: []});
        markers.get(key).ants.push(ant);
    }
    app.hits = [];
    for (const {x, y, ants} of markers.values()) {
        if (ants.length === 1) {
            const a=ants[0];
            const half=terrain && (a.loaded?terrain.loaded_half_q:terrain.body_half_q)*terrain.quantum_m*pixelsPerMeter;
            const size = adultGlyphSize(a, terrain, pixelsPerMeter);
            if (a.stage==="Adult" && a.caste!=="Male") {
                const motion = displayedMotion(a);
                drawAdult(ctx, a, x, y, size, adultHeading(a, point, time), a.id === app.selected,
                    motion?.progress, time, half);
            } else markerShape(ctx,a,x,y,a.id===app.selected);
            app.hits.push({id:a.id,x,y,radius:Math.max(11,a.stage==="Adult"?size:0),ants});
            continue;
        }
        const selected = ants.some(a => a.id === app.selected);
        circle(ctx, x, y, 12, "#152319", selected ? "#f8e9a1" : "#aab9a1");
        const counts = stageCounts(ants);
        let angle = -Math.PI / 2;
        for (const [stage] of mapStages) {
            if (!counts.get(stage)) continue;
            const next = angle + counts.get(stage) / ants.length * Math.PI * 2;
            ctx.beginPath();
            ctx.arc(x, y, 11, angle, next);
            ctx.strokeStyle = colors[stage] || colors.worker;
            ctx.lineWidth = 3;
            ctx.stroke();
            angle = next;
        }
        ctx.lineWidth = 1;
        ctx.font = "bold 10px monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "#f4efd7";
        ctx.fillText(ants.length > 99 ? "99+" : String(ants.length), x, y + .5);
        ctx.textAlign = "left";
        ctx.textBaseline = "alphabetic";
        app.hits.push({x, y, radius: 15, ants});
    }
}

let soilGrain;
function soilTexture(ctx) {
    if (!soilGrain) {
        const tile = document.createElement("canvas");
        tile.width=47; tile.height=41;
        const brush=tile.getContext("2d");
        for (let i=0;i<120;i++) {
            brush.fillStyle=i%3===0?"#f3d6a748":"#27170f33";
            brush.fillRect((i*23+i*i)%47,(i*19+i*i)%41,i%7===0?2:1,1);
        }
        soilGrain=ctx.createPattern(tile,"repeat");
    }
    return soilGrain;
}
function paintSoilEdges(ctx, slice, p, bounds) {
    const grain=soilTexture(ctx);
    const q=slice.quantum_m;
    ctx.beginPath();
    for (const [j,row] of slice.rows.entries()) for (let i=0;i<row.length;i++) if (row[i]!=="0") {
        const [x0,y0]=p.point(bounds[0]+i*q,bounds[1]+j*q);
        ctx.rect(x0,y0-q*p.unit,q*p.unit,q*p.unit);
    }
    if (grain) { ctx.fillStyle=grain; ctx.fill(); }
    ctx.beginPath();
    for (const [j,row] of slice.rows.entries()) for (let i=0;i<row.length;i++) if (row[i]==="0") {
        const u=bounds[0]+i*q,v=bounds[1]+j*q;
        const edge=(x1,y1,x2,y2)=>{ctx.moveTo(...p.point(x1,y1));ctx.lineTo(...p.point(x2,y2));};
        if (i>0 && row[i-1]!=="0") edge(u,v,u,v+q);
        if (i+1<row.length && row[i+1]!=="0") edge(u+q,v,u+q,v+q);
        if (j>0 && slice.rows[j-1][i]!=="0") edge(u,v,u+q,v);
        if (j+1<slice.rows.length && slice.rows[j+1][i]!=="0") edge(u,v+q,u+q,v+q);
    }
    ctx.strokeStyle="#301f19";
    ctx.lineWidth=4;
    ctx.stroke();
    ctx.strokeStyle="#dbaf8170";
    ctx.lineWidth=1;
    ctx.stroke();
}
function drawUnderground(ctx, p, bounds, slice) {
    const q = slice.quantum_m;
    rect(ctx, p, bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1], "#736550");
    for (const [row, cells] of slice.rows.entries()) {
        for (let start = 0, end; start < cells.length; start = end) {
            end = start + 1;
            while (end < cells.length && cells[end] === cells[start]) end++;
            if (cells[start] === "0") continue;
            const shade = cells[start] === "2" ? "#676869" : "#987657";
            rect(ctx, p, bounds[0] + start * q, bounds[1] + row * q, (end - start) * q, q, shade);
        }
    }
    paintSoilEdges(ctx, slice, p, bounds);
    for (const [row, cells] of (slice.unloaded_body_clear || []).entries()) {
        for (let i = 0; i < cells.length; i++) if (cells[i] === "1") {
            circle(ctx, ...p.point(bounds[0] + i*q, bounds[1] + row*q), Math.min(2.5, p.unit*q/5), "#91be80");
        }
    }
}

let nurseryTerrain;
function drawNurseryTerrain(ctx, p, bounds, slice, width, height) {
    const dpr = window.devicePixelRatio || 1, margin = 96;
    const [x, y] = p.point(bounds[0], bounds[1]);
    const key = [liveView.state.epoch, app.geometry.revision, slice.axis, slice.plane_q, ...slice.bounds_q,
        Boolean(slice.unloaded_body_clear), p.unit, width, height, dpr].join(":");
    if (nurseryTerrain?.key !== key || Math.abs(x - nurseryTerrain.x) >= margin || Math.abs(y - nurseryTerrain.y) >= margin) {
        const layer = nurseryTerrain?.layer ?? document.createElement("canvas");
        layer.width = Math.ceil((width + 2 * margin) * dpr);
        layer.height = Math.ceil((height + 2 * margin) * dpr);
        const brush = layer.getContext("2d");
        brush.setTransform(dpr, 0, 0, dpr, margin * dpr, margin * dpr);
        drawUnderground(brush, p, bounds, slice);
        nurseryTerrain = {key, layer, x, y};
    }
    const {layer} = nurseryTerrain;
    ctx.drawImage(layer, x - nurseryTerrain.x - margin, y - nurseryTerrain.y - margin, layer.width / dpr, layer.height / dpr);
}

function renderLocation() {
    $("location").hidden = !app.location;
    if (!app.location) return;
    const ants = app.location.all ? app.visible : app.location.ids ? app.visible.filter(a => app.location.ids.has(a.id)) :
        app.visible.filter(a => a.position_m[app.location.axes[0]] === app.location.at[0] &&
            a.position_m[app.location.axes[1]] === app.location.at[1]);
    put("location-title", tr(app.location.all ? "Individuals in view" : "Individuals at this marker"));
    put("location-note", stageSummary(ants) || tr("No living individuals here at this time."));
    const signature = JSON.stringify([language, app.selected, ants.map(a => [a.id, a.stage])]);
    if ($("location-list").dataset.signature === signature) return;
    $("location-list").dataset.signature = signature;
    $("location-list").replaceChildren(...ants.map(a => {
        const chip = button(tr(a.stage === "Adult" ? a.caste : a.stage) + " #" + a.id, () => selectAnt(a.id).catch(report));
        chip.dataset.antId = a.id;
        chip.setAttribute("aria-pressed", String(a.id === app.selected));
        return chip;
    }));
}
function showLocation(hit = null) {
    const axes = app.section === "slice" && app.geometry?.slice ? app.geometry.slice.axes : [0, 2];
    app.location = !hit ? {all: true} : app.section === "nest" ? {ids: new Set(hit.ants.map(a => a.id))} :
        {axes, at: [hit.ants[0].position_m[axes[0]], hit.ants[0].position_m[axes[1]]]};
    renderLocation();
}
function showLiveMotor() {
    return app.live && Boolean(liveView.state?.seeded_nursery || liveView.state?.habitat);
}

function drawSite(ctx, at, label, color, dy = -11, outline = false) {
    const [x, y] = at;
    ctx.save();
    circle(ctx, x, y, 6, outline ? "transparent" : color, outline ? color : "#17231a");
    ctx.font = '12px "Inter", "Microsoft YaHei", sans-serif';
    ctx.textBaseline = "middle";
    const width = ctx.measureText(label).width;
    ctx.fillStyle = "#152019ee";
    ctx.fillRect(x + 9, y + dy - 9, width + 12, 20);
    ctx.fillStyle = "#fff5de";
    ctx.fillText(label, x + 15, y + dy + 1);
    ctx.restore();
}

function drawMap(motionOnly = false) {
    if (app.compare || !app.state) return;
    const nursery = app.live && liveView.state?.seeded_nursery;
    const habitat = app.live && liveView.state?.habitat;
    const display = showLiveMotor() ? liveMotion.frame(performance.now(), app.section === "nest") : null;
    if (motionOnly && !display) return;
    if (!motionOnly) $("viewer").classList.toggle("nursery-view", Boolean(nursery));
    const canvas = canvasContext($("map"));
    if (!canvas) return;
    const {ctx, width, height} = canvas;
    const state = display ?? app.state, surface = app.meta.surface, slice = app.geometry?.slice;
    const time = display?.time ?? app.time;
    app.renderedTimeMs = time;
    if (app.section === "nest") {
        $("trail-control").hidden = $("envelope-control").hidden = true;
        $("find-pantry").hidden = !app.live;
        $("find-brood").hidden = !habitat;
        $("find-entrance").hidden = !habitat || !app.geometry?.openings?.length;
        return drawNest(canvas, state, motionOnly);
    }
    const underground = app.section === "slice" && slice;
    const follow = app.live && app.follow && state.ants.find(a => a.id === app.selected);
    const tracked = follow ? motorPose(follow) : null;
    const terrain = app.meta.settings.geometry, surfaceY = planeSurface();
    if (!motionOnly) {
        $("envelope-control").hidden = !terrain || !app.live;
        $("find-pantry").hidden = !app.live;
        $("find-brood").hidden = !habitat;
        $("find-entrance").hidden = !habitat || !app.geometry?.openings?.length;
        $("trail-control").hidden = !habitat || Boolean(underground);
    }
    ctx.fillStyle = underground ? "#152019" : "#15241a";
    ctx.fillRect(0, 0, width, height);
    let p, fits, point, orientation;
    if (underground) {
        const [u, v, n] = slice.axes, q = slice.quantum_m, o = slice.origin_m;
        const [x0, y0, x1, y1] = slice.bounds_q;
        const bounds = [o[u] + x0 * q, o[v] + y0 * q, o[u] + x1 * q, o[v] + y1 * q];
        p = projection(width, height, bounds, tracked && [tracked[u], tracked[v]]);
        point = a => p.point(a[u], a[v]);
        fits = a => Math.floor((a[n] - o[n]) / q + 1e-9) === slice.plane_q;
        orientation = slice.axis === "z" ? "X east / Y up" : slice.axis === "x" ? "Z north / Y up" : "X east / Z north";
        if (nursery) drawNurseryTerrain(ctx, p, bounds, slice, width, height);
        else drawUnderground(ctx, p, bounds, slice);
        if (!motionOnly) {
            put("space-caption", tr("Quantized material section · {count} committed edits", {count: app.geometry.revision}) +
                (app.geometry.cropped ? " · " + tr("Local section of the terrain") : ""));
            legend("map-legend", [["soil", "Soil"], ["rock", "Rock"], ["void", "Void"], ["queen", "Queen"], ["egg", "Eggs"],
                ["larva", "Larvae"], ["pupa", "Pupae"], ["worker", "Worker"], ["entrance", "Recent movement points"],
                ...(app.path.length ? [["trace", "Selected individual's recorded positions"]] : []),
                ...(slice.unloaded_body_clear ? [["entrance", "Unloaded body fits here"]] : [])]);
        }
    } else {
        const [lo, hi] = app.meta.bounds_m;
        const points = [...state.sources.map(s => s.position_m), ...app.meta.colonies.map(c => c.position_m)];
        let bounds = [lo[0], lo[2], hi[0], hi[2]];
        if (surface) {
            const [x, , z] = surface.origin_m, step = surface.cell_m;
            bounds = [x - step / 2, z - step / 2, x + (surface.width - .5) * step, z + (surface.height - .5) * step];
        } else if (points.length) {
            bounds = [Math.min(...points.map(a => a[0])) - .01, Math.min(...points.map(a => a[2])) - .01,
                Math.max(...points.map(a => a[0])) + .01, Math.max(...points.map(a => a[2])) + .01];
        }
        p = projection(width, height, bounds, tracked && [tracked[0], tracked[2]]);
        point = a => p.point(a[0], a[2]);
        fits = a => a[1] >= surfaceY - 1e-10;
        orientation = "X east / Z north";
        rect(ctx, p, bounds[0], bounds[1], bounds[2]-bounds[0], bounds[3]-bounds[1], "#243629", "#58705b");
        if (surface) {
            const step = surface.cell_m;
            const stride = Math.max(1, Math.ceil(Math.max(surface.width, surface.height) / 120));
            ctx.lineWidth = .5;
            ctx.strokeStyle = "#3b5140";
            ctx.beginPath();
            for (let x = 0; x <= surface.width; x += stride) {
                ctx.moveTo(...p.point(bounds[0] + x*step, bounds[1]));
                ctx.lineTo(...p.point(bounds[0] + x*step, bounds[3]));
            }
            for (let z = 0; z <= surface.height; z += stride) {
                ctx.moveTo(...p.point(bounds[0], bounds[1] + z*step));
                ctx.lineTo(...p.point(bounds[2], bounds[1] + z*step));
            }
            ctx.stroke();
            ctx.lineWidth = 1;
            for (const i of surface.blocked) rect(ctx, p, bounds[0] + i%surface.width*step,
                bounds[1] + Math.floor(i/surface.width)*step, step, step, "#152019");
        }
        if (terrain) {
            const [x, , z] = terrain.origin_m, q = terrain.quantum_m, s = terrain.solid;
            rect(ctx, p, x + s[0]*q, z + s[2]*q, (s[3]-s[0])*q, (s[5]-s[2])*q, "#354135", "#80936f");
        }
        if (habitat && surface && $("show-trails").checked) {
            const [x, , z] = surface.origin_m, step = surface.cell_m;
            ctx.save();
            for (const [column, row, units] of state.trails ?? []) {
                ctx.globalAlpha = Math.min(.65, .12 + .18 * Math.sqrt(units));
                rect(ctx, p, x + (column - .5)*step, z + (row - .5)*step, step, step, "#be9ddd");
            }
            ctx.restore();
        }
        const openings = app.geometry?.openings || [];
        for (const o of openings) {
            const q = app.geometry.opening_cell_m;
            rect(ctx, p, o[0]-q/2, o[2]-q/2, q, q, colors.entrance);
        }
        for (const o of app.meta.surface_entrances_m) {
            if (!openings.length) circle(ctx, ...point(o), 4, "#aac68f", "#102418");
        }
        for (const s of state.sources.filter(s => fits(s.position_m))) {
            const [x, y] = point(s.position_m);
            const inStock = s.stock_ug.some(v => v > 0);
            if (habitat) {
                const water = s.initial_ug[2] > 0 && s.initial_ug[2] === s.initial_ug.reduce((n, part) => n + part, 0);
                const label = tr(water ? "Water source" : "Food source");
                drawSite(ctx, [x, y], label + (inStock ? "" : " · " + tr("depleted")), water ? "#91c9db" : colors.food);
                continue;
            }
            ctx.fillStyle = inStock ? colors.food : "#52635a";
            ctx.fillRect(x-4, y-4, 8, 8);
            ctx.font = '11px "Cascadia Mono", "Microsoft YaHei", monospace';
            ctx.fillStyle = "#d3e6d5";
            ctx.fillText(tr("Source #{id}", {id: s.id}) + (inStock ? "" : " · " + tr("depleted")), x + 8, y - 5);
        }
        if (!motionOnly) {
            put("space-caption", tr("Surface positions at this cut") + " · " +
                tr(openings.length ? "terrain openings from geometry" : "flat grid where recorded"));
            legend("map-legend", [["entrance", "Opening / surface nest"], ["food", "Source"], ["worker", "Worker"],
                ...(habitat && $("show-trails").checked ? [["trace", "Trail pheromone"]] : []),
                ["entrance", "Recent movement points"], ...(app.path.length ? [["trace", "Selected individual's recorded positions"]] : [])]);
        }
    }
    const motion = app.recentMotion;
    const trail = (motion?.points || []).filter(move => (!display || move.time_ms <= time) && fits(move.position_m));
    for (const move of trail) circle(ctx, ...point(move.position_m), 1.8, "#93d4b07a");
    for (const move of app.path) {
        if ((!display || move.time_ms <= time) && fits(move.position_m)) circle(ctx, ...point(move.position_m), 2, "#ad9ce18a");
    }
    const segment = app.restReplay;
    const visible = state.ants.filter(a => fits(motorPose(a)));
    app.visible = visible;
    drawSoilParcels(ctx, state.soil_piles, point, fits, p.unit);
    drawOccupants(ctx, segment ? visible.filter(a => a.id !== segment.start.actor) : visible, point, p.unit, terrain, time);
    if (underground && app.live) {
        for (const depot of display?.colonies ?? app.meta.colonies) {
            if (!fits(depot.position_m)) continue;
            const stock = depot.stock_ug.reduce((total, part) => total + part, 0);
            drawSite(ctx, point(depot.position_m), tr("Nest food · {mass}", {mass: withUnit(stock, "µg")}),
                stock ? "#f1ce86" : "#a08d67", 17);
        }
        if (habitat) {
            if (fits(habitat.brood_site_m))
                drawSite(ctx, point(habitat.brood_site_m), tr(habitat.sealed_chamber ? "Brood area" : "Brood chamber"), "#d9a375", -19, true);
            for (const source of state.sources) if (source.position_m[1] < surfaceY && fits(source.position_m)) {
                const label = tr("Water in the brood chamber") + " · " + withUnit(source.stock_ug[2], "µg");
                drawSite(ctx, point(source.position_m), label, "#91c9db", 35, true);
            }
        }
    }
    if (segment) drawRestSegment(ctx, point, fits, segment);
    const selected = app.live && visible.find(a => a.id === app.selected);
    const plan = selected && displayedMotion(selected);
    if (plan && fits(plan.from_m) && fits(plan.to_m)) {
        ctx.save();
        ctx.strokeStyle = "#e4c791";
        ctx.setLineDash([3,4]);
        ctx.beginPath();
        ctx.moveTo(...point(plan.from_m));
        ctx.lineTo(...point(plan.to_m));
        ctx.stroke();
        ctx.restore();
    }
    if (app.live) drawLiveActions(ctx, point, fits, time);
    if (!motionOnly) describeMap(visible, underground, state, trail, motion, segment, plan, display);
    if (app.selectedFact && fits(app.selectedFact.position_m)) {
        const [x, y] = point(app.selectedFact.position_m);
        ctx.strokeStyle = "#ffe1a3";
        ctx.strokeRect(x - 7, y - 7, 14, 14);
    }
    scaleMark(ctx, width, height, p, orientation);
    ctx.font = '11px "Cascadia Mono", "Microsoft YaHei", monospace';
    ctx.fillStyle = "#a9b6a7";
    ctx.fillText(tr("{count} living", {count: state.ants.length}), 13, height - 13);
}

function describeMap(visible, underground, state, trail, motion, segment, plan, display) {
    const shared = app.hits.filter(hit => hit.ants.length > 1);
    const largest = shared.reduce((best, item) => !best || item.ants.length > best.ants.length ? item : best, null);
    app.visibleSummary = largest;
    $("show-largest").hidden = !largest;
    if (largest) put("show-largest", tr("At marker ({count})", {count: largest.ants.length}));
    const name = underground ? "{count} in section" : "{count} on surface";
    put("map-summary", tr(name, {count: visible.length}) + (visible.length ? " · " + stageSummary(visible) : ""));
    const notes = [];
    if (largest) notes.push(tr("Click a numbered marker to inspect individuals at that position."));
    if (!visible.length && state.ants.length) notes.push(tr(underground ?
        "No living individuals in this layer. Try another layer or the surface." :
        "No living individuals on the surface at this time. Try the underground view."));
    if (!underground && !visible.length && state.ants.length) {
        notes.push(tr("{count} living outside this view.", {count: state.ants.length}));
    }
    if (trail.length) notes.push(tr(app.live ? "{count} movement points from recent live events." :
        "{count} recorded movement points in this view over the last 5 simulated minutes.", {count: trail.length}));
    else if (!app.live && motion && !motion.points.length) notes.push(tr("No movement recorded in the last 5 simulated minutes."));
    if (motion?.truncated) notes.push(tr("Recent movement display capped at 144 points."));
    if (segment) notes.push(tr("Recorded movement segment shown in slow motion. The heading is the direction of travel."));
    if (display) notes.push(tr("Live motion follows Core segments with a short display delay."));
    else if (showLiveMotor()) notes.push(tr("Moving markers follow the validated Core segments at the current simulation time."));
    if (plan) notes.push(tr("Selected worker · open Core segment · {percent}% through translation", {percent: Math.round(100*plan.progress)}));
    put("map-detail", notes.join(" "));
    renderLocation();
}

function graph(id, tracks, end, stamp, legendId = null, origin = 0) {
    const canvas = canvasContext($(id));
    if (!canvas) return;
    const {ctx, width, height} = canvas;
    let max = 1;
    for (const s of tracks) for (const [, value] of s.values) if (value != null) max = Math.max(max, value);
    const low = 38, plotW = Math.max(1, width - low - 13), plotH = Math.max(1, height - 26);
    const xx = ms => low + plotW * ms / Math.max(1, end), yy = v => 9 + plotH * (1 - v / max);
    ctx.font = '10px "Cascadia Mono", "Microsoft YaHei", monospace';
    ctx.fillStyle = "#a9b6a7";
    ctx.strokeStyle = "#354237";
    for (const i of [0, .5, 1]) {
        const y = yy(max * i);
        ctx.beginPath(); ctx.moveTo(low, y); ctx.lineTo(width - 13, y); ctx.stroke();
        ctx.fillText(new Intl.NumberFormat(language, {notation: "compact", maximumFractionDigits: 1}).format(max * i), 2, y + 3);
    }
    for (const s of tracks) {
        ctx.strokeStyle = s.color;
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        let drawing = false;
        for (const [time, value] of s.values) {
            if (value == null) { drawing = false; continue; }
            if (drawing) ctx.lineTo(xx(time), yy(value));
            else ctx.moveTo(xx(time), yy(value));
            drawing = true;
        }
        ctx.stroke();
    }
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#e4e6d6";
    const mark = xx(stamp);
    ctx.beginPath(); ctx.moveTo(mark, 6); ctx.lineTo(mark, height - 12); ctx.stroke();
    ctx.fillStyle = "#a9b6a7";
    ctx.fillText(day(origin), low, height - 3);
    ctx.textAlign = "right";
    ctx.fillText(day(origin+end), width - 11, height - 3);
    ctx.textAlign = "left";
    if (legendId) legend(legendId, tracks.map(t => [t.key, t.label]));
}
function track(key, label, field, series = app.series) {
    return {key, label, color: colors[key] || colors.worker, values: series.map(row => [row.time_ms, field(row)])};
}
function populationTracks() {
    return ["workers", "eggs", "larvae", "pupae"].map((k, i) =>
        track(["worker", "egg", "larva", "pupa"][i], k, row => row.population[k]));
}
function dashboard() {
    const kind = $("chart-series").value;
    const keys = ["worker", "food", "larva", "pupa"];
    let tracks = [];
    if (kind === "resources") {
        tracks = [track("worker", "External carbohydrate (µg)", r => r.external_ug[0]), track("food", "External water (µg)", r => r.external_ug[2]),
            track("larva", "Nest protein (µg)", r => r.nest_ug[1]), track("pupa", "Nest water (µg)", r => r.nest_ug[2])];
    } else if (kind === "activity") {
        tracks = ["collections", "deliveries", "trophallaxis", "activations"].map((k, i) => track(keys[i], columns[k], r => r.cumulative[k] || 0));
    } else if (kind === "deaths") {
        tracks = ["Energy depleted", "Dehydration", "Unknown", "Fixture death"].map((k, i) =>
            track(keys[i], k, r => r.deaths[k] || 0));
    } else if (kind === "soil") {
        const units = app.meta.settings.geometry?.quantum_m;
        if (units) tracks = [track("larva", "Excavated (mm³)", r => r.excavated_q3 * units**3 * 1e9),
            track("pupa", "Backfilled (mm³)", r => r.filled_q3 * units**3 * 1e9)];
    } else {
        tracks = [track("queen", "Queen water (µg)", r => r.queen_sample?.hydration_ug),
            track("food", "Queen energy (µJ)", r => r.queen_sample?.energy_nj == null ? null : r.queen_sample.energy_nj / 1000)];
    }
    graph("ledger-chart", tracks, app.meta.end_ms, app.time, "ledger-legend");
}
function draw() {
    if (!app.meta) return;
    if (app.live) { drawMap(); return; }
    if (!app.compare) {
        drawMap();
        graph("timeline-chart", populationTracks(), app.meta.end_ms, app.time);
        dashboard();
    } else if (app.reference) {
        graph("compare-chart", [
            track("worker", "Active archive", r => r.population.workers),
            track("larva", "Reference", r => r.population.workers, app.referenceSeries)
        ], Math.max(app.meta.end_ms, app.reference.end_ms), app.time);
    }
}

async function loadReference(preferred) {
    const version = ++app.referenceVersion;
    if (!$("reference").value) return;
    stopPlay();
    show(tr("Opening and verifying the reference archive…"));
    const archive = await api("archive/" + $("reference").value);
    const record = archive.worlds.find(w => w.key === preferred) || archive.worlds[0];
    if (version !== app.referenceVersion || !app.compare) return;
    setOptions($("reference-world"), archive.worlds, record.key);
    $("reference-world").hidden = archive.worlds.length < 2;
    const series = await api("world/" + record.key + "/series");
    if (version !== app.referenceVersion || !app.compare) return;
    app.reference = record;
    app.referenceSeries = series;
    $("compare-time").max = Math.max(app.meta.end_ms, record.end_ms);
    await updateComparison();
    show();
}
async function updateComparison() {
    const version = ++app.compareVersion;
    const nest = [app.meta, app.reference].some(m => [32,33].includes(m.settings?.physics || m.physics)) ? "1" : "0";
    const [data, lists] = await Promise.all([api("compare", {left: app.meta.key, right: app.reference.key, time_ms: app.time, nest}),
        Promise.all([app.meta, app.reference].map(m => {
            const low = Math.floor(Math.min(app.time, m.end_ms) / DAY) * DAY;
            return api("world/" + m.key + "/events", {group: "highlights", since_ms: low, until_ms: Math.min(low + DAY - 1, m.end_ms), limit: 5});
        }))]);
    if (!app.compare || version !== app.compareVersion) return;
    $("compare-marker-option").hidden = !data.worlds.some(trial => trial.nest);
    const differing = Object.values(data.settings).filter(s => s.status === "different").length;
    const unknown = Object.values(data.settings).filter(s => s.status === "unknown").length;
    $("compare-status").replaceChildren(node("p", tr(
        "{different} recorded input differences · {unknown} unknown input fields. Compare colony outcomes and roles. Ant IDs remain local to each archive.",
        {different: differing, unknown}), differing || unknown ? "different" : "matching"));
    const cards = data.worlds.map(({world, state, cohort, outside_record, morphology}, i) => {
        const box = node("article", null, "compare-card");
        const p = state.population, c = state.cumulative;
        box.append(node("h3", tr(world.title)), node("p", day(state.time_ms) +
            (outside_record ? " · " + tr("Archive ends before cursor") : "") +
            " · " + tr("Physics {version}", {version: world.physics}) + " · " + tr("Seed {seed}", {seed: world.seed}), "muted"),
        keyValues([["Queen / workers", tr(p.queens_alive.length ? "Alive" : "Absent") + " / " + p.workers],
            ["Eggs / larvae / pupae", [p.eggs, p.larvae, p.pupae].join(" / ")],
            ["First census cohort", cohort ? tr("{eclosed} eclosed / {size}", cohort) : tr("Not recorded at this cut")],
            ["No recorded positive feeding", cohort?.without_recorded_feeding ?? tr("Not recorded at this cut")],
            ["First cohort deaths", cohort ? Object.entries(cohort.deaths).map(([k, v]) => tr(k) + " " + v).join(", ") || tr("None at this cut") : null],
            ["Collections / deliveries", (c.collections || 0) + " / " + (c.deliveries || 0)],
            ["Recruitment activations", c.activations || 0], ["Excavations / soil placements", (c.excavations || 0) + " / " + (c.soil_drops || 0)],
            ["Net soil removed", withUnit(state.net_removed_m3 == null ? null : state.net_removed_m3 * 1e9, "mm³")]]));
        if (morphology) box.append(keyValues([
            ["Floor section area",withUnit(morphology.area_mm2,"mm²")],
            ["Section perimeter",withUnit(morphology.perimeter_mm,"mm")],
            ["Wide room cores",morphology.rooms.length],
            ["Narrow junctions",morphology.junctions_q.length],
            ["Workers on reachable floor",morphology.supported_workers]
        ]));
        box.append(node("h4", tr("Committed facts on this day"), "subhead"));
        for (const event of lists[i].events) {
            const detail = node("p", "#" + event.id + " · " + eventLabel(event) + " · " + day(event.time_ms), "compare-fact");
            box.append(detail);
        }
        if (!lists[i].events.length) box.append(node("p", tr("No matching facts on this day."), "muted"));
        return box;
    });
    $("compare-cards").replaceChildren(...cards);
    data.worlds.forEach((trial, i) => {
        if (!trial.nest) return;
        const preview = node("canvas", null, "compare-nest");
        preview.setAttribute("aria-label", tr("Nest floor at the selected time"));
        cards[i].insertBefore(preview, cards[i].children[2]);
        drawCompareNest(preview, trial.nest, $("compare-markers").checked ? trial.state.ants : [], trial.morphology);
    });
    const inputSignature = language + JSON.stringify(data.settings);
    if ($("compare-config").dataset.signature !== inputSignature) {
        $("compare-config").dataset.signature = inputSignature;
        const settings = Object.entries(data.settings).map(([key, item]) => {
            const label = tr(names[key] || key);
            const container = node("div");
            const detail = node("details");
            detail.append(node("summary", label + " · " + tr(item.status), item.status === "different" ? "different" : ""),
                keyValues([["Active world", truth(item.left)], ["Reference", truth(item.right)]]));
            container.append(detail);
            return container;
        });
        $("compare-config").replaceChildren(...settings);
    }
    draw();
}

function stopPlay() {
    ++app.playVersion;
    if (app.playback) clearInterval(app.playback);
    app.playback = null;
    app.playingDelivery = false;
    app.restReplay = null;
    playbackControls(false);
}
function playbackControls(active) {
    for (const id of ["play", "compare-play"]) {
        put(id, tr(active ? "Ⅱ Pause" : "▶ Play"));
        $(id).setAttribute("aria-pressed", String(active));
    }
    const delivery = $("watch-delivery");
    if (app.playingDelivery) {
        delivery.textContent = tr("Stop delivery replay");
    } else {
        delivery.replaceChildren(document.createTextNode(tr("Watch first food delivery")));
        const first = firstDelivery(app.meta);
        if (first) delivery.append(node("small", day(first.time_ms)));
    }
    $("watch-delivery").setAttribute("aria-pressed", String(app.playingDelivery));
}
function playFrames(advance, interval) {
    const generation = ++app.playVersion;
    playbackControls(true);
    let busy = false;
    app.playback = setInterval(async () => {
        if (busy || generation !== app.playVersion) return;
        busy = true;
        try {
            if (!await advance(generation) && generation === app.playVersion) stopPlay();
        } catch (err) {
            if (generation === app.playVersion) { stopPlay(); report(err); }
        } finally {
            busy = false;
        }
    }, interval);
}
function firstDelivery(meta) {
    return meta?.milestones.find(m => m.label === "First food delivered" && m.ant);
}
async function actionBoundaries(end) {
    let frames = [end];
    if (end.action?.began_ms != null) {
        const result = await world("events", {group:"care",ant:end.actor,since_ms:end.action.began_ms,
            until_ms:end.time_ms,cut_event:end.id,limit:200});
        const start = result.events.find(e => e.actor===end.actor && e.action?.bout===end.action.bout && e.action.phase==="Started");
        const moved = result.events.filter(e => e.kind==="BroodMoved" && e.source===end.source && e.actor===end.related);
        if (start) frames = [start,...moved,end];
    } else if (end.kind === "AntBorn" && BigInt(end.id)>1n) {
        const previous = await world("event", {id:(BigInt(end.id)-1n).toString()});
        if (previous.kind==="ReproductionAttempt" && previous.source===end.source) frames = [previous,end];
    }
    return frames;
}
async function watchAction(mark) {
    if (["First move to a resting site", "Resting site with 10 or more workers"].includes(mark.label)) {
        await watchRestSegment(mark);
        return;
    }
    stopPlay();
    const version = app.playVersion;
    const end = await world("event",{id:mark.id});
    const frames = await actionBoundaries(end);
    if (version!==app.playVersion) return;
    app.selected = end.kind==="AntBorn" ? end.actor : end.related || end.actor;
    $("ant-id").value = app.selected || "";
    app.follow=false; toggle("follow",false);
    app.location=null;
    $("axis").value="y";
    inspect(true);
    show(tr("Showing recorded action boundaries in order."));
    let index=0;
    playFrames(async () => {
        const fact = frames[index++];
        preferView(fact.position_m);
        await seek(fact.time_ms,fact);
        if (app.selectedFact===fact) showEvent(fact);
        return index<frames.length;
    },850);
}
function drawRestSegment(ctx, point, fits, segment) {
    const a = segment.start.position_m, b = segment.move.position_m;
    const timing = segment.move.motion;
    const delay = timing ? timing.turn_ms / timing.duration_ms : 0;
    const translated = Math.max(0, (segment.progress-delay)/(1-delay));
    const current = a.map((value, i) => value + (b[i] - value) * translated);
    if (!fits(current)) return;
    const [x, y] = point(current), from = point(a), to = point(b);
    const heading = Math.atan2(to[1] - from[1], to[0] - from[0]);
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(...from);
    ctx.lineTo(...to);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#e4c791";
    ctx.stroke();
    ctx.translate(x, y);
    ctx.rotate(heading);
    ctx.beginPath();
    ctx.moveTo(9, 0);
    ctx.lineTo(-6, -4);
    ctx.lineTo(-4, 0);
    ctx.lineTo(-6, 4);
    ctx.closePath();
    ctx.fillStyle = "#ffe1a3";
    ctx.fill();
    ctx.restore();
    ctx.save();
    ctx.font = '600 12px "Cascadia Mono", monospace';
    const label = tr("Worker") + " #" + segment.start.actor +
        (delay && segment.progress<delay ? " · " + tr("Turning") : "");
    ctx.fillStyle = "#152319";
    ctx.fillRect(x+10,y-29,ctx.measureText(label).width+12,20);
    ctx.fillStyle = "#ffe1a3";
    ctx.fillText(label,x+16,y-15);
    ctx.restore();
}
async function watchRestSegment(mark) {
    stopPlay();
    const generation = app.playVersion;
    const data = await world("rest-segment", {id: mark.id});
    if (generation !== app.playVersion) return;
    if (!data) {
        await jumpEvent(mark.id, mark.ant);
        return;
    }
    app.selected = data.start.actor;
    $("ant-id").value = app.selected;
    app.follow = false;
    toggle("follow", false);
    app.location = null;
    app.map = {zoom: 2, x: 0, y: 0};
    $("axis").value = "y";
    preferView(data.start.position_m);
    await seek(data.start.time_ms, data.start);
    if (generation !== app.playVersion) return;
    app.restReplay = {...data, progress: 0};
    const begin = performance.now();
    show(tr("Recorded movement segment shown in slow motion. The heading is the direction of travel."));
    playbackControls(true);
    const step = now => {
        if (generation !== app.playVersion || !app.restReplay) return;
        app.restReplay.progress = Math.min(1, (now - begin) / 1600);
        drawMap();
        if (app.restReplay.progress < 1) requestAnimationFrame(step);
        else {
            stopPlay();
            seek(data.completion.time_ms, data.completion).then(() => showEvent(data.completion)).catch(report);
        }
    };
    requestAnimationFrame(step);
}
function drawCompareNest(canvas, slice, ants, morphology) {
    const view = canvasContext(canvas);
    if (!view) return;
    const {ctx, width, height} = view;
    const [u, v, normal] = slice.axes, q = slice.quantum_m, o = slice.origin_m;
    const [x0, y0, x1, y1] = slice.bounds_q;
    const bounds = [o[u] + x0*q, o[v] + y0*q, o[u] + x1*q, o[v] + y1*q];
    const p = projection(width, height, bounds, null, {zoom: morphology ? 1.1 : 2.25, x: 0, y: 0});
    slice.rows.forEach((line, z) => [...line].forEach((material, x) => {
        rect(ctx, p, bounds[0]+x*q, bounds[1]+z*q, q, q, material === "0" ? "#222f25" :
            material === "2" ? "#707c72" : "#826647");
    }));
    if (morphology) {
        for (const [x,z] of morphology.corridor_q)
            rect(ctx,p,o[u]+x*q,o[v]+z*q,q,q,"#49695b");
        for (const room of morphology.rooms) {
            const [x,z] = room.center_q;
            const [px,py] = p.point(o[u]+x*q,o[v]+z*q);
            circle(ctx,px,py,5,"#d3ab6b","#152319");
        }
        for (const [x,z] of morphology.junctions_q) {
            const [px,py] = p.point(o[u]+x*q,o[v]+z*q);
            circle(ctx,px,py,3,"#8eebde","#152319");
        }
    }
    const sites = new Map();
    for (const ant of ants) {
        const at = ant.position_m;
        if (Math.floor((at[normal]-o[normal])/q+1e-9) !== slice.plane_q) continue;
        const key = `${at[u]},${at[v]}`;
        if (!sites.has(key)) sites.set(key, []);
        sites.get(key).push(ant);
    }
    for (const at of sites.values()) {
        const first = at[0];
        const [x,y] = p.point(first.position_m[u],first.position_m[v]);
        circle(ctx,x,y,at.length>1?8:first.stage==="Adult"?4:2,
            colors[first.stage === "Adult" ? first.caste.toLowerCase() : first.stage.toLowerCase()],"#122319");
        if (at.length>1) {
            ctx.font = "10px monospace";
            ctx.fillStyle = "#152019";
            ctx.textAlign = "center";
            ctx.fillText(String(at.length),x,y+3);
        }
    }
    scaleMark(ctx, width, height, p, "X east / Z north");
}
async function watchDelivery() {
    const delivery = firstDelivery(app.meta);
    if (!delivery || app.compare) return;
    if (app.playingDelivery) { stopPlay(); return; }
    stopPlay();
    const generation = app.playVersion;
    const options = {ant: delivery.ant, since_ms: Math.max(0, delivery.time_ms - 15 * MINUTE), until_ms: delivery.time_ms,
        cut_event: delivery.id, limit: 200};
    const [travel, food] = await Promise.all([
        world("events", {...options, group: "movement"}),
        world("events", {...options, group: "food"})
    ]);
    if (generation !== app.playVersion) return;
    const foodFrames = food.events.filter(e => e.actor === delivery.ant && ["FoodCollected", "FoodDelivered"].includes(e.kind));
    const frames = [...travel.events.filter(e => e.actor === delivery.ant), ...foodFrames]
        .sort((a, b) => BigInt(a.id) < BigInt(b.id) ? -1 : 1);
    if (travel.next_after || food.next_after || !frames.length || frames.at(-1).id !== delivery.id) {
        show(tr("Use Movement only to inspect this delivery. Its records do not fit the quick replay."));
        return;
    }
    show(tr("Delivery replay shows recorded steps from the preceding 15 simulated minutes at a slower speed."));
    app.selected = delivery.ant;
    $("ant-id").value = delivery.ant;
    inspect(false);
    app.location = null;
    app.map = {zoom: 1, x: 0, y: 0};
    app.playingDelivery = true;
    $("map").scrollIntoView({block: "nearest"});
    let index = 0;
    playFrames(async () => {
        const fact = frames[index++];
        preferView(fact.position_m);
        await seek(fact.time_ms, fact);
        return index < frames.length;
    }, 260);
}
function replayMode() {
    return $("replay-mode").value === "movement" ? "movement" : "outcomes";
}
function replaySettings() {
    const showSpeed = app.compare || $("replay-mode").value === "overview";
    $("speed").hidden = !showSpeed;
    put("replay-note", tr(showSpeed ? "Overview skips ahead in simulated time." :
        $("replay-mode").value === "scenes" ? "Pauses at major events and shows recorded care boundaries." :
        replayMode() === "movement" ? "Each recorded position is shown in commit order." :
            "Steps through key outcomes and movements. See Events for all records."));
}
async function stepEvent(direction, generation = null) {
    const mode = replayMode();
    const version = app.seekVersion, open = app.openVersion;
    const e = await world("adjacent", {...cut(), direction, mode, ant: app.follow ? app.selected : null});
    if (version !== app.seekVersion || open !== app.openVersion || (generation !== null && generation !== app.playVersion)) return false;
    if (!e) {
        if (generation === null) show(tr("No matching event in that direction."));
        return false;
    }
    show();
    if (e.actor && ["Moved", "BroodMoved", "AntBorn", "StageChanged", "SoilExcavated", "FoodCollected", "FoodDelivered"].includes(e.kind)) {
        preferView(e.position_m);
    }
    await seek(e.time_ms, e);
    if (app.selectedFact === e) {
        if (!$("event-panel").hidden) showEvent(e);
    }
    return true;
}
function togglePlay() {
    if (!app.meta) return;
    if (app.playback || app.restReplay) { stopPlay(); drawMap(); return; }
    const end = app.compare && app.reference ? Math.max(app.meta.end_ms, app.reference.end_ms) : app.meta.end_ms;
    const inRealOrder = !app.compare && $("replay-mode").value !== "overview";
    if (app.time >= end) {
        app.time = 0;
        app.selectedFact = null;
        ++app.seekVersion;
    }
    if (!app.compare && $("replay-mode").value === "scenes") {
        const marks = app.meta.milestones.filter(m => m.time_ms>app.time || (m.time_ms===app.time && app.selectedFact &&
            BigInt(m.id)>BigInt(app.selectedFact.id)));
        let frames = [];
        playFrames(async generation => {
            if (!frames.length) {
                if (!marks.length) { await seek(end); return false; }
                const event = await world("event",{id:marks.shift().id});
                frames = (await actionBoundaries(event)).filter(e => e.time_ms>=app.time);
            }
            if (generation!==app.playVersion) return false;
            const fact = frames.shift();
            if (!fact) return true;
            preferView(fact.position_m);
            await seek(fact.time_ms,fact);
            if (generation===app.playVersion && app.selectedFact===fact && !$('event-panel').hidden) showEvent(fact);
            return true;
        },1000);
        return;
    }
    let previous = performance.now();
    playFrames(async generation => {
        if (inRealOrder) return stepEvent("next", generation);
        const now = performance.now();
        const next = app.time + Number($("speed").value) * DAY * (now - previous) / 1000;
        previous = now;
        await seek(next);
        return app.time < end;
    }, inRealOrder ? 220 : 135);
}

function bind() {
    const safe = (action) => (...args) => Promise.resolve().then(() => action(...args)).catch(report);
    const click = (id, action) => $(id).addEventListener("click", safe(action));
    const change = (id, action) => $(id).addEventListener("change", safe(action));
    change("locale", () => setLanguage($("locale").value));
    change("body-envelopes", drawMap);
    change("archive", () => openArchive($("archive").value));
    change("archived-world", () => openArchive($("archive").value, $("archived-world").value));
    click("observe-tab", openArchiveView);
    click("compare-tab", async () => {
        if (!app.meta) return;
        setMode(true);
        await loadReference();
    });
    change("reference", () => loadReference());
    change("compare-markers", () => { if (app.reference) return updateComparison(); });
    change("reference-world", () => loadReference($("reference-world").value));
    click("individual-tab", () => inspect(false));
    click("events-tab", async () => { inspect(true); await loadEvents(false); });
    change("filter", () => loadEvents(false));
    change("event-range", () => loadEvents(false));
    click("more-events", () => loadEvents(true));
    $("ant-form").addEventListener("submit", safe(e => { e.preventDefault(); return selectAnt($("ant-id").value.trim()); }));
    click("follow", () => {
        app.follow = !app.follow && Boolean(app.selected);
        toggle("follow", app.follow);
        return seek(app.time, app.selectedFact);
    });
    click("surface-button", () => { setSection("surface"); drawMap(); });
    click("nest-button", () => { setSection("nest"); drawMap(); });
    click("slice-button", () => {
        setSection("slice");
        const selected = app.state?.ants.find(a => a.id === app.selected);
        if (selected && selected.position_m[1] < planeSurface()) {
            preferView(selected.position_m);
            return seek(app.time, app.selectedFact);
        }
        drawMap();
    });
    change("nest-scale", () => { nestView.zoom = 1; nestView.x = nestView.y = 0; nestView.focus = null; drawMap(); });
    change("nest-transparent", () => drawMap());
    $("nest-depth").addEventListener("input", () => drawMap());
    change("axis", () => { app.location = null; app.layer = null; return seek(app.time, app.selectedFact); });
    change("clearance", () => seek(app.time, app.selectedFact));
    $("layer").addEventListener("input", safe(() => { app.location = null; app.layer = Number($("layer").value); return seek(app.time, app.selectedFact); }));
    click("back", () => { stopPlay(); return seek(app.time - DAY); });
    click("next", () => { stopPlay(); return seek(app.time + DAY); });
    click("play", togglePlay);
    click("watch-delivery", watchDelivery);
    click("compare-play", togglePlay);
    change("replay-mode", () => { stopPlay(); replaySettings(); });
    click("previous-event", () => { stopPlay(); return stepEvent("previous"); });
    click("next-event", () => { stopPlay(); return stepEvent("next"); });
    $("day-time").addEventListener("input", safe(() => {
        stopPlay();
        return seek(Math.floor(app.time / DAY) * DAY + Number($("day-time").value));
    }));
    for (const id of ["time", "compare-time"]) $(id).addEventListener("input", safe(() => { stopPlay(); return seek(Number($(id).value)); }));
    change("chart-series", dashboard);
    const zoom = factor => {
        const camera = app.section === "nest" ? nestView : app.map;
        camera.zoom = Math.max(.25, Math.min(64, camera.zoom * factor));
        drawMap();
    };
    click("zoom-in", () => zoom(1.25));
    click("zoom-out", () => zoom(.8));
    click("reset-map", () => { resetNestCamera(); app.map = {zoom: 1, x: 0, y: 0}; drawMap(); });
    click("show-occupants", () => showLocation());
    click("show-largest", () => { if (app.visibleSummary) { stopPlay(); showLocation(app.visibleSummary); } });
    click("close-location", () => { app.location = null; renderLocation(); });
    const map = $("map");
    map.addEventListener("wheel", e => { e.preventDefault(); zoom(e.deltaY > 0 ? .9 : 1.12); }, {passive: false});
    map.addEventListener("pointerdown", e => {
        const camera = app.section === "nest" ? nestView : app.map;
        app.drag = {x: e.clientX, y: e.clientY, left: camera.x, top: camera.y, yaw: camera.yaw,
            pitch: camera.pitch, pan: e.shiftKey, moved: false};
        map.setPointerCapture(e.pointerId);
    });
    map.addEventListener("pointermove", e => {
        const d = app.drag;
        if (!d) return;
        const dx = e.clientX - d.x, dy = e.clientY - d.y;
        if (d.moved || Math.abs(dx) + Math.abs(dy) > 5) {
            d.moved = true;
            const perspective = app.section === "nest";
            const camera = perspective ? nestView : app.map;
            if (perspective && !d.pan) {
                camera.yaw = d.yaw + dx * .012;
                camera.pitch = Math.max(.12, Math.min(1.54, d.pitch + dy * .012));
            } else { camera.x = d.left + dx; camera.y = d.top + dy; }
            drawMap();
        }
    });
    map.addEventListener("pointerup", safe(e => {
        const d = app.drag;
        app.drag = null;
        if (!d || d.moved) return;
        const rect = map.getBoundingClientRect();
        const matches = app.hits.map(hit => ({...hit, distance: Math.hypot(hit.x - (e.clientX - rect.left), hit.y - (e.clientY - rect.top))}))
            .filter(hit => hit.distance < hit.radius).sort((a, b) => a.distance - b.distance);
        const closest = matches[0];
        if (app.section === "nest" && matches.length > 1) {
            return showLocation({...closest, ants: matches.flatMap(hit => hit.ants)});
        }
        if (closest?.ants.length > 1) {
            stopPlay();
            showLocation(closest);
        } else if (closest) return selectAnt(closest.id);
    }));
    map.addEventListener("pointercancel", () => { app.drag = null; });
    map.addEventListener("keydown", e => {
        if (app.section !== "nest" || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "+", "-"].includes(e.key)) return;
        e.preventDefault();
        if (e.key === "+" || e.key === "-") return zoom(e.key === "+" ? 1.15 : .87);
        if (e.key === "ArrowLeft" || e.key === "ArrowRight") nestView.yaw += e.key === "ArrowLeft" ? -.12 : .12;
        else nestView.pitch = Math.max(.12, Math.min(1.54, nestView.pitch + (e.key === "ArrowUp" ? .12 : -.12)));
        drawMap();
    });
    new ResizeObserver(draw).observe(document.querySelector("main"));
}

function showEmptyCatalog() {
    put("title", tr("No archives available"));
    put("subtitle", tr("Import a Core ZIP or SQLite backup with python -m op0 import PATH, then restart this viewer."));
}

async function openArchiveView() {
    if (app.live) leaveLiveView();
    if (app.meta) { stopPlay(); setMode(false); await seek(app.time); return; }
    const version = ++app.openVersion;
    const active = $("archive").value;
    app.catalog = await api("catalog");
    if (app.live || version !== app.openVersion) return;
    if (!app.catalog.length) { showEmptyCatalog(); return; }
    setOptions($("archive"), app.catalog, active);
    await openArchive($("archive").value || app.catalog[0].key);
}

async function start() {
    captureStaticStrings();
    await setLanguage(preference(), false);
    put("title", tr("Opening AntWorld"));
    put("subtitle", tr("Checking the local archive catalogue…"));
    put("time-note", day(0));
    put("space-caption", tr("Committed positions and ordered geometry edits"));
    stopPlay();
    bind();
    bindLive();
    const live = await api("live/status");
    $("live-tab").hidden = !live.enabled;
    if (live.enabled) await openLiveView();
    else await openArchiveView();
}
start().catch(report);
