"""Is a STEP file of a whole assembly the assembly a flattened scene describes?

A whole-assembly STEP file repeats the solids of the part files, each at the
place of one occurrence. `expected()` lists where the scene puts every solid
of every visible occurrence; `match()` pairs that list with the solids found
in a file, by volume and centre of mass. A kernel measures the solids
(`tools/kernel.py`); nothing here needs one.

This checks a file this project generated (`tools/assembly_step.py`) and a file
another system exported from its own assembly document
(`tools/compare_assembly_step.py`): the second is an independent check of the
placements the assembly manifests record.
"""
from __future__ import annotations

from . import transforms as T

# The volume of a solid with spline faces moves a little when a kernel writes it and reads it again
# (2.5e-4 of the volume at most over the 102 solids of the first project, FreeCAD 1.1.3, 2026-11-11).
VOLUME_REL_TOL = 1e-3
POSITION_TOL_MM = 1e-2
FRAMES = ("own", "z-up")


def apply(m, p):
    """The point p moved by the 4x4 transform m."""
    return [m[r][0] * p[0] + m[r][1] * p[1] + m[r][2] * p[2] + m[r][3] for r in range(3)]


def frame_matrix(scene, frame):
    """What takes the scene's own frame to `frame`: the identity, or the scene's turn to Z up."""
    if frame not in FRAMES:
        raise ValueError(f"unknown frame {frame!r}; known: {', '.join(FRAMES)}")
    basis = scene["coordinate_system"].get("basis_to_z_up")
    return basis if frame == "z-up" and basis else T.identity()


def placed(scene):
    """The occurrences a whole-assembly file holds: the visible ones (suppressed ones are not in a scene)."""
    return [o for o in scene["occurrences"] if o.get("visible_effective", True) and not o.get("suppressed")]


def expected(scene, part_solids, frame="own"):
    """Every solid of every placed occurrence, in `frame`, in millimetres.

    part_solids: {part id: [(volume_mm3, [x, y, z] centre of mass in the part's own frame), ...]}.
    """
    if scene["units"] != "mm":
        raise ValueError(f"the scene is in {scene['units']!r}; this reads scenes in mm")
    to_frame = frame_matrix(scene, frame)
    out = []
    for o in placed(scene):
        world = T.multiply(to_frame, o["transform_world"])
        for volume, com in part_solids[o["part_id"]]:
            out.append({"occurrence": o["id"], "part_id": o["part_id"], "volume_mm3": volume,
                        "center_of_mass_mm": apply(world, com)})
    return out


def _distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def match(expected_solids, found, volume_rel_tol=VOLUME_REL_TOL, position_tol_mm=POSITION_TOL_MM):
    """Pair each expected solid with the nearest found solid of the same volume.

    found: [(volume_mm3, [x, y, z])]. A solid is matched when one of the same
    volume (within volume_rel_tol of it) has its centre of mass within
    position_tol_mm. An unmatched solid says how far the nearest solid of its
    volume is: a part in the wrong place shows as that distance, a missing part
    as none. `same` is true when every expected solid is matched and no found
    solid is left over.
    """
    free = list(found)
    unmatched = []
    worst_position = worst_volume = 0.0
    for e in expected_solids:
        best = None
        for j, (volume, com) in enumerate(free):
            if abs(volume - e["volume_mm3"]) <= volume_rel_tol * abs(e["volume_mm3"]):
                d = _distance(com, e["center_of_mass_mm"])
                if best is None or d < best[0]:
                    best = (d, j)
        if best is not None and best[0] <= position_tol_mm:
            volume = free.pop(best[1])[0]
            worst_position = max(worst_position, best[0])
            worst_volume = max(worst_volume, abs(volume - e["volume_mm3"]) / abs(e["volume_mm3"]))
        else:
            unmatched.append({"occurrence": e["occurrence"], "part_id": e["part_id"], "volume_mm3": e["volume_mm3"],
                              "center_of_mass_mm": e["center_of_mass_mm"],
                              "nearest_solid_of_this_volume_mm": None if best is None else best[0]})
    return {
        "same": not unmatched and not free,
        "solids_expected": len(expected_solids), "solids_found": len(found),
        "solids_matched": len(expected_solids) - len(unmatched),
        "unmatched": unmatched,
        "found_but_not_expected": [{"volume_mm3": v, "center_of_mass_mm": list(c)} for v, c in free],
        "worst_position_deviation_mm": worst_position, "worst_relative_volume_deviation": worst_volume,
        "tolerances": {"volume_relative": volume_rel_tol, "position_mm": position_tol_mm},
    }
