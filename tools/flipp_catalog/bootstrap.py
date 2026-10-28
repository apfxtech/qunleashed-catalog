"""Which entries bootstrap sends to a catalog server: every one in force, or
in update those the server does not hold or holds at a version other than
the one this repository last published, as its bundle.json says. With more
than one server, an entry one of them lacks is sent to all."""

import json

from . import server
from .manifests import entries


def stale(mode: str) -> list[str]:
    listed = entries()
    if mode == "force":
        return [entry.rel for entry in listed]
    held = [server.held(base) for base in server.servers()]
    out = []
    for entry in listed:
        try:
            meta = json.loads(entry.meta_path.read_text())
        except (OSError, ValueError):
            out.append(entry.rel)  # never published from here
            continue
        key = (meta.get("family"), meta.get("id"))
        if any(versions.get(key) != meta.get("version") for versions in held):
            out.append(entry.rel)
    return out
