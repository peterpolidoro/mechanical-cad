"""Polyhedra as solids, shells, frames, panels and flat patterns of build123d, measured by the kernel and held to
what tests/test_polyhedra.py establishes without one. Run where build123d is installed:

    guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -- python3 -B -m pytest -q tests/test_shape_forms.py
"""
import importlib.util
import json
import math
import shutil
import subprocess
from functools import lru_cache
from itertools import combinations

import pytest
from conftest import REPO, write_json

from mechanical_cad.shapes import forms, polyhedra, unfold
from mechanical_cad.shapes.polyhedra import add, dot, norm, sub, times

pytestmark = pytest.mark.skipif(importlib.util.find_spec("build123d") is None,
                                reason="build123d is not in this environment (make test-build123d)")
FREECAD = shutil.which("FreeCADCmd")
REL = 1e-9
WALL = 3.0


def resting_truncated_octahedron():
    p = polyhedra.named("truncated-octahedron", 30.0)
    return p.resting_on(p.faces_with(6)[0])


# The solid docs/direction.md names, not centred and turned: it rests on a hexagon. Two solids with four faces at
# a vertex, one of them with faces at two distances from the centre. One with sharp angles between its faces. And
# a plain box.
SHAPES = [resting_truncated_octahedron(), polyhedra.named("cuboctahedron", 30.0), polyhedra.named("octahedron", 40.0),
          polyhedra.named("tetrahedron", 50.0), polyhedra.box(100.0, 80.0, 20.0)]
every = pytest.mark.parametrize("p", SHAPES, ids=[p.name for p in SHAPES])


@lru_cache(maxsize=None)
def closed_shell(p):
    return forms.shell(p, WALL)


@lru_cache(maxsize=None)
def plain_frame(p):
    return forms.frame(p, 2.0)


def one_valid_solid(shape):
    return len(shape.solids()) == 1 and shape.is_valid


def volume_in_common(one, other):
    common = one.intersect(other)
    return sum(shape.volume for shape in common) if common else 0.0


def under(p, face, depth):
    """The point `depth` under the middle of a face."""
    return sub(p.face_centres[face], times(p.normals[face], depth))


@every
def test_the_solid_is_valid_and_has_the_volume_and_area_worked_out_without_a_kernel(p):
    solid = forms.solid(p)
    assert one_valid_solid(solid) and len(solid.faces()) == len(p.faces)
    assert solid.volume == pytest.approx(p.volume, rel=REL) and solid.area == pytest.approx(p.area, rel=REL)
    box = solid.bounding_box()
    assert tuple(box.min) == pytest.approx(tuple(min(v[c] for v in p.vertices) for c in range(3)), abs=1e-6)
    assert tuple(box.max) == pytest.approx(tuple(max(v[c] for v in p.vertices) for c in range(3)), abs=1e-6)
    assert tuple(solid.center()) == pytest.approx(p.centre, abs=1e-6)


@every
def test_the_shell_has_the_same_wall_at_every_face(p):
    shell = closed_shell(p)
    assert one_valid_solid(shell) and len(shell.faces()) == 2 * len(p.faces)
    # what was cut out is the solid with every face moved in by the wall, which is not a scaled copy
    assert p.volume - shell.volume == pytest.approx(p.inset(WALL).volume, rel=REL)
    planes = [(tuple(face.normal_at()), dot(tuple(face.normal_at()), tuple(face.center()))) for face in shell.faces()]
    for f, (n, d) in enumerate(zip(p.normals, p.distances)):
        # an outer face in the plane of the face, and an inner one, facing the cavity, a wall behind it
        assert sum(norm(sub(m, n)) < 1e-9 and abs(e - d) < 1e-7 for m, e in planes) == 1
        assert sum(norm(add(m, n)) < 1e-9 and abs(-e - (d - WALL)) < 1e-7 for m, e in planes) == 1
        assert shell.is_inside(under(p, f, WALL - 0.01)) and not shell.is_inside(under(p, f, WALL + 0.01))
    assert not shell.is_inside(p.centre)


def test_the_cavity_of_a_solid_with_faces_at_two_distances_is_not_a_scaled_copy():
    p = polyhedra.named("cuboctahedron", 30.0)
    cavity = p.volume - closed_shell(p).volume
    factor = 1 - WALL / p.inradius                                 # the scale that moves the nearest faces in by the wall
    assert cavity > p.volume * factor ** 3 * 1.01                  # the others would have moved further


