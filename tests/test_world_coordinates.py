import math
import random
import unittest

from tools.world_coordinates import (FrameMap, decode_crash, encode_crash,
                                     map_log, sm64_floor_query_safe)


class WorldCoordinatesTests(unittest.TestCase):
    def test_signed_fixed_point_roundtrip_including_limits(self):
        for raw in ((-257, 513, -1), (-(2**31), 2**31-1, 0)):
            self.assertEqual(encode_crash(decode_crash(raw)), raw)
        self.assertEqual(decode_crash((-257, 513, -1)), (-1.00390625, 2.00390625, -0.00390625))
        for raw in ((2**31, 0, 0), (0, 0), (True, 0, 0), (1.0, 0, 0)):
            with self.assertRaises(ValueError):
                decode_crash(raw)

    def test_calibrated_transform_roundtrip_distance_and_up(self):
        mapping = FrameMap((10, -20, 30), (100, 200, -300), 2.5, 73)
        self.assertEqual(mapping.to_mario(mapping.crash_origin), mapping.mario_origin)
        rng = random.Random(64)
        for _ in range(100):
            position = tuple(rng.uniform(-2000, 2000) for _ in range(3))
            mapped = mapping.to_mario(position)
            recovered = mapping.to_crash(mapped)
            for before, after in zip(position, recovered):
                self.assertAlmostEqual(before, after, delta=0.0003)  # target float32 quantization
            self.assertAlmostEqual(math.dist(mapped, mapping.mario_origin),
                                   2.5*math.dist(position, mapping.crash_origin), delta=0.001)
        above = mapping.to_mario((10, -19, 30))
        self.assertEqual(above, (100, 202.5, -300))
        # Positive uniform scale + yaw preserves winding, avoiding floor/ceiling reflection.
        origin, a, b = (mapping.to_mario(p) for p in ((0, 0, 0), (0, 0, 1), (1, 0, 0)))
        ax, az = a[0]-origin[0], a[2]-origin[2]
        bx, bz = b[0]-origin[0], b[2]-origin[2]
        self.assertGreater(az*bx-ax*bz, 0)

    def test_reject_missing_invalid_or_overflowing_mapping(self):
        for scale in (0, -1, math.nan, math.inf, True):
            with self.assertRaises(ValueError):
                FrameMap((0, 0, 0), (0, 0, 0), scale, 0)
        with self.assertRaises(ValueError):
            FrameMap((0, 0, 0), (0, 0, 0), 1, math.inf)
        with self.assertRaises(ValueError):
            FrameMap((0, 0, 0), (0, 0, 0), 1e39, 0).to_mario((1, 0, 0))
        with self.assertRaises(ValueError):
            encode_crash((2**23, 0, 0))
        with self.assertRaises(ValueError):
            encode_crash((1e308, 0, 0))
        for mapping in (FrameMap((0, 0, 0), (0, 0, 0), 1e-50, 0),
                        FrameMap((0, 0, 0), (1e25, 0, 0), 1, 0)):
            with self.assertRaisesRegex(ValueError, "quantization"):
                mapping.to_mario((1, 0, 0))

    def test_native_floor_boundaries_do_not_wrap(self):
        self.assertTrue(sm64_floor_query_safe((8191, -32768, -8191)))
        for point in ((8192, 0, 0), (-8192, 0, 0), (0, 0, 8192),
                      (0, 32768, 0), (65536, 0, 0)):
            self.assertFalse(sm64_floor_query_safe(point))
        with self.assertRaises(ValueError):
            sm64_floor_query_safe((0, math.nan, 0))

    def test_read_only_native_log_mapping_and_level_guard(self):
        calibration = dict(schema_version=1, crash_level=9, mario_frame="operator test area",
                           crash_origin=[0, 0, 0], mario_origin=[10, 20, 30],
                           scale=2, yaw_degrees=90)
        log = "[cm64] motion_sample seq=11 n=1 y_raw=512 x_raw=-256 z_raw=768 crash_level=9"
        result = map_log(log, calibration)
        self.assertEqual(result["interpretation"], "OBSERVATION_ONLY")
        self.assertEqual(result["samples"][0]["mario_candidate"], (16, 24, 32))
        self.assertTrue(result["samples"][0]["floor_query_safe"])
        with self.assertRaises(ValueError):
            map_log(log.replace("crash_level=9", "crash_level=10"), calibration)
        with self.assertRaises(KeyError):
            map_log("[cm64] motion_sample seq=1 n=1 y_raw=100", calibration)
        with self.assertRaises(ValueError):
            map_log("", calibration)
        with self.assertRaises(ValueError):
            map_log(log, {**calibration, "mario_frame": ""})


if __name__ == "__main__":
    unittest.main()
