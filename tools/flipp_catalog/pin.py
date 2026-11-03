"""commit_sha written into a manifest the way an author would: that one line
changed, or added under origin, and the rest of the file left as it was."""

import re
from pathlib import Path

import yaml

from . import BundlerException

SHA_LINE = re.compile(r"^([ \t]+)commit_sha:.*$", re.M)
ORIGIN_LINE = re.compile(r"^([ \t]+)origin:.*$", re.M)


def set_commit_sha(path: Path, sha: str) -> None:
    text = path.read_text()
    if SHA_LINE.search(text):
        new = SHA_LINE.sub(lambda m: f"{m.group(1)}commit_sha: {sha}", text, count=1)
    elif (origin := ORIGIN_LINE.search(text)) is not None:
        new = f"{text[:origin.end()]}\n{origin.group(1)}commit_sha: {sha}{text[origin.end():]}"
    else:
        raise BundlerException(f"{path.name}: no origin line to put commit_sha under")
    location = (yaml.safe_load(new).get("sourcecode") or {}).get("location") or {}
    if str(location.get("commit_sha")) != sha:
        raise BundlerException(f"{path.name}: commit_sha could not be written in place; set it by hand")
    path.write_text(new)
