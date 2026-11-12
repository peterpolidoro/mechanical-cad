"""What a FreeCAD document shows when it is opened in the FreeCAD window.

A document saved by FreeCADCmd, which has no window, holds no view data. The
window hides every object while it restores a document and shows again only
those whose view data say so; without any, the document opens with nothing
to see (FreeCAD 1.1.3, observed 2026-11-12). `write_view()` adds the view
data: for each named object whether it is shown, which nodes of the tree are
open, and a camera that has the whole model in view (without one the window
opens on the origin at a fixed zoom, which for most assemblies is empty).

An .FCStd file is a zip archive. The view data are its member
`GuiDocument.xml`, which has to come after the members the document itself
names (`Document.xml` and the shape files), because FreeCAD reads the archive
in one pass; it is appended. Only the two properties that decide whether an
object is drawn are written; everything else keeps FreeCAD's defaults. No
kernel is needed here.
"""
from __future__ import annotations

import math
import zipfile
from xml.sax.saxutils import quoteattr

MEMBER = "GuiDocument.xml"
# The rotation of FreeCAD's isometric view, as a quaternion (x, y, z, w).
ISOMETRIC = (0.424708, 0.17592, 0.339851, 0.820473)


class FcstdError(ValueError):
    pass


def _rotate(q, v):
    """The vector v turned by the unit quaternion q = (x, y, z, w)."""
    x, y, z, w = q
    u = (x, y, z)
    cross = lambda a, b: (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])  # noqa: E731
    t = tuple(2.0 * c for c in cross(u, v))
    return tuple(v[i] + w * t[i] + cross(u, t)[i] for i in range(3))


def isometric_camera(bounds):
    """An orthographic camera, as Open Inventor text on one line, that has the box
    bounds = (xmin, ymin, zmin, xmax, ymax, zmax) in view from FreeCAD's isometric direction."""
    lo, hi = bounds[:3], bounds[3:]
    if len(bounds) != 6 or not all(math.isfinite(v) for v in bounds) or any(a > b for a, b in zip(lo, hi)):
        raise FcstdError(f"not a bounding box: {bounds!r}")
    centre = [(a + b) / 2.0 for a, b in zip(lo, hi)]
    radius = math.dist(lo, hi) / 2.0 or 1.0
    norm = math.sqrt(sum(c * c for c in ISOMETRIC))
    q = tuple(c / norm for c in ISOMETRIC)
    looking = _rotate(q, (0.0, 0.0, -1.0))               # a camera looks along its own -Z
    distance = 2.0 * radius
    position = [c - d * distance for c, d in zip(centre, looking)]
    angle = 2.0 * math.acos(q[3])
    axis = [c / math.sin(angle / 2.0) for c in q[:3]]
    number = lambda v: repr(round(v, 6))                  # noqa: E731
    return ("OrthographicCamera { viewportMapping ADJUST_CAMERA"
            f" position {' '.join(map(number, position))}"
            f" orientation {' '.join(map(number, axis))} {number(angle)}"
            f" nearDistance {number(distance - radius)} farDistance {number(distance + radius)}"
            f" aspectRatio 1 focalDistance {number(distance)} height {number(2.1 * radius)} }}")


def view_xml(shown, expanded=(), camera=""):
    """The text of GuiDocument.xml for {object name: shown?}, the names of the
    open tree nodes and the camera (Open Inventor text; none: FreeCAD's default)."""
    expanded = set(expanded)
    unknown = sorted(expanded - set(shown))
    if unknown:
        raise FcstdError("expanded but not listed: " + ", ".join(unknown))
    out = ["<?xml version='1.0' encoding='utf-8'?>", '<Document SchemaVersion="1">',
           f'    <ViewProviderData Count="{len(shown)}">']
    for name, visible in shown.items():
        out += [
            f'        <ViewProvider name={quoteattr(name)} expanded="{1 if name in expanded else 0}">',
            '            <Properties Count="2" TransientCount="0">',
            '                <Property name="DisplayMode" type="App::PropertyEnumeration" status="1">',
            '                    <Integer value="0"/>',
            '                </Property>',
            '                <Property name="Visibility" type="App::PropertyBool" status="1">',
            f'                    <Bool value="{"true" if visible else "false"}"/>',
            '                </Property>',
            '            </Properties>',
            '        </ViewProvider>',
        ]
    out += ["    </ViewProviderData>", f"    <Camera settings={quoteattr(camera)}/>", "</Document>", ""]
    return "\n".join(out)


def write_view(path, shown, expanded=(), camera=""):
    """Append the view data to the FreeCAD document at `path`.

    shown: {object name: True to show it, False to hide it}; an object that is
    not named stays hidden. Refuses a file that is not a FreeCAD document or
    that has view data already.
    """
    text = view_xml(shown, expanded, camera)
    try:
        with zipfile.ZipFile(path, "a") as archive:
            names = archive.namelist()
            if "Document.xml" not in names:
                raise FcstdError(f"{path}: no Document.xml; not a FreeCAD document")
            if MEMBER in names:
                raise FcstdError(f"{path}: has view data already")
            info = zipfile.ZipInfo(MEMBER, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, text.encode("utf-8"))
    except zipfile.BadZipFile as exc:
        raise FcstdError(f"{path}: {exc}") from None


def read_view(path):
    """{object name: shown?} as the document's view data have it, or None when it has none."""
    import xml.etree.ElementTree as ET
    try:
        with zipfile.ZipFile(path) as archive:
            if MEMBER not in archive.namelist():
                return None
            root = ET.fromstring(archive.read(MEMBER))
    except zipfile.BadZipFile as exc:
        raise FcstdError(f"{path}: {exc}") from None
    out = {}
    for provider in root.iter("ViewProvider"):
        for prop in provider.iter("Property"):
            if prop.get("name") == "Visibility":
                out[provider.get("name")] = prop.find("Bool").get("value") == "true"
    return out
