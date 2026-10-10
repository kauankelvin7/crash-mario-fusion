"""Pinned, reversible source-only GPU seam; never runs games or projects a camera."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from tools import prepare_m41b_host as overlay
from tools import prepare_m41b2_atlas as atlas

FOLDER = "RecompOne.Runtime/Host/Window/"
FILES = {
    "OriginalMarioClipFrame.cs": "OriginalMarioClipFrame.cs",
    "OriginalMarioGpu.cs": "OriginalMarioGpuHost.cs",
    "MarioGpuState.cs": "MarioGpuState.cs",
}
BEGIN = "OriginalMarioGpu.BeginFrame(activeGl); "
END = (
    "        try { OriginalMarioGpu.Shutdown(_gl); }\n"
    "        catch (Exception e) { Console.Error.WriteLine(\"[cm64-gpu] cleanup deferred: \" + e.GetType().Name); }\n"
)


def expected(source: Path):
    host = (source / (FOLDER + "HostWindow.cs")).read_text(encoding="utf-8-sig")
    menu = (source / (FOLDER + "MenuRegistry.cs")).read_text(encoding="utf-8-sig")
    for text, anchor in ((host, atlas.GL_ANCHOR), (host, atlas.SHUTDOWN_ANCHOR),
                         (menu, overlay.MENU_ANCHOR)):
        if text.count(anchor) != 1:
            raise ValueError("Unverified pinned renderer seam")
    host = host.replace(atlas.GL_ANCHOR, atlas.GL_REPLACEMENT).replace(
        atlas.SHUTDOWN_ANCHOR, atlas.SHUTDOWN_REPLACEMENT)
    menu = menu.replace(overlay.MENU_ANCHOR, overlay.MENU_REPLACEMENT).replace(
        atlas.MENU_ANCHOR, atlas.MENU_REPLACEMENT)
    return host, menu


def action(source: Path, target: Path, repo: Path, verify_only=False):
    if source.resolve() == target.resolve() or source.resolve() in target.resolve().parents:
        raise ValueError("Refuse to modify original pinned sources")
    host, menu = expected(source)
    host_after = host.replace(atlas.SHUTDOWN_REPLACEMENT, END + atlas.SHUTDOWN_REPLACEMENT)
    menu_after = menu.replace("OriginalMarioAtlas.RenderTick(activeGl);",
                              BEGIN + "OriginalMarioAtlas.RenderTick(activeGl);")
    planned = {FOLDER + "HostWindow.cs": (host, host_after),
               FOLDER + "MenuRegistry.cs": (menu, menu_after)}
    output_name = FOLDER + "Panels/Debug/OutputPanel.cs"
    original_output = (source / output_name).read_text(encoding="utf-8-sig")
    if original_output.count(overlay.OUTPUT_ANCHOR) != 1:
        raise ValueError("Unverified original OutputPanel")
    output = original_output.replace(overlay.OUTPUT_ANCHOR, overlay.OUTPUT_REPLACEMENT)
    atlas_text = (repo / "integration/embedded_mario/OriginalMarioAtlasHost.cs").read_text(encoding="utf-8")
    for relative, text in ((output_name, output), (atlas.ATLAS_PATH, atlas_text)):
        if (target / relative).read_text(encoding="utf-8-sig") != text:
            raise ValueError("Existing private host/atlas drift: " + relative)
    for name, local in FILES.items():
        text = (repo / "integration/embedded_mario" / local).read_text(encoding="utf-8")
        planned[FOLDER + name] = (None, text)
    for relative, (before, after) in planned.items():
        path = target / relative
        if target.resolve() not in path.resolve().parents:
            raise ValueError("Generated resource escapes disposable clone")
        if verify_only:
            if not path.is_file() or path.read_text(encoding="utf-8-sig") != after:
                raise ValueError("Private GPU source drift: " + relative)
        elif before is None:
            if path.exists():
                raise ValueError("Refuse to overwrite existing GPU source")
        elif path.read_text(encoding="utf-8-sig") != before:
            raise ValueError("Private atlas/host source drift")
    if not verify_only:
        atlas.action(source, target, repo / "integration/embedded_mario/OriginalMarioAtlasHost.cs", True)
        for relative, (_, after) in planned.items():
            (target / relative).write_text(after, encoding="utf-8", newline="")
    return {"status": "VERIFIED_SYNTHETIC", "camera_adapter": "BLOCKED", "playable": False}


def verify_pin(source: Path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    if git("rev-parse", "HEAD") != overlay.EXPECTED_PIN or git("status", "--porcelain"):
        raise ValueError("Original public source must be pinned and clean")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--private-clone", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    verify_pin(args.source)
    if args.private_clone is None:
        expected(args.source)
        print("GOAL19_RENDERER_SOURCE_PIN_OK original_game=NOT_TESTED")
        return
    if (repo / ".cache").resolve() not in args.private_clone.resolve().parents:
        raise ValueError("Generated host must stay inside this worktree's ignored .cache")
    print(json.dumps(action(args.source, args.private_clone, repo, args.verify_only)))


if __name__ == "__main__":
    main()
