"""Asset-free renderer contracts; native GPU fixture is a separate explicit oracle."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from test_m41b2_textured_mario import original_source_fixture
from tools.prepare_m41b_host import patch_private
from tools.prepare_m41b2_atlas import action as atlas_action
from tools.prepare_goal19_renderer import action, expected, verify_pin, FOLDER, FILES

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "integration/embedded_mario"


def prepare(root):
    source, target = original_source_fixture(root)
    patch_private(source, target)
    atlas_action(source, target, SRC / "OriginalMarioAtlasHost.cs", False)
    action(source, target, ROOT)
    return source, target


class RendererContracts(unittest.TestCase):
    def test_private_source_seam_preserves_originals_and_overlay(self):
        with TemporaryDirectory() as folder:
            source, target = prepare(Path(folder))
            before = {path: path.read_bytes() for path in source.rglob("*.cs")}
            report = action(source, target, ROOT, True)
            self.assertFalse(report["playable"])
            self.assertEqual(report["camera_adapter"], "BLOCKED")
            menu = (target / (FOLDER + "MenuRegistry.cs")).read_text()
            self.assertLess(menu.index("OriginalMarioGpu.BeginFrame"), menu.index("OriginalMarioAtlas.RenderTick"))
            host = (target / (FOLDER + "HostWindow.cs")).read_text()
            self.assertLess(host.index("OriginalMarioGpu.Shutdown"), host.index("OriginalMarioAtlas.Shutdown"))
            self.assertLess(host.index("OriginalMarioAtlas.Shutdown"), host.index("_glBackend?.Dispose"))
            self.assertEqual(before, {path: path.read_bytes() for path in source.rglob("*.cs")})
            with self.assertRaises(ValueError):
                action(source, target, ROOT)
            with self.assertRaises(ValueError):
                action(source, source, ROOT, True)

    def test_all_generated_resources_and_original_hooks_reject_drift(self):
        relatives = list(FILES) + ["HostWindow.cs", "MenuRegistry.cs", "OriginalMarioAtlas.cs",
                                   "Panels/Debug/OutputPanel.cs"]
        for relative in relatives:
            with self.subTest(relative=relative), TemporaryDirectory() as folder:
                source, target = prepare(Path(folder))
                path = target / (FOLDER + relative)
                path.write_text(path.read_text() + "\nforeign fixture edit\n")
                with self.assertRaises(ValueError):
                    action(source, target, ROOT, True)

    def test_wrong_original_pin_fails_before_generation(self):
        with patch("tools.prepare_goal19_renderer.subprocess.check_output", return_value="wrong"):
            with self.assertRaises(ValueError):
                verify_pin(Path("unused"))

    def test_actual_pinned_original_host_seams(self):
        source = os.environ.get("CM64_CRASH_HOST_ROOT")
        if not source:
            self.skipTest("Set CM64_CRASH_HOST_ROOT for pinned public host source oracle")
        verify_pin(Path(source))
        host, menu = expected(Path(source))
        self.assertIn("CM64ActiveGL", host)
        self.assertIn("OriginalMarioAtlas.RenderTick(activeGl)", menu)

    def test_homogeneous_shader_and_private_per_fragment_depth(self):
        source = (SRC / "OriginalMarioGpuHost.cs").read_text()
        for token in ("gl_Position = clip;", "smooth out vec2 uv", "smooth out vec3 color",
                      "flat out float textured", "pixel *= texture(atlas, uv)",
                      "InternalFormat.DepthComponent24", "gl.DepthFunc(DepthFunction.Less)",
                      "gl.DepthMask(true)", "gl.DrawArrays(PrimitiveType.Triangles",
                      "using var saved = new MarioGpuState(gl)"):
            self.assertIn(token, source)
        for forbidden in ("noperspective", "Array.Sort", "cam_rot", "screen_proj", "Matrix4x4",
                          "PSMemory", "File.ReadAllBytes", "DrawElements"):
            self.assertNotIn(forbidden, source)
        self.assertIn('"CM64_GPU_SELF_DEPTH") != "1"', source)

    def test_previous_overlay_is_untouched_until_source_projection_exists(self):
        overlay = (SRC / "OriginalMarioOutputOverlay.cs").read_text()
        self.assertIn("Array.Sort(triangles", overlay)
        self.assertNotIn("OriginalMarioGpu.TryRender", overlay)
        self.assertIn("camera_calibrated=false shared_depth=false shared_collider=false", overlay)

    def test_source_state_and_cleanup_own_mutated_resources(self):
        state = (SRC / "MarioGpuState.cs").read_text()
        for token in ("GetPName.DrawFramebufferBinding", "GetPName.ReadFramebufferBinding",
                      "GetPName.PixelUnpackBufferBinding", "GetPName.SamplerBinding",
                      "GetPName.ColorWritemask", "GetPName.DepthRange", "GetPName.PolygonMode",
                      "gl.ActiveTexture((TextureUnit)activeTexture)"):
            self.assertIn(token, state)
        renderer = (SRC / "OriginalMarioGpuHost.cs").read_text()
        for token in ("DeleteProgram", "DeleteVertexArray", "DeleteBuffer", "DeleteFramebuffer",
                      "DeleteTexture", "DeleteRenderbuffer", "Environment.CurrentManagedThreadId"):
            self.assertIn(token, renderer)

    def test_perspective_oracle_differs_from_screen_linear_interpolation(self):
        barycentric = [1 - 2 * 16.5 / 64, 16.5 / 64, 16.5 / 64]
        clip_w = [1, 2, 4]
        divided = [weight / w for weight, w in zip(barycentric, clip_w)]
        perspective = [value / sum(divided) for value in divided]
        self.assertAlmostEqual(sum(perspective), 1)
        self.assertGreater(abs(perspective[0] - barycentric[0]), .2)
        self.assertLess(perspective[2], .1)
