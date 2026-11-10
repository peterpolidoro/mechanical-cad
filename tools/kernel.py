"""Shared by the kernel-backed tools: measure a shape with FreeCAD's OpenCASCADE.

Import only inside FreeCADCmd. FreeCAD reads every STEP file into millimetres
whatever unit the file declares, so everything here is in millimetres.
"""
from __future__ import annotations

import FreeCAD as App
import Part


def tool():
    return {"name": "FreeCAD", "version": ".".join(str(v) for v in App.Version()[:3]),
            "kernel": "OpenCASCADE", "kernel_version": str(Part.OCC_VERSION)}


def read_step(path):
    return Part.read(str(path))


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
