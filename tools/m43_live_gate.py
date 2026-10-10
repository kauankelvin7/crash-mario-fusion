"""Source contract and bounded telemetry oracle; neither certifies human gameplay."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

PIN = "224da7757920a817de2d9242416f657ab95782ea"
RESERVED = {"I", "J", "K", "L", "U"}

def source_gate(source: Path) -> dict:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    if git("rev-parse", "HEAD") != PIN or git("status", "--porcelain"):
        raise ValueError("Source must be pinned and clean")
    anchors = {
        "Host/Window/HostWindow.cs": ["static void OnRender(double dt)", "_imgui!.Update((float)dt);", "PanelManager.DrawPanels();", "public static bool IsInputActive"],
        "Host/Window/Panels/Debug/OutputPanel.cs": ["ImGui.Image((nint)_texId, imageSize);"],
        "Host/InputManager.cs": ["KeyState(kb, ConfigManager.Game.Keys)", "KeyState(kb, ConfigManager.Game.Keys2)", "KeyBindingNames.AnyPressed(keyName, IsKeyDown)", "static Key ResolveCheatMenuKey()"],
        "Config/GameConfig.cs": ['Select { get; set; } = "ShiftRight"'],
        "Config/KeyBindingNames.cs": ["public static bool AnyPressed", "public static bool TryParse"],
        "Host/FramePacing.cs": ["const uint PausedAddr = 0x80056400u;", "const uint PauseStatusAddr = 0x8005640Cu;"],
        "Catalog/Catalog.cs": ["const uint DefaultLevelIdAddr = 0x80056710u;"],
        "sdk/LibEtc.cs": ["Event.Dispatch(e)", "VSyncEvent"],
    }
    hashes = {}
    for relative, required in anchors.items():
        path = source / "RecompOne.Runtime" / relative
        text = path.read_text(encoding="utf-8-sig")
        if any(anchor not in text for anchor in required):
            raise ValueError("Unproved input/scene seam: " + relative)
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    config = (source / "RecompOne.Runtime/Config/GameConfig.cs").read_text()
    defaults = re.findall(r'public string (\w+) \{ get; set; \} = "([^"]+)"', config.split("public class GamepadBindings")[0])
    if len(defaults) != 16 or RESERVED.intersection(value for _, value in defaults):
        raise ValueError("Original Crash defaults conflict or unknown")
    return {"pin": PIN, "source_gate": True, "mapping": "IJKL/U", "hashes": hashes,
            "native_game": "NOT_TESTED", "surface": "AUTHORED_NOT_CRASH"}

def audit(rows: list[dict]) -> dict:
    if not 90 <= len(rows) <= 3600:
        raise ValueError("Expected 90..3600 actual native ticks")
    previous = None
    jump_start = None
    airborne = False
    landed = False
    moved_x = moved_z = False
    intervals = []
    for row in rows:
        if row.get("schema") != 1 or row.get("surface") != "AUTHORED_NOT_CRASH":
            raise ValueError("Unknown evidence schema/surface")
        for key in ("x", "y", "z", "vx", "vy", "vz", "stickX", "stickY"):
            if not isinstance(row[key], (int, float)) or not math.isfinite(row[key]):
                raise ValueError("Nonfinite native evidence")
        if row["frequency"] <= 0 or row["sequence"] < 1:
            raise ValueError("Invalid native clock/input")
        if previous:
            if (row["tick"] != previous["tick"] + 1 or row["sequence"] < previous["sequence"] or
                row["timestamp"] <= previous["timestamp"] or row["hostFrame"] <= previous["hostFrame"]):
                raise ValueError("Nonmonotonic evidence")
            if row["epoch"] != previous["epoch"] or row["actorEpoch"] != previous["actorEpoch"]:
                jump_start = None
                airborne = False
            else:
                elapsed = (row["timestamp"] - previous["timestamp"]) / row["frequency"]
                if elapsed < 1 / 120:
                    raise ValueError("Burst/native tick cadence invalid")
                if elapsed <= .25:
                    intervals.append(elapsed)
                moved_x |= abs(row["x"] - previous["x"]) > .1 and (row["stickX"] != 0 or row["stickY"] != 0)
                moved_z |= abs(row["z"] - previous["z"]) > .1 and (row["stickX"] != 0 or row["stickY"] != 0)
                if row["jump"] and not previous["jump"] and abs(previous["y"]) < 2 and abs(previous["vy"]) < 1:
                    jump_start = row["tick"]
                if jump_start is not None and row["tick"] > jump_start and row["y"] > 20 and row["vy"] > 0:
                    airborne = True
                if airborne and row["tick"] > jump_start and abs(row["y"]) < 2 and abs(row["vy"]) < 1:
                    landed = True
        previous = row
    cadence = len(intervals) >= 60 and .029 <= sum(intervals) / len(intervals) <= .040
    passed = moved_x and moved_z and landed and cadence
    return {"passed": passed, "ticks": len(rows), "native_x_displacement": moved_x,
            "native_z_displacement": moved_z, "input_jump_air_land": landed, "cadence_30hz": cadence,
            "surface": "AUTHORED_NOT_CRASH", "human_playability": "NOT_CERTIFIED",
            "authentic_crash_collision": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--trace", type=Path)
    args = parser.parse_args()
    if bool(args.source) == bool(args.trace):
        parser.error("Choose source or trace")
    if args.source:
        result = source_gate(args.source)
    else:
        if args.trace.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("Evidence exceeds private bound")
        result = audit([json.loads(line) for line in args.trace.read_text().splitlines()])
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("passed", True) else 1

if __name__ == "__main__":
    raise SystemExit(main())
