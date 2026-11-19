"""Convex polyhedra by their vertices: the Platonic and Archimedean solids, prisms, antiprisms and boxes.

A `Polyhedron` is a name, the vertices as (x, y, z) tuples and the faces as
tuples of vertex indices, counter-clockwise seen from outside. Everything
else is derived from those: edges, face normals and distances, volume, area
and the three radii. A polyhedron is never changed; `scaled`, `with_edge`,
`rotated`, `translated`, `mirrored` and `resting_on` return new ones with the
same faces under the same indices. `inset` and `panel` return other
polyhedra: the cavity behind a wall, and the plate of one face.

    from mechanical_cad.shapes import polyhedra

    p = polyhedra.named("truncated-octahedron", edge=30.0)
    p = p.resting_on(p.faces_with(6)[0])                  # a hexagon in z = 0, the solid above it
    factor = p.scale_to_hold_box((50, 40, 10), wall=3, clearance=2, offset=(0, 0, 18))

The coordinates of the named solids are the published closed forms: changes
of sign and permutations of a few numbers built from sqrt(2), the golden
ratio, the tribonacci constant (snub cube) and the real root of
x^3 - 2x = golden ratio (snub dodecahedron). They are evaluated in floating
point here and nothing is copied as a rounded decimal. The faces are not
tabulated: they are the convex hull of the vertices, found by `hull`. Each
solid is then scaled to the edge asked for by its own measured edge.
tests/test_polyhedra.py holds every solid to what is known of it.

The two snubs come in a left and a right form. `named` gives the one its
coordinates here produce; `mirrored()` gives the other.

The solids of one family are placed alike, so that every rotation that lays
one of them on itself does so for all: the tetrahedron and the truncated
tetrahedron with their three-fold axes along (1, 1, 1) and its like; the
cube's family with the four-fold axes along X, Y and Z; the icosahedron's
family with two-fold axes along X, Y and Z and a five-fold axis along
(1, 0, golden ratio).

Lengths have no unit here. A part's program uses millimetres.

Standard library only: nothing here needs a CAD kernel.
mechanical_cad/shapes/forms.py makes solids, shells, frames and panels of a
polyhedron with build123d, and mechanical_cad/shapes/unfold.py its flat
pattern.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from functools import cached_property, lru_cache

# Two numbers are taken as equal when they differ by less than this fraction of the size of the shape.
TOLERANCE = 1e-9

PHI = (1.0 + math.sqrt(5.0)) / 2.0
SQRT2 = math.sqrt(2.0)


def _newton(x, f, df):
    """One Newton step: it removes what the roots of a closed form lost in rounding."""
    return x - f(x) / df(x)


# The tribonacci constant, the real root of t^3 = t^2 + t + 1.
TRIBONACCI = _newton((1.0 + math.cbrt(19.0 + 3.0 * math.sqrt(33.0)) + math.cbrt(19.0 - 3.0 * math.sqrt(33.0))) / 3.0,
                     lambda t: t ** 3 - t ** 2 - t - 1.0, lambda t: 3.0 * t ** 2 - 2.0 * t - 1.0)
# The real root of x^3 - 2x = PHI, by Cardano's formula.
SNUB_DODECAHEDRON_ROOT = _newton(math.cbrt((PHI + math.sqrt(PHI - 5.0 / 27.0)) / 2.0)
                                 + math.cbrt((PHI - math.sqrt(PHI - 5.0 / 27.0)) / 2.0),
                                 lambda x: x ** 3 - 2.0 * x - PHI, lambda x: 3.0 * x ** 2 - 2.0)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def times(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    return times(a, 1.0 / norm(a))


def mean(points):
    return times(tuple(map(math.fsum, zip(*points))), 1.0 / len(points))


def _area_vector(points):
    """The sum of the cross products of a fan over a polygon: its length is twice the area, its direction the
    normal about which the polygon runs counter-clockwise."""
    total = (0.0, 0.0, 0.0)
    for k in range(1, len(points) - 1):
        total = add(total, cross(sub(points[k], points[0]), sub(points[k + 1], points[0])))
    return total


# ---- the convex hull --------------------------------------------------------------------------------------------

def _corners(flat, eps):
    """The corners of the convex hull of 2D points, counter-clockwise, as indices into `flat`.

    A point within `eps` of the line through its two neighbours is not a corner.
    """
    order = sorted(range(len(flat)), key=lambda i: flat[i])

    def chain(indices):
        out = []
        for i in indices:
            while len(out) >= 2:
                o, a, p = flat[out[-2]], flat[out[-1]], flat[i]
                turn = (a[0] - o[0]) * (p[1] - o[1]) - (a[1] - o[1]) * (p[0] - o[0])
                if turn > eps * math.hypot(p[0] - o[0], p[1] - o[1]):
                    break
                out.pop()
            out.append(i)
        return out

    lower, upper = chain(order), chain(reversed(order))
    return lower[:-1] + upper[:-1]


def hull(points, tolerance=TOLERANCE):
    """The faces of the convex hull of `points`, each a tuple of indices, counter-clockwise seen from outside.

    A point inside the hull, inside a face or inside an edge is in no face. The method is gift wrapping: a plane
    through an edge of a known face is turned about that edge until it meets another point, which gives the face
    on the other side of the edge; the points are gone through a few times for each edge. Points nearer a plane
    than `tolerance` times the size of the set are taken to lie in it, so a face may have any number of corners.
    """
    count = len(points)
    if count < 4:
        raise ValueError("a polyhedron needs at least four points")
    centre = mean(points)
    eps = tolerance * max(norm(sub(p, centre)) for p in points)
    if eps == 0.0:
        raise ValueError("the points are all the same point")

    def in_plane(a, m):
        return [i for i in range(count) if abs(dot(m, sub(points[i], a))) <= eps]

    def face_about(a, u):
        """The corners of the hull's face, or edge, in the plane that holds the line through `a` along `u` and has
        every point on one side, the first such plane met when turning about the line."""
        m = None
        for v in points:
            w = sub(v, a)
            if m is None or dot(m, w) > eps:
                k = cross(w, u)
                if norm(k) > eps:                                  # a point on the line itself does not fix a plane
                    m = unit(k)
        if m is None:
            raise ValueError("the points all lie on one line")
        # fix the plane by the point in it that is farthest from the line, then by the whole outline
        far = max(in_plane(a, m), key=lambda i: norm(cross(sub(points[i], a), u)))
        k = unit(cross(sub(points[far], a), u))
        m = k if dot(k, m) > 0.0 else times(k, -1.0)               # that point may lie across the line
        for _ in range(2):
            on = in_plane(a, m)
            v = cross(m, u)                                        # u, v, m: right-handed, so u-v is seen from outside
            flat = [(dot(sub(points[i], a), u), dot(sub(points[i], a), v)) for i in on]
            corners = [on[i] for i in _corners(flat, eps)]
            if len(corners) < 3:
                return tuple(corners)
            m = unit(_area_vector([points[i] for i in corners]))
            a = mean([points[i] for i in corners])
        if max(dot(m, sub(p, a)) for p in points) > 4.0 * eps:
            raise ValueError("no plane through these points has the rest on one side; are two points nearly the same?")
        return tuple(corners)

    # A first face: no point is higher than the last one in the order (z, y, x), and none at its height is
    # farther along y, so a plane turned about the line through it along x meets the hull in an edge or a face.
    start = points[max(range(count), key=lambda i: (points[i][2], points[i][1], points[i][0]))]
    first = face_about(start, (1.0, 0.0, 0.0))
    if len(first) == 2:
        first = face_about(points[first[0]], unit(sub(points[first[1]], points[first[0]])))
    if len(first) < 3 or len(in_plane(points[first[0]], unit(_area_vector([points[i] for i in first])))) == count:
        raise ValueError("the points all lie in one plane")

    faces, sides, queue = [], set(), [first]
    sides.update(zip(first, first[1:] + first[:1]))
    while queue:
        face = queue.pop()
        faces.append(face)
        for a, b in zip(face, face[1:] + face[:1]):
            if (b, a) in sides:
                continue
            other = face_about(points[a], unit(sub(points[b], points[a])))
            edges = set(zip(other, other[1:] + other[:1]))
            if len(other) < 3 or (b, a) not in edges or edges & sides:
                raise ValueError("the faces found do not close; are two points nearly the same?")
            sides.update(edges)
            queue.append(other)
    used = {i for face in faces for i in face}
    if len(used) - len(sides) // 2 + len(faces) != 2:
        raise ValueError("the faces found do not make a closed surface")
    return faces


def _ordered(faces):
    """Faces in a fixed order: each begins with its lowest vertex, and the list is sorted."""
    return tuple(sorted(face[face.index(min(face)):] + face[:face.index(min(face))] for face in map(tuple, faces)))


def from_vertices(name, vertices):
    """The convex polyhedron with these corners. A point that is not a corner of their hull is refused."""
    points = tuple(tuple(float(c) + 0.0 for c in v) for v in vertices)
    faces = hull(points)
    unused = sorted(set(range(len(points))) - {i for face in faces for i in face})
    if unused:
        raise ValueError(f"{name}: points {unused} are not corners of the convex hull of the points given")
    return Polyhedron(name, points, _ordered(faces))


def intersection(name, half_spaces, inside):
    """The polyhedron of the points x with a . x <= b for every (a, b) of `half_spaces`.

    `inside` is a point strictly inside all of them. The half-spaces must bound a region on every side. A
    half-space that only touches the region, or misses it, gives no face.

    Seen from `inside`, each plane a . x = b is the point a / b of a dual space, and each corner of the region
    is a face of the hull of those points: so one hull finds the corners and a second the faces.
    """
    dual = []
    for a, b in half_spaces:
        room = b - dot(a, inside)
        if room <= 0.0:
            raise ValueError(f"{name}: the point given as inside is not inside every half-space")
        dual.append(times(a, 1.0 / room))
    corners = []
    for face in hull(dual):
        m = unit(_area_vector([dual[i] for i in face]))
        corners.append(add(inside, times(m, 1.0 / (math.fsum(dot(m, dual[i]) for i in face) / len(face)))))
    eps = TOLERANCE * max(norm(sub(c, inside)) for c in corners)
    distinct = []
    for c in corners:
        if all(norm(sub(c, d)) > eps for d in distinct):
            distinct.append(c)
    return from_vertices(name, distinct)


# ---- the polyhedron ---------------------------------------------------------------------------------------------

@dataclass(frozen=True, repr=False)
class Polyhedron:
    """A convex polyhedron: `vertices` as (x, y, z) tuples, `faces` as tuples of vertex indices, counter-clockwise
    seen from outside. The solids made by this module are centred on the origin until they are moved."""
    name: str
    vertices: tuple
    faces: tuple

    def __repr__(self):
        return "Polyhedron({!r}: {} vertices, {} edges, {} faces)".format(self.name, *self.counts)

    # -- derived

    @cached_property
    def edges(self):
        """Every edge once, as a pair of vertex indices, the lower first, sorted."""
        return tuple(sorted({(min(a, b), max(a, b)) for face in self.faces for a, b in zip(face, face[1:] + face[:1])}))

    @property
    def counts(self):
        """(vertices, edges, faces)."""
        return len(self.vertices), len(self.edges), len(self.faces)

    def polygon(self, face):
        """The corners of a face as points, in the face's order."""
        return tuple(self.vertices[i] for i in self.faces[face])

    @cached_property
    def normals(self):
        """The outward unit normal of every face."""
        return tuple(unit(_area_vector(self.polygon(f))) for f in range(len(self.faces)))

    @cached_property
    def distances(self):
        """For every face, the distance of its plane from the origin along its normal: n . x = distance on the face.
        Negative when the origin is outside that face."""
        return tuple(math.fsum(dot(n, v) for v in self.polygon(f)) / len(self.faces[f]) for f, n in enumerate(self.normals))

    @cached_property
    def face_areas(self):
        return tuple(norm(_area_vector(self.polygon(f))) / 2.0 for f in range(len(self.faces)))

    @cached_property
    def face_centres(self):
        """The mean of the corners of every face."""
        return tuple(mean(self.polygon(f)) for f in range(len(self.faces)))

    @cached_property
    def edge_lengths(self):
        """The length of every edge, in the order of `edges`."""
        return tuple(norm(sub(self.vertices[a], self.vertices[b])) for a, b in self.edges)

    @property
    def edge_length(self):
        """The one length all edges have. A polyhedron whose edges differ has none, and asking is an error."""
        low, high = min(self.edge_lengths), max(self.edge_lengths)
        if high - low > TOLERANCE * high:
            raise ValueError(f"{self.name}: its edges are not of one length ({low:.9g} to {high:.9g})")
        return math.fsum(self.edge_lengths) / len(self.edge_lengths)

    @cached_property
    def centre(self):
        """The mean of the vertices. For the solids of this module it is the centre of symmetry."""
        return mean(self.vertices)

    @cached_property
    def volume(self):
        c = self.centre
        return math.fsum(dot(sub(p[0], c), cross(sub(p[k], c), sub(p[k + 1], c)))
                         for p in map(self.polygon, range(len(self.faces))) for k in range(1, len(p) - 1)) / 6.0

    @cached_property
    def area(self):
        return math.fsum(self.face_areas)

    @cached_property
    def circumradius(self):
        """The distance from the centre to the farthest vertex. On a uniform solid every vertex is that far."""
        return max(norm(sub(v, self.centre)) for v in self.vertices)

    @cached_property
    def inradius(self):
        """The distance from the centre to the nearest face: the radius of the largest ball about the centre."""
        return min(d - dot(n, self.centre) for n, d in zip(self.normals, self.distances))

    @cached_property
    def midradius(self):
        """The distance from the centre to the nearest edge. On a uniform solid every edge is that far."""
        def to_edge(a, b):
            along = sub(b, a)
            t = min(1.0, max(0.0, dot(sub(self.centre, a), along) / dot(along, along)))
            return norm(sub(self.centre, add(a, times(along, t))))
        return min(to_edge(self.vertices[a], self.vertices[b]) for a, b in self.edges)

    def faces_with(self, sides):
        """The indices of the faces that have that many sides."""
        return tuple(f for f, face in enumerate(self.faces) if len(face) == sides)

    def face_towards(self, direction):
        """The index of the face whose outward normal is nearest to `direction`; the lowest index of several."""
        d = unit(direction)
        return max(range(len(self.faces)), key=lambda f: (round(dot(self.normals[f], d), 9), -f))

    # -- the same solid, somewhere else or of another size

    def _with(self, vertices, faces=None):
        return Polyhedron(self.name, tuple(vertices), self.faces if faces is None else faces)

    def scaled(self, factor):
        """Every coordinate times `factor`: the solid grows or shrinks about the origin."""
        if not factor > 0.0:
            raise ValueError(f"a scale factor is positive, not {factor!r}")
        return self._with(times(v, factor) for v in self.vertices)

    def with_edge(self, length):
        """Scaled so that every edge has that length. Only for a solid whose edges are of one length."""
        return self.scaled(length / self.edge_length)

    def translated(self, offset):
        return self._with(add(v, offset) for v in self.vertices)

    def rotated(self, matrix):
        """Turned about the origin by a 3 x 3 rotation matrix, given as rows and applied to column vectors.
        A matrix that is not a rotation (a mirror, a scale, a shear) is refused."""
        rows = [tuple(float(c) for c in row) for row in matrix]
        if len(rows) != 3 or any(len(row) != 3 for row in rows):
            raise ValueError("expected a 3 x 3 matrix")
        if any(abs(dot(rows[i], rows[j]) - (i == j)) > 1e-9 for i in range(3) for j in range(3)):
            raise ValueError("the matrix is not orthonormal")
        if dot(rows[0], cross(rows[1], rows[2])) < 0.0:
            raise ValueError("the matrix is a mirror, not a rotation; use mirrored()")
        return self._with((dot(rows[0], v), dot(rows[1], v), dot(rows[2], v)) for v in self.vertices)

    def mirrored(self):
        """The mirror image in the plane x = 0. Face i is the image of face i, and still runs counter-clockwise
        seen from outside. For the two snubs this is the other form; the other named solids come out as
        themselves, the tetrahedron and the truncated tetrahedron turned a quarter about Z."""
        return self._with(((-v[0] + 0.0, v[1], v[2]) for v in self.vertices),
                          tuple(face[:1] + face[:0:-1] for face in self.faces))

    def resting_on(self, face, edge=0):
        """Turned and moved so that it rests on a face: the face lies in z = 0 with its outward normal along -Z,
        the edge from its corner number `edge` to the next runs along +X, the rest of the solid is above, and
        the centre is on the Z axis."""
        corners = self.polygon(face)
        x = unit(sub(corners[(edge + 1) % len(corners)], corners[edge]))
        z = times(self.normals[face], -1.0)
        y = cross(z, x)
        height = self.distances[face] - dot(self.normals[face], self.centre)
        moved = []
        for v in self.vertices:
            w = sub(v, self.centre)
            moved.append((dot(x, w), dot(y, w), dot(z, w) + height))
        return self._with(moved)

    # -- sizing

    def scale_to_hold_box(self, half_extents, wall=0.0, clearance=0.0, offset=(0.0, 0.0, 0.0)):
        """The smallest factor for `scaled` at which this solid, every face then moved inward by `wall`, holds a box.

        The box has its sides along the axes and its centre at `offset`; it reaches `half_extents` plus
        `clearance` from there along X, Y and Z. `wall`, `clearance` and `offset` are lengths of the scaled
        solid: they are not scaled. At the factor returned at least one corner of the box touches a moved face.

        The solid is scaled about the origin, which has to be inside it or on its surface. A solid centred on the
        origin grows about its centre. One that rests on z = 0 (`resting_on`) keeps its bottom face there, and
        then the box has to clear that face by `wall` whatever the factor: the offset of a board on standoffs.

        The factor is the largest, over the faces, of (reach of the box along the face's normal + wall) / (distance
        of the face from the origin): nothing is searched.
        """
        if min(half_extents) < 0.0 or wall < 0.0 or clearance < 0.0:
            raise ValueError("half extents, wall and clearance cannot be negative")
        half = tuple(h + clearance for h in half_extents)
        flat = TOLERANCE * self.circumradius
        factor = 0.0
        for f, (n, d) in enumerate(zip(self.normals, self.distances)):
            reach = dot(n, offset) + abs(n[0]) * half[0] + abs(n[1]) * half[1] + abs(n[2]) * half[2] + wall
            if d < -flat:
                raise ValueError(f"{self.name}: the origin is outside face {f}; move the solid over the origin first")
            if d <= flat:                                          # a face through the origin stays where it is
                if reach > flat:
                    raise ValueError(f"{self.name}: face {f} passes through the origin and does not move with the "
                                     f"scale; the box and the wall reach {reach:.6g} beyond it")
            else:
                factor = max(factor, reach / d)
        if factor <= 0.0:
            raise ValueError("the box and the wall have no size")
        return factor

    # -- parts of the solid, as polyhedra

    def inset(self, wall):
        """The polyhedron left when every face is moved inward by `wall`: the cavity of a shell with that wall.

        It is not a scaled copy unless every face is equally far from the centre. A face may vanish and the
        corners may be other than the solid's. `wall` has to be less than `inradius`.
        """
        if not 0.0 < wall < self.inradius:
            raise ValueError(f"{self.name}: the wall has to be more than 0 and less than the inradius "
                             f"{self.inradius:.6g}, not {wall!r}")
        return intersection(self.name, [(n, d - wall) for n, d in zip(self.normals, self.distances)], self.centre)

    def panel(self, face, thickness):
        """The plate of a face: the points of the solid within `thickness` of that face's plane and no nearer to
        the plane of any other face.

        Its sides are the planes that halve the angle to the neighbouring faces, so the plates of neighbours meet
        in a mitre. The plates of all faces fill the solid outside `inset(thickness)` and share only their sides.
        """
        if not thickness > 0.0:
            raise ValueError(f"a panel's thickness is positive, not {thickness!r}")
        n, d, c = self.normals[face], self.distances[face], self.face_centres[face]
        others = [(m, e) for g, (m, e) in enumerate(zip(self.normals, self.distances)) if g != face]
        # The plate is inside the straight prism under its face: the point of the surface nearest to a point of
        # the plate is straight above it. Another face can only bound the plate if some point of that prism is
        # as near to it as to this face, which need only be asked at the prism's lower corners.
        corners, slack = self.polygon(face), TOLERANCE * self.circumradius
        near = [(m, e) for m, e in others
                if min(e - dot(m, v) for v in corners) <= thickness * (1.0 - dot(m, n)) + slack]
        # a point under the middle of the face, nearer to this face than to any other
        depth = min([thickness] + [(e - dot(m, c)) / 2.0 for m, e in others]) / 2.0
        planes = [(n, d), (times(n, -1.0), thickness - d)] + [(sub(m, n), e - d) for m, e in near]
        return intersection(f"{self.name}-panel-{face}", planes, sub(c, times(n, depth)))

    def panels(self, thickness):
        """`panel` for every face, in the order of the faces."""
        return tuple(self.panel(f, thickness) for f in range(len(self.faces)))


