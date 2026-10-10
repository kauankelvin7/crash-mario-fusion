"""Pinned public-source G1 adaptation; writes only a repo-local private clone."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from tools.prepare_m41b_host import EXPECTED_PIN, MENU_ANCHOR, MENU_REPLACEMENT, OUTPUT_ANCHOR, OUTPUT_REPLACEMENT
from tools import prepare_m41b2_atlas as atlas

REPO = Path(__file__).resolve().parents[1]
C1_PIN = "256fdcef59f15a190290cc19db3fa9a707843b69"
LIBSM64_PIN = "fd11813208272b4271d92bd92feb8f3fdbe61be5"
PROBE_PATH = "RecompOne.Runtime/Hardware/CrashWorldSourceProbe.cs"
PATCHES = {
    "RecompOne.Runtime/Dispatch/Dispatcher.cs": (
        "        if (!skip)\n            fn(c, m);\n",
        "        if (!skip)\n        {\n"
        "            CrashWorldSourceProbe.Enter(addr, c, m);\n"
        "            bool completed = false;\n"
        "            try { fn(c, m); completed = true; }\n"
        "            finally { CrashWorldSourceProbe.Leave(addr, completed); }\n"
        "        }\n",
    ),
    "RecompOne.Runtime/Hardware/Gte.cs": (
        "    public static void Execute(uint cmd)\n    {\n",
        "    public static void Execute(uint cmd)\n    {\n"
        "        CrashWorldSourceProbe.BeforeGte(cmd);\n",
    ),
    "RecompOne.Runtime/Memory/Dma.cs": (
        "        GteScreenCache.BeginFrame();\n",
        "        GteScreenCache.BeginFrame();\n"
        "        CrashWorldSourceProbe.OrderingTable(madr, count);\n",
    ),
    "RecompOne.Runtime/Memory/PSMemory.cs": (
        "    public ReadOnlySpan<byte> Ram => _ram;\n",
        "    public ReadOnlySpan<byte> Ram => _ram;\n"
        "    internal ReadOnlySpan<byte> CM64Scratchpad => _scratchpad;\n",
    ),
}
GTE_END = "        if ((FLAG & 0x7F87E000u) != 0) FLAG |= 0x80000000u;\n"


def expected_sources(source: Path) -> dict[str, str]:
    planned = {}
    for name, (old, new) in PATCHES.items():
        raw = (source / name).read_text(encoding="utf-8-sig")
        if raw.count(old) != 1 or "CrashWorldSourceProbe" in raw:
            raise ValueError("Unknown pinned source seam: " + name)
        expected = raw.replace(old, new)
        if name.endswith("Gte.cs"):
            if expected.count(GTE_END) != 1:
                raise ValueError("Unknown GTE completion seam")
            expected = expected.replace(GTE_END, GTE_END + "        CrashWorldSourceProbe.AfterGte(cmd);\n")
        planned[name] = expected
    planned[PROBE_PATH] = (REPO / "integration/embedded_mario/CrashWorldSourceProbe.cs").read_text(encoding="utf-8")
    return planned


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def verify_public_sources(source: Path, c1: Path, libsm64: Path) -> None:
    for root, pin in ((source, EXPECTED_PIN), (c1, C1_PIN), (libsm64, LIBSM64_PIN)):
        if git(root, "rev-parse", "HEAD") != pin or git(root, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("Public source must be clean and pinned: " + root.name)


def private_target(source: Path, target: Path) -> tuple[Path, Path]:
    source, target = source.resolve(), target.resolve()
    private_root = (REPO / ".cache/m42-g1").resolve()
    if not private_root.is_relative_to(REPO) or source == target or \
       not target.is_relative_to(private_root) or target == private_root:
        raise ValueError("G1 target must be a separate repo-local .cache/m42-g1 clone")
    return source, target


def verify_texture(source: Path, target: Path) -> None:
    menu_name = "RecompOne.Runtime/Host/Window/MenuRegistry.cs"
    host_name = "RecompOne.Runtime/Host/Window/HostWindow.cs"
    output_name = "RecompOne.Runtime/Host/Window/Panels/Debug/OutputPanel.cs"
    menu = (source / menu_name).read_text(encoding="utf-8-sig")
    host = (source / host_name).read_text(encoding="utf-8-sig")
    output = (source / output_name).read_text(encoding="utf-8-sig")
    expected = {
        menu_name: menu.replace(MENU_ANCHOR, MENU_REPLACEMENT).replace(atlas.MENU_ANCHOR, atlas.MENU_REPLACEMENT),
        host_name: host.replace(atlas.GL_ANCHOR, atlas.GL_REPLACEMENT).replace(atlas.SHUTDOWN_ANCHOR, atlas.SHUTDOWN_REPLACEMENT),
        output_name: output.replace(OUTPUT_ANCHOR, OUTPUT_REPLACEMENT),
        atlas.ATLAS_PATH: (REPO / "integration/embedded_mario/OriginalMarioAtlasHost.cs").read_text(encoding="utf-8"),
    }
    for name, text in expected.items():
        path = target / name
        if not path.resolve().is_relative_to(target) or path.read_text(encoding="utf-8-sig") != text:
            raise ValueError("Existing original Mario pipeline drift: " + name)


def action(source: Path, target: Path, verify_only: bool = False) -> None:
    source, target = private_target(source, target)
    if git(source, "rev-parse", "HEAD") != EXPECTED_PIN or git(source, "status", "--porcelain"):
        raise ValueError("Public original launcher must be clean and pinned")
    if git(target, "rev-parse", "HEAD") != EXPECTED_PIN:
        raise ValueError("Private clone pin mismatch")
    verify_texture(source, target)
    planned = expected_sources(source)
    for name, expected in planned.items():
        path = target / name
        if not path.resolve().is_relative_to(target):
            raise ValueError("Private source symlink escape")
        if verify_only:
            if not path.is_file() or path.read_text(encoding="utf-8-sig") != expected:
                raise ValueError("Private G1 source drift: " + name)
        elif name == PROBE_PATH:
            if path.exists():
                raise ValueError("Existing probe; verify instead of overwrite")
        elif path.read_bytes() != (source / name).read_bytes():
            raise ValueError("Private original seam already edited: " + name)
    if not verify_only:
        for name, expected in planned.items():
            (target / name).write_text(expected, encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--private-clone", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--check-target-only", action="store_true")
    parser.add_argument("--c1", type=Path, required=True)
    parser.add_argument("--libsm64", type=Path, required=True)
    args = parser.parse_args()
    try:
        verify_public_sources(args.source, args.c1, args.libsm64)
        if args.check_target_only:
            private_target(args.source, args.private_clone)
        else:
            action(args.source, args.private_clone, args.verify_only)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, "G1_SOURCE_REJECTED: " + str(error) + "\n")
    print("G1_PRIVATE_SOURCE_OK original_game_NOT_TESTED")


if __name__ == "__main__":
    main()
