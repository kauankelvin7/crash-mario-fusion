"""Expose the pinned host focus/pause gate only in the isolated M43 clone."""
import argparse
from pathlib import Path
from tools.m43_live_gate import source_gate
from tools.prepare_m41b2_atlas import action as verify_atlas

def prepare(source: Path, target: Path, verify_only=False):
    source_gate(source)
    if source.resolve() == target.resolve():
        raise ValueError("Refuse public source edits")
    verify_atlas(source, target, Path(__file__).resolve().parents[1] /
                 "integration/embedded_mario/OriginalMarioAtlasHost.cs", True)
    path = target / "RecompOne.Runtime/Host/Window/OriginalMarioInputHost.cs"
    expected = (Path(__file__).resolve().parents[1] / "integration/embedded_mario/OriginalMarioInputHost.cs").read_bytes()
    if path.exists():
        if path.read_bytes() != expected:
            raise ValueError("Private input host drift")
    elif verify_only:
        raise ValueError("Private input host missing")
    else:
        path.write_bytes(expected)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--private-clone", required=True, type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    prepare(args.source, args.private_clone, args.verify_only)
    print("M43_PRIVATE_INPUT_HOST_OK native_game=NOT_TESTED")

if __name__ == "__main__":
    main()