# ---- the named solids -------------------------------------------------------------------------------------------

EVEN = ((0, 1, 2), (1, 2, 0), (2, 0, 1))
ODD = ((0, 2, 1), (2, 1, 0), (1, 0, 2))


def _images(seeds, keep):
    """The seed points under permutations of the coordinates and changes of sign.

    `keep(odd, minus)` says which are taken: `odd` is whether the permutation is odd, `minus` how many of the
    three signs are changed.
    """
    points = set()
    for seed in seeds:
        for odd, permutations in ((False, EVEN), (True, ODD)):
            for permutation in permutations:
                for signs in itertools.product((1.0, -1.0), repeat=3):
                    if keep(odd, signs.count(-1.0)):
                        points.add(tuple(seed[permutation[c]] * signs[c] + 0.0 for c in range(3)))
    return sorted(points)


def _all(seeds):
    return _images(seeds, lambda odd, minus: True)


def _even(seeds):
    return _images(seeds, lambda odd, minus: not odd)


def _odd(seeds):
    return _images(seeds, lambda odd, minus: odd)


def _snub_dodecahedron():
    x = SNUB_DODECAHEDRON_ROOT
    a, b = x - 1.0 / x, x * PHI + PHI ** 2 + PHI / x
    return _images([(2.0 * a, 2.0, 2.0 * b),
                    (a + b / PHI + PHI, -a * PHI + b + 1.0 / PHI, a / PHI + b * PHI - 1.0),
                    (a + b / PHI - PHI, a * PHI - b + 1.0 / PHI, a / PHI + b * PHI + 1.0),
                    (-a / PHI + b * PHI + 1.0, -a + b / PHI - PHI, a * PHI + b - 1.0 / PHI),
                    (-a / PHI + b * PHI - 1.0, a - b / PHI - PHI, a * PHI + b + 1.0 / PHI)],
                   lambda odd, minus: not odd and minus % 2 == 1)


