#!/usr/bin/env python3
"""Fast-forward a clone that lives on a filesystem where git cannot write safely.

    python3 tools/update_shared_clone.py LOCAL_CHECKOUT SHARED_CLONE [--no-upstream-check]

The Windows agent fetches from clones of the repositories kept on a network
share. On the Linux workstation that share is a GVFS mount, and git's own
updates of refs and of the index fail there: on 2026-11-10 a `git fetch` into
such a clone deleted a ref. Reading with git works. This script therefore
brings SHARED_CLONE to the commit of LOCAL_CHECKOUT without running any git
command that writes in the shared clone:

1. checks: the local checkout is clean and level with its upstream (it has
   been pushed); the shared clone is clean, on the same branch, and its commit
   is an ancestor of the local one (a fast-forward);
2. packs the new objects in a temporary directory and copies the pack files
   into the shared clone's object store;
3. writes the branch and its remote-tracking ref as plain files;
4. copies the changed files from a fresh temporary clone (so that line endings
   are what a checkout would produce), removes the deleted ones, and copies
   that clone's index;
5. verifies with read-only git that the shared clone is at the new commit and
   clean.

Every file is written under a temporary name and renamed, then read back. It
works on an ordinary filesystem too, which is how it is tested.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class UpdateError(Exception):
    pass


def git(repo, *args, check=True, stdin=None):
    """Run a git command that only reads the repository it is pointed at."""
    proc = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True, input=stdin)
    if check and proc.returncode:
        raise UpdateError(f"git {' '.join(args)} failed in {repo}: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout.decode(errors="replace").strip() if check else proc


def put(path, data):
    """Write bytes under a temporary name, rename, read back."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-update")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(data).digest():
        raise UpdateError(f"{path}: what was written is not what is there")


def update(local, shared, upstream_check=True):
    local, shared = Path(local).resolve(), Path(shared)
    for repo in (local, shared):
        if not (repo / ".git").is_dir():
            raise UpdateError(f"{repo} is not a git checkout")
    if git(local, "status", "--porcelain"):
        raise UpdateError(f"{local} has uncommitted changes")
    branch = git(local, "symbolic-ref", "--short", "HEAD")
    new = git(local, "rev-parse", "HEAD")
    if upstream_check:
        up = git(local, "rev-parse", "@{upstream}", check=False)
        if up.returncode or up.stdout.decode().strip() != new:
            raise UpdateError(f"{local}: {branch} is not level with its upstream; push first")
    if git(shared, "symbolic-ref", "--short", "HEAD") != branch:
        raise UpdateError(f"{shared} is not on {branch}")
    old = git(shared, "rev-parse", "HEAD")
    if git(shared, "status", "--porcelain"):
        raise UpdateError(f"{shared} has changes of its own; look at them first")
    summary = {"local": str(local), "shared": str(shared), "branch": branch, "old": old, "new": new}
    if old == new:
        summary["result"] = "already current"
        return summary
    if git(local, "merge-base", "--is-ancestor", old, new, check=False).returncode:
        raise UpdateError(f"{shared} is at {old[:7]}, which is not an ancestor of {new[:7]}; not a fast-forward")
    head_ref = shared / ".git" / "refs" / "heads" / branch
    if not head_ref.is_file():
        raise UpdateError(f"{head_ref} is not a loose ref file; this script writes loose refs only")

    # git renames the finished pack from the local object store into place, so the directory it is written to
    # has to be on the same filesystem as the local repository: a directory inside its .git, removed afterwards
    with tempfile.TemporaryDirectory() as tmp, \
            tempfile.TemporaryDirectory(prefix="update-shared-clone-", dir=local / ".git") as pack_dir:
        tmp, pack_dir = Path(tmp), Path(pack_dir)
        # 2. the new objects, as one pack made locally
        objects = git(local, "rev-list", "--objects", f"{old}..{new}")
        packed = subprocess.run(["git", "-C", str(local), "pack-objects", "--quiet", str(pack_dir / "pack")],
                                input=(objects + "\n").encode(), capture_output=True)
        if packed.returncode:
            raise UpdateError("pack-objects failed: " + packed.stderr.decode(errors="replace").strip())
        copied = []
        for f in sorted(pack_dir.glob("pack-*")):
            target = shared / ".git" / "objects" / "pack" / f.name
            if not target.exists():
                put(target, f.read_bytes())
            copied.append(f.name)
        git(shared, "rev-list", "--objects", new)       # every object the new commit needs is there
        summary["pack_files"] = copied

        # 3. the refs
        put(head_ref, (new + "\n").encode())
        tracking = shared / ".git" / "refs" / "remotes" / "origin"
        if tracking.is_dir():
            put(tracking / branch, (new + "\n").encode())

        # 4. the working files and the index, from a fresh clone
        clone = tmp / "clone"
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", "--branch", branch, str(local), str(clone)],
                       check=True, capture_output=True)
        if git(clone, "rev-parse", "HEAD") != new:
            raise UpdateError("the temporary clone is not at the new commit")
        changes = subprocess.run(["git", "-C", str(local), "diff", "--name-status", "--no-renames", "-z", old, new],
                                 capture_output=True, check=True).stdout.decode().split("\0")
        written = removed = 0
        for status, name in zip(changes[0::2], changes[1::2]):
            target = shared / name
            if status == "D":
                if target.exists():
                    target.unlink()
                    removed += 1
            else:
                put(target, (clone / name).read_bytes())
                written += 1
        put(shared / ".git" / "index", (clone / ".git" / "index").read_bytes())
        summary.update(files_written=written, files_removed=removed)

    # 5. read-only verification
    if git(shared, "rev-parse", "HEAD") != new:
        raise UpdateError("the shared clone is not at the new commit after the update")
    dirty = git(shared, "status", "--porcelain")
    if dirty:
        raise UpdateError("the shared clone is not clean after the update:\n" + dirty)
    problems = git(shared, "fsck", "--connectivity-only", check=False)
    if problems.returncode:
        raise UpdateError("fsck: " + (problems.stdout + problems.stderr).decode(errors="replace").strip())
    summary["result"] = "fast-forwarded"
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("local")
    ap.add_argument("shared")
    ap.add_argument("--no-upstream-check", action="store_true",
                    help="do not require the local branch to be level with its upstream")
    args = ap.parse_args(argv)
    try:
        summary = update(args.local, args.shared, upstream_check=not args.no_upstream_check)
    except UpdateError as exc:
        print(f"update_shared_clone: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
