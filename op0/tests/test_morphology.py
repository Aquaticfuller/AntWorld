"""Separate wide room cores joined by a body-clear narrow corridor."""

import unittest

from op0.morphology import floor_shape


class MorphologyTest(unittest.TestCase):
    def test_two_wide_regions_separated_by_a_narrow_neck(self):
        geometry = dict(origin_m=(0,0,0), quantum_m=.0005, solid=(-30,-20,-30,30,0,30),
                        voids=[(-8,-10,-7,8,-6,7)], rocks=[], body_half_q=1, loaded_half_q=2)
        cuts = [dict(box_q=(8,-10,-2,18,-6,2),kind=0),
                dict(box_q=(18,-10,-7,30,-6,7),kind=0)]
        window=(-25,-24,30,24)
        before=floor_shape(geometry,[], -8,window,(0,0))
        first=floor_shape(geometry,cuts[:1], -8,window,(0,0))
        after=floor_shape(geometry,cuts, -8,window,(0,0))
        self.assertEqual([len(p["rooms"]) for p in (before,first,after)],[1,1,2])
        self.assertGreater(len(after["corridor_q"]),4)
        self.assertTrue(after["necks_q"])
        self.assertGreater(after["loaded_floor_mm2"],before["loaded_floor_mm2"])
        sealed = cuts + [dict(box_q=(11,-10,-2,12,-6,2),kind=1)]
        self.assertEqual(len(floor_shape(geometry,sealed,-8,window,(0,0))["rooms"]),1)
