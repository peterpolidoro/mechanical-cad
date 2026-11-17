"""Write the interface of a circuit board from the files its repository generates and from its solid model.

    FreeCADCmd tools/board_interface.py --pass PROJECT/designs/parts/KEY GEOMETRY.json [DATUMS.json]

The part is a supplied part: the STEP file of the assembled board, put into the
project with `python3 -m mechanical_cad add-supplied`. GEOMETRY.json is the
board repository's `board-geometry.json` (the outline, the thickness, the
mounting holes, the connectors with their courtyards, in a frame at the middle
of the outline with x to the right and y up). DATUMS.json, optional, is its
`mechanical-datums.json`, which says for some connectors from which side a
plug comes and which plug.

What those files do not say is height. This command takes it from the solid
model: for each connector, how far the solids over its courtyard reach from
the board; and how far anything reaches above and below the board.

It writes `interface.json` beside the part (docs/layout-specification.md, "The
interface of a part"), in the frame of the STEP file as it came:

    frames.board     the frame of the geometry file, with z = 0 on the top face
    outline          the outline on the top face
    top, bottom      the two faces
    h101 ...         a hole for each mounting hole, through the board
    j201 ...         a port for each connector: its courtyard, from the board to the top of its solids
    parts-above, parts-below   what the board's parts occupy on each side

The board is found in the file as the solid whose extent in x and y is the
outline's. Nothing is assumed of where the file's origin is; the frames are
taken to be turned alike, and that is tested: every mounting hole must be
empty in the board, and solids must stand over the connectors' courtyards.
A file that fails that is refused.

The interface holds each mounting hole to the solid, so measure the part again
afterwards (tools/step_facts.py) for `check` to read it.

FreeCADCmd prints an uncaught exception and still exits 0, so this script
prints its own status line; trust that and the file, not the exit code.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kernel  # noqa: E402
from mechanical_cad import interfaces, jsonio, layout  # noqa: E402

SIZE_TOLERANCE_MM = 0.05            # the board's extent in the file against the outline's
OVER_COURTYARD_MM = 0.25            # a solid counts as a connector's when its middle is within its courtyard, by this much
SIDES = {"top": 1.0, "front": 1.0, "bottom": -1.0, "back": -1.0}
DIRECTIONS = {"+z": [0.0, 0.0, 1.0], "-z": [0.0, 0.0, -1.0], "+x": [1.0, 0.0, 0.0], "-x": [-1.0, 0.0, 0.0],
              "+y": [0.0, 1.0, 0.0], "-y": [0.0, -1.0, 0.0]}


def _r(v):
    """A number as it is written: micrometres are more than a board's files know."""
    return round(float(v), 4) + 0.0


def _feature_id(reference):
    out = "".join(c if c.isalnum() else "-" for c in str(reference).lower()).strip("-")
    return out or "unnamed"


def find_board(shape, width, height):
    """The solid that is the board itself: the one whose extent in x and y is the outline's."""
    found = [s for s in shape.Solids
             if abs(s.BoundBox.XLength - width) <= SIZE_TOLERANCE_MM and abs(s.BoundBox.YLength - height) <= SIZE_TOLERANCE_MM]
    if not found:
        raise ValueError(f"no solid of the file is {width} x {height} mm in x and y: the board is not found, or the "
                         "file is turned against the geometry file")
    return max(found, key=lambda s: s.Volume)


