"""Pinned c1 query functions with authored neighbors; no retail assets or game."""
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PIN = "256fdcef59f15a190290cc19db3fa9a707843b69"


class NativeQueryOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get("CM64_C1_ROOT", "/workspace/.cache/crash-mario-m0/c1"))
        if not source.is_dir() or not shutil.which("gcc"):
            if "CM64_C1_ROOT" in os.environ:
                raise AssertionError("Configured c1 oracle requires exact source and GCC")
            raise unittest.SkipTest("Set CM64_C1_ROOT to pinned public c1 source")
        head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
        if head != PIN or dirty:
            raise AssertionError("c1 oracle requires unchanged original pin")
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        solid = (source / "src/solid.c").read_text()
        level = (source / "src/level.c").read_text()
        selected = solid[solid.index("static void ZoneQueryOctreeR("):solid.index("\nvoid PlotQueryWalls(")]
        selected += level[level.index("int TestRectIntersectsBound("):level.index("//----- (80026CA8)")]
        selected += level[level.index("int ZoneQueryOctrees("):level.index("//----- (8002967C)")]
        generated = Path(cls.temp.name) / "cm64_native_query.h"
        generated.write_text('#include "solid.h"\nextern entry *cur_zone;\n' + selected)
        cls.source = source
        cls.probe = Path(cls.temp.name) / "query-probe"
        command = ["gcc", "-std=gnu11", "-fplan9-extensions", "-UNDEBUG",
                   "-I" + str(source / "src"), "-I" + cls.temp.name,
                   str(ROOT / "tests/native_crash_query_probe.c"), "-o", str(cls.probe)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stderr)

    def query_bytes(self, mode):
        result = subprocess.run([str(self.probe), str(mode)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = bytes.fromhex(result.stdout.strip())
        self.assertEqual(len(payload), 0x1050)
        return payload

    @unittest.skipUnless(os.environ.get("CM64_QUERY_CHECKS_DLL"), "Set CM64_QUERY_CHECKS_DLL for C-to-.NET comparison")
    def test_original_query_bytes_pass_native_dotnet_contract(self):
        checks = Path(os.environ["CM64_QUERY_CHECKS_DLL"])
        self.assertTrue(checks.is_file(), "Configured .NET fixture missing; no silent skip")
        for mode in (0, 1, 2, 3):
            result = subprocess.run([os.environ.get("CM64_DOTNET", "dotnet"), str(checks), "--oracle", str(mode)],
                input=self.query_bytes(mode).hex(), capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFIED_SYNTHETIC native_query_checks=", result.stdout)


    @unittest.skipUnless(os.environ.get("CM64_QUERY_CHECKS_DLL"), "Set CM64_QUERY_CHECKS_DLL for C-to-.NET comparison")
    def test_native_results_reject_mismatched_recorded_roots(self):
        checks = Path(os.environ["CM64_QUERY_CHECKS_DLL"])
        self.assertTrue(checks.is_file())
        for output_mode, source_mode in ((0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)):
            with self.subTest(output=output_mode, source=source_mode):
                result = subprocess.run([os.environ.get("CM64_DOTNET", "dotnet"), str(checks),
                    "--oracle", str(source_mode)], input=self.query_bytes(output_mode).hex(),
                    capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ROOT_RESULT", result.stdout + result.stderr)


    def test_original_neighbor_order_bounds_descriptor_and_sentinel(self):
        payload = self.query_bytes(0)
        self.assertEqual(struct.unpack_from("<ii", payload, 0x1000), (1, 6))
        self.assertEqual(struct.unpack_from("<6i", payload, 0x1008),
                         (-76800, -68480, -76800, 76800, 238720, 76800))
        self.assertEqual(struct.unpack_from("<8h", payload), (0, 64, 64, 64, 0, 0, 0, 0))
        self.assertEqual(struct.unpack_from("<4h", payload, 16), (8, 4288, 4280, 4800))
        self.assertEqual(struct.unpack_from("<4h", payload, 40), (8, 4800, 4536, 4800))
        self.assertEqual(struct.unpack_from("<I", payload, 48)[0], 0xFFFFFFFF)

    def test_native_negative_shift_and_nonmultiple_bounds(self):
        payload = self.query_bytes(3)
        self.assertEqual(struct.unpack_from("<3i", payload, 0x1008), (-6799, -68477, -76795))
        self.assertEqual(struct.unpack_from("<4h", payload, 16), (8, -88, 4279, 4799))

    def test_empty_nodes_are_descriptors_not_manufactured_ground(self):
        payload = self.query_bytes(1)
        self.assertEqual(struct.unpack_from("<i", payload, 0x1004)[0], 4)
        self.assertEqual(struct.unpack_from("<I", payload, 32)[0], 0xFFFFFFFF)

    def test_event_subtype_bits_are_retained(self):
        payload = self.query_bytes(2)
        self.assertEqual(struct.unpack_from("<H", payload, 16)[0], 72)
        self.assertEqual(struct.unpack_from("<H", payload, 40)[0], 72)

    @unittest.skipUnless(platform.system() == "Windows", "Guest32 ABI compiled by native Windows MinGW")
    def test_original_guest32_layout(self):
        result = subprocess.run(["gcc", "-m32", "-std=gnu11", "-fplan9-extensions",
            "-I" + str(self.source / "src"), "-c", str(ROOT / "tests/native_crash_query_layout.c"),
            "-o", str(Path(self.temp.name) / "guest-layout.o")], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)


class NativeQuerySourceGuards(unittest.TestCase):
    def test_hooks_observe_only_and_never_replace_originals(self):
        source = (ROOT / "integration/crash_collision/CrashNativeQueryMod.cs").read_text()
        self.assertNotIn("AddReplace", source)
        self.assertNotIn("ReadU32", source)
        self.assertNotIn("sm64_", source)
        self.assertNotIn("Dispatcher.Call(", source)
        self.assertIsNone(re.search(r"context\.\w+\s*=(?!=)", source))
        for address in ("0x800294B0", "0x80015A98", "0x80013B30", "0x80015B58"):
            self.assertIn(address, source)
        self.assertIn("receipts < 24", source)
        self.assertIn("attempts >= 96", source)
        self.assertIn("rejects < 8", source)
        self.assertIn("<= 90000", source)

    def test_receipts_cannot_enable_surfaces_or_claim_lifetime(self):
        source = (ROOT / "integration/crash_collision/CrashNativeQuery.cs").read_text()
        for flag in ("AllocationGenerationKnown", "NativeFrameKnown", "MaterialMappingKnown", "SurfacesAllowed"):
            self.assertIn("public bool " + flag + " => false;", source)

    def test_private_host_runner_rejects_concurrent_games_and_uploads_no_assets(self):
        source = (ROOT / "tools/windows/Run-CollisionProbe.ps1").read_text()
        self.assertIn("Get-Process -Name CrashBandicoot", source)
        self.assertIn("Owned disc must remain under LOCALAPPDATA", source)
        self.assertIn("NO_ORIGINAL_QUERY_RECEIPTS", source)
        self.assertIn("physical_contact_verified=$false", source)
        self.assertIn("Stop-Process -Id $process.Id", source)
