"""Asset-free adversarial G1 parser and exact pinned-source adaptation tests."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.assess_world_source_probe import assess, decode_vertex, divide, project, validate_record
from tools.prepare_world_source_probe import expected_sources, private_target, PATCHES, REPO
from tools.prepare_m41b_host import EXPECTED_PIN
from tools.prepare_world_source_probe import C1_PIN, LIBSM64_PIN, verify_public_sources
from unittest.mock import patch


def receipt():
    points = [[-128, -128, 1024], [128, -128, 1024], [0, 128, 1024]]
    words = []
    for x, y, z in points:
        words += [((z >> 3) & 255) << 24, (x & 0xFFF8) | ((y & 0xFFF8) << 16)]
    return dict(schema=2, phase="GUEST_WORLD_RTPT_OT", source_pin=EXPECTED_PIN, c1_pin=C1_PIN,
                sequence=1, epoch=1, ot_generation=1, level=9, draw=7,
                zone=0x80001000, path=0x80007000, ot=0x80010000, world=0, world_key=123,
                header=0x80002000, polygon=0x80003000, polygon_words=[2 << 20, 1 << 8],
                zone_header=0x80001100, world_descriptor=0x80001104, poly_id=0,
                zone_magic=0x0100FFFF, world_count=1, poly_id_address=0x80006004, poly_id_word=0,
                descriptor_words=[123, 0, 0, 0, 0x80002000, 0x80003000, 0x80004000, 0x80008000],
                header_words=[0, 0, 0, 1, 3, 0, 0, 0],
                origin=[0, 0, 0], vertex_addresses=[0x80004000, 0x80004008, 0x80004010],
                vertex_words=words, xyz=sum(points, []), rotation=[4096, 0, 0, 0, 4096, 0, 0, 0, 4096],
                translation=[0, 0, 0], camera_translation=[0, 0, 0], h=256, ofx=160 << 16, ofy=120 << 16,
                command=0x4A280030, sxy=[(88 << 16) | 128, (88 << 16) | 192, (152 << 16) | 160],
                z=[1024] * 3, flag=0, primitive=0x80005000, primitive_code=0x30,
                ot_chain=[[0x80010000, 0x5000], [0x80005000, 0x06FFFFFF]],
                postphysics=False, depth_complete=False, collision_ready=False)


class WorldSourceTests(unittest.TestCase):
    def test_native_oem_noise_never_weakens_utf8_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "native.log"
            path.write_bytes(b"native host noise \x85\n" + self.encode(receipt()).encode("utf-8") + b"\n")
            self.assertEqual(assess(path)["receipts"], 1)
            path.write_bytes(b"[cm64-world] \x85\n")
            with self.assertRaises(UnicodeError): assess(path)
            path.write_bytes(b"native host noise \x85\n")
            with self.assertRaisesRegex(ValueError, "No source-owned"): assess(path)

    def test_private_runner_keeps_observation_and_owned_process_boundary(self):
        source = (REPO / "tools/windows/Run-WorldSourceProbe.ps1").read_text(encoding="utf-8")
        for required in ("--verify-only", "--c1", "--libsm64", "Assert-Hash", "$process.Kill()",
                         "$process.HasExited", "-WindowStyle Hidden", "CM64_EMBED_ENABLE = '0'",
                         "$settings.ActiveMods = @()", "verified_real = $false"):
            self.assertIn(required, source)
        for forbidden in ("SendInput", "PostMessage", "Stop-Process -Name", "Remove-Item", "--prepare"):
            self.assertNotIn(forbidden, source)

    def test_public_sources_reject_each_dirty_or_unpinned_checkout(self):
        roots = [Path("launcher"), Path("c1"), Path("libsm64")]
        pins = dict(zip(roots, (EXPECTED_PIN, C1_PIN, LIBSM64_PIN)))
        with patch("tools.prepare_world_source_probe.git", side_effect=lambda root, *args: pins[root] if args[0] == "rev-parse" else ""):
            verify_public_sources(*roots)
        for bad_root in roots:
            for dirty in (False, True):
                def answer(root, *args):
                    if args[0] == "rev-parse":
                        return "wrong" if root == bad_root and not dirty else pins[root]
                    return " M source" if root == bad_root and dirty else ""
                with self.subTest(root=bad_root, dirty=dirty), patch("tools.prepare_world_source_probe.git", side_effect=answer):
                    with self.assertRaises(ValueError): verify_public_sources(*roots)

    def test_zone_count_id_word_and_ot_overlap_rejected(self):
        for field, value in [("schema", 1), ("c1_pin", "wrong"), ("zone_magic", 0),
                             ("world_count", 0), ("world_count", 9), ("world", 1),
                             ("poly_id_word", 1), ("poly_id_address", 0x80006005),
                             ("primitive", 0x8000FFFC)]:
            row = receipt(); row[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): validate_record(row)

    def test_poly_id_upper_half_and_gt3_tag(self):
        row = receipt(); row.update(poly_id_address=0x80006006, poly_id_word=0xFFFF)
        validate_record(row)
        row["poly_id_word"] |= 1 << 16
        with self.assertRaises(ValueError): validate_record(row)
        row = receipt(); row["primitive_code"] = 0x36; row["ot_chain"][-1][1] = 0x09FFFFFF
        validate_record(row)

    def audit(self, lines):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "private.log"
            path.write_text("\n".join(lines), encoding="utf-8")
            return assess(path)

    def encode(self, row):
        return "[cm64-world] " + json.dumps(row)

    def test_original_triangle_zero_error_without_real_claim(self):
        result = self.audit(["ordinary host log", self.encode(receipt())])
        self.assertEqual(result["vertices"], 3)
        self.assertEqual(result["max_integer_pixel_error"], 0)
        self.assertFalse(result["run_authenticity_verified"])
        self.assertFalse(result["collision_ready"])

    def test_reject_field_types_shapes_ranges_and_claims(self):
        changes = [("schema", True), ("phase", "PAD_UNKNOWN"), ("source_pin", "bad"),
                   ("command", 0x4A180001), ("world", 8), ("level", 9.0), ("draw", True),
                   ("rotation", [0] * 8), ("translation", [1 << 31, 0, 0]),
                   ("h", 0), ("flag", 1), ("sxy", [0, 1, 2]), ("z", [1025] * 3),
                   ("postphysics", True), ("depth_complete", True), ("collision_ready", True),
                   ("ot", 0x1F801000), ("primitive", 0x80010000), ("primitive_code", 0x20),
                   ("zone", 0x80200000), ("polygon", 0x80003001), ("path", -1)]
        for name, value in changes:
            with self.subTest(field=name, value=value):
                row = receipt(); row[name] = value
                with self.assertRaises(ValueError): validate_record(row)

    def test_required_fields(self):
        for name in receipt():
            with self.subTest(field=name):
                row = receipt(); del row[name]
                with self.assertRaises(ValueError): validate_record(row)

    def test_identity_and_vertex_word_corruption(self):
        for field, delta in [("vertex_addresses", 8), ("vertex_words", 1 << 24), ("xyz", 8), ("polygon_words", 1 << 20)]:
            row = receipt(); row[field][0] += delta
            with self.subTest(field=field), self.assertRaises(ValueError): validate_record(row)

    def test_degenerate_source(self):
        row = receipt()
        row["vertex_words"][2:4] = row["vertex_words"][0:2]
        row["xyz"][3:6] = row["xyz"][0:3]
        with self.assertRaises(ValueError): validate_record(row)

    def test_broken_cyclic_wrong_root_and_length_ot(self):
        chains = [[], [[0x80010000, 0x5004], [0x80005000, 0x06FFFFFF]],
                  [[0x80008000, 0x5000], [0x80005000, 0x06FFFFFF]],
                  [[0x80010000, 0x10000], [0x80010000, 0x5000], [0x80005000, 0x06FFFFFF]],
                  [[0x80010000, 0x5000], [0x80005000, 0x09FFFFFF]]]
        for chain in chains:
            with self.subTest(chain=chain):
                row = receipt(); row["ot_chain"] = chain
                with self.assertRaises(ValueError): validate_record(row)

    def test_frame_zone_generation_rejections(self):
        for field, value in [("sequence", 3), ("epoch", 0), ("ot_generation", 1),
                             ("draw", 7), ("zone", 0x80001004), ("path", 0x80007004), ("level", 10)]:
            first, second = receipt(), receipt()
            second.update(sequence=2, draw=8, ot_generation=2)
            second[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.audit([self.encode(first), self.encode(second)])

    def test_explicit_new_epoch_not_conflated_with_old_zone(self):
        first, second = receipt(), receipt()
        second.update(sequence=2, epoch=2, zone=0x80009000, ot_generation=2, draw=1)
        self.assertEqual(self.audit([self.encode(first), self.encode(second)])["receipts"], 2)

    def test_malformed_duplicate_truncated_nonfinite_json(self):
        for line in ["[cm64-world] {", "x[cm64-world] {}", "[cm64-world] []",
                     '[cm64-world] {"schema":1,"schema":1}', self.encode(receipt()).replace('"h": 256', '"h": NaN')]:
            with self.subTest(line=line[:40]), self.assertRaises(ValueError): self.audit([line])

    def test_empty_and_budgets(self):
        for lines in [[], ["x" * 16385], [self.encode(receipt())] * 25]:
            with self.assertRaises(ValueError): self.audit(lines)

    def test_exact_reciprocal_and_signed_packing(self):
        self.assertEqual(divide(256, 1024), 16384)
        self.assertEqual(project([-128, -128, 1024], receipt()["rotation"], [0, 0, 0],
                                 256, 160 << 16, 120 << 16), ((88 << 16) | 128, 1024))
        self.assertEqual(decode_vertex(128 << 24, 0xFF80FF80), [-128, -128, 1024])
        for h, z in [(256, 0), (256, 128)]:
            with self.assertRaises(ValueError): divide(h, z)

    def test_saturation_fails_closed(self):
        for xyz, trans in [([0, 0, -8], [0, 0, 0]), ([0, 0, 32760], [0, 0, 32760]),
                           ([32760, 0, 256], [0, 0, 0])]:
            with self.assertRaises(ValueError): project(xyz, receipt()["rotation"], trans, 256, 0, 0)

    def test_camera_world_origin_and_descriptor_consistency(self):
        for field, index in [("camera_translation", 0), ("origin", 0), ("descriptor_words", 1),
                             ("header_words", 7), ("header_words", 4)]:
            row = receipt(); row[field][index] += 256
            if field == "header_words" and index == 4: row[field][index] = 1
            with self.subTest(field=field, index=index), self.assertRaises(ValueError): validate_record(row)

    def test_pixel_error_is_quantified(self):
        row = receipt(); row["sxy"][0] += 1
        with self.assertRaisesRegex(ValueError, "pixel_dx=-1 pixel_dy=0 z_error=0"):
            validate_record(row)

    def test_private_root_boundary_rejects_original_and_other_worktrees(self):
        public = Path("C:/original-launcher")
        for target in [public, REPO, REPO.parent / "other-worktree", REPO / ".cache/m42-g1"]:
            with self.subTest(target=target), self.assertRaises(ValueError): private_target(public, target)
        self.assertEqual(private_target(public, REPO / ".cache/m42-g1/source")[1],
                         (REPO / ".cache/m42-g1/source").resolve())

    def test_exact_patch_seams_and_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            for name, (old, _) in PATCHES.items():
                path = source / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(old + ("        if ((FLAG & 0x7F87E000u) != 0) FLAG |= 0x80000000u;\n"
                                      if name.endswith("Gte.cs") else ""), encoding="utf-8")
            expected = expected_sources(source)
            self.assertIn("finally { CrashWorldSourceProbe.Leave(addr, completed); }", expected[next(iter(PATCHES))])
            for name in PATCHES:
                path = source / name; original = path.read_text()
                path.write_text(original + original)
                with self.subTest(name=name), self.assertRaises(ValueError): expected_sources(source)
                path.write_text(original)


if __name__ == "__main__": unittest.main()
