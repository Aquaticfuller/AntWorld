"""The volume and the independent 2D section must describe the same material."""

from base64 import b64decode
import unittest

from op0.geometry import MAX_PIXELS, nest_volume, slice_at


class NestVolumeTests(unittest.TestCase):
    def test_edit_order_rock_and_negative_quantized_coordinates(self):
        geometry = dict(solid=[-5, -8, -7, 6, 0, 6], origin_m=[.01, 0, -.02], quantum_m=.002,
                        voids=[[-3, -8, -4, 4, -1, 5]], rocks=[[0, -5, -2, 2, -4, 3]])
        edits = [dict(kind=0, box_q=[0, -6, -3, 6, 0, 2]), dict(kind=3, box_q=[2, -5, -2, 6, -2, 1]),
                 dict(kind=0, box_q=[3, -5, -2, 4, -2, 1])]
        block = nest_volume(geometry, edits, [0, -.01, 0])
        self.assertEqual(block["revision"], len(edits))
        self.assertFalse(block["cropped"])
        cells = b64decode(block["materials_b64"])
        left, bottom, front, _, top, _ = block["bounds_q"]
        width, depth, height = block["dimensions"]
        self.assertEqual(len(cells), width * depth * height)
        self.assertEqual(set(cells), {0, 1, 2})
        for layer in range(bottom, top):
            expected = slice_at(geometry, edits, "y", layer)["rows"]
            for row in range(height):
                at = (row * depth + layer - bottom) * width
                self.assertEqual(cells[at:at + width], bytes(map(int, expected[row])), (left, layer, front + row))

    def test_large_terrain_is_bounded(self):
        geometry = dict(solid=[-12000,-3000,-12000,12000,0,12000], origin_m=[0,0,0], quantum_m=.001,
                        voids=[], rocks=[])
        block = nest_volume(geometry, [], (0, -.1, 0))
        self.assertTrue(block["cropped"])
        cells = b64decode(block["materials_b64"])
        self.assertLessEqual(len(cells), MAX_PIXELS)
        self.assertEqual(set(cells), {1})
