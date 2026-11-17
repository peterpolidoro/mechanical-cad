"""A polyhedron as shapes of build123d: solid, shell, frame, panels and flat pattern.

    from mechanical_cad.shapes import forms, polyhedra

    def build(parameters):
        p = polyhedra.named("truncated-octahedron", edge=parameters["edge_mm"])
        p = p.resting_on(p.faces_with(6)[0])
        return forms.shell(p, parameters["wall_mm"], open_faces=[p.face_towards((0, 0, 1))])

`solid`, `shell` and `frame` return one solid, which a part's `build.py` can return as it is
(tools/build_part.py). `panels` returns a list of solids, one for each face, and `flat_pattern` a list of faces
and a list of edges; `Compound(children=...)` of build123d makes one shape of a list.

build123d is imported when a function is called, not when this module is: the module can be imported where no
kernel is installed. The polyhedron itself, its sizing and the corners of its panels and of its flat pattern are
worked out without a kernel (polyhedra.py, unfold.py); the kernel makes the solids, cuts and joins.

Nothing the kernel makes is returned unchecked. A solid, a shell and a panel have to be one valid solid of the
volume worked out without a kernel, and a frame one within the bounds of `frame_volume`, which needs no kernel
either; a `ValueError` says what came out instead.
"""
from __future__ import annotations

import math
from itertools import combinations

from . import unfold as _unfold
from .polyhedra import TOLERANCE, add, dot, norm, sub, times, unit

# How near the kernel's figure for a volume has to be to the one worked out here. With plane faces the two
# agreed to 1e-14 in trials, on solids at the origin; a wrong cut or union is out by far more than either bound.
# With round faces the kernel's figure is good to a few parts in a million: the same frame joined in two ways
# differed by 3e-6 of its volume.
PLANE_VOLUME_REL = 1e-6
FRAME_VOLUME_REL = 1e-4
# A node whose surface passes within this fraction of its radius of the point where two struts part is refused.
FRAME_NEAR_PARTING = 1e-4


def _face(points):
    from build123d import Face, Vector, Wire

    return Face(Wire.make_polygon([Vector(*p) for p in points], close=True))


def _held(shape, volume, what, rel=PLANE_VOLUME_REL):
    """The one solid of what the kernel made, if it is one valid solid of the volume worked out without a kernel."""
    solids = shape.solids()
    if len(solids) != 1 or not solids[0].is_valid or abs(solids[0].volume - volume) > rel * volume:
        found = " + ".join(f"{one.volume:.9g}" for one in solids) or "nothing"
        raise ValueError(f"{what}: the kernel did not make one valid solid of the volume {volume:.9g}; what came "
                         f"out has the volume {found}")
    return solids[0]


def solid(polyhedron):
    """The polyhedron as one solid: a plane face for each of its faces, sewn into a closed shell."""
    from build123d import Shell, Solid

    return _held(Solid(Shell([_face(polyhedron.polygon(f)) for f in range(len(polyhedron.faces))])),
                 polyhedron.volume, polyhedron.name)


def shell(polyhedron, wall, open_faces=()):
    """The polyhedron hollowed out, with a wall of the same thickness at every face.

    The cavity is the polyhedron with every face moved inward by `wall`, measured square to the face. It is cut
    from the solid with one plane for each face, so it is not a scaled copy: where faces are at different
    distances from the centre a scaled copy would give them walls of different thickness. `wall` has to be less
    than the polyhedron's `inradius`.

    `open_faces` lists the indices of faces to open. An open face keeps its wall except over the inner face: the
    opening is the inner face (the face of the cavity that lies `wall` behind the open face) moved straight out
    through the wall, a hole with sides square to the face and as large as the cavity is there. The rim left
    around it is where the walls of the neighbouring faces end. A face whose inner face has vanished, because
    the wall is thick enough for its neighbours to meet behind it, cannot be opened.

    The result is held to the volume worked out without a kernel: the solid less `polyhedron.inset(wall)`, less
    the area of the inner face times the wall for each open face. Anything else is a `ValueError`.
    """
    from build123d import Keep, Plane, Solid, Vector

    if not 0.0 < wall < polyhedron.inradius:
        raise ValueError(f"{polyhedron.name}: the wall has to be more than 0 and less than the inradius "
                         f"{polyhedron.inradius:.6g}, not {wall!r}")
    outer = solid(polyhedron)
    cavity = outer
    for n, d in zip(polyhedron.normals, polyhedron.distances):
        cavity = cavity.split(Plane(origin=times(n, d - wall), z_dir=n), keep=Keep.BOTTOM)
    hollow = polyhedron.inset(wall)
    result, volume = outer - cavity, polyhedron.volume - hollow.volume
    near = TOLERANCE * polyhedron.circumradius * 1e3               # well above what the cuts leave, far below a wall
    for f in sorted(set(open_faces)):
        n, d = polyhedron.normals[f], polyhedron.distances[f]
        inner = [face for face in cavity.faces()
                 if abs(dot(n, tuple(face.center())) - (d - wall)) < near and dot(n, tuple(face.normal_at())) > 0.5]
        if len(inner) != 1:
            raise ValueError(f"{polyhedron.name}: face {f} has no inner face behind a wall of {wall!r}")
        result = result - Solid.extrude(inner[0], Vector(*n) * (2.0 * wall))    # past the outer face, into the open
        volume -= hollow.face_areas[hollow.face_towards(n)] * wall
    return _held(result, volume, f"the shell of {polyhedron.name}")