# Each solid by the points that are its vertices, at whatever size the closed form has. The icosahedron and the
# truncated icosahedron are usually given by the even permutations of these numbers; the odd ones are the same two
# solids turned a quarter about Z, which is how they share their axes with the other six of their family.
_VERTICES = {
    "tetrahedron": lambda: _images([(1.0, 1.0, 1.0)], lambda odd, minus: minus % 2 == 0),
    "cube": lambda: _all([(1.0, 1.0, 1.0)]),
    "octahedron": lambda: _all([(1.0, 0.0, 0.0)]),
    "dodecahedron": lambda: _all([(1.0, 1.0, 1.0)]) + _even([(0.0, 1.0 / PHI, PHI)]),
    "icosahedron": lambda: _odd([(0.0, 1.0, PHI)]),
    "truncated-tetrahedron": lambda: _images([(1.0, 1.0, 3.0)], lambda odd, minus: minus % 2 == 0),
    "cuboctahedron": lambda: _all([(1.0, 1.0, 0.0)]),
    "truncated-cube": lambda: _all([(SQRT2 - 1.0, 1.0, 1.0)]),
    "truncated-octahedron": lambda: _all([(0.0, 1.0, 2.0)]),
    "rhombicuboctahedron": lambda: _all([(1.0, 1.0, 1.0 + SQRT2)]),
    "truncated-cuboctahedron": lambda: _all([(1.0, 1.0 + SQRT2, 1.0 + 2.0 * SQRT2)]),
    "snub-cube": lambda: _images([(1.0, 1.0 / TRIBONACCI, TRIBONACCI)], lambda odd, minus: odd == (minus % 2 == 0)),
    "icosidodecahedron": lambda: _even([(0.0, 0.0, PHI), (0.5, PHI / 2.0, PHI ** 2 / 2.0)]),
    "truncated-dodecahedron": lambda: _even([(0.0, 1.0 / PHI, 2.0 + PHI), (1.0 / PHI, PHI, 2.0 * PHI),
                                             (PHI, 2.0, PHI + 1.0)]),
    "truncated-icosahedron": lambda: _odd([(0.0, 1.0, 3.0 * PHI), (1.0, 2.0 + PHI, 2.0 * PHI),
                                           (PHI, 2.0, 2.0 * PHI + 1.0)]),
    "rhombicosidodecahedron": lambda: _even([(1.0, 1.0, PHI ** 3), (PHI ** 2, PHI, 2.0 * PHI),
                                             (2.0 + PHI, 0.0, PHI ** 2)]),
    "truncated-icosidodecahedron": lambda: _even([(1.0 / PHI, 1.0 / PHI, 3.0 + PHI),
                                                  (2.0 / PHI, PHI, 1.0 + 2.0 * PHI),
                                                  (1.0 / PHI, PHI ** 2, 3.0 * PHI - 1.0),
                                                  (2.0 * PHI - 1.0, 2.0, 2.0 + PHI),
                                                  (PHI, 3.0, 2.0 * PHI)]),
    "snub-dodecahedron": _snub_dodecahedron,
}
PLATONIC = ("tetrahedron", "cube", "octahedron", "dodecahedron", "icosahedron")
ARCHIMEDEAN = tuple(name for name in _VERTICES if name not in PLATONIC)
NAMES = PLATONIC + ARCHIMEDEAN


