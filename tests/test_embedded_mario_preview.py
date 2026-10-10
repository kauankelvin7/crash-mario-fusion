"""M4.1 source-level guardrails for the original libsm64 mesh preview.

The only proof of actual visual drawing is the separately observed original
Windows Crash host screenshot; these tests never start a game or upload assets.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "integration/embedded_mario/OriginalMarioPreview.cs"
HOSTMOD = ROOT / "integration/embedded_mario/CrashEmbeddedMarioMod.cs"
BUILDER = ROOT / "tools/windows/Build-EmbeddedMario.ps1"
RUNNER = ROOT / "tools/windows/Run-EmbeddedMario.ps1"


class EmbeddedPreviewTests(unittest.TestCase):
    def test_guest_geometry_not_replaced_by_stock_art(self):
        s=PREVIEW.read_text(encoding="utf-8")
        self.assertIn("OriginalMarioMeshFrame",s)
        self.assertIn("triangleCount * 9",s)
        self.assertIn("positions[i]",s)
        self.assertIn("colors[i]",s)
        self.assertIn("draw.AddTriangleFilled",s)
        self.assertIn("new Projected",s)
        self.assertIn("original_triangles=",s)
        self.assertNotIn("gl.DrawArrays",s)
        self.assertNotIn("CreateFramebuffer",s)

    def test_snapshot_is_immutable_and_owns_buffers(self):
        s=PREVIEW.read_text(encoding="utf-8")
        for token in ("readonly float[] Position","readonly float[] Color",
                      "new float[components]","Volatile.Write(ref current",
                      "Volatile.Read(ref current","float.IsFinite",
                      "triangleCount > 1024"):
            self.assertIn(token,s)

    def test_render_called_only_from_verified_existing_host_window_event(self):
        s=PREVIEW.read_text(encoding="utf-8")
        m=HOSTMOD.read_text(encoding="utf-8")
        self.assertIn("MenuRegistry.RegisterWindow(Draw)",s)
        self.assertIn("OriginalMarioPreview.Register();",m)
        self.assertIn("OriginalMarioPreview.Publish(geometry.Position, geometry.Color",m)
        self.assertIn("OriginalMarioPreview.Stop();",m)
        self.assertNotIn("PadReadEvent",s)
        self.assertNotIn("PadReadEvent",m)
        self.assertNotIn("sm64_mario_tick",s)

    def test_not_false_claim_full_shared_scene(self):
        s=PREVIEW.read_text(encoding="utf-8")
        self.assertIn("shared_scene=false shared_depth=false",s)
        self.assertIn("NOT composited with Crash camera or depth",s)
        self.assertIn("AUTHORED", (ROOT/"docs/M41_PREVIEW_GATE.md").read_text(encoding="utf-8"))

    def test_only_private_hash_sealed_mod_files_deployed(self):
        a=BUILDER.read_text(encoding="utf-8")
        b=RUNNER.read_text(encoding="utf-8")
        self.assertGreaterEqual(a.count("OriginalMarioPreview.cs"),3)
        self.assertIn("OriginalMarioPreview.cs",b)
        self.assertIn("RequirePreview",b)
        self.assertIn("guest_mesh_preview=$preview",b)
        self.assertIn("M41_PREVIEW_DREW native_mesh=true",b)


if __name__=="__main__":
    unittest.main()