def _apart(p1, q1, p2, q2):
    """The least distance between the segment from p1 to q1 and the segment from p2 to q2."""
    d1, d2, r = sub(q1, p1), sub(q2, p2), sub(p1, p2)
    a, e, b, c, f = dot(d1, d1), dot(d2, d2), dot(d1, d2), dot(d1, r), dot(d2, r)
    across = a * e - b * b                                         # zero when the two are parallel
    s = min(1.0, max(0.0, (b * f - c * e) / across)) if across > 1e-12 * a * e else 0.0
    t = (b * s + f) / e
    if not 0.0 <= t <= 1.0:
        t = min(1.0, max(0.0, t))
        s = min(1.0, max(0.0, (b * t - c) / a))
    return norm(sub(add(p1, times(d1, s)), add(p2, times(d2, t))))


def _leaving(polyhedron):
    """{vertex: [(the vertex at the other end of an edge, the unit direction of that edge away from the vertex)]}."""
    leaving = {}
    for a, b in polyhedron.edges:
        along = unit(sub(polyhedron.vertices[b], polyhedron.vertices[a]))
        leaving.setdefault(a, []).append((b, along))
        leaving.setdefault(b, []).append((a, times(along, -1.0)))
    return leaving


def frame_volume(polyhedron, radius, node_radius=None):
    """(least, most): two bounds on the volume of `frame`, worked out without a kernel.

    `most` is the balls and, of every strut, what is outside the two balls at its ends. `least` is that without
    what two struts at one vertex have in common outside the ball of a strut's radius; where the node covers the
    place where they part they have nothing in common outside it. With nodes that cover every such place the
    two bounds are the same number, the volume itself.

    The sizes `frame` refuses are refused here, with a `ValueError` that says which: see there.
    """
    node = radius if node_radius is None else node_radius
    if not 0.0 < radius <= node:
        raise ValueError(f"a strut's radius is positive and a node's is no less: got {radius!r} and {node!r}")
    vertices, name = polyhedron.vertices, polyhedron.name
    if min(polyhedron.edge_lengths) <= 2.0 * node:
        raise ValueError(f"{name}: nodes of radius {node!r} would touch along its shortest edge, "
                         f"{min(polyhedron.edge_lengths):.6g} long")
    for (a, b), (c, d) in combinations(polyhedron.edges, 2):
        if len({a, b, c, d}) == 4 and _apart(vertices[a], vertices[b], vertices[c], vertices[d]) <= 2.0 * node:
            raise ValueError(f"{name}: the struts along the edges {a}-{b} and {c}-{d}, which share no vertex, "
                             f"would run into each other or into each other's nodes")
    inside = math.sqrt(node * node - radius * radius)              # how far along a strut its node reaches
    cap = math.pi * (node - inside) ** 2 * (2.0 * node + inside) / 3.0
    most = (len(vertices) * 4.0 / 3.0 * math.pi * node ** 3
            + math.fsum(math.pi * radius ** 2 * (length - 2.0 * inside) - 2.0 * cap for length in polyhedron.edge_lengths))
    shared = 0.0
    for vertex, edges in _leaving(polyhedron).items():
        for (b, u), (c, v) in combinations(edges, 2):
            half = math.acos(max(-1.0, min(1.0, dot(u, v)))) / 2.0
            parting = radius / math.sin(half)                      # how far from the vertex the two struts part
            if 2.0 * radius / math.tan(half) >= min(norm(sub(vertices[b], vertices[vertex])),
                                                    norm(sub(vertices[c], vertices[vertex]))):
                raise ValueError(f"{name}: the struts along the edges {vertex}-{b} and {vertex}-{c} meet at "
                                 f"{math.degrees(2.0 * half):.6g} degrees and, {radius!r} thick, run into each "
                                 f"other along more than half of the shorter")
            if abs(node - parting) <= FRAME_NEAR_PARTING * parting:
                raise ValueError(
                    f"{name}: two struts of radius {radius!r} that meet at {math.degrees(2.0 * half):.6g} degrees part "
                    f"{parting:.9g} from the vertex, and the node of radius {node!r} ends there: the kernel does "
                    f"not join that reliably. Make the node a little larger or smaller.")
            if parting > node:
                shared += 4.0 / 3.0 * radius ** 3 * (1.0 / math.tan(half) - (math.pi / 2.0 - half))
    return most - shared, most


