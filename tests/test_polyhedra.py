"""The polyhedra of mechanical_cad/shapes held to what is known of each; no kernel needed.

What is known of a solid is written here independently of the library: its numbers of vertices, edges and
faces, the faces around a vertex, and the closed form of its volume for a unit edge as the literature gives it.
The closed forms were written down here without a source at hand, so the circumradius and the volume are also
worked out a second way, from the faces around a vertex alone, with no coordinates and none of those formulas
(`from_the_vertex`); the two agree for all eighteen.
"""
import math
from collections import Counter
from itertools import combinations

import pytest

from mechanical_cad.shapes import forms, polyhedra, unfold
from mechanical_cad.shapes.polyhedra import add, cross, dot, norm, sub, times, unit

REL = 1e-9
PHI = (1 + math.sqrt(5)) / 2
R2, R5 = math.sqrt(2), math.sqrt(5)


def root(f, low, high):
    """The zero of a rising function between two bounds, by halving: nothing here is taken from the library."""
    for _ in range(200):
        mid = (low + high) / 2
        low, high = (low, mid) if f(mid) > 0 else (mid, high)
    return (low + high) / 2


T = root(lambda t: t ** 3 - t ** 2 - t - 1, 1, 2)                 # the tribonacci constant
XI = root(lambda x: x ** 3 - 2 * x - PHI, 1, 2)

# name: vertices, edges, faces, how many faces of how many sides, the faces around a vertex, volume for edge 1
KNOWN = {
    "tetrahedron": (4, 6, 4, {3: 4}, (3, 3, 3), R2 / 12),
    "cube": (8, 12, 6, {4: 6}, (4, 4, 4), 1.0),
    "octahedron": (6, 12, 8, {3: 8}, (3, 3, 3, 3), R2 / 3),
    "dodecahedron": (20, 30, 12, {5: 12}, (5, 5, 5), (15 + 7 * R5) / 4),
    "icosahedron": (12, 30, 20, {3: 20}, (3, 3, 3, 3, 3), 5 * (3 + R5) / 12),
    "truncated-tetrahedron": (12, 18, 8, {3: 4, 6: 4}, (3, 6, 6), 23 * R2 / 12),
    "cuboctahedron": (12, 24, 14, {3: 8, 4: 6}, (3, 4, 3, 4), 5 * R2 / 3),
    "truncated-cube": (24, 36, 14, {3: 8, 8: 6}, (3, 8, 8), (21 + 14 * R2) / 3),
    "truncated-octahedron": (24, 36, 14, {4: 6, 6: 8}, (4, 6, 6), 8 * R2),
    "rhombicuboctahedron": (24, 48, 26, {3: 8, 4: 18}, (3, 4, 4, 4), (12 + 10 * R2) / 3),
    "truncated-cuboctahedron": (48, 72, 26, {4: 12, 6: 8, 8: 6}, (4, 6, 8), 22 + 14 * R2),
    "snub-cube": (24, 60, 38, {3: 32, 4: 6}, (3, 3, 3, 3, 4), (8 * T + 6) / (3 * math.sqrt(2 * (T * T - 3)))),
    "icosidodecahedron": (30, 60, 32, {3: 20, 5: 12}, (3, 5, 3, 5), (45 + 17 * R5) / 6),
    "truncated-dodecahedron": (60, 90, 32, {3: 20, 10: 12}, (3, 10, 10), 5 * (99 + 47 * R5) / 12),
    "truncated-icosahedron": (60, 90, 32, {5: 12, 6: 20}, (5, 6, 6), (125 + 43 * R5) / 4),
    "rhombicosidodecahedron": (60, 120, 62, {3: 20, 4: 30, 5: 12}, (3, 4, 5, 4), (60 + 29 * R5) / 3),
    "truncated-icosidodecahedron": (120, 180, 62, {4: 30, 6: 20, 10: 12}, (4, 6, 10), 95 + 50 * R5),
    "snub-dodecahedron": (60, 150, 92, {3: 80, 5: 12}, (3, 3, 3, 3, 5),
                          (12 * XI ** 2 * (3 * PHI + 1) - XI * (36 * PHI + 7) - (53 * PHI + 6)) / (6 * (3 - XI ** 2) ** 1.5)),
}
# and beside the named solids, shapes whose edges and faces are not all alike
OTHERS = [polyhedra.prism(6), polyhedra.prism(5, 2.0, 7.0), polyhedra.antiprism(5), polyhedra.box(100.0, 80.0, 20.0)]
SHAPES = [polyhedra.named(name) for name in polyhedra.NAMES] + OTHERS

named = pytest.mark.parametrize("name", polyhedra.NAMES)
every = pytest.mark.parametrize("p", SHAPES, ids=[p.name for p in SHAPES])


def regular_area(sides):
    """The area of a regular polygon of side 1."""
    return sides / (4 * math.tan(math.pi / sides))


def from_the_vertex(around, faces):
    """(circumradius, volume) of the solid of edge 1 that has these faces around every vertex.

    The neighbours of a vertex are 1 away from it and on the sphere, so they lie on a circle; two that follow
    each other are the ends of a chord across a face of n sides, 2 cos(pi / n) long. The circle is the one on
    which those chords close up, and its radius gives the sphere's. A face is then at the distance from the
    centre that its own circumcircle leaves, which gives the volume as a sum of pyramids.
    """
    half_chords = [math.cos(math.pi / n) for n in around]
    circle = root(lambda r: math.pi - sum(math.asin(c / r) for c in half_chords), max(half_chords), 1.0)
    radius = 1 / (2 * math.sqrt(1 - circle ** 2))
    volume = sum(count * regular_area(n) * math.sqrt(radius ** 2 - 1 / (4 * math.sin(math.pi / n) ** 2)) / 3
                 for n, count in faces.items())
    return radius, volume


def around(p, vertex):
    """The numbers of sides of the faces around a vertex, in the order in which they follow each other."""
    after = {}
    for face in p.faces:
        if vertex in face:
            i = face.index(vertex)
            after[face[i - 1]] = (len(face), face[(i + 1) % len(face)])
    sizes, first = [], min(after)
    at = first
    while not sizes or at != first:
        size, at = after[at]
        sizes.append(size)
    return sizes


def same_ring(one, other):
    """Whether two rings are the same, wherever each starts and whichever way it runs."""
    turned = [tuple(one[k:]) + tuple(one[:k]) for k in range(len(one))]
    return tuple(other) in turned or tuple(reversed(other)) in turned


def same_points(one, other, tolerance=1e-9):
    """Whether every point of one list is a point of the other, and they are as many."""
    nearby = {tuple(round(c, 6) for c in b): b for b in other}
    def has(a):
        b = nearby.get(tuple(round(c, 6) for c in a))
        return (b is not None and norm(sub(a, b)) < tolerance) or any(norm(sub(a, b)) < tolerance for b in other)
    return len(one) == len(other) and all(has(a) for a in one)


def common_area(one, other):
    """The area two convex polygons have in common: the first cut down by every side of the second."""
    if (max(x for x, _ in one) <= min(x for x, _ in other) or max(x for x, _ in other) <= min(x for x, _ in one)
            or max(y for _, y in one) <= min(y for _, y in other) or max(y for _, y in other) <= min(y for _, y in one)):
        return 0.0
    left = list(one)
    for (ax, ay), (bx, by) in zip(other, other[1:] + other[:1]):
        def side(point):
            return (bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax)
        kept = []
        for p, q in zip(left, left[1:] + left[:1]):
            if side(p) >= 0:
                kept.append(p)
            if side(p) * side(q) < 0:
                t = side(p) / (side(p) - side(q))
                kept.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
        left = kept
        if len(left) < 3:
            return 0.0
    return unfold.polygon_area(tuple(left))


def box_corners(half, offset=(0.0, 0.0, 0.0)):
    return [(offset[0] + sx * half[0], offset[1] + sy * half[1], offset[2] + sz * half[2])
            for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]


