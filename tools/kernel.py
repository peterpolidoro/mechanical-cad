"""Shared by the kernel-backed tools: read, write and measure a shape with FreeCAD's OpenCASCADE.

A part's program may build its shape with FreeCAD's Part module or with
build123d; as_shape brings either to the Part.Shape everything here works on.
A part drawn in FreeCAD has a document for its source; document_shape gives
the shape that document is a part of. A part built against other parts gets
each of them as an Input.

Volumes and areas that are recorded (facts.json, a receipt's re-import check)
are measured with OpenCASCADE's adaptive integration, which FreeCAD's Python
interface does not offer: `measure` hands the shape to the OCP bindings as
BREP for that. FreeCAD's own `Volume` is the kernel's plain integration over
the faces, and was 0.8 % low for a solid whose surface is a B-spline spiral
(2026-11-13). `solids`, which only compares what one run reads with what the
same run reads back, keeps the plain integration and needs no bindings.

Import only inside FreeCADCmd. FreeCAD reads every STEP file into millimetres
whatever unit the file declares, so everything here is in millimetres.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import FreeCAD as App
import Part

from mechanical_cad import stepfile


INTEGRATION_TOLERANCE = 1e-7        # relative, asked of the adaptive integration


class MeasureError(RuntimeError):
    """A shape cannot be measured here."""


def tool():
    return {"name": "FreeCAD", "version": ".".join(str(v) for v in App.Version()[:3]),
            "kernel": "OpenCASCADE", "kernel_version": str(Part.OCC_VERSION)}


def _bindings_version():
    from importlib import metadata, util
    if util.find_spec("OCP") is None:
        raise MeasureError("measuring needs the OCP bindings of OpenCASCADE beside FreeCAD: run in the environment "
                           "of .guix/manifest-build123d.scm (README.md, \"Guix packages\")")
    try:
        return metadata.version("cadquery-ocp")
    except metadata.PackageNotFoundError:
        return "unknown"


def measuring_tool():
    """What `measure` measures with: `tool()` and how volumes and areas are integrated."""
    return dict(tool(), integration={"method": "adaptive", "relative_tolerance": INTEGRATION_TOLERANCE,
                                     "bindings": "OCP", "bindings_version": _bindings_version()})


def as_shape(result):
    """What a part's build() returned, as (Part.Shape, library).

    A Part.Shape comes back as it is, with None. A shape of build123d, or
    anything else that wraps a TopoDS_Shape of the OCP bindings in `wrapped`,
    or such a TopoDS_Shape itself, is handed over as BREP, the kernel's own
    exact format: FreeCAD and OCP wrap the same OpenCASCADE and share no
    object. `library` then names what built it, for the receipt.
    """
    if isinstance(result, Part.Shape):
        return result, None
    wrapped = getattr(result, "wrapped", result)
    if type(wrapped).__module__.split(".")[0] != "OCP":
        raise TypeError(f"build() returned a {type(result).__module__}.{type(result).__name__}; expected a "
                        "Part.Shape of FreeCAD or a shape of build123d")
    import io
    from importlib import metadata

    from OCP.BRepTools import BRepTools

    stream = io.BytesIO()
    BRepTools.Write_s(wrapped, stream)
    shape = Part.Shape()
    shape.importBrepFromString(stream.getvalue().decode("ascii"))

    def version(distribution):
        try:
            return metadata.version(distribution)
        except metadata.PackageNotFoundError:
            return None

    name, bindings = type(result).__module__.split(".")[0], version("cadquery-ocp")
    if name == "OCP":
        return shape, {"name": "OCP", "version": bindings}
    return shape, {"name": name, "version": version(name), "bindings": "OCP", "bindings_version": bindings}


class Input:
    """A part that another part is built against, as its program receives it.

    `key` and `name` say which part; `facts` is its facts.json and `interface`
    its interface.json, each None when the part has none. The solid is read
    when asked for, without the items the file marks invisible: `shape()` as a
    Part.Shape of FreeCAD, `build123d()` as a shape of build123d. The program
    reads no file itself, so what it was built against is what the build
    command recorded.
    """

    def __init__(self, key, name, step_path, facts=None, interface=None):
        self.key, self.name, self.step_path = key, name, Path(step_path)
        self.facts, self.interface = facts, interface

    def shape(self):
        return read_step_visible(self.step_path)[0]

    def build123d(self):
        from build123d import import_step
        data = self.step_path.read_bytes()
        if not stepfile.invisible_items(data):
            return import_step(str(self.step_path))
        with tempfile.TemporaryDirectory() as tmp:
            visible = Path(tmp) / "visible.step"
            visible.write_bytes(stepfile.visible_only(data))
            return import_step(str(visible))

    def __repr__(self):
        return f"Input({self.key!r})"


def document_shape(path):
    """The shape a FreeCAD document is a part of, as (Part.Shape, what was exported).

    The document is opened, every object in it is computed again, and it is
    closed without being saved: the file is not touched. What is exported is
    the one object nothing else in the document uses that has a solid: a
    body, a part container, the last feature of a chain of Part features.
    Sketches, planes and spreadsheets that are left over have no solid and do
    not count. Refused: an object that does not compute, no such object, and
    more than one, because a part is one thing and the document does not say
    which.
    """
    document = App.openDocument(str(path), True)
    try:
        for obj in document.Objects:
            obj.touch()
        document.recompute()
        broken = sorted(o.Label for o in document.Objects if not o.isValid())
        if broken:
            raise ValueError(f"{Path(path).name}: {', '.join(broken)} did not compute; open the document in FreeCAD and repair it")
        found = []
        for obj in document.Objects:
            if obj.InList:
                continue
            try:
                shape = Part.getShape(obj)
            except Exception:
                continue
            if shape is not None and not shape.isNull() and shape.Solids:
                found.append((obj, shape))
        if not found:
            raise ValueError(f"{Path(path).name}: no object with a solid that nothing else in the document uses")
        if len(found) > 1:
            raise ValueError(f"{Path(path).name}: more than one object with a solid that nothing else uses "
                             f"({', '.join(sorted(o.Label for o, _ in found))}); a part is one of them")
        obj, shape = found[0]
        return shape.copy(), {"object": obj.Name, "label": obj.Label, "type": obj.TypeId}
    finally:
        App.closeDocument(document.Name)


POINT_TOLERANCE_MM = 1e-6


def at_points(shape, points):
    """What a shape has at each point: [{"point": [x, y, z], "is": "material" | "empty" | "surface"}].

    "material" is inside a solid of the shape, "empty" is outside all of them,
    and "surface" is on a face within POINT_TOLERANCE_MM, where neither can be
    said: a check has to name a point clear of the surface.
    """
    out = []
    for point in points:
        vector = App.Vector(*point)
        if shape.isInside(vector, POINT_TOLERANCE_MM, False):
            state = "material"
        elif shape.isInside(vector, POINT_TOLERANCE_MM, True):
            state = "surface"
        else:
            state = "empty"
        out.append({"point": [float(v) for v in point], "is": state})
    return out


def read_step(path):
    return Part.read(str(path))


def read_step_visible(path, data=None):
    """The shape of a STEP file without the items it marks invisible.

    Returns (shape, number of invisible items left out). An AP242 file exported
    from Inventor holds the bodies hidden in the native part; they are not part
    of what the file is taken to be (mechanical_cad/stepfile.py, visible_only).
    """
    data = Path(path).read_bytes() if data is None else data
    hidden = stepfile.invisible_items(data)
    if not hidden:
        return read_step(path), 0
    with tempfile.TemporaryDirectory() as tmp:
        visible = Path(tmp) / "visible.step"
        visible.write_bytes(stepfile.visible_only(data))
        return read_step(visible), len(hidden)


def measure_step(path, data=None):
    """The facts of a STEP file, measured without the items it marks invisible.

    Returns (facts, number of invisible items left out).
    """
    shape, hidden = read_step_visible(path, data)
    return measure(shape), hidden


def solids(shape):
    """[(volume in mm3, [x, y, z] of the centre of mass)] of the solids of a shape, in its own frame, by
    FreeCAD's plain integration: for matching what one run reads against what it reads back, not for records."""
    return [(s.Volume, [s.CenterOfMass.x, s.CenterOfMass.y, s.CenterOfMass.z]) for s in shape.Solids]


