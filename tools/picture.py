"""Pictures of a part or of a built assembly, made without a window: something to look at, for a person or an agent.

    python3 tools/picture.py PROJECT KEY [--views iso,iso-back] [--up +Z] [--size 1400x900] [--out DIR]
    python3 tools/picture.py FILE.step   [--views ...] [--up ...] [--size ...] [--out DIR]
    python3 tools/picture.py PROJECT KEY --where       print the STEP file that would be drawn, and draw nothing

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

A numerical check passes on a shape that is wrong in a way only a picture
shows: the first build of a lofted housing was twisted and passed every check.
Look at what was built.

Prints one line per picture and a status line. f3d may end with a fault after
it has written the image (seen with EGL, 2026-11-16); the image is what
counts, and the line says so.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mechanical_cad import assemblies, layout  # noqa: E402

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
        # straight along the up axis a camera has no up; lean it a little
        return _add((1, side), (0.02, a)) if [abs(c) for c in side].index(1) == index else side
    raise ValueError(f"unknown view {view!r}; known: {', '.join(list(corners) + [k.lower() for k in AXES])}")


def file_name(view):
    """A view's name in a file name: `+x` is plus-x and `-z` is minus-z."""
    return {"+": "plus-", "-": "minus-"}[view[0]] + view[1:].lower() if view[0] in "+-" else view


def options(argv):
    opts = {"views": ",".join(DEFAULT_VIEWS), "up": "+Z", "size": "1400x900", "out": None, "where": False}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--where":
            opts["where"] = True
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


def draw(step, png, direction, up, size):
    """One picture. Returns (written, note): whether the image is there, and what f3d said if it did not end well."""
    if png.exists():
        png.unlink()
    command = ["f3d", "--rendering-backend=egl", f"--output={png}", f"--resolution={size[0]},{size[1]}", f"--up={up}",
               "--camera-direction=" + ",".join(f"{c:g}" for c in direction), "--no-config", str(step)]
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
    step, stem, default_out = source(positional)
    directions = [(view, tuple(-c for c in stands(view, opts["up"]))) for view in opts["views"]]
    out = Path(opts["out"]) if opts["out"] else default_out
    out.mkdir(parents=True, exist_ok=True)
    failed = 0
    for view, direction in directions:
        png = out / f"{stem}-{file_name(view)}.png"
        written, note = draw(step, png, direction, opts["up"], opts["size"])
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
