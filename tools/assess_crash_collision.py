"""Strict G1 audit of private source-volume observations; never a G2 converter."""
import argparse
import json
from pathlib import Path
import re
import sys

LAUNCHER_PIN = "224da7757920a817de2d9242416f657ab95782ea"
C1_PIN = "256fdcef59f15a190290cc19db3fa9a707843b69"
BASE, END = 0x80000000, 0x80200000


def integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("INTEGER_DOMAIN")
    return value


def vector(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("XYZ_DOMAIN")
    return tuple(integer(part, -(2**31), 2**31 - 1) for part in value)


def pointer(value, span=4):
    integer(value, BASE, END - span)
    if value % 4:
        raise ValueError("POINTER_ALIGNMENT")
    return value


def validate(record):
    integer(record["version"], 1, 1)
    integer(record["level"], 9, 9)
    if record["version"] != 1 or record["launcherPin"] != LAUNCHER_PIN or record["c1Pin"] != C1_PIN:
        raise ValueError("VERSION_OR_PIN")
    if record["level"] != 9 or record["source"] != "C1_ZONE_ITEM1" or record["phase"] != "PAD_UNKNOWN":
        raise ValueError("SOURCE_SCOPE_OR_PHASE")
    for name in ("originalQueryCorrelated", "allocationGenerationKnown", "neighborCoverage",
                 "materialMappingKnown", "triangles"):
        if record[name] is not False:
            raise ValueError("UNSUPPORTED_PROMOTION")
    integer(record["sequence"], 1, 24)
    integer(record["epoch"], 1, 2**31 - 1)
    pointer(record["path"])
    pointer(record["actor"], 0x124)
    pointer(record["actorZone"])
    vector(record["position"])
    zone = record["zone"]
    pointer(zone["Entry"], 28)
    integer(zone["Eid"], 0, 2**32 - 1)
    integer(zone["EntryType"], 0, 2**32 - 1)
    start, end = pointer(zone["RectAddress"]), pointer(zone["RectEnd"], 0)
    if not 36 <= end - start <= 65536 or not re.fullmatch("[0-9a-f]{64}", zone["Digest"]):
        raise ValueError("RECT_PROVENANCE")
    low, high = vector(zone["Min"]), vector(zone["Max"])
    depths = vector(zone["Depths"])
    if any(not 0 <= depth <= 16 for depth in depths) or any(a >= b for a, b in zip(low, high)):
        raise ValueError("ZONE_BOUNDS")
    volumes = zone["Volumes"]
    if not isinstance(volumes, list) or not 1 <= len(volumes) <= 4096:
        raise ValueError("VOLUME_CAPACITY")
    seen = set()
    for volume in volumes:
        node = integer(volume["Node"], 1, 65535)
        depth = integer(volume["Depth"], 0, max(depths))
        first, last = vector(volume["Min"]), vector(volume["Max"])
        if not node & 1 or any(not a <= c < d <= b for a, b, c, d in zip(low, high, first, last)):
            raise ValueError("VOLUME_BOUNDS")
        for axis in range(3):
            size = (high[axis] - low[axis]) >> min(depth, depths[axis])
            if size <= 0 or last[axis] - first[axis] != size or (first[axis] - low[axis]) % size:
                raise ValueError("VOLUME_SUBDIVISION")
        identity = (first, last)
        if identity in seen:
            raise ValueError("DUPLICATE_VOLUME")
        seen.add(identity)
    return (record["level"], zone["Entry"], zone["Eid"], zone["EntryType"], start, end,
            zone["Digest"], record["path"], record["actor"], record["actorZone"])


def assess(records):
    result = dict(g1_passed=False, g2_allowed=False, diagnostic_observed=False,
                  samples=len(records), status="BLOCKED")
    try:
        if not 3 <= len(records) <= 24:
            raise ValueError("SAMPLE_COUNT")
        previous_sequence = previous_epoch = 0
        scopes, positions, fingerprints = {}, {}, {}
        previous_scope = None
        for record in records:
            scope = validate(record)
            epoch = record["epoch"]
            if record["sequence"] != previous_sequence + 1 or epoch < previous_epoch:
                raise ValueError("NONMONOTONIC_SEQUENCE_OR_EPOCH")
            if previous_scope is not None and scope != previous_scope and epoch == previous_epoch:
                raise ValueError("STALE_SCENE_EPOCH")
            key = (epoch, scope)
            fingerprint = json.dumps(record["zone"], sort_keys=True, separators=(",", ":"))
            if key in fingerprints and fingerprints[key] != fingerprint:
                raise ValueError("SAME_SCOPE_VOLUME_DRIFT")
            fingerprints[key] = fingerprint
            scopes[key] = scopes.get(key, 0) + 1
            positions.setdefault(key, set()).add(tuple(record["position"]))
            previous_sequence, previous_epoch, previous_scope = record["sequence"], epoch, scope
        eligible = [key for key in scopes if scopes[key] >= 3 and len(positions[key]) >= 2]
        if not eligible:
            raise ValueError("NO_STABLE_MOVING_SCENE")
        result.update(diagnostic_observed=True, reason="VOLUMES_OBSERVED_NOT_PHYSICS_PROVEN",
                      blockers=["PAD_UNKNOWN", "ORIGINAL_QUERY_UNCORRELATED", "NEIGHBORS_UNCOVERED",
                                "ALLOCATION_GENERATION_UNKNOWN", "MATERIAL_MAPPING_UNKNOWN",
                                "CRASH_TO_MARIO_LANDMARK_TRANSFORM_UNPROVEN"])
    except (ValueError, KeyError, TypeError) as error:
        result["reason"] = str(error)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-log", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.private_log.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("PRIVATE_LOG_CAPACITY")
        records = []
        with args.private_log.open("rb") as stream:
            for line in stream:
                if line.startswith(b"CM64_COLLISION "):
                    if len(records) >= 24:
                        raise ValueError("SAMPLE_CAPACITY")
                    records.append(json.loads(line[len(b"CM64_COLLISION "):].decode("utf-8")))
        result = assess(records)
    except (OSError, ValueError) as error:
        result = dict(g1_passed=False, g2_allowed=False, status="BLOCKED", reason=str(error))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["g1_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
