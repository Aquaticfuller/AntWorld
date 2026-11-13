"""Render slices from the Core's half-open, quantized material boxes."""

from .codec import require


AXES = {"x": (2, 1, 0), "y": (0, 2, 1), "z": (0, 1, 2)}
MAX_PIXELS = 262_144


def slice_at(geometry, edits, axis, plane, window=None):
    require(axis in AXES, "Slice axis must be x, y or z")
    u, v, n = AXES[axis]
    solid = geometry["solid"]
    require(solid[n] <= plane < solid[n + 3], "Slice lies outside the initial solid bounds")
    x, y, end_x, end_y = window or (solid[u], solid[v], solid[u + 3], solid[v + 3])
    require(solid[u] <= x < end_x <= solid[u + 3] and solid[v] <= y < end_y <= solid[v + 3],
            "Slice window lies outside the initial solid bounds")
    width, height = end_x - x, end_y - y
    require(width * height <= MAX_PIXELS, "Slice is too large; request a smaller quantized window")
    cells = [bytearray(b"1" * width) for _ in range(height)]

    def paint(box, material):
        if box[n] <= plane < box[n + 3]:
            left, right = max(x, box[u]), min(end_x, box[u + 3])
            if right > left:
                segment = material * (right - left)
                for row in range(max(y, box[v]), min(end_y, box[v + 3])):
                    cells[row - y][left - x:right - x] = segment

    for box in geometry["voids"]:
        paint(box, b"0")
    for edit in edits:
        paint(edit["box_q"], b"0" if edit["kind"] == 0 else b"1")
    for box in geometry["rocks"]:
        paint(box, b"2")
    return dict(axis=axis, plane_q=plane, axes=[u, v, n], bounds_q=[x, y, end_x, end_y],
                rows=[row.decode("ascii") for row in cells], quantum_m=geometry["quantum_m"],
                origin_m=geometry["origin_m"], evidence="RECONSTRUCTED",
                materials={"0": "Void", "1": "Soil", "2": "Rock"})


def clear_centers(geometry, edits, section):
    """Test the static unloaded body cube around each quantized slice point."""
    u, v, n = section["axes"]
    x, y, end_x, end_y = section["bounds_q"]
    solid, half = geometry["solid"], geometry["body_half_q"]
    require(1 <= half <= 8, "Unsupported body clearance extent")
    left, bottom = max(solid[u], x-half), max(solid[v], y-half)
    right, top = min(solid[u+3], end_x+half), min(solid[v+3], end_y+half)
    width, height = right-left, top-bottom
    require(width*height <= MAX_PIXELS, "Clearance window is too large")
    solid_count = [bytearray(width) for _ in range(height)]
    plane = section["plane_q"]
    for layer in range(max(solid[n], plane-half), min(solid[n+3], plane+half)):
        rows = slice_at(geometry, edits, section["axis"], layer, (left, bottom, right, top))["rows"]
        for dest, values in zip(solid_count, rows):
            for col, value in enumerate(values):
                dest[col] += value != "0"
    sums = [[0] * (width+1)]
    for row in solid_count:
        above = sums[-1]
        total = 0
        prefix = [0]
        for col, value in enumerate(row, 1):
            total += value
            prefix.append(above[col] + total)
        sums.append(prefix)
    rows = []
    for at_y in range(y, end_y):
        upper, lower = sums[min(top, at_y+half)-bottom], sums[max(bottom, at_y-half)-bottom]
        values = []
        for at_x in range(x, end_x):
            a, b = max(left, at_x-half)-left, min(right, at_x+half)-left
            values.append("1" if upper[b]-lower[b]-upper[a]+lower[a] == 0 else "0")
        rows.append("".join(values))
    return rows