@every
def test_an_open_face_is_a_hole_the_size_of_the_inner_face_and_square_to_it(p):
    top = p.face_towards((0, 0, 1))
    cavity = p.inset(WALL)
    inner = cavity.face_towards(p.normals[top])
    opened = forms.shell(p, WALL, open_faces=[top])
    assert one_valid_solid(opened)
    assert closed_shell(p).volume - opened.volume == pytest.approx(cavity.face_areas[inner] * WALL, rel=REL)
    # the inner face is gone and the hole has a side for each of its edges, which is one face with the
    # neighbouring inner wall where that wall is square to the open face, as in a box
    around = [g for (a, b), (f, g) in unfold.neighbours(cavity).items() if f == inner]
    square = sum(abs(dot(cavity.normals[g], cavity.normals[inner])) < 1e-9 for g in around)
    assert len(opened.faces()) == 2 * len(p.faces) - 1 + len(around) - square
    assert closed_shell(p).is_inside(under(p, top, WALL / 2)) and not opened.is_inside(under(p, top, WALL / 2))
    # the hole's sides stand on the inner face's edges: just inside a corner it is open, just outside it is wall
    middle = cavity.face_centres[inner]
    for corner in cavity.polygon(inner):
        out = add(corner, times(p.normals[top], WALL / 2))
        assert not opened.is_inside(add(out, times(sub(middle, corner), 0.02)))
        assert opened.is_inside(add(out, times(sub(middle, corner), -0.02)))
    for f in range(len(p.faces)):                                  # and every other wall is whole
        if f != top:
            assert opened.is_inside(under(p, f, WALL / 2))


def test_several_faces_can_be_open_and_a_face_with_no_inner_face_cannot():
    p = resting_truncated_octahedron()
    top, side = p.face_towards((0, 0, 1)), p.faces_with(4)[0]
    cavity = p.inset(WALL)
    opened = forms.shell(p, WALL, open_faces=[top, side])
    assert one_valid_solid(opened)
    gone = sum(cavity.face_areas[cavity.face_towards(p.normals[f])] for f in (top, side)) * WALL
    assert closed_shell(p).volume - opened.volume == pytest.approx(gone, rel=REL)
    assert not opened.is_inside(under(p, top, WALL / 2)) and not opened.is_inside(under(p, side, WALL / 2))

    thick = polyhedra.named("truncated-cube", 30.0)
    wall = 0.6 * thick.inradius                                    # the octagons meet behind the triangles
    assert len(thick.inset(wall).faces) == 6
    assert one_valid_solid(forms.shell(thick, wall, open_faces=[thick.faces_with(8)[0]]))
    with pytest.raises(ValueError, match="has no inner face behind a wall"):
        forms.shell(thick, wall, open_faces=[thick.faces_with(3)[0]])
    for wall in (0.0, thick.inradius):
        with pytest.raises(ValueError, match="less than the inradius"):
            forms.shell(thick, wall)


@every
def test_the_frame_is_one_valid_solid_along_every_edge(p):
    radius = 2.0
    frame = plain_frame(p)
    assert one_valid_solid(frame)
    assert all(frame.is_inside(v) for v in p.vertices)
    assert all(frame.is_inside(times(add(p.vertices[a], p.vertices[b]), 0.5)) for a, b in p.edges)
    assert not frame.is_inside(p.centre) and not any(frame.is_inside(c) for c in p.face_centres)
    box = frame.bounding_box()
    assert tuple(box.min) == pytest.approx(tuple(min(v[c] for v in p.vertices) - radius for c in range(3)), abs=1e-6)
    assert tuple(box.max) == pytest.approx(tuple(max(v[c] for v in p.vertices) + radius for c in range(3)), abs=1e-6)
    least, most = forms.frame_volume(p, radius)                    # struts share what is near a vertex
    assert least < frame.volume < most and most - least < 0.04 * most


def test_the_frame_is_the_same_wherever_the_solid_lies():
    # cylinders and balls joined as they are came out with material missing for the solid resting on a hexagon and
    # whole for the same solid centred: the frame is made of pieces that meet in flat faces instead (forms.frame)
    resting, centred = resting_truncated_octahedron(), polyhedra.named("truncated-octahedron", 30.0)
    assert forms.frame_volume(resting, 2.0) == pytest.approx(forms.frame_volume(centred, 2.0), rel=1e-12)
    assert plain_frame(resting).volume == pytest.approx(plain_frame(centred).volume, rel=1e-5)
    assert len(plain_frame(resting).faces()) == len(plain_frame(centred).faces())


def test_with_nodes_that_cover_where_the_struts_part_the_volume_is_known_without_a_kernel():
    # struts of radius 2 at 60 and at 90 degrees part 4 and 2.83 from the vertex; struts at 90 and 120, 2.83 and 2.31
    for p, node in ((polyhedra.named("octahedron", 40.0), 5.0), (resting_truncated_octahedron(), 3.0)):
        least, most = forms.frame_volume(p, 2.0, node)
        assert least == most
        knobbed = forms.frame(p, 2.0, node_radius=node)
        assert one_valid_solid(knobbed) and knobbed.volume == pytest.approx(most, rel=1e-5)
        outward = times(sub(p.vertices[0], p.centre), 1 / norm(sub(p.vertices[0], p.centre)))
        assert knobbed.is_inside(add(p.vertices[0], times(outward, node - 0.1)))
        assert not knobbed.is_inside(add(p.vertices[0], times(outward, node + 0.1)))
        assert not plain_frame(p).is_inside(add(p.vertices[0], times(outward, node - 0.1)))


