"""M4.1B2A original Mario texture atlas asset-free source and lifecycle gates.

These tests never load commercial game bytes or start original renderers.
"""
from pathlib import Path
import tempfile
import unittest

from tools.prepare_m41b_host import patch_private
from tools.prepare_m41b2_atlas import action

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"integration/embedded_mario"
HOST=SRC/"OriginalMarioAtlasHost.cs"
MOD=SRC/"CrashEmbeddedMarioMod.cs"
FRAME=SRC/"OriginalMarioPreview.cs"
DRAW=SRC/"OriginalMarioOutputOverlay.cs"


def original_source_fixture(root):
    src=root/"source"
    tgt=root/"private"
    for p in (src,tgt):
        folder=p/"RecompOne.Runtime/Host/Window"
        (folder/"Panels/Debug").mkdir(parents=True)
        (folder/"MenuRegistry.cs").write_text(
            "class MenuRegistry {\n"
            "    public static void RegisterWindow(Action draw)\n"
            "    {\n"
            "        if (draw == null) return;\n"
            "        _windows.Add(draw);\n"
            "    }\n"
            "}\n",encoding="utf-8")
        (folder/"Panels/Debug/OutputPanel.cs").write_text(
            "class OutputPanel {\n        ImGui.Image((nint)_texId, imageSize);\n}\n",
            encoding="utf-8")
        (folder/"HostWindow.cs").write_text(
            "class HostWindow {\n    static GL? _gl;\n"
            "    static void OnClosing() {\n"
            "        _glBackend?.Dispose();\n    }\n}\n",
            encoding="utf-8")
    return src,tgt


class TexturedOriginalMario(unittest.TestCase):
    def test_704x64_native_original_mario_atlas(self):
        h=HOST.read_text(encoding="utf-8")
        self.assertIn("Width = 704, Height = 64",h)
        self.assertIn("ByteCount = Width * Height * 4",h)
        self.assertIn("QueueAtlas(byte[] pixels)",h)
        self.assertIn("var copy=(byte[])pixels.Clone()",h)
        self.assertIn("Array.Clear(bytes)",h)
        self.assertNotIn("File.WriteAllBytes",h)

    def test_native_uv_snapshot_unmodified_and_bounded(self):
        s=FRAME.read_text(encoding="utf-8")
        self.assertIn("new float[checked(triangleCount * 6)]",s)
        self.assertIn("coords[i]=value",s)
        self.assertIn("float.IsFinite(value)",s)
        self.assertIn("Color, Uv, Triangles, Tick",s)
        self.assertIn("Volatile.Write(ref current",s)

    def test_real_original_owned_rom_texture_only_memory(self):
        m=MOD.read_text(encoding="utf-8")
        self.assertIn("CM64_TEXTURE_ATLAS",m)
        self.assertIn("Marshal.Copy((nint)texture,rgba,0,rgba.Length)",m)
        self.assertIn("sm64_global_init(rom, texture)",m)
        self.assertIn("QueueAtlas(rgba)",m)
        self.assertIn("CryptographicOperations.ZeroMemory(rgba)",m)
        self.assertIn("ReleaseAtlas()",m)

    def test_host_gl_render_thread_owns_texture_and_restores_binding(self):
        s=HOST.read_text(encoding="utf-8")
        for token in ("RenderTick(GL gl)","gl.TexImage2D(","gl.DeleteTexture(",
            "gl.GetInteger(GetPName.TextureBinding2D)",
            "gl.GetInteger(GetPName.UnpackAlignment)",
            "gl.GetInteger(GetPName.PixelUnpackBufferBinding)",
            "gl.BindBuffer(BufferTargetARB.PixelUnpackBuffer,0)",
            "gl.BindBuffer(BufferTargetARB.PixelUnpackBuffer,(uint)previousPbo)",
            "gl.PixelStore(PixelStoreParameter.UnpackAlignment,previousUnpack)",
            "gl.BindTexture(TextureTarget.Texture2D,(uint)previousBinding)"):
            self.assertIn(token,s)

    def test_sentinel_untextured_geometry_stays_colored(self):
        s=DRAW.read_text(encoding="utf-8")
        self.assertIn("if(uv[j]!=1f||uv[j+1]!=1f)untextured=false",s)
        self.assertIn("draw.AddTriangleFilled",s)
        self.assertIn("draw.PrimReserve(3,3)",s)
        self.assertIn("draw.PrimVtx(tri.A,tri.UvA,tri.ColorA)",s)
        self.assertIn("draw.PushTextureID(atlas)",s)
        self.assertIn("draw.PopTextureID()",s)
        self.assertIn("draw.PushClipRect(topLeft,bottomRight,true)",s)

    def test_private_pin_locked_host_generation_and_verification(self):
        with tempfile.TemporaryDirectory() as d:
            src,target=original_source_fixture(Path(d))
            patch_private(src,target)
            action(src,target,HOST,False)
            action(src,target,HOST,True)
            atlas=target/"RecompOne.Runtime/Host/Window/OriginalMarioAtlas.cs"
            self.assertEqual(atlas.read_text(encoding="utf-8"),HOST.read_text(encoding="utf-8"))
            menu=(target/"RecompOne.Runtime/Host/Window/MenuRegistry.cs").read_text()
            self.assertIn("OriginalMarioAtlas.RenderTick(activeGl)",menu)
            host=(target/"RecompOne.Runtime/Host/Window/HostWindow.cs").read_text()
            self.assertIn("OriginalMarioAtlas.Shutdown(_gl)",host)
            with self.assertRaises(ValueError):
                action(src,target,HOST,False)

    def test_private_patch_detects_noncanonical_host(self):
        with tempfile.TemporaryDirectory() as d:
            src,target=original_source_fixture(Path(d))
            patch_private(src,target)
            host=target/"RecompOne.Runtime/Host/Window/HostWindow.cs"
            host.write_text(host.read_text()+"// modified\n")
            with self.assertRaises(ValueError):
                action(src,target,HOST,False)

    def test_windows_run_is_bounded_hash_sealed_and_not_full_fusion(self):
        build=(ROOT/"tools/windows/Build-TexturedMario.ps1").read_text(encoding="utf-8")
        run=(ROOT/"tools/windows/Run-TexturedMario.ps1").read_text(encoding="utf-8")
        for token in ("OriginalMarioAtlasHost.cs","224da7757920a817de2d9242416f657ab95782ea","SHA256"):
            self.assertIn(token,build)
        for token in ("CM64_TEXTURE_ATLAS='1'","HOST_GL_ATLAS_UPLOADED",
                      "M41B2_TEXTURED_MESH_DREW","Stop-Process -Id $p.Id",
                      "shared_depth=$false","camera_calibrated=$false"):
            self.assertIn(token,run)

    def test_no_committed_original_retail_images_or_binary(self):
        for folder in (SRC,ROOT/"tests"):
            for p in folder.iterdir():
                self.assertNotIn(p.suffix.lower(),
                    {".dll",".exe",".z64",".n64",".v64",".cue",".bin",".chd",".png",".bmp",".jpg",".rom"})


if __name__=="__main__":unittest.main()
