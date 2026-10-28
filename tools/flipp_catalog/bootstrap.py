"""Which entries bootstrap sends to a catalog server: every one in force, or
in update those the server does not hold. A newer version of an entry the
server holds reaches it the usual way, through publish of the manifest that
changed. With more than one server, an entry one of them lacks is sent to
all."""

from . import server
from .manifests import entries


def stale(mode: str) -> list[str]:
    listed = entries()
    if mode == "force":
        return [entry.rel for entry in listed]
    held = [server.held(base) for base in server.servers()]
    return [entry.rel for entry in listed if any((entry.family, entry.name) not in versions for versions in held)]
