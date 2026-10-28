"""Which manifests a run works on: every one the catalog publishes, or the
ones a range of commits changed."""

import sys
from pathlib import Path

from . import BundlerException
from .entry import FAMILIES, MANIFEST_RE, ROOT, Entry, git


def manifests(trees=FAMILIES) -> list[Path]:
    """The manifests of the trees; one in the code a bundle carries is the
    author's, not ours."""
    return sorted(p for tree in trees if (ROOT / tree).is_dir() for p in (ROOT / tree).rglob("manifest.yml")
                  if not in_bundle(p.relative_to(ROOT).as_posix()))


def entries(trees=FAMILIES) -> list[Entry]:
    """The manifests that read; one that does not is named on stderr, where
    it stays out of a command's JSON, and left out."""
    out = []
    for path in manifests(trees):
        try:
            out.append(Entry(path))
        except BundlerException as e:
            print(f"::warning file={path.relative_to(ROOT)}::{e}", file=sys.stderr)
    return out


def in_bundle(path: str) -> bool:
    """A file of a bundle this repository once kept, not one an author wrote.
    The history still names them, the commit that removed them first of all:
    a manifest.yml of the code a bundle carried is not a deleted manifest."""
    parts = path.split("/")
    return "bundle" in parts[:-1] or parts[-1] == "bundle.json"


def changed(base: str, head: str) -> tuple[list[str], list[str]]:
    """(changed, deleted) manifests between two commits. A file next to a
    manifest of an animation kept in this repository changes that manifest."""
    out = git(["diff", "--name-status", "--no-renames", base, head], ROOT)
    changes, deleted = set(), []
    for line in out.splitlines():
        status, _, path = line.partition("\t")
        if in_bundle(path):
            continue
        if MANIFEST_RE.match(path):
            (deleted.append(path) if status == "D" else changes.add(path))
        elif path.startswith("animations/") and (ROOT / Path(path).parent / "manifest.yml").is_file():
            changes.add((Path(path).parent / "manifest.yml").as_posix())
    return sorted(changes), deleted


def batches(paths: list[str], size: int) -> list[list[str]]:
    return [paths[i:i + size] for i in range(0, len(paths), size)]