def _integrate(shape):
    """([(volume, [x, y, z] of the centre of mass)] of the solids, area, worst relative error reached), by
    OpenCASCADE's adaptive integration, through the OCP bindings."""
    _bindings_version()
    import io

    from OCP.BRep import BRep_Builder
    from OCP.BRepGProp import BRepGProp
    from OCP.BRepTools import BRepTools
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS_Shape

    handed = TopoDS_Shape()                 # FreeCAD and OCP share no object: BREP is the kernel's exact format
    BRepTools.Read_s(handed, io.BytesIO(shape.exportBrepToString().encode("ascii")), BRep_Builder())
    solids, worst = [], 0.0
    explorer = TopExp_Explorer(handed, TopAbs_SOLID)
    while explorer.More():
        properties = GProp_GProps()
        worst = max(worst, abs(BRepGProp.VolumeProperties_s(explorer.Current(), properties, INTEGRATION_TOLERANCE)))
        centre = properties.CentreOfMass()
        solids.append((properties.Mass(), [centre.X(), centre.Y(), centre.Z()]))
        explorer.Next()
    surface = GProp_GProps()
    worst = max(worst, abs(BRepGProp.SurfaceProperties_s(handed, surface, INTEGRATION_TOLERANCE)))
    return solids, surface.Mass(), worst


