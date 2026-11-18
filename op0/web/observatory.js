"use strict";

const landmarkLabels = {...liveMilestones, nursing: "First maternal feeding", trophallaxis: "First food exchange",
    "queen-death": "Queen died"};
const observatory = {epoch: null, cursor: null, selected: null, filled: false, busy: false, last: -Infinity, generation: 0, language: null};

function updatePresets() {
    const active = app.live && liveView.state?.observatory_available;
    $("observatory-presets").hidden = !active;
    for (const control of $("observatory-presets").querySelectorAll("button")) control.disabled = liveView.busy;
}

function renderChronicle(data) {
    const get = key => data.landmarks[key];
    const names = ["egg", "hatch", "nursing", "worker", "exit", "delivery", "trophallaxis", "excavation"];
    if (get("queen-death")) names.push("queen-death");
    $("chronicle-steps").replaceChildren(...names.map(key => {
        const fact = get(key), option = $("live-target").querySelector(`option[value="${key}"]`);
        const canSeek = !fact && option && !option.disabled && liveView.state.ants.some(ant => ant.stage !== "Dead");
        const action = button("", () => {
            if (option && !option.disabled) $("live-target").value = key;
            if (fact) return showLiveFact(fact.id).catch(report);
            return seekLiveEvent(key, "first").catch(report);
        });
        action.disabled = !fact && !canSeek;
        action.classList.toggle("reached", Boolean(fact));
        action.dataset.landmark = key;
        action.append(node("strong", tr(landmarkLabels[key])), node("small", fact ? duration(fact.time_ms) :
            tr(canSeek ? "Fast-forward" : "Not yet observed")));
        return action;
    }));
    const death = get("queen-death");
    put("chronicle-status", death ? tr("Queen died at {time} · {cause}", {time: duration(death.time_ms), cause: tr(death.death_cause)}) :
        tr(data.through === data.cursor ? "From committed events" : "Reading earlier committed events…"));
}

function updateObservatory() {
    const live = liveView.state;
    const enabled = app.live && Boolean(live?.habitat);
    $("live-chronicle").hidden = !enabled;
    $("live-life").hidden = !app.live || !live?.world_id || !app.selected;
    if (!app.live || !live?.world_id) return;
    const reset = observatory.epoch !== live.epoch, actor = app.selected;
    if (reset) {
        observatory.generation++;
        Object.assign(observatory, {epoch: live.epoch, cursor: null, selected: null, busy: false, filled: false, last: -Infinity});
        $("chronicle-steps").replaceChildren();
        $("live-life-events").replaceChildren();
    }
    if (observatory.selected !== actor) $("live-life-events").replaceChildren();
    const sameView = observatory.selected === actor && observatory.language === language;
    if (observatory.busy || (sameView && ((observatory.filled && observatory.cursor === live.cursor) ||
        performance.now() - observatory.last < 400))) return;
    const epoch = live.epoch, generation = observatory.generation;
    observatory.busy = true;
    observatory.last = performance.now();
    (async () => {
        const data = await api("live/chronicle", {epoch});
        if (!app.live || observatory.generation !== generation || epoch !== liveView.epoch) return;
        if (enabled) renderChronicle(data);
        if (actor && actor === app.selected) {
            const life = await api("live/life", {epoch, id: actor});
            if (!app.live || observatory.generation !== generation || actor !== app.selected) return;
            const rows = [...life.lifecycle, ...life.recent_activity];
            const facts = [...new Map(rows.map(e => [e.id, e])).values()].sort((a, b) => a.time_ms - b.time_ms ||
                (BigInt(a.id) < BigInt(b.id) ? -1 : 1));
            $("live-life-events").replaceChildren(...facts.map(e => eventButton(e, true)));
            if (!facts.length || life.through !== life.cursor) $("live-life-events").append(node("p",
                tr(life.through !== life.cursor ? "Reading earlier committed events…" : "No recorded events for this individual."), "muted"));
        }
        observatory.cursor = data.cursor;
        observatory.filled = data.through === data.cursor;
        observatory.selected = actor;
        observatory.language = language;
    })().catch(error => {
        if (app.live && epoch === liveView.epoch && observatory.generation === generation) {
            put("chronicle-status", tr(error.message));
        }
    }).finally(() => { if (observatory.generation === generation) observatory.busy = false; });
}

function bindObservatory() {
    for (const control of $("observatory-presets").querySelectorAll("button")) {
        control.addEventListener("click", () => {
            if (liveView.state?.dirty && !confirm(tr("Create a colony and replace the current unsaved progress?"))) return;
            liveCommand("observatory", {preset: control.dataset.preset}).catch(report);
        });
    }
}
