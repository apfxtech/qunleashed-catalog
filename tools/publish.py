import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FAMILIES = {"applications": "application", "menustyles": "menustyle", "animations": "animation"}
APP_CATEGORIES = {"Sub-GHz", "RFID", "NFC", "Infrared", "GPIO", "iButton", "USB", "Games", "Media", "Tools", "Bluetooth"}
MENUSTYLE_CATEGORIES = {"Layouts", "Themes", "Functional", "Animated"}
DOLPHIN_KEYS = ("min_butthurt", "max_butthurt", "min_level", "max_level", "weight")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
ANIMATION_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
FRAME_RE = re.compile(r"^frame_\d+\.bm$")
MANIFEST_GLOB = re.compile(r"^(applications|menustyles|animations)/.+/manifest\.yml$")


class CatalogError(Exception):
    pass


class Entry:
    def __init__(self, path: Path):
        self.path = path.resolve()
        rel = self.path.relative_to(ROOT).parts
        if len(rel) < 4 or rel[0] not in FAMILIES or rel[-1] != "manifest.yml":
            raise CatalogError(f"{path}: expected <family>/<category>[/<sub>]/<id>/manifest.yml")
        self.rel = "/".join(rel)
        self.family = FAMILIES[rel[0]]
        self.category = "/".join(rel[1:-2])
        self.name = rel[-2]
        try:
            data = yaml.safe_load(self.path.read_text())
        except (OSError, yaml.YAMLError) as e:
            raise CatalogError(f"{self.rel}: {e}")
        if not isinstance(data, dict):
            raise CatalogError(f"{self.rel}: not a mapping")
        self.data = data
        source = data.get("sourcecode") or {}
        location = source.get("location") or {}
        self.type = source.get("type", "git")
        self.origin = str(location.get("origin", "") or "").strip()
        self.commit_sha = str(location.get("commit_sha", "") or "").strip()
        self.subdir = str(location.get("subdir", "") or "").strip()

    @property
    def local(self) -> bool:
        return not self.origin

    @property
    def pinned(self) -> bool:
        return self.local or bool(self.commit_sha)

    def validate(self) -> list[str]:
        errors = []
        top = self.category.split("/")[0]
        for part in self.category.split("/"):
            if not NAME_RE.match(part):
                errors.append(f"bad category folder: {part}")
        if self.family == "application" and top not in APP_CATEGORIES:
            errors.append(f"unknown category: {top}")
        if self.family == "menustyle" and top not in MENUSTYLE_CATEGORIES:
            errors.append(f"unknown menu style category: {top}")
        name_re = ANIMATION_NAME_RE if self.family == "animation" else NAME_RE
        if not name_re.match(self.name):
            errors.append(f"bad id folder: {self.name}")
        if self.type != "git":
            errors.append("sourcecode.type must be git")
        if self.local:
            if self.family != "animation":
                errors.append("sourcecode.location.origin is required")
            if self.commit_sha:
                errors.append("commit_sha without origin: the files next to the manifest are taken as they are")
        elif not self.origin.startswith("https://"):
            errors.append("sourcecode.location.origin must be an https git url")
        if self.commit_sha and not SHA_RE.match(self.commit_sha):
            errors.append("commit_sha must be the full 40-character sha")
        category = self.data.get("category")
        if category is not None and str(category) not in (self.category, top):
            errors.append(f"category {category} does not match folder {self.category}")
        wanted = self.data.get("id")
        if self.family != "menustyle" and wanted is not None and str(wanted) != self.name:
            errors.append(f"id {wanted} does not match folder {self.name}")
        if self.family == "animation":
            for key in DOLPHIN_KEYS:
                value = self.data.get(key)
                if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                    errors.append(f"{key} must be a non-negative integer")
        return errors


def git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise CatalogError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def catalog_origin() -> str:
    if os.environ.get("GITHUB_REPOSITORY"):
        return f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}.git"
    return git(["remote", "get-url", "origin"], ROOT)


def resolve_subdir(entry: Entry, base: Path) -> Path:
    code = (base / entry.subdir).resolve() if entry.subdir else base.resolve()
    if not code.is_relative_to(base.resolve()):
        raise CatalogError(f"{entry.rel}: subdir escapes the repository")
    if not code.is_dir():
        raise CatalogError(f"{entry.rel}: subdir not found: {entry.subdir}")
    return code


