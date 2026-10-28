"""What a pull request runs on each changed manifest, and what an author runs
before sending one: every rule, the apps application.fam gives the server,
and a ufbt build within a time limit for an app outside trusted.yml.
Nothing is written into the repository."""

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from . import BundlerException
from .assemble import assemble
from .entry import ROOT, Entry
from .fam import FamApp, fam_apps
from .manifests import entries
from .report import Line, Report
from .sources import Sources


def check(paths: list[str], report: Report, *, build: bool, offline: bool, timeout: int) -> int:
    seen: dict[tuple[str, str], list[str]] = {}
    for entry in entries():
        seen.setdefault((entry.family, entry.name), []).append(entry.rel)
    sources = Sources()
    try:
        for path in paths:
            report.add(_check(path, seen, sources, build, offline, timeout))
    finally:
        shutil.rmtree(sources.root, ignore_errors=True)
    report.save()
    return report.failed


def _check(path: str, seen: dict, sources: Sources, build: bool, offline: bool, timeout: int) -> Line:
    line = Line(manifest=path)
    try:
        entry = Entry(ROOT / path)
        line.errors += entry.validate()
        users = seen.get((entry.family, entry.name), [])
        if len(users) > 1:
            line.errors.append(f"id {entry.name} is used by {', '.join(users)}")
        if not offline and not line.errors:
            _assembled(entry, line, sources, build, timeout)
    except BundlerException as e:
        line.errors.append(str(e))
    line.status = "failed" if line.errors else "ok"
    return line


def _assembled(entry: Entry, line: Line, sources: Sources, build: bool, timeout: int) -> None:
    """The entry as a publish would send it, in a scratch folder. A trusted
    repository's entry is told what it lacks and goes through."""
    code, sha, origin = sources.checkout(entry)
    scratch = Path(tempfile.mkdtemp(prefix="bundle-"))
    try:
        found = assemble(entry, code, sha, origin, scratch / "bundle", scratch / "bundle.json")
        (line.warnings if entry.trusted else line.errors).extend(found)
        line.source = json.loads((scratch / "bundle.json").read_text())["links"]["source_code"]
        if entry.family == "animation":
            return
        line.apps = describe(fam_apps(scratch / "bundle" / "code"))
        if entry.trusted or entry.family != "application":
            line.build = "fbt on the server"
        elif build:
            line.build, error = ufbt_build(scratch / "bundle" / "code", timeout)
            if error:
                line.errors.append(error)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def describe(apps: list[FamApp]) -> list[str]:
    """The apps as the server takes them: the first is the entry's app, a
    later EXTERNAL one another app of the entry, a PLUGIN built in."""
    out = []
    for index, app in enumerate(apps):
        if index == 0:
            out.append(app.appid)
        elif app.apptype == "EXTERNAL":
            out.append(f"{app.appid} (extra)")
        else:
            out.append(f"{app.appid} ({app.apptype.lower() or 'no apptype'})")
    return out


def ufbt_build(code: Path, timeout: int) -> tuple[str, str | None]:
    """(what the report says, the error if any). ufbt runs in a process group
    of its own, so the time limit takes scons and the compilers down too."""
    started = time.monotonic()
    process = subprocess.Popen(["ufbt"], cwd=code, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               start_new_session=True)
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        return "timeout", f"the ufbt build took longer than {timeout} s"
    seconds = round(time.monotonic() - started)
    if process.returncode != 0:
        return "failed", f"the ufbt build failed:\n{output[-3000:]}"
    return f"ok, {seconds} s", None
