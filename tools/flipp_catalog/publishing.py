"""What publish runs on the manifests a push to main changed: each entry
assembled into a scratch folder and sent to every catalog server; a deleted
manifest's entry taken out of every server. Nothing of a bundle is kept in
this repository: the servers hold it. A server that cannot be reached or
fails on its own side is a retry, not the entry's fault."""

import json
import shutil
import tempfile
from pathlib import Path

from . import BundlerException, server
from .assemble import assemble
from .entry import FAMILIES, ROOT, Entry
from .manifests import entries
from .report import Line, Report
from .sources import Sources


def publish(paths: list[str], report: Report) -> int:
    sources = Sources()
    try:
        for path in paths:
            report.add(_publish(path, sources))
    finally:
        shutil.rmtree(sources.root, ignore_errors=True)
    report.save()
    return report.failed


def _publish(path: str, sources: Sources) -> Line:
    line = Line(manifest=path)
    if not (ROOT / path).is_file():
        line.status = "skipped"
        line.warnings.append("the manifest is gone since; its deletion takes the entry out")
        return line
    scratch = Path(tempfile.mkdtemp(prefix="bundle-"))
    try:
        entry = Entry(ROOT / path)
        errors = entry.validate()
        if errors:
            raise BundlerException("; ".join(errors))
        code, sha, origin = sources.checkout(entry)
        folder, meta = scratch / "bundle", scratch / "bundle.json"
        line.warnings += assemble(entry, code, sha, origin, folder, meta)
        line.source = json.loads(meta.read_text())["links"]["source_code"]
        refusals, created = [], False
        for base in server.servers():
            status, text = server.put_bundle(base, meta, folder)
            if status in (200, 201):
                created |= status == 201
            else:
                refusals.append(status)
                line.errors.append(f"{server.host(base)} answered {status}: {text[:500]}")
        line.status = _outcome(refusals, "published" if created else "refreshed")
    except BundlerException as e:
        line.status = "failed"
        line.errors.append(str(e))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
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


def _outcome(refusals: list[int], done: str) -> str:
    """Done when every server took it. A server that refused it fails the
    entry; one that could not be reached or failed on its own side makes it
    a retry, and the next run sends it to every server again."""
    if not refusals:
        return done
    return "retry" if all(status == 0 or status >= 500 for status in refusals) else "failed"
