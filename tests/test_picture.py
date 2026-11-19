"""tools/picture.py: where a camera stands, and pictures made with f3d where it is on PATH with EGL:

    guix shell --pure -m manifest.scm -m .guix/manifest-view.scm -- python3 -B -m pytest -q tests/test_picture.py

and, cut open and coloured, where build123d is there as well (make test-view):

    guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -m .guix/manifest-view.scm -- python3 -B -m pytest -q tests/test_picture.py
"""
import importlib.util
import json
import shutil
import struct
import subprocess
import sys

import pytest
from conftest import REPO

TOOL = REPO / "tools" / "picture.py"
spec = importlib.util.spec_from_file_location("picture_tool", TOOL)
picture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(picture)

F3D = shutil.which("f3d")


def egl():
    if F3D is None:
        return False
    listed = subprocess.run([F3D, "--list-rendering-backends"], capture_output=True, text=True)
    return "egl: available" in listed.stdout + listed.stderr


draws = pytest.mark.skipif(not egl(), reason="f3d with EGL is not on PATH (use .guix/manifest-view.scm)")
cuts = pytest.mark.skipif(not egl() or importlib.util.find_spec("build123d") is None,
                          reason="a cut needs f3d with EGL and build123d (make test-view)")


def run(*args):
    done = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True)
    return done.stdout + done.stderr


def test_a_view_says_where_the_camera_stands():
    assert picture.stands("iso", "+Z") == (1, -1, 0.8)
    assert picture.stands("iso-back", "+Z") == (-1, 1, 0.8)
    assert picture.stands("below", "+Z") == (1, -1, -0.8)
    assert picture.stands("+x", "+Z") == (1, 0, 0) and picture.stands("-Y", "+Z") == (0, -1, 0)
    # with Y up, the two other axes are Z and X: above is +Y
    assert picture.stands("iso", "+Y") == (-1, 0.8, 1)
    assert picture.stands("iso", "-Z")[2] == -0.8
    # straight along the up axis the camera leans a little, so that it has an up: from above against Y, which
    # then runs upwards in the picture with X to the right, a plan as it is drawn; from below towards it
    assert picture.stands("+z", "+Z") == (0, -0.02, 1) and picture.stands("-z", "+Z") == (0, 0.02, -1)
    assert picture.stands("-y", "+Y") == (0.02, -1, 0)
    with pytest.raises(ValueError, match="unknown view"):
        picture.stands("front", "+Z")
    assert [picture.file_name(v) for v in ("iso", "+x", "-Z")] == ["iso", "plus-x", "minus-z"]


def test_where_prints_the_file_and_draws_nothing(project_copy):
    assert run(project_copy, "spacer", "--where").strip() == str(project_copy / "designs/parts/spacer/part.step")
    out = run(project_copy, "fixture-with-spacer", "--where")
    assert "is an assembly and is not built" in out and "[picture] exit status 2" in out


def test_what_cannot_be_drawn_is_said(project_copy):
    assert "exit status 2" in run(project_copy)                                      # no key
    if F3D is None:
        assert "f3d is not on PATH" in run(project_copy, "spacer")
        return
    out = run(project_copy, "washer")
    assert "has no component 'washer'; its keys:" in out and "spacer" in out and "exit status 2" in out
    out = run(project_copy, "fixture-root")
    assert "fixture-root is an assembly and is not built" in out and "exit status 2" in out
    assert "unknown view 'front'" in run(project_copy, "spacer", "--views", "front")


@draws
def test_a_part_is_drawn_from_its_step_file(project_copy, tmp_path):
    out = run(project_copy, "spacer", "--views", "iso,-z", "--size", "400x300")
    assert "[picture] exit status 0" in out, out
    for name in ("spacer-iso.png", "spacer-minus-z.png"):
        png = project_copy / ".cache" / "pictures" / name
        assert png.read_bytes()[:8] == picture.PNG and png.stat().st_size > 1000, name
    # a file by itself, to a directory that is named
    out = run(project_copy / "designs/parts/spacer/part.step", "--views", "below", "--up", "+Y", "--out", tmp_path / "out")
    assert "[picture] exit status 0" in out and (tmp_path / "out" / "part-below.png").read_bytes()[:8] == picture.PNG


