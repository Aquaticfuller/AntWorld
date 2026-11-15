"""Measure a supported, loaded-body floor section from committed voxel geometry."""

from collections import deque

from .geometry import clear_centers, slice_at


AXIAL = ((1, 0), (0, 1), (-1, 0), (0, -1))
RING = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))


def adjacent(point, directions=AXIAL):
    return [(point[0]+dx, point[1]+dy) for dx, dy in directions]


def regions(pixels, directions=AXIAL):
    left = set(pixels)
    result = []
    while left:
        origin = min(left)
        cell = [origin]
        left.remove(origin)
        for point in cell:
            for other in adjacent(point, directions):
                if other in left:
                    left.remove(other)
                    cell.append(other)
        result.append(cell)
    return result


def clearance(pixels):
    boundary = [p for p in sorted(pixels) if any(q not in pixels for q in adjacent(p, RING))]
    dist = dict.fromkeys(boundary, 1)
    pending = deque(boundary)
    while pending:
        p = pending.popleft()
        for q in adjacent(p, RING):
            if q in pixels and q not in dist:
                dist[q] = dist[p]+1
                pending.append(q)
    return dist


def skeleton(pixels):
    """Topology-preserving Zhang–Suen thinning of the supported center mask."""
    remaining = set(pixels)
    while True:
        changed = False
        for side in (0, 1):
            remove = []
            for p in remaining:
                ring = [q in remaining for q in adjacent(p, RING)]
                if not 2 <= sum(ring) <= 6:
                    continue
                if sum(not ring[i-1] and ring[i] for i in range(8)) != 1:
                    continue
                n, e, s, w = ring[0], ring[2], ring[4], ring[6]
                if (n and e and (w if side else s)) or (s and w and (n if side else e)):
                    continue
                remove.append(p)
            remaining.difference_update(remove)
            changed |= bool(remove)
        if not changed:
            return remaining


def floor_shape(geometry, edits, layer, window, origin_q, occupants=()):
    """Widths use the voxel plane. Connectivity uses actual supported clearance."""
    section = slice_at(geometry, edits, "y", layer, window)
    floor = {(x, z) for z, row in enumerate(section["rows"], window[1])
             for x, cell in enumerate(row, window[0]) if cell == "0"}
    half = geometry["loaded_half_q"]
    below_y = layer-half-1
    if below_y < geometry["solid"][1]:
        below = ["1"*(window[2]-window[0])]*(window[3]-window[1])
    else:
        below = slice_at(geometry, edits, "y", below_y, window)["rows"]
    fits = clear_centers(geometry | {"body_half_q": half}, edits, section)
    supported = {(x, z) for x, z in floor
                 if fits[z-window[1]][x-window[0]] == "1" and below[z-window[1]][x-window[0]] != "0"}
    route = next((set(c) for c in regions(supported) if tuple(origin_q) in c), set())
    radius = clearance(floor)
    threshold = 2*half+1
    wide = {p for p in route if radius[p] >= threshold}
    cores = sorted((c for c in regions(wide) if len(c) >= 4), key=lambda c: (-len(c), min(c)))
    lines = skeleton(route)

    def edges(p):
        for q in adjacent(p, RING):
            if q not in lines:
                continue
            if q[0] != p[0] and q[1] != p[1]:
                if (q[0], p[1]) in lines or (p[0], q[1]) in lines:
                    continue
            yield q

    # Suppress one- and two-voxel edge stubs before identifying branch nodes.
    for _ in range(2):
        lines.difference_update([p for p in lines if p not in wide and sum(1 for _ in edges(p)) < 2])
    branch = {p for p in lines-wide if sum(1 for _ in edges(p)) >= 3}
    necks = sorted(p for p in lines-wide if any(q in wide for q in adjacent(p, RING)))
    quantum = geometry["quantum_m"]*1000
    perimeter = sum(q not in floor for p in floor for q in adjacent(p))*quantum
    by_cell = {}
    for ant in occupants:
        if ant["stage"] not in (3, "Adult") or ant["caste"] not in (0, "Worker"):
            continue
        xyz = [round((v-o)/geometry["quantum_m"]) for v, o in zip(ant["position_m"], geometry["origin_m"], strict=True)]
        if xyz[1] == layer:
            by_cell[(xyz[0], xyz[2])] = by_cell.get((xyz[0], xyz[2]), 0)+1
    rooms = [dict(center_q=min(c, key=lambda p: (-radius[p], p)), area_mm2=len(c)*quantum**2,
                  workers=sum(by_cell.get(p, 0) for p in c), initial=tuple(origin_q) in c) for c in cores]
    return dict(plane_q=layer, area_mm2=len(floor)*quantum**2, perimeter_mm=perimeter,
                loaded_floor_mm2=len(route)*quantum**2, rooms=rooms, corridor_q=sorted(lines-wide),
                junctions_q=sorted(min(c) for c in regions(branch, RING)), necks_q=necks,
                supported_workers=sum(by_cell.get(p, 0) for p in route),
                window_contact=any(x in (window[0],window[2]-1) or z in (window[1],window[3]-1) for x, z in floor))
