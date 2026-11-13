"""The versioned, read-only API shared by the browser and terminal."""

from collections import Counter, OrderedDict
from contextlib import closing
import json
from threading import Lock
from urllib.parse import parse_qs, urlsplit
import zlib

from . import SCHEMA
from .codec import CASTES, DEATHS, FACETS, HIGHLIGHTS, KINDS, MASK, PROGRAMS, STAGES, decode_fact, label, require, sql_id
from .geometry import AXES, MAX_PIXELS, clear_centers, slice_at
from .index import BLOCK_RECORDS, COUNTERS, LEDGER


def integer(options, name, default, low=0, high=(1 << 53) - 1):
    raw = options.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer") from None
    require(low <= value <= high, f"{name} is outside [{low}, {high}]")
    return value


def records(db, start, stop, kinds=(), ant=None, limit=51, reverse=False, actors_only=False):
    conditions = ["id>? AND id<=?"]
    params = [start, stop]
    if kinds:
        conditions.append("kind IN (" + ",".join("?" for _ in kinds) + ")")
        params.extend(sorted(kinds))
    if ant is not None:
        if actors_only:
            conditions.append("actor=?")
            params.append(ant)
        else:
            conditions.append("(actor=? OR related=?)")
            params.extend((ant, ant))
    order = "DESC" if reverse else "ASC"
    return db.execute(f"SELECT id,offset FROM facts WHERE {' AND '.join(conditions)} ORDER BY id {order} LIMIT ?",
                      (*params, limit)).fetchall()


def cursor_at(db, stamp, inclusive=True):
    comparison = "<=" if inclusive else "<"
    row = db.execute(f"SELECT id FROM facts WHERE time{comparison}? ORDER BY time DESC,id DESC LIMIT 1", (stamp,)).fetchone()
    return row[0] if row else 0


def cut_at(db, meta, options):
    if "event" in options:
        event = integer(options, "event", 0, 1, meta["facts"])
        row = db.execute("SELECT time FROM facts WHERE id=?", (event,)).fetchone()
        require(row is not None, "Unknown event")
        return row[0], event
    stamp = integer(options, "time_ms", 0, 0, meta["end_ms"])
    return stamp, cursor_at(db, stamp)


def positions(db, cursor):
    # One bounded seek per ant at this cut. Dead individuals stay in the assigned identity table.
    return db.execute("""SELECT a.id,a.caste,c.x,c.y,c.z,c.stage,c.program,c.event
        FROM ants a JOIN changes c ON c.ant=a.id AND c.event=(
            SELECT event FROM changes WHERE ant=a.id AND event<=? ORDER BY event DESC LIMIT 1)
        WHERE a.birth_event<=? AND (a.death_event IS NULL OR a.death_event>?) ORDER BY a.id""",
        (cursor, cursor, cursor))


def state_at(db, meta, stamp, cursor, include_space=True):
    day = db.execute("SELECT time,cursor,value FROM daily WHERE time<=? AND cursor<=? ORDER BY time DESC LIMIT 1",
                     (stamp, cursor)).fetchone()
    base = json.loads(day[2]) if day else {}
    after = day[1] if day else 0
    pop = dict(eggs=0, larvae=0, pupae=0, adults=0, workers=0, queens_alive=[])
    names = ("eggs", "larvae", "pupae", "adults")
    ants = []
    for aid, caste, x, y, z, stage, program, event in positions(db, cursor):
        identifier = str(aid & MASK)
        pop[names[stage]] += 1
        if stage == 3 and caste == 0:
            pop["workers"] += 1
        elif stage == 3 and caste == 1:
            pop["queens_alive"].append(identifier)
        if include_space:
            ants.append(dict(id=identifier, caste=label(CASTES, caste), stage=label(STAGES, stage),
                             position_m=[x, y, z], program=label(PROGRAMS, program), at_event=str(event)))
    sources, external = [], [0] * 4
    for sid, x, y, z, *mass in db.execute("""SELECT s.id,s.x,s.y,s.z,h.c,h.p,h.w,h.o
            FROM sources s JOIN source_history h ON h.source=s.id AND h.event=(
                SELECT event FROM source_history WHERE source=s.id AND event<=? ORDER BY event DESC LIMIT 1)
            WHERE s.created<=? ORDER BY s.id""", (cursor, cursor)):
        external = [a + b for a, b in zip(external, mass)]
        if include_space:
            sources.append(dict(id=str(sid & MASK), position_m=[x, y, z], stock_ug=mass))
    nest = db.execute("SELECT c,p,w,o FROM nest_history WHERE event<=? ORDER BY event DESC LIMIT 1", (cursor,)).fetchone()
    counters = Counter(base.get("cumulative", {}))
    for kind, count in db.execute("SELECT kind,count(*) FROM facts WHERE id>? AND id<=? AND kind IN (" +
                                  ",".join("?" for _ in COUNTERS) + ") GROUP BY kind", (after, cursor, *COUNTERS)):
        counters[COUNTERS[kind]] += count
    deaths = {label(DEATHS, cause): n for cause, n in db.execute(
        "SELECT death,count(*) FROM ants WHERE death_event<=? GROUP BY death", (cursor,))}
    revision, dig, fill = base.get("geometry_revision", 0), base.get("excavated_q3", 0), base.get("filled_q3", 0)
    for raw, in db.execute("SELECT value FROM edits WHERE event>? AND event<=? ORDER BY event", (after, cursor)):
        edit = json.loads(raw)
        revision += 1
        if edit["kind"] == 0:
            dig += edit["volume_q3"]
        else:
            fill += edit["volume_q3"]
    queen = None
    if pop["queens_alive"]:
        queen = sample_at(db, sql_id(int(pop["queens_alive"][0])), stamp, cursor)
    geometry = meta["settings"]["geometry"]
    return dict(time_ms=stamp, cursor=str(cursor), evidence="RECONSTRUCTED", last_daily_cut_ms=day[0] if day else None,
                population=pop, queens_last_sample=queen, ants=ants, sources=sources,
                external_ug=external, nest_ug=nest or [0] * 4, mass_order=LEDGER, cumulative=counters,
                deaths=deaths, geometry_revision=revision, excavated_q3=dig, filled_q3=fill,
                net_removed_m3=(dig-fill) * geometry["quantum_m"] ** 3 if geometry else None)


