"use strict";

// Each merged quad marks a material interface in the bounded native grid.
// The sides of the requested window are open, with no invented boundary wall.
function nestFaces(cells, dimensions, ceiling) {
    const [width, depth, height] = dimensions;
    const shape = [width, ceiling, height];
    const index = p => (p[2] * depth + p[1]) * width + p[0];
    const faces = [];
    for (let axis = 0; axis < 3; axis++) {
        const u = (axis + 1) % 3, v = (axis + 2) % 3;
        const w = shape[u], h = shape[v], mask = new Int8Array(w * h);
        for (let plane = 1; plane <= shape[axis]; plane++) {
            const cap = plane === shape[axis];
            if (cap && axis !== 1) continue;
            const p = [0, 0, 0];
            for (let j = 0; j < h; j++) {
                p[v] = j;
                for (let i = 0; i < w; i++) {
                    p[u] = i;
                    p[axis] = plane - 1;
                    const lower = cells[index(p)];
                    p[axis] = plane;
                    const upper = cap ? 0 : cells[index(p)];
                    mask[j * w + i] = lower && !upper ? lower : upper && !lower ? -upper : 0;
                }
            }
            for (let j = 0; j < h; j++) for (let i = 0; i < w;) {
                const material = mask[j * w + i];
                if (!material) { i++; continue; }
                let cols = 1, rows = 1;
                while (i + cols < w && mask[j * w + i + cols] === material) cols++;
                while (j + rows < h && mask.subarray((j + rows) * w + i, (j + rows) * w + i + cols)
                    .every(value => value === material)) rows++;
                for (let k = 0; k < rows; k++) mask.fill(0, (j + k) * w + i, (j + k) * w + i + cols);
                const corner = (a, b) => {
                    const point = [0, 0, 0];
                    point[axis] = plane; point[u] = a; point[v] = b;
                    return point;
                };
                faces.push({axis, cap, material: Math.abs(material), sign: Math.sign(material),
                    vertices: [corner(i, j), corner(i + cols, j), corner(i + cols, j + rows), corner(i, j + rows)]});
                i += cols;
            }
        }
    }
    return faces;
}

const nestView = {
    yaw: -.6, pitch: .64, zoom: 1, x: 0, y: 0, focus: null,
    request: null, key: null, volume: null, faces: null, built: 0, lastDrawMs: null,
    updateKey: null, error: null
};

function resetNestCamera() {
    Object.assign(nestView, {yaw: -.6, pitch: .64, zoom: 1, x: 0, y: 0, focus: null});
    $("nest-scale").value = "nest";
}

function requestNestVolume() {
    const live = app.live, epoch = liveView.epoch;
    const selectedWorld = live ? liveView.state.world_id : app.meta.world_id;
    const revision = app.geometry?.revision;
    if (revision == null || !app.meta.settings.geometry) return;
    const key = `${live ? epoch : app.meta.key}:${selectedWorld}:${revision}`;
    if (nestView.key === key || nestView.request === key) return;
    nestView.request = key;
    nestView.volume = null;
    nestView.error = null;
    const get = live ? api("live/volume", {epoch}) : world("volume", cut());
    get.then(volume => {
        if (nestView.request !== key) return;
        if (volume.world_id !== selectedWorld || volume.revision !== revision || (live && volume.epoch !== epoch)) return;
        const previous = nestView.key?.split(":").slice(0, -1).join(":");
        if (previous !== key.split(":").slice(0, -1).join(":")) {
            resetNestCamera();
            $("nest-depth").value = 0;
        }
        nestView.key = key;
        nestView.volume = volume;
        nestView.faces = null;
        nestView.cells = Uint8Array.from(atob(volume.materials_b64), value => value.charCodeAt(0));
        $("nest-depth").max = volume.dimensions[1] - 1;
        drawMap();
    }).catch(error => {
        if (nestView.request === key) {
            nestView.key = key;
            nestView.error = error.message;
            drawMap();
        }
    }).finally(() => { if (nestView.request === key) nestView.request = null; });
}

