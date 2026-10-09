"""Original full-sm64ex loader/query oracle with authored geometry, no ROM."""
import os
import platform
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.geometry_preflight import preflight_mesh, plan_native_surfaces
from tools.world_coordinates import FrameMap

PIN = "d7ca2c04364a6dd0dac58b47151e04e26887e6f0"
ROOT = Path(__file__).resolve().parents[1]


class NativeGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get("CM64_SM64EX_ROOT", "/workspace/.cache/crash-mario-m0/sm64ex"))
        if not source.is_dir() or not shutil.which("gcc"):
            if "CM64_SM64EX_ROOT" in os.environ:
                raise AssertionError("Configured native oracle requires pinned source and GCC; do not silently skip")
            raise unittest.SkipTest("Pinned sm64ex/GCC absent; set CM64_SM64EX_ROOT for native oracle")
        revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        if revision != PIN or subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
            raise AssertionError("Native oracle requires unchanged pinned sm64ex source")
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.probe = Path(cls.temp.name) / "native-geometry-probe"
        command = ["gcc", "-std=c11", "-g", "-UNDEBUG", "-DVERSION_US", "-D_LANGUAGE_C",
                   "-DNON_MATCHING", "-DAVOID_UB", "-ffunction-sections", "-fdata-sections"]
        # ASan/UBSan supported by hosted/cloud Linux GCC; Windows oracle uses its
        # native compiler without claiming sanitizer coverage there.
        if platform.system() == "Linux":
            command += ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-pie", "-no-pie"]
        command += ["-I"+str(source/"include"), "-I"+str(source/"src"), "-I"+str(source),
                    str(ROOT/"tests/native_geometry_probe.c"),
                    str(source/"src/engine/surface_collision.c"), "-Wl,--gc-sections", "-lm", "-o", str(cls.probe)]
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)

    def test_mapped_triangle_original_loader_contact_material_and_cleanup(self):
        for material in (0, 1):  # explicitly authored DEFAULT/BURNING, no Crash mapping
            for yaw in (0, 90, 173):
                with self.subTest(material=material, yaw=yaw):
                    preview = preflight_mesh(vertices=[(0,0,0), (0,0,100), (100,0,0)],
                                             triangles=[(0,1,2)],
                                             frame_map=FrameMap((0,0,0), (500,20,500),2,yaw),
                                             crash_level=9, calibrated_level=9,
                                             mario_frame="AUTHORED_TEST_FRAME_ONLY")
                    plan = plan_native_surfaces(preview,
                        materials=[dict(provenance="AUTHORED_SYNTHETIC",native_type=material,room=-3)],
                        surface_capacity=2,node_capacity=256,surfaces_used=0,nodes_used=0)
                    face=plan["surfaces"][0]
                    data=" ".join(str(v) for point in face["vertices"] for v in point)+f" {material} -3\n"
                    result=subprocess.run([str(self.probe)],input=data,capture_output=True,text=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertIn("height=20.000000 ny=1.000000 surfaces=1",result.stdout)
                    self.assertIn(f"nodes={plan['nodes_required']} type={material} room=-3",result.stdout)
                    self.assertIn("control and lifecycle PASS",result.stdout)

    def test_probe_rejects_out_of_fixture_bounds_or_unreviewed_material(self):
        for data in ("0 0 0 0 0 100 9000 0 0 0 0\n", "0 0 0 0 0 100 100 0 0 999 0\n",
                     "9"*200+"\n", "0 0 0 0 0 100 100 0 0 0 0 garbage\n", "0 0 0"):
            result=subprocess.run([str(self.probe)],input=data,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,2,result.stdout+result.stderr)


if __name__ == "__main__":
    unittest.main()