@lru_cache(maxsize=None)
def _unit(name):
    solid = from_vertices(name, _VERTICES[name]())
    return solid.scaled(1.0 / solid.edge_length)


def named(name, edge=1.0):
    """A Platonic or Archimedean solid by its name (`NAMES`), centred on the origin, every edge `edge` long.

    A name may be written with spaces or underscores for the hyphens, and in any case.
    """
    key = str(name).strip().lower().replace(" ", "-").replace("_", "-")
    if key not in _VERTICES:
        raise ValueError(f"no solid named {name!r}; known: {', '.join(NAMES)}")
    return _unit(key).scaled(edge)


def _ring(n, radius, z, turn=0.0):
    """A regular n-gon about the Z axis at height z; without `turn` its lowest side (least y) is parallel to X."""
    start = -math.pi / 2.0 + math.pi / n + turn
    return [(radius * math.cos(start + 2.0 * math.pi * k / n), radius * math.sin(start + 2.0 * math.pi * k / n), z)
            for k in range(n)]


def prism(n, edge=1.0, height=None):
    """A right prism on a regular n-gon of side `edge`, its axis along Z, centred on the origin. Without a
    `height` it is as high as its edge, so that its sides are squares."""
    if n < 3 or not edge > 0.0 or (height is not None and not height > 0.0):
        raise ValueError("a prism needs at least three sides, a positive edge and a positive height")
    radius, half = edge / (2.0 * math.sin(math.pi / n)), (edge if height is None else height) / 2.0
    return from_vertices(f"prism-{n}", _ring(n, radius, -half) + _ring(n, radius, half))


