"""Shared by the kernel-backed tools: measure a shape with FreeCAD's OpenCASCADE.

A part's program may build its shape with FreeCAD's Part module or with
build123d; as_shape brings either to the Part.Shape everything here works on.

Import only inside FreeCADCmd. FreeCAD reads every STEP file into millimetres
whatever unit the file declares, so everything here is in millimetres.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import FreeCAD as App
import Part

from mechanical_cad import stepfile


def tool():
    return {"name": "FreeCAD", "version": ".".join(str(v) for v in App.Version()[:3]),
            "kernel": "OpenCASCADE", "kernel_version": str(Part.OCC_VERSION)}


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
    """[(volume in mm3, [x, y, z] of the centre of mass)] of the solids of a shape, in its own frame."""
    return [(s.Volume, [s.CenterOfMass.x, s.CenterOfMass.y, s.CenterOfMass.z]) for s in shape.Solids]


def measure(shape):
    """The facts of one shape: validity, counts, volume, area, centre of mass, bounding box."""
    notes = []
    solids = shape.Solids
    volume = sum(s.Volume for s in solids)
    if solids and volume > 0:
        com = [sum(getattr(s.CenterOfMass, axis) * s.Volume for s in solids) / volume for axis in ("x", "y", "z")]
    else:
        com = [0.0, 0.0, 0.0]
        notes.append("no solid with a positive volume; the centre of mass is not defined")
    if any(s.Volume <= 0 for s in solids):
        notes.append("a solid has a non-positive volume")
    bb = shape.optimalBoundingBox(True, False)
    return {
        "valid": bool(shape.isValid()),
        "solids": len(solids), "shells": len(shape.Shells), "faces": len(shape.Faces),
        "volume_mm3": volume, "area_mm2": shape.Area, "center_of_mass_mm": com,
        "bounding_box_mm": {"min": [bb.XMin, bb.YMin, bb.ZMin], "max": [bb.XMax, bb.YMax, bb.ZMax]},
        "notes": notes,
    }
