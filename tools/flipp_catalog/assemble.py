"""The bundle folder of an entry and the meta that goes with it: exactly what
the catalog server receives and keeps. Written next to the manifest as
bundle/ and bundle.json, so this repository records what was published.

The meta names everything the server needs: the category's id, the install
path, the authors, the apps with their files and icons, the screenshots in
the manifest's order, an animation's files and its whole dolphin entry. The
server reads none of it from the folder and works none of it out.

One implementation for both uses: a pull request fails on any problem it
finds, a publish goes ahead and reports them."""

import hashlib
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from markdown import Markdown

from . import BundlerException, images
from .entry import DOLPHIN_KEYS, Entry, catalog_origin, category_ids
from .fam import fam_apps, write_entry_fam
from .markdown_filter import BasicFormattingEnforcingExtension

APP_ID_RE = re.compile(r"^[a-z0-9_]+$")
AUTHOR_RE = re.compile(r"@([A-Za-z0-9][A-Za-z0-9_.-]*)")
FRAME_RE = re.compile(r"^frame_\d+\.bm$")
FAP_VERSION_DEFAULT = "0.1"  # what fbt embeds when application.fam names none
MENUSTYLE_INSTALL_PATH = "/ext/apps_data/loader/plugins"
DOLPHIN_DEFAULTS = {"min_butthurt": 0, "max_butthurt": 14, "min_level": 1, "max_level": 30, "weight": 8}


