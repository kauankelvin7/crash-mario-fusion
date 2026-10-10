"""Asset-free, bounded auditor of private same-pass original GTE/OT receipts.

Passing establishes internal source/projection consistency, never authenticity
of a game run, postphysics ownership, complete depth or usable collision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.prepare_m41b_host import EXPECTED_PIN
from tools.prepare_world_source_probe import C1_PIN

PREFIX = "[cm64-world] "
MAX_BYTES = 4 * 1024 * 1024
MAX_LINE = 16384
MAX_RECORDS = 24


def integer(value: object, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError("Integer type/range rejected")
    return value


def vector(value: object, size: int, low: int, high: int) -> list[int]:
    if not isinstance(value, list) or len(value) != size:
        raise ValueError("Vector shape rejected")
    return [integer(item, low, high) for item in value]


def physical(address: object, size: int = 4) -> int:
    address = integer(address, 0, 0xFFFFFFFF)
    if address >> 29 not in (0, 4, 5):
        raise ValueError("Non-RAM address segment")
    offset = address & 0x1FFFFFFF
    if offset % 4 or offset + size > 0x200000:
        raise ValueError("RAM span rejected")
    return offset


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def decode_vertex(low: int, high: int) -> list[int]:
    bits = high & 0x70006
    return [signed16(high & 0xFFF8), signed16((high >> 16) & 0xFFF8),
            signed16(((low >> 24) << 3) | (bits << 10) | (bits >> 3))]


def divide(h: int, z: int) -> int:
    if z <= 0 or h >= z * 2:
        raise ValueError("GTE divide overflow/near plane")
    shift = 16 - z.bit_length()
    numerator, denominator = h << shift, z << shift
    index = max(0, min(0x100, (denominator - 0x7FC0) >> 7))
    table = max(0, min(255, (0x40000 // (index + 0x100) + 1) // 2 - 0x101))
    reciprocal = table + 0x101
    denominator = (0x2000080 - denominator * reciprocal) >> 8
    denominator = (0x80 + denominator * reciprocal) >> 8
    return min(0x1FFFF, (numerator * denominator + 0x8000) >> 16)


def project(xyz: list[int], rotation: list[int], translation: list[int],
            h: int, ofx: int, ofy: int) -> tuple[int, int]:
    accumulators = [(translation[axis] << 12) +
                    sum(rotation[axis * 3 + column] * xyz[column] for column in range(3))
                    for axis in range(3)]
    if any(not -(1 << 43) <= number < (1 << 43) for number in accumulators):
        raise ValueError("GTE MAC overflow")
    ir = [number >> 12 for number in accumulators]
    if any(not -32768 <= number <= 32767 for number in ir):
        raise ValueError("GTE IR saturation unsupported")
    z = ir[2]
    reciprocal = divide(h, z)
    screen = [reciprocal * ir[0] + ofx, reciprocal * ir[1] + ofy]
    if any(not -(1 << 31) <= number < (1 << 31) for number in screen):
        raise ValueError("GTE screen MAC overflow")
    sx, sy = [number >> 16 for number in screen]
    if not (-1024 <= sx <= 1023 and -1024 <= sy <= 1023):
        raise ValueError("GTE screen saturation unsupported")
    return (sx & 0xFFFF) | ((sy & 0xFFFF) << 16), z


def validate_record(row: object) -> dict:
    if not isinstance(row, dict):
        raise ValueError("Record is not an object")
    if row.get("schema") != 2 or type(row.get("schema")) is not int or row.get("phase") != "GUEST_WORLD_RTPT_OT":
        raise ValueError("Unknown schema/phase")
    if row.get("source_pin") != EXPECTED_PIN or row.get("c1_pin") != C1_PIN or row.get("command") != 0x4A280030:
        raise ValueError("Unknown pinned projection")
    for flag in ("postphysics", "depth_complete", "collision_ready"):
        if row.get(flag) is not False:
            raise ValueError("Unsupported readiness claim")
    if integer(row.get("flag"), 0, 0xFFFFFFFF) != 0:
        raise ValueError("Saturated GTE receipt")
    for name in ("sequence", "epoch", "ot_generation"):
        integer(row.get(name), 1, 0x7FFFFFFF)
    for name in ("level", "draw", "world_key"):
        integer(row.get(name), 0, 0xFFFFFFFF)
    integer(row.get("world"), 0, 7)
    if integer(row.get("zone_magic"), 0, 0xFFFFFFFF) != 0x0100FFFF or \
       row["world"] >= integer(row.get("world_count"), 1, 8):
        raise ValueError("Original zone/world count mismatch")
    for name in ("zone", "path", "header", "polygon"):
        physical(row.get(name), 32 if name == "header" else 8)
    ot, primitive = physical(row.get("ot"), 8192), physical(row.get("primitive"), 40)
    zone_header = physical(row.get("zone_header"), 516)
    if physical(row.get("world_descriptor"), 32) != zone_header + 4 + row["world"] * 64:
        raise ValueError("World descriptor identity mismatch")
    descriptor = vector(row.get("descriptor_words"), 8, 0, 0xFFFFFFFF)
    header = vector(row.get("header_words"), 8, 0, 0xFFFFFFFF)
    poly_id = integer(row.get("poly_id"), 0, 65535)
    id_address = integer(row.get("poly_id_address"), 0, 0xFFFFFFFF)
    physical(id_address & ~3)
    id_word = integer(row.get("poly_id_word"), 0, 0xFFFFFFFF)
    if id_address & 1 or (id_word >> ((id_address & 2) * 8)) & 0xFFFF != poly_id:
        raise ValueError("Original poly ID word mismatch")
    if poly_id >> 12 != row["world"] or poly_id & 0xFFF >= header[3] or header[7] != 0:
        raise ValueError("Unsupported polygon/backdrop")
    if descriptor[0] != row["world_key"] or descriptor[4] != row["header"] or \
       physical(row["polygon"], 8) != physical(descriptor[5], 8) + (poly_id & 0xFFF) * 8:
        raise ValueError("Source world/polygon identity mismatch")
    if primitive < ot + 8192 and primitive + 40 > ot:
        raise ValueError("Primitive overlaps OT")
    words = vector(row.get("vertex_words"), 6, 0, 0xFFFFFFFF)
    xyz = vector(row.get("xyz"), 9, -32768, 32767)
    vertices = vector(row.get("vertex_addresses"), 3, 0, 0xFFFFFFFF)
    addresses = [physical(address, 8) for address in vertices]
    first, second = vector(row.get("polygon_words"), 2, 0, 0xFFFFFFFF)
    offsets = [(second >> 17) & 0x7FF8, (second >> 5) & 0x7FF8, (first >> 17) & 0x7FF8]
    if any(offset // 8 >= header[4] or address != physical(descriptor[6], 8) + offset
           for address, offset in zip(addresses, offsets)):
        raise ValueError("World vertex span/index mismatch")
    if len(set(addresses)) != 3 or len({address - offset for address, offset in zip(addresses, offsets)}) != 1:
        raise ValueError("Polygon-to-vertex identity mismatch")
    for index in range(3):
        if decode_vertex(*words[index * 2:index * 2 + 2]) != xyz[index * 3:index * 3 + 3]:
            raise ValueError("Source vertex does not match GTE input")
    edge1 = [xyz[3 + axis] - xyz[axis] for axis in range(3)]
    edge2 = [xyz[6 + axis] - xyz[axis] for axis in range(3)]
    if all(edge1[(axis + 1) % 3] * edge2[(axis + 2) % 3] ==
           edge1[(axis + 2) % 3] * edge2[(axis + 1) % 3] for axis in range(3)):
        raise ValueError("Degenerate source triangle")
    rotation = vector(row.get("rotation"), 9, -32768, 32767)
    translation = vector(row.get("translation"), 3, -(1 << 31), (1 << 31) - 1)
    vector(row.get("origin"), 3, -(1 << 31), (1 << 31) - 1)
    signed32 = lambda value: value - (1 << 32) if value & (1 << 31) else value
    if [signed32(value) for value in descriptor[1:4]] != translation or \
       [signed32(value) for value in header[0:3]] != row["origin"]:
        raise ValueError("Original world translation/origin mismatch")
    camera = vector(row.get("camera_translation"), 3, -(1 << 31), (1 << 31) - 1)
    relative = [row["origin"][axis] - (camera[axis] >> 8) for axis in range(3)]
    for axis in range(3):
        terms = [rotation[axis * 3 + column] * relative[column] for column in range(3)]
        if any(not -(1 << 31) <= term < (1 << 31) for term in terms) or \
           not -(1 << 31) <= sum(terms) < (1 << 31) or sum(terms) >> 12 != translation[axis]:
            raise ValueError("Original GfxLoadWorlds camera/origin translation mismatch")
    h = integer(row.get("h"), 1, 4096)
    ofx, ofy = [integer(row.get(name), -(1 << 31), (1 << 31) - 1) for name in ("ofx", "ofy")]
    sxy = vector(row.get("sxy"), 3, 0, 0xFFFFFFFF)
    depths = vector(row.get("z"), 3, 1, 65535)
    for index in range(3):
        predicted, depth = project(xyz[index * 3:index * 3 + 3], rotation, translation, h, ofx, ofy)
        if predicted != sxy[index] or depth != depths[index]:
            dx = signed16(predicted) - signed16(sxy[index])
            dy = signed16(predicted >> 16) - signed16(sxy[index] >> 16)
            raise ValueError(f"Reprojection mismatch vertex={index} pixel_dx={dx} pixel_dy={dy} z_error={depth - depths[index]}")
    code = integer(row.get("primitive_code"), 0, 255) & 0xFD
    if code not in (0x30, 0x34):
        raise ValueError("Not an original G3/GT3")
    chain = row.get("ot_chain")
    if not isinstance(chain, list) or not 2 <= len(chain) <= 128:
        raise ValueError("Missing/budget-exceeding OT linkage")
    seen = set()
    previous_tag = None
    for index, link in enumerate(chain):
        address, tag = vector(link, 2, 0, 0xFFFFFFFF)
        offset = physical(address)
        if offset in seen:
            raise ValueError("Cyclic OT link")
        seen.add(offset)
        if index == 0:
            if not ot <= offset < ot + 8192 or tag >> 24:
                raise ValueError("OT chain is not rooted in this frame's table")
        elif previous_tag & 0xFFFFFF != offset:
            raise ValueError("Broken OT link")
        if index == len(chain) - 1:
            if offset != primitive or tag >> 24 != (9 if code == 0x34 else 6):
                raise ValueError("Wrong primitive OT tag")
        previous_tag = tag
    return row


def no_duplicates(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def assess(path: Path) -> dict:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Log byte budget exceeded")
    rows = []
    total = 0
    with path.open("rb") as stream:
        while line := stream.readline(MAX_LINE + 1):
            total += len(line)
            if len(line) > MAX_LINE or total > MAX_BYTES:
                raise ValueError("Log line/byte budget exceeded")
            if b"[cm64-world]" not in line:
                continue
            text = line.decode("utf-8-sig").rstrip("\r\n")
            if not text.startswith(PREFIX):
                raise ValueError("Malformed probe prefix")
            if len(rows) >= MAX_RECORDS:
                raise ValueError("Receipt budget exceeded")
            row = validate_record(json.loads(text[len(PREFIX):], object_pairs_hook=no_duplicates))
            if row["sequence"] != len(rows) + 1:
                raise ValueError("Non-contiguous receipt sequence")
            if rows:
                old = rows[-1]
                if row["ot_generation"] <= old["ot_generation"] or row["epoch"] < old["epoch"]:
                    raise ValueError("Stale OT/epoch")
                if row["epoch"] == old["epoch"] and (row["draw"] <= old["draw"] or
                    any(row[name] != old[name] for name in ("level", "zone", "path"))):
                    raise ValueError("Mixed scene/frame in one epoch")
            rows.append(row)
    if not rows:
        raise ValueError("No source-owned original RTPT/OT receipts")
    return {"self_consistent": True, "status": "RECORDED_G1_CANDIDATE_ONLY",
            "receipts": len(rows), "vertices": len(rows) * 3,
            "max_integer_pixel_error": 0, "max_z_error": 0,
            "run_authenticity_verified": False, "postphysics": False,
            "depth_complete": False, "collision_ready": False, "camera_calibrated": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(assess(args.log), sort_keys=True))
    except (ValueError, OSError, UnicodeError, RecursionError) as error:
        print(json.dumps({"self_consistent": False, "status": "REJECTED", "reason": str(error)}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
