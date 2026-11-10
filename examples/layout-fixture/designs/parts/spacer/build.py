"""A plain spacer ring: the fixture's one part written as code.

`build(parameters)` returns the shape and touches no file. tools/build_part.py
calls it, writes part.step, receipt.json and facts.json beside this file, and
evaluates checks.json.
"""


def build(parameters):
    import FreeCAD as App
    import Part

    outer = parameters["outer_diameter_mm"] / 2.0
    inner = parameters["inner_diameter_mm"] / 2.0
    height = parameters["height_mm"]
    if not 0 < inner < outer or height <= 0:
        raise ValueError("need 0 < inner diameter < outer diameter and a positive height")
    ring = Part.makeCylinder(outer, height).cut(Part.makeCylinder(inner, height))
    ring.translate(App.Vector(0, 0, 0))     # axis along Z, bottom face on Z = 0
    return ring