def interface_of(key, shape, geometry, datums=None):
    """(the interface, what was found as a list of lines). Raises ValueError when the file and the geometry disagree."""
    if geometry.get("units") != "mm":
        raise ValueError(f"the geometry file is in {geometry.get('units')!r}; expected mm")
    frame = geometry.get("frame", {})
    if frame.get("x_axis") != "right" or frame.get("y_axis") != "up":
        raise ValueError("the geometry file's frame is not x to the right and y up")
    outline = geometry["outline"]
    box = outline["bbox"]
    width, height = box["max_x"] - box["min_x"], box["max_y"] - box["min_y"]
    board = find_board(shape, width, height)
    bb = board.BoundBox
    # the geometry file's frame in the file's: its origin is the middle of the outline's bounding box
    ox = bb.XMin - box["min_x"]
    oy = bb.YMin - box["min_y"]
    top, bottom = bb.ZMax, bb.ZMin
    thickness = top - bottom
    said = [f"the board: {bb.XLength:.3f} x {bb.YLength:.3f} x {thickness:.3f} mm, its frame at ({ox:.3f}, {oy:.3f}) of the file's"]
    stated = geometry.get("stackup", {}).get("board_thickness_mm")
    if isinstance(stated, (int, float)) and abs(stated - thickness) > 0.01:
        said.append(f"the board's solid is {thickness:.3f} mm thick; its files say {stated} mm")

    def at(x, y, z):
        return [_r(ox + x), _r(oy + y), _r(z)]

    features = [
        {"id": "outline", "kind": "outline", "point": at(0, 0, top), "normal": [0.0, 0.0, 1.0], "x": [1.0, 0.0, 0.0],
         "polygon": [[_r(box["min_x"]), _r(box["min_y"])], [_r(box["max_x"]), _r(box["min_y"])],
                     [_r(box["max_x"]), _r(box["max_y"])], [_r(box["min_x"]), _r(box["max_y"])]]},
        {"id": "top", "kind": "plane", "point": at(0, 0, top), "normal": [0.0, 0.0, 1.0]},
        {"id": "bottom", "kind": "plane", "point": at(0, 0, bottom), "normal": [0.0, 0.0, -1.0]},
    ]
    if outline.get("shape") == "rounded_rectangle" and outline.get("corner_radius_mm"):
        features[0]["corner_radius"] = _r(outline["corner_radius_mm"])
    elif outline.get("shape") not in ("rectangle", "rounded_rectangle"):
        features[0]["note"] = f"the outline is a {outline.get('shape')}; this is its bounding box"

    # the mounting holes, and the test that the two frames are turned alike: each must be empty in the board
    filled = []
    for hole in geometry.get("mounting_holes", []):
        centre = at(hole["x_mm"], hole["y_mm"], top)
        if board.isInside(kernel.App.Vector(centre[0], centre[1], (top + bottom) / 2), 1e-6, True):
            filled.append(hole["reference"])
        features.append({"id": _feature_id(hole["reference"]), "kind": "hole", "center": centre, "axis": [0.0, 0.0, 1.0],
                         "diameter": _r(hole["drill_diameter_mm"]), "depth": _r(thickness), "through": True,
                         "reference": hole["reference"]})
    if filled:
        raise ValueError(f"the board is solid where the geometry file has the mounting hole(s) {', '.join(filled)}: "
                         "the file and the geometry file are not turned alike, or are not of the same board")
    said.append(f"{len(geometry.get('mounting_holes', []))} mounting hole(s), each empty in the board")

    others = [s for s in shape.Solids if not s.isSame(board)]
    mating = {c.get("reference"): c for c in (datums or {}).get("connectors", []) if isinstance(c, dict)}
    without = []
    for connector in geometry.get("connectors", []):
        reference, yard = connector["reference"], connector["courtyard"]
        side = SIDES.get(connector.get("side"))
        if side is None:
            raise ValueError(f"{reference}: side {connector.get('side')!r} is neither top nor bottom")
        x0, x1, y0, y1 = ox + yard["min_x"], ox + yard["max_x"], oy + yard["min_y"], oy + yard["max_y"]
        over = [s.BoundBox for s in others
                if x0 - OVER_COURTYARD_MM <= s.BoundBox.Center.x <= x1 + OVER_COURTYARD_MM
                and y0 - OVER_COURTYARD_MM <= s.BoundBox.Center.y <= y1 + OVER_COURTYARD_MM
                and (s.BoundBox.ZMax > top + 1e-6 if side > 0 else s.BoundBox.ZMin < bottom - 1e-6)]
        if over:
            reach = max(b.ZMax for b in over) - top if side > 0 else bottom - min(b.ZMin for b in over)
        else:
            reach = 0.0
            without.append(reference)
        low, high = (top, top + reach) if side > 0 else (bottom - reach, bottom)
        datum = mating.get(reference, {})
        direction = DIRECTIONS.get(datum.get("mating_direction"))
        note = [str(connector.get("value") or ""), f"{reach:.2f} mm from the board"]
        if direction is None:
            direction = [0.0, 0.0, side]
            note.append("the board's files do not say from where a plug comes; taken as away from the board")
        if not over:
            note.append("no solid of the model stands over the courtyard")
        port = {"id": _feature_id(reference), "kind": "port",
                "box": {"min": [_r(x0), _r(y0), _r(low)], "max": [_r(x1), _r(y1), _r(high)]},
                "direction": direction, "reference": reference, "note": "; ".join(n for n in note if n)}
        if datum.get("plug_series"):
            port["accepts"] = str(datum["plug_series"])
        features.append(port)
    connectors = geometry.get("connectors", [])
    if connectors and len(without) > len(connectors) / 2:
        raise ValueError(f"no solid stands over the courtyard of {len(without)} of {len(connectors)} connectors "
                         f"({', '.join(without[:5])}): the file and the geometry file are not turned alike, or the "
                         "model has no components")
    said.append(f"{len(connectors)} connector(s)" + (f"; no solid over {', '.join(without)}" if without else ", a solid over each"))

    whole = shape.BoundBox
    for fid, low, high in (("parts-above", top, whole.ZMax), ("parts-below", whole.ZMin, bottom)):
        if high - low > 1e-6:
            features.append({"id": fid, "kind": "keep_out",
                             "box": {"min": [_r(bb.XMin), _r(bb.YMin), _r(low)], "max": [_r(bb.XMax), _r(bb.YMax), _r(high)]},
                             "note": f"{high - low:.2f} mm {'above the top' if fid == 'parts-above' else 'below the bottom'} face"})
    said.append(f"parts reach {whole.ZMax - top:.3f} mm above the top face and {bottom - whole.ZMin:.3f} mm below the bottom face")
    data = {
        "schema_version": interfaces.SCHEMA_VERSION, "key": key, "length_unit": "mm",
        "frames": {"board": {"transform": [[1.0, 0.0, 0.0, _r(ox)], [0.0, 1.0, 0.0, _r(oy)], [0.0, 0.0, 1.0, _r(top)],
                                           [0.0, 0.0, 0.0, 1.0]],
                             "note": "the frame of the board's geometry file: the middle of the outline, x to the "
                                     "right and y up, with z = 0 on the top face"}},
        "features": features,
    }
    wrong = interfaces.problems(data, key)
    if wrong:
        raise ValueError("the interface made is not well formed: " + "; ".join(wrong[:3]))
    return data, said


