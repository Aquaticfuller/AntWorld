// Drive a real Chromium browser through its local testing protocol. Node 22+.
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {mkdtemp, mkdir, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {setTimeout as sleep} from "node:timers/promises";

const [browser, host = "http://127.0.0.1:8765", output = "out/op0-browser"] = process.argv.slice(2);
if (!browser) throw Error("Usage: node op0/tests/browser_smoke.mjs <chromium> [local viewer URL] [output]");
const cache = await mkdtemp(join(tmpdir(), "antworld-op0-browser-"));
await mkdir(output, {recursive: true});
const processHandle = spawn(browser, ["--headless=new", "--disable-background-networking", "--no-first-run",
    "--no-default-browser-check", "--remote-debugging-port=0", "--user-data-dir=" + cache,
    "--window-size=1540,1160", "--disable-dev-shm-usage",
    ...(process.getuid?.() === 0 ? ["--no-sandbox"] : []), "about:blank"],
    {windowsHide: true, stdio: ["ignore", "ignore", "pipe"]});
let browserError = "", exitMessage = "";
processHandle.on("error", err => { exitMessage = String(err); });
processHandle.stderr.on("data", message => { browserError = (browserError + message).slice(-3000); });
const exited = new Promise(resolveExit => processHandle.once("close", resolveExit));
let socket, sequence = 0;
const pending = new Map(), exceptions = [], result = {};
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
    if (response.exceptionDetails) throw Error("Evaluation failed: " + expression + "\n" + response.exceptionDetails.text);
    return response.result.value;
}
async function click(selector) {
    const [x, y] = await evaluate("(() => { const e = document.querySelector(" + JSON.stringify(selector) +
        "); if (!e || e.hidden) throw Error('Missing control'); e.scrollIntoView({block:'center', inline:'center'});" +
        " const b = e.getBoundingClientRect(); return [b.left + b.width/2, b.top + b.height/2]; })()");
    await mouse(x, y);
}
async function mouse(x, y) {
    await send("Input.dispatchMouseEvent", {type: "mousePressed", x, y, button: "left", clickCount: 1});
    await send("Input.dispatchMouseEvent", {type: "mouseReleased", x, y, button: "left", clickCount: 1});
}
async function select(id, value) {
    return evaluate("(() => { const e = $(" + JSON.stringify(id) + "); e.value = " + JSON.stringify(value) +
        "; e.dispatchEvent(new Event('change')); return e.value; })()");
}
async function screenshot(name) {
    await evaluate("scrollTo(0, 0)");
    await sleep(250);
    const frame = await send("Page.captureScreenshot", {format: "png", captureBeyondViewport: false});
    await writeFile(join(output, name + ".png"), Buffer.from(frame.data, "base64"));
}
async function opened() {
    await wait(() => evaluate('document.documentElement.dataset.ready === "true" && !!app.state'), "Rendered world");
}
async function timed(name, execute) {
    const start = clock();
    await execute();
    result[name] = +(clock() - start).toFixed(2);
}

try {
    const port = await wait(async () => {
        try { return (await readFile(join(cache, "DevToolsActivePort"), "utf8")).split("\n")[0]; }
        catch { return null; }
    }, "Chromium testing port", 15000);
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
    });
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", {width: 1480, height: 1080, deviceScaleFactor: 1, mobile: false});
    await timed("first_browser_view_ms", async () => {
        await send("Page.navigate", {url: host});
        await opened();
        result.shell_paint_ms = await evaluate("performance.getEntriesByType('paint').find(x => x.name === 'first-contentful-paint')?.startTime ?? null");
        result.world_ready_ms_after_navigation = await evaluate("performance.getEntriesByName('op0-world-ready')[0].startTime");
    });
    assert.equal(await evaluate("$('title').textContent"), "Founding colony");
    assert.equal(await evaluate("app.meta.facts"), 668720);
    assert.equal(await evaluate("app.state.time_ms"), 0);
    assert.equal(await evaluate("app.hits.some(a => a.id === '2')"), true);
    await screenshot("founding-day-0");

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
    const position = await evaluate("(() => { const b = $('map').getBoundingClientRect(), a = app.hits.find(h => h.id === '4');" +
        " return a ? [b.left + a.x, b.top + a.y] : null; })()");
    assert.ok(position, "Worker is visible at the real food source");
    await timed("select_ant_from_map_ms", async () => {
        await mouse(...position);
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
    await click("#observe-tab");

    const absent = await evaluate("app.catalog[1].key");
    await select("archive", absent);
    await wait(() => evaluate("$('title').textContent === 'No external supply' && !!app.state"), "Negative archive");
    await click("#days button[title='Jump to day 150']");
    await wait(() => evaluate("app.state.time_ms === 150 * DAY"), "Negative end");
    assert.equal(await evaluate("$('workers').textContent"), "0");
    assert.equal(await evaluate("$('queen-state').textContent"), "Absent");
    await screenshot("no-external-supply");

    await timed("reopen_browser_with_index_ms", async () => {
        await send("Page.reload");
        await opened();
    });
    assert.equal(await evaluate("app.meta.facts"), 668720);
    assert.deepEqual(exceptions, []);
    result.world = await evaluate("app.meta.world_id");
    result.archive_sha256 = await evaluate("app.meta.archive_sha256");
    result.chromium = (await send("Browser.getVersion")).product;
    result.date_utc = new Date().toISOString();
    result.status = "PASS";
    await writeFile(join(output, "browser-receipt.json"), JSON.stringify(result, null, 2) + "\n");
    console.log(JSON.stringify(result, null, 2));
} finally {
    socket?.close();
    processHandle.kill();
    await Promise.race([exited, sleep(3000)]);
    await rm(cache, {recursive: true, force: true, maxRetries: 5, retryDelay: 200}).catch(err => console.error(String(err)));
}
