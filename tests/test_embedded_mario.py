"""M4 source-only ABI, privacy and seam guardrails. No ROM, games or DLL required."""
import ctypes
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "integration" / "embedded_mario"

class Surface(ctypes.Structure):
    _fields_ = [("type",ctypes.c_int16),("force",ctypes.c_int16),
                ("terrain",ctypes.c_uint16),("vertices",ctypes.c_int32*9)]

class Inputs(ctypes.Structure):
    _fields_ = [("camLookX",ctypes.c_float),("camLookZ",ctypes.c_float),
                ("stickX",ctypes.c_float),("stickY",ctypes.c_float),
                ("buttonA",ctypes.c_uint8),("buttonB",ctypes.c_uint8),
                ("buttonZ",ctypes.c_uint8)]

class State(ctypes.Structure):
    _fields_ = [("position",ctypes.c_float*3),("velocity",ctypes.c_float*3),
                ("faceAngle",ctypes.c_float),("forwardVelocity",ctypes.c_float),
                ("health",ctypes.c_int16),("action",ctypes.c_uint32),
                ("animID",ctypes.c_int32),("animFrame",ctypes.c_int16),
                ("flags",ctypes.c_uint32),("particleFlags",ctypes.c_uint32),
                ("invincTimer",ctypes.c_int16)]

class Geometry(ctypes.Structure):
    _fields_ = [("position",ctypes.c_void_p),("normal",ctypes.c_void_p),
                ("color",ctypes.c_void_p),("uv",ctypes.c_void_p),
                ("numTrianglesUsed",ctypes.c_uint16)]

class EmbeddedMarioTests(unittest.TestCase):
    def test_c_abi_x64_layout(self):
        self.assertEqual([ctypes.sizeof(v) for v in (Surface,Inputs,State,Geometry)],
                         [44,20,60,40])
        self.assertEqual(State.action.offset,36)
        self.assertEqual(State.invincTimer.offset,56)

    def test_managed_layout_and_cdecl_imports_are_explicit(self):
        text=(SRC/"Interop.cs").read_text(encoding="utf-8")
        for expect in ("MarioSurface)!=44","MarioInputs)!=20","MarioState)!=60",
                       "MarioGeometry)!=40","CallingConvention.Cdecl","sm64_global_init",
                       "sm64_mario_tick","sm64_static_surfaces_load",
                       "sm64_global_terminate"):
            self.assertIn(expect,text)
        self.assertNotIn("Pack=1",text)

    def test_host_uses_opt_in_without_crash_memory_or_input_mutations(self):
        text=(SRC/"CrashEmbeddedMarioMod.cs").read_text(encoding="utf-8")
        self.assertIn('CM64_EMBED_ENABLE',text)
        self.assertIn("Event.AddListener<VSyncEvent>",text)
        self.assertIn("MarioNative.sm64_mario_tick",text)
        self.assertIn("fixed (MarioInputs* inputs",text)
        for forbidden in ("PadReadEvent","WriteU32","WriteU16",
                          "Recompiled.Entry","GameLoader.Run","CollisionApply"):
            self.assertNotIn(forbidden,text)

    def test_only_one_manifest_mod_and_no_game_assets_committed(self):
        manifest=json.loads((SRC/"mod.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["id"],"cm64-embedded-mario")
        self.assertEqual(manifest["dependencies"],[])
        source_files=list(SRC.iterdir())
        self.assertFalse([p.name for p in source_files if p.suffix.lower() in
                          (".z64",".n64",".v64",".cue",".bin",".chd",".dll",".exe")])

    def test_private_runner_requires_rom_sha1_and_hash_manifests(self):
        builder=(ROOT/"tools/windows/Build-EmbeddedMario.ps1").read_text(encoding="utf-8")
        runner=(ROOT/"tools/windows/Run-EmbeddedMario.ps1").read_text(encoding="utf-8")
        self.assertIn("fd11813208272b4271d92bd92feb8f3fdbe61be5",builder)
        self.assertIn("224da7757920a817de2d9242416f657ab95782ea",builder)
        for text in (builder,runner):
            self.assertIn("cm64-embedded-mario",text)
            self.assertIn("sm64.dll",text)
        self.assertIn("9bef1128717f958171a4afac3ed78ee2bb4e86ce",runner)
        self.assertIn("Stop-Process -Id $p.Id",runner)

    def test_native_probe_cannot_claim_shared_world(self):
        text=(SRC/"embedded_probe.c").read_text(encoding="utf-8")
        self.assertIn("surface=AUTHORED_NOT_CRASH",text)
        self.assertIn("physical_status=BLOCKED",text)
        self.assertIn("sm64_mario_tick",text)
        doc=(ROOT/"docs/M4_EMBEDDED_PLAN.md").read_text(encoding="utf-8")
        self.assertIn("M4.2",doc)
        self.assertIn("BLOCKED",doc)

if __name__=="__main__":
    unittest.main()
