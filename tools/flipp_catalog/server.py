"""The catalog servers as the CI talks to them: the category tree, a bundle
folder sent file by file with its meta, an entry taken out, and what a
server holds."""

import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import yaml

from . import BundlerException
from .entry import ROOT


def servers() -> list[str]:
    """Where the CI sends: the one address QU_CATALOG_URL names, as bootstrap
    sets it, or else every domain servers.yml lists."""
    url = os.environ.get("QU_CATALOG_URL", "").strip().rstrip("/")
    if url:
        return [url]
    domains = (str(item).strip().rstrip("/") for item in yaml.safe_load((ROOT / "servers.yml").read_text()) or [])
    out = [domain if "://" in domain else f"https://{domain}" for domain in domains if domain]
    if not out:
        raise BundlerException("servers.yml lists no server")
    return out


def _request(base: str, method: str, path: str, body: bytes | None = None,
             content_type: str | None = None) -> tuple[int, str]:
    token = os.environ.get("QU_CI_TOKEN", "")
    if not token:
        raise BundlerException("QU_CI_TOKEN must be set")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "qunleashed-catalog-ci"}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(f"{base}{path}", data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return response.status, response.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        # The server restarting costs this entry, not the rest of the run.
        return 0, f"server unreachable: {e}"


def _multipart(meta: str | None, files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body = bytearray()
    if meta is not None:
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="meta"\r\n\r\n{meta}\r\n'.encode()
    for name, path in files.items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
                 "Content-Type: application/octet-stream\r\n\r\n").encode()
        body += path.read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def put_categories(base: str) -> tuple[int, str]:
    """categories.yml as a whole: the server replaces its tree with it."""
    body, content_type = _multipart(None, {"categories.yml": ROOT / "categories.yml"})
    return _request(base, "POST", "/api/v1/categories", body, content_type)


def put_bundle(base: str, meta_file: Path, folder: Path) -> tuple[int, str]:
    files = {path.relative_to(folder).as_posix(): path
             for path in sorted(p for p in folder.rglob("*") if p.is_file() and not p.is_symlink())}
    body, content_type = _multipart(meta_file.read_text(), files)
    return _request(base, "POST", "/api/v1/bundles", body, content_type)


def withdraw(base: str, family: str, entry_id: str) -> tuple[int, str]:
    return _request(base, "DELETE", f"/api/v1/bundles/{family}/{entry_id}")


def held(base: str) -> dict[tuple[str, str], str]:
    """{(family, id): version} of every entry the server holds, hidden ones too."""
    status, text = _request(base, "GET", "/api/v1/bundles")
    if status != 200:
        raise BundlerException(f"{host(base)} answered {status} to what it holds: {text[:500]}")
    return {(row["family"], row["id"]): row["version"] for row in json.loads(text)}



def host(base: str) -> str:
    return base.split("://", 1)[-1]