def test_a_cut_names_an_axis_a_side_and_a_place():
    assert picture.cut_plane("+y") == (1, 1, None) and picture.cut_plane("y") == (1, 1, None)
    assert picture.cut_plane("-x=12.5") == (0, -1, 12.5) and picture.cut_plane("+Z=-3") == (2, 1, -3.0)
    for wrong in ("front", "+w", "xy", "+y=there"):
        with pytest.raises(ValueError, match="--cut"):
            picture.cut_plane(wrong)


def test_parts_keep_their_colours_and_a_model_is_turned_for_the_viewer():
    first = picture.colours(["plate", "pin", "spacer", "pin"])
    assert sorted(first) == ["pin", "plate", "spacer"] and len(set(first.values())) == 3
    assert picture.colours(["spacer", "plate", "pin"]) == first               # whatever the order they come in
    assert all(0 <= c <= 1 for colour in first.values() for c in colour)
    # a glTF file has Y up: what pointed up along Z points up along Y, and Y points towards the viewer's -Z
    assert picture.to_viewer((0, 0, 1)) == (0, 1, 0) and picture.to_viewer((0, 1, 0)) == (0, 0, -1)
    assert picture.to_viewer((1, 0, 0)) == (1, 0, 0)


def test_a_model_s_materials_are_said_not_to_be_metal(tmp_path):
    """A GLB file: a header, a chunk of JSON padded to four bytes, a chunk of numbers."""
    document = json.dumps({"asset": {"version": "2.0"}, "materials": [
        {"name": "mat_0", "pbrMetallicRoughness": {"baseColorFactor": [0.2, 0.6, 0.8, 1.0]}}, {"name": "bare"}]}).encode()
    document += b" " * (-len(document) % 4)
    numbers = struct.pack("<I4s", 8, b"BIN\0") + bytes(range(8))
    glb = tmp_path / "model.glb"
    glb.write_bytes(struct.pack("<4sII", b"glTF", 2, 20 + len(document) + len(numbers)) + struct.pack("<I4s", len(document), b"JSON")
                    + document + numbers)
    picture.matte(glb)
    data = glb.read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    length, kind = struct.unpack_from("<I4s", data, 12)
    assert (magic, version, total, kind) == (b"glTF", 2, len(data), b"JSON") and length % 4 == 0
    materials = json.loads(data[20:20 + length])["materials"]
    assert [m["pbrMetallicRoughness"]["metallicFactor"] for m in materials] == [0.0, 0.0]
    assert materials[0]["pbrMetallicRoughness"]["baseColorFactor"] == [0.2, 0.6, 0.8, 1.0]
    assert data[20 + length:] == numbers                                      # the numbers are as they were
    (tmp_path / "other.glb").write_bytes(b"not a model at all, whatever its name")
    with pytest.raises(ValueError, match="not a GLB file"):
        picture.matte(tmp_path / "other.glb")


def glb_file(path, materials):
    """A GLB file with those materials: a header, a chunk of JSON padded to four bytes, a chunk of numbers."""
    document = json.dumps({"asset": {"version": "2.0"}, "materials": materials}).encode()
    document += b" " * (-len(document) % 4)
    numbers = struct.pack("<I4s", 8, b"BIN\0") + bytes(range(8))
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 20 + len(document) + len(numbers)) + struct.pack("<I4s", len(document), b"JSON")
                     + document + numbers)
    return numbers


def materials_of(path):
    data = path.read_bytes()
    return json.loads(data[20:20 + struct.unpack_from("<I", data, 12)[0]])["materials"], data