def checkout(entry: Entry, dest: Path) -> tuple[Path, str, str]:
    if entry.local:
        return resolve_subdir(entry, entry.path.parent), git(["rev-parse", "HEAD"], ROOT), catalog_origin()
    dest.mkdir(parents=True, exist_ok=True)
    git(["init", "-q"], dest)
    git(["remote", "add", "origin", entry.origin], dest)
    git(["fetch", "-q", "--depth", "1", "origin", entry.commit_sha or "HEAD"], dest)
    git(["-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD"], dest)
    git(["submodule", "update", "--init", "--recursive", "--depth", "1"], dest)
    return resolve_subdir(entry, dest), git(["rev-parse", "HEAD"], dest), entry.origin


def include(entry: Entry, code: Path, key: str) -> str:
    value = entry.data.get(key)
    if not isinstance(value, str) or not value.startswith("@"):
        return "" if value is None else str(value)
    target = (code / value[1:]).resolve()
    if not target.is_relative_to(code) or not target.is_file():
        raise CatalogError(f"{entry.rel}: {key} file not found: {value[1:]}")
    return target.read_text(errors="replace")


def check_sources(entry: Entry, code: Path) -> None:
    if entry.family == "animation":
        if not (code / "meta.txt").is_file():
            raise CatalogError(f"{entry.rel}: no meta.txt in {entry.subdir or '.'}")
        if not any(FRAME_RE.match(p.name) for p in code.iterdir()):
            raise CatalogError(f"{entry.rel}: no frame_*.bm in {entry.subdir or '.'}")
        include(entry, code, "description")
        return
    if not (code / "application.fam").is_file():
        raise CatalogError(f"{entry.rel}: no application.fam in {entry.subdir or '/'}")
    for key in ("description", "changelog"):
        include(entry, code, key)
    for shot in entry.data.get("screenshots") or []:
        target = (code / str(shot)).resolve()
        if not target.is_relative_to(code) or not target.is_file():
            raise CatalogError(f"{entry.rel}: screenshot not found: {shot}")


def animation_bundle(entry: Entry, code: Path, sha: str, origin: str, out: Path) -> None:
    manifest = {
        "id": entry.name,
        "category": entry.category,
        "sourcecode": {"type": "git", "location": {"origin": origin, "commit_sha": sha, "subdir": entry.subdir or "."}},
    }
    for key in ("author", "short_description"):
        if entry.data.get(key):
            manifest[key] = str(entry.data[key])
    description = include(entry, code, "description")
    if description:
        manifest["description"] = description
    for key in DOLPHIN_KEYS:
        if key in entry.data:
            manifest[key] = entry.data[key]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.yml", yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
        archive.write(code / "meta.txt", "meta.txt")
        for frame in sorted(p for p in code.iterdir() if FRAME_RE.match(p.name)):
            archive.write(frame, frame.name)


