"""Pictures of a part or of a built assembly, made without a window: something to look at, for a person or an agent.

    python3 tools/picture.py PROJECT KEY [--views iso,iso-back] [--up +Z] [--size 1400x900] [--out DIR]
    python3 tools/picture.py FILE.step   [--views ...] [--up ...] [--size ...] [--out DIR]
    python3 tools/picture.py PROJECT KEY --where       print the STEP file that would be drawn, and draw nothing
    python3 tools/picture.py PROJECT KEY --cut +y [--colour] ...       cut open, and each part in a colour of its own

Run it where `f3d` is on PATH (.guix/manifest-view.scm). f3d is a viewer built
on VTK and OpenCASCADE that reads a STEP file and renders it to an image
through EGL, which needs no display.

KEY is a component of the project. A part is drawn from its `part.step`. An
assembly is drawn from the file tools/assembly_step.py built of it
(PROJECT/.cache/assemblies/KEY.step); build it first. The pictures go to
PROJECT/.cache/pictures/, which the project ignores, as KEY-VIEW.png. With a
file instead of a project they go to --out, or beside the command.

A view says where the camera stands. `--up` names the axis that points up in
the picture (+Z by default; a part's own frame may have another). With A and
B the two axes that follow the up axis in the order X, Y, Z, X:

    iso        from +A, -B and above           iso-back   from -A, +B and above
    below      from +A, -B and below           below-back from -A, +B and below
    +x -x +y -y +z -z                          from that side, looking along the axis

Seen along the up axis the picture is a plan: from above, A runs to the right
and B upwards.

`--cut` takes away what lies on one side of a plane, so that the inside shows:
`--cut +y` everything beyond the middle of what is drawn towards +Y, `--cut
-x=12.5` everything below X = 12.5. Look at a cut from the side that was
taken away (`--cut +y --views +y` or `iso-back`; `--cut -y --views -y` or
`iso`). `--colour` gives every part of
an assembly a colour of its own, the same part the same colour wherever it
is placed; a part by itself, or a file, gets one colour per solid. Both need
build123d beside the viewer (.guix/manifest-build123d.scm with
.guix/manifest-view.scm): the solids are placed as the project's records say,
cut, and written as a model the viewer reads (KEY-cut-plus-y.glb beside the
pictures, which any viewer of glTF files opens as well). An assembly need not
be built first for that. The pictures are then named KEY-cut-plus-y-VIEW.png
and KEY-colour-VIEW.png.

A numerical check passes on a shape that is wrong in a way only a picture
shows: the first build of a lofted housing was twisted and passed every check.
Look at what was built.

Prints one line per picture and a status line. f3d may end with a fault after
it has written the image (seen with EGL, 2026-11-16); the image is what
counts, and the line says so.
"""
from __future__ import annotations

import colorsys
import json
import shutil
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mechanical_cad import assemblies, flatten, layout, solids, stepfile  # noqa: E402
from mechanical_cad import transforms as T  # noqa: E402

