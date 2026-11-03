"""The code an entry points at. One clone per repository for a whole run:
every app of all-the-plugins comes out of the same clone, each at its own
commit, and only what a commit needs is fetched."""

import subprocess
import tempfile
from pathlib import Path

from . import BundlerException
from .entry import ROOT, Entry, catalog_origin, git


class Sources:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="catalog-clones-"))
        self._repos: dict[str, Path] = {}
        self._heads: dict[str, str] = {}
        self._at: dict[str, str] = {}

    def checkout(self, entry: Entry) -> tuple[Path, str, str]:
        """(code folder, commit, origin) of an entry. The folder holds until
        the next checkout from the same repository: take what is needed first."""
        if entry.local:
            # The last commit that changed the entry itself, not its bundle: the
            # link moves only when the animation does.
            here = entry.dir_rel
            sha = git(["log", "-1", "--format=%H", "--", here, f":!{here}/bundle", f":!{here}/bundle.json"], ROOT)
            return self._subdir(entry, entry.dir), sha or git(["rev-parse", "HEAD"], ROOT), catalog_origin()
        repo = self._repo(entry.origin)
        self._switch(entry.origin, entry.commit_sha or self._head(entry.origin))
        # A trusted entry app-stream has not pinned yet is taken at the commit
        # it would be pinned to.
        sha = entry.commit_sha or self.last_change(entry)
        return self._subdir(entry, repo), sha, entry.origin

    def last_change(self, entry: Entry) -> str:
        """The last commit on the repository HEAD that changed the entry's
        folder: what app-stream pins an entry of a trusted repository to."""
        head = self._head(entry.origin)
        path = entry.subdir.strip("/")
        if not path:
            return head
        sha = git(["log", "-1", "--format=%H", head, "--", path], self._repo(entry.origin))
        if not sha:
            raise BundlerException(f"{entry.rel}: {entry.subdir} is not in {entry.origin}")
        return sha

    def _repo(self, origin: str) -> Path:
        if origin not in self._repos:
            dest = Path(tempfile.mkdtemp(prefix="repo", dir=self.root))
            git(["init", "-q"], dest)
            git(["remote", "add", "origin", origin], dest)
            self._repos[origin] = dest
        return self._repos[origin]

    def _head(self, origin: str) -> str:
        if origin not in self._heads:
            repo = self._repo(origin)
            git(["fetch", "-q", "--filter=blob:none", "origin", "HEAD"], repo)
            self._heads[origin] = git(["rev-parse", "FETCH_HEAD"], repo)
        return self._heads[origin]

    def _switch(self, origin: str, sha: str) -> None:
        if self._at.get(origin) == sha:
            return
        repo = self._repo(origin)
        known = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=repo, capture_output=True)
        if known.returncode != 0:
            git(["fetch", "-q", "--filter=blob:none", "origin", sha], repo)
        git(["checkout", "-q", "-f", sha], repo)
        git(["clean", "-q", "-ffdx"], repo)
        git(["submodule", "update", "-q", "--init", "--recursive", "--depth", "1"], repo)
        self._at[origin] = sha

    @staticmethod
    def _subdir(entry: Entry, base: Path) -> Path:
        code = (base / entry.subdir).resolve() if entry.subdir else base.resolve()
        if not code.is_relative_to(base.resolve()):
            raise BundlerException(f"{entry.rel}: subdir escapes the repository")
        if not code.is_dir():
            raise BundlerException(f"{entry.rel}: subdir not found: {entry.subdir}")
        return code