def as_written(colour):
    """A colour as the kernel writes it into a model: counted as light adds up, in single precision."""
    return [struct.unpack("<f", struct.pack("<f", c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4))[0] for c in colour]


def test_a_finish_goes_into_the_model_under_a_colour_that_says_which_it_is():
    seen = set()
    for n in (0, 1, 2, 9, 10, 11, 127, 254, 255, 256, 257, 4000, 65534, 65535, 70000):
        colour = picture.carrier(n)
        assert all(0 <= c <= 1 for c in colour) and colour not in seen
        seen.add(colour)
        assert picture._carried(as_written(colour) + [1.0]) == n          # read back from what the model holds


def test_a_model_s_materials_get_what_the_finishes_say(tmp_path):
    looks = [("aluminium", {"color": "#c8cacd", "metallic": 0.8, "roughness": 0.55, "opacity": 1.0}),
             ("clear-blue", {"color": "#2f6fd0", "metallic": 0.0, "roughness": 0.2, "opacity": 0.4})]
    glb = tmp_path / "model.glb"
    # the kernel writes them in an order of its own, and says of one that lets light through that it does
    numbers = glb_file(glb, [
        {"name": "mat_0", "pbrMetallicRoughness": {"baseColorFactor": as_written(picture.carrier(1)) + [1.0]}, "alphaMode": "BLEND"},
        {"name": "mat_1", "pbrMetallicRoughness": {"baseColorFactor": as_written(picture.carrier(0)) + [1.0]}, "alphaMode": "BLEND"}])
    picture.dress(glb, looks)
    materials, data = materials_of(glb)
    assert [m["name"] for m in materials] == ["clear-blue", "aluminium"]
    blue, aluminium = (m["pbrMetallicRoughness"] for m in materials)
    assert blue["baseColorFactor"] == pytest.approx([0.02843, 0.15896, 0.63076, 0.4], abs=1e-5)
    assert (blue["metallicFactor"], blue["roughnessFactor"]) == (0.0, 0.2) and materials[0]["alphaMode"] == "BLEND"
    assert (aluminium["metallicFactor"], aluminium["roughnessFactor"]) == (0.8, 0.55) and "alphaMode" not in materials[1]
    assert aluminium["baseColorFactor"][3] == 1.0 and data.endswith(numbers)
    # a material that stands for no finish is not guessed at
    glb_file(glb, [{"pbrMetallicRoughness": {"baseColorFactor": as_written(picture.carrier(7)) + [1.0]}}])
    with pytest.raises(ValueError, match="stands for none of the 2 finish"):
        picture.dress(glb, looks)


def test_the_surroundings_are_a_small_image_and_colours_and_finishes_are_one_or_the_other(tmp_path):
    sky = picture.surroundings(tmp_path / "sky.png")
    first = sky.read_bytes()
    assert first[:8] == picture.PNG and struct.unpack_from(">II", first, 16) == (64, 32)
    assert picture.surroundings(tmp_path / "again.png").read_bytes() == first
    assert picture.options(["project", "key", "--finish"])[1]["finish"] is True
    with pytest.raises(ValueError, match="one or the other"):
        picture.options(["project", "key", "--finish", "--colour"])


