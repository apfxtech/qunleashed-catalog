"""What a run did to each entry. Every job of a run writes its own JSON file
and the last job puts them together: a pull request's comment, a run's
summary. An entry the server could not take for a reason of the server's
own is marked retry, and the run then leaves its commits to the next one."""

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

COMMENT_LIMIT = 60000  # GitHub takes 65536 characters in a comment


@dataclass
class Line:
    manifest: str
    status: str = ""
    apps: list[str] = field(default_factory=list)
    build: str = ""
    source: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Report:
    def __init__(self, path: str | None = None):
        self.path = Path(path) if path else None
        self.lines: list[Line] = []

    def add(self, line: Line) -> Line:
        """Kept, and told in the job's log the way the report will tell it."""
        self.lines.append(line)
        for text in line.warnings:
            print(f"::warning file={line.manifest}::{_escape(text)}")
        for text in line.errors:
            print(f"::error file={line.manifest}::{_escape(text)}")
        print(f"{line.status} {line.manifest}" + (f" ({line.build})" if line.build else ""))
        return line

    @property
    def failed(self) -> int:
        return sum(1 for line in self.lines if line.errors)

    def save(self) -> None:
        """Written once the job got through all of its entries: a job that
        did not leaves no file, and its run is not settled."""
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps([asdict(line) for line in self.lines], indent=1))

    @staticmethod
    def load(paths) -> list[Line]:
        return [Line(**row) for path in paths for row in json.loads(Path(path).read_text())]


def settled(paths: list[str], expected: int) -> bool:
    """Every job of the run reported, and the server took or refused each
    entry for a reason of the entry's own."""
    return len(paths) == expected and all(line.status != "retry" for line in Report.load(paths))


def markdown(title: str, lines: list[Line]) -> str:
    if not lines:
        return f"### {title}\n\nNothing to do.\n"
    counts = Counter(line.status for line in lines)
    # A column no entry has anything in, such as the build in a publish, is left out.
    columns = [("Entry", _entry), ("Apps (application.fam)", _apps), ("Build", lambda line: _cell(line.build)),
               ("Result", _result)]
    columns = [(name, cell) for name, cell in columns if any(cell(line) for line in lines)]
    out = [f"### {title}", "", ", ".join(f"{n} {status}" for status, n in sorted(counts.items())), "",
           "| " + " | ".join(name for name, _ in columns) + " |", "|" + "---|" * len(columns)]
    for line in lines:
        out.append("| " + " | ".join(cell(line) or "—" for _, cell in columns) + " |")
    out.append("")
    for line in lines:
        if line.errors or line.warnings:
            out += [f"<details><summary>{_folder(line)}</summary>", ""]
            out += [text for error in line.errors for text in _bullet("error", error)]
            out += [text for warning in line.warnings for text in _bullet("warning", warning)]
            out += ["", "</details>", ""]
    text = "\n".join(out)
    if len(text) > COMMENT_LIMIT:
        text = text[:COMMENT_LIMIT] + "\n\n</details>\n\nCut here: the log of the run has the rest.\n"
    return text


def _folder(line: Line) -> str:
    return line.manifest.removesuffix("/manifest.yml")


def _entry(line: Line) -> str:
    return f"[{_folder(line)}]({line.source})" if line.source else _folder(line)


def _apps(line: Line) -> str:
    return ", ".join(f"`{app}`" for app in line.apps)


def _result(line: Line) -> str:
    result = f"**{line.status}**" if line.status in ("failed", "retry") else line.status
    if line.warnings:
        result += f", {len(line.warnings)} warning{'s' if len(line.warnings) > 1 else ''}"
    return result


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _bullet(kind: str, text: str) -> list[str]:
    first, _, rest = text.partition("\n")
    out = [f"- {kind}: {first}"]
    if rest.strip():
        out += ["", "  ```", *(f"  {row}" for row in rest.rstrip().splitlines()), "  ```"]
    return out


def _escape(text: str) -> str:
    """A workflow command's message is one line."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