def sample_at(db, ant, stamp, cursor):
    row = db.execute("SELECT time,cursor,value FROM samples WHERE ant=? AND time<=? AND cursor<=? "
                     "ORDER BY time DESC,cursor DESC LIMIT 1", (ant, stamp, cursor)).fetchone()
    if row is None:
        return None
    return dict(**json.loads(row[2]), time_ms=row[0], cursor=str(row[1]), evidence="CUT_SNAPSHOT")


class ReadAPI:
    def __init__(self, catalog):
        self.catalog = catalog
        self.blocks = OrderedDict()
        self.blocks_lock = Lock()

    def fact(self, db, meta, row):
        identifier, offset = row
        first = ((identifier - 1) // BLOCK_RECORDS) * BLOCK_RECORDS + 1
        key = meta["key"], first
        with self.blocks_lock:
            raw = self.blocks.get(key)
            if raw is None:
                block = db.execute("SELECT packed FROM blocks WHERE first=?", (first,)).fetchone()
                require(block is not None, "Browse index lacks a fact block")
                raw = zlib.decompress(block[0])
                self.blocks[key] = raw
                if len(self.blocks) > 12:
                    self.blocks.popitem(last=False)
            else:
                self.blocks.move_to_end(key)
        _, fact = decode_fact(raw, offset)
        require(fact.id == identifier, "Browse index fact references the wrong record")
        return fact

    def page(self, db, meta, options):
        lo = integer(options, "since_ms", 0, 0, meta["end_ms"])
        hi = integer(options, "until_ms", meta["end_ms"], lo, meta["end_ms"])
        start = max(integer(options, "after", 0, 0, meta["facts"]), cursor_at(db, lo, inclusive=False))
        stop = cursor_at(db, hi)
        if "cut_event" in options:
            stop = min(stop, integer(options, "cut_event", stop, 0, meta["facts"]))
        limit = integer(options, "limit", 50, 1, 200)
        group = options.get("group", "highlights")
        require(group in ("all", "highlights", *FACETS), "Unknown event category")
        kinds = HIGHLIGHTS if group == "highlights" else FACETS.get(group, ())
        ant = sql_id(integer(options, "ant", 0, 1, MASK)) if "ant" in options else None
        rows = records(db, start, stop, kinds, ant, limit + 1)
        events = [self.fact(db, meta, r).packet() for r in rows[:limit]]
        return dict(events=events, next_after=events[-1]["id"] if len(rows) > limit else None,
                    since_ms=lo, until_ms=hi, world_id=meta["world_id"])

    def event(self, db, meta, options):
        identifier = integer(options, "id", None, 1, meta["facts"])
        row = db.execute("SELECT id,offset FROM facts WHERE id=?", (identifier,)).fetchone()
        require(row is not None, "Unknown event")
        event = self.fact(db, meta, row).packet()
        if "parcel" in event:
            event["geometry_edits"] = [edit_packet(raw) for raw, in
                                       db.execute("SELECT value FROM edits WHERE parcel=? AND event<=? ORDER BY event",
                                                  (sql_id(int(event["parcel"])), identifier))]
        if event["kind"] == "RecruitmentCue":
            event["origin_fact"] = event["payload"]
        elif event["kind"] in ("RecruitmentObserved", "RecruitmentActivated"):
            event["origin_fact"] = event["auxiliary"]
        return event

    def ant(self, db, meta, options, stamp, cursor):
        aid = integer(options, "id", None, 1, MASK)
        ant = sql_id(aid)
        row = db.execute("SELECT mother,colony,born,birth_event,caste,seeded,dead,death_event,death FROM ants WHERE id=?",
                         (ant,)).fetchone()
        require(row is not None, "Unknown ant in this archive")
        mother, colony, born, birth_event, caste, seeded, dead, death_event, death = row
        state = db.execute("SELECT x,y,z,stage,program,event FROM changes WHERE ant=? AND event<=? ORDER BY event DESC LIMIT 1",
                           (ant, cursor)).fetchone()
        sample = sample_at(db, ant, stamp, cursor)
        life = [self.fact(db, meta, r).packet() for r in records(db, 0, meta["facts"], (2, 7, 8, 35), ant, 12, actors_only=True)]
        activity = [self.fact(db, meta, r).packet() for r in records(
            db, 0, cursor, (*HIGHLIGHTS, 19, 20, 46, 47, 50, 51, 53, 54, 55, 57), ant, 28, reverse=True)]
        return dict(id=str(aid), world_id=meta["world_id"], time_ms=stamp, cursor=str(cursor), mother=mother, colony=colony,
                    caste=label(CASTES, caste), stage=label(STAGES, state[3]) if state else "Not yet present",
                    program=label(PROGRAMS, state[4]) if state else "Not recorded",
                    status="Not yet present" if not state else "Dead" if state[3] == 4 else "Alive",
                    position_m=state[:3] if state else None, born_ms=None if seeded else born, seeded_ms=born if seeded else None,
                    birth_event=str(birth_event), died_ms=dead if death_event and death_event <= cursor else None,
                    death_cause=label(DEATHS, death) if death_event and death_event <= cursor else None,
                    life_events=life, activity=activity, sample=sample)

    def track(self, db, meta, options, cursor):
        ant = sql_id(integer(options, "id", None, 1, MASK))
        limit = integer(options, "limit", 200, 1, 200)
        rows = records(db, 0, cursor, (2, 4, 35, 43), ant, limit + 1, reverse=True, actors_only=True)
        facts = [self.fact(db, meta, r) for r in reversed(rows[:limit])]
        return dict(points=[dict(id=str(f.id), time_ms=f.time, position_m=f.position, evidence="COMMITTED_FACT") for f in facts],
                    earlier_points_available=len(rows) > limit, connected_segments=False)

    def cohort(self, db, meta, cursor):
        saved = meta["first_cohort"]
        if not saved or cursor < int(saved["cursor"]):
            return None
        deaths = Counter()
        eclosed = unfed = 0
        # Fixed membership at the first recorded larval census, counted through the requested cut.
        for aid in saved["members"]:
            ant = sql_id(int(aid))
            eclosed += bool(db.execute("SELECT 1 FROM changes WHERE ant=? AND stage=3 AND event<=? LIMIT 1", (ant, cursor)).fetchone())
            unfed += not db.execute("SELECT 1 FROM feedings WHERE ant=? AND event<=? LIMIT 1", (ant, cursor)).fetchone()
            death = db.execute("SELECT death FROM ants WHERE id=? AND death_event<=?", (ant, cursor)).fetchone()
            if death:
                deaths[label(DEATHS, death[0])] += 1
        return dict(time_ms=saved["time_ms"], size=len(saved["members"]), members=saved["members"],
                    eclosed=eclosed, without_recorded_feeding=unfed, deaths=deaths)

    def geometry(self, db, meta, options, cursor):
        geometry = meta["settings"]["geometry"]
        if geometry is None:
            return dict(slice=None, openings=None, reason="No authoritative 3D geometry was recorded")
        axis = options.get("axis", "z")
        require(axis in AXES, "Unknown slice axis")
        u, v, n = AXES[axis]
        solid = geometry["solid"]
        default = (solid[n] + solid[n+3]) // 2
        layer = integer(options, "layer_q", default, solid[n], solid[n+3] - 1)
        window = None
        if "window" in options:
            try:
                window = tuple(int(x) for x in options["window"].split(","))
            except ValueError:
                raise ValueError("Use four integer bounds for window") from None
            require(len(window) == 4, "Use four integer bounds for window")
        elif (solid[u+3] - solid[u]) * (solid[v+3] - solid[v]) > MAX_PIXELS:
            window = solid[u], solid[v], min(solid[u+3], solid[u]+480), min(solid[v+3], solid[v]+480)
        edits = [json.loads(raw) for raw, in db.execute("SELECT value FROM edits WHERE event<=? ORDER BY event", (cursor,))]
        sliced = slice_at(geometry, edits, axis, layer, window)
        if options.get("clearance") == "1":
            sliced["unloaded_body_clear"] = clear_centers(geometry, edits, sliced)
        openings = None
        if (solid[3] - solid[0]) * (solid[5] - solid[2]) <= MAX_PIXELS:
            roof = slice_at(geometry, edits, "y", solid[4] - 1)
            origin, scale = geometry["origin_m"], geometry["quantum_m"]
            x, z = roof["bounds_q"][:2]
            openings = [[origin[0] + (x + col + .5) * scale, origin[1] + solid[4] * scale,
                         origin[2] + (z + row + .5) * scale]
                        for row, values in enumerate(roof["rows"]) for col, mat in enumerate(values) if mat == "0"]
        return dict(slice=sliced, openings=openings, opening_cell_m=geometry["quantum_m"], revision=len(edits),
                    geometry_bounds_q=solid, cropped=window is not None)

    def compare(self, options):
        require(options.get("left") != options.get("right"), "Choose two different archived worlds")
        a, left = self.catalog.data(options.get("left", ""))
        with closing(left) as ldb:
            b, right = self.catalog.data(options.get("right", ""))
            with closing(right) as rdb:
                return self.compare_open(a, ldb, b, rdb, options)

    def compare_open(self, a, ldb, b, rdb, options):
        stamp = integer(options, "time_ms", 0, 0, max(a["end_ms"], b["end_ms"]))
        results = []
        for meta, db in ((a, ldb), (b, rdb)):
            at = min(stamp, meta["end_ms"])
            cursor = cursor_at(db, at)
            results.append(dict(world=brief(meta), state=state_at(db, meta, at, cursor, False),
                                cohort=self.cohort(db, meta, cursor), outside_record=at != stamp))
        compared = {}
        for fields, left, right in (
            (("physics", "inner_physics", "seed", "geometry", "initial_maternal", "initial_external_ug", "initial_sources",
              "ecological", "care_enabled", "initial_workers"), a["settings"], b["settings"]),
            (("population", "layout", "supply"), a, b),
        ):
            for field in fields:
                lvalue, rvalue = left.get(field), right.get(field)
                status = "unknown" if lvalue is None or rvalue is None else "same" if lvalue == rvalue else "different"
                compared[field] = dict(left=lvalue, right=rvalue, status=status)
        return dict(worlds=results, settings=compared, individual_alignment=False, full_matching_inputs_verified=False)

    def dispatch(self, target):
        url = urlsplit(target)
        route = url.path.strip("/").split("/")
        require(route[:2] == ["api", "v1"], "Unknown API version or route")
        opts = parse_qs(url.query, max_num_fields=16)
        require(all(len(values) == 1 for values in opts.values()), "Repeated query parameter")
        options = {name: value[0] for name, value in opts.items()}
        path = route[2:]
        if path == ["catalog"]:
            result = [entry | {"worlds": [brief(w) for w in entry["worlds"]]} for entry in self.catalog.list()]
        elif len(path) == 2 and path[0] == "archive":
            worlds, warmed, elapsed = self.catalog.browse(path[1])
            result = dict(worlds=[brief(world) for world in worlds], cached=warmed, open_ms=round(elapsed, 2))
        elif path == ["compare"]:
            result = self.compare(options)
        else:
            require(len(path) == 3 and path[0] == "world", "Unknown API endpoint")
            _, world, operation = path
            meta, handle = self.catalog.data(world)
            with closing(handle) as db:
                result = self.world(db, meta, operation, options)
        return dict(schema=SCHEMA, data=result)

    def world(self, db, meta, operation, options):
        if operation == "meta":
            return meta
        if operation == "events":
            return self.page(db, meta, options)
        if operation == "event":
            return self.event(db, meta, options)
        if operation == "series":
            return [dict(time_ms=stamp, cursor=str(cursor), **json.loads(value))
                    for stamp, cursor, value in db.execute("SELECT time,cursor,value FROM daily ORDER BY time")]
        stamp, cursor = cut_at(db, meta, options)
        if operation == "state":
            return state_at(db, meta, stamp, cursor)
        if operation == "ant":
            return self.ant(db, meta, options, stamp, cursor)
        if operation == "path":
            return self.track(db, meta, options, cursor)
        if operation == "geometry":
            return self.geometry(db, meta, options, cursor)
        if operation == "cohort":
            return self.cohort(db, meta, cursor)
        raise ValueError("Unknown world endpoint")


def brief(meta):
    result = {name: meta[name] for name in ("key", "title", "world_id", "population", "layout", "supply", "scenario", "start_ms",
                                          "end_ms", "facts", "integrity", "readiness", "description", "final_population")}
    return dict(**result, physics=meta["settings"]["physics"], seed=meta["settings"]["seed"])


def edit_packet(raw):
    edit = json.loads(raw)
    return edit | {key: str(edit[key]) for key in ("event", "source", "actor", "parcel")}
