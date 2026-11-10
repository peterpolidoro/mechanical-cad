"""4x4 rigid transforms as nested lists: row-major, applied to column vectors.

    p_parent = T_parent_from_child @ [x, y, z, 1]^T
    T_root_from_child = T_root_from_parent @ T_parent_from_child

The convention and the rigidity rule are those of mechanical-docs
(mechanical_docs/transforms.py), which reads the scene this package writes.
Rotations must be orthonormal with determinant +1; a reflection, scale or shear
is refused, never applied.
"""
from __future__ import annotations

import math

UNIT_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}


class TransformError(ValueError):
    pass


def identity():
    return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def check_matrix(m, where="transform", tol=1e-6):
    """Return the matrix as floats if it is a rigid 4x4; raise TransformError otherwise."""
    if not isinstance(m, list) or len(m) != 4 or any(not isinstance(r, list) or len(r) != 4 for r in m):
        raise TransformError(f"{where}: expected a 4x4 nested list")
    out = []
    for r in m:
        row = []
        for v in r:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TransformError(f"{where}: non-numeric entry")
            if not math.isfinite(v):
                raise TransformError(f"{where}: non-finite entry")
            row.append(float(v))
        out.append(row)
    if any(abs(a - b) > tol for a, b in zip(out[3], [0.0, 0.0, 0.0, 1.0])):
        raise TransformError(f"{where}: last row must be [0, 0, 0, 1], got {out[3]}")
    rot = [r[:3] for r in out[:3]]
    for i in range(3):
        for j in range(3):
            dot = sum(rot[k][i] * rot[k][j] for k in range(3))
            want = 1.0 if i == j else 0.0
            if abs(dot - want) > tol * 10:
                raise TransformError(f"{where}: rotation block is not orthonormal (scale or shear present)")
    if det3(rot) < 0:
        raise TransformError(f"{where}: rotation determinant is negative (a reflection)")
    return out


def det3(r):
    return (r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
            - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
            + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]))


def multiply(a, b):
    """a @ b for 4x4 nested lists."""
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def translation(m):
    return [m[0][3], m[1][3], m[2][3]]


def scaled_translation(m, factor):
    """The same rotation with the translation multiplied by `factor` (a unit change)."""
    out = [list(r) for r in m]
    for r in range(3):
        out[r][3] *= factor
    return out


def unit_factor(src, dst):
    """Multiply a length in `src` by this to get `dst`."""
    try:
        return UNIT_TO_MM[src] / UNIT_TO_MM[dst]
    except KeyError:
        raise TransformError(f"unsupported unit {src!r} or {dst!r}; known: {sorted(UNIT_TO_MM)}") from None


def deviation(a, b):
    """(largest difference between rotation cells, largest difference between translation cells)."""
    rot = max(abs(a[r][c] - b[r][c]) for r in range(3) for c in range(3))
    tra = max(abs(a[r][3] - b[r][3]) for r in range(3))
    return rot, tra


def basis_to_z_up(up_axis):
    """The rigid matrix taking coordinates of a frame with the given up axis to a +Z-up frame."""
    if up_axis == "+Z":
        return identity()
    if up_axis == "+Y":
        # (x, y, z) -> (x, -z, y): the mapping the Inventor exporter declares and mechanical-docs accepts
        return [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, -1.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    raise TransformError(f"unsupported up axis {up_axis!r}; known: '+Z', '+Y'")
