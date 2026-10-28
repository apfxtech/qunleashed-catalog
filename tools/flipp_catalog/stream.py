"""What app-stream brings into the repository once a day: the official
catalog's manifests we have none of or hold an older copy of, and every
entry of a repository in trusted.yml pinned to the last commit that changed
its app. Its push to main is what publish then sends."""

import hashlib
import shutil
from pathlib import Path

from . import BundlerException
from .entry import ROOT, git
from .manifests import entries, manifests
from .pin import set_commit_sha
from .sources import Sources


def sync_ofw(upstream: Path) -> None:
    """A manifest of flipper-application-catalog for an app we have none of
    is copied to the path it has there, applications/<Category>/<appid>.
    Ours is replaced by the official one when it is, byte for byte, a version
    the official one once was; one that differs from all of them is ours."""
    ours = {path.parent.name: path for path in manifests(["applications"])}
    versions = _versions(upstream)
    for src in sorted((upstream / "applications").rglob("manifest.yml")):
        own = ours.get(src.parent.name)
        if own is None:
            _copy(src, ROOT / src.relative_to(upstream))
        elif _blob(own) in versions.get(src.parent.name, ()):
            _copy(src, own)


def pin() -> None:
    """An entry whose folder is gone from its repository is named and left
    as it is: the rest of the stream still goes through."""
    sources = Sources()
    try:
        for entry in entries():
            if entry.local or not entry.trusted:
                continue
            try:
                sha = sources.last_change(entry)
                if sha != entry.commit_sha:
                    set_commit_sha(entry.path, sha)
                    print(f"pinned {entry.rel} {sha[:12]}")
            except BundlerException as e:
                print(f"::warning file={entry.rel}::{e}")
    finally:
        shutil.rmtree(sources.root, ignore_errors=True)


def _versions(repo: Path) -> dict[str, set[str]]:
    """The blob of every version each app's manifest has had, by app id. The
    history's trees name them, so a clone without blobs does."""
    out = git(["log", "--format=", "--raw", "--no-abbrev", "--no-renames", "--", "applications"], repo)
    versions: dict[str, set[str]] = {}
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        if path.endswith("/manifest.yml"):
            _, _, old, new, _ = meta.split()
            versions.setdefault(Path(path).parent.name, set()).update({old, new} - {"0" * 40})
    return versions


def _blob(path: Path) -> str:
    """The id git gives the file's content."""
    content = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()


def _copy(src: Path, dest: Path) -> None:
    content = src.read_bytes()
    if dest.is_file() and dest.read_bytes() == content:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    print(f"synced {dest.relative_to(ROOT).as_posix()}")
