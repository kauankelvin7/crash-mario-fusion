"""Asset-free candidate triangle checks, never native-game collision tests."""
import math
import unittest

from tools.geometry_preflight import preflight_mesh
from tools.world_coordinates import FrameMap


def fixture(**overrides):
    data = {
        "vertices": [(0, 0, 0), (0, 0, 2), (2, 0, 0)],
        "triangles": [(0, 1, 2)],
        "frame_map": FrameMap((0, 0, 0), (10, 20, 30), 2, 90),
        "crash_level": 9,
        "calibrated_level": 9,
        "mario_frame": "SYNTHETIC_TEST_AREA_ONLY",
    }
    data.update(overrides)
    return data


class GeometryPreflightTests(unittest.TestCase):
    def test_synthetic_triangle_mapping_preserves_winding_and_area(self):
        result = preflight_mesh(**fixture())
        self.assertEqual(result["interpretation"], "SYNTHETIC_GEOMETRY_PREFLIGHT_ONLY")
        self.assertFalse(result["engine_collision_inserted"])
        self.assertFalse(result["engine_rendering_inserted"])
        self.assertEqual(result["vertices_mario_candidate"],
                         ((10.0, 20.0, 30.0), (14.0, 20.0, 30.0), (10.0, 20.0, 26.0)))
        self.assertEqual(result["triangles"][0]["indices"], (0, 1, 2))
        self.assertAlmostEqual(result["triangles"][0]["source_double_area"], 4)
        self.assertAlmostEqual(result["triangles"][0]["mapped_double_area"], 16)
        self.assertGreater(result["triangles"][0]["orientation_cosine"], 0.999)

    def test_needs_explicit_frame_identity_and_same_crash_level(self):
        for values in ({"crash_level": 10}, {"crash_level": True},
                       {"calibrated_level": False}, {"mario_frame": "  "},
                       {"frame_map": None}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                preflight_mesh(**fixture(**values))

    def test_rejects_malformed_indices_and_repeated_triangles(self):
        for faces in ([(0, 1)], [(0, 1, 3)], [(True, 1, 2)],
                      [(0, 0, 2)], [(0, 1, 2), (2, 1, 0)],
                      [], [(0, 1, -1)]):
            with self.subTest(faces=faces), self.assertRaises(ValueError):
                preflight_mesh(**fixture(triangles=faces))

    def test_rejects_zero_area_and_quantized_away_triangles(self):
        with self.assertRaisesRegex(ValueError, "degenerate"):
            preflight_mesh(**fixture(vertices=[(0, 0, 0), (1, 0, 0), (2, 0, 0)]))
        with self.assertRaisesRegex(ValueError, "degenerate"):
            preflight_mesh(**fixture(
                frame_map=FrameMap((0, 0, 0), (1000, 0, 1000), 1, 0),
                vertices=[(0, 0, 0), (0, 0, 1e-8), (1e-8, 0, 0)]))

    def test_rejects_nonfinite_points_and_out_of_native_query_bounds(self):
        with self.assertRaises(ValueError):
            preflight_mesh(**fixture(vertices=[(0, 0, 0), (math.nan, 0, 2), (2, 0, 0)]))
        with self.assertRaisesRegex(ValueError, "floor-query bounds"):
            preflight_mesh(**fixture(frame_map=FrameMap((0, 0, 0), (8200, 0, 0), 1, 0)))
        with self.assertRaisesRegex(ValueError, "floor-query bounds"):
            preflight_mesh(**fixture(frame_map=FrameMap((0, 0, 0), (0, 40000, 0), 1, 0)))

    def test_conservative_mesh_count_guard(self):
        with self.assertRaises(ValueError):
            preflight_mesh(**fixture(vertices=[]))
        with self.assertRaises(ValueError):
            preflight_mesh(**fixture(vertices=[(0, 0, 0)]*65536))

    def test_no_game_material_ids_or_collisions_are_inferred(self):
        result = preflight_mesh(**fixture())
        self.assertNotIn("collision_ready", result)
        self.assertNotIn("material_id", result)
        self.assertNotIn("native_surface_type", result)
        self.assertEqual(result["frame_identity"], "OPERATOR_SUPPLIED_NOT_RUNTIME_VERIFIED")


if __name__ == "__main__":
    unittest.main()