def source_zip(entry: Entry, code: Path, out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(code.rglob("*")):
            rel = path.relative_to(code)
            if path.is_symlink() or any(part.startswith(".git") for part in rel.parts):
                continue
            if path.is_file() and rel.as_posix() != "manifest.yml":
                archive.write(path, rel.as_posix())
        archive.write(entry.path, "manifest.yml")


def multipart(fields: dict, file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
    body += (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{file_path.name}\"\r\n"
        "Content-Type: application/zip\r\n\r\n"
    ).encode()
    body += file_path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def server() -> tuple[str, str]:
    url = os.environ.get("QU_CATALOG_URL", "").rstrip("/")
    token = os.environ.get("QU_CI_TOKEN", "")
    if not url or not token:
        raise CatalogError("QU_CATALOG_URL and QU_CI_TOKEN must be set")
    return url, token


def request(method: str, url: str, token: str, body: bytes | None = None, content_type: str | None = None) -> tuple[int, str]:
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "qunleashed-catalog-ci"}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            return response.status, response.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def batches(paths: list[str], size: int) -> list:
    if size <= 0:
        return paths
    return [paths[i : i + size] for i in range(0, len(paths), size)]


def cmd_changed(args) -> int:
    out = git(["diff", "--name-status", "--no-renames", args.base, args.head], ROOT)
    changed, deleted = set(), []
    for line in out.splitlines():
        status, _, path = line.partition("\t")
        if MANIFEST_GLOB.match(path):
            if status == "D":
                deleted.append(path)
            else:
                changed.add(path)
        elif path.startswith("animations/") and (ROOT / Path(path).parent / "manifest.yml").is_file():
            changed.add((Path(path).parent / "manifest.yml").as_posix())
    changed = sorted(changed)
    print(json.dumps({"changed": changed, "batches": batches(changed, args.batch), "deleted": deleted}))
    return 0


def cmd_list(args) -> int:
    paths = sorted(p.relative_to(ROOT).as_posix() for family in FAMILIES for p in (ROOT / family).rglob("manifest.yml"))
    if args.unpinned:
        paths = [p for p in paths if not Entry(ROOT / p).pinned]
    print(json.dumps(batches(paths, args.batch)))
    return 0


def prepare(path: str, tmp: Path) -> tuple[Entry, Path, str, str]:
    entry = Entry(Path(path))
    errors = entry.validate()
    if errors:
        raise CatalogError(f"{entry.rel}: " + "; ".join(errors))
    code, sha, origin = checkout(entry, tmp / "src")
    check_sources(entry, code)
    return entry, code, sha, origin


def cmd_check(args) -> int:
    failed = 0
    for path in args.manifests:
        try:
            if args.offline:
                entry = Entry(Path(path))
                errors = entry.validate()
                if errors:
                    raise CatalogError(f"{entry.rel}: " + "; ".join(errors))
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    entry, *_ = prepare(path, Path(tmp))
            print(f"ok {entry.rel}" + ("" if entry.pinned else " (HEAD)"))
        except CatalogError as e:
            failed += 1
            print(f"::error file={path}::{e}")
    return 1 if failed else 0


def cmd_publish(args) -> int:
    url, token = server()
    failed = 0
    for path in args.manifests:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                entry, code, sha, origin = prepare(path, Path(tmp))
                zip_path = Path(tmp) / "upload.zip"
                if entry.family == "animation":
                    animation_bundle(entry, code, sha, origin, zip_path)
                    body, content_type = multipart({}, "bundle", zip_path)
                    endpoint = "/api/v1/animations/version/bundle"
                else:
                    source_zip(entry, code, zip_path)
                    fields = {"family": entry.family, "origin": "unleashed", "category": entry.category,
                              "commit_sha": sha, "origin_url": origin}
                    body, content_type = multipart(fields, "source", zip_path)
                    endpoint = "/api/v1/sources/upload"
                status, text = request("POST", f"{url}{endpoint}", token, body, content_type)
            if status not in (200, 201):
                raise CatalogError(f"{entry.rel}: server answered {status}: {text[:500]}")
            print(f"{'published' if status == 201 else 'unchanged'} {entry.rel} {text}")
        except CatalogError as e:
            failed += 1
            print(f"::error file={path}::{e}")
    return 1 if failed else 0


def cmd_delete(args) -> int:
    url, token = server()
    failed = 0
    for path in args.manifests:
        parts = Path(path).parts
        if len(parts) < 4 or parts[0] not in FAMILIES:
            continue
        family, name = FAMILIES[parts[0]], parts[-2]
        if family != "application":
            print(f"::warning file={path}::the server has no delete for {family} yet, hide it with the admin api")
            continue
        status, text = request("DELETE", f"{url}/api/v0/application/{name}", token)
        if status not in (200, 404):
            failed += 1
            print(f"::error file={path}::server answered {status}: {text[:500]}")
        else:
            print(f"hidden {path}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="publish.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("changed")
    p.add_argument("base")
    p.add_argument("head")
    p.add_argument("--batch", type=int, default=0)
    p.set_defaults(func=cmd_changed)
    p = sub.add_parser("list")
    p.add_argument("--unpinned", action="store_true")
    p.add_argument("--batch", type=int, default=0)
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("check")
    p.add_argument("--offline", action="store_true")
    p.add_argument("manifests", nargs="+")
    p.set_defaults(func=cmd_check)
    p = sub.add_parser("publish")
    p.add_argument("manifests", nargs="+")
    p.set_defaults(func=cmd_publish)
    p = sub.add_parser("delete")
    p.add_argument("manifests", nargs="+")
    p.set_defaults(func=cmd_delete)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
