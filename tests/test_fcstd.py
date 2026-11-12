"""The view data added to a FreeCAD document that was saved without a window; no kernel needed."""
import math
import xml.etree.ElementTree as ET
import zipfile

import pytest

from mechanical_cad import fcstd

SHOWN = {"occ_0000": True, "asm_000": True, "part_000": False, "definitions": False}


def document(path, members=("Document.xml", "part_000.Shape.brp")):
    """A zip archive with the members a FreeCAD document saved without a window has."""
    with zipfile.ZipFile(path, "w") as archive:
        for name in members:
            archive.writestr(name, b"<Document/>" if name.endswith(".xml") else b"shape")
    return path


def test_the_view_data_are_appended_after_what_the_document_names(tmp_path):
    path = document(tmp_path / "a.FCStd")
    assert fcstd.read_view(path) is None
    fcstd.write_view(path, SHOWN, expanded={"asm_000"}, camera="OrthographicCamera { height 3 }")
    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == ["Document.xml", "part_000.Shape.brp", "GuiDocument.xml"]   # read in one pass
        assert archive.read("part_000.Shape.brp") == b"shape" and archive.testzip() is None
        root = ET.fromstring(archive.read("GuiDocument.xml"))
    assert fcstd.read_view(path) == SHOWN
    assert root.tag == "Document" and root.get("SchemaVersion") == "1"
    providers = root.find("ViewProviderData")
    assert providers.get("Count") == "4" and len(providers) == 4
    assert {p.get("name"): p.get("expanded") for p in providers} == {"occ_0000": "0", "asm_000": "1", "part_000": "0",
                                                                     "definitions": "0"}
    for provider in providers:                      # only what decides whether an object is drawn
        properties = provider.find("Properties")
        assert properties.get("Count") == "2" and [p.get("name") for p in properties] == ["DisplayMode", "Visibility"]
    assert root.find("Camera").get("settings") == "OrthographicCamera { height 3 }"


def test_a_file_is_given_view_data_once_and_only_a_freecad_document(tmp_path):
    path = document(tmp_path / "a.FCStd")
    fcstd.write_view(path, SHOWN)
    with pytest.raises(fcstd.FcstdError, match="has view data already"):
        fcstd.write_view(path, SHOWN)
    with pytest.raises(fcstd.FcstdError, match="not a FreeCAD document"):
        fcstd.write_view(document(tmp_path / "b.FCStd", members=("other.txt",)), SHOWN)
    (tmp_path / "c.FCStd").write_bytes(b"not a zip archive")
    with pytest.raises(fcstd.FcstdError):
        fcstd.write_view(tmp_path / "c.FCStd", SHOWN)
    with pytest.raises(fcstd.FcstdError, match="expanded but not listed: whole"):
        fcstd.view_xml(SHOWN, expanded={"whole"})


def test_a_name_is_written_so_that_it_reads_back(tmp_path):
    path = document(tmp_path / "a.FCStd")
    fcstd.write_view(path, {'a"b<c&d': True})
    assert fcstd.read_view(path) == {'a"b<c&d': True}


def numbers(camera, field, count):
    words = camera.split()
    at = words.index(field)
    return [float(w) for w in words[at + 1:at + 1 + count]]


def test_the_camera_looks_at_the_middle_of_the_box_from_the_isometric_direction():
    box = (-100.0, 0.0, 50.0, 300.0, 200.0, 2650.0)
    camera = fcstd.isometric_camera(box)
    assert camera.startswith("OrthographicCamera {") and camera.endswith("}") and "\n" not in camera
    centre = [(box[i] + box[i + 3]) / 2 for i in range(3)]
    radius = math.dist(box[:3], box[3:]) / 2
    position = numbers(camera, "position", 3)
    towards = [c - p for c, p in zip(centre, position)]
    distance = math.hypot(*towards)
    # FreeCAD's isometric view looks along (-1, 1, -1): from the front right, from above
    assert [t / distance for t in towards] == pytest.approx([-3 ** -0.5, 3 ** -0.5, -3 ** -0.5], abs=1e-5)
    assert numbers(camera, "orientation", 4) == pytest.approx([0.742906, 0.307722, 0.594473, 1.217116], abs=1e-5)
    assert numbers(camera, "height", 1)[0] >= 2 * radius                      # the whole box is in view
    assert numbers(camera, "nearDistance", 1)[0] > 0
    assert numbers(camera, "nearDistance", 1)[0] <= distance - radius + 1e-6
    assert numbers(camera, "farDistance", 1)[0] >= distance + radius - 1e-6


def test_a_box_without_size_and_a_box_that_is_none():
    assert numbers(fcstd.isometric_camera((5.0, 5.0, 5.0, 5.0, 5.0, 5.0)), "height", 1)[0] > 0
    for bad in ((0.0, 0.0, 0.0, -1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 1.0, 1.0, float("inf")), (0.0, 0.0, 0.0)):
        with pytest.raises(fcstd.FcstdError, match="not a bounding box"):
            fcstd.isometric_camera(bad)
