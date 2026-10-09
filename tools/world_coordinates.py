"""Read-only Crash NTSC-U -> sm64ex coordinate contract; never writes game state.

Crash translation has 8 fractional bits (pinned Launcher CameraTrace).
Mario positions are native float32. Cross-game scale/origins/yaw are calibration
inputs, not facts implied by those representations. See docs/CONTRACT.md.
"""
import argparse
import json
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path


def vector(value):
    if len(value) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float))
                              or not math.isfinite(v) for v in value):
        raise ValueError("Expected three finite numeric coordinates")
    return tuple(value)


def decode_crash(raw):
    if len(raw) != 3 or any(type(v) is not int or not -(2**31) <= v < 2**31 for v in raw):
        raise ValueError("Crash translation must be signed int32 XYZ")
    return tuple(v / 256 for v in raw)


def encode_crash(position):
    # Nearest fixed-point sample; maximum coordinate error is 1/512 unit.
    try:
        raw = tuple(round(v * 256) for v in vector(position))
    except OverflowError as exc:
        raise ValueError("Position exceeds Crash fixed-point range") from exc
    decode_crash(raw)  # reject overflow, never wrap memory coordinates
    return raw


def sm64_floor_query_safe(position):
    """Conservative preflight, NOT a collision result or proof a floor exists.

    Full sm64ex find_floor casts XYZ to s16 and rejects XZ outside +/-0x2000.
    Reject wraparound before that cast; retain an open XZ boundary.
    """
    x, y, z = vector(position)
    return -8192 < x < 8192 and -8192 < z < 8192 and -32768 <= y <= 32767


@dataclass(frozen=True)
class FrameMap:
    crash_origin: tuple
    mario_origin: tuple
    scale: float
    yaw_degrees: float

    def __post_init__(self):
        object.__setattr__(self, "crash_origin", vector(self.crash_origin))
        object.__setattr__(self, "mario_origin", vector(self.mario_origin))
        if (isinstance(self.scale, bool) or not isinstance(self.scale, (int, float))
                or not math.isfinite(self.scale) or self.scale <= 0):
            raise ValueError("An explicitly calibrated positive scale is required")
        if (isinstance(self.yaw_degrees, bool) or not isinstance(self.yaw_degrees, (int, float))
                or not math.isfinite(self.yaw_degrees)):
            raise ValueError("A finite, explicitly calibrated yaw is required")

    def _rotate(self, position, inverse=False):
        x, y, z = position
        angle = math.radians(self.yaw_degrees % 360) * (-1 if inverse else 1)
        c, s = math.cos(angle), math.sin(angle)
        return c*x + s*z, y, -s*x + c*z

    def to_mario(self, crash_position):
        position = vector(crash_position)
        delta = vector(tuple(v-o for v, o in zip(position, self.crash_origin)))
        result = vector(tuple(o + self.scale*v for o, v in
                              zip(self.mario_origin, self._rotate(delta))))
        # Model the actual target position representation, including float32 overflow.
        try:
            target = vector(struct.unpack("<3f", struct.pack("<3f", *result)))
        except OverflowError as exc:
            raise ValueError("Mapped position exceeds Mario float32 range") from exc
        recovered = self.to_crash(target)
        if max(abs(a-b) for a, b in zip(position, recovered)) > 1/512:
            raise ValueError("Mario float32 quantization loses more than half a Crash raw unit; recalibrate")
        return target

    def to_crash(self, mario_position):
        delta = vector(tuple((v-o)/self.scale for v, o in
                             zip(vector(mario_position), self.mario_origin)))
        return vector(tuple(o+v for o, v in zip(self.crash_origin, self._rotate(delta, True))))


def map_log(log, calibration):
    if calibration.get("schema_version") != 1 or type(calibration.get("crash_level")) is not int:
        raise ValueError("Calibration needs schema_version=1 and explicit crash_level")
    if not isinstance(calibration.get("mario_frame"), str) or not calibration["mario_frame"].strip():
        raise ValueError("Explicit operator-confirmed Mario level/area label required")
    mapping = FrameMap(*(calibration[key] for key in
                         ("crash_origin", "mario_origin", "scale", "yaw_degrees")))
    samples = []
    for line in log.splitlines():
        if "[cm64] motion_sample " not in line:
            continue
        fields = dict(re.findall(r"(\w+)=([^\s]+)", line))
        # Older M2 logs lack XZ: refuse to invent a 3D coordinate.
        raw = tuple(int(fields[key]) for key in ("x_raw", "y_raw", "z_raw"))
        if int(fields["crash_level"]) != calibration["crash_level"]:
            raise ValueError("Trace crossed calibrated Crash level; recalibrate")
        crash = decode_crash(raw)
        mario = mapping.to_mario(crash)
        samples.append(dict(seq=int(fields["seq"]), n=int(fields["n"]),
                            crash_native=crash, mario_candidate=mario,
                            roundtrip_error=max(abs(a-b) for a, b in zip(crash, mapping.to_crash(mario))),
                            floor_query_safe=sm64_floor_query_safe(mario)))
    if not samples:
        raise ValueError("No complete native XYZ motion samples found")
    return dict(interpretation="OBSERVATION_ONLY", mario_frame=calibration["mario_frame"],
                frame_identity="OPERATOR_SUPPLIED_NOT_RUNTIME_VERIFIED", samples=samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = map_log(args.log.read_text(encoding="utf-8-sig"),
                         json.loads(args.calibration.read_text(encoding="utf-8-sig")))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f"Coordinate validation failed: {exc}\n")
    print(json.dumps(result, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
