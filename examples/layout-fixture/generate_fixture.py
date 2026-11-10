"""Regenerate the layout fixture's derived files.

    guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd examples/layout-fixture/generate_fixture.py

Everything under references/, vault-lock.json and the spacer's part.step,
receipt.json and facts.json are written by this script. The hand-written
files are designs/parts/spacer/{build.py,parameters.json,checks.json} and
designs/assemblies/fixture-with-spacer/assembly.json.

The fixture is synthetic. Its "Vault" identities are invented and say so; the
script stands in for the three commands that write a real project: the
exporter and import command (references/, the lock), the facts command, and
the build command (the spacer).
"""
from __future__ import annotations

import shutil
import sys

sys.dont_write_bytecode = True
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

import build_part  # noqa: E402
import kernel  # noqa: E402
import step_facts  # noqa: E402
from mechanical_cad import jsonio, layout, stepfile  # noqa: E402

RUN = "synthetic-export-0001"
EXPORTED_AT = "2026-01-01T00:00:00Z"
# part Z onto the assembly's Y: the parts are modelled Z-up, the assemblies are Y-up like Inventor's
Z_TO_Y = [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]]
IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def matrix(rotation, translation):
    return [rotation[i] + [float(translation[i])] for i in range(3)] + [[0.0, 0.0, 0.0, 1.0]]


def step_bytes(shape, product):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "shape.step"
        shape.exportStep(str(path))
        return stepfile.set_product_name(path.read_bytes(), product)


def with_exporter_header(data, name, author):
    """A header as an exporter that does not normalise would leave it: a name
    derived from the document, a timestamp and an author. Fixed here so the
    fixture is reproducible."""
    data = stepfile.normalise_header(data, name)
    return data.replace(("'" + stepfile.NORMALISED_TIMESTAMP + "',(''),").encode(),
                        ("'2026-01-01T00:00:00',('" + author + "'),").encode(), 1)


def vault(master, version, name, ext):
    return {"vault_id": "0", "master_id": master, "version_id": version, "version_number": 1, "revision": "A",
            "lifecycle_state": "Synthetic", "checkin_date": "2026-01-01T00:00:00Z",
            "path": f"$/SYNTHETIC/FIXTURE/{name}.{ext}", "native_sha256": None}