def main(argv):
    args = [a for a in argv if not a.startswith("-")]
    if len(args) not in (2, 3):
        raise SystemExit(__doc__)
    part_dir = Path(args[0]).resolve()
    key = part_dir.name
    if not (part_dir / layout.ORIGIN).is_file() or not (part_dir / "part.step").is_file():
        print(f"[board_interface] {part_dir}: not a supplied part (no {layout.ORIGIN} beside a part.step)")
        return 2
    geometry = jsonio.load(args[1])
    datums = jsonio.load(args[2]) if len(args) == 3 else None
    shape, _ = kernel.read_step_visible(part_dir / "part.step")
    try:
        data, said = interface_of(key, shape, geometry, datums)
    except (ValueError, KeyError) as exc:
        print(f"[board_interface] {key}: FAILED: {exc}")
        return 1
    for line in said:
        print(f"[board_interface] {key}: {line}")
    target = part_dir / layout.INTERFACE
    if target.is_file() and jsonio.load(target) == data:
        print(f"[board_interface] {key}: {layout.INTERFACE} is as it was")
    else:
        jsonio.write(target, data)
        print(f"[board_interface] {key}: wrote {layout.INTERFACE} with {len(data['features'])} features; measure the "
              f"part again: FreeCADCmd tools/step_facts.py --pass {part_dir.parents[2]} -- --only {key}")
    return 0


def _is_entry():
    """True when this file is the script FreeCADCmd or python was asked to run
    (FreeCADCmd executes a script in its own namespace, not as __main__)."""
    here = Path(__file__).resolve()
    return any(a and Path(a).resolve() == here for a in sys.argv[:2])


if _is_entry():
    if "--pass" in sys.argv:
        args = sys.argv[sys.argv.index("--pass") + 1:]
    else:
        args = [a for a in sys.argv[1:] if Path(a).resolve() != Path(__file__).resolve()]
    try:
        rc = main(args)
    except BaseException:
        import traceback
        traceback.print_exc()
        rc = 1
    print(f"[board_interface] exit status {rc}", flush=True)
    sys.exit(rc)
