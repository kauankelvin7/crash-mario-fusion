"""Asset-free triangular geometry preflight for a *candidate* M3 placement.

This module NEVER extracts commercial assets, installs native surfaces, writes
game RAM, or declares a collision. Inputs are authored/synthetic vertices in
already-reviewed Crash *view units*, not guessed retail mesh-format bytes.

A live world/geometry seam and verified calibration are required before any
mapped triangle may be used inside either original game engine.
"""
import math

from tools.world_coordinates import FrameMap, sm64_floor_query_safe, vector


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normal(vertices):
    a, b, c = vertices
    u = tuple(bi - ai for ai, bi in zip(a, b))
    v = tuple(ci - ai for ai, ci in zip(a, c))
    normal = _cross(u, v)
    twice_area = math.hypot(*normal)
    if not math.isfinite(twice_area) or twice_area == 0:
        raise ValueError("Triangle is degenerate or its normal overflows")
    return normal, twice_area


def native_cell_span(vertices):
    """Exact pinned surface_load.c cell fan-out, including its 50-unit border."""
    def lower(value):
        coord = value + 8192
        return max(0, coord // 1024 - (coord % 1024 < 50))

    def upper(value):
        coord = value + 8192
        return min(15, coord // 1024 + (coord % 1024 > 974))

    lo_x, hi_x = lower(min(v[0] for v in vertices)), upper(max(v[0] for v in vertices))
    lo_z, hi_z = lower(min(v[2] for v in vertices)), upper(max(v[2] for v in vertices))
    return lo_x, hi_x, lo_z, hi_z


def native_integer_normal(vertices):
    # The original loader computes these products/subtractions in signed s32.
    # s16 vertices alone do not guarantee freedom from signed overflow.
    if (len(vertices) != 3 or any(len(p) != 3 or any(type(v) is not int or not -32768 <= v <= 32767
                                                   for v in p) for p in vertices)):
        raise ValueError("Native triangle requires three signed-s16 XYZ vertices")
    a, b, c = vertices
    u = tuple(y-x for x, y in zip(a, b))
    v = tuple(y-x for x, y in zip(b, c))
    for i, j in ((1, 2), (2, 0), (0, 1)):
        p, q = u[i]*v[j], u[j]*v[i]
        if any(not -(2**31) <= n < 2**31 for n in (p, q, p-q)):
            raise ValueError("Native s32 triangle normal arithmetic would overflow")
    if min(p[1] for p in vertices) < -32763 or max(p[1] for p in vertices) > 32762:
        raise ValueError("Native lowerY/upperY padding would overflow s16")
    return _normal(vertices)


def plan_native_surfaces(preview, *, materials, surface_capacity, node_capacity,
                         surfaces_used, nodes_used):
    """Bounded offline reservation; caller must supply observed capacities.

    Only explicitly authored test materials are supported, never inferred Crash
    semantics. These native type IDs come from surface_terrains.h. Live insertion
    remains gated on provenance, identity, capacity and lifecycle observation.
    """
    for value in (surface_capacity, node_capacity, surfaces_used, nodes_used):
        if type(value) is not int or not 0 <= value <= 1000000:
            raise ValueError("Explicit bounded nonnegative pool counts required")
    if surfaces_used > surface_capacity or nodes_used > node_capacity:
        raise ValueError("Invalid existing pool occupancy")
    if (preview.get("interpretation") != "SYNTHETIC_GEOMETRY_PREFLIGHT_ONLY" or
            not 1 <= len(preview["triangles"]) <= 512):
        raise ValueError("A bounded geometry preflight result is required")
    if not isinstance(materials, (list,tuple)) or len(materials) != len(preview["triangles"]):
        raise ValueError("One explicit material record required per triangle")
    records = []
    for face, material in zip(preview["triangles"], materials):
        if (not isinstance(material,dict) or material.get("provenance") != "AUTHORED_SYNTHETIC" or
                type(material.get("native_type")) is not int or
                material["native_type"] not in (0x0000, 0x0001) or
                type(material.get("room")) is not int or not -128 <= material["room"] <= 127):
            raise ValueError("Unsupported or unverified material/room mapping")
        vertices = face["s16_trunc_vertices"]
        normal, area = native_integer_normal(vertices)
        if any(not sm64_floor_query_safe(p) for p in vertices):
            raise ValueError("Native triangle exceeds conservative query bounds")
        span = native_cell_span(vertices)
        nodes = (span[1]-span[0]+1) * (span[3]-span[2]+1)
        ny = normal[1]/area
        records.append(dict(vertices=vertices, material=dict(material), cell_span=span,
                            nodes_required=nodes, unit_normal=tuple(v/area for v in normal),
                            partition="floor" if ny > 0.01 else "ceiling" if ny < -0.01 else "wall"))
    nodes = sum(record["nodes_required"] for record in records)
    if surfaces_used + len(records) > surface_capacity or nodes_used + nodes > node_capacity:
        raise ValueError("Insufficient surface/node capacity; no reservation performed")
    return dict(interpretation="SYNTHETIC_NATIVE_SURFACE_PLAN_ONLY", surfaces=records,
                surfaces_required=len(records), nodes_required=nodes,
                engine_collision_inserted=False)


def preflight_mesh(*, vertices, triangles, frame_map, crash_level, mario_frame,
                   calibrated_level):
    """Validate a synthetic triangle index buffer without loading any engine.

    `vertices` are Crash view-unit XYZ, NOT original game geometry bytes.
    Calibrated identity is passed explicitly; no fallback scale, location,
    material, collision category, or Mario area is invented.
    """
    if not isinstance(frame_map, FrameMap):
        raise ValueError("An explicit calibrated FrameMap is required")
    if type(crash_level) is not int or type(calibrated_level) is not int:
        raise ValueError("Crash level identities must be integers")
    if crash_level != calibrated_level:
        raise ValueError("Crash level differs from the calibrated level")
    if not isinstance(mario_frame, str) or not mario_frame.strip():
        raise ValueError("Explicit Mario area/frame identity is required")
    if not isinstance(vertices, (list, tuple)) or not isinstance(triangles, (list, tuple)):
        raise ValueError("Vertex and triangle arrays are required")
    # Defensive offline preview limits only, NOT an available native surface budget.
    # The original sm64ex allocator has ineffective per-pool overrun checks.
    if not 3 <= len(vertices) <= 4096 or not 1 <= len(triangles) <= 512:
        raise ValueError("Candidate mesh size outside bounded offline preflight limits")

    source = tuple(vector(point) for point in vertices)
    target = tuple(frame_map.to_mario(point) for point in source)
    if any(not sm64_floor_query_safe(point) for point in target):
        raise ValueError("Mapped vertex lies outside conservative Mario floor-query bounds")

    previews, seen = [], set()
    for face in triangles:
        if (not isinstance(face, (list, tuple)) or len(face) != 3 or
                any(type(index) is not int or index < 0 or index >= len(source)
                    for index in face)):
            raise ValueError("Triangle indices must be three valid non-boolean integers")
        indices = tuple(face)
        if len(set(indices)) != 3:
            raise ValueError("Triangle references a vertex more than once")
        if frozenset(indices) in seen:
            raise ValueError("Duplicate or reversed triangle uses the same vertices")
        seen.add(frozenset(indices))

        original_normal, source_double_area = _normal(tuple(source[i] for i in indices))
        mapped_normal, target_double_area = _normal(tuple(target[i] for i in indices))
        # Native sm64ex Surface vertices are signed Vec3s, not f32. Simulate a
        # conservative C-style truncation; a mapped f32 triangle might collapse
        # once vertices become s16. This does NOT write or allocate a Surface.
        quantized = tuple(tuple(math.trunc(component) for component in target[i])
                          for i in indices)
        quantized_normal, quantized_double_area = native_integer_normal(quantized)
        # Positive uniform scale and Y-axis rotation must preserve triangle
        # winding. No implied relationship to any native material/collision id.
        expected_normal = frame_map._rotate(original_normal)
        expected_magnitude = math.hypot(*expected_normal)
        dot = sum(a*b for a, b in zip(mapped_normal, expected_normal))
        orientation_cosine = dot / (target_double_area * expected_magnitude)
        if not math.isfinite(orientation_cosine) or orientation_cosine <= 0:
            raise ValueError("Mapping changed triangle orientation or collapsed its normal")
        quantized_dot = sum(a*b for a, b in zip(quantized_normal, expected_normal))
        if not math.isfinite(quantized_dot) or quantized_dot <= 0:
            raise ValueError("Native s16 vertex quantization changes orientation")
        previews.append({
            "indices": indices,
            "source_double_area": source_double_area,
            "mapped_double_area": target_double_area,
            "s16_trunc_double_area": quantized_double_area,
            "orientation_cosine": min(1.0, orientation_cosine),
            "s16_trunc_vertices": quantized,
        })

    return {
        "interpretation": "SYNTHETIC_GEOMETRY_PREFLIGHT_ONLY",
        "engine_collision_inserted": False,
        "engine_rendering_inserted": False,
        "native_surface_pool_capacity_verified": False,
        "native_material_and_room_verified": False,
        "frame_identity": "OPERATOR_SUPPLIED_NOT_RUNTIME_VERIFIED",
        "crash_level": crash_level,
        "mario_frame": mario_frame,
        "vertices_crash_view_units": source,
        "vertices_mario_candidate": target,
        "triangles": previews,
    }
