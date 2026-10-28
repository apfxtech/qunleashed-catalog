"""What publish runs on the manifests a push to main changed: each entry
assembled into bundle/ and bundle.json next to its manifest and sent to
every catalog server when they differ from what the repository holds; a
deleted manifest's entry taken out of every server. A server that cannot be
reached or fails on its own side is a retry, not the entry's fault."""

import json
import shutil
import subprocess
from pathlib import Path

from . import BundlerException, server
from .assemble import assemble
from .entry import FAMILIES, ROOT, Entry, git
from .manifests import entries
from .report import Line, Report
from .sources import Sources


def publish(paths: list[str], report: Report, *, force: bool) -> int:
    sources = Sources()
    try:
        for path in paths:
            report.add(_publish(path, sources, force))
    finally:
        shutil.rmtree(sources.root, ignore_errors=True)
    report.save()
    return report.failed


def _publish(path: str, sources: Sources, force: bool) -> Line:
    line = Line(manifest=path)
    if not (ROOT / path).is_file():
        line.status = "skipped"
        line.warnings.append("the manifest is gone since; its deletion takes the entry out")
        return line
    entry = None
    try:
        entry = Entry(ROOT / path)
        errors = entry.validate()
        if errors:
            raise BundlerException("; ".join(errors))
        code, sha, origin = sources.checkout(entry)
        line.warnings += assemble(entry, code, sha, origin, entry.bundle_dir, entry.meta_path)
        line.source = json.loads(entry.meta_path.read_text())["links"]["source_code"]
        if not force and not changed_on_disk(entry):
            line.status = "unchanged"
            return line
        refusals, created = [], False
        for base in server.servers():
            status, text = server.put_bundle(base, entry.meta_path, entry.bundle_dir)
            if status in (200, 201):
                created |= status == 201
            else:
                refusals.append(status)
                line.errors.append(f"{server.host(base)} answered {status}: {text[:500]}")
        line.status = _outcome(refusals, "published" if created else "refreshed")
        if not refusals:
            return line
    except BundlerException as e:
        line.status = "failed"
        line.errors.append(str(e))
    if entry is not None:
        restore(entry)
    return line


def withdraw(paths: list[str], report: Report) -> int:
    """Deleted manifests. One whose id another manifest took over, such as
    a manifest moved into another folder, leaves the server alone: the entry
    goes on under the other manifest."""
    remaining = {(entry.family, entry.name) for entry in entries()}
    servers = server.servers()
    for path in paths:
        parts = Path(path).parts
        if len(parts) < 4 or parts[0] not in FAMILIES:
            continue
        family, name = FAMILIES[parts[0]], parts[-2]
        line = Line(manifest=path)
        if (family, name) in remaining:
            line.status = "kept"
            line.warnings.append(f"another manifest has {name}")
        else:
            refusals = []
            for base in servers:
                status, text = server.withdraw(base, family, name)
                if status not in (200, 404):
                    refusals.append(status)
                    line.errors.append(f"{server.host(base)} answered {status}: {text[:500]}")
            line.status = _outcome(refusals, "withdrawn")
        report.add(line)
    report.save()
    return report.failed


def prune() -> list[str]:
    """Bundles left without a manifest next to them, removed: what a
    deleted manifest leaves behind."""
    found = set()
    for tree in FAMILIES:
        if (ROOT / tree).is_dir():
            for path in [*(ROOT / tree).rglob("bundle.json"), *(ROOT / tree).rglob("bundle")]:
                if "bundle" not in path.parent.relative_to(ROOT).parts:  # not a file of a bundle itself
                    found.add(path.parent)
    gone = []
    for folder in sorted(found):
        if not (folder / "manifest.yml").is_file():
            shutil.rmtree(folder / "bundle", ignore_errors=True)
            (folder / "bundle.json").unlink(missing_ok=True)
            gone.append(folder.relative_to(ROOT).as_posix())
    return gone


def changed_on_disk(entry: Entry) -> bool:
    paths = [str(entry.bundle_dir), str(entry.meta_path)]
    return bool(git(["status", "--porcelain", "--", *paths], ROOT))


def restore(entry: Entry) -> None:
    """Back to what this repository holds: the entry stays as it was last
    published, and the next run or a bootstrap sends it again."""
    paths = [str(entry.bundle_dir), str(entry.meta_path)]
    subprocess.run(["git", "checkout", "-q", "--", *paths], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "clean", "-fdq", "--", *paths], cwd=ROOT, capture_output=True)


def _outcome(refusals: list[int], done: str) -> str:
    """Done when every server took it. A server that refused it fails the
    entry; one that could not be reached or failed on its own side makes it
    a retry, and the next run sends it to every server again."""
    if not refusals:
        return done
    return "retry" if all(status == 0 or status >= 500 for status in refusals) else "failed"
