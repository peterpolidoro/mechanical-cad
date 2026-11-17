"""The file to print a part from: a mesh of its STEP file, checked against the solid, and shown to a slicer.

    python3 tools/print_file.py PROJECT KEY [--deflection 0.01] [--angle 0.1] [--out DIR]

Run it where build123d is (.guix/manifest-build123d.scm); with
.guix/manifest-print.scm beside it the slicer looks at the file as well.

KEY is a part of the project. Its `part.step` is read and written as a mesh,
`KEY.stl`, into PROJECT/.cache/print/, which the project ignores, with
`KEY.print.json` beside it: what the mesh was made from and how it compares.
A mesh is flat triangles, so it is never the solid; `--deflection` is how far
a triangle may lie from the surface, in millimetres, and `--angle` how far two
neighbouring triangles may turn against each other on a curved face, in
radians.

What is checked, and recorded:

    closed     every edge of the mesh is shared by exactly two triangles that
               run along it in opposite directions: the mesh bounds a volume
               and has an inside. A slicer needs that.
    volume     the mesh's volume against the solid's, as facts.json has it.
               They differ by what the triangles cut off curved faces; more
               than --volume-tolerance (0.5 %) is a fault.
    extent     the mesh's bounding box against the solid's, within twice the
               deflection.
    slicer     where `prusa-slicer` is on PATH: what it says of the file
               (`--info`): that the mesh is manifold, its parts and its
               volume. It is not sliced: that needs a printer and a material.

The record carries no timestamp, so the same part with the same settings gives
the same record. Prints a line per check and a status line; the exit status is
0 when every check that was made passed.

Printing a part is the first half of "made and verified". The other half, the
part measured and compared with its STEP file, is not built.
"""
from __future__ import annotations

import shutil
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mechanical_cad import jsonio, layout, stepfile  # noqa: E402

PRINT_DIR = (".cache", "print")
RECORD_SCHEMA = 1
VOLUME_TOLERANCE = 0.005


def options(argv):
    opts = {"deflection": "0.01", "angle": "0.1", "volume-tolerance": str(VOLUME_TOLERANCE), "out": None}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--") and a[2:] in opts and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 1
        elif a.startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(a)
        i += 1
    if len(positional) != 2:
        raise SystemExit(__doc__)
    try:
        numbers = {k: float(opts[k]) for k in ("deflection", "angle", "volume-tolerance")}
    except ValueError:
        raise SystemExit(__doc__) from None
    if any(v <= 0 for v in numbers.values()):
        raise SystemExit("[print_file] the deflection, the angle and the volume tolerance are positive numbers")
    return positional, numbers, opts["out"]


def read_stl(path):
    """The triangles of a binary STL file: [((x, y, z), (x, y, z), (x, y, z))], as the file's 32-bit numbers."""
    data = Path(path).read_bytes()
    if len(data) < 84:
        raise ValueError(f"{path}: too short for an STL file")
    (count,) = struct.unpack_from("<I", data, 80)
    if len(data) != 84 + 50 * count:
        raise ValueError(f"{path}: not a binary STL file ({len(data)} bytes for {count} triangles)")
    out = []
    for n in range(count):
        v = struct.unpack_from("<9f", data, 84 + 50 * n + 12)
        out.append((v[0:3], v[3:6], v[6:9]))
    return out


def mesh_facts(triangles):
    """What a list of triangles is: how many, whether they close a volume, its volume and its bounding box.

    `open_edges` counts the edges that are not shared by exactly two triangles
    running along them in opposite directions; zero means the mesh is closed
    and has an inside. The volume is the sum of the tetrahedra the triangles
    span with the origin, which is the enclosed volume when the mesh is closed.
    """
    along = {}
    volume = 0.0
    low, high = [float("inf")] * 3, [float("-inf")] * 3
    degenerate = 0
    for a, b, c in triangles:
        if a == b or b == c or c == a:
            degenerate += 1
            continue
        for p, q in ((a, b), (b, c), (c, a)):
            along[(p, q)] = along.get((p, q), 0) + 1
        volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                   + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
        for p in (a, b, c):
            for i in range(3):
                low[i], high[i] = min(low[i], p[i]), max(high[i], p[i])
    open_edges = sum(1 for (p, q), n in along.items() if n != 1 or along.get((q, p)) != 1)
    return {"triangles": len(triangles), "degenerate_triangles": degenerate, "open_edges": open_edges,
            "closed": open_edges == 0 and len(triangles) > 0, "volume_mm3": volume,
            "bounding_box_mm": {"min": low, "max": high}}


