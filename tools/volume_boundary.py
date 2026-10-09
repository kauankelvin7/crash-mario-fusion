"""Authored single-leaf c1 reference fixture -> explicit candidate top boundary.

Not a retail octree decoder, Launcher extractor, material mapper or live collider.
The c1 reference shifts zone origin/dimensions by 8; that evidence applies only
to this declared source format, not to a rendered mesh or Launcher guest data.
"""
from dataclasses import dataclass

from tools.geometry_preflight import preflight_mesh, plan_native_surfaces


@dataclass(frozen=True)
class AuthoredLeaf:
    origin: tuple
    dimensions: tuple
    provenance: str
    node: int

    def raw_bounds(self):
        """Reference bounds for query origin (0,0,0), including compact s16 safety."""
        if self.provenance != "AUTHORED_C1_SINGLE_LEAF":
            raise ValueError("Only caller-authored reference leaves are supported")
        if self.node != 3 or type(self.node) is not int:
            raise ValueError("Only explicit ordinary reference type-1 leaf 0x0003 supported")
        if (not isinstance(self.origin,(tuple,list)) or not isinstance(self.dimensions,(tuple,list))
                or len(self.origin) != 3 or len(self.dimensions) != 3):
            raise ValueError("Three source origin and dimension values required")
        # Keep this proof in the source-defined nonnegative arithmetic domain:
        # original c1 left-shifts signed coordinates; negative shifts are UB in C.
        if any(type(v) is not int or not 0 <= v <= 2047 for v in self.origin):
            raise ValueError("Reference origin*16 must fit the nonnegative compact signed-s16 query")
        if any(type(v) is not int or not 0 < v <= 32767 for v in self.dimensions):
            raise ValueError("Reference dimensions must be positive signed-s16 units")
        lo = tuple(v*256 for v in self.origin)
        hi = tuple((v+d)*256 for v,d in zip(self.origin,self.dimensions))
        if any(v >= 2**31 for v in hi):
            raise ValueError("Reference raw endpoint exceeds signed int32")
        return lo,hi


def top_boundary(leaf, *, frame_map, crash_level, mario_frame, calibrated_level,
                 material, surface_capacity, node_capacity, surfaces_used, nodes_used):
    """Two upward faces for a reviewed authored top, not full volumetric semantics."""
    lo,hi=leaf.raw_bounds()
    x,y,z=(v/256 for v in lo)
    xx,yy,zz=(v/256 for v in hi)
    preview=preflight_mesh(vertices=[(x,yy,z),(x,yy,zz),(xx,yy,z),(xx,yy,zz)],
        triangles=[(0,1,2),(2,1,3)], frame_map=frame_map,crash_level=crash_level,
        calibrated_level=calibrated_level,mario_frame=mario_frame)
    plan=plan_native_surfaces(preview,materials=[material,material],
        surface_capacity=surface_capacity,node_capacity=node_capacity,
        surfaces_used=surfaces_used,nodes_used=nodes_used)
    return dict(interpretation="AUTHORED_REFERENCE_TOP_BOUNDARY_ONLY",
                source_raw_bounds=(lo,hi),query_bound_origin_raw=(0,0,0),preview=preview,plan=plan,
                full_volume_equivalence=False,live_collision_inserted=False)
