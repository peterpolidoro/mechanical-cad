"""The flat pattern of a convex polyhedron: its faces laid in one plane, joined along fold lines.

    from mechanical_cad.shapes import polyhedra, unfold

    pattern = unfold.unfold(polyhedra.named("truncated-octahedron", edge=30.0))
    pattern.polygons      # for every face its corners as (x, y), in the face's own order
    pattern.folds         # the edges along which two faces stay joined, each with its segment and its angle
    pattern.cuts          # the other edges: each is on the outline twice, once for each of its two faces
    pattern.size          # (width, height) of the pattern, which lies between (0, 0) and that corner
    unfold.outline(pattern)   # the loops to cut the pattern out along, each by its corners

    tray = unfold.unfold(box, root=bottom, open_faces=[top])     # the same with faces left out: an open shell

The pattern is seen from outside the solid: every face keeps its counter-clockwise order, and every fold bends
the sheet away from the viewer. tools/cut_file.py writes it as a drawing to cut and fold from, for a part that
is a convex solid with flat faces.

Faces can be left out (`open_faces`): what is laid out is then the rest of the surface, a shell that is open
where those faces were, which is what a sheet folds into when it makes a tray or half of an enclosure. An edge
between a face that is kept and one that is left out is cut once and is the rim of the opening. The faces that
are kept have to hang together.

Which edges are folds is a choice: any set of edges that joins all the faces without a ring will do (a spanning
tree of the faces), and some choices lay one face over another. `unfold` tries trees in a fixed order and returns
the first whose faces do not overlap: the tree that reaches the faces breadth-first from the root face, the same
from every other face, then the trees left by cutting, at every vertex, the edge that climbs most steeply
towards one of a fixed list of directions. Overlap is decided exactly for convex polygons: two of them have no
area in common when the line through one side of either has the other polygon on its outer side. A solid for
which none of these trees is free of overlap raises `UnfoldError`. For the eighteen named solids, and for the
prism, the antiprism and the box that tests/test_polyhedra.py tries, the first tree is free of it. With faces
left out the trees are the same with those faces taken away, and one that then no longer joins the rest is
passed over.

Nothing here allows for the thickness of the sheet or the radius of a bend, and no tabs are added to join the
cut edges by.

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
    the pattern on the first face and on the second: the two are joined again when the pattern is folded up.
    Where the second face is left open the edge is on the rim of the opening, and `segments` has the one place
    it lies on the first."""
    faces: tuple
    edge: tuple
    segments: tuple


@dataclass(frozen=True)
class Pattern:
    """A flat pattern. `polygons[i]` is face i of the polyhedron, its corners as (x, y) in the order of the face.
    `root` is the face whose first edge runs along +X. There is one fold fewer than there are faces, and the
    folds are in the order in which the faces were laid: each joins one more face to the root and those before.
    `open_faces` are the faces left out, in order; such a face has no corners here, `polygons[i]` is empty, and
    the folds are one fewer than the faces that are kept."""
    polygons: tuple
    folds: tuple
    cuts: tuple
    size: tuple
    root: int
    open_faces: tuple = ()

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


def breadth_first(polyhedron, start, open_faces=()):
    """The folds of the tree that reaches every face from `start` in the fewest steps, as a set of edges. Faces
    in `open_faces` are neither reached nor passed through; faces that can then not be reached are in no fold."""
    across = neighbours(polyhedron)
    seen, queue, folds = {start, *open_faces}, [start], set()
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


def lay_out(polyhedron, folds, root=0, open_faces=()):
    """Every face in the plane, for a set of fold edges that joins all faces without a ring.

    Returns (polygons, parents): the corners of every face as (x, y), and for every face but the root the face
    it is joined to on the way to the root together with the edge. The root's first corner is at the origin and
    its first edge along +X. A face in `open_faces` is not laid, whatever the folds say: it has no corners, and
    the folds have to join all the others.
    """
    left_out = set(open_faces)
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
            if g in flat or g in left_out or (min(a, b), max(a, b)) not in folds:
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
    if len(flat) != len(faces) - len(left_out):
        raise ValueError("these folds do not join all the faces")
    return [tuple(flat[f][i] for i in faces[f]) if f in flat else () for f in range(len(faces))], parents