def measure(shape):
    """The facts of one shape: validity, counts, volume, area, centre of mass, bounding box.

    Volume, area and centre of mass are by the kernel's adaptive integration (see the head of this file);
    the rest is FreeCAD's. Raises MeasureError where the OCP bindings are not to be had.
    """
    notes = []
    solids, area, worst = _integrate(shape)
    if len(solids) != len(shape.Solids):
        raise MeasureError(f"the shape has {len(shape.Solids)} solid(s) in FreeCAD and {len(solids)} as handed over")
    volume = sum(v for v, _ in solids)
    if solids and volume > 0:
        com = [sum(c[axis] * v for v, c in solids) / volume for axis in range(3)]
    else:
        com = [0.0, 0.0, 0.0]
        notes.append("no solid with a positive volume; the centre of mass is not defined")
    if any(v <= 0 for v, _ in solids):
        notes.append("a solid has a non-positive volume")
    if worst > 10 * INTEGRATION_TOLERANCE:
        notes.append(f"the integration reached a relative error of {worst:.1e}, not the {INTEGRATION_TOLERANCE:.0e} asked")
    bb = shape.optimalBoundingBox(True, False)
    valid = bool(shape.isValid())
    if not valid and len(shape.Solids) > 1:
        # a file of many solids, a circuit board's with a model per component, is often valid but for a few
        broken = sum(1 for s in shape.Solids if not s.isValid())
        if broken:
            notes.append(f"{broken} of {len(shape.Solids)} solids are not valid")
    return {
        "valid": valid,
        "solids": len(solids), "shells": len(shape.Shells), "faces": len(shape.Faces),
        "volume_mm3": volume, "area_mm2": area, "center_of_mass_mm": com,
        "bounding_box_mm": {"min": [bb.XMin, bb.YMin, bb.ZMin], "max": [bb.XMax, bb.YMax, bb.ZMax]},
        "notes": notes,
    }
