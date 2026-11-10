import json
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