def beyond(p, wall, points):
    """How far the worst of the points is beyond a face of p moved inward by the wall: negative when all are inside."""
    return max(dot(n, point) - (d - wall) for n, d in zip(p.normals, p.distances) for point in points)


# ---- the eighteen named solids ----------------------------------------------------------------------------------

def test_the_names_are_the_five_platonic_and_the_thirteen_archimedean_solids():
    assert len(polyhedra.PLATONIC) == 5 and len(polyhedra.ARCHIMEDEAN) == 13
    assert polyhedra.NAMES == polyhedra.PLATONIC + polyhedra.ARCHIMEDEAN and set(polyhedra.NAMES) == set(KNOWN)
    assert polyhedra.named("Truncated Octahedron").vertices == polyhedra.named("truncated_octahedron").vertices
    with pytest.raises(ValueError, match="no solid named 'sphere'; known: tetrahedron, cube"):
        polyhedra.named("sphere")


def test_the_two_roots_are_the_roots_of_their_cubics():
    assert polyhedra.TRIBONACCI == pytest.approx(T, rel=1e-15) and T == pytest.approx(1.839286755, rel=1e-9)
    assert polyhedra.SNUB_DODECAHEDRON_ROOT == pytest.approx(XI, rel=1e-15) and XI == pytest.approx(1.7155615, rel=1e-7)
    assert polyhedra.PHI ** 2 == pytest.approx(polyhedra.PHI + 1, rel=1e-15)


@named
def test_vertices_edges_and_faces_are_as_many_as_known(name):
    p = polyhedra.named(name)
    vertices, edges, faces, by_sides, _, _ = KNOWN[name]
    assert p.counts == (vertices, edges, faces) == (len(p.vertices), len(p.edges), len(p.faces))
    assert vertices - edges + faces == 2                                           # Euler
    assert Counter(len(face) for face in p.faces) == by_sides
    assert {sides: len(p.faces_with(sides)) for sides in by_sides} == by_sides
    assert all(edges_of_vertex == len(KNOWN[name][4]) for edges_of_vertex in
               Counter(i for edge in p.edges for i in edge).values())
    assert repr(p) == f"Polyhedron('{name}': {vertices} vertices, {edges} edges, {faces} faces)"


@named
def test_every_edge_has_the_length_asked_for(name):
    for length in (1.0, 30.0):
        p = polyhedra.named(name, length)
        assert max(p.edge_lengths) - min(p.edge_lengths) < REL * length
        assert p.edge_length == pytest.approx(length, rel=1e-12)
    assert polyhedra.named(name).with_edge(7.5).edge_length == pytest.approx(7.5, rel=1e-12)


@named
def test_every_face_is_plane_and_convex_and_runs_counter_clockwise_seen_from_outside(name):
    p = polyhedra.named(name)
    for f, face in enumerate(p.faces):
        corners = [p.vertices[i] for i in face]
        normal = unit(cross(sub(corners[1], corners[0]), sub(corners[2], corners[0])))
        assert all(abs(dot(normal, sub(corner, corners[0]))) < REL for corner in corners)          # in one plane
        assert dot(normal, corners[0]) > 0                                         # which has the centre behind it
        for a, b, c in zip(corners, corners[1:] + corners[:1], corners[2:] + corners[:2]):
            assert dot(normal, cross(sub(b, a), sub(c, b))) > 1e-3                 # a left turn at every corner
        assert all(dot(normal, sub(v, corners[0])) < REL for v in p.vertices)      # and no vertex in front of it
        assert p.normals[f] == pytest.approx(normal, abs=REL)
        assert p.distances[f] == pytest.approx(dot(normal, corners[0]), rel=REL)


@named
def test_every_vertex_is_alike(name):
    p = polyhedra.named(name)
    radii = [norm(v) for v in p.vertices]
    assert max(radii) - min(radii) < REL * max(radii)                             # all on one sphere about the origin
    assert p.circumradius == pytest.approx(max(radii), rel=REL)
    assert norm(p.centre) < REL
    for vertex in range(len(p.vertices)):
        assert same_ring(around(p, vertex), KNOWN[name][4]), (vertex, around(p, vertex))


@named
def test_volume_and_area_are_those_of_the_closed_forms(name):
    p = polyhedra.named(name)
    by_sides, volume = KNOWN[name][3], KNOWN[name][5]
    assert p.volume == pytest.approx(volume, rel=REL)
    assert p.area == pytest.approx(sum(count * regular_area(sides) for sides, count in by_sides.items()), rel=REL)
    for f, face in enumerate(p.faces):
        assert p.face_areas[f] == pytest.approx(regular_area(len(face)), rel=REL)
    scaled = polyhedra.named(name, 3.0)
    assert scaled.volume == pytest.approx(27 * volume, rel=REL) and scaled.area == pytest.approx(9 * p.area, rel=REL)


@named
def test_radius_and_volume_follow_from_the_faces_around_a_vertex(name):
    p = polyhedra.named(name)
    radius, volume = from_the_vertex(KNOWN[name][4], KNOWN[name][3])
    assert p.circumradius == pytest.approx(radius, rel=REL)
    assert p.volume == pytest.approx(volume, rel=REL)
    assert volume == pytest.approx(KNOWN[name][5], rel=REL)                       # the two things known agree too


def test_the_volumes_of_the_two_snubs_are_the_published_decimals():
    assert polyhedra.named("snub-cube").volume == pytest.approx(7.889477, rel=1e-7)
    assert polyhedra.named("snub-dodecahedron").volume == pytest.approx(37.61665, rel=1e-7)


def test_the_three_radii_of_a_cube_and_a_truncated_octahedron():
    cube = polyhedra.named("cube", 2.0)
    assert (cube.inradius, cube.midradius, cube.circumradius) == pytest.approx((1.0, R2, math.sqrt(3)), rel=REL)
    solid = polyhedra.named("truncated-octahedron")
    # the hexagons are nearer the centre than the squares
    assert (solid.inradius, solid.midradius, solid.circumradius) == pytest.approx(
        (math.sqrt(6) / 2, 1.5, math.sqrt(10) / 2), rel=REL)
    assert {round(solid.distances[f], 9) for f in solid.faces_with(4)} == {round(R2, 9)}