def assemble(entry: Entry, code: Path, sha: str, origin: str, out: Path, meta_file: Path) -> list[str]:
    """Writes the bundle folder to out and its meta to meta_file, replacing
    what was there: the entry's bundle_dir and meta_path for a publish, a scratch
    folder for a check. Returns what is not right with the entry."""
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    if entry.family == "animation":
        meta, problems = _animation(entry, code, out)
    else:
        meta, problems = _app(entry, code, out)
    meta["links"] = {"source_code": source_url(origin, sha, entry.subdir if not entry.local else entry.dir_rel),
                     "manifest_uri": manifest_url(entry)}
    meta_file.write_text(json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return problems


def _app(entry: Entry, code: Path, out: Path) -> tuple[dict, list[str]]:
    problems: list[str] = []
    dest = out / "code"
    shutil.copytree(code, dest, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    for link in [p for p in dest.rglob("*") if p.is_symlink()]:
        link.unlink()  # never follow a link out of the author's tree
    main_id = str(entry.data.get("id") or entry.name)
    apps = fam_apps(dest)
    main = next((app for app in apps if app.appid == main_id), None)
    if main is None:
        raise BundlerException(f"application.fam has no App() with appid {main_id}")
    if entry.family == "application" and apps[0].appid != main_id:
        problems.append(f"the first App() of application.fam must be {main_id}, the entry's own app")
    apps = write_entry_fam(dest, apps, main_id, only_main=entry.family == "menustyle")
    version = str(entry.data.get("version") or main.version or "")
    if not version:
        problems.append("version is missing in both manifest.yml and application.fam")
        version = FAP_VERSION_DEFAULT
    if not APP_ID_RE.match(main_id):
        problems.append(f"id {main_id} is not lowercase [a-z0-9_]")
    name = str(entry.data.get("name") or main.name)
    short = str(entry.data.get("short_description") or main.fields.get("fap_description") or "")
    description = include(entry, code, "description")
    changelog = include(entry, code, "changelog")
    for label, value in (("short_description", short), ("description", description), ("changelog", changelog)):
        if not value.strip():
            problems.append(f"{label} is empty")
    problems += markdown_problems(description, changelog)

    icon = entry.data.get("icon") or main.fields.get("fap_icon")
    icon_rel = _picture(images.icon, code, str(icon), out, "assets/icon.png", problems) if icon else None
    if not icon and entry.family == "application":
        problems.append("no icon: fap_icon in application.fam")
    # The first App() and every later EXTERNAL one: a PLUGIN is built into
    # the app that requires it and is not offered on its own.
    offered = [apps[0], *(app for app in apps[1:] if app.apptype == "EXTERNAL")]
    meta_apps = []
    for position, app in enumerate(offered):
        own = None
        if position and app.fields.get("fap_icon"):
            own = _picture(images.icon, code, app.fields["fap_icon"], out, f"assets/apps/{app.appid}.png", problems)
        meta_apps.append({"appid": app.appid, "name": app.name if position else name,
                          "version": app.version or FAP_VERSION_DEFAULT, "file": app.file, "icon": own or icon_rel})
    shots = entry.data.get("screenshots") or []
    if not shots:
        problems.append("at least one screenshot is required")
    screenshots = [rel for index, src in enumerate(shots)
                   if (rel := _picture(images.screenshot, code, str(src), out, f"assets/screenshots/{index}.png", problems))]
    author = str(entry.data.get("author") or main.fields.get("fap_author") or "")
    return {
        "family": entry.family, "id": main_id, "version": version, "name": name, "category": entry.category,
        "category_id": category_ids().get((entry.family, entry.category), ""),
        "install_path": MENUSTYLE_INSTALL_PATH if entry.family == "menustyle" else entry.category,
        "author": author, "authors": authors(author), "short_description": short or name,
        "description": description or short or name, "changelog": changelog or f"v{version}",
        "icon": icon_rel, "screenshots": screenshots, "apps": meta_apps,
    }, problems


def _animation(entry: Entry, code: Path, out: Path) -> tuple[dict, list[str]]:
    if not (code / "meta.txt").is_file():
        raise BundlerException(f"no meta.txt in {entry.subdir or '.'}")
    frames = sorted(p for p in code.iterdir() if FRAME_RE.match(p.name))
    if not frames:
        raise BundlerException(f"no frame_*.bm in {entry.subdir or '.'}")
    files = [code / "meta.txt", *frames]
    digest = hashlib.sha256()
    for path in files:
        shutil.copy2(path, out / path.name)
        digest.update(path.name.encode() + b"\0" + path.read_bytes())
    dolphin = {key: entry.data[key] for key in DOLPHIN_KEYS if key in entry.data}
    digest.update(json.dumps(dolphin, sort_keys=True).encode())
    description = include(entry, code, "description")
    author = str(entry.data.get("author") or "")
    return {
        "family": "animation", "id": entry.name, "version": digest.hexdigest()[:12], "name": entry.name,
        "category": entry.category, "category_id": category_ids().get((entry.family, entry.category), ""),
        "install_path": f"/ext/dolphin/{entry.name}", "author": author, "authors": authors(author),
        "short_description": str(entry.data.get("short_description") or ""), "description": description,
        "changelog": "", "files": [path.name for path in files], "dolphin": {**DOLPHIN_DEFAULTS, **dolphin},
    }, markdown_problems(description)


def authors(author: str) -> list[dict]:
    """Every @name of the author line, in order, once."""
    out: list[dict] = []
    for name in AUTHOR_RE.findall(author):
        entry = {"id": name.lower(), "name": name}
        if entry not in out:
            out.append(entry)
    return out


def _picture(convert, code: Path, rel: str, out: Path, dest: str, problems: list[str]) -> str | None:
    """The picture converted to dest under the bundle folder; dest when it
    is there, None when the problem is named."""
    src = (code / rel).resolve()
    if not src.is_relative_to(code.resolve()) or not src.is_file():
        problems.append(f"file not found: {rel}")
        return None
    try:
        convert(src, out / dest)
    except BundlerException as e:
        problems.append(str(e))
        return None
    except OSError as e:
        problems.append(f"{rel}: {e}")
        return None
    return dest


def include(entry: Entry, code: Path, key: str) -> str:
    """A text as the manifest gives it, or the file it names with a leading @."""
    value = entry.data.get(key)
    if not isinstance(value, str) or not value.startswith("@"):
        return "" if value is None else str(value)
    target = (code / value[1:]).resolve()
    if not target.is_relative_to(code.resolve()) or not target.is_file():
        raise BundlerException(f"{key} file not found: {value[1:]}")
    return target.read_text(errors="replace")


def markdown_problems(*texts: str) -> list[str]:
    out = []
    for text in texts:
        try:
            Markdown(extensions=[BasicFormattingEnforcingExtension()]).convert(text)
        except Exception as e:
            out.append(f"markdown: {e}")
    return out


def source_url(origin: str, commit: str, subdir: str) -> str:
    """The entry's folder at the commit on the forge that hosts it."""
    base = origin.rstrip("/").removesuffix(".git")
    path = "" if subdir.strip("/") in ("", ".") else subdir.strip("/")
    host = (urlparse(base).hostname or "").lower()
    middle = f"/-/tree/{commit}" if "gitlab" in host else f"/src/commit/{commit}" if host == "codeberg.org" else f"/tree/{commit}"
    return f"{base}{middle}/{path}" if path else f"{base}{middle}"


def manifest_url(entry: Entry) -> str:
    """The manifest on the main branch: a link that does not move with every commit here."""
    base = catalog_origin().removesuffix(".git")
    return f"{base}/blob/main/{entry.rel}" if base.startswith("https://") else ""
