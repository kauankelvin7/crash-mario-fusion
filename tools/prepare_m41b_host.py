"""M4.1B1 public Crash host source patch in a *private cloned checkout* only.

Fail closed on version drift, missing exact anchors, pre-existing edits or
attempted overwrites. No retail assets or binaries emitted into Git checkout.
"""
from __future__ import annotations

import argparse
from pathlib import Path

EXPECTED_PIN = "224da7757920a817de2d9242416f657ab95782ea"

MENU_ANCHOR = """    public static void RegisterWindow(Action draw)
    {
        if (draw == null) return;
        _windows.Add(draw);
    }
"""
MENU_REPLACEMENT = MENU_ANCHOR + """
    // M4.1B1 private host extension. Draws strictly within the presented Crash
    // OutputPanel image bounds, not an arbitrarily guessed desktop rectangle.
    private static readonly List<Action<System.Numerics.Vector2, System.Numerics.Vector2>>
        _outputOverlays = [];
    private static readonly object _outputOverlayLock = new();

    public static void RegisterOutputOverlay(Action<System.Numerics.Vector2,
        System.Numerics.Vector2> draw)
    {
        if (draw == null) return;
        lock (_outputOverlayLock)
            if (!_outputOverlays.Contains(draw)) _outputOverlays.Add(draw);
    }

    public static void UnregisterOutputOverlay(Action<System.Numerics.Vector2,
        System.Numerics.Vector2> draw)
    {
        lock (_outputOverlayLock) _outputOverlays.Remove(draw);
    }

    internal static void DrawOutputOverlays(System.Numerics.Vector2 min,
                                           System.Numerics.Vector2 max)
    {
        if (max.X <= min.X || max.Y <= min.Y) return;
        Action<System.Numerics.Vector2, System.Numerics.Vector2>[] callbacks;
        lock (_outputOverlayLock) callbacks = _outputOverlays.ToArray();
        foreach (var callback in callbacks)
        {
            try { callback(min, max); }
            catch (Exception e)
            {
                lock (_outputOverlayLock) _outputOverlays.Remove(callback);
                Console.Error.WriteLine("[cm64-output] overlay disabled: " +
                                        e.GetType().Name);
            }
        }
    }
"""
OUTPUT_ANCHOR = """        ImGui.Image((nint)_texId, imageSize);
"""
OUTPUT_REPLACEMENT = OUTPUT_ANCHOR + """        // Exact displayed Crash image rect; never touch original scene GPU state.
        MenuRegistry.DrawOutputOverlays(ImGui.GetItemRectMin(),
                                        ImGui.GetItemRectMax());
"""

def patch_private(source: Path, target: Path):
    if source.resolve() == target.resolve():
        raise ValueError("Refuse to patch public upstream in place")
    if not target.exists():
        raise ValueError("Private target clone does not exist")
    files = [
        ("RecompOne.Runtime/Host/Window/MenuRegistry.cs", MENU_ANCHOR, MENU_REPLACEMENT),
        ("RecompOne.Runtime/Host/Window/Panels/Debug/OutputPanel.cs", OUTPUT_ANCHOR, OUTPUT_REPLACEMENT)
    ]
    # The source must be an identical clone: this is not a generic patch utility.
    planned = []
    for name, old, new in files:
        upstream = (source / name).read_bytes()
        checkout = (target / name).read_bytes()
        if checkout != upstream:
            raise ValueError("Private clone differs from public source: " + name)
        raw = checkout.decode("utf-8-sig").replace("\r\n", "\n")
        if raw.count(old) != 1 or "RegisterOutputOverlay" in raw:
            raise ValueError("Unverified original source anchor: " + name)
        patched = raw.replace(old, new)
        planned.append((target / name, patched))
    for path, patched in planned:
        path.write_text(patched, encoding="utf-8", newline="")
    return [str(path) for path, _ in planned]


def verify_private(source: Path, target: Path):
    files = [
        ("RecompOne.Runtime/Host/Window/MenuRegistry.cs", MENU_ANCHOR, MENU_REPLACEMENT),
        ("RecompOne.Runtime/Host/Window/Panels/Debug/OutputPanel.cs", OUTPUT_ANCHOR, OUTPUT_REPLACEMENT)
    ]
    for name, original, replacement in files:
        upstream = (source / name).read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
        if upstream.count(original) != 1:
            raise ValueError("Unverified original source: " + name)
        expected = upstream.replace(original, replacement)
        installed = (target / name).read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
        if expected != installed:
            raise ValueError("Private generated renderer source changed: " + name)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--private-clone", type=Path, required=True)
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()
    if args.verify_only:
        verify_private(args.source, args.private_clone)
        print("PRIVATE_HOST_PATCH_VERIFIED")
    else:
        paths = patch_private(args.source, args.private_clone)
        for path in paths:
            print("PRIVATE_HOST_SOURCE_PATCHED:", Path(path).name)

if __name__ == "__main__":
    main()
