"""application.fam as fbt reads it: App(...) blocks with comments dropped,
strings respected and parentheses balanced. The catalog's rule is that the
first App() is the entry's app; every other EXTERNAL one is another app of
the same entry, a PLUGIN is built into the app that requires it."""

import re
from dataclasses import dataclass
from pathlib import Path

FAM_NAME = "application.fam"
APP_START = re.compile(r"\bApp\s*\(")
FIELD_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
APPTYPE_RE = re.compile(r"apptype\s*=\s*FlipperAppType\.(\w+)")
VERSION_STRING_RE = re.compile(r'fap_version\s*=\s*"([^"]*)"')
VERSION_TUPLE_RE = re.compile(r"fap_version\s*=\s*[\(\[]([^\)\]]*)[\)\]]")


@dataclass(frozen=True)
class FamApp:
    appid: str
    apptype: str
    fields: dict
    block: str

    @property
    def name(self) -> str:
        return self.fields.get("name") or self.appid

    @property
    def version(self) -> str:
        """fap_version as fbt embeds it: a string, or a tuple of integers
        joined with dots; empty when absent."""
        string = VERSION_STRING_RE.search(self.block)
        if string:
            return string.group(1).strip()
        tuple_ = VERSION_TUPLE_RE.search(self.block)
        if tuple_:
            parts = [p.strip() for p in tuple_.group(1).split(",") if p.strip()]
            return ".".join(str(int(p)) if p.isdigit() else p for p in parts)
        return ""

    @property
    def file(self) -> str:
        """The file fbt leaves for it: a plugin is a .fal."""
        return f"{self.appid}.{'fal' if self.apptype == 'PLUGIN' else 'fap'}"


def strip_comments(text: str) -> str:
    out, quote, i = [], None, 0
    while i < len(text):
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _closing(text: str, start: int) -> int | None:
    depth, quote, i = 0, None, start
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def fam_apps(code: Path) -> list[FamApp]:
    """Every App() with an appid, in file order."""
    try:
        clean = strip_comments((code / FAM_NAME).read_text(errors="replace"))
    except OSError:
        return []
    out, position = [], 0
    while (match := APP_START.search(clean, position)) is not None:
        end = _closing(clean, match.end() - 1)
        if end is None:
            break
        block = clean[match.start():end]
        position = end
        fields = dict(FIELD_RE.findall(block))
        kind = APPTYPE_RE.search(block)
        if fields.get("appid"):
            out.append(FamApp(fields["appid"], kind.group(1) if kind else "", fields, block))
    return out


def write_entry_fam(code: Path, apps: list[FamApp], main: str, only_main: bool) -> list[FamApp]:
    """Rewrites application.fam so the entry's app comes first: alone for a
    menu style picked out of a repository of styles, else followed by the
    rest in their order. Returns the apps as written."""
    first = next(app for app in apps if app.appid == main)
    written = [first] if only_main else [first, *(app for app in apps if app.appid != main)]
    if written != apps:
        (code / FAM_NAME).write_text("\n\n".join(app.block for app in written) + "\n")
    return written