AXES = {"+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0), "+Z": (0, 0, 1), "-Z": (0, 0, -1)}
DEFAULT_VIEWS = ("iso", "iso-back")
PICTURES_DIR = (".cache", "pictures")
PNG = b"\x89PNG\r\n\x1a\n"
TIMEOUT_S = 600


def _add(*terms):
    return tuple(sum(scale * vector[i] for scale, vector in terms) for i in range(3))


def stands(view, up):
    """Where the camera stands, as a direction from the middle of what is drawn."""
    u = AXES[up]
    index = [abs(c) for c in u].index(1)
    sign = u[index]
    a = tuple(1 if i == (index + 1) % 3 else 0 for i in range(3))
    b = tuple(sign if i == (index + 2) % 3 else 0 for i in range(3))           # a x b = u
    corners = {"iso": (1, -1, 0.8), "iso-back": (-1, 1, 0.8), "below": (1, -1, -0.8), "below-back": (-1, 1, -0.8)}
    if view in corners:
        ca, cb, cu = corners[view]
        return _add((ca, a), (cb, b), (cu, u))
    if view.upper() in AXES:
        side = AXES[view.upper()]
        if [abs(c) for c in side].index(1) != index:
            return side
        # Straight along the up axis a camera has no up; lean it a little, so that the picture is a plan as it
        # is drawn: from above A runs to the right and B upwards, from below B is still upwards.
        return _add((1, side), (-0.02 if side[index] * sign > 0 else 0.02, b))
    raise ValueError(f"unknown view {view!r}; known: {', '.join(list(corners) + [k.lower() for k in AXES])}")


def file_name(view):
    """A view's name in a file name: `+x` is plus-x and `-z` is minus-z."""
    return {"+": "plus-", "-": "minus-"}[view[0]] + view[1:].lower() if view[0] in "+-" else view


def cut_plane(text):
    """What `--cut` asks for: (the axis as 0, 1 or 2; +1 or -1, the side that is taken away; where, or None).

    `+y` and `y` take away what lies beyond the middle towards +Y, `-y` what lies towards -Y, `-x=12.5` what is
    below X = 12.5.
    """
    side, _, where = text.partition("=")
    side = side.strip().lower()
    if side[:1] not in "+-":
        side = "+" + side
    if len(side) != 2 or side[1] not in "xyz":
        raise ValueError(f"--cut {text!r}: expected an axis and a side, +x -x +y -y +z or -z, and =WHERE if not the middle")
    try:
        offset = float(where) if where.strip() else None
    except ValueError:
        raise ValueError(f"--cut {text!r}: {where!r} is not a number") from None
    return "xyz".index(side[1]), (1 if side[0] == "+" else -1), offset


def colours(names):
    """A colour for each name, as (r, g, b) between 0 and 1: the same names give the same colours, and
    neighbours in the alphabet get hues far apart."""
    out = {}
    for i, name in enumerate(sorted(set(names))):
        out[name] = colorsys.hsv_to_rgb((0.58 + i * 0.6180339887) % 1.0, 0.45, 0.9)
    return out


PLAIN = (0.72, 0.74, 0.76)
MODEL_LIGHT = 1.7        # the viewer's light for a model that brings its own colours


def to_viewer(vector):
    """A direction of the model in a glTF file's frame. Such a file has Y up; what was Z up is turned to it."""
    x, y, z = vector
    return (x, z, -y)


def matte(path):
    """Say in a GLB file that its materials are not metal. OpenCASCADE writes a colour and nothing else, and a
    glTF material without a word on it is polished metal, which a viewer without surroundings draws nearly black."""
    data = Path(path).read_bytes()
    magic, version, _ = struct.unpack_from("<4sII", data, 0)
    length, kind = struct.unpack_from("<I4s", data, 12)
    if magic != b"glTF" or version != 2 or kind != b"JSON":
        raise ValueError(f"{path}: not a GLB file of glTF 2")
    document = json.loads(data[20:20 + length])
    for material in document.get("materials", []):
        material.setdefault("pbrMetallicRoughness", {}).update(metallicFactor=0.0, roughnessFactor=0.75)
    text = json.dumps(document, separators=(",", ":")).encode("utf-8")
    text += b" " * (-len(text) % 4)
    rest = data[20 + length:]
    Path(path).write_bytes(struct.pack("<4sII", b"glTF", 2, 20 + len(text) + len(rest)) + struct.pack("<I4s", len(text), b"JSON")
                           + text + rest)


def placed_solids(positional, scratch):
    """Every solid of what is to be drawn, where it belongs: [(the name that gives it its colour, the solid)].

    An assembly is put together from its parts' files and the placements the project records, in the frame its
    built file has (Z up), and a solid's name is its part's key. A part or a file is read as it is, and its
    solids are numbered. `scratch` is a directory a file may be written to for a moment. Needs build123d.
    """
    try:
        from build123d import Location, import_step
        from OCP.gp import gp_Trsf
    except ImportError:
        raise SystemExit("[picture] a cut and colours need build123d: add .guix/manifest-build123d.scm to the "
                         "environment (make picture does when CUT or COLOUR is given)") from None

    def read(path):
        data = Path(path).read_bytes()
        if not stepfile.invisible_items(data):
            return import_step(str(path)).solids()
        visible = scratch / ".visible.step"
        visible.write_bytes(stepfile.visible_only(data))
        try:
            return import_step(str(visible)).solids()
        finally:
            visible.unlink()

    placed = []
    project = layout.load(Path(positional[0])) if len(positional) == 2 else None
    comp = project.components.get(positional[1]) if project else None
    if comp is not None and comp.kind == "assembly":
        try:
            scene, assets, _ = flatten.flatten(project, flatten.find_root(project, comp.key).key)
        except flatten.FlattenError as exc:
            raise SystemExit(f"[picture] {exc}") from None
        shapes = {part: read(path) for part, path in assets}
        upright = solids.frame_matrix(scene, "z-up")
        for occurrence in solids.placed(scene):
            m = T.multiply(upright, occurrence["transform_world"])
            trsf = gp_Trsf()
            trsf.SetValues(*[float(m[r][c]) for r in range(3) for c in range(4)])
            placed += [(occurrence["part_id"], solid.moved(Location(trsf))) for solid in shapes[occurrence["part_id"]]]
    else:
        step = source(positional)[0]
        placed = [(f"solid {n + 1:04d}", solid) for n, solid in enumerate(read(step))]
    if not placed:
        raise SystemExit("[picture] there is no solid to draw")
    return placed


def extent(placed):
    """The box round every solid, as (low, high), and each solid's own."""
    def span(solid):
        box = solid.bounding_box()
        return (box.min.X, box.min.Y, box.min.Z), (box.max.X, box.max.Y, box.max.Z)
    spans = [span(s) for _, s in placed]
    return ([min(lo[i] for lo, _ in spans) for i in range(3)], [max(hi[i] for _, hi in spans) for i in range(3)]), spans


def model(positional, cut, coloured, out, stem):
    """The model the viewer is shown when a cut or colours are asked for: a GLB file, written with build123d.
    Returns its path."""
    placed = placed_solids(positional, out)
    from build123d import Align, Box, Color, Compound, Pos, export_gltf

    if cut:
        axis, side, where = cut
        (low, high), spans = extent(placed)
        where = (low[axis] + high[axis]) / 2 if where is None else where
        reach = 4 * max(h - l for l, h in zip(low, high)) + 10
        corner = [-reach / 2 + (l + h) / 2 for l, h in zip(low, high)]
        corner[axis] = where if side > 0 else where - reach
        away = Pos(*corner) * Box(reach, reach, reach, align=(Align.MIN, Align.MIN, Align.MIN))
        kept = []
        for (name, solid), (lo, hi) in zip(placed, spans):
            near, far = lo[axis], hi[axis]
            if (far <= where) if side > 0 else (near >= where):
                kept.append((name, solid))                      # wholly on the side that stays
            elif not ((near >= where) if side > 0 else (far <= where)):
                kept += [(name, piece) for piece in (solid - away).solids()]
        placed = kept
        if not placed:
            raise SystemExit("[picture] the cut takes everything away")
    shade = colours(name for name, _ in placed) if coloured else {}
    for name, solid in placed:
        solid.color = Color(*shade.get(name, PLAIN))
    glb = out / f"{stem}.glb"
    if not export_gltf(Compound(children=[solid for _, solid in placed]), str(glb), binary=True,
                       linear_deflection=0.002, angular_deflection=0.2):
        raise SystemExit(f"[picture] {glb} could not be written")
    matte(glb)
    return glb


def options(argv):
    opts = {"views": ",".join(DEFAULT_VIEWS), "up": "+Z", "size": "1400x900", "out": None, "where": False,
            "cut": None, "colour": False}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--where":
            opts["where"] = True
        elif a in ("--colour", "--color"):
            opts["colour"] = True
        elif a.startswith("--") and a[2:] in opts and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 1
        elif a.startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(a)
        i += 1
    size = opts["size"].lower().split("x")
    if not 1 <= len(positional) <= 2 or opts["up"].upper() not in AXES or len(size) != 2 or not all(s.isdigit() and int(s) > 0 for s in size):
        raise SystemExit(__doc__)
    opts["up"], opts["size"] = opts["up"].upper(), (int(size[0]), int(size[1]))
    opts["views"] = [v for v in opts["views"].split(",") if v]
    if opts["cut"] is not None:
        opts["cut"] = cut_plane(opts["cut"])
    return positional, opts


def source(positional):
    """(the STEP file to draw, the stem of the pictures' names, where they go by default)."""
    if len(positional) == 1:
        path = Path(positional[0])
        if not path.is_file():
            raise SystemExit(f"[picture] {path} is not a file; for a component of a project give the project and its key")
        return path, path.stem, Path.cwd()
    project_dir, key = Path(positional[0]), positional[1]
    project = layout.load(project_dir)
    comp = project.components.get(key)
    if comp is None:
        raise SystemExit(f"[picture] {project_dir} has no component {key!r}; its keys: {', '.join(sorted(project.components))}")
    out = project_dir.joinpath(*PICTURES_DIR)
    if comp.kind == "part":
        return comp.dir / "part.step", key, out
    built = assemblies.default_dir(project_dir) / f"{key}.step"
    if not built.is_file():
        raise SystemExit(f"[picture] {key} is an assembly and is not built ({built}); build it first with tools/assembly_step.py")
    return built, key, out


def draw(step, png, direction, up, size, light=None):
    """One picture. Returns (written, note): whether the image is there, and what f3d said if it did not end well.

    `light` is how strong the viewer's light is, where its own (1) is not wanted: a model with colours of its
    own comes out dim in it.
    """
    if png.exists():
        png.unlink()
    command = ["f3d", "--rendering-backend=egl", f"--output={png}", f"--resolution={size[0]},{size[1]}", f"--up={up}",
               "--camera-direction=" + ",".join(f"{c:g}" for c in direction), "--no-config"]
    command += ([f"--light-intensity={light:g}"] if light else []) + [str(step)]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return False, f"f3d did not finish in {TIMEOUT_S} s"
    written = png.is_file() and png.stat().st_size > 1000 and png.read_bytes()[:8] == PNG
    said = " ".join((done.stderr or done.stdout).split())[-200:]
    if written:
        return True, (f"f3d ended with status {done.returncode} after writing it" if done.returncode else "")
    return False, f"f3d wrote no image (status {done.returncode}): {said}"


def main(argv):
    positional, opts = options(argv)
    if opts["where"]:
        # for a viewer that follows the file (make view): the file alone on a line, and no f3d needed to say it
        print(source(positional)[0])
        return 0
    if shutil.which("f3d") is None:
        print("[picture] f3d is not on PATH; run this in the environment of .guix/manifest-view.scm")
        return 2
    made = opts["cut"] is not None or opts["colour"]
    if made and len(positional) == 2:
        # an assembly is put together from the records, so it need not be built for this
        project_dir, key = Path(positional[0]), positional[1]
        if key not in layout.load(project_dir).components:
            source(positional)                      # says what the project has, and stops
        step, stem, default_out = None, key, project_dir.joinpath(*PICTURES_DIR)
    else:
        step, stem, default_out = source(positional)
    directions = [(view, tuple(-c for c in stands(view, opts["up"]))) for view in opts["views"]]
    out = Path(opts["out"]) if opts["out"] else default_out
    out.mkdir(parents=True, exist_ok=True)
    up = opts["up"]
    if made:
        if opts["cut"] is not None:
            axis, side, _ = opts["cut"]
            stem += "-cut-" + file_name(("+" if side > 0 else "-") + "xyz"[axis])
        if opts["colour"]:
            stem += "-colour"
        step = model(positional, opts["cut"], opts["colour"], out, stem)
        print(f"[picture] {step}")
        # the model is a glTF file, which has Y up: the camera and the up axis are turned with it
        directions = [(view, to_viewer(direction)) for view, direction in directions]
        turned = to_viewer(AXES[up])
        up = next(name for name, vector in AXES.items() if vector == turned)
    failed = 0
    for view, direction in directions:
        png = out / f"{stem}-{file_name(view)}.png"
        written, note = draw(step, png, direction, up, opts["size"], light=MODEL_LIGHT if made else None)
        failed += not written
        print(f"[picture] {png}" + (f" ({note})" if written and note else "") if written else f"[picture] {view}: {note}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except SystemExit as exc:
        print(exc)
        rc = 2
    except ValueError as exc:
        print(f"[picture] {exc}")
        rc = 2
    if "--where" not in sys.argv[1:] or rc:
        print(f"[picture] exit status {rc}", flush=True)
    sys.exit(rc)