HALF_TURN = [[-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]]              # about Z
QUARTER_TURN = [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]            # about Z
THIRD_TURN = [[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]               # about (1, 1, 1): x, y, z take turns
FIFTH_TURN = [[0.5, PHI / 2, 1 / (2 * PHI)], [-PHI / 2, 1 / (2 * PHI), 0.5], [1 / (2 * PHI), -0.5, PHI / 2]]   # about (1, 0, PHI)


def rotations(*generators):
    """Every rotation that products of the given ones make: the group they generate."""
    def key(m):
        return tuple(round(c, 9) for row in m for c in row)
    found = {key(g): g for g in generators}
    new = list(found.values())
    while new:
        m = new.pop()
        for g in generators:
            product = [[sum(m[i][k] * g[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
            if key(product) not in found:
                found[key(product)] = product
                new.append(product)
    return list(found.values())


# the rotations of the tetrahedron, of the cube and of the icosahedron, and which solids have which
GROUPS = {12: rotations(HALF_TURN, THIRD_TURN), 24: rotations(QUARTER_TURN, THIRD_TURN), 60: rotations(FIFTH_TURN, THIRD_TURN)}
FAMILY = {"tetrahedron": 12, "truncated-tetrahedron": 12,
          "cube": 24, "octahedron": 24, "cuboctahedron": 24, "truncated-cube": 24, "truncated-octahedron": 24,
          "rhombicuboctahedron": 24, "truncated-cuboctahedron": 24, "snub-cube": 24,
          "dodecahedron": 60, "icosahedron": 60, "icosidodecahedron": 60, "truncated-dodecahedron": 60,
          "truncated-icosahedron": 60, "rhombicosidodecahedron": 60, "truncated-icosidodecahedron": 60,
          "snub-dodecahedron": 60}


@named
def test_every_rotation_of_its_family_lays_the_solid_on_itself(name):
    turns = GROUPS[FAMILY[name]]
    assert len(turns) == FAMILY[name]
    p = polyhedra.named(name)
    assert all(same_points(p.rotated(turn).vertices, p.vertices) for turn in turns)
    # so the vertices are alike in more than their distance from the centre: one vertex is carried to all others,
    # or, where there are twice as many vertices as rotations, to every second one
    images = [p.rotated(turn).vertices[0] for turn in turns]
    reached = sum(any(norm(sub(v, image)) < REL for image in images) for v in p.vertices)
    assert reached == min(len(p.vertices), len(turns))


@pytest.mark.parametrize("name", ["snub-cube", "snub-dodecahedron"])
def test_a_snub_is_not_its_mirror_image(name):
    p = polyhedra.named(name)
    mirror = p.mirrored()
    # a turn that laid the mirror image on the solid would be one of its family's: there is none
    assert not any(same_points(mirror.rotated(turn).vertices, p.vertices) for turn in GROUPS[FAMILY[name]])
    assert mirror.volume == pytest.approx(p.volume, rel=REL)                       # positive: its faces still face out
    assert mirror.counts == p.counts and mirror.edge_length == pytest.approx(1.0, rel=1e-12)
    assert all(same_ring(around(mirror, v), KNOWN[name][4]) for v in range(len(mirror.vertices)))
    assert mirror.mirrored() == p


def test_the_mirror_image_of_another_solid_is_the_solid_itself_perhaps_turned():
    for name in ("cube", "truncated-octahedron", "icosidodecahedron", "truncated-icosidodecahedron"):
        p = polyhedra.named(name)
        assert same_points(p.vertices, p.mirrored().vertices)
        assert p.mirrored().volume == pytest.approx(p.volume, rel=REL)
    for name in ("tetrahedron", "truncated-tetrahedron"):
        p = polyhedra.named(name)
        assert not same_points(p.vertices, p.mirrored().vertices)
        assert same_points(p.rotated(QUARTER_TURN).vertices, p.mirrored().vertices)


# ---- the same solid, somewhere else -----------------------------------------------------------------------------

def test_scaled_turned_and_moved():
    p = polyhedra.named("truncated-octahedron")
    big = p.scaled(2.0)
    assert big.faces == p.faces and big.vertices[5] == pytest.approx(times(p.vertices[5], 2.0))
    turned = polyhedra.box(4.0, 2.0, 1.0).rotated(QUARTER_TURN)
    assert same_points(turned.vertices, polyhedra.box(2.0, 4.0, 1.0).vertices)
    assert turned.volume == pytest.approx(8.0)
    moved = p.translated((10.0, 0.0, -2.0))
    assert moved.centre == pytest.approx((10.0, 0.0, -2.0)) and moved.volume == pytest.approx(p.volume, rel=REL)
    assert (moved.inradius, moved.midradius, moved.circumradius) == pytest.approx(
        (p.inradius, p.midradius, p.circumradius), rel=REL)
    for n, d, was in zip(moved.normals, moved.distances, p.distances):
        assert d == pytest.approx(was + dot(n, (10.0, 0.0, -2.0)), abs=REL)
    with pytest.raises(ValueError, match="a mirror, not a rotation"):
        p.rotated([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])
    with pytest.raises(ValueError, match="not orthonormal"):
        p.rotated([[2, 0, 0], [0, 1, 0], [0, 0, 1]])
    for factor in (0.0, -1.0):
        with pytest.raises(ValueError, match="a scale factor is positive"):
            p.scaled(factor)


@named
def test_resting_on_a_face_puts_it_in_z0_with_the_rest_above(name):
    p = polyhedra.named(name, 2.0)
    for sides in sorted({len(face) for face in p.faces}):
        f = p.faces_with(sides)[-1]
        for edge in (0, sides - 1):
            q = p.resting_on(f, edge)
            assert q.faces == p.faces
            assert all(abs(q.vertices[i][2]) < REL for i in q.faces[f])
            assert all(v[2] > 1e-3 for i, v in enumerate(q.vertices) if i not in q.faces[f])
            assert q.normals[f] == pytest.approx((0.0, 0.0, -1.0), abs=REL) and abs(q.distances[f]) < REL
            start, end = q.vertices[q.faces[f][edge]], q.vertices[q.faces[f][(edge + 1) % sides]]
            assert sub(end, start) == pytest.approx((2.0, 0.0, 0.0), abs=REL)       # that edge runs along +X
            assert q.centre == pytest.approx((0.0, 0.0, p.distances[f]), abs=REL)
            assert q.volume == pytest.approx(p.volume, rel=REL) and q.edge_length == pytest.approx(2.0, rel=REL)
            assert q.face_towards((0, 0, -1)) == f


# ---- sizing -----------------------------------------------------------------------------------------------------

@every
def test_the_scale_to_hold_a_box_holds_it_and_no_smaller_one_does(p):
    half, wall, clearance = (50.0, 40.0, 10.0), 3.0, 2.0
    corners = box_corners((52.0, 42.0, 12.0))
    q = p.scaled(p.scale_to_hold_box(half, wall, clearance))
    tolerance = REL * q.circumradius
    assert beyond(q, wall, corners) < tolerance                                    # every corner inside every moved face
    assert beyond(q, wall, corners) > -tolerance                                   # and one of them on a face: tight
    assert all(dot(n, c) <= d + tolerance for c in box_corners(half) for n, d in zip(q.normals, q.distances))
    # without wall and clearance the solid is smaller, and the bare box touches it
    bare = p.scaled(p.scale_to_hold_box(half))
    assert bare.circumradius < q.circumradius and abs(beyond(bare, 0.0, box_corners(half))) < tolerance


@every
def test_the_scale_to_hold_a_box_that_stands_off_the_face_the_solid_rests_on(p):
    resting = p.resting_on(p.faces_with(max(len(face) for face in p.faces))[0])
    half, wall, clearance, standoff = (50.0, 40.0, 10.0), 3.0, 2.0, 5.0
    offset = (4.0, -3.0, wall + standoff + half[2] + clearance)                    # its underside 5 above the inner floor
    corners = box_corners((52.0, 42.0, 12.0), offset)
    q = resting.scaled(resting.scale_to_hold_box(half, wall, clearance, offset))
    tolerance = REL * q.circumradius
    floor = q.face_towards((0, 0, -1))
    assert all(abs(q.vertices[i][2]) < tolerance for i in q.faces[floor])          # it still rests on z = 0
    assert abs(beyond(q, wall, corners)) < tolerance                               # holds the box, tightly
    assert min(c[2] for c in corners) == pytest.approx(wall + standoff)
    # off centre the solid has to be larger than for the same box in the middle, at the same height
    centred = resting.scaled(resting.scale_to_hold_box(half, wall, clearance, (0.0, 0.0, offset[2])))
    assert centred.circumradius <= q.circumradius + tolerance
    with pytest.raises(ValueError, match="passes through the origin and does not move with the scale"):
        resting.scale_to_hold_box(half, wall, clearance, (0.0, 0.0, wall + half[2] + clearance - 1.0))


def test_what_scale_to_hold_box_refuses():
    p = polyhedra.named("cube")
    assert p.scale_to_hold_box((1.0, 2.0, 3.0)) == pytest.approx(6.0)             # the cube of edge 6 holds 2 x 4 x 6
    assert p.scale_to_hold_box((1.0, 2.0, 3.0), wall=0.5, clearance=0.25) == pytest.approx(7.5)
    with pytest.raises(ValueError, match="cannot be negative"):
        p.scale_to_hold_box((1.0, 2.0, 3.0), wall=-1.0)
    with pytest.raises(ValueError, match="have no size"):
        p.scale_to_hold_box((0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="the origin is outside face"):
        p.translated((5.0, 0.0, 0.0)).scale_to_hold_box((1.0, 1.0, 1.0))


# ---- the cavity and the plates ----------------------------------------------------------------------------------

@every
def test_the_plates_of_all_faces_fill_the_shell_and_share_only_their_sides(p):
    wall = 0.2 * p.inradius
    tolerance = REL * p.circumradius
    cavity = p.inset(wall)
    assert len(cavity.faces) == len(p.faces)
    for n, d in zip(cavity.normals, cavity.distances):                             # every face moved in by the wall
        f = p.face_towards(n)
        assert dot(n, p.normals[f]) == pytest.approx(1.0, abs=REL) and d == pytest.approx(p.distances[f] - wall, abs=tolerance)
    plates = p.panels(wall)
    assert math.fsum(plate.volume for plate in plates) == pytest.approx(p.volume - cavity.volume, rel=REL)
    for f, plate in enumerate(plates):
        n, d = p.normals[f], p.distances[f]
        front, back = plate.face_towards(n), plate.face_towards(times(n, -1.0))
        assert plate.face_areas[front] == pytest.approx(p.face_areas[f], rel=REL)   # its outer face is the face
        assert plate.distances[front] == pytest.approx(d, abs=tolerance)
        assert plate.distances[back] == pytest.approx(wall - d, abs=tolerance)      # and its inner face the cavity's
        assert plate.face_areas[back] == pytest.approx(cavity.face_areas[cavity.face_towards(n)], rel=1e-7)
        for v in plate.vertices:
            depth = d - dot(n, v)
            assert -tolerance < depth < wall + tolerance
            # no nearer to any other face than to its own: the plane halfway to another face has that
            # face's plate on its other side, so two plates have no volume in common
            assert all(e - dot(m, v) > depth - tolerance for m, e in zip(p.normals, p.distances))


@pytest.mark.parametrize("name", ["truncated-cube", "cuboctahedron", "snub-cube", "truncated-icosahedron"])
def test_behind_a_thick_wall_small_faces_vanish_and_the_plates_still_fill_the_shell(name):
    p = polyhedra.named(name)
    wall = 0.95 * p.inradius
    cavity = p.inset(wall)
    assert len(cavity.faces) < len(p.faces)
    assert math.fsum(plate.volume for plate in p.panels(wall)) == pytest.approx(p.volume - cavity.volume, rel=REL)


def test_the_cavity_is_a_scaled_copy_only_where_all_faces_are_equally_far():
    for name in polyhedra.PLATONIC:
        p = polyhedra.named(name, 10.0)
        wall = 0.3 * p.inradius
        assert p.inset(wall).volume == pytest.approx(p.volume * 0.7 ** 3, rel=REL)
        assert same_points(p.inset(wall).vertices, p.scaled(0.7).vertices, 1e-9 * p.circumradius)
    assert polyhedra.box(100.0, 80.0, 20.0).inset(3.0).volume == pytest.approx(94.0 * 74.0 * 14.0, rel=REL)
    p = polyhedra.named("truncated-octahedron")
    wall = 0.3 * p.inradius                                                        # 0.3 of the way in for a hexagon
    cavity = p.inset(wall)
    assert cavity.volume > p.volume * 0.7 ** 3 * (1 + 1e-3)                        # a copy scaled by 0.7 is smaller
    squares, hexagons = cavity.faces_with(4), cavity.faces_with(6)
    assert (len(squares), len(hexagons)) == (6, 8)
    assert {round(cavity.distances[f], 9) for f in squares} == {round(R2 - wall, 9)}
    assert {round(cavity.distances[f], 9) for f in hexagons} == {round(0.7 * math.sqrt(6) / 2, 9)}
    assert max(cavity.edge_lengths) - min(cavity.edge_lengths) > 0.1               # its edges are no longer equal
    for wall in (0.0, p.inradius, 2 * p.inradius):
        with pytest.raises(ValueError, match="less than the inradius"):
            p.inset(wall)
    with pytest.raises(ValueError, match="thickness is positive"):
        p.panel(0, 0.0)


# ---- prisms, antiprisms, boxes ----------------------------------------------------------------------------------

def test_prisms_antiprisms_and_boxes():
    prism = polyhedra.prism(6)
    assert prism.counts == (12, 18, 8) and Counter(map(len, prism.faces)) == {4: 6, 6: 2}
    assert prism.edge_length == pytest.approx(1.0, rel=1e-12)                      # square sides
    assert prism.volume == pytest.approx(regular_area(6), rel=REL)
    tall = polyhedra.prism(5, 2.0, 7.0)
    assert tall.counts == (10, 15, 7) and tall.volume == pytest.approx(4 * regular_area(5) * 7.0, rel=REL)
    assert sorted(round(length, 9) for length in tall.edge_lengths) == [2.0] * 10 + [7.0] * 5
    assert {v[2] for v in tall.vertices} == {-3.5, 3.5}
    with pytest.raises(ValueError, match="edges are not of one length"):
        tall.with_edge(1.0)
    assert same_points(polyhedra.prism(4).vertices, polyhedra.named("cube").vertices)

    for n in (3, 5, 8):
        anti = polyhedra.antiprism(n, 2.0)
        assert anti.counts == (2 * n, 4 * n, 2 * n + 2)
        assert Counter(map(len, anti.faces)) == ({3: 8} if n == 3 else {3: 2 * n, n: 2})
        assert anti.edge_length == pytest.approx(2.0, rel=1e-12)
        closed_form = n * math.sqrt(4 * math.cos(math.pi / (2 * n)) ** 2 - 1) * math.sin(3 * math.pi / (2 * n)) \
            / (12 * math.sin(math.pi / n) ** 2)
        assert anti.volume == pytest.approx(8 * closed_form, rel=REL)
    assert polyhedra.antiprism(3).volume == pytest.approx(KNOWN["octahedron"][5], rel=REL)

    box = polyhedra.box(100.0, 80.0, 20.0)
    assert box.counts == (8, 12, 6) and box.volume == 160000.0 and box.area == 23200.0
    assert set(box.vertices) == {(x, y, z) for x in (-50.0, 50.0) for y in (-40.0, 40.0) for z in (-10.0, 10.0)}
    assert (box.inradius, box.circumradius) == pytest.approx((10.0, math.sqrt(50 ** 2 + 40 ** 2 + 10 ** 2)))
    assert sorted(box.distances) == pytest.approx([10.0, 10.0, 40.0, 40.0, 50.0, 50.0])
    for make in (lambda: polyhedra.prism(2), lambda: polyhedra.antiprism(2), lambda: polyhedra.box(0.0, 1.0, 1.0),
                 lambda: polyhedra.prism(5, 1.0, 0.0)):
        with pytest.raises(ValueError):
            make()


def test_a_prism_on_any_convex_polygon():
    corners = [(0, 0), (40, 0), (50, 10), (50, 30), (20, 40), (0, 30)]
    area = unfold.polygon_area(corners)
    around = math.fsum(math.dist(a, b) for a, b in zip(corners, corners[1:] + corners[:1]))
    assert area == 1700.0
    prism = polyhedra.prism_on(corners, 12.0)
    assert prism.name == "prism-on-6" and prism.counts == (12, 18, 8) and Counter(map(len, prism.faces)) == {4: 6, 6: 2}
    assert prism.volume == pytest.approx(area * 12.0, rel=REL) and prism.area == pytest.approx(2 * area + around * 12.0, rel=REL)
    assert {v[2] for v in prism.vertices} == {-6.0, 6.0} and {v[:2] for v in prism.vertices} == set(map(tuple, corners))
    ends = prism.faces_with(6)
    assert sorted(prism.normals[f] for f in ends) == [pytest.approx((0.0, 0.0, -1.0)), pytest.approx((0.0, 0.0, 1.0))]
    # the corners may run either way round, and a regular polygon gives the prism of that name
    other = polyhedra.prism_on(corners[::-1], 12.0, "other")
    assert other.name == "other" and same_points(other.vertices, prism.vertices) and other.volume == pytest.approx(prism.volume, rel=REL)
    regular = polyhedra.prism(7, 3.0, 5.0)
    again = polyhedra.prism_on([v[:2] for v in regular.vertices if v[2] < 0], 5.0)
    assert again.counts == regular.counts and again.volume == pytest.approx(regular.volume, rel=REL)
    # a point on a side or inside the polygon is no corner of it
    for extra in ((20, 0), (20, 20)):
        with pytest.raises(ValueError, match=r"points \[6, 13\] are not corners"):
            polyhedra.prism_on(corners + [extra], 12.0)
    for make in (lambda: polyhedra.prism_on(corners[:2], 12.0), lambda: polyhedra.prism_on(corners, 0.0)):
        with pytest.raises(ValueError, match="at least three corners and a positive height"):
            make()


def test_a_solid_clipped_by_a_plane_is_the_part_on_its_inner_side():
    cube = polyhedra.named("cube", 2.0)
    half = cube.clipped((0, 0, 1), 0.0)
    assert half.name == "cube" and half.counts == (8, 12, 6)
    assert half.volume == pytest.approx(4.0, rel=REL) and half.area == pytest.approx(16.0, rel=REL)
    cut = half.face_towards((0, 0, 1))                              # the cut is a face, where the plane is
    assert half.normals[cut] == pytest.approx((0.0, 0.0, 1.0)) and half.distances[cut] == pytest.approx(0.0, abs=1e-12)
    assert half.face_areas[cut] == pytest.approx(4.0, rel=REL) and {v[2] for v in half.polygon(cut)} == {0.0}
    assert min(v[2] for v in half.vertices) == -1.0
    # a normal of any length is a direction, and the distance is along it: the plane z = 0.5
    assert cube.clipped((0, 0, 4), 0.5).volume == pytest.approx(6.0, rel=REL)
    assert cube.clipped((0, 0, -1), -0.5).volume == pytest.approx(2.0, rel=REL)
    # one corner cut off through the middles of its three edges: a triangle there, three pentagons, three squares
    corner = cube.clipped((1, 1, 1), 2 / math.sqrt(3))
    assert corner.counts == (10, 15, 7) and Counter(map(len, corner.faces)) == {3: 1, 4: 3, 5: 3}
    assert corner.volume == pytest.approx(8 - 1 / 6, rel=REL)
    # a truncated octahedron on a hexagon, divided at half its height: the plane crosses six hexagons and leaves
    # three of them as hexagons and three as quadrilaterals on either side, beside the three squares
    p = polyhedra.named("truncated-octahedron", 30.0)
    p = p.resting_on(p.faces_with(6)[0])
    height = max(v[2] for v in p.vertices)
    below, above = p.clipped((0, 0, 1), height / 2), p.clipped((0, 0, -1), -height / 2)
    for part in (below, above):
        assert part.counts == (18, 27, 11) and Counter(map(len, part.faces)) == {4: 6, 6: 5}
        assert part.volume == pytest.approx(p.volume / 2, rel=REL)
    cut = below.face_towards((0, 0, 1))
    assert below.area + above.area == pytest.approx(p.area + 2 * below.face_areas[cut], rel=REL)
    # a plane that only touches, or misses, cuts nothing off or leaves nothing
    for distance, what in ((1.0, "all"), (5.0, "all"), (-1.0, "none"), (-5.0, "none")):
        with pytest.raises(ValueError, match=f"cube: the plane leaves {what} of the solid"):
            cube.clipped((0, 0, 1), distance)


# ---- the convex hull --------------------------------------------------------------------------------------------

def test_the_hull_takes_corners_only_and_a_polyhedron_refuses_other_points():
    cube = [(x, y, z) for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)]
    inside, in_a_face, on_an_edge = (0.5, 0.5, 0.5), (0.5, 0.5, 1.0), (0.5, 0.0, 0.0)
    faces = polyhedra.hull(cube + [inside, in_a_face, on_an_edge])
    assert sorted(len(face) for face in faces) == [4] * 6 and {i for face in faces for i in face} == set(range(8))
    with pytest.raises(ValueError, match=r"points \[8, 9, 10\] are not corners"):
        polyhedra.from_vertices("cube and more", cube + [inside, in_a_face, on_an_edge])
    with pytest.raises(ValueError, match="all lie in one plane"):
        polyhedra.hull([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0), (0.5, 0.5, 0.0)])
    with pytest.raises(ValueError, match="at least four points"):
        polyhedra.hull(cube[:3])


def faces_by_trying_every_plane(points):
    """The faces of a convex hull found the slow way: a plane through three of the points that has every other
    point on one side holds a face, whose corners are the points in that plane."""
    found = set()
    for i, j, k in combinations(range(len(points)), 3):
        normal = cross(sub(points[j], points[i]), sub(points[k], points[i]))
        if norm(normal) > 1e-9:
            side = [dot(unit(normal), sub(point, points[i])) for point in points]
            if max(side) < 1e-7 or min(side) > -1e-7:
                found.add(frozenset(m for m, s in enumerate(side) if abs(s) < 1e-7))
    return found


SMALL = [p for p in SHAPES if len(p.vertices) <= 30] + [
    polyhedra.from_vertices("lens-24", [(x, y, 0.1 * z) for x, y, z in unfold.directions(24)])]


@pytest.mark.parametrize("p", SMALL, ids=[p.name for p in SMALL])
def test_the_faces_are_those_found_by_trying_every_plane(p):
    assert {frozenset(face) for face in p.faces} == faces_by_trying_every_plane(p.vertices)


def test_the_faces_do_not_depend_on_the_order_of_the_vertices():
    p = polyhedra.named("snub-cube")
    again = polyhedra.from_vertices("again", list(reversed(p.vertices)))
    assert again.counts == p.counts and again.volume == pytest.approx(p.volume, rel=REL)
    back = {len(p.vertices) - 1 - i: i for i in range(len(p.vertices))}
    assert {frozenset(back[i] for i in face) for face in again.faces} == {frozenset(face) for face in p.faces}
    # a face begins with its lowest vertex and the faces are sorted: the indices of faces are settled
    assert all(face[0] == min(face) for face in p.faces) and list(p.faces) == sorted(p.faces)


def test_the_intersection_of_half_spaces_leaves_out_what_only_touches():
    planes = [((1.0, 0.0, 0.0), 1.0), ((-1.0, 0.0, 0.0), 1.0), ((0.0, 1.0, 0.0), 1.0), ((0.0, -1.0, 0.0), 1.0),
              ((0.0, 0.0, 1.0), 1.0), ((0.0, 0.0, -1.0), 1.0)]
    touching = [(unit((1.0, 1.0, 0.0)), R2), (unit((1.0, 1.0, 1.0)), math.sqrt(3)), ((1.0, 0.0, 0.0), 5.0)]
    cube = polyhedra.intersection("cube", planes + touching, (0.1, 0.2, -0.3))
    assert cube.counts == (8, 12, 6) and cube.volume == pytest.approx(8.0, rel=REL)
    cut = polyhedra.intersection("cut", planes + [(unit((1.0, 1.0, 1.0)), 2 / math.sqrt(3))], (0.0, 0.0, 0.0))
    assert cut.counts == (10, 15, 7) and cut.volume == pytest.approx(8.0 - 1 / 6, rel=REL)    # a corner of side 1 gone
    with pytest.raises(ValueError, match="not inside every half-space"):
        polyhedra.intersection("cube", planes, (1.0, 0.0, 0.0))


# ---- the flat pattern -------------------------------------------------------------------------------------------

def no_two_overlap(polygons, area):
    return all(common_area(a, b) < REL * area for a, b in combinations(polygons, 2))


@every
def test_the_flat_pattern_has_every_face_once_and_no_two_overlap(p):
    pattern = unfold.unfold(p)
    vertices, edges, faces = p.counts
    tolerance = REL * p.circumradius
    assert len(pattern.polygons) == faces and len(pattern.folds) == faces - 1 and len(pattern.cuts) == edges - faces + 1
    assert pattern.area == pytest.approx(p.area, rel=REL)
    for face, polygon, area in zip(p.faces, pattern.polygons, p.face_areas):
        assert unfold.polygon_area(polygon) == pytest.approx(area, rel=REL)        # counter-clockwise, the same area
        for i, j in combinations(range(len(face)), 2):                             # and the same shape
            assert math.dist(polygon[i], polygon[j]) == pytest.approx(
                norm(sub(p.vertices[face[i]], p.vertices[face[j]])), abs=tolerance)
    assert no_two_overlap(pattern.polygons, p.area)
    assert {fold.edge for fold in pattern.folds} == unfold.breadth_first(p, 0)     # the first tree tried did
    joined = {pattern.root}
    for fold in pattern.folds:                                                     # each fold joins a new face on
        (f, g), (a, b) = fold.faces, fold.edge
        assert f in joined and g not in joined
        joined.add(g)
        for face in (f, g):                                                        # along an edge both faces have
            where = (pattern.polygons[face][p.faces[face].index(a)], pattern.polygons[face][p.faces[face].index(b)])
            assert where[0] == pytest.approx(fold.segment[0], abs=tolerance)
            assert where[1] == pytest.approx(fold.segment[1], abs=tolerance)
        assert math.cos(fold.angle) == pytest.approx(dot(p.normals[f], p.normals[g]), abs=REL) and 0 < fold.angle < math.pi
    assert len(joined) == faces
    assert {cut.edge for cut in pattern.cuts} | {fold.edge for fold in pattern.folds} == set(p.edges)
    for cut in pattern.cuts:                                                       # a cut edge is on the outline twice
        for face, (start, end) in zip(cut.faces, cut.segments):
            assert math.dist(start, end) == pytest.approx(norm(sub(*(p.vertices[i] for i in cut.edge))), abs=tolerance)
            assert start in pattern.polygons[face] and end in pattern.polygons[face]
    xs, ys = [x for polygon in pattern.polygons for x, _ in polygon], [y for polygon in pattern.polygons for _, y in polygon]
    assert (min(xs), min(ys)) == (0.0, 0.0) and pattern.size == (max(xs), max(ys))


@named
def test_the_outline_of_a_flat_pattern_is_one_loop_round_the_area_of_the_faces_whatever_the_root(name):
    p = polyhedra.named(name, 30.0)
    lengths = dict(zip(p.edges, p.edge_lengths))
    for root in range(len(p.faces)):
        pattern = unfold.unfold(p, root)
        (loop,) = unfold.outline(pattern)
        assert unfold.polygon_area(loop) == pytest.approx(p.area, rel=REL)        # counter-clockwise, round every face
        # every cut edge is on it twice and nothing else is
        assert len(loop) == 2 * len(pattern.cuts)
        around = math.fsum(math.dist(a, b) for a, b in zip(loop, loop[1:] + loop[:1]))
        assert around == pytest.approx(2 * math.fsum(lengths[cut.edge] for cut in pattern.cuts), rel=REL)
        if root == 0:                                              # and every fold line runs from the outline to it
            for fold in pattern.folds:
                assert all(min(math.dist(end, corner) for corner in loop) < 1e-6 for end in fold.segment)


def test_the_outline_of_a_box_and_of_a_prism_on_unequal_sides():
    box = polyhedra.box(100.0, 80.0, 20.0)
    (loop,) = unfold.outline(unfold.unfold(box))
    assert len(loop) == 14 and unfold.polygon_area(loop) == pytest.approx(23200.0, rel=REL)
    # every side of the outline is one of the box's three lengths, and runs along x or y
    for a, b in zip(loop, loop[1:] + loop[:1]):
        assert round(math.dist(a, b), 6) in (20.0, 80.0, 100.0) and min(abs(a[0] - b[0]), abs(a[1] - b[1])) < 1e-9
    prism = polyhedra.prism_on([(0, 0), (40, 0), (50, 10), (50, 30), (20, 40), (0, 30)], 12.0)
    (loop,) = unfold.outline(unfold.unfold(prism))
    assert unfold.polygon_area(loop) == pytest.approx(prism.area, rel=REL) and len(loop) == 2 * (18 - 7)


def test_cut_edges_that_are_no_outline_are_refused():
    def pattern(*squares, more=()):
        """A pattern of unit squares at those corners, with no fold: every side of every square is cut."""
        sides = [((x + a, y + b), (x + c, y + d)) for x, y in squares
                 for (a, b), (c, d) in (((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)), ((0, 1), (0, 0)))] + list(more)
        cuts = tuple(unfold.Cut((0, 1), (0, 1), (sides[k], sides[k + 1])) for k in range(0, len(sides), 2))
        return unfold.Pattern((), (), cuts, (3.0, 3.0), 0)

    (alone,) = unfold.outline(pattern((0.0, 0.0)))
    assert unfold.polygon_area(alone) == pytest.approx(1.0) and len(alone) == 4
    # two squares side by side, and two that meet in a corner: four cut edges end where they touch
    with pytest.raises(unfold.UnfoldError, match=r"4 cut edges of the pattern end at \(1, 0\), not two"):
        unfold.outline(pattern((0.0, 0.0), (1.0, 0.0)))
    with pytest.raises(unfold.UnfoldError, match=r"4 cut edges of the pattern end at \(1, 1\), not two"):
        unfold.outline(pattern((0.0, 0.0), (1.0, 1.0)))
    # two edges that lie on each other from end to end, with nothing else at their ends: a slit
    slit = ((0.25, 0.5), (0.75, 0.5))
    with pytest.raises(unfold.UnfoldError, match=r"lie side by side at \(0.25, 0.5\): the cut between them is a slit"):
        unfold.outline(pattern((0.0, 0.0), more=(slit, slit[::-1])))
    # two squares apart are two loops, which a pattern of one solid never is: the larger comes first
    apart = unfold.outline(pattern((0.0, 0.0), (1.5, 1.5)))
    assert len(apart) == 2 and unfold.polygon_area(apart[0]) > 0 > unfold.polygon_area(apart[1])
    # a corner of one face in the middle of a side of another: the cut edges meet two by two at every corner and
    # still pass that point twice. Two squares side by side, one half a side further up; a square and a kite
    # that touches its side with one corner
    with pytest.raises(unfold.UnfoldError, match=r"a corner of the pattern at \(1, 0.5\) lies on a cut edge that does not end there"):
        unfold.outline(pattern((0.0, 0.0), (1.0, 0.5)))
    kite = (((1.0, 0.5), (2.0, 0.0)), ((2.0, 0.0), (3.0, 0.5)), ((3.0, 0.5), (2.0, 1.0)), ((2.0, 1.0), (1.0, 0.5)))
    with pytest.raises(unfold.UnfoldError, match=r"a corner of the pattern at \(1, 0.5\) lies on a cut edge that does not end there"):
        unfold.outline(pattern((0.0, 0.0), more=kite))
    # two faces that lie over one another: their sides cross
    with pytest.raises(unfold.UnfoldError, match=r"two cut edges of the pattern cross at \(1, 0.5\)"):
        unfold.outline(pattern((0.0, 0.0), (0.5, 0.5)))
    # a kite that stops short of the square is a second loop
    short = tuple(((x + 0.001, y), (u + 0.001, v)) for (x, y), (u, v) in kite)
    assert len(unfold.outline(pattern((0.0, 0.0), more=short))) == 2


def test_the_root_face_lies_along_x_and_the_fold_angles_of_a_cube_are_right_angles():
    p = polyhedra.named("truncated-octahedron", 30.0)
    root = p.faces_with(4)[2]
    pattern = unfold.unfold(p, root)
    start, end = pattern.polygons[root][0], pattern.polygons[root][1]
    assert pattern.root == root and sub(end + (0.0,), start + (0.0,)) == pytest.approx((30.0, 0.0, 0.0), abs=1e-9)
    assert {round(fold.angle, 9) for fold in unfold.unfold(polyhedra.named("cube")).folds} == {round(math.pi / 2, 9)}
    # square to hexagon 125.26 degrees, hexagon to hexagon 109.47: the sheet bends by what is left of 180
    assert {round(math.degrees(fold.angle), 2) for fold in pattern.folds} <= {54.74, 70.53}
    with pytest.raises(ValueError, match="has no face 14"):
        unfold.unfold(p, 14)


def lens():
    """A flat solid of 76 triangles. Its breadth-first pattern from face 48, as from 25 others, lays faces over
    each other."""
    return polyhedra.from_vertices("lens", [(x, y, 0.1 * z) for x, y, z in unfold.directions(40)])


def test_when_the_first_tree_overlaps_another_is_taken():
    p = lens()
    first, _ = unfold.lay_out(p, unfold.breadth_first(p, 48), 48)
    pair = unfold.overlapping(first, REL * p.circumradius)
    assert pair is not None and common_area(first[pair[0]], first[pair[1]]) > 0    # found there, and it is one
    assert max(common_area(a, b) for a, b in combinations(first, 2)) > 1e-4
    pattern = unfold.unfold(p, 48)
    assert pattern.root == 48 and pattern.area == pytest.approx(p.area, rel=REL)
    assert no_two_overlap(pattern.polygons, p.area)
    start, end = pattern.polygons[48][:2]                          # the root still lies along +X
    assert end[1] == pytest.approx(start[1], abs=REL) and end[0] > start[0]


def test_cutting_the_steepest_edges_leaves_a_tree_of_faces():
    for p in (lens(), polyhedra.named("snub-dodecahedron"), polyhedra.box(1.0, 1.0, 30.0)):
        free = 0
        for direction in unfold.directions(12) + [(1.0, 0.0, 0.0), (0.0, 0.0, -1.0)]:  # also along edges and faces
            folds = unfold.steepest_edge(p, direction)
            assert len(folds) == len(p.faces) - 1
            polygons, parents = unfold.lay_out(p, folds)                           # which fails if they do not join all
            assert len(parents) == len(p.faces) - 1
            free += unfold.overlapping(polygons, REL * p.circumradius) is None
            assert (unfold.overlapping(polygons, REL * p.circumradius) is None) == no_two_overlap(polygons, p.area)
        assert free >= 12


def test_a_solid_with_no_pattern_among_the_trees_tried_is_an_error(monkeypatch):
    p = lens()
    monkeypatch.setattr(unfold, "candidates", lambda polyhedron, root=0, open_faces=(): iter([unfold.breadth_first(polyhedron, 48)]))
    with pytest.raises(unfold.UnfoldError, match="lens: every one of the 1 flat patterns tried lays one face over another"):
        unfold.unfold(p)


# ---- a flat pattern with faces left open ------------------------------------------------------------------------

def walked(loop):
    """How long a loop of points is, round and back to its first."""
    return math.fsum(math.dist(a, b) for a, b in zip(loop, loop[1:] + loop[:1]))


def test_a_box_without_its_top_unfolds_into_a_tray():
    box = polyhedra.box(100.0, 80.0, 20.0)
    top, bottom = box.face_towards((0, 0, 1)), box.face_towards((0, 0, -1))
    pattern = unfold.unfold(box, bottom, [top])
    assert pattern.open_faces == (top,) and pattern.polygons[top] == () and pattern.root == bottom
    assert sum(1 for polygon in pattern.polygons if polygon) == 5 and no_two_overlap([p for p in pattern.polygons if p], box.area)
    # the floor with a wall on each of its sides: four folds of a right angle, none of them to the top
    assert len(pattern.folds) == 4 and all(fold.angle == pytest.approx(math.pi / 2) and top not in fold.faces for fold in pattern.folds)
    # the four upright edges are cut between two walls; the four round the top are on one wall only: the rim
    rim = [cut for cut in pattern.cuts if len(cut.segments) == 1]
    assert len(pattern.cuts) == 8 and len(rim) == 4 and all(cut.faces[1] == top and cut.faces[0] != top for cut in rim)
    assert sorted(round(math.dist(*cut.segments[0]), 9) for cut in rim) == [80.0, 80.0, 100.0, 100.0]
    assert all(len(cut.segments) == 2 and top not in cut.faces for cut in pattern.cuts if cut not in rim)
    (loop,) = unfold.outline(pattern)
    assert len(loop) == 12 and unfold.polygon_area(loop) == pytest.approx(100 * 80 + 2 * 20 * (100 + 80), rel=REL)
    assert walked(loop) == pytest.approx(2 * 4 * 20 + 2 * (100 + 80), rel=REL)
    assert sorted(pattern.size) == pytest.approx([120.0, 140.0]) and pattern.area == pytest.approx(15200.0, rel=REL)
    for fold in pattern.folds:                                     # every fold from the outline to the outline
        assert all(min(math.dist(end, corner) for corner in loop) < 1e-9 for end in fold.segment)
    # the closed box from the same face is the same with the top hung on one wall
    closed = unfold.unfold(box, bottom)
    assert closed.open_faces == () and len(closed.folds) == 5 and len(closed.cuts) == 7
    assert all(len(cut.segments) == 2 for cut in closed.cuts) and closed.area == pytest.approx(box.area, rel=REL)
    # the five faces lie as they lay, moved together by what the top adds on the low side of the pattern
    dx, dy = (closed.polygons[bottom][0][k] - pattern.polygons[bottom][0][k] for k in range(2))
    for f in range(6):
        assert f == top or all(a == pytest.approx((b[0] + dx, b[1] + dy)) for a, b in zip(closed.polygons[f], pattern.polygons[f]))


@named
def test_a_pattern_without_one_face_is_one_loop_round_the_faces_that_are_kept(name):
    p = polyhedra.named(name, 30.0)
    lengths, count = dict(zip(p.edges, p.edge_lengths)), len(p.faces)
    # one face of every kind left out, and the first and the last; from the face after it and from the one before
    for left_out in sorted({p.faces_with(sides)[0] for sides in set(map(len, p.faces))} | {0, count - 1}):
        for root in ((left_out + 1) % count, (left_out - 1) % count):
            pattern = unfold.unfold(p, root, [left_out])
            assert pattern.open_faces == (left_out,) and pattern.polygons[left_out] == () and len(pattern.folds) == count - 2
            assert no_two_overlap([polygon for polygon in pattern.polygons if polygon], p.area)
            (loop,) = unfold.outline(pattern)
            assert unfold.polygon_area(loop) == pytest.approx(p.area - p.face_areas[left_out], rel=REL)
            assert pattern.area == pytest.approx(p.area - p.face_areas[left_out], rel=REL)
            # the sides of the face left out are the rim, each on the outline once; every other cut edge twice
            rim = [cut for cut in pattern.cuts if len(cut.segments) == 1]
            assert len(rim) == len(p.faces[left_out]) and all(cut.faces[1] == left_out for cut in rim)
            assert len(pattern.cuts) + len(pattern.folds) == len(p.edges)
            assert len(loop) == sum(len(cut.segments) for cut in pattern.cuts)
            assert walked(loop) == pytest.approx(math.fsum(lengths[cut.edge] * len(cut.segments) for cut in pattern.cuts), rel=REL)


def test_several_faces_left_open_and_what_cannot_be_left_open():
    box = polyhedra.box(100.0, 80.0, 20.0)
    towards = {axis: box.face_towards(direction) for axis, direction in (
        ("+x", (1, 0, 0)), ("-x", (-1, 0, 0)), ("+y", (0, 1, 0)), ("-y", (0, -1, 0)), ("+z", (0, 0, 1)), ("-z", (0, 0, -1)))}
    # the four walls without top and floor: a band, three folds, one upright edge cut, eight edges of rim
    band = unfold.unfold(box, towards["+x"], [towards["+z"], towards["-z"]])
    (loop,) = unfold.outline(band)
    assert band.open_faces == tuple(sorted((towards["+z"], towards["-z"]))) and len(band.folds) == 3
    assert sorted(len(cut.segments) for cut in band.cuts) == [1] * 8 + [2]
    assert unfold.polygon_area(loop) == pytest.approx(2 * 20 * (100 + 80), rel=REL) and sorted(band.size) == pytest.approx([20.0, 360.0])
    # top and one wall: the edge between the two faces left out is nowhere in the pattern
    scoop = unfold.unfold(box, towards["-z"], [towards["+z"], towards["-y"]])
    assert len(scoop.folds) == 3 and len(scoop.cuts) + len(scoop.folds) == 12 - 1
    assert sorted(len(cut.segments) for cut in scoop.cuts) == [1] * 6 + [2] * 2
    assert unfold.polygon_area(unfold.outline(scoop)[0]) == pytest.approx(15200 - 100 * 20, rel=REL)
    # one face alone: no fold, and its own outline
    alone = unfold.unfold(box, towards["-z"], [f for axis, f in towards.items() if axis != "-z"])
    assert alone.folds == () and len(alone.cuts) == 4 and unfold.polygon_area(unfold.outline(alone)[0]) == pytest.approx(8000.0, rel=REL)
    # floor and top without the walls between them are two pieces
    with pytest.raises(unfold.UnfoldError, match="box: without the 4 faces left open the others do not hang together"):
        unfold.unfold(box, towards["-z"], [towards[axis] for axis in ("+x", "-x", "+y", "-y")])
    with pytest.raises(ValueError, match=f"box: face {towards['+z']} is left open, so it cannot be the face laid first"):
        unfold.unfold(box, towards["+z"], [towards["+z"]])
    for wrong in ([6], [-1], ["top"], [1.0]):
        with pytest.raises(ValueError, match="box has no faces .* to leave open"):
            unfold.unfold(box, 0, wrong)


def test_trees_that_do_not_join_the_faces_kept_are_passed_over(monkeypatch):
    p = polyhedra.named("dodecahedron", 30.0)
    # Cutting the steepest edges leaves a tree of all twelve faces. Without one of them the others may fall
    # apart: such a set of folds cannot be laid out, and the breadth-first ones always can.
    laid, apart = 0, 0
    for folds in unfold.candidates(p, 0, [5]):
        try:
            polygons, parents = unfold.lay_out(p, folds, 0, [5])
        except ValueError as exc:
            assert str(exc) == "these folds do not join all the faces"
            apart += 1
            continue
        laid += 1
        assert polygons[5] == () and len(parents) == 10 and all(polygons[f] for f in range(12) if f != 5)
    assert laid >= 11 and apart > 0 and laid + apart == 11 + unfold.STEEPEST_EDGE_DIRECTIONS
    # `unfold` takes the first that can be laid out and lays no face over another
    some = [folds for folds in unfold.candidates(p, 0, [5])]
    first_apart = next(folds for folds in some if len({edge for edge in folds if 5 not in unfold.neighbours(p)[edge]}) < 10)
    monkeypatch.setattr(unfold, "candidates", lambda polyhedron, root=0, open_faces=(): iter([first_apart, some[0]]))
    pattern = unfold.unfold(p, 0, [5])
    assert len(pattern.folds) == 10 and pattern.area == pytest.approx(p.area * 11 / 12, rel=REL)
    monkeypatch.setattr(unfold, "candidates", lambda polyhedron, root=0, open_faces=(): iter([first_apart]))
    with pytest.raises(unfold.UnfoldError, match="every one of the 0 flat patterns tried"):
        unfold.unfold(p, 0, [5])


def test_half_of_a_solid_open_where_it_was_divided():
    p = polyhedra.named("truncated-octahedron", 30.0)
    p = p.resting_on(p.faces_with(6)[0])
    height = max(v[2] for v in p.vertices)
    areas = []
    for normal, root in (((0, 0, 1), (0, 0, -1)), ((0, 0, -1), (0, 0, 1))):
        half = p.clipped(normal, (height / 2) * normal[2])
        cut = half.face_towards(normal)
        pattern = unfold.unfold(half, half.face_towards(root), [cut])
        (loop,) = unfold.outline(pattern)
        assert len(pattern.folds) == 9 and unfold.polygon_area(loop) == pytest.approx(half.area - half.face_areas[cut], rel=REL)
        rim = [cut_edge for cut_edge in pattern.cuts if len(cut_edge.segments) == 1]
        # the rim is the cut's outline: six sides, each across a hexagon where it is one and a half edges wide
        assert len(rim) == 6 and walked(half.polygon(cut)) == pytest.approx(6 * 45.0, rel=REL)
        assert math.fsum(math.dist(*cut_edge.segments[0]) for cut_edge in rim) == pytest.approx(6 * 45.0, rel=REL)
        areas.append(unfold.polygon_area(loop))
    assert sum(areas) == pytest.approx(p.area, rel=REL)                # the two halves are the whole surface


# ---- what of the kernel side needs no kernel --------------------------------------------------------------------

def test_the_kernel_side_can_be_imported_without_a_kernel():
    assert callable(forms.solid) and callable(forms.shell) and callable(forms.frame)
    assert callable(forms.panels) and callable(forms.flat_pattern)


def test_the_volume_of_a_frame_is_bounded_without_a_kernel():
    cube = polyhedra.named("cube", 30.0)
    # nodes as thin as the struts: twelve struts less a half ball at each end, eight balls, and at most that
    most = 12 * (math.pi * 4 * 30 - 2 * (2 / 3) * math.pi * 8) + 8 * (4 / 3) * math.pi * 8
    # three pairs of struts at each corner, at right angles: each pair shares (4/3) r^3 (1 - pi/4) outside the ball
    least = most - 8 * 3 * (4 / 3) * 8 * (1 - math.pi / 4)
    assert forms.frame_volume(cube, 2.0) == pytest.approx((least, most), rel=1e-12)
    assert forms.frame_volume(cube, 2.0, 2.0) == forms.frame_volume(cube, 2.0)
    # struts at right angles part at 2 sqrt(2) from the corner: a node of 3 covers that, and the volume is known
    inside = math.sqrt(9 - 4)
    cap = math.pi * (3 - inside) ** 2 * (6 + inside) / 3
    known = 8 * (4 / 3) * math.pi * 27 + 12 * (math.pi * 4 * (30 - 2 * inside) - 2 * cap)
    assert forms.frame_volume(cube, 2.0, 3.0) == pytest.approx((known, known), rel=1e-12)
    least, most = forms.frame_volume(cube, 2.0, 2.5)               # between the two: the struts still meet outside
    assert least < most


def test_the_sizes_a_frame_refuses():
    octahedron = polyhedra.named("octahedron", 40.0)
    with pytest.raises(ValueError, match="meet at 60 degrees part 4 from the vertex, and the node of radius 4.0 ends there"):
        forms.frame(octahedron, 2.0, 4.0)
    with pytest.raises(ValueError, match="meet at 90 degrees part 2.82842712 from the vertex"):
        forms.frame_volume(octahedron, 2.0, 2.0 * R2)
    least, most = forms.frame_volume(octahedron, 2.0, 3.0)        # covers where struts at 90 degrees part, not at 60
    assert least < most
    least, most = forms.frame_volume(octahedron, 2.0, 4.01)       # a little larger than refused: covers both
    assert least == most
    for radius, node in ((2.0, 1.0), (0.0, None), (-1.0, 3.0)):
        with pytest.raises(ValueError, match="a strut's radius is positive and a node's is no less"):
            forms.frame(octahedron, radius, node)
    with pytest.raises(ValueError, match="nodes of radius 20.0 would touch along its shortest edge, 40 long"):
        forms.frame(octahedron, 2.0, 20.0)
    with pytest.raises(ValueError, match="meet at 60 degrees and, 12.0 thick, run into each other along more than half"):
        forms.frame(octahedron, 12.0)
    # two long edges that cross 1 apart, one above the other
    wedge = polyhedra.from_vertices("wedge", [(-10.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, -10.0, 1.0), (0.0, 10.0, 1.0)])
    assert forms.frame_volume(wedge, 0.4)[0] > 0
    with pytest.raises(ValueError, match="the struts along the edges 0-1 and 2-3, which share no vertex, would run into"):
        forms.frame(wedge, 0.6)
