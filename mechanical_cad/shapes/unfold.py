"""The flat pattern of a convex polyhedron: its faces laid in one plane, joined along fold lines.

    from mechanical_cad.shapes import polyhedra, unfold

    pattern = unfold.unfold(polyhedra.named("truncated-octahedron", edge=30.0))
    pattern.polygons      # for every face its corners as (x, y), in the face's own order
    pattern.folds         # the edges along which two faces stay joined, each with its segment and its angle
    pattern.cuts          # the other edges: each is on the outline twice, once for each of its two faces
    pattern.size          # (width, height) of the pattern, which lies between (0, 0) and that corner

The pattern is seen from outside the solid: every face keeps its counter-clockwise order, and every fold bends
the sheet away from the viewer.

Which edges are folds is a choice: any set of edges that joins all the faces without a ring will do (a spanning
tree of the faces), and some choices lay one face over another. `unfold` tries trees in a fixed order and returns
the first whose faces do not overlap: the tree that reaches the faces breadth-first from the root face, the same
from every other face, then the trees left by cutting, at every vertex, the edge that climbs most steeply
towards one of a fixed list of directions. Overlap is decided exactly for convex polygons: two of them have no
area in common when the line through one side of either has the other polygon on its outer side. A solid for
which none of these trees is free of overlap raises `UnfoldError`. For the eighteen named solids, and for the
prism, the antiprism and the box that tests/test_polyhedra.py tries, the first tree is free of it.

Nothing here allows for the thickness of the sheet or the radius of a bend.

Standard library only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .polyhedra import TOLERANCE, cross, dot, norm, sub, unit

STEEPEST_EDGE_DIRECTIONS = 64


class UnfoldError(ValueError):
    pass


@dataclass(frozen=True)
class Fold:
    """An edge along which two faces stay joined. `faces` are the two faces, the one nearer the root first;
    `edge` the two vertices; `segment` where the edge lies in the pattern; `angle` how far the sheet is bent
    there, in radians: the angle between the outward normals of the two faces, pi minus the dihedral angle."""
    faces: tuple
    edge: tuple
    segment: tuple
    angle: float


@dataclass(frozen=True)
class Cut:
    """An edge that is cut. `faces` are its two faces, `edge` its two vertices, and `segments` where it lies in
    the pattern on the first face and on the second: the two are joined again when the pattern is folded up."""
    faces: tuple
    edge: tuple
    segments: tuple


@dataclass(frozen=True)
class Pattern:
    """A flat pattern. `polygons[i]` is face i of the polyhedron, its corners as (x, y) in the order of the face.
    `root` is the face whose first edge runs along +X. There is one fold fewer than there are faces, and the
    folds are in the order in which the faces were laid: each joins one more face to the root and those before."""
    polygons: tuple
    folds: tuple
    cuts: tuple
    size: tuple
    root: int

    @property
    def area(self):
        return math.fsum(polygon_area(p) for p in self.polygons)


def polygon_area(polygon):
    """The area of a polygon given by its corners; positive when they run counter-clockwise."""
    return math.fsum(a[0] * b[1] - a[1] * b[0] for a, b in zip(polygon, polygon[1:] + polygon[:1])) / 2.0


def neighbours(polyhedron):
    """{(a, b): (f, g)}: for every edge, the face f in which it runs from a to b and the face g on its other side."""
    left = {(a, b): f for f, face in enumerate(polyhedron.faces) for a, b in zip(face, face[1:] + face[:1])}
    return {(a, b): (f, left[(b, a)]) for (a, b), f in left.items()}


def breadth_first(polyhedron, start):
    """The folds of the tree that reaches every face from `start` in the fewest steps, as a set of edges."""
    across = neighbours(polyhedron)
    seen, queue, folds = {start}, [start], set()
    for f in queue:
        face = polyhedron.faces[f]
        for a, b in zip(face, face[1:] + face[:1]):
            g = across[(a, b)][1]
            if g not in seen:
                seen.add(g)
                queue.append(g)
                folds.add((min(a, b), max(a, b)))
    return folds


def steepest_edge(polyhedron, direction):
    """The folds left when, at every vertex but the highest along `direction`, the edge that climbs most steeply
    is cut. The cuts reach every vertex and close no ring, so what is left joins all the faces.

    Of two vertices equally high the one further along X counts as higher, then along Y, then along Z: as if the
    direction were tilted a very little, so that there is one highest vertex whatever the direction.
    """
    vertices = polyhedron.vertices
    height = [(dot(v, direction),) + tuple(v) for v in vertices]
    steepest = {}
    for a, b in polyhedron.edges:
        low, high = (a, b) if height[a] < height[b] else (b, a)
        along = sub(vertices[high], vertices[low])
        slope = dot(along, direction) / norm(along)
        if low not in steepest or slope > steepest[low][0]:
            steepest[low] = (slope, (a, b))
    return set(polyhedron.edges) - {edge for _, edge in steepest.values()}


def directions(count):
    """`count` directions spread over the sphere, the same every time (a spiral with the golden angle)."""
    golden = math.pi * (3.0 - math.sqrt(5.0))
    out = []
    for k in range(count):
        z = 1.0 - (2.0 * k + 1.0) / count
        r = math.sqrt(1.0 - z * z)
        out.append((r * math.cos(golden * k), r * math.sin(golden * k), z))
    return out


def lay_out(polyhedron, folds, root=0):
    """Every face in the plane, for a set of fold edges that joins all faces without a ring.

    Returns (polygons, parents): the corners of every face as (x, y), and for every face but the root the face
    it is joined to on the way to the root together with the edge. The root's first corner is at the origin and
    its first edge along +X.
    """
    across = neighbours(polyhedron)
    vertices, faces, normals = polyhedron.vertices, polyhedron.faces, polyhedron.normals
    first = vertices[faces[root][0]]
    u = unit(sub(vertices[faces[root][1]], first))
    v = cross(normals[root], u)
    flat = {root: {i: (dot(sub(vertices[i], first), u), dot(sub(vertices[i], first), v)) for i in faces[root]}}
    parents, queue = {}, [root]
    for f in queue:
        face = faces[f]
        for a, b in zip(face, face[1:] + face[:1]):
            g = across[(a, b)][1]
            if g in flat or (min(a, b), max(a, b)) not in folds:
                continue
            # g is turned about the edge into the plane of f: along the edge and across it, on the far side from f
            (ax, ay), (bx, by) = flat[f][a], flat[f][b]
            length = math.hypot(bx - ax, by - ay)
            ex = ((bx - ax) / length, (by - ay) / length)
            u = unit(sub(vertices[b], vertices[a]))
            v = cross(normals[g], u)
            flat[g] = {}
            for i in faces[g]:
                w = sub(vertices[i], vertices[a])
                s, t = dot(w, u), dot(w, v)
                flat[g][i] = (ax + s * ex[0] - t * ex[1], ay + s * ex[1] + t * ex[0])
            parents[g] = (f, (a, b))
            queue.append(g)
    if len(flat) != len(faces):
        raise ValueError("these folds do not join all the faces")
    return [tuple(flat[f][i] for i in faces[f]) for f in range(len(faces))], parents


def overlapping(polygons, eps):
    """The first two convex polygons, as a pair of indices, that have area in common; None when no two have.

    Polygons run counter-clockwise. Two that share a side or a corner, or lie nearer than `eps`, do not overlap.
    """
    boxes = [(min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly))
             for poly in polygons]

    def apart(one, other):
        """Whether the line through some side of `one` has all of `other` on its outer side."""
        for (ax, ay), (bx, by) in zip(one, one[1:] + one[:1]):
            nx, ny = by - ay, ax - bx                              # outward, for a counter-clockwise polygon
            if all((px - ax) * nx + (py - ay) * ny >= -eps * math.hypot(nx, ny) for px, py in other):
                return True
        return False

    for i in range(len(polygons)):
        for j in range(i + 1, len(polygons)):
            a, b = boxes[i], boxes[j]
            if a[2] <= b[0] + eps or b[2] <= a[0] + eps or a[3] <= b[1] + eps or b[3] <= a[1] + eps:
                continue
            if not apart(polygons[i], polygons[j]) and not apart(polygons[j], polygons[i]):
                return i, j
    return None


def candidates(polyhedron, root=0):
    """The sets of folds that `unfold` tries, in its order."""
    yield breadth_first(polyhedron, root)
    for start in range(len(polyhedron.faces)):
        if start != root:
            yield breadth_first(polyhedron, start)
    for direction in directions(STEEPEST_EDGE_DIRECTIONS):
        yield steepest_edge(polyhedron, direction)


def unfold(polyhedron, root=0):
    """The flat pattern of a convex polyhedron in which no two faces overlap, as a `Pattern`.

    `root` is the face laid first: its first edge runs along +X, and the search for a tree starts from it. The
    pattern is then moved so that it lies between (0, 0) and `size`. Raises `UnfoldError` when none of the
    trees tried is free of overlap.
    """
    if not 0 <= root < len(polyhedron.faces):
        raise ValueError(f"{polyhedron.name} has no face {root}")
    eps = TOLERANCE * polyhedron.circumradius
    tried = 0
    for folds in candidates(polyhedron, root):
        tried += 1
        polygons, parents = lay_out(polyhedron, folds, root)
        if overlapping(polygons, eps) is None:
            return _pattern(polyhedron, polygons, parents, root)
    raise UnfoldError(f"{polyhedron.name}: every one of the {tried} flat patterns tried lays one face over another")


def _pattern(polyhedron, polygons, parents, root):
    low_x = min(x for polygon in polygons for x, _ in polygon)
    low_y = min(y for polygon in polygons for _, y in polygon)
    polygons = tuple(tuple((x - low_x, y - low_y) for x, y in polygon) for polygon in polygons)
    size = (max(x for polygon in polygons for x, _ in polygon), max(y for polygon in polygons for _, y in polygon))

    def segment(f, a, b):
        return polygons[f][polyhedron.faces[f].index(a)], polygons[f][polyhedron.faces[f].index(b)]

    def bend(f, g):
        return math.acos(max(-1.0, min(1.0, dot(polyhedron.normals[f], polyhedron.normals[g]))))

    folded = {(min(a, b), max(a, b)): (f, g) for g, (f, (a, b)) in parents.items()}
    folds = tuple(Fold((f, g), edge, segment(f, *edge), bend(f, g)) for edge, (f, g) in folded.items())
    across = neighbours(polyhedron)
    cuts = tuple(Cut(across[edge], edge, (segment(across[edge][0], *edge), segment(across[edge][1], *edge)))
                 for edge in polyhedron.edges if edge not in folded)
    return Pattern(polygons, folds, cuts, size, root)
