"""Build an authored part from its program.

    FreeCADCmd tools/build_part.py --pass PROJECT/designs/parts/KEY [...]

The part directory holds `build.py` and `parameters.json`. `build.py` defines

    def build(parameters): ...  ->  a Part.Shape of FreeCAD, or a shape of build123d

a pure function: it takes the parsed parameters and returns the shape; it
reads and writes no file. A build123d shape needs build123d in the same
environment as FreeCAD (README.md, "Guix"); it is handed to FreeCAD as BREP,
and the receipt names the library and its version beside the tool.
This tool does the rest and is the only writer of
the three files it produces:

    part.step      the shape as STEP, with a normalised header and its product
                   named after the part's key
    receipt.json   hashes of the program, the parameters and the STEP, the tool
                   and kernel versions, and the re-import check
    facts.json     what the kernel measures of part.step as read back

None of the three carries a timestamp, so building an unchanged part again
changes no file. If the part has a `checks.json`, its checks are evaluated
against the new facts and a failure is reported.

FreeCADCmd prints an uncaught exception and still exits 0, so this script
prints its own status line; trust that and the files, not the exit code.
"""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kernel  # noqa: E402
from mechanical_cad import facts, jsonio, layout, stepfile  # noqa: E402

REIMPORT_RELATIVE = 1e-6
REIMPORT_LENGTH_MM = 1e-6


def build(part_dir):
    part_dir = Path(part_dir).resolve()
    key = part_dir.name
    if part_dir.parent.name != "parts" or part_dir.parent.parent.name != "designs" or not layout.KEY.match(key):
        raise ValueError(f"{part_dir}: expected PROJECT/designs/parts/<key>")
    program, params_file = part_dir / "build.py", part_dir / "parameters.json"
    parameters = jsonio.load(params_file)
    namespace = {"__file__": str(program), "__name__": f"build_{key.replace('-', '_').replace('@', '_')}"}
    exec(compile(program.read_text(encoding="utf-8"), str(program), "exec"), namespace)
    if not callable(namespace.get("build")):
        raise ValueError(f"{program}: no build(parameters) function")
    shape, library = kernel.as_shape(namespace["build"](parameters))
    built = kernel.measure(shape)
    if not built["valid"] or built["solids"] < 1:
        raise ValueError(f"{key}: build() returned a shape that is not valid or has no solid")

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "part.step"
        shape.exportStep(str(raw))
        data = stepfile.set_product_name(stepfile.normalise_header(raw.read_bytes()), key)
    tmp_step = part_dir / "part.step.tmp"
    tmp_step.write_bytes(data)
    os.replace(tmp_step, part_dir / "part.step")

    back = kernel.measure(kernel.read_step(part_dir / "part.step"))
    same, diffs = facts.compare(built, back, REIMPORT_RELATIVE, REIMPORT_LENGTH_MM)
    tool = kernel.tool()
    unit = stepfile.length_unit(data)
    step = {"sha256": stepfile.sha256_bytes(data), "data_sha256": stepfile.data_sha256(data), "bytes": len(data),
            "length_unit": unit, "header_normalised": True}
    name = parameters.get("name") if isinstance(parameters, dict) and isinstance(parameters.get("name"), str) else key
    receipt = {
        "schema_version": layout.SCHEMA_VERSION, "key": key, "name": name, "step": step,
        "program": {"file": "build.py", "sha256": stepfile.sha256_file(program)},
        "parameters": {"file": "parameters.json", "sha256": stepfile.sha256_file(params_file)},
        "tool": dict(tool, library=library) if library else tool,
        "reimport": {"passed": same, "differences": diffs,
                     "tolerance": {"relative": REIMPORT_RELATIVE, "length_mm": REIMPORT_LENGTH_MM}},
    }
    fact = {"schema_version": layout.SCHEMA_VERSION, "key": key,
            "step": {"sha256": step["sha256"], "data_sha256": step["data_sha256"]},
            "tool": tool, "length_unit_declared": unit}
    fact.update(back)
    if not fact["notes"]:
        del fact["notes"]
    jsonio.write(part_dir / "receipt.json", receipt)
    jsonio.write(part_dir / "facts.json", fact)

    results = []
    if (part_dir / "checks.json").is_file():
        results = facts.evaluate(jsonio.load(part_dir / "checks.json"), fact)
    failed = [r["id"] for r in results if not r["passed"]]
    e = facts.extent(fact)
    print(f"[build_part] {key}: solids={fact['solids']} extent_mm={[round(v, 4) for v in e]} "
          f"volume_mm3={fact['volume_mm3']:.4f} re-import {'ok' if same else 'DIFFERS: ' + '; '.join(diffs)}; "
          f"{len(results)} check(s)" + (f", FAILED: {', '.join(failed)}" if failed else ""), flush=True)
    return same and not failed


def main(argv):
    dirs = [a for a in argv if not a.startswith("-")]
    if not dirs:
        raise SystemExit(__doc__)
    ok = True
    for d in dirs:
        try:
            ok &= build(d)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            print(f"[build_part] {d}: FAILED: {exc}")
            ok = False
    return 0 if ok else 1


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
    print(f"[build_part] exit status {rc}", flush=True)
    sys.exit(rc)
