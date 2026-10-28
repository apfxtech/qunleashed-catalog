"""One catalog entry: where its manifest lies, what the manifest says, and
the sources it points at. The path tells the family, the category and the id."""

import functools
import os
import re
import subprocess
from pathlib import Path

import yaml

from . import BundlerException

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = {"applications": "application", "menustyles": "menustyle", "animations": "animation"}
DOLPHIN_KEYS = ("min_butthurt", "max_butthurt", "min_level", "max_level", "weight")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
ANIMATION_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
MANIFEST_RE = re.compile(r"^(applications|menustyles|animations)/.+/manifest\.yml$")


def git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise BundlerException(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def trusted_origins() -> set[str]:
    """Repositories app-stream follows: their manifests may leave commit_sha
    to it, and their apps may need fbt, so a pull request does not build
    them with ufbt."""
    data = yaml.safe_load((ROOT / "trusted.yml").read_text()) or []
    return {str(url).strip().removesuffix(".git").lower() for url in data}


@functools.cache
def category_ids() -> dict[tuple[str, str], str]:
    """The id of every category categories.yml declares, by (family, "Root/Child")."""
    out = {}

    def walk(family: str, nodes, parent: str) -> None:
        for node in nodes or []:
            path = f"{parent}/{node['name']}" if parent else str(node["name"])
            out[(family, path)] = str(node["id"])
            walk(family, node.get("children"), path)

    for family, roots in (yaml.safe_load((ROOT / "categories.yml").read_text()) or {}).items():
        walk(family, roots, "")
    return out


def catalog_origin() -> str:
    if os.environ.get("GITHUB_REPOSITORY"):
        return f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}.git"
    return git(["remote", "get-url", "origin"], ROOT)


class Entry:
    def __init__(self, path: Path):
        self.path = path.resolve()
        rel = self.path.relative_to(ROOT).parts
        if len(rel) < 4 or rel[0] not in FAMILIES or rel[-1] != "manifest.yml":
            raise BundlerException(f"{path}: expected <family>/<category>[/<sub>]/<id>/manifest.yml")
        self.rel = "/".join(rel)
        self.dir = self.path.parent
        self.family = FAMILIES[rel[0]]
        self.category = "/".join(rel[1:-2])
        self.name = rel[-2]
        try:
            data = yaml.safe_load(self.path.read_text())
        except (OSError, yaml.YAMLError) as e:
            raise BundlerException(f"{self.rel}: {e}")
        if not isinstance(data, dict):
            raise BundlerException(f"{self.rel}: not a mapping")
        self.data = data
        location = (data.get("sourcecode") or {}).get("location") or {}
        self.type = (data.get("sourcecode") or {}).get("type", "git")
        self.origin = str(location.get("origin", "") or "").strip()
        self.commit_sha = str(location.get("commit_sha", "") or "").strip()
        self.subdir = str(location.get("subdir", "") or "").strip()

    @property
    def dir_rel(self) -> str:
        return self.dir.relative_to(ROOT).as_posix()

    @property
    def bundle_dir(self) -> Path:
        """What was last published of the entry, next to its manifest."""
        return self.dir / "bundle"

    @property
    def meta_path(self) -> Path:
        return self.dir / "bundle.json"

    @property
    def local(self) -> bool:
        """An animation whose files lie next to its manifest."""
        return not self.origin

    @property
    def pinned(self) -> bool:
        return self.local or bool(self.commit_sha)

    @property
    def trusted(self) -> bool:
        return self.local or self.origin.removesuffix(".git").lower() in trusted_origins()

    def validate(self) -> list[str]:
        errors = []
        top = self.category.split("/")[0]
        errors += [f"bad category folder: {p}" for p in self.category.split("/") if not NAME_RE.match(p)]
        if (self.family, self.category) not in category_ids():
            errors.append(f"category {self.category} is not declared in categories.yml")
        if not (ANIMATION_NAME_RE if self.family == "animation" else NAME_RE).match(self.name):
            errors.append(f"bad id folder: {self.name}")
        if "bundle" in self.rel.split("/")[1:-1]:
            errors.append("bundle is the folder a publish writes; no folder of the path may take that name")
        if self.type != "git":
            errors.append("sourcecode.type must be git")
        if self.local:
            if self.family != "animation":
                errors.append("sourcecode.location.origin is required")
            if self.commit_sha:
                errors.append("commit_sha without origin: the files next to the manifest are taken as they are")
        elif not self.origin.startswith("https://"):
            errors.append("sourcecode.location.origin must be an https git url")
        elif not self.commit_sha and not self.trusted:
            errors.append("commit_sha is required; app-stream sets it only for repositories in trusted.yml")
        if self.commit_sha and not SHA_RE.match(self.commit_sha):
            errors.append("commit_sha must be the full 40-character sha")
        category = self.data.get("category")
        if category is not None and str(category) not in (self.category, top):
            errors.append(f"category {category} does not match folder {self.category}")
        wanted = self.data.get("id")
        if wanted is not None and str(wanted) != self.name:
            errors.append(f"id {wanted} does not match folder {self.name}")
        if self.family == "animation":
            for key in DOLPHIN_KEYS:
                value = self.data.get(key)
                if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                    errors.append(f"{key} must be a non-negative integer")
        return errors