def overlapping(polygons, eps):
    """The first two convex polygons, as a pair of indices, that have area in common; None when no two have.

    Polygons run counter-clockwise. Two that share a side or a corner, or lie nearer than `eps`, do not overlap.
    A polygon without corners, a face left out of a pattern, overlaps nothing.
    """
    boxes = [(min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly))
             if poly else None for poly in polygons]

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
            if a is None or b is None:
                continue
            if a[2] <= b[0] + eps or b[2] <= a[0] + eps or a[3] <= b[1] + eps or b[3] <= a[1] + eps:
                continue
            if not apart(polygons[i], polygons[j]) and not apart(polygons[j], polygons[i]):
                return i, j
    return None


def candidates(polyhedron, root=0, open_faces=()):
    """The sets of folds that `unfold` tries, in its order. With `open_faces`, a set of the steepest edges may
    not join the faces that are kept; `unfold` passes over one that does not."""
    yield breadth_first(polyhedron, root, open_faces)
    for start in range(len(polyhedron.faces)):
        if start != root and start not in open_faces:
            yield breadth_first(polyhedron, start, open_faces)
    for direction in directions(STEEPEST_EDGE_DIRECTIONS):
        yield steepest_edge(polyhedron, direction)


def unfold(polyhedron, root=0, open_faces=()):
    """The flat pattern of a convex polyhedron in which no two faces overlap, as a `Pattern`.

    `root` is the face laid first: its first edge runs along +X, and the search for a tree starts from it. The
    pattern is then moved so that it lies between (0, 0) and `size`. Raises `UnfoldError` when none of the
    trees tried is free of overlap.

    `open_faces` are faces to leave out, by their indices: the pattern is that of the shell that is left, open
    where they were. The root is one of the faces that are kept, and those have to hang together: a shell in
    two pieces is no pattern, and raises `UnfoldError`.
    """
    count = len(polyhedron.faces)
    if not 0 <= root < count:
        raise ValueError(f"{polyhedron.name} has no face {root}")
    left_out = frozenset(open_faces)
    if not all(isinstance(f, int) and 0 <= f < count for f in left_out):
        raise ValueError(f"{polyhedron.name} has no faces {sorted(left_out, key=str)} to leave open")
    if root in left_out:
        raise ValueError(f"{polyhedron.name}: face {root} is left open, so it cannot be the face laid first")
    if len(breadth_first(polyhedron, root, left_out)) != count - len(left_out) - 1:
        raise UnfoldError(f"{polyhedron.name}: without the {len(left_out)} faces left open the others do not hang "
                          "together, and no one sheet folds into them")
    eps = TOLERANCE * polyhedron.circumradius
    tried = 0
    for folds in candidates(polyhedron, root, left_out):
        try:
            polygons, parents = lay_out(polyhedron, folds, root, left_out)
        except ValueError:
            continue                                               # steepest edges that do not join the faces kept
        tried += 1
        if overlapping(polygons, eps) is None:
            return _pattern(polyhedron, polygons, parents, root, left_out)
    raise UnfoldError(f"{polyhedron.name}: every one of the {tried} flat patterns tried lays one face over another")