@every
def test_the_panels_are_the_closed_shell_in_as_many_pieces_as_faces(p):
    panels = forms.panels(p, WALL)
    shell = closed_shell(p)
    assert len(panels) == len(p.faces) and all(one_valid_solid(panel) for panel in panels)
    assert sum(panel.volume for panel in panels) == pytest.approx(shell.volume, rel=REL)
    for f, panel in enumerate(panels):                             # each lies under its own face
        assert panel.is_inside(under(p, f, WALL / 2))
        assert panel.volume == pytest.approx(p.panel(f, WALL).volume, rel=REL)
    # no two have volume in common: a mitre is a shared side, not an overlap
    assert all(volume_in_common(a, b) == 0.0 for a, b in combinations(panels, 2))
    assert volume_in_common(panels[0], shell) == pytest.approx(panels[0].volume, rel=1e-7)   # which this would see
    # and joined they are the shell
    joined = panels[0].fuse(*panels[1:])
    assert joined.volume == pytest.approx(shell.volume, rel=REL)
    assert volume_in_common(joined, shell) == pytest.approx(shell.volume, rel=1e-7)


@every
def test_the_flat_pattern_has_the_area_of_the_surface_and_lies_in_one_plane(p):
    faces, folds = forms.flat_pattern(p)
    pattern = unfold.unfold(p)
    assert len(faces) == len(p.faces) and len(folds) == len(p.faces) - 1
    assert all(face.is_valid for face in faces)
    assert sum(face.area for face in faces) == pytest.approx(p.area, rel=REL)
    assert sum(face.area for face in faces) == pytest.approx(forms.solid(p).area, rel=REL)
    for face, area in zip(faces, p.face_areas):
        assert face.area == pytest.approx(area, rel=REL)
        assert tuple(face.normal_at()) == pytest.approx((0.0, 0.0, 1.0), abs=1e-9)   # seen from outside the solid
    joined = faces[0].fuse(*faces[1:])                             # no face lies over another
    assert joined.area == pytest.approx(p.area, rel=REL)
    box = joined.bounding_box()
    assert tuple(box.min) == pytest.approx((0.0, 0.0, 0.0), abs=1e-6)
    assert tuple(box.max) == pytest.approx(pattern.size + (0.0,), abs=1e-6)
    for edge, fold in zip(folds, pattern.folds):
        assert edge.length == pytest.approx(norm(sub(*(p.vertices[i] for i in fold.edge))), rel=REL)
        assert joined.distance_to(edge.center()) < 1e-6            # a fold line runs inside the pattern


ENCLOSURE = '''"""A truncated octahedron as an enclosure: it rests on a hexagon and the hexagon on top is open."""


def build(parameters):
    from mechanical_cad.shapes import forms, polyhedra

    p = polyhedra.named("truncated-octahedron", edge=parameters["edge_mm"])
    p = p.resting_on(p.faces_with(6)[0])
    return forms.shell(p, parameters["wall_mm"], open_faces=[p.face_towards((0, 0, 1))])
'''


@pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd is not on PATH (use the CAD role)")
def test_a_part_whose_program_uses_the_shapes_is_built_by_the_build_tool(tmp_path):
    part = tmp_path / "project" / "designs" / "parts" / "enclosure"
    part.mkdir(parents=True)
    (part / "build.py").write_text(ENCLOSURE, encoding="utf-8")
    write_json(part / "parameters.json", {"name": "Enclosure", "edge_mm": 30.0, "wall_mm": WALL})
    p = resting_truncated_octahedron()
    height = max(v[2] for v in p.vertices)
    write_json(part / "checks.json", {"schema_version": 1, "checks": [
        {"id": "one-solid", "fact": "solids", "equals": 1},
        {"id": "floor", "point": [0.0, 0.0, WALL / 2], "is": "material"},
        {"id": "cavity", "point": [0.0, 0.0, height / 2], "is": "empty"},
        {"id": "open-top", "point": [0.0, 0.0, height - WALL / 2], "is": "empty"}]})
    proc = subprocess.run([FREECAD, str(REPO / "tools" / "build_part.py"), "--pass", str(part)], capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    assert "re-import ok" in out and "4 check(s)" in out and "FAILED" not in out, out
    assert "[build_part] exit status 0" in out, out
    facts = json.loads((part / "facts.json").read_text())
    cavity = p.inset(WALL)
    expected = p.volume - cavity.volume - cavity.face_areas[cavity.face_towards((0, 0, 1))] * WALL
    assert facts["solids"] == 1 and facts["volume_mm3"] == pytest.approx(expected, rel=1e-9)
    assert facts["bounding_box_mm"]["min"][2] == pytest.approx(0.0, abs=1e-6)
    assert facts["bounding_box_mm"]["max"][2] == pytest.approx(height, abs=1e-6)
