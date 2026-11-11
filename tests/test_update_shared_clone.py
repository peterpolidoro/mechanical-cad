"""tools/update_shared_clone.py on an ordinary filesystem."""
import shutil
import subprocess
import sys

import pytest
from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import update_shared_clone as U  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is not on PATH")


def run(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=test", "-c", "user.email=test@example.org", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repos(tmp_path):
    local, shared = tmp_path / "local", tmp_path / "shared"
    local.mkdir()
    run(local, "init", "-q", "-b", "main")
    (local / ".gitattributes").write_text("*.ps1 text eol=crlf\n")
    (local / "keep.txt").write_text("one\n")
    (local / "gone.txt").write_text("to be deleted\n")
    (local / "script.ps1").write_text("Write-Output 1\n")
    run(local, "add", "-A")
    run(local, "commit", "-q", "-m", "first")
    subprocess.run(["git", "clone", "-q", str(local), str(shared)], check=True)
    (local / "keep.txt").write_text("two\n")
    (local / "gone.txt").unlink()
    (local / "sub").mkdir()
    (local / "sub" / "new.ps1").write_text("Write-Output 2\n")
    run(local, "add", "-A")
    run(local, "commit", "-q", "-m", "second")
    return local, shared


def test_fast_forward(repos):
    local, shared = repos
    old, new = run(shared, "rev-parse", "HEAD"), run(local, "rev-parse", "HEAD")
    summary = U.update(local, shared, upstream_check=False)
    assert (summary["result"], summary["old"], summary["new"]) == ("fast-forwarded", old, new)
    assert (summary["files_written"], summary["files_removed"]) == (2, 1)
    assert run(shared, "rev-parse", "HEAD") == new == run(shared, "rev-parse", "origin/main")
    assert run(shared, "status", "--porcelain") == ""
    assert (shared / "keep.txt").read_text() == "two\n" and not (shared / "gone.txt").exists()
    assert (shared / "sub" / "new.ps1").read_bytes() == b"Write-Output 2\r\n"        # as a checkout writes it
    assert run(shared, "log", "--format=%s") == "second\nfirst"
    assert not list(shared.rglob("*.tmp-update"))
    assert U.update(local, shared, upstream_check=False)["result"] == "already current"


def test_refusals(repos, tmp_path):
    local, shared = repos
    with pytest.raises(U.UpdateError, match="not level with its upstream"):
        U.update(local, shared)                                   # the local repository has no upstream at all
    (shared / "keep.txt").write_text("edited on the share\n")
    with pytest.raises(U.UpdateError, match="has changes of its own"):
        U.update(local, shared, upstream_check=False)
    run(shared, "checkout", "-q", "keep.txt")
    (local / "keep.txt").write_text("uncommitted\n")
    with pytest.raises(U.UpdateError, match="uncommitted changes"):
        U.update(local, shared, upstream_check=False)
    run(local, "checkout", "-q", "keep.txt")
    (shared / "other.txt").write_text("x\n")
    run(shared, "add", "-A")
    run(shared, "commit", "-q", "-m", "diverged")
    with pytest.raises(U.UpdateError, match="not a fast-forward"):
        U.update(local, shared, upstream_check=False)
    with pytest.raises(U.UpdateError, match="not a git checkout"):
        U.update(local, tmp_path / "nothing", upstream_check=False)


def test_level_with_upstream_is_accepted(repos, tmp_path):
    local, shared = repos
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(local), str(bare)], check=True)
    run(local, "remote", "add", "origin", str(bare))
    run(local, "fetch", "-q", "origin")
    run(local, "branch", "-q", "--set-upstream-to=origin/main")
    assert U.update(local, shared)["result"] == "fast-forwarded"
    (local / "keep.txt").write_text("three\n")
    run(local, "commit", "-q", "-am", "third, not pushed")
    with pytest.raises(U.UpdateError, match="push first"):
        U.update(local, shared)


def test_command_line(repos, capsys):
    local, shared = repos
    assert U.main([str(local), str(shared), "--no-upstream-check"]) == 0
    assert '"result": "fast-forwarded"' in capsys.readouterr().out
    (shared / "keep.txt").write_text("edited\n")
    assert U.main([str(local), str(shared), "--no-upstream-check"]) == 1
    assert "changes of its own" in capsys.readouterr().err