function nestProjection(width, height, focus, field) {
    const camera = nestView;
    const sy = Math.sin(camera.yaw), cy = Math.cos(camera.yaw);
    const sp = Math.sin(camera.pitch), cp = Math.cos(camera.pitch);
    const horizontal = [cy, 0, sy], vertical = [-sy * sp, cp, cy * sp], depth = [sy * cp, sp, -cy * cp];
    const unit = Math.min(width - 40, height * 1.12) * camera.zoom / field;
    const project = point => {
        const x = point[0] - focus[0], y = point[1] - focus[1], z = point[2] - focus[2];
        return [width / 2 + camera.x + unit * (x * horizontal[0] + z * horizontal[2]),
            height * .53 + camera.y - unit * (x * vertical[0] + y * vertical[1] + z * vertical[2]),
            x * depth[0] + y * depth[1] + z * depth[2]];
    };
    return {project, depth};
}

function nestPolygon(ctx, polygon, fill, edge) {
    ctx.beginPath();
    for (const [i, p] of polygon.entries()) {
        if (!i) ctx.moveTo(p[0], p[1]);
        else ctx.lineTo(p[0], p[1]);
    }
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (edge) { ctx.strokeStyle = edge; ctx.stroke(); }
}

function nestAnt(ctx, ant, p, direction, size) {
    const [x, y] = p;
    if (ant.stage === "Adult") {
        drawAdult(ctx,ant,x,y,size,direction,ant.id===app.selected,ant.display_motion?.progress,app.renderedTimeMs);
        return;
    }
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(direction);
    ctx.fillStyle = colors[ant.stage.toLowerCase()] || colors.worker;
    ctx.strokeStyle = "#4d3d2c";
    ctx.lineWidth = .7;
    ctx.beginPath();
    ctx.ellipse(0,0,size,size*.68,0,0,2*Math.PI);
    ctx.fill(); ctx.stroke();
    if (ant.id === app.selected) {
        ctx.strokeStyle = "#f6eac6";
        ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.arc(0, 0, size + 5, 0, 2 * Math.PI); ctx.stroke();
    }
    ctx.restore();
}

function nestCallout(ctx, point, label, color, [dx, dy], width, height) {
    const [x, y] = point;
    if (x < 0 || y < 0 || x > width || y > height) return;
    ctx.save();
    ctx.font = '600 12px "Inter", "Microsoft YaHei UI", sans-serif';
    const w = ctx.measureText(label).width + 16;
    const left = Math.max(8,Math.min(width-w-8,x+dx-(dx<0?w:0)));
    const top = Math.max(8,Math.min(height-32,y+dy-11));
    ctx.strokeStyle = color;
    ctx.lineWidth = .75;
    ctx.beginPath();
    ctx.moveTo(x,y); ctx.lineTo(dx < 0 ? left + w : left,top+11);
    ctx.stroke();
    circle(ctx,x,y,3,color,"#262b26");
    ctx.fillStyle = "#172123f2";
    ctx.beginPath(); ctx.roundRect(left,top,w,22,4); ctx.fill();
    ctx.textBaseline = "middle"; ctx.fillStyle = "#fff6e4";
    ctx.fillText(label,left+8,top+11);
    ctx.restore();
}