@cuts
def test_an_assembly_is_drawn_with_the_finishes_the_project_gives_its_parts(project_copy):
    pictures = project_copy / ".cache" / "pictures"
    out = run(project_copy, "fixture-with-spacer", "--finish", "--views", "iso", "--size", "400x300")
    assert "[picture] exit status 0" in out and "no finish" not in out, out
    assert (pictures / "fixture-with-spacer-finish-iso.png").read_bytes()[:8] == picture.PNG
    assert not list(pictures.glob(".*surroundings*"))                         # what the viewer was shown round it is gone
    materials = {m["name"]: m for m in materials_of(pictures / "fixture-with-spacer-finish.glb")[0]}
    assert sorted(materials) == ["aluminium", "clear-blue", "grey-plastic"]   # the pin has the file's default
    assert materials["aluminium"]["pbrMetallicRoughness"]["metallicFactor"] == 0.8
    assert materials["clear-blue"]["alphaMode"] == "BLEND"
    assert materials["clear-blue"]["pbrMetallicRoughness"]["baseColorFactor"][3] == 0.4
    assert "alphaMode" not in materials["grey-plastic"]
    assert not (project_copy / ".cache" / "assemblies").exists()              # nothing was built for it
    # a part by itself has its finish, whatever its solids; cut open as well
    out = run(project_copy, "spacer", "--finish", "--cut", "-x=0", "--views", "-x", "--size", "400x300")
    assert "[picture] exit status 0" in out, out
    assert [m["name"] for m in materials_of(pictures / "spacer-cut-minus-x-finish.glb")[0]] == ["clear-blue"]
    # a part the project gives no finish is drawn plain, and the tool says which
    text = (project_copy / "finishes.toml").read_text().replace('default = "grey-plastic"', "")
    (project_copy / "finishes.toml").write_text(text)
    out = run(project_copy, "fixture-with-spacer", "--finish", "--views", "iso", "--size", "400x300")
    assert "1 part(s) have no finish and are drawn plain: pin" in out and "[picture] exit status 0" in out, out
    assert "no finish" in [m["name"] for m in materials_of(pictures / "fixture-with-spacer-finish.glb")[0]]
    # and a project without the file, or a file by itself, has no finishes to draw with
    (project_copy / "finishes.toml").unlink()
    out = run(project_copy, "fixture-with-spacer", "--finish")
    assert "finishes.toml is not there" in out and "exit status 2" in out, out
    out = run(project_copy / "designs/parts/spacer/part.step", "--finish")
    assert "a file by itself has no finishes" in out and "exit status 2" in out, out


@cuts
def test_an_assembly_is_cut_open_and_coloured_without_being_built(project_copy):
    pictures = project_copy / ".cache" / "pictures"

    def materials(name):
        glb = (pictures / name).read_bytes()
        return json.loads(glb[20:20 + struct.unpack_from("<I", glb, 12)[0]])["materials"]

    out = run(project_copy, "fixture-with-spacer", "--colour", "--views", "iso", "--size", "400x300")
    assert "[picture] exit status 0" in out, out
    assert (pictures / "fixture-with-spacer-colour-iso.png").read_bytes()[:8] == picture.PNG
    # the fixture's parts: a base plate, a pin placed twice in the same colour, a spacer
    whole = materials("fixture-with-spacer-colour.glb")
    assert len(whole) == 3 and all(m["pbrMetallicRoughness"]["metallicFactor"] == 0.0 for m in whole)
    assert not (project_copy / ".cache" / "assemblies").exists()              # nothing was built for it
    # cut open, seen from the side that was taken away; what is left has the colours it had
    out = run(project_copy, "fixture-with-spacer", "--cut", "+y", "--colour", "--views", "+y", "--size", "400x300")
    assert "[picture] exit status 0" in out, out
    assert (pictures / "fixture-with-spacer-cut-plus-y-colour-plus-y.png").read_bytes()[:8] == picture.PNG
    colours = [m["pbrMetallicRoughness"]["baseColorFactor"] for m in whole]
    left = materials("fixture-with-spacer-cut-plus-y-colour.glb")
    assert 1 <= len(left) <= 3 and all(m["pbrMetallicRoughness"]["baseColorFactor"] in colours for m in left)
    # a part by itself, cut at a place that is named; and a cut that leaves nothing
    out = run(project_copy, "spacer", "--cut", "-x=0", "--views", "-x", "--size", "400x300")
    assert "[picture] exit status 0" in out and (pictures / "spacer-cut-minus-x-minus-x.png").is_file(), out
    assert "the cut takes everything away" in run(project_copy, "spacer", "--cut", "+x=-500")
    assert "--cut 'sideways'" in run(project_copy, "spacer", "--cut", "sideways")