def slicer_info(path):
    """What prusa-slicer says of a mesh file, as a dict of its `name = value` lines; None when it is not on PATH."""
    tool = shutil.which("prusa-slicer")
    if tool is None:
        return None
    done = subprocess.run([tool, "--info", str(path)], capture_output=True, text=True, timeout=600)
    out = {}
    for line in (done.stdout + done.stderr).splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() and " " not in name.strip():
            out[name.strip()] = value.strip()
    out["exit_status"] = done.returncode
    return out


def main(argv):
    (project_dir, key), numbers, out_dir = options(argv)
    project_dir = Path(project_dir)
    project = layout.load(project_dir)
    comp = project.components.get(key)
    if comp is None or comp.kind != "part":
        print(f"[print_file] {project_dir} has no part {key!r}")
        return 2
    if comp.facts is None or comp.step_sha256 is None or comp.facts.get("step", {}).get("sha256") != comp.step_sha256:
        print(f"[print_file] {key}: no facts.json of the part.step that is there; build or measure the part first")
        return 2
    from build123d import export_stl, import_step

    out = Path(out_dir) if out_dir else project_dir.joinpath(*PRINT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    stl = out / f"{key}.stl"
    data = comp.step_path.read_bytes()
    shape = import_step(str(comp.step_path)) if not stepfile.invisible_items(data) else None
    if shape is None:
        print(f"[print_file] {key}: the STEP file marks items invisible; a part to print has none")
        return 2
    if not export_stl(shape, str(stl), tolerance=numbers["deflection"], angular_tolerance=numbers["angle"]):
        print(f"[print_file] {key}: the mesh could not be written")
        return 1
    mesh = mesh_facts(read_stl(stl))
    solid_volume = comp.facts["volume_mm3"]
    box = comp.facts["bounding_box_mm"]
    off = abs(mesh["volume_mm3"] - solid_volume) / solid_volume if solid_volume else float("inf")
    reach = 2 * numbers["deflection"] + 1e-4            # the file's numbers are 32-bit
    extent_ok = all(abs(mesh["bounding_box_mm"][end][i] - box[end][i]) <= reach for end in ("min", "max") for i in range(3))
    checks = {"closed": mesh["closed"], "volume": off <= numbers["volume-tolerance"], "extent": extent_ok}
    print(f"[print_file] {key}: {mesh['triangles']} triangles; "
          + ("closed" if mesh["closed"] else f"NOT CLOSED: {mesh['open_edges']} edge(s) without their partner"))
    print(f"[print_file] {key}: volume {mesh['volume_mm3']:.3f} mm3 against the solid's {solid_volume:.3f}, "
          f"{off * 100:.4f} % apart" + ("" if checks["volume"] else f": MORE THAN {numbers['volume-tolerance'] * 100:g} %"))
    if not extent_ok:
        print(f"[print_file] {key}: the mesh's bounding box IS NOT the solid's within {reach:.3f} mm")
    slicer = slicer_info(stl)
    if slicer is None:
        print(f"[print_file] {key}: prusa-slicer is not on PATH; the slicer has not looked at the file")
    else:
        checks["slicer"] = slicer.get("manifold") == "yes" and slicer.get("exit_status") == 0
        print(f"[print_file] {key}: prusa-slicer: manifold = {slicer.get('manifold')}, parts = {slicer.get('number_of_parts')}, "
              f"volume = {slicer.get('volume')}" + ("" if checks["slicer"] else ": NOT ACCEPTED"))
    record = {
        "schema_version": RECORD_SCHEMA, "key": key,
        "step": {"sha256": comp.step_sha256, "data_sha256": comp.step_data_sha256},
        "mesh": {"file": stl.name, "sha256": stepfile.sha256_file(stl), "format": "binary STL", "length_unit": "mm",
                 "deflection_mm": numbers["deflection"], "angle_rad": numbers["angle"], **mesh},
        "solid": {"volume_mm3": solid_volume, "bounding_box_mm": box},
        "volume_relative_difference": off, "volume_tolerance": numbers["volume-tolerance"],
        "slicer": slicer, "checks": checks, "passed": all(checks.values()),
    }
    jsonio.write(out / f"{key}.print.json", record)
    print(f"[print_file] {stl}")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except SystemExit as exc:
        print(exc)
        rc = 2
    except ValueError as exc:
        print(f"[print_file] {exc}")
        rc = 2
    print(f"[print_file] exit status {rc}", flush=True)
    sys.exit(rc)