function drawNest(canvas, state, motionOnly) {
    const started = performance.now(), {ctx, width, height} = canvas;
    const backdrop = ctx.createRadialGradient(width*.5,height*.43,0,width*.5,height*.43,width*.74);
    backdrop.addColorStop(0,"#26383a");
    backdrop.addColorStop(1,"#11191c");
    ctx.fillStyle = backdrop;
    ctx.fillRect(0, 0, width, height);
    requestNestVolume();
    const volume = nestView.volume;
    if (!volume) {
        put("space-caption", tr(nestView.error || "Reading committed nest geometry…"));
        app.hits = [];
        return;
    }
    const [x, bottom, z, right, roof, far] = volume.bounds_q;
    const q = volume.quantum_m, origin = volume.origin_m;
    const clipped = Number($("nest-depth").value), top = roof - clipped;
    const transparent = $("nest-transparent").checked;
    const center = app.meta.colonies[0].position_m;
    const scale = $("nest-scale").value;
    const follow = app.follow && state.ants.find(ant => ant.id === app.selected);
    const focus = (follow && (follow.display_position_m || follow.position_m)) || nestView.focus || center;
    const field = scale === "world" ? Math.max(...[0, 2].map(i => app.meta.bounds_m[1][i] - app.meta.bounds_m[0][i])) :
        scale === "chamber" ? 24 * q : Math.max(right - x, far - z) * q * 1.04;
    const {project, depth} = nestProjection(width, height, focus, field);
    const unit = Math.min(width-40,height*1.12)*nestView.zoom/field;
    const coordinate = point => point.map((value, i) => origin[i] + value * q);
    const cutY = origin[1] + top * q;
    const above = position => position[1] >= planeSurface() - 1e-10;
    const within = position => [0, 1, 2].every(i => position[i] >= origin[i] + volume.bounds_q[i] * q - 1e-10 &&
        position[i] <= origin[i] + volume.bounds_q[i + 3] * q + 1e-10);
    const visible = position => above(position) || within(position) && position[1] <= cutY + 1e-10;
    if (!nestView.faces || nestView.ceiling !== top) {
        const began = performance.now();
        nestView.faces = nestFaces(nestView.cells, volume.dimensions, top - bottom).map(face => ({...face,
            points: face.vertices.map(p => coordinate([p[0] + x, p[1] + bottom, p[2] + z]))}));
        nestView.ceiling = top;
        nestView.buildMs = performance.now() - began;
        nestView.built++;
    }
    const surfaceY = planeSurface(), surface = app.meta.surface;
    const bounds = surface ? [surface.origin_m[0], surface.origin_m[2],
        surface.origin_m[0] + surface.cell_m * surface.width, surface.origin_m[2] + surface.cell_m * surface.height] : null;
    if (bounds) {
        const [a, b, c, d] = bounds;
        ctx.setLineDash([5, 5]);
        nestPolygon(ctx, [[a, surfaceY, b], [c, surfaceY, b], [c, surfaceY, d], [a, surfaceY, d]].map(project),
            null, "#61816e");
        ctx.setLineDash([]);
    }
    const layers = [];
    for (const f of nestView.faces) {
        if (f.sign * depth[f.axis] < 0) continue;
        // In x-ray mode the real roof remains visible but cannot conceal actors below it.
        const shade = f.material === 2 ? ["#657379", "#879397", "#515e62"] : ["#8d6247", "#c28e60", "#664433"];
        const polygon = f.points.map(project), order = polygon.reduce((n, p) => n + p[2], 0) / 4;
        layers.push({polygon, order, fill: shade[f.axis], cap: f.cap});
    }
    const points = [], actors = [], events = [];
    for (const ant of state.ants) {
        const position = ant.display_position_m || ant.position_m;
        if (!visible(position)) continue;
        const p = project(position);
        if (p[0] < -15 || p[1] < -15 || p[0] > width + 15 || p[1] > height + 15) continue;
        const size = ant.stage === "Adult" ? adultGlyphSize(ant,app.meta.settings.geometry,unit) :
            Math.max(2,unit*(ant.stage === "Egg" ? .00019 : .00030));
        const angle = adultHeading(ant,project,app.renderedTimeMs);
        actors.push({ant, p, size, angle, order: p[2]});
    }
    const add = (site, message, color, offset) => {
        if (site && visible(site)) points.push({p: project(site), message, color, offset});
    };
    for (const source of state.sources || []) if (source.stock_ug.some(n => n > 0)) {
        const water = !(source.stock_ug[0] || source.stock_ug[1]);
        add(source.position_m, water ? "Water" : "Food source", water ? "#92d6ec" : "#92ddb5", [-31,-40]);
    }
    add(center, "Nest depot", "#eed29a", [39,42]);
    const habitat = app.live ? liveView.state.habitat : app.meta.settings.ecological?.founding_habitat;
    add(habitat?.brood_site_m, habitat?.sealed_chamber ? "Brood area" : "Brood chamber","#dcb7da", [-32,45]);
    const opening = app.geometry.openings || [];
    if (opening.length) add(opening[Math.floor(opening.length / 2)], "Open entrance", "#bcdea5", [23,-27]);
    if (app.selectedFact?.position_m && visible(app.selectedFact.position_m)) events.push(app.selectedFact);
    else if (app.live && liveView.state.running && liveView.state.rate === 1) {
        const at = app.renderedTimeMs;
        const recent = [...liveView.state.actions, ...liveView.state.events.filter(event =>
            ["AntDied", "AntBorn", "SoilExcavated", "SoilDropped", "FoodCollected", "FoodDelivered"].includes(event.kind))];
        const moment = recent.find(event => event.time_ms <= at && at - event.time_ms <= 2300 && visible(event.position_m));
        if (moment) events.push(moment);
    }
    const paintFace = ({polygon, cap, fill}) => {
        ctx.globalAlpha = cap && transparent ? .14 : transparent ? .86 : 1;
        nestPolygon(ctx,polygon,fill,"#eab88f34");
        const grain = soilTexture(ctx);
        if (grain && !cap) {
            ctx.globalAlpha *= .5;
            nestPolygon(ctx,polygon,grain,null);
        }
        ctx.globalAlpha = 1;
    };
    const drawActor = ({ant, p, size, angle}) => nestAnt(ctx, ant, p, angle, size);
    if (transparent) {
        layers.sort((a, b) => a.order - b.order).forEach(paintFace);
        actors.sort((a, b) => a.order - b.order).forEach(drawActor);
    } else {
        layers.concat(actors).sort((a, b) => a.order - b.order).forEach(item => item.ant ? drawActor(item) : paintFace(item));
    }
    drawSoilParcels(ctx,state.soil_piles,project,visible,unit);
    const scaleMm = unit>40000 ? 1 : unit>9000 ? 2 : unit>2000 ? 10 : 50;
    const bar = scaleMm*unit/1000, rulerY = height-22;
    ctx.strokeStyle = "#d9d4bc";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(19,rulerY-3); ctx.lineTo(19,rulerY); ctx.lineTo(19+bar,rulerY); ctx.lineTo(19+bar,rulerY-3);
    ctx.stroke();
    ctx.fillStyle = "#d9d4bc"; ctx.font = "11px system-ui";
    ctx.fillText(withUnit(scaleMm,"mm"),19,rulerY-7);
    for (const {p, message, color, offset} of points)
        nestCallout(ctx,p,tr(message),color,offset,width,height);
    if (app.follow && app.path.length) {
        ctx.fillStyle = "#c5b0e9";
        for (const event of app.path) if (visible(event.position_m)) {
            const p = project(event.position_m);
            ctx.fillRect(p[0] - 1, p[1] - 1, 2, 2);
        }
    }
    for (const event of events) nestCallout(ctx,project(event.position_m),
        `${tr(event.kind)} · #${event.id}`,"#f3da94",[44,-44],width,height);
    app.hits = actors.map(({ant, p, size}) => ({x: p[0], y: p[1], radius: size + 6, id: ant.id, ants: [ant]}));
    nestView.lastDrawMs = performance.now() - started;
    if (!motionOnly) {
        app.visible = actors.map(({ant}) => ant);
        $("show-largest").hidden = true;
        put("map-summary", tr("{count} individuals in this view", {count: actors.length}));
        put("map-detail", tr("Drag to rotate · Shift-drag to pan · Scroll to zoom") + (app.live ?
            " · " + tr("Visual interpolation of committed moves at 1×") : ""));
        renderLocation();
        put("nest-depth-value", `${decimal.format(clipped * q * 1000)} mm`);
        put("space-caption", tr("Local material surfaces · {count} committed edits", {count: volume.revision}) +
            (volume.cropped ? " · " + tr("Local section of the terrain") : ""));
        legend("map-legend", [["soil", "Soil"], ["rock", "Rock"], ["queen", "Queen"], ["egg", "Eggs"],
            ["larva", "Larvae"], ["pupa", "Pupae"], ["worker", "Worker"], ["food", "Food source"],
            ...(state.soil_piles?.length ? [["soil", "Deposited soil"]] : [])]);
    }
}