def frame(polyhedron, radius, node_radius=None):
    """The edges of the polyhedron as round struts of that radius and its vertices as balls, joined into one solid.

    The axis of a strut is the edge, from vertex to vertex. A ball has `node_radius`, the strut's radius when
    none is given, which rounds the ends of the struts where they meet.

    Refused, with a `ValueError` that says which: a node thinner than a strut; nodes that would touch along an
    edge; struts that share no vertex and would run into each other; struts at one vertex so thick for their
    angle that they run into each other along more than half of the shorter; and a node that ends where two of
    its struts part, at radius / sin(half the angle between them) from the vertex (twice the strut's radius
    for struts at 60 degrees, 1.414 times at 90).

    How it is made. Cylinders and balls joined as they are came out wrong in trials, in some positions of the
    solid and not in others: several solids, none, or one with material missing. A ball as thin as its struts
    touches each of them along a circle, and two struts touch each other at two points of that circle, which
    the kernel has to find. So nothing is left to find. Each strut is cut, at each end, by the planes halfway
    between it and the other struts of that vertex: what is cut off lies inside those struts. A ball as thin as
    the struts is cut by the plane through its centre across each strut, which leaves the part behind all of
    them. These pieces fill the frame, have no volume in common and meet only in flat faces, along which they
    are joined. A larger ball is left whole and joined to the struts, which it crosses in plain circles.

    What comes out is held to `frame_volume`: one valid solid whose volume is within those bounds, or a
    `ValueError`. The bounds are the same number where the nodes cover the places where struts part, and a few
    per cent apart with nodes as thin as the struts.
    """
    least, most = frame_volume(polyhedron, radius, node_radius)

    from build123d import Cylinder, Keep, Plane, Sphere, Vector

    node_radius = radius if node_radius is None else node_radius
    vertices, leaving = polyhedron.vertices, _leaving(polyhedron)
    struts = []
    for a, b in polyhedron.edges:
        start, end = Vector(*vertices[a]), Vector(*vertices[b])
        strut = Plane(origin=(start + end) / 2, z_dir=end - start) * Cylinder(radius, (end - start).length)
        for here, there in ((a, b), (b, a)):
            own = next(along for other, along in leaving[here] if other == there)
            for other, along in leaving[here]:
                if other != there:                                 # keep what is nearer to this strut's direction
                    strut = strut.split(Plane(origin=vertices[here], z_dir=sub(along, own)), keep=Keep.BOTTOM)
        struts.append(strut)
    balls = []
    for vertex, edges in leaving.items():
        # the two poles of the kernel's ball lie on the line through the centre of the solid, which no edge follows
        ball = Plane(origin=vertices[vertex], z_dir=sub(vertices[vertex], polyhedron.centre)) * Sphere(node_radius)
        if node_radius == radius:
            for _, along in edges:                                 # keep what is behind every strut
                ball = ball.split(Plane(origin=vertices[vertex], z_dir=along), keep=Keep.BOTTOM)
        balls.append(ball)
    if node_radius == radius:
        joined = struts[0].fuse(*struts[1:], *balls, glue=True)
    else:
        joined = struts[0].fuse(*struts[1:], glue=True).fuse(*balls)
    solids = joined.solids()
    if (len(solids) != 1 or not solids[0].is_valid
            or not least * (1.0 - FRAME_VOLUME_REL) <= solids[0].volume <= most * (1.0 + FRAME_VOLUME_REL)):
        found = " + ".join(f"{one.volume:.6g}" for one in solids) or "nothing"
        raise ValueError(f"{polyhedron.name}: the kernel did not join struts of radius {radius!r} and nodes of radius "
                         f"{node_radius!r} into one valid solid with a volume from {least:.6g} to {most:.6g}; "
                         f"what came out has the volume {found}. Change one of the radii a little.")
    return solids[0]


def panels(polyhedron, thickness):
    """One plate for each face, in the order of the faces: `polyhedron.panel(face, thickness)` as a solid.

    A plate is the part of the solid within `thickness` of its face and no nearer to any other face, so its
    sides lie in the planes that halve the angles to its neighbours: mitres. Together the plates are the closed
    shell of that wall, and no two share more than a side. The corners are worked out in polyhedra.py from all
    the faces, not only the neighbours across an edge: where more than three faces meet at a vertex the plates of
    two faces that share only that vertex can meet in a small facet.
    """
    return [solid(panel) for panel in polyhedron.panels(thickness)]


def flat_pattern(polyhedron, root=0):
    """The flat pattern of the polyhedron in the XY plane: (faces, folds).

    `faces` has one plane face of build123d for each face of the polyhedron, in their order, seen from outside
    the solid when looking down -Z. `folds` has one edge for each fold line, in the order of the `folds` of
    `unfold.unfold(polyhedron, root)`, which says what the pattern is and gives the angle of each fold.
    """
    from build123d import Edge

    pattern = _unfold.unfold(polyhedron, root)
    faces = [_face([(x, y, 0.0) for x, y in polygon]) for polygon in pattern.polygons]
    folds = [Edge.make_line((ax, ay, 0.0), (bx, by, 0.0)) for (ax, ay), (bx, by) in (f.segment for f in pattern.folds)]
    return faces, folds
