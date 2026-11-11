import json
import re
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
FIXTURE = REPO / "examples" / "layout-fixture"


@pytest.fixture
def fixture_dir():
    return FIXTURE


@pytest.fixture
def project_copy(tmp_path):
    """A writable copy of the layout fixture."""
    dst = tmp_path / "project"
    shutil.copytree(FIXTURE, dst, ignore=shutil.ignore_patterns("__pycache__", "generate_fixture.py", "README.md"))
    return dst


def edit_json(path, change):
    """Load a JSON file, apply `change(data)` in place, write it back."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    change(data)
    write_json(path, data)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def relock(project_dir):
    """Rewrite vault-lock.json from the directories, as the import command does."""
    from mechanical_cad import jsonio, layout
    lock = project_dir / "vault-lock.json"
    if lock.exists():
        lock.unlink()
    jsonio.write(lock, layout.derive_lock(layout.load(project_dir)))


def invisible(data, item):
    """`data` with its representation item #item marked invisible, the way
    Inventor's AP242 translator marks a body that is hidden in the native part."""
    end = data.rindex(b"ENDSEC;")
    return data[:end] + b"#9002 = STYLED_ITEM('',(),#%d);\n#9003 = INVISIBILITY((#9002));\n" % item + data[end:]


def replace_step(project_dir, part, data, **facts):
    """Put `data` in place of an imported part's part.step and bring its
    source.json, its facts.json and the lock in line with the new file."""
    from mechanical_cad import stepfile
    d = Path(project_dir) / part
    (d / "part.step").write_bytes(data)
    hashes = {"sha256": stepfile.sha256_bytes(data), "data_sha256": stepfile.data_sha256(data)}
    edit_json(d / "source.json", lambda s: s["step"].update(hashes, bytes=len(data)))
    edit_json(d / "facts.json", lambda f: (f["step"].update(hashes), f.update(facts)))
    relock(Path(project_dir))


def add_invisible_point(project_dir, part="references/parts/base-plate"):
    """Give an imported part one more representation item, a point, and mark it
    invisible. The solid is untouched, so the part's facts still hold."""
    data = (Path(project_dir) / part / "part.step").read_bytes()
    m = re.search(rb"ADVANCED_BREP_SHAPE_REPRESENTATION\('',\(", data)
    end = data.rindex(b"ENDSEC;")
    data = data[:m.end()] + b"#9001," + data[m.end():end] + b"#9001 = CARTESIAN_POINT('hidden',(0.,0.,0.));\n" + data[end:]
    replace_step(project_dir, part, invisible(data, 9001), invisible_items=1)
