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
        quantized_normal, quantized_double_area = _normal(quantized)
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