def outline(pattern):
    """The outline of a flat pattern, to cut it out along: the loops its cut edges close into.

    Each loop is a tuple of corners (x, y) in the order of a walk round it. The first is the outside of the
    pattern and runs counter-clockwise; any others are holes in it, places the faces lie around without
    covering, and run clockwise. Every cut edge is on the outline twice, once for each of its two faces, so the
    outline is as long as all the cut edges twice over, and what it encloses is the area of the solid's faces.
    Corners that the two faces of a fold both have are one corner here. Where faces are left open, an edge
    between a face that is kept and one that is not is on the outline once, and what the outline encloses is
    the area of the faces that are kept.

    Raises `UnfoldError` where the cut edges do not close into loops that pass no point twice: two faces that
    are not joined lie side by side or meet in a corner there, or a corner of one lies on a side of another, so
    what would be cut is a slit or two loops that touch, not an outline. Another root may give a pattern
    without that. Cut edges that cross are refused too: faces lie over one another there, which `unfold` does
    not return. The patterns of the eighteen named solids have one loop and no such place, whichever face is
    the root.
    """
    segments = [segment for cut in pattern.cuts for segment in cut.segments]
    near = 1e-7 * max(pattern.size)                                # far above rounding, far below an edge
    corners = []

    def corner(p):
        for k, q in enumerate(corners):
            if abs(p[0] - q[0]) <= near and abs(p[1] - q[1]) <= near:
                return k
        corners.append(p)
        return len(corners) - 1

    ends = [(corner(a), corner(b)) for a, b in segments]
    meeting = {}
    for k, (a, b) in enumerate(ends):
        meeting.setdefault(a, []).append(k)
        meeting.setdefault(b, []).append(k)
    for k, there in meeting.items():
        if len(there) != 2:
            x, y = corners[k]
            raise UnfoldError(f"{len(there)} cut edges of the pattern end at ({x:.6g}, {y:.6g}), not two: faces that "
                              "are not joined meet there, and the cut edges are no outline. Try another root")
    loops, walked = [], set()
    for start in range(len(ends)):
        if start in walked:
            continue
        loop, k, here = [], start, ends[start][0]
        while k not in walked:
            walked.add(k)
            loop.append(corners[here])
            here = ends[k][1] if here == ends[k][0] else ends[k][0]
            k = next((other for other in meeting[here] if other != k), k)
        if len(loop) < 3 or abs(polygon_area(loop)) <= near * max(pattern.size):
            x, y = loop[0]
            raise UnfoldError(f"two faces of the pattern that are not joined lie side by side at ({x:.6g}, {y:.6g}): "
                              "the cut between them is a slit, not an outline. Try another root")
        loops.append(tuple(loop))
    # Two cut edges end at every corner now. A point is still passed twice where a corner lies on a cut edge that
    # does not end there, or where two cut edges cross.
    sides = [(corners[a], corners[b]) for a, b in ends]
    boxes = [(min(p[0], q[0]) - near, min(p[1], q[1]) - near, max(p[0], q[0]) + near, max(p[1], q[1]) + near)
             for p, q in sides]

    def left_of(p, q, r):                                          # twice the area of the triangle p, q, r
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    for (a, b), (p, q), box in zip(ends, sides, boxes):
        reach = near * math.dist(p, q)
        for c, r in enumerate(corners):
            if (box[0] <= r[0] <= box[2] and box[1] <= r[1] <= box[3] and c != a and c != b
                    and abs(left_of(p, q, r)) <= reach):
                raise UnfoldError(f"a corner of the pattern at ({r[0]:.6g}, {r[1]:.6g}) lies on a cut edge that does not "
                                  "end there: faces that are not joined touch there, and the cut edges are no "
                                  "outline. Try another root")
    for k, ((p, q), one) in enumerate(zip(sides, boxes)):
        for (r, s), other in zip(sides[k + 1:], boxes[k + 1:]):
            if one[2] < other[0] or other[2] < one[0] or one[3] < other[1] or other[3] < one[1]:
                continue
            here, there = left_of(r, s, p), left_of(r, s, q)
            if here * there < 0.0 and left_of(p, q, r) * left_of(p, q, s) < 0.0:
                t = here / (here - there)
                raise UnfoldError(f"two cut edges of the pattern cross at ({p[0] + t * (q[0] - p[0]):.6g}, "
                                  f"{p[1] + t * (q[1] - p[1]):.6g}): faces lie over one another there")
    loops.sort(key=lambda loop: -abs(polygon_area(loop)))
    return tuple(loop if (polygon_area(loop) > 0.0) == (k == 0) else loop[::-1] for k, loop in enumerate(loops))


def _pattern(polyhedron, polygons, parents, root, left_out=frozenset()):
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
    cuts = []
    for edge in polyhedron.edges:
        kept = tuple(f for f in across[edge] if f not in left_out)
        if edge in folded or not kept:                             # an edge between two faces left open is nowhere
            continue
        faces = kept + tuple(f for f in across[edge] if f in left_out)
        cuts.append(Cut(faces, edge, tuple(segment(f, *edge) for f in kept)))
    return Pattern(polygons, folds, tuple(cuts), size, root, tuple(sorted(left_out)))