def main():
    for stale in (HERE / "references", HERE / "vault-lock.json"):
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()
    parts_dir = HERE / "references" / "parts"
    asm_dir = HERE / "references" / "assemblies"
    receipts = HERE / "references" / "receipts" / RUN
    for d in (parts_dir, asm_dir, receipts):
        d.mkdir(parents=True)
    export = {"run": RUN, "exporter": "examples/layout-fixture/generate_fixture.py (synthetic)", "exported_at": EXPORTED_AT}

    plate = Part.makeBox(100, 60, 8, App.Vector(-50, -30, 0))
    pin = Part.makeCylinder(5, 30)
    specs = [
        ("base-plate", "BASE PLATE", "900001", "900101", stepfile.normalise_header(step_bytes(plate, "BASE PLATE")), True,
         {"part_number": "FX-001", "description": "Synthetic base plate", "material": "Generic"}),
        ("pin", "PIN", "900002", "900102",
         with_exporter_header(step_bytes(pin, "PIN"), "PIN__[Primary]__00000000.step", "fixture-author"), False,
         {"part_number": "FX-002", "description": "Synthetic pin", "material": "Steel"}),
    ]
    files = {}
    for key, name, master, version, data, normalised, props in specs:
        d = parts_dir / key
        d.mkdir()
        (d / "part.step").write_bytes(data)
        m = kernel.measure(kernel.read_step(d / "part.step"))
        box = m["bounding_box_mm"]
        package_path = f"{master}/part.step"
        files[package_path] = {"sha256": stepfile.sha256_bytes(data), "bytes": len(data)}
        jsonio.write(d / "source.json", {
            "schema_version": 1, "kind": "part", "key": key, "name": name, "model_state": "[Primary]",
            "vault": vault(master, version, name, "ipt"),
            "step": {"sha256": stepfile.sha256_bytes(data), "data_sha256": stepfile.data_sha256(data), "bytes": len(data),
                     "protocol": stepfile.header(data)["protocol"], "length_unit": stepfile.length_unit(data),
                     "header_normalised": normalised, "received_sha256": None},
            "export": dict(export, package_id=f"{master}|[Primary]", package_path=package_path),
            "properties": props, "bom_structure_default": "Normal",
            "native": {"length_unit": "mm", "bodies": {"surface_bodies": 1, "solid_bodies": 1, "visible_solid_bodies": 1},
                       "extent_mm": [round(box["max"][i] - box["min"][i], 9) for i in range(3)],
                       "volume_mm3": round(m["volume_mm3"], 6)},
            "materials": None,
        })

    def child(name, component, kind, master, rotation, translation, **flags):
        rec = {"name": name, "component": component, "kind": kind, "master_id": master, "model_state": "[Primary]",
               "transform": matrix(rotation, translation), "bom_structure": "Normal",
               "visible": True, "suppressed": False, "grounded": False, "flexible": False, "mirrored": False}
        rec.update(flags)
        return rec

    manifests = [
        ("pin-pair", "PIN PAIR", "900003", "900103", {
            "schema_version": 1, "key": "pin-pair", "name": "PIN PAIR", "length_unit": "cm",
            "children": [child("PIN:1", "pin", "part", "900002", IDENTITY, [-2.5, 0, 0], grounded=True),
                         child("PIN:2", "pin", "part", "900002", IDENTITY, [2.5, 0, 0])]}),
        ("fixture-root", "FIXTURE ROOT", "900004", "900104", {
            "schema_version": 1, "key": "fixture-root", "name": "FIXTURE ROOT", "length_unit": "mm",
            "frame": {"handedness": "right", "up_axis": "+Y"},
            "children": [
                child("BASE PLATE:1", "base-plate", "part", "900001", Z_TO_Y, [0, 0, 0], grounded=True),
                child("PIN PAIR:1", "pin-pair", "assembly", "900003", Z_TO_Y, [0, 8, -15]),
                # a flexible instance: its second pin sits 10 mm further out than the definition says
                child("PIN PAIR:2", "pin-pair", "assembly", "900003", Z_TO_Y, [0, 8, 15], flexible=True,
                      overrides=[{"path": ["PIN:2"], "transform": matrix(IDENTITY, [35, 0, 0])}]),
            ]}),
    ]
    for key, name, master, version, manifest in manifests:
        d = asm_dir / key
        d.mkdir()
        jsonio.write(d / "assembly.json", manifest)
        jsonio.write(d / "source.json", {
            "schema_version": 1, "kind": "assembly", "key": key, "name": name, "model_state": "[Primary]",
            "vault": vault(master, version, name, "iam"),
            "export": dict(export, package_id=f"{master}|[Primary]"),
            "native": {"length_unit": manifest["length_unit"]},
        })
    jsonio.write(receipts / "export-receipt.json", {
        "schema_version": 1, "exporter": export["exporter"], "generated_at": EXPORTED_AT,
        "note": "synthetic: the package paths name the files as an exporter would have delivered them",
        "files": files})

    ok = build_part.build(HERE / "designs" / "parts" / "spacer")
    rc = step_facts.main([str(HERE), "--force"])
    project = layout.load(HERE)
    jsonio.write(HERE / "vault-lock.json", layout.derive_lock(project))
    project = layout.load(HERE)
    for line in project.errors:
        print("ERROR  ", line)
    for line in project.findings:
        print("FINDING", line)
    print(f"[generate_fixture] built spacer: {ok}; facts exit {rc}; layout errors: {len(project.errors)}")
    return 0 if ok and rc == 0 and project.ok else 1


def _is_entry():
    """True when this file is the script FreeCADCmd or python was asked to run
    (FreeCADCmd executes a script in its own namespace, not as __main__)."""
    here = Path(__file__).resolve()
    return any(a and Path(a).resolve() == here for a in sys.argv[:2])


if _is_entry():
    try:
        status = main()
    except BaseException:
        import traceback
        traceback.print_exc()
        status = 1
    print(f"[generate_fixture] exit status {status}", flush=True)
    sys.exit(status)
