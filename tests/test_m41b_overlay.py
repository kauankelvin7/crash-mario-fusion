"""M4.1B1 deterministic image-overlay patch/guest-frame contracts (no game)."""
from pathlib import Path
import tempfile
import unittest

from tools.prepare_m41b_host import (
    MENU_ANCHOR, OUTPUT_ANCHOR, patch_private, verify_private
)

ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/"integration/embedded_mario/OriginalMarioOutputOverlay.cs"
MOD=ROOT/"integration/embedded_mario/CrashEmbeddedMarioMod.cs"
PREVIEW=ROOT/"integration/embedded_mario/OriginalMarioPreview.cs"
BUILDER=ROOT/"tools/windows/Build-OutputOverlay.ps1"
RUNNER=ROOT/"tools/windows/Run-OutputOverlay.ps1"

def make_fixture(base: Path):
    src=base/"source"
    dst=base/"private"
    for root in (src,dst):
        a=root/"RecompOne.Runtime/Host/Window"
        b=a/"Panels/Debug"
        b.mkdir(parents=True)
        (a/"MenuRegistry.cs").write_text("public class MenuRegistry {\n"+MENU_ANCHOR+"}\n",encoding="utf-8")
        (b/"OutputPanel.cs").write_text("class OutputPanel {\n"+OUTPUT_ANCHOR+"}\n",encoding="utf-8")
    return src,dst

class OverlayContracts(unittest.TestCase):
    def test_patch_uses_exact_output_image_rect_in_original_gui(self):
        with tempfile.TemporaryDirectory() as t:
            src,dst=make_fixture(Path(t))
            self.assertEqual(len(patch_private(src,dst)),2)
            self.assertTrue(verify_private(src,dst))
            menu=(dst/"RecompOne.Runtime/Host/Window/MenuRegistry.cs").read_text()
            output=(dst/"RecompOne.Runtime/Host/Window/Panels/Debug/OutputPanel.cs").read_text()
            for token in ("RegisterOutputOverlay","UnregisterOutputOverlay",
                          "DrawOutputOverlays","_outputOverlayLock","lock (_outputOverlayLock)"):
                self.assertIn(token,menu)
            self.assertIn("ImGui.GetItemRectMin()",output)
            self.assertIn("ImGui.GetItemRectMax()",output)
            self.assertLess(output.index("ImGui.Image"),output.index("DrawOutputOverlays"))

    def test_patch_refuses_source_alias_and_modified_checkout(self):
        with tempfile.TemporaryDirectory() as t:
            src,dst=make_fixture(Path(t))
            with self.assertRaises(ValueError):
                patch_private(src,src)
            menu=dst/"RecompOne.Runtime/Host/Window/MenuRegistry.cs"
            menu.write_text(menu.read_text()+"// unexpected\n")
            with self.assertRaises(ValueError):
                patch_private(src,dst)
            self.assertNotIn("DrawOutputOverlays",(dst/"RecompOne.Runtime/Host/Window/Panels/Debug/OutputPanel.cs").read_text())

    def test_patch_is_not_silently_repeatable_or_drift_tolerant(self):
        with tempfile.TemporaryDirectory() as t:
            src,dst=make_fixture(Path(t))
            patch_private(src,dst)
            with self.assertRaises(ValueError):
                patch_private(src,dst)
            menu=dst/"RecompOne.Runtime/Host/Window/MenuRegistry.cs"
            menu.write_text(menu.read_text().replace("_outputOverlayLock","unexpected"))
            with self.assertRaises(ValueError):
                verify_private(src,dst)

    def test_original_guest_buffers_and_not_stock_art(self):
        text=OVERLAY.read_text(encoding="utf-8")
        old=PREVIEW.read_text(encoding="utf-8")
        self.assertIn("OriginalMarioPreview.Current",text)
        self.assertIn("new Tri[frame.Triangles]",text)
        self.assertIn("draw.AddTriangleFilled",text)
        self.assertIn("draw.PushClipRect(topLeft,bottomRight,true)",text)
        self.assertIn("Volatile.Read(ref current)",old)
        self.assertNotIn("Bitmap",text)
        self.assertNotIn("Texture2D",text)

    def test_drawing_stays_in_image_clipped_region_not_new_window(self):
        text=OVERLAY.read_text(encoding="utf-8")
        self.assertNotIn("ImGui.Begin(",text)
        self.assertNotIn("ImGui.Image(",text)
        self.assertIn("UnregisterOutputOverlay(Draw)",text)
        self.assertIn("PushClipRect(topLeft,bottomRight,true)",text)
        self.assertIn("draw.PopClipRect();",text)
        self.assertIn("GetWindowDrawList",text)

    def test_guest_alone_does_not_change_original_crash_physics(self):
        m=MOD.read_text(encoding="utf-8")
        self.assertIn('CM64_INOUTPUT',m)
        self.assertIn("OriginalMarioOutputOverlay.Register()",m)
        self.assertIn("OriginalMarioOutputOverlay.Stop()",m)
        for forbidden in ("PadReadEvent","WriteU16","WriteU32","Hle.GpuHle","GpuBackend"):
            self.assertNotIn(forbidden,m)

    def test_bounded_private_hash_sealed_windows_process(self):
        build=BUILDER.read_text(encoding="utf-8")
        run=RUNNER.read_text(encoding="utf-8")
        for token in ("CrashMarioFusion/M41B-overlay","sm64.dll","RecompOne.Runtime.dll",
                      "mod.json","SHA256"):
            self.assertIn(token,build)
            self.assertIn(token,run)
        self.assertIn("CheckOnly",run)
        self.assertIn("Stop-Process -Id $p.Id",run)
        self.assertIn("shared_depth=$false",run)
        self.assertIn("camera_calibrated=$false",run)

    def test_no_retail_files_in_tracked_overlay_sources(self):
        for folder in (ROOT/"integration/embedded_mario", ROOT/"tests"):
            for p in folder.iterdir():
                self.assertNotIn(p.suffix.lower(), {".z64",".n64",".v64",".cue",
                    ".chd",".bin",".exe",".dll",".png",".bmp"})

if __name__=="__main__":
    unittest.main()
