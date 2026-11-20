// Drive a real Chromium browser through its local testing protocol. Node 22+.
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {mkdtemp, mkdir, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {setTimeout as sleep} from "node:timers/promises";

const [browser, host = "http://127.0.0.1:8765", output = "out/op0-browser", mode] = process.argv.slice(2);
if (!browser) throw Error("Usage: node op0/tests/browser_smoke.mjs <chromium> [local viewer URL] [output]");
const cache = await mkdtemp(join(tmpdir(), "antworld-op0-browser-"));
await mkdir(output, {recursive: true});
const processHandle = spawn(browser, ["--headless=new", "--disable-background-networking", "--no-first-run", "--disable-spell-checking",
    "--no-default-browser-check", "--remote-debugging-port=0", "--user-data-dir=" + cache,
    "--window-size=1540,1160", "--disable-dev-shm-usage",
    ...(process.platform === "win32" && ["nursery", "ecology", "habitat", "m1", "m2", "overhaul", "founder-access", "m1-witnesses", "m1-soak"].includes(mode) ?
        ["--disable-component-update", "--disable-gpu-shader-disk-cache", "--disk-cache-size=1"] : []),
    ...(process.getuid?.() === 0 ? ["--no-sandbox"] : []), "about:blank"],
    {windowsHide: true, stdio: ["ignore", "ignore", "pipe"]});
let browserError = "", exitMessage = "";
processHandle.on("error", err => { exitMessage = String(err); });
processHandle.stderr.on("data", message => { browserError = (browserError + message).slice(-3000); });
const exited = new Promise(resolveExit => processHandle.once("close", resolveExit));
let socket, sequence = 0;
const pending = new Map(), exceptions = [], dialogs = [], result = {};
const clock = () => performance.now();

async function wait(read, name, timeout = 110_000) {
    const started = clock();
    while (clock() - started < timeout) {
        if (exitMessage) throw Error(exitMessage);
        const value = await read();
        if (value) return value;
        await sleep(60);
    }
    throw Error("Timed out: " + name + "\n" + browserError);
}
function send(method, params = {}) {
    return new Promise((resolveRequest, reject) => {
        const id = ++sequence;
        const timer = setTimeout(() => { pending.delete(id); reject(Error("Protocol timeout: " + method)); }, 120_000);
        pending.set(id, message => {
            clearTimeout(timer);
            if (message.error) reject(Error(message.error.message));
            else resolveRequest(message.result);
        });
        socket.send(JSON.stringify({id, method, params}));
    });
}
async function evaluate(expression) {
    const response = await send("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true});
    if (response.exceptionDetails) throw Error("Evaluation failed: " + expression + "\n" +
        (response.exceptionDetails.exception?.description || response.exceptionDetails.text));
    return response.result.value;
}
async function click(selector) {
    const [x, y] = await evaluate("(() => { const e = document.querySelector(" + JSON.stringify(selector) +
        "); if (!e || e.hidden) throw Error('Missing control'); e.scrollIntoView({block:'center', inline:'center'});" +
        " const b = e.getBoundingClientRect(); return [b.left + b.width/2, b.top + b.height/2]; })()");
    await mouse(x, y);
}
async function clickMap(query) {
    const position = await evaluate("(() => { const map = $('map'); map.scrollIntoView({block:'center'});" +
        " const b = map.getBoundingClientRect(), a = app.hits.find(" + query + ");" +
        " return a ? [b.left + a.x, b.top + a.y] : null; })()");
    assert.ok(position, "Requested real position has a map marker");
    await mouse(...position);
}
async function mouse(x, y) {
    await send("Input.dispatchMouseEvent", {type: "mousePressed", x, y, button: "left", clickCount: 1});
    await send("Input.dispatchMouseEvent", {type: "mouseReleased", x, y, button: "left", clickCount: 1});
}
async function select(id, value) {
    return evaluate("(() => { const e = $(" + JSON.stringify(id) + "); e.value = " + JSON.stringify(value) +
        "; e.dispatchEvent(new Event('change')); return e.value; })()");
}
async function screenshot(name, includeHours = false, format = "png") {
    await evaluate(name.startsWith("m1-") ?
        "scrollTo(0, Math.max(0, $('space-title').getBoundingClientRect().top + scrollY - 315))" : includeHours ?
        "scrollTo(0, Math.max(0, $('hour-bins').getBoundingClientRect().bottom + scrollY - innerHeight + 45))" : "scrollTo(0, 0)");
    await sleep(250);
    const frame = await send("Page.captureScreenshot", {format, captureBeyondViewport: false,
        ...(format === "webp" ? {quality:94} : {})});
    await writeFile(join(output, name + "." + format), Buffer.from(frame.data, "base64"));
}
async function opened() {
    await wait(async () => {
        try {
            return await evaluate('document.documentElement?.dataset.ready === "true" && typeof app !== "undefined" && !!app.state');
        } catch (error) {
            // A navigation can replace the document between polling and evaluation.
            if (/Execution context was destroyed|Cannot find context with specified id/.test(error.message)) return false;
            throw error;
        }
    }, "Rendered world");
}

async function r0World() {
    assert.equal(await evaluate("app.meta.settings.physics"), 32);
    const mark = await evaluate("app.meta.milestones.find(m=>m.label==='Resting site with 10 or more workers')");
    assert.ok(mark, "The colony developed at least ten workers before its recorded relocation");
    const started = clock();
    await evaluate("[...$('action-replays').children].find(e=>e.textContent==='Watch movement in an established nest').click()");
    await wait(() => evaluate("app.restReplay?.progress > 0"), "Recorded nest interaction in progress");
    const segment = await evaluate("app.restReplay");
    assert.equal(segment.start.actor, mark.ant);
    assert.equal(segment.completion.id, mark.id);
    assert.notDeepEqual(segment.move.position_m, segment.start.position_m);
    assert.ok(segment.start.time_ms < segment.completion.time_ms);
    await screenshot("r0-recorded-rest-movement");
    await wait(() => evaluate(`app.selectedFact?.id === ${JSON.stringify(mark.id)} && !app.restReplay`), "Verified end of nest movement");
    result.rest_replay_ms = Math.round(clock()-started);
    assert.equal(await evaluate("app.state.population.workers >= 10"), true);
    await click("#compare-tab");
    await wait(() => evaluate("document.querySelectorAll('.compare-nest').length === 2"), "Synchronized committed nest sections");
    assert.equal(await evaluate("app.reference.title"), "R0 · matched reference");
    assert.match(await evaluate("$('compare-cards').textContent"), /Physics 32.*Physics 29/s);
    await screenshot("r0-matched-nest-comparison");
    await evaluate("window.testOriginalCut = app.comparisonCut; window.testOriginalCut.key");
    const comparisonReads = "performance.getEntriesByType('resource').filter(r => new URL(r.name).pathname === '/api/v1/compare').length";
    const readCount = await evaluate(comparisonReads);
    await select("locale", "zh-CN");
    await wait(() => evaluate("document.documentElement.lang === 'zh-CN' && document.querySelectorAll('.compare-nest').length === 2 && $('compare-cards').textContent.includes('\\u914d\\u5bf9\\u5bf9\\u7167')"),
        "Localized comparison");
    assert.match(await evaluate("$('compare-cards').textContent"), /\u914d\u5bf9\u5bf9\u7167/);
    assert.equal(await evaluate("app.comparisonCut === window.testOriginalCut"), true);
    assert.equal(await evaluate(comparisonReads), readCount);
    await evaluate("delete window.testOriginalCut");
    assert.deepEqual(exceptions, []);
    result.segment = {start: segment.start.id, end: segment.completion.id, actor: mark.ant, time_ms: mark.time_ms};
    result.status = "PASS";
    await writeFile(join(output, "browser-receipt.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify(result, null, 2));
}
async function r0r1World() {
    assert.equal(await evaluate("app.meta.settings.physics"), 33);
    assert.equal(await evaluate("app.state.population.workers"), 0);
    const mark = await evaluate("app.meta.milestones.find(m => m.label === 'Resting site with 10 or more workers')");
    assert.ok(mark, "Naturally developed workers have a late movement record");
    await evaluate("[...$('action-replays').children].find(e => e.textContent === 'Watch movement in an established nest').click()");
    await wait(() => evaluate("app.restReplay?.move?.motion && app.restReplay.progress > 0"), "Native motor segment is playing");
    const segment = await evaluate("app.restReplay");
    assert.equal(segment.start.time_ms, segment.move.motion.begins_ms);
    assert.equal(segment.completion.id, mark.id);
    assert.notDeepEqual(segment.start.position_m, segment.move.position_m);
    await screenshot("r0-r1-worker-motor");
    await wait(() => evaluate(`app.state.cursor === ${JSON.stringify(mark.id)} && !app.restReplay &&
        $('event-detail').dataset.event === ${JSON.stringify(mark.id)}`), "Return to the committed motor endpoint");
    await evaluate(`document.querySelector("#milestones button[title^='First food delivered']").click()`);
    await wait(() => evaluate("app.selectedFact?.kind === 'FoodDelivered'"), "Open the actual underground delivery");
    assert.ok(await evaluate("app.selectedFact.mass_ug.some(m => m > 0)"));
    result.motion = {archive:await evaluate("app.meta.archive_sha256"), actor:mark.ant,
        begin:segment.start.id, move:segment.move.id, end:mark.id, duration_ms:segment.move.motion.duration_ms};
    await evaluate("seek(90 * DAY)");
    await click("#compare-tab");
    const shaft = await evaluate("app.catalog.find(x => x.title === 'R0-r1 · shaft · reference').key");
    await select("reference", shaft);
    await wait(() => evaluate("app.reference?.title === 'R0-r1 · shaft · reference' && $('compare-cards').textContent.includes('Physics 32')"),
        "Compare naturally developed workers in matched nests");
    await screenshot("r0-r1-founding-comparison");

    await click("#observe-tab");
    await opened();
    result.excavation = {};
    for (const count of [50, 300]) {
        const title = `R0-r1 · ${count} workers · dig score`;
        const candidate = await evaluate(`app.catalog.find(x => x.title === ${JSON.stringify(title)}).key`);
        await select("archive", candidate);
        await wait(() => evaluate(`app.meta?.title === ${JSON.stringify(title)} && document.documentElement.dataset.ready === 'true'`),
            "Open a seeded excavation world");
        assert.equal(await evaluate("$('axis').value"), "y");
        assert.equal(await evaluate("app.state.population.workers"), count);
        const initial = await evaluate("app.state.net_removed_m3");
        await evaluate(`document.querySelector("#milestones button[title^='First excavation']").click()`);
        await wait(() => evaluate("app.selectedFact?.kind === 'SoilExcavated'"), "Show the first committed excavation");
        assert.ok(await evaluate("app.selectedFact.geometry_edits[0].volume_q3 > 0"));
        const firstCut = await evaluate("app.selectedFact.id");
        await evaluate("seek(DAY)");
        assert.ok(await evaluate("app.state.net_removed_m3") > initial);
        await click("#compare-tab");
        const refTitle = `R0-r1 · ${count} workers · random boundary`;
        const reference = await evaluate(`app.catalog.find(x => x.title === ${JSON.stringify(refTitle)}).key`);
        await select("reference", reference);
        await wait(() => evaluate(`app.reference?.title === ${JSON.stringify(refTitle)} && document.querySelectorAll('.compare-nest').length === 2 && $('compare-cards').textContent.includes('Wide room cores')`),
            "Render both soil histories and their measured chamber cores");
        result.excavation[count] = {archive:await evaluate("app.meta.archive_sha256"), first_cut:firstCut,
            net_mm3:await evaluate("app.state.net_removed_m3 * 1e9")};
        if (await evaluate("$('compare-markers').checked")) {
            const old = await evaluate("window.previousSection = document.querySelector('.compare-nest'); !!window.previousSection");
            assert.ok(old);
            await click("#compare-markers");
            await wait(() => evaluate("!$('compare-markers').checked && document.querySelector('.compare-nest') !== window.previousSection"),
                "Show edited terrain without overlapping ant badges");
        }
        await screenshot(`r0-r1-excavation-${count}`);
        await click("#observe-tab");
        await opened();
    }
    await select("locale", "zh-CN");
    await wait(() => evaluate("document.documentElement.lang === 'zh-CN'"), "Change the language without changing the world");
    assert.deepEqual(exceptions, []);
    result.status = "PASS";
    result.chromium = (await send("Browser.getVersion")).product;
    await writeFile(join(output, "r0-r1-browser-receipt.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify(result, null, 2));
}
async function timed(name, execute) {
    const start = clock();
    await execute();
    result[name] = +(clock() - start).toFixed(2);
}

async function microWorld() {
    assert.equal(await evaluate("$('title').textContent"),"MicroWorld · shaft");
    assert.equal(await evaluate("app.meta.settings.physics"),29);
    assert.equal(await evaluate("app.state.ants.length"),1);
    assert.equal(await evaluate("$('replay-mode').value"),"scenes");
    await click("#play");
    await wait(() => evaluate("app.selectedFact?.kind === 'AntBorn' && app.state.cursor === app.selectedFact.id"),"Overview pauses on the first real egg");
    await click("#play");
    await click("#action-replays button:nth-child(1)");
    await wait(() => evaluate("app.selectedFact?.kind === 'AntBorn' && app.playback === null"),"Paid hatch-free egg placement replay");
    await evaluate("seek(5 * DAY - 1)");
    assert.ok(await evaluate("app.visible.filter(a => a.stage === 'Egg').length > 2 && new Set(app.visible.map(a => a.position_m.join(','))).size === app.visible.length"));
    await screenshot("m0-egg-clutch");
    await click("#action-replays button:nth-child(2)");
    await wait(() => evaluate("app.selectedFact?.action?.act === 'Arrange brood' && app.selectedFact.action.phase === 'Completed' && app.playback === null"),"Timed brood arrangement");
    await screenshot("m0-arrangement");
    await select("locale","zh-CN");
    const chinese = JSON.parse(await readFile(new URL("../locales/zh-CN.json", import.meta.url), "utf-8"));
    const arrangementLabel = chinese["Watch brood arrangement"];
    assert.ok(arrangementLabel && arrangementLabel !== "Watch brood arrangement");
    await wait(() => evaluate("document.documentElement.lang === 'zh-CN' && $('action-replays').textContent.includes(" +
        JSON.stringify(arrangementLabel) + ")"),"Chinese MicroWorld actions");
    await select("locale","en");
    await wait(() => evaluate("document.documentElement.lang === 'en' && $('action-replays').textContent.includes('Watch brood arrangement')"),"English MicroWorld actions");
    await click("#milestones button[title^='First larval death']");
    await wait(() => evaluate("app.selectedFact?.kind === 'AntDied' && app.state.cursor === app.selectedFact.id && $('event-detail').dataset.event === app.selectedFact.id"),"Real larval death");
    await click("#individual-tab");
    assert.match(await evaluate("$('individual-content').textContent"),/Energy depleted|Dehydration/);
    await screenshot("m0-larval-outcome");
    await click("#watch-delivery");
    await wait(() => evaluate("app.selectedFact?.kind === 'FoodCollected' && app.section === 'surface'"),"First worker reaches a food source");
    await screenshot("m0-surface-food");
    await wait(() => evaluate("app.selectedFact?.kind === 'FoodDelivered' && app.playback === null && app.section === 'slice'"),"First worker brings food underground");
    await click("#individual-tab");
    await click("#individual-content .individual-window summary");
    await click("#individual-content .individual-window button:nth-child(2)");
    await wait(() => evaluate("$('individual-content').textContent.includes('Paid work') && !!$('ant-energy_nj')"),"Individual time budget and samples");
    await screenshot("m0-worker-window");
    await click("#milestones button[title^='First excavation']");
    await wait(() => evaluate("app.selectedFact?.kind === 'SoilExcavated' && $('event-detail').textContent.includes('Material edited')"),"Actual soil edit with parcel");
    await screenshot("m0-excavation");
    await click("#compare-tab");
    const baseline = await evaluate("app.catalog.find(x => x.title === 'MicroWorld · reference placement').key");
    await select("reference",baseline);
    await wait(() => evaluate("$('compare-cards').children.length === 2 && $('compare-config').textContent.includes('brood_space')"),"Matched geometry across two physics versions");
    await screenshot("m0-placement-comparison");
    await click("#observe-tab");
    const sealed = await evaluate("app.catalog.find(x => x.title === 'MicroWorld · sealed entrance').key");
    await select("archive",sealed);
    await wait(() => evaluate("$('title').textContent === 'MicroWorld · sealed entrance' && !!app.state"),"Sealed entrance control");
    await click("#days button[title='Jump to day 90']");
    await wait(() => evaluate("app.state.time_ms === 90 * DAY"),"Sealed negative at day 90");
    assert.equal(await evaluate("app.state.cumulative.deliveries || 0"),0);
    assert.deepEqual(exceptions,[]);
    result.status="PASS";
    result.chromium=(await send("Browser.getVersion")).product;
    result.date_utc=new Date().toISOString();
    result.archive_sha256=await evaluate("app.meta.archive_sha256");
    await writeFile(join(output,"m0-browser-receipt.json"),JSON.stringify(result,null,2)+"\n");
    console.log(JSON.stringify(result,null,2));
}

async function liveWorld() {
    await click("#new-colony");
    await wait(() => evaluate("liveView.state?.world_id && !$('viewer').hidden && app.hits.some(a => a.id === '2')"), "Fresh Core queen");
    const before = await evaluate("liveView.state.time_ms");
    assert.equal(await evaluate("liveView.state.rate"), 1);
    await sleep(1300);
    const elapsed = await evaluate("liveView.state.time_ms") - before;
    assert.ok(elapsed >= 800 && elapsed < 2500, `Expected 1x clock, advanced ${elapsed} ms`);
    await click("#live-pause");
    await wait(() => evaluate("!liveView.state.running && !liveView.busy"), "Pause the Core clock");
    const paused = await evaluate("liveView.state.time_ms");
    await sleep(350);
    assert.equal(await evaluate("liveView.state.time_ms"), paused);

    await select("live-target", "egg");
    await click("#live-seek");
    await wait(() => evaluate("liveView.state.fast_forward?.state === 'seeking' && $('live-rate').disabled"), "Look for the first egg");
    await wait(() => evaluate("liveView.state.fast_forward?.state === 'reached' && !$('event-detail').hidden"),
        "Stop and show the first committed birth", 22000);
    const savedTime = await evaluate("liveView.state.time_ms");
    assert.equal(savedTime, 4 * 86400000);
    assert.equal(await evaluate("liveView.state.fast_forward.event.time_ms"), savedTime);
    assert.equal(await evaluate("liveView.state.running"), false);
    assert.equal(await evaluate("$('live-rate').value"), "1");
    assert.equal(await evaluate("app.state.ants.filter(a => a.stage === 'Egg').length"), 1);
    await screenshot("m0-live-colony");
    await click("#open-saves");
    await evaluate("$('save-name').value = 'Live browser test'");
    await select("save-mode","archive");
    await click("#save-form button");
    await wait(() => evaluate("$('saved-colonies').textContent.includes('Live browser test') && !liveView.busy"), "List the native SQLite save");
    assert.match(await evaluate("$('saved-colonies').textContent"), /Day 4|Day 5/);
    assert.match(await evaluate("$('saved-colonies').textContent"), /KiB|MiB/);
    await screenshot("m0-live-saves");
    const savedEpoch = await evaluate("liveView.state.epoch");
    await click("#saved-colonies button");
    await wait(() => evaluate(`liveView.state.epoch > ${savedEpoch} && !$('save-manager').open`), "Load the saved world");
    assert.equal(await evaluate("liveView.state.time_ms"), savedTime);
    assert.equal(await evaluate("liveView.state.rate"), 1);
    assert.equal(await evaluate("liveView.state.running"), false);
    await click("#live-seek");
    await wait(() => evaluate("liveView.state.fast_forward?.state === 'already'"), "Find the saved milestone in the Core history");
    assert.equal(await evaluate("liveView.state.time_ms"), savedTime);
    await click("#observe-tab");
    await opened();
    assert.equal(await evaluate("app.meta.settings.physics"), 29);
    await click("#live-tab");
    await wait(() => evaluate("app.live && ! $('viewer').hidden && Boolean(app.state)"), "Return from the original archive");
    assert.equal(await evaluate("$('watch-delivery').hidden"), true);
    assert.equal(await evaluate("liveView.state.time_ms"), savedTime);
    await select("locale", "zh-CN");
    await wait(() => evaluate("document.documentElement.lang === 'zh-CN' && $('live-seek').textContent === '\u67e5\u627e\u9996\u6b21'"),
        "Translate the live controls without resetting the world");
    assert.equal(await evaluate("liveView.state.time_ms"), savedTime);
    await click("#live-pause");
    await wait(() => evaluate(`liveView.state.running && liveView.state.time_ms > ${savedTime}`), "Resume live sim at 1x");
    assert.equal(await evaluate("liveView.state.rate"), 1);
    result.worker_stops = {};
    for (const [target, kind, section] of [["exit", "Moved", "surface"], ["delivery", "FoodDelivered", "slice"],
        ["excavation", "SoilExcavated", "slice"]]) {
        await select("live-target", target);
        await click("#live-seek");
        const stop = await wait(() => evaluate(`(() => {
            const s = liveView.state.fast_forward;
            return s?.target === '${target}' && s.state === 'reached' && !liveView.busy && app.follow &&
                app.selected === s.event.actor && app.section === '${section}' && !$('event-detail').hidden ? s.event : null;
        })()`), `Pause and follow the worker at ${target}`);
        assert.equal(stop.kind, kind);
        assert.equal(await evaluate("liveView.state.time_ms"), stop.time_ms);
        assert.equal(await evaluate("liveView.state.running"), false);
        assert.equal(await evaluate("$('live-rate').value"), "1");
        result.worker_stops[target] = {time_ms: stop.time_ms, actor: stop.actor};
        if (target === "exit") {
            await screenshot("m0-live-follow");
            await click("#live-pause");
            await wait(() => evaluate(`liveView.state.running && app.follow && app.selected === '${stop.actor}' &&
                liveView.state.time_ms > ${stop.time_ms}`), "Keep following the same worker at 1x");
        }
        if (target === "delivery") assert.ok(stop.mass_ug.some(mass => mass > 0));
        if (target === "excavation") assert.ok(stop.geometry_edits[0].volume_q3 > 0);
    }
    assert.deepEqual(exceptions, []);
    result.status = "PASS";
    result.elapsed_at_1x_ms = elapsed;
    result.loaded_time_ms = savedTime;
    await writeFile(join(output, "m0-live-receipt.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify(result, null, 2));
}

async function nurseryWorld() {
    await click("#open-nursery");
    await wait(() => evaluate("liveView.state?.physics === 35 && liveView.state.provisioned_nursery && app.visible?.length >= 15"),
        "Render the provisioned ten-worker nursery from the native Core");
    assert.equal(await evaluate("liveView.state.rate"), 1);
    assert.equal(await evaluate("$('map').getBoundingClientRect().bottom <= window.innerHeight"), true);
    assert.equal(await evaluate("$('colony-settings').open"), false);
    const sample = await evaluate(`new Promise(resolve => {
        const start = performance.now();
        let previous;
        function observe() {
            if (performance.now() - start > 18000) return resolve(null);
            const ant = app.visible.find(a => a.display_motion?.progress > 0 && a.display_motion.progress < 1);
            const hit = ant && app.hits.find(h => h.id === ant.id);
            if (hit) {
                const now = {id: ant.id, x: hit.x, y: hit.y, begins: ant.display_motion.begins_ms,
                    view: app.renderedTimeMs, core: liveView.state.time_ms};
                if (previous && now.id === previous.id && now.begins === previous.begins && now.core === previous.core &&
                    now.view > previous.view && Math.hypot(now.x - previous.x, now.y - previous.y) > .05)
                    return resolve({previous, now});
                previous = now;
            }
            requestAnimationFrame(observe);
        }
        requestAnimationFrame(observe);
    })`);
    assert.ok(sample, "Paint two different poses within a single server cut");
    assert.ok(sample.now.view <= sample.now.core, "Display never moves beyond validated Core time");
    await click("#nursery-delivery");
    await wait(() => evaluate("liveView.state?.fast_forward?.state === 'reached' && !liveView.busy"),
        "Find and freeze the first actual food delivery", 28_000);
    const atDelivery = await evaluate("({clock: liveView.state.time_ms, event: liveView.state.fast_forward.event, ant: app.selected})");
    assert.equal(atDelivery.event.kind, "FoodDelivered");
    assert.ok(atDelivery.event.mass_ug.reduce((a, b) => a + b) > 0);
    assert.equal(atDelivery.event.time_ms, atDelivery.clock);
    assert.equal(atDelivery.event.actor, atDelivery.ant);
    assert.equal(await evaluate("!liveView.state.running && app.renderedTimeMs === liveView.state.time_ms"), true);
    await click("#body-envelopes");
    await select("locale", "zh-CN");
    await wait(() => evaluate("document.documentElement.lang==='zh-CN' && $('open-nursery').textContent.includes('\\u80b2\\u5e7c')"),
        "Translate the same native nursery controls");
    await screenshot("nursery-continuity");
    await select("nursery-treatment", "traffic");
    await Promise.all([click("#open-nursery"), (async () => {
        await wait(() => dialogs.shift(), "Confirm replacement of unsaved nursery progress", 5_000);
        await send("Page.handleJavaScriptDialog", {accept: true});
    })()]);
    await wait(() => evaluate("liveView.state?.physics === 34 && !liveView.state.provisioned_nursery && app.visible?.length >= 15"),
        "Open the previous nursery under its original physics version", 10_000);
    assert.deepEqual(exceptions, []);
    result.status = "PASS";
    result.frame_pair = sample;
    result.delivery = atDelivery;
    result.browser = (await send("Browser.getVersion")).product;
    await writeFile(join(output, "nursery-continuity-browser.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify(result, null, 2));
}

async function ecologyWorld() {
    await select("nursery-treatment", "ecology");
    await click("#open-nursery");
    await wait(() => evaluate("liveView.state?.ecology === 'water-fed' && !$('live-environment').hidden && app.visible?.length >= 15"),
        "Show the local ecology and real feeder reserve");
    assert.deepEqual(await evaluate("liveView.state.feeder_reserve_ug"), [7000, 875, 7000, 0]);
    assert.equal(await evaluate("liveView.state.rate"), 1);
    await click("#nursery-delivery");
    await wait(() => evaluate("liveView.state?.fast_forward?.state === 'reached' && !liveView.busy"),
        "Pause at the actual food delivery", 28_000);
    const delivery = await evaluate("liveView.state.fast_forward.event");
    assert.equal(delivery.kind, "FoodDelivered");
    assert.ok(delivery.mass_ug.slice(0, 3).every(n => n > 0));
    assert.equal(delivery.actor, await evaluate("app.selected"));
    await click("#individual-tab");
    await wait(() => evaluate("$('individual-content').textContent.includes('Next scheduled absorption')"),
        "Inspect the worker's stored physiology");
    await select("locale", "zh-CN");
    await wait(() => evaluate("document.documentElement.lang === 'zh-CN' && $('live-resources').textContent.includes('\u6c34\u5206')"),
        "Show quantities in the Chinese UI");
    await screenshot("local-ecology");
    await select("nursery-treatment", "ecology-dry");
    await Promise.all([click("#open-nursery"), (async () => {
        await wait(() => dialogs.shift(), "Confirm replacement of unsaved progress", 5_000);
        await send("Page.handleJavaScriptDialog", {accept: true});
    })()]);
    await wait(() => evaluate("liveView.state?.ecology === 'no-external-water' && !liveView.busy"), "Open the dry comparison");
    assert.equal(await evaluate("liveView.state.feeder_reserve_ug[2]"), 0);
    assert.equal(await evaluate("liveView.state.sources[0].stock_ug[2]"), 0);
    assert.deepEqual(exceptions, []);
    result.status = "PASS";
    result.delivery = delivery;
    result.browser = (await send("Browser.getVersion")).product;
    await writeFile(join(output, "local-ecology-browser.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify(result, null, 2));
}

async function activityWorld() {
    await click("#open-saves");
    await wait(() => evaluate("$('saved-colonies').textContent.includes('Worker activity test')"), "Find the activity test save");
    await click("#saved-colonies button");
    await wait(() => evaluate("liveView.state?.physics === 31 && !$('save-manager').open"), "Load the shorter worker timing");
    assert.deepEqual(await evaluate("liveView.state.worker_activity_timing"), {check_ms: 900000, minimum_program_ms: 3600000});
    assert.equal(await evaluate("liveView.state.running"), false);
    const categories = await evaluate("[...$('live-action-list').querySelectorAll('button')].map(e => e.dataset.activity).sort()");
    assert.deepEqual(categories, ["Brood care", "Ingest food", "Trophallaxis"]);
    const timestamp = await evaluate("liveView.state.time_ms");
    const labels = await evaluate(`(() => {
        const ctx = $('map').getContext('2d'), original = ctx.fillText, labels = [];
        try { ctx.fillText = (...args) => { labels.push(args[0]); return original.apply(ctx, args); }; drawMap(); }
        finally { ctx.fillText = original; }
        return labels;
    })()`);
    assert.ok(labels.includes("Ingest food #2"), "Draw the just-recorded queen meal at its recorded location");
    await click('#live-action-list [data-activity="Trophallaxis"]');
    assert.equal(await evaluate("$('event-detail').dataset.event"),
        await evaluate("liveView.state.actions.find(e => e.kind === 'NutritionTransferred').id"));
    assert.equal(await evaluate("liveView.state.time_ms"), timestamp);
    await select("locale", "zh-CN");
    await wait(() => evaluate("$('live-action-list').textContent.includes('\u4ea4\u54fa') && $('event-detail').textContent.includes('\u4ea4\u54fa')"),
        "Translate in-place actions and the selected fact");
    await screenshot("m0-in-place-actions");
    await select("colony-timing", "shorter");
    await click("#new-colony");
    await wait(() => evaluate("liveView.state.physics === 31 && liveView.state.running && !liveView.busy"), "Create a new shorter-timing colony");
    assert.equal(await evaluate("liveView.state.actions.length"), 0);
    assert.deepEqual(exceptions, []);
    result.status = "PASS";
    result.activity_groups = categories;
    console.log(JSON.stringify(result, null, 2));
}

async function foundingHabitat() {
    await click("#new-habitat");
    await wait(() => evaluate("liveView.state?.physics === 36 && !!liveView.state.climate && !liveView.busy"), "Open the founding habitat");
    assert.equal(await evaluate("liveView.state.rate"), 1);
    assert.equal(await evaluate("liveView.state.surface.trail_half_life_s"), 1955);
    assert.deepEqual(await evaluate("liveView.state.ants.map(a => a.caste)"), ["Queen"]);
    await click("#find-entrance");
    await wait(() => evaluate("app.section === 'surface' && !$('trail-control').hidden"), "Locate the actual opening");
    await click("#find-pantry");
    await wait(() => evaluate("app.section === 'slice' && $('live-resources').textContent.includes('Nest stock')"), "Locate the nest depot");
    await select("live-target", "delivery");
    await click("#live-seek");
    await wait(() => evaluate("liveView.state?.fast_forward?.state === 'reached' && !liveView.busy"), "Reach a real foundress-world delivery", 95_000);
    const delivery = await evaluate("liveView.state.fast_forward.event");
    assert.equal(delivery.kind, "FoodDelivered");
    assert.ok(delivery.mass_ug[0] > 0);
    assert.equal(delivery.actor, await evaluate("app.selected"));
    assert.equal(await evaluate("liveView.state.rate"), 1);
    assert.equal(await evaluate("liveView.state.running"), false);
    await select("locale", "zh-CN");
    await wait(() => evaluate("document.documentElement.lang === 'zh-CN' && $('title').textContent.includes('\u5355\u8681\u540e')"),
        "Localize the running habitat viewer");
    await screenshot("founding-habitat-delivery");
    assert.deepEqual(exceptions, []);
    console.log(JSON.stringify({status: "PASS", browser: (await send("Browser.getVersion")).product, delivery}, null, 2));
}

async function sealedNestWorld() {
    await evaluate("liveCommand('single-nest',{model:'reference',seed:2})");
    await wait(() => evaluate("liveView.state?.physics===38 && app.section==='nest' && Boolean(nestView.volume) && !liveView.busy"),
        "Sealed nest in the live viewport");
    assert.equal(await evaluate("liveView.state.ants.length"), 1);
    assert.equal(await evaluate("app.geometry.openings.length"), 0);
    await click("#live-pause");
    await wait(() => evaluate("liveView.state?.running === false && !liveView.busy"),
        "Pause Core before a presentation-only control test");
    // Presentation-only immersion must never advance or replace the Core cut.
    const intact = await evaluate("({cursor: liveView.state.cursor, time: liveView.state.time_ms})");
    await click("#focus-view");
    assert.equal(await evaluate("document.body.classList.contains('focus-view')"), true);
    await click("#focus-view");
    assert.equal(await evaluate("document.body.classList.contains('focus-view')"), false);
    assert.deepEqual(await evaluate("({cursor: liveView.state.cursor, time: liveView.state.time_ms})"), intact);
    assert.ok(await evaluate("adultGlyphSize({caste:'Queen'}, null, 80000) > adultGlyphSize({caste:'Worker'}, null, 80000)"));
    const seek = async (target, kind) => {
        await select("live-target",target);
        await click("#live-seek-next");
        await wait(() => evaluate(`liveView.state?.fast_forward?.state==='reached' &&
            liveView.state.fast_forward.target==='${target}' && !liveView.busy`), "Next committed " + target);
        const event = await evaluate("liveView.state.fast_forward.event");
        assert.equal(event.kind,kind);
        assert.equal(await evaluate("liveView.state.running || liveView.state.rate!==1"),false);
        return event;
    };
    await click("#live-seek-group");
    assert.equal(await evaluate("$('live-group-title').textContent"), "Fast-forward to next in group");
    assert.equal(await evaluate("$('live-group-start').disabled"), true);
    await click("#live-group-picker .panel-head button");
    await select("locale", "zh-CN");
    await wait(() => evaluate("document.documentElement.lang==='zh-CN' && $('live-seek-group').textContent === '\u5feb\u8fdb\u5230\u4e0b\u4e00\u7ec4'"),
        "Chinese event group control");
    await click("#live-seek-group");
    await click('#live-group-options input[value="hatch"]');
    await click('#live-group-options input[value="egg"]');
    assert.equal(await evaluate("$('live-group-count').textContent"), "\u5df2\u9009 2 \u9879");
    await click("#live-group-start");
    result.egg = await wait(() => evaluate("(() => {" +
        "const stop = liveView.state.fast_forward;" +
        "return stop?.state === 'reached' && stop.targets?.length === 2 && !liveView.busy && !$('event-detail').hidden ? stop.event : null; })()"),
        "Pause at the first selected event");
    assert.equal(result.egg.kind, "AntBorn");
    assert.equal(await evaluate("liveView.state.fast_forward.target"), "egg");
    assert.equal(await evaluate("liveView.state.time_ms"), result.egg.time_ms);
    assert.equal(await evaluate("liveView.state.running || liveView.state.rate !== 1"), false);
    assert.match(await evaluate("$('live-stop').textContent"), /\u4ea7\u5375/);
    await click("#live-seek-group");
    assert.deepEqual(await evaluate("selectedLiveGroup()"), ["egg", "hatch"]);
    await click("#live-group-picker .panel-head button");
    result.brood = await seek("brood-moved","BroodMoved");
    assert.equal(result.brood.related, "2");
    await wait(() => evaluate("$('title').textContent==='\u5c01\u95ed\u5efa\u7fa4\u5ba4'"),
        "Chinese sealed-nest title");
    await screenshot("m2-brood-zh");
    result.worker = await seek("worker","StageChanged");
    result.dig = await seek("excavation","SoilExcavated");
    result.delivery = await seek("delivery","FoodDelivered");
    assert.equal(result.dig.actor, result.worker.actor);
    assert.equal(result.delivery.actor, result.worker.actor);
    await wait(() => evaluate("liveView.state.soil_piles?.length && nestView.volume?.revision===app.geometry.revision"),
        "Real deposited soil in the amended nest view");
    await screenshot("m2-worker-zh");
    await click("#open-saves");
    assert.equal(await evaluate("$('save-mode').value"), "snapshot");
    await evaluate("$('save-name').value='Sealed nest browser'; $('save-form').requestSubmit()");
    await wait(() => evaluate("liveView.saves.some(s=>s.mode==='snapshot'&&s.history_floor>0)"), "Compact snapshot listed");
    assert.equal(await evaluate("$('saved-colonies').querySelectorAll('button').length"), 1);
    await click("#saved-colonies button");
    await wait(() => evaluate("!$('save-manager').open && liveView.state.history_floor>0 && !$('live-seek-next').disabled"),
        "Reloaded compact snapshot with next-event navigation");
    assert.equal(await evaluate("$('live-seek').disabled"), true);
    result.snapshot = await evaluate("liveView.saves[0].size_bytes");
    assert.equal(exceptions.length,0,JSON.stringify(exceptions));
    await writeFile(join(output,"sealed-nest-browser-receipt.json"),JSON.stringify(result,null,2)+"\n");
}

async function anatomicalNestWorld() {
    await click("#new-single-nest");
    await wait(() => evaluate("liveView.state?.physics===39 && Boolean(nestView.volume) && !liveView.busy"),
        "Anatomical nest in the viewport");
    assert.equal(await evaluate("liveView.state.ants.length"), 1);
    assert.equal(await evaluate("app.geometry.openings.length"), 0);
    assert.ok(await evaluate("liveView.state.ants[0].body.segments.length===3"));
    await click("#live-pause");
    await wait(() => evaluate("!liveView.state.running && !liveView.busy"),"Paused single queen");
    const unchanged = await evaluate("liveView.state.cursor");
    await click("#research-view");
    assert.equal(await evaluate("$('research-view').getAttribute('aria-pressed')"), "true");
    await click("#research-view");
    assert.equal(await evaluate("liveView.state.cursor"),unchanged);
    await select("locale","zh-CN");
    await wait(() => evaluate("document.documentElement.lang==='zh-CN'"),"Chinese observatory");
    const seek = async (target,kind) => {
        await select("live-target",target);
        await click("#live-seek-next");
        await wait(() => evaluate(`liveView.state?.fast_forward?.state==='reached' &&
            liveView.state.fast_forward.target==='${target}' && !liveView.busy`),"Actual " + target);
        const hit = await evaluate("liveView.state.fast_forward.event");
        assert.equal(hit.kind,kind);
        assert.equal(await evaluate("liveView.state.running || liveView.state.rate!==1"),false);
        return hit;
    };
    result.egg = await seek("egg","AntBorn");
    assert.ok(result.egg.position_m[0] < -.004);
    result.pickup = await seek("brood-moved","BroodMoved");
    assert.equal(result.pickup.related,"2");
    result.relocation = await seek("brood-moved","BroodMoved");
    assert.ok(BigInt(result.relocation.id)>BigInt(result.pickup.id));
    result.renderer = await evaluate("$('map').dataset.renderer");
    result.render_ms = await evaluate("nestView.lastDrawMs");
    await screenshot("single-nest-brood-zh");
    result.worker = await seek("worker","StageChanged");
    assert.equal(result.worker.stage,"Adult");
    result.excavation = await seek("excavation","SoilExcavated");
    result.delivery = await seek("delivery","FoodDelivered");
    assert.ok(result.delivery.mass_ug.reduce((a,b)=>a+b)>0);
    await wait(() => evaluate("liveView.state.soil_piles.length > 0 && nestView.volume?.revision===app.geometry.revision"),
        "Authored shaft and deposited parcel from actual excavation");
    assert.ok(await evaluate("liveView.state.ants.filter(a=>a.caste==='Worker' && a.body?.segments.length===3).length > 0"));
    await select("locale","en");
    await wait(() => evaluate("document.documentElement.lang==='en'"),"English observatory");
    await screenshot("single-nest-delivery-en");
    await click("#open-saves");
    assert.equal(await evaluate("$('save-mode').value"),"snapshot");
    await evaluate("$('save-name').value='Single nest review'; $('save-form').requestSubmit()");
    await wait(() => evaluate("liveView.saves.some(s=>s.mode==='snapshot')"),"Compact player save");
    await click("#saved-colonies button");
    await wait(() => evaluate("!$('save-manager').open && liveView.state.physics===39 && !liveView.busy"),
        "Loaded anatomical snapshot");
    result.snapshot_bytes = await evaluate("liveView.saves[0].size_bytes");
    assert.equal(exceptions.length,0,JSON.stringify(exceptions));
    await writeFile(join(output,"anatomical-browser-receipt.json"),JSON.stringify(result,null,2)+"\n");
}

async function founderAccessWorld() {
    await select("locale","zh-CN");
    await click("#colony-settings summary");
    await select("sealed-model","oral");
    await click("#new-single-nest");
    await wait(() => evaluate("liveView.state?.physics===40 && !liveView.busy"),"New experimental sealed nest");
    assert.equal(await evaluate("liveView.state.ants.length"),1);
    assert.equal(await evaluate("app.geometry.openings.length"),0);
    assert.equal(await evaluate("$('title').textContent"),"\u5c01\u95ed\u5efa\u7fa4\u5ba4");
    for (const target of ["delivery","queen-meal","queen-uptake"]) {
        await select("live-target",target);
        await click("#live-seek-next");
        await wait(() => evaluate(`liveView.state.fast_forward?.target==='${target}' &&
            liveView.state.fast_forward.state==='reached' && !liveView.busy`),"Committed " + target);
        const event=await evaluate("liveView.state.fast_forward.event");
        assert.ok(event.mass_ug.some(x => x>0));
        assert.equal(await evaluate("liveView.state.running || liveView.state.rate!==1"),false);
        assert.equal(await evaluate("app.selected"),event.actor);
        assert.equal(await evaluate("app.follow"),true);
        result[target]=event;
    }
    assert.equal(result["queen-meal"].kind,"FoundressNestMeal");
    assert.ok(["PhysiologyUpdated","FoundingBoundaryUptake"].includes(result["queen-uptake"].kind));
    assert.ok(result["queen-uptake"].mass_ug[0]>0);
    assert.ok(result.delivery.time_ms<result["queen-meal"].time_ms &&
              result["queen-meal"].time_ms<result["queen-uptake"].time_ms);
    assert.match(await evaluate("$('live-stop').textContent"),/\u5df2\u4ece\u55c9\u56ca\u5438\u6536/);
    assert.equal(await evaluate("$('title').textContent"),"\u5efa\u7fa4\u5de2 \u00b7 \u5de2\u53e3\u5df2\u6253\u5f00");
    await screenshot("queen-uptake-zh");
    await writeFile(join(output,"founder-access-browser.json"),JSON.stringify(result,null,2)+"\n");
    await select("sealed-model","offers");
    await Promise.all([click("#new-single-nest"), (async () => {
        await wait(() => dialogs.shift(), "Replace the finite food-access world", 5_000);
        await send("Page.handleJavaScriptDialog", {accept: true});
    })()]);
    await wait(() => evaluate("liveView.state?.physics===41 && !liveView.busy"),"New adult food-offer experiment");
    const offers = [], contactCuts = [];
    async function checkContact(event, destination) {
        const data = await evaluate(`(() => {
            const view = liveView.state, fact = app.selectedFact;
            const actor = view.ants.find(a => a.id === fact.actor);
            const other = ${destination === "recipient" ? "view.ants.find(a => a.id === fact.recipient).body.mouth_m" : "view.colonies.find(c => c.id === fact.colony).position_m"};
            const sites = liveTransferSites(fact,view);
            return {id:fact.id, time_ms:view.time_ms, actor_mouth_m:actor.body.mouth_m, other_m:other,
                marked:[sites?.mouth,sites?.other], card:$('event-detail').querySelector('.flow-contact')?.textContent,
                unsupported:liveTransferSites(fact,{...view,habitat:{anatomical:true}}),
                later:liveTransferSites(fact,{...view,time_ms:view.time_ms+1}),
                missing:liveTransferSites(fact,{...view,ants:view.ants.filter(a => a.id !== fact.actor)})};
        })()`);
        assert.equal(data.id,event.id);
        assert.equal(data.time_ms,event.time_ms);
        assert.deepEqual(data.marked,[data.actor_mouth_m,data.other_m]);
        assert.deepEqual([data.unsupported,data.later,data.missing],[null,null,null]);
        const distance = 1000 * Math.hypot(...data.actor_mouth_m.map((v,i) => v-data.other_m[i]));
        assert.ok(distance>=0 && distance<=0.65, `Native contact gap ${distance} mm`);
        assert.ok(data.card.includes(new Intl.NumberFormat('zh-CN',{maximumFractionDigits:3}).format(distance)+' mm'));
        contactCuts.push({event_id:event.id,time_ms:event.time_ms,actor:event.actor,other:event.recipient || event.colony,
            destination,actor_mouth_m:data.actor_mouth_m,other_m:data.other_m,gap_mm:distance});
    }
    for (const target of ["queen-gift","queen-gift","queen-uptake"]) {
        await select("live-target", target);
        await click("#live-seek-next");
        await wait(() => evaluate(`liveView.state.fast_forward?.target==='${target}' &&
            liveView.state.fast_forward.state==='reached' && !liveView.busy`),"Observe " + target);
        const event = await evaluate("liveView.state.fast_forward.event");
        assert.equal(await evaluate("liveView.state.running || liveView.state.rate!==1"), false);
        assert.equal(await evaluate("app.selected"), event.actor);
        offers.push(event);
        if (target === "queen-gift") {
            assert.equal(event.kind, "NutritionTransferred");
            assert.equal(event.recipient,"2");
            assert.notEqual(event.actor,event.recipient);
            assert.ok(event.mass_ug.some(x => x > 0));
            assert.ok((await evaluate("$('live-stop').textContent")).includes("#" + event.actor));
            if (event.mass_ug[0]) {
                const masses = await evaluate("[...document.querySelectorAll('#event-detail .flow-ingredients dd')].map(e=>e.textContent)");
                assert.match(masses[0], /^12\D/);
                assert.match(masses[1], /^0\D/);
                assert.match(masses[2], /^88\D/);
                await checkContact(event,"recipient");
                await screenshot("oral-contact-zh",false,"webp");
                await select('locale','en');
                await wait(() => evaluate("$('event-detail').querySelector('.flow-contact')?.textContent.includes('Mouth separation')"),
                    "Read the same mouth measurement in English");
                assert.equal(await evaluate("app.time"),event.time_ms);
                await select('locale','zh-CN');
                await wait(() => evaluate("$('event-detail').querySelector('.flow-contact')?.textContent.includes('\\u53e3\\u5668')"),
                    "Restore the Chinese contact receipt");
                await click('#event-detail .food-flow button[data-ant="2"]');
                await wait(() => evaluate("app.selected==='2' && !liveView.state.running"),"Inspect the actual recipient while paused");
                await click('#live-pause');
                await wait(() => evaluate(`liveView.state.running && app.time>${event.time_ms} && !liveView.busy &&
                    !pinnedAtDisplayedCut(app.selectedFact)`),"Release the old interaction marker during 1x playback");
                await click('#live-pause');
                await wait(() => evaluate("!liveView.state.running && !liveView.busy"),"Pause after leaving the oral contact");
            }
        }
    }
    assert.equal(offers[0].mass_ug[0],0);
    assert.ok(offers[1].mass_ug[0] > 0);
    assert.equal(offers[2].actor, offers[1].recipient);
    assert.ok(offers[0].time_ms < offers[1].time_ms && offers[1].time_ms < offers[2].time_ms);
    assert.equal(exceptions.length,0,JSON.stringify(exceptions));
    await writeFile(join(output,"local-offer-browser.json"),JSON.stringify(offers,null,2)+"\n");
    await select("sealed-model","mouth-handoff");
    await evaluate("$('sealed-seed').value='2'");
    await Promise.all([click("#new-single-nest"), (async () => {
        await wait(() => dialogs.shift(), "Open the wall-delivery control", 5_000);
        await send("Page.handleJavaScriptDialog", {accept: true});
    })()]);
    await wait(() => evaluate("liveView.state?.physics===43 && !liveView.busy"),"New wall-side delivery world");
    assert.equal(await evaluate("liveView.state.seed"), "2");
    await select("live-target","wall-delivery");
    assert.equal(await evaluate("$('live-target').value"), "wall-delivery");
    await click("#live-seek-next");
    await wait(async () => {
        const cut = await evaluate("({stop:liveView.state.fast_forward,time:liveView.state.time_ms,error:liveView.state.error})");
        if (cut.error || ["exhausted","cancelled","already"].includes(cut.stop?.state))
            throw Error("Wall delivery ended early: " + JSON.stringify(cut));
        return cut.stop?.target === "wall-delivery" && cut.stop.state === "reached" && !(await evaluate("liveView.busy"));
    },"Wall-side delivery",90_000).catch(async error => {
        const cut = await evaluate("({seed:liveView.state.seed,stop:liveView.state.fast_forward,time:liveView.state.time_ms,error:liveView.state.error,control:$('live-stop').textContent})");
        throw Error(error.message + " at " + JSON.stringify(cut));
    });
    const handoff = await evaluate("liveView.state.fast_forward.event");
    assert.equal(handoff.kind,"FoodDelivered");
    assert.equal(handoff.payload,"1");
    assert.ok(handoff.mass_ug[0]>0);
    assert.equal(await evaluate("liveView.state.running || liveView.state.rate!==1"),false);
    assert.equal(await evaluate("app.selected"),handoff.actor);
    assert.ok(await evaluate("app.follow"));
    assert.match(await evaluate("$('live-stop').textContent"),/\u5b58\u5165\u5de2\u5185/);
    assert.equal(exceptions.length,0,JSON.stringify(exceptions));
    await checkContact(handoff,"depot");
    await screenshot("wall-mouth-contact-zh",false,"webp");
    await writeFile(join(output,"live-contact-cuts.json"),JSON.stringify(contactCuts,null,2)+"\n");
    await writeFile(join(output,"wall-delivery-browser.json"),JSON.stringify(handoff,null,2)+"\n");
}

async function observatoryWorld() {
    const waitView = (expression, label, limit) => wait(() => evaluate(expression), label, limit);
    const stopAt = async (target, occurrence = "first") => {
        await select("live-target", target);
        await click(occurrence === "next" ? "#live-seek-next" : "#live-seek");
        await waitView(`liveView.state?.fast_forward?.state === 'reached' && !liveView.busy &&
            liveView.state.fast_forward.target === '${target}' && (liveView.state.fast_forward.occurrence || 'first') === '${occurrence}'`,
            "Committed " + target, 105_000);
        const stop = await evaluate("({id: liveView.state.world_id, time: liveView.state.time_ms, event: liveView.state.fast_forward.event, actor: app.selected})");
        assert.equal(stop.event.time_ms, stop.time);
        return stop;
    };
    const preset = async (type, replace) => {
        const clickPreset = click(`#observatory-presets button[data-preset="${type}"]`);
        if (replace) await Promise.all([clickPreset, (async () => {
            await wait(() => dialogs.shift(), "Confirm replacement of unsaved colony", 5_000);
            await send("Page.handleJavaScriptDialog", {accept: true});
        })()]);
        else await clickPreset;
        await waitView("nestView.volume && nestView.volume.epoch === liveView.epoch && app.section === 'nest' && !liveView.busy", "3D native cut");
    };
    await timed("first_nest_view_ms", () => preset("open", false));
    assert.deepEqual(await evaluate("liveView.state.ants.map(a => a.caste)"), ["Queen"]);
    assert.equal(await evaluate("liveView.state.physics"), 36);
    assert.equal(await evaluate("liveView.state.rate"), 1);
    await timed("pause_ui_ms", async () => {
        await click("#live-pause");
        await waitView("!liveView.state.running && !liveView.busy", "Pause settled");
    });
    const paused = await evaluate("liveView.state.time_ms");
    await clickMap("hit => hit.id === liveView.state.ants[0].id");
    await waitView("$('live-life-events').querySelector('button')", "Queen life evidence");
    const before = await evaluate("({edits: nestView.volume.revision, builds: nestView.built, yaw: nestView.yaw})");
    await evaluate("$('map').focus(); $('map').dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowRight'}))");
    assert.notEqual(await evaluate("nestView.yaw"), before.yaw);
    assert.equal(await evaluate("nestView.built"), before.builds);
    await evaluate("$('nest-depth').value=2; $('nest-depth').dispatchEvent(new Event('input'))");
    assert.equal(await evaluate("nestView.built"), before.builds + 1);
    await evaluate("$('nest-depth').value=0; $('nest-depth').dispatchEvent(new Event('input'))");
    assert.equal(await evaluate("liveView.state.time_ms"), paused);
    await click("#slice-button");
    await waitView("app.section === 'slice' && !$('plane-controls').hidden", "Original research section");
    await click("#nest-button");

    result.egg = await stopAt("egg");
    assert.equal(result.egg.event.kind, "AntBorn");
    await click("#individual-tab");
    await select("locale", "zh-CN");
    await waitView("document.documentElement.lang === 'zh-CN' && $('chronicle-steps').textContent.includes('\u9996\u6b21')", "Chinese milestones");
    await screenshot("m1-first-egg");
    assert.equal(await evaluate("$('live-seek-next').textContent"), "\u5feb\u8fdb\u5230\u4e0b\u4e00\u6b21");
    result.next_egg = await stopAt("egg", "next");
    assert.equal(result.next_egg.event.kind, "AntBorn");
    assert.ok(BigInt(result.next_egg.event.id) > BigInt(result.egg.event.id));
    assert.equal(result.next_egg.time - result.egg.time, 2 * 3600000);
    assert.equal(await evaluate("liveView.state.running || liveView.state.rate !== 1"), false);
    await select("locale", "en");
    result.exit = await stopAt("exit");
    assert.equal(result.exit.event.kind, "Moved");
    assert.equal(result.exit.event.actor, result.exit.actor);
    assert.ok(result.exit.event.position_m[1] >= 0);
    assert.equal(await evaluate("app.follow && app.section === 'nest'"), true);
    await timed("resume_ui_ms", async () => {
        await click("#live-pause");
        await waitView("liveView.state.running && !liveView.busy", "Resume settled");
    });
    result.frame_sample = await evaluate(`new Promise(resolve => {
        const times = [], start = performance.now();
        function sample(time) {
            times.push(time);
            if (time - start < 1200) return requestAnimationFrame(sample);
            resolve({frames: times.length, elapsed_ms: times.at(-1) - times[0], draw_ms: nestView.lastDrawMs,
                     mesh_ms: nestView.buildMs, faces: nestView.faces.length, occupancy_bytes: nestView.cells.byteLength});
        }
        requestAnimationFrame(sample);
    })`);
    result.delivery = await stopAt("delivery");
    assert.equal(result.delivery.event.kind, "FoodDelivered");
    assert.ok(result.delivery.event.mass_ug[0] > 0);
    assert.equal(result.delivery.event.actor, result.delivery.actor);
    await click("#individual-tab");
    await screenshot("m1-worker-delivery");
    await click("#open-saves");
    await select("save-mode","archive");
    await evaluate("$('save-name').value='M1 review'; $('save-form').requestSubmit()");
    await waitView("$('saved-colonies').textContent.includes('M1 review') && !liveView.busy", "Published save");
    await click("#saved-colonies button:first-child");
    await waitView("!$('save-manager').open && !liveView.busy && !liveView.state.running", "Restored native save");
    assert.equal(await evaluate("liveView.state.time_ms"), result.delivery.time);
    await click("#open-saves");
    await waitView("$('saved-colonies').textContent.includes('Replay')", "Save replay action");
    await click("#saved-colonies button:last-child");
    await opened();
    assert.equal(await evaluate("app.meta.world_id"), result.delivery.id);
    const replayed = await evaluate(`world('event', {id:'${result.delivery.event.id}'})`);
    assert.equal(replayed.time_ms, result.delivery.time);
    assert.deepEqual(replayed.mass_ug, result.delivery.event.mass_ug);

    await click("#live-tab");
    await waitView("app.live && !liveView.busy", "Return to live clock");
    await preset("plugged", false);
    assert.equal(await evaluate("liveView.state.terrain.openings.length"), 0);
    result.dig = await stopAt("excavation");
    assert.equal(result.dig.event.kind, "SoilExcavated");
    assert.ok(result.dig.event.geometry_edits.length);
    await waitView("nestView.volume?.revision === liveView.state.terrain.revision", "Geometry published after excavation");
    await screenshot("m1-excavation");
    await preset("absent", true);
    assert.equal(await evaluate("liveView.state.external_supply"), false);
    assert.deepEqual(await evaluate("liveView.state.feeder_reserve_ug"), [0, 0, 0, 0]);
    assert.deepEqual(exceptions, []);
    result.browser = (await send("Browser.getVersion")).product;
    result.status = "PASS";
    await writeFile(join(output, "m1-browser-receipt.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify(result));
}

async function observatoryWitnesses() {
    await wait(() => evaluate("app.section === 'nest' && nestView.volume?.world_id === app.meta.world_id"), "Shallow-plug archive geometry");
    assert.equal(await evaluate("app.meta.integrity"), "VERIFIED_PUBLISHED");
    assert.equal(await evaluate("app.meta.end_ms"), 90 * 86400000);
    assert.equal(await evaluate("app.geometry.openings.length"), 0);
    await click("#milestones button[title^='First excavation']");
    await wait(() => evaluate("app.selectedFact?.kind === 'SoilExcavated' && nestView.volume?.revision > 0"), "Recorded excavation");
    assert.equal(await evaluate("app.selectedFact.geometry_edits[0].event"), await evaluate("app.selectedFact.id"));
    result.shallow_plug = await evaluate("({id: app.meta.world_id, facts: app.meta.facts, excavation: app.selectedFact.id})");

    await select("archive", await evaluate("app.catalog[1].key"));
    await wait(() => evaluate("app.meta?.end_ms === 240 * DAY && nestView.volume?.world_id === app.meta.world_id"), "No-supply archive geometry");
    const death = await evaluate("app.meta.milestones.find(m => m.label === 'Queen died')");
    assert.ok(death, "The no-supply witness records a queen death");
    await click("#milestones button[title^='Queen died']");
    await wait(() => evaluate("app.selectedFact?.kind === 'AntDied' && !$('event-detail').hidden"), "Committed no-supply outcome");
    assert.equal(await evaluate("$('queen-state').textContent"), "Absent");
    assert.ok(await evaluate("app.selectedFact.death_cause"));
    result.absent_supply = await evaluate("({id: app.meta.world_id, facts: app.meta.facts, death: app.selectedFact.id, cause: app.selectedFact.death_cause})");
    await screenshot("m1-no-supply");
    assert.deepEqual(exceptions, []);
    result.browser = (await send("Browser.getVersion")).product;
    result.status = "PASS";
    await writeFile(join(output, "m1-witness-browser-receipt.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify(result));
}

async function observatorySoak() {
    await click('#observatory-presets [data-preset="open"]');
    await wait(() => evaluate("nestView.volume && !liveView.busy"), "Open the bounded browser soak");
    const started = clock(), samples = [];
    await select("live-rate", "86400");
    await wait(() => evaluate("liveView.state?.rate === 86400 && !liveView.busy"), "Accelerate the live clock");
    let snapshot;
    do {
        snapshot = await evaluate(`({time_ms:liveView.state.time_ms, cursor:liveView.state.cursor, error:liveView.state.error,
            geometryEdits:liveView.state.terrain.revision, meshRebuilds:nestView.built, lastDrawMs:nestView.lastDrawMs})`);
        samples.push({...snapshot, elapsed_ms: Math.round(clock() - started), heap_bytes: (await send("Runtime.getHeapUsage")).usedSize});
        if (snapshot.time_ms >= 150 * 86400000 || snapshot.error || clock() - started >= 180000) break;
        await sleep(7500);
    } while (true);
    if (await evaluate("liveView.state.running")) await click("#live-pause");
    await wait(() => evaluate("!liveView.state.running && !liveView.busy"), "Pause after browser soak");
    result.intent = {horizon_days: 150, wall_budget_seconds: 180, sampling_delay_ms: 7500};
    result.status = snapshot.time_ms >= 150 * 86400000 ? "COMPLETE" : "STOPPED";
    result.last_sample = snapshot;
    result.samples = samples;
    result.browser = (await send("Browser.getVersion")).product;
    assert.deepEqual(exceptions, []);
    await writeFile(join(output, "m1-soak-receipt.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify({status: result.status, last_sample: snapshot}));
}

try {
    const port = await wait(async () => {
        try { return (await readFile(join(cache, "DevToolsActivePort"), "utf8")).split("\n")[0]; }
        catch { return null; }
    }, "Chromium testing port", 45000);
    const tabs = await fetch("http://127.0.0.1:" + port + "/json/list").then(r => r.json());
    socket = new WebSocket(tabs.find(t => t.type === "page").webSocketDebuggerUrl);
    await new Promise((success, failure) => {
        socket.addEventListener("open", success, {once: true});
        socket.addEventListener("error", failure, {once: true});
    });
    socket.addEventListener("message", ({data}) => {
        const message = JSON.parse(data);
        if (pending.has(message.id)) {
            const callback = pending.get(message.id);
            pending.delete(message.id);
            callback(message);
        }
        if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails);
        if (message.method === "Page.javascriptDialogOpening") dialogs.push(message.params);
    });
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", {width: 1480, height: 1080, deviceScaleFactor: 1, mobile: false});
    await timed("first_browser_view_ms", async () => {
        await send("Page.navigate", {url: host});
        if (["live", "activity", "nursery", "ecology", "habitat", "m1", "m2", "overhaul", "founder-access", "m1-soak"].includes(mode)) {
            await wait(() => evaluate("typeof app !== 'undefined' && app.live && liveView.state?.core_available && !$('new-colony').disabled"),
                "Live controls ready");
            return;
        }
        await opened();
        result.shell_paint_ms = await evaluate("performance.getEntriesByType('paint').find(x => x.name === 'first-contentful-paint')?.startTime ?? null");
        result.world_ready_ms_after_navigation = await evaluate("performance.getEntriesByName('op0-world-ready')[0].startTime");
    });
    if (mode === "live") {
        await liveWorld();
    } else if (mode === "nursery") {
        await nurseryWorld();
    } else if (mode === "ecology") {
        await ecologyWorld();
    } else if (mode === "habitat") {
        await foundingHabitat();
    } else if (mode === "m2") {
        await sealedNestWorld();
    } else if (mode === "overhaul") {
        await anatomicalNestWorld();
    } else if (mode === "founder-access") {
        await founderAccessWorld();
    } else if (mode === "m1") {
        await observatoryWorld();
    } else if (mode === "m1-witnesses") {
        await observatoryWitnesses();
    } else if (mode === "m1-soak") {
        await observatorySoak();
    } else if (mode === "activity") {
        await activityWorld();
    } else if (mode === "micro") {
        await microWorld();
    } else if (mode === "r0") {
        await r0World();
    } else if (mode === "r0r1") {
        await r0r1World();
    } else {
    assert.equal(await evaluate("$('title').textContent"), "Founding colony");
    assert.equal(await evaluate("app.meta.facts"), 668720);
    assert.equal(await evaluate("app.state.time_ms"), 0);
    assert.equal(await evaluate("app.hits.some(a => a.id === '2')"), true);
    await screenshot("founding-day-0");

    await click("#milestones button[title^='First egg laid']");
    await wait(() => evaluate("app.state.cursor === '84' && app.state.population.eggs === 1"), "First recorded egg");
    await clickMap("hit => hit.ants.length === 2");
    await wait(() => evaluate("$('location-list').textContent.includes('Egg #4') && $('location-list').textContent.includes('Queen #2')"),
        "Both insects share an inspectable coordinate");
    await click("#location-list [data-ant-id='4']");
    await wait(() => evaluate("document.querySelector('#individual-content h3')?.textContent === 'Egg #4'"), "Select an egg from its shared marker");
    await screenshot("first-egg-shared-location");
    await click("#close-location");

    await click("#days button[title='Jump to day 45']");
    await wait(() => evaluate("$('day-counts').textContent.includes('400 committed records') && $('day-counts').textContent.includes('30 movements')"),
        "Daily facts and movement counts");
    assert.equal(await evaluate("$('hour-bins').children.length"), 24);
    await click("#hour-bins button:nth-child(16)");
    await wait(() => evaluate("app.state.time_ms === 45 * DAY + 15 * HOUR"), "Exact hour seek");
    await select("replay-mode", "movement");
    await click("#next-event");
    await wait(() => evaluate("app.state.cursor === '9721' && $('day-time-value').textContent === '15:36:00.103'"), "First movement step");
    await click("#next-event");
    await wait(() => evaluate("app.state.cursor === '9728' && $('day-time-value').textContent === '15:36:00.204'"), "Second movement step");
    await click("#previous-event");
    await wait(() => evaluate("app.state.cursor === '9721'"), "Move one committed step backwards");
    await click("#play");
    await wait(() => evaluate("Number(app.state.cursor) >= 9728"), "Movement plays at subsecond simulation intervals");
    await click("#play");
    await select("replay-mode", "overview");
    await select("locale", "zh-CN");
    await wait(() => evaluate("$('day-counts').textContent.includes('400 \u6761\u63d0\u4ea4\u8bb0\u5f55')"), "Chinese intraday activity");
    assert.equal(await evaluate("$('day-title').textContent"), "\u65e5\u5185\u6d3b\u52a8");
    await screenshot("within-day-movement", true);
    await select("locale", "en");
    await wait(() => evaluate("$('day-counts').textContent.includes('400 committed records')"), "English intraday activity");

    await click("#watch-delivery");
    await wait(() => evaluate("app.playingDelivery && app.state.cursor === '9721' && app.section === 'slice' && app.selected === '4'"),
        "Quick replay starts at worker #4's actual departure");
    await wait(() => evaluate("app.state.cursor === '9826' && app.section === 'surface' && app.hits.some(a => a.id === '4')"),
        "Quick replay follows the worker to the surface and its recorded collection");
    await wait(() => evaluate("!app.playingDelivery && app.state.cursor === '9938' && app.section === 'slice'"),
        "Quick replay stops at the actual delivery back underground");
    assert.equal(await evaluate("app.state.cumulative.deliveries"), 1);

    await timed("jump_to_worker_ms", async () => {
        await click("#milestones button[title^='First worker eclosed']");
        await wait(() => evaluate("app.state.cursor === '9661' && $('event-detail').textContent.includes('Eclosed')"), "Worker eclosed");
    });
    await click("#individual-tab");
    assert.equal(await evaluate("document.querySelector('#individual-content h3').textContent"), "Worker #4");
    await click("#milestones button[title^='First food delivered']");
    await wait(() => evaluate("app.state.cursor === '9938' && $('event-detail').textContent.includes('Food delivered')"), "Food delivery");
    await click("#milestones button[title^='First food collection']");
    await wait(() => evaluate("app.state.cursor === '9826' && !$('event-detail').hidden"), "Source reached from a real fact");
    await timed("select_ant_from_map_ms", async () => {
        await clickMap("h => h.id === '4'");
        await wait(() => evaluate("!$('individual-panel').hidden && document.querySelector('#individual-content h3')?.textContent === 'Worker #4'"), "Map selection");
    });
    await click("#follow");
    assert.equal(await evaluate("$('follow').getAttribute('aria-pressed')"), "true");
    await screenshot("worker-at-food-source");
    await click("#milestones button[title^='First excavation']");
    await wait(() => evaluate("app.state.cursor === '10692' && $('event-detail').textContent.includes('Quantized box')"), "Excavation geometry");
    assert.equal(await evaluate("app.geometry.revision"), 1);
    await screenshot("first-excavation");
    await click("#milestones button[title^='First recruitment activation']");
    await wait(() => evaluate("app.state.cursor === '17118' && !$('event-detail').hidden"), "Recruitment activation");
    await click("#milestones button[title^='First larval death']");
    await wait(() => evaluate("app.state.cursor === '5375' && !$('event-detail').hidden"), "Larval death");
    await click("#individual-tab");
    assert.equal(await evaluate("app.selected"), "5");
    assert.match(await evaluate("$('individual-content').textContent"), /Larva|Dead/);
    assert.match(await evaluate("$('individual-content').textContent"), /Body energy/);
    await screenshot("larval-life-history");
    const originalIdentity = await evaluate("[app.meta.archive_sha256, app.state.cursor, app.selected]");
    await select("locale", "zh-CN");
    await wait(() => evaluate("document.documentElement.lang === 'zh-CN' && $('individual-content').textContent.includes('\u80fd\u91cf\u8017\u5c3d')"), "Chinese larval profile");
    assert.equal(await evaluate("$('compare-tab').textContent"), "\u5bf9\u6bd4\u4e16\u754c");
    assert.equal(await evaluate("$('ant-id').placeholder"), "\u8f93\u5165\u8682\u8681\u7f16\u53f7");
    assert.deepEqual(await evaluate("[app.meta.archive_sha256, app.state.cursor, app.selected]"), originalIdentity);
    await screenshot("larval-life-history-zh");
    await select("locale", "en");
    await wait(() => evaluate("document.documentElement.lang === 'en' && $('individual-content').textContent.includes('Energy depleted')"), "Restored English larval profile");
    await click("#follow");
    await click("#events-tab");
    await select("filter", "care");
    await select("event-range", "all");
    await wait(() => evaluate("$('event-list').textContent.includes('Opportunity') || $('event-list').textContent.includes('Care')"),
        "Care events");
    await wait(() => evaluate("!$('more-events').hidden"), "Second event page");
    const first = await evaluate("document.querySelector('#event-list .event-row').dataset.event");
    await click("#more-events");
    await wait(() => evaluate("Number($('event-list').querySelector('.event-row')?.dataset.event || '0') > " + Number(first)), "Ordered second page");

    await click("#days button[title='Jump to day 0']");
    await wait(() => evaluate("app.state.time_ms === 0"), "Day zero");
    await select("speed", "30");
    await click("#play");
    await wait(() => evaluate("app.state.time_ms > 0"), "Playback starts");
    await click("#play");
    const paused = await evaluate("app.time");
    await sleep(250);
    assert.equal(await evaluate("app.time"), paused);
    await click("#play");
    await wait(() => evaluate("app.state.time_ms === 150 * DAY && app.playback === null"), "Playback through day 150", 35000);
    assert.equal(await evaluate("$('workers').textContent"), "45");
    await timed("seek_day_90_ms", async () => {
        await evaluate("(() => { $('time').value = 90 * DAY; $('time').dispatchEvent(new Event('input')); })()");
        await wait(() => evaluate("app.state.time_ms === 90 * DAY"), "Slider seek to day 90");
    });
    await click("#days button[title='Jump to day 150']");
    await click("#compare-tab");
    const reference = await evaluate("app.catalog[4].key");
    await select("reference", reference);
    await wait(() => evaluate("$('compare-cards').children.length === 2 && $('compare-config').textContent.includes('different')"), "Paired comparison");
    assert.match(await evaluate("$('compare-cards').textContent"), /First census cohort/);
    assert.match(await evaluate("$('compare-config').textContent"), /first_ration_ppm/);
    await screenshot("physics-25-comparison");
    await select("locale", "zh-CN");
    await wait(() => evaluate("$('compare-config').textContent.includes('\u751f\u6001\u5f00\u5173')"), "Chinese comparison controls and settings");
    assert.match(await evaluate("$('compare-config').textContent"), /first_ration_ppm/);
    await select("locale", "en");
    await wait(() => evaluate("$('compare-config').textContent.includes('Ecological switches')"), "Restored English comparison");
    await click("#observe-tab");

    const absent = await evaluate("app.catalog[1].key");
    await select("archive", absent);
    await wait(() => evaluate("$('title').textContent === 'No external supply' && !!app.state"), "Negative archive");
    await click("#days button[title='Jump to day 150']");
    await wait(() => evaluate("app.state.time_ms === 150 * DAY"), "Negative end");
    assert.equal(await evaluate("$('workers').textContent"), "0");
    assert.equal(await evaluate("$('queen-state').textContent"), "Absent");
    await screenshot("no-external-supply");

    await select("locale", "zh-CN");
    await wait(() => evaluate("document.documentElement.lang === 'zh-CN' && $('queen-state').textContent !== 'Absent'"), "Language preference saved");
    await timed("reopen_browser_with_index_ms", async () => {
        await send("Page.reload");
        await opened();
    });
    assert.equal(await evaluate("document.documentElement.lang"), "zh-CN");
    assert.equal(await evaluate("$('locale').value"), "zh-CN");
    await select("locale", "en");
    await wait(() => evaluate("document.documentElement.lang === 'en' && $('title').textContent === 'Founding colony'"), "Switch back after reopening");
    assert.equal(await evaluate("app.meta.facts"), 668720);
    assert.deepEqual(exceptions, []);
    result.world = await evaluate("app.meta.world_id");
    result.archive_sha256 = await evaluate("app.meta.archive_sha256");
    result.chromium = (await send("Browser.getVersion")).product;
    result.localization = "English and Simplified Chinese switched at the same cut and comparison, persisted after reload";
    result.within_day_replay = "Selected a real egg from a shared marker; observed 400 facts and 30 movements on day 45; stepped through the real 101 ms interval and back";
    result.delivery_replay = "Followed worker #4 underground to surface collection and back underground, stopping at fact #9938";
    result.date_utc = new Date().toISOString();
    result.status = "PASS";
    await writeFile(join(output, "browser-receipt.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify(result, null, 2));
    }
} finally {
    if (socket?.readyState===WebSocket.OPEN) {
        socket.send(JSON.stringify({id:++sequence,method:"Browser.close"}));
        await Promise.race([exited,sleep(1800)]);
    }
    socket?.close();
    processHandle.kill();
    await Promise.race([exited, sleep(3000)]);
    await rm(cache, {recursive: true, force: true, maxRetries: 10, retryDelay: 200}).catch(err => console.error(String(err)));
}