def prism_on(corners, height, name=None):
    """A right prism on any convex polygon: `corners` are the polygon's corners as (x, y), in either direction;
    its axis is along Z and it lies between z = -height / 2 and height / 2, where the corners are. A point that
    is not a corner of the polygon, one inside it or on one of its sides, is refused."""
    corners = [(float(x), float(y)) for x, y in corners]
    if len(corners) < 3 or not height > 0.0:
        raise ValueError("a prism needs at least three corners and a positive height")
    half = height / 2.0
    return from_vertices(name or f"prism-on-{len(corners)}",
                         [(x, y, -half) for x, y in corners] + [(x, y, half) for x, y in corners])


def antiprism(n, edge=1.0):
    """An antiprism on two regular n-gons of side `edge`, one turned half a step against the other, joined by
    2n equilateral triangles. Its axis is along Z and it is centred on the origin."""
    if n < 3 or not edge > 0.0:
        raise ValueError("an antiprism needs at least three sides and a positive edge")
    radius = edge / (2.0 * math.sin(math.pi / n))
    half = edge * math.sqrt(1.0 - 1.0 / (4.0 * math.cos(math.pi / (2.0 * n)) ** 2)) / 2.0
    return from_vertices(f"antiprism-{n}", _ring(n, radius, -half) + _ring(n, radius, half, math.pi / n))


def box(x, y, z):
    """A box of those three sizes along X, Y and Z, centred on the origin."""
    if not (x > 0.0 and y > 0.0 and z > 0.0):
        raise ValueError("the three sizes of a box are positive")
    return from_vertices("box", [(sx * x / 2.0, sy * y / 2.0, sz * z / 2.0)
                                 for sx in (-1.0, 1.0) for sy in (-1.0, 1.0) for sz in (-1.0, 1.0)])
