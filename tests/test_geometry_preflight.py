"""Asset-free candidate triangle checks, never native-game collision tests."""
import math
import unittest

from tools.geometry_preflight import preflight_mesh, plan_native_surfaces, native_cell_span, native_integer_normal
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
        self.assertFalse(result["native_surface_pool_capacity_verified"])
        self.assertFalse(result["native_material_and_room_verified"])
        self.assertEqual(result["vertices_mario_candidate"],
                         ((10.0, 20.0, 30.0), (14.0, 20.0, 30.0), (10.0, 20.0, 26.0)))
        self.assertEqual(result["triangles"][0]["indices"], (0, 1, 2))
        self.assertAlmostEqual(result["triangles"][0]["source_double_area"], 4)
        self.assertAlmostEqual(result["triangles"][0]["mapped_double_area"], 16)
        self.assertEqual(result["triangles"][0]["s16_trunc_vertices"],
                         ((10, 20, 30), (14, 20, 30), (10, 20, 26)))
        self.assertAlmostEqual(result["triangles"][0]["s16_trunc_double_area"], 16)
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

    def test_rejects_float32_triangle_collapsing_in_native_s16_surface(self):
        # Float32 preserves this triangle, but the original sm64ex Surface
        # Vec3s integer vertex representation cannot represent it as a floor.
        with self.assertRaisesRegex(ValueError, "degenerate"):
            preflight_mesh(**fixture(
                frame_map=FrameMap((0, 0, 0), (100, 0, 100), 1, 0),
                vertices=[(0, 0, 0), (0, 0, 0.4), (0.4, 0, 0)]))

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
            preflight_mesh(**fixture(vertices=[(0, 0, 0)]*4097))
        with self.assertRaises(ValueError):
            preflight_mesh(**fixture(triangles=[(0, 1, 2)]*513))

    def test_no_game_material_ids_or_collisions_are_inferred(self):
        result = preflight_mesh(**fixture())
        self.assertNotIn("collision_ready", result)
        self.assertNotIn("material_id", result)
        self.assertNotIn("native_surface_type", result)
        self.assertEqual(result["frame_identity"], "OPERATOR_SUPPLIED_NOT_RUNTIME_VERIFIED")

    def test_native_materials_and_pool_reservation_are_explicit(self):
        preview = preflight_mesh(**fixture())
        material=dict(provenance="AUTHORED_SYNTHETIC",native_type=0,room=0)
        counts=dict(surface_capacity=2,node_capacity=256,surfaces_used=1,nodes_used=0)
        result=plan_native_surfaces(preview,materials=[material],**counts)
        self.assertEqual(result["surfaces"][0]["partition"],"floor")
        self.assertEqual(result["surfaces"][0]["unit_normal"],(0,1,0))
        self.assertEqual(result["nodes_required"],4)  # 50-unit border includes neighboring cells
        for overrides in (dict(surfaces_used=2),dict(node_capacity=3),dict(node_capacity=True),
                          dict(surfaces_used=-1),dict(nodes_used=257)):
            with self.assertRaises(ValueError):
                plan_native_surfaces(preview,materials=[material],**{**counts,**overrides})
        for bad in ({**material,"native_type":True}, {**material,"native_type":999},
                    {**material,"provenance":"UNKNOWN_CRASH_LEAF"},{**material,"room":128}):
            with self.assertRaises(ValueError):
                plan_native_surfaces(preview,materials=[bad],**counts)
        with self.assertRaises(ValueError):
            plan_native_surfaces(preview,materials=[],**counts)

    def test_native_integer_arithmetic_and_height_padding_guards(self):
        for vertices in ([(0,-32768,0),(0,-32768,100),(100,-32768,0)],):
            with self.assertRaisesRegex(ValueError,"overflow"):
                preflight_mesh(**fixture(vertices=vertices,
                    frame_map=FrameMap((0,0,0),(0,0,0),1,0)))
        # A general s16 stream can overflow s32 cross-products even though the
        # earlier conservative query guard rejects this large XZ footprint.
        with self.assertRaisesRegex(ValueError,"overflow"):
            native_integer_normal([(-32760,-32760,-32760),(32760,32760,-32760),(-32760,32760,32760)])

    def test_cell_border_buffer_is_not_one_node_per_triangle(self):
        self.assertEqual(native_cell_span([(0,0,0),(0,0,100),(100,0,0)]),(7,8,7,8))
        self.assertEqual(native_cell_span([(100,0,100),(100,0,200),(200,0,100)]),(8,8,8,8))


if __name__ == "__main__":
    unittest.main()
