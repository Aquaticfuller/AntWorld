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
    map: {zoom: 1, x: 0, y: 0}, drag: null, activity: null, activityVersion: 0, playVersion: 0,
    eventAfter: null, eventListVersion: 0, seekVersion: 0, openVersion: 0, playback: null,
    compare: false, reference: null, referenceSeries: [], compareVersion: 0, referenceVersion: 0
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
    const dynamic = new Set(["space-caption", "queen-mass", "play", "compare-play"]);
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
        "Queen died": "Queen death"};
    $("milestones").replaceChildren(...meta.milestones.filter(m => labels[m.label]).map(m =>
        button(labels[m.label], () => jumpEvent(m.id, m.ant).catch(report), tr(m.label) + " · " + exactTime(m.time_ms))));
    setOptions($("reference"), app.catalog.filter(e => e.key !== $("archive").value));
    const prior = app.catalog.find(e => e.title === "Before the feeding correction" && e.key !== $("archive").value);
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
    setSection(meta.settings.geometry && meta.initial_queens.length ? "slice" : "surface");
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
    toggle("observe-tab", !compare);
    replaySettings();
    if (!compare) requestAnimationFrame(draw);
}

async function seek(ms, exact = null) {
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

function updateState(state) {
    const p = state.population;
    put("queen-state", tr(p.queens_alive.length ? "Alive" : "Absent"));
    const s = state.queens_last_sample;
    put("queen-mass", s ? tr("{water} · sampled on {day}", {water: withUnit(s.hydration_ug, "µg water"), day: day(s.time_ms)}) :
        tr(p.queens_alive.length ? "Physiology unavailable at this cut" : "No live queen at this cut"));
    for (const name of ["workers", "eggs", "larvae", "pupae"]) put(name, p[name].toLocaleString(language));
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
        FoundingRation: "Maternal ration", SoilExcavated: "Soil excavated", SoilDropped: "Soil placed",
        RecruitmentObserved: "Scout cue sensed", RecruitmentActivated: "Recruitment activated"};
    if (e.kind === "StageChanged") return tr({Larva: "Hatched", Pupa: "Pupated", Adult: "Eclosed"}[e.stage] || e.stage);
    if (e.action) return tr(e.action.act) + " · " + tr(e.action.phase);
    return tr(labels[e.kind] || (Object.hasOwn(messages, e.kind) ? e.kind : e.kind.replace(/([a-z])([A-Z])/g, "$1 $2")));
}
function eventButton(e, extra = false) {
    const b = button("", () => jumpEvent(e.id).catch(report));
    b.className = "event-row";
    b.dataset.event = e.id;
    b.append(node("span", eventLabel(e)), node("span", day(e.time_ms)));
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
    panel.replaceChildren(title, keyValues([["Mother", mother], ["Born", ant.born_ms == null ? null : day(ant.born_ms)],
        ["Last position at cut", coords(ant.position_m)], ...(ant.died_ms == null ? [] : [["Died", exactTime(ant.died_ms)], ["Cause", tr(ant.death_cause)]])]),
        node("h4", s ? tr("Physiology · sample on {day}", {day: day(s.time_ms)}) : tr("Physiology · not recorded"), "subhead"));
    if (s) panel.append(keyValues([["Body energy", withUnit(s.energy_nj, "nJ")], ["Body water", withUnit(s.hydration_ug, "µg")],
        ["Tissue protein", withUnit(s.tissue_protein_ug, "µg")], ["Crop C/P/W/other", mass(s.crop_ug)],
        ["Carried C/P/W/other", mass(s.carried_ug)]]));
    panel.append(node("h4", tr("Lifetime · includes later recorded events"), "subhead"),
        ...ant.life_events.map(e => eventButton(e)), node("h4", tr("Recent facts through cursor"), "subhead"),
        ...ant.activity.slice(0, 12).map(e => eventButton(e, true)));
    if (!ant.activity.length) panel.append(node("p", tr("No matching actions by this time."), "muted"));
}
function inspect(events) {
    $("individual-panel").hidden = events;
    $("event-panel").hidden = !events;
    toggle("events-tab", events);
    toggle("individual-tab", !events);
}
async function selectAnt(id) {
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
        ["Simulation time", exactTime(e.time_ms)], ["Actor", antLink(e.actor)], ["Participant", antLink(e.related)],
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
    stopPlay();
    const version = app.openVersion;
    const e = await world("event", {id});
    if (version !== app.openVersion) return;
    if (ant) {
        app.selected = ant;
        $("ant-id").value = ant;
    }
    if (["SoilExcavated", "SoilFilled"].includes(e.kind) && e.geometry_edits?.length) {
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
    $("plane-controls").hidden = section === "surface" || !app.meta?.settings.geometry;
    $("clearance-control").hidden = $("plane-controls").hidden;
    $("view-controls").hidden = !$("plane-controls").hidden;
}
function preferView(p) {
    if (!p || !app.meta) return;
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
function projection(width, height, bounds) {
    const [u0, v0, u1, v1] = bounds;
    const unit = Math.max(1, Math.min((width - 68) / (u1 - u0 || .01), (height - 58) / (v1 - v0 || .01))) * app.map.zoom;
    const dx = width / 2 + app.map.x - (u0 + u1) / 2 * unit;
    const dy = height / 2 + app.map.y + (v0 + v1) / 2 * unit;
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
function drawOccupants(ctx, visible, point) {
    const markers = new Map();
    for (const ant of visible) {
        const [x, y] = point(ant.position_m);
        // Only merge coincident projections. Membership retains original 3D coordinates.
        const key = x + "," + y;
        if (!markers.has(key)) markers.set(key, {x, y, ants: []});
        markers.get(key).ants.push(ant);
    }
    app.hits = [];
    for (const {x, y, ants} of markers.values()) {
        if (ants.length === 1) {
            markerShape(ctx, ants[0], x, y, ants[0].id === app.selected);
            app.hits.push({id: ants[0].id, x, y, radius: 11, ants});
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
function renderLocation() {
    $("location").hidden = !app.location;
    if (!app.location) return;
    const ants = app.location.all ? app.visible :
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
    app.location = hit ? {axes, at: [hit.ants[0].position_m[axes[0]], hit.ants[0].position_m[axes[1]]]} : {all: true};
    renderLocation();
}
function drawMap() {
    if (app.compare || !app.state) return;
    const canvas = canvasContext($("map"));
    if (!canvas) return;
    const {ctx, width, height} = canvas;
    const state = app.state, surface = app.meta.surface, slice = app.geometry?.slice;
    const underground = app.section === "slice" && slice;
    const terrain = app.meta.settings.geometry, surfaceY = planeSurface();
    ctx.fillStyle = underground ? "#152019" : "#15241a";
    ctx.fillRect(0, 0, width, height);
    let p, fits, point, orientation;
    if (underground) {
        const [u, v, n] = slice.axes, q = slice.quantum_m, o = slice.origin_m;
        const [x0, y0, x1, y1] = slice.bounds_q;
        const bounds = [o[u] + x0 * q, o[v] + y0 * q, o[u] + x1 * q, o[v] + y1 * q];
        p = projection(width, height, bounds);
        point = a => p.point(a[u], a[v]);
        fits = a => Math.floor((a[n] - o[n]) / q + 1e-9) === slice.plane_q;
        orientation = slice.axis === "z" ? "X east / Y up" : slice.axis === "x" ? "Z north / Y up" : "X east / Z north";
        for (const [row, cells] of slice.rows.entries()) {
            let start = 0;
            while (start < cells.length) {
                let end = start + 1;
                while (cells[end] === cells[start]) end++;
                const shade = cells[start] === "0" ? "#222f25" : cells[start] === "2" ? "#707c72" :
                    (row % 3 === 0 ? "#917451" : "#826647");
                rect(ctx, p, bounds[0] + start * q, bounds[1] + row * q, (end - start) * q, q, shade);
                start = end;
            }
        }
        for (const [row, cells] of (slice.unloaded_body_clear || []).entries()) {
            for (let i = 0; i < cells.length; i++) {
                if (cells[i] === "1") circle(ctx, ...p.point(bounds[0] + i*q, bounds[1] + row*q),
                    Math.min(2.5, p.unit*q/5), "#91be80");
            }
        }
        put("space-caption", tr("Quantized material section · {count} committed edits", {count: app.geometry.revision}) +
            (app.geometry.cropped ? " · " + tr("Section cropped to first 480 quanta on each axis") : ""));
        legend("map-legend", [["soil", "Soil"], ["rock", "Rock"], ["void", "Void"], ["queen", "Queen"], ["egg", "Eggs"],
            ["larva", "Larvae"], ["pupa", "Pupae"], ["worker", "Worker"], ["entrance", "Recent movement points"],
            ...(app.path.length ? [["trace", "Selected individual's recorded positions"]] : []),
            ...(slice.unloaded_body_clear ? [["entrance", "Unloaded body fits here"]] : [])]);
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
        p = projection(width, height, bounds);
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
            ctx.fillStyle = inStock ? colors.food : "#52635a";
            ctx.fillRect(x-4, y-4, 8, 8);
            ctx.font = '11px "Cascadia Mono", "Microsoft YaHei", monospace';
            ctx.fillStyle = "#d3e6d5";
            ctx.fillText(tr("Source #{id}", {id: s.id}) + (inStock ? "" : " · " + tr("depleted")), x + 8, y - 5);
        }
        put("space-caption", tr("Surface positions at this cut") + " · " +
            tr(openings.length ? "terrain openings from geometry" : "flat grid where recorded"));
        legend("map-legend", [["entrance", "Opening / surface nest"], ["food", "Source"], ["worker", "Worker"],
            ["entrance", "Recent movement points"], ...(app.path.length ? [["trace", "Selected individual's recorded positions"]] : [])]);
    }
    const motion = app.recentMotion;
    const trail = (motion?.points || []).filter(move => fits(move.position_m));
    for (const move of trail) circle(ctx, ...point(move.position_m), 1.8, "#93d4b07a");
    for (const move of app.path) {
        if (fits(move.position_m)) circle(ctx, ...point(move.position_m), 2, "#ad9ce18a");
    }
    const visible = state.ants.filter(a => fits(a.position_m));
    app.visible = visible;
    drawOccupants(ctx, visible, point);
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
    if (trail.length) notes.push(tr("{count} recorded movement points in this view over the last 5 simulated minutes.", {count: trail.length}));
    if (motion?.truncated) notes.push(tr("Recent movement display capped at 144 points."));
    put("map-detail", notes.join(" "));
    renderLocation();
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

function graph(id, tracks, end, stamp, legendId = null) {
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
    ctx.fillText(day(0), low, height - 3);
    ctx.textAlign = "right";
    ctx.fillText(day(end), width - 11, height - 3);
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
    const [data, lists] = await Promise.all([api("compare", {left: app.meta.key, right: app.reference.key, time_ms: app.time}),
        Promise.all([app.meta, app.reference].map(m => {
            const low = Math.floor(Math.min(app.time, m.end_ms) / DAY) * DAY;
            return api("world/" + m.key + "/events", {group: "highlights", since_ms: low, until_ms: Math.min(low + DAY - 1, m.end_ms), limit: 5});
        }))]);
    if (!app.compare || version !== app.compareVersion) return;
    const differing = Object.values(data.settings).filter(s => s.status === "different").length;
    const unknown = Object.values(data.settings).filter(s => s.status === "unknown").length;
    $("compare-status").replaceChildren(node("p", tr(
        "{different} recorded input differences · {unknown} unknown input fields. Compare colony outcomes and roles. Ant IDs remain local to each archive.",
        {different: differing, unknown}), differing || unknown ? "different" : "matching"));
    const cards = data.worlds.map(({world, state, cohort, outside_record}, i) => {
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
        box.append(node("h4", tr("Committed facts on this day"), "subhead"));
        for (const event of lists[i].events) {
            const detail = node("p", "#" + event.id + " · " + eventLabel(event) + " · " + day(event.time_ms), "compare-fact");
            box.append(detail);
        }
        if (!lists[i].events.length) box.append(node("p", tr("No matching facts on this day."), "muted"));
        return box;
    });
    $("compare-cards").replaceChildren(...cards);
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
    for (const id of ["play", "compare-play"]) {
        put(id, tr("▶ Play"));
        $(id).setAttribute("aria-pressed", "false");
    }
}
function replayMode() {
    return $("replay-mode").value === "overview" ? "outcomes" : $("replay-mode").value;
}
function replaySettings() {
    const showSpeed = app.compare || $("replay-mode").value === "overview";
    $("speed").hidden = !showSpeed;
    put("replay-note", tr(showSpeed ? "Overview skips ahead in simulated time." :
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
    if (app.playback) { stopPlay(); return; }
    const end = app.compare && app.reference ? Math.max(app.meta.end_ms, app.reference.end_ms) : app.meta.end_ms;
    const inRealOrder = !app.compare && $("replay-mode").value !== "overview";
    const generation = ++app.playVersion;
    if (app.time >= end) {
        app.time = 0;
        app.selectedFact = null;
        ++app.seekVersion;
    }
    for (const id of ["play", "compare-play"]) {
        put(id, tr("Ⅱ Pause"));
        $(id).setAttribute("aria-pressed", "true");
    }
    let busy = false, previous = performance.now();
    app.playback = setInterval(async () => {
        if (busy || generation !== app.playVersion) return;
        busy = true;
        const now = performance.now();
        const next = app.time + Number($("speed").value) * DAY * (now - previous) / 1000;
        previous = now;
        try {
            if (inRealOrder) {
                if (!await stepEvent("next", generation) && generation === app.playVersion) stopPlay();
            } else {
                await seek(next);
                if (app.time >= end && generation === app.playVersion) stopPlay();
            }
        }
        catch (err) { stopPlay(); report(err); }
        finally { busy = false; }
    }, inRealOrder ? 220 : 135);
}

function bind() {
    const safe = (action) => (...args) => Promise.resolve().then(() => action(...args)).catch(report);
    const click = (id, action) => $(id).addEventListener("click", safe(action));
    const change = (id, action) => $(id).addEventListener("change", safe(action));
    change("locale", () => setLanguage($("locale").value));
    change("archive", () => openArchive($("archive").value));
    change("archived-world", () => openArchive($("archive").value, $("archived-world").value));
    click("observe-tab", () => { if (app.meta) { stopPlay(); setMode(false); return seek(app.time); } });
    click("compare-tab", async () => {
        if (!app.meta) return;
        setMode(true);
        await loadReference();
    });
    change("reference", () => loadReference());
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
    click("slice-button", () => {
        const selected = app.state?.ants.find(a => a.id === app.selected);
        if (selected && selected.position_m[1] < planeSurface()) {
            preferView(selected.position_m);
            return seek(app.time, app.selectedFact);
        }
        setSection("slice");
        drawMap();
    });
    change("axis", () => { app.location = null; app.layer = null; return seek(app.time, app.selectedFact); });
    change("clearance", () => seek(app.time, app.selectedFact));
    $("layer").addEventListener("input", safe(() => { app.location = null; app.layer = Number($("layer").value); return seek(app.time, app.selectedFact); }));
    click("back", () => { stopPlay(); return seek(app.time - DAY); });
    click("next", () => { stopPlay(); return seek(app.time + DAY); });
    click("play", togglePlay);
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
    const zoom = factor => { app.map.zoom = Math.max(.25, Math.min(64, app.map.zoom * factor)); drawMap(); };
    click("zoom-in", () => zoom(1.25));
    click("zoom-out", () => zoom(.8));
    click("reset-map", () => { app.map = {zoom: 1, x: 0, y: 0}; drawMap(); });
    click("show-occupants", () => showLocation());
    click("show-largest", () => { if (app.visibleSummary) { stopPlay(); showLocation(app.visibleSummary); } });
    click("close-location", () => { app.location = null; renderLocation(); });
    const map = $("map");
    map.addEventListener("wheel", e => { e.preventDefault(); zoom(e.deltaY > 0 ? .9 : 1.12); }, {passive: false});
    map.addEventListener("pointerdown", e => {
        app.drag = {x: e.clientX, y: e.clientY, left: app.map.x, top: app.map.y, moved: false};
        map.setPointerCapture(e.pointerId);
    });
    map.addEventListener("pointermove", e => {
        const d = app.drag;
        if (!d) return;
        const dx = e.clientX - d.x, dy = e.clientY - d.y;
        if (d.moved || Math.abs(dx) + Math.abs(dy) > 5) {
            d.moved = true; app.map.x = d.left + dx; app.map.y = d.top + dy; drawMap();
        }
    });
    map.addEventListener("pointerup", safe(e => {
        const d = app.drag;
        app.drag = null;
        if (!d || d.moved) return;
        const rect = map.getBoundingClientRect();
        const closest = app.hits.map(hit => ({...hit, distance: Math.hypot(hit.x - (e.clientX - rect.left), hit.y - (e.clientY - rect.top))}))
            .filter(hit => hit.distance < hit.radius).sort((a, b) => a.distance - b.distance)[0];
        if (closest?.ants.length > 1) {
            stopPlay();
            showLocation(closest);
        } else if (closest) return selectAnt(closest.id);
    }));
    map.addEventListener("pointercancel", () => { app.drag = null; });
    new ResizeObserver(draw).observe(document.querySelector("main"));
}

function showEmptyCatalog() {
    put("title", tr("No archives available"));
    put("subtitle", tr("Import a Core ZIP or SQLite backup with python -m op0 import PATH, then restart this viewer."));
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
    app.catalog = await api("catalog");
    if (!app.catalog.length) {
        showEmptyCatalog();
        return;
    }
    setOptions($("archive"), app.catalog);
    await openArchive(app.catalog[0].key);
}
start().catch(report);
