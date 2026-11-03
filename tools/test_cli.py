"""The CLI entry reaches the server with a buildable plugin contract.

The sources live in their own repository; these tests assemble the entry from
a small tree written on the fly, so they need no network."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from flipp_catalog import BundlerException
from flipp_catalog.assemble import assemble
from flipp_catalog.check import _assembled
from flipp_catalog.entry import ROOT, Entry
from flipp_catalog.manifests import changed, entries
from flipp_catalog.report import Line
from flipp_catalog.sources import Sources

MANIFEST = "cli/Games/cli_tictactoe/manifest.yml"
BLACK = (0, 0, 0)
FAM = '''App(
    appid="cli_tictactoe",
    name="TicTacToe CLI",
    apptype=FlipperAppType.PLUGIN,
    entry_point="cli_tictactoe_ep",
    requires=["cli"],
    sources=["tictactoe.c"],
    fap_version="1.0",
    fap_author="@apfxtech",
    fap_icon="icon.png",
    fap_description="Play tic-tac-toe against minimax in the Flipper terminal",
)
'''


def write_sources(code: Path) -> Path:
    """What the entry's repository holds, as far as the catalog reads it."""
    (code / "screenshots").mkdir(parents=True)
    (code / "application.fam").write_text(FAM)
    (code / "tictactoe.c").write_text("int cli_tictactoe_ep(void) { return 0; }\n")
    Image.new("RGB", (10, 10), (255, 255, 255)).save(code / "icon.png")
    Image.new("RGB", (512, 256), BLACK).save(code / "screenshots/terminal.png")
    return code


class TestCli(unittest.TestCase):
    def setUp(self):
        self.entry = Entry(ROOT / MANIFEST)
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.out = Path(self.scratch.name)
        self.code = write_sources(self.out / "code")

    def test_sources_are_pinned_in_their_own_repository(self):
        self.assertEqual(self.entry.validate(), [])
        self.assertFalse(self.entry.local)
        self.assertEqual(self.entry.origin, "https://github.com/apfxtech/FlipCliTictactoe.git")
        self.assertFalse((self.entry.dir / "code").exists())

    def test_metadata(self):
        sha = "b" * 40
        problems = assemble(self.entry, self.code, sha, self.entry.origin, self.out / "bundle", self.out / "bundle.json")
        self.assertEqual(problems, [])
        meta = json.loads((self.out / "bundle.json").read_text())
        self.assertEqual(meta["family"], "cli")
        self.assertEqual(meta["category_id"], "games")
        self.assertEqual(meta["install_path"], "/ext/apps_data/cli/plugins")
        self.assertEqual(meta["version"], "1.0")
        self.assertEqual(meta["authors"], [{"id": "apfxtech", "name": "apfxtech"}])
        self.assertEqual(meta["apps"][0]["file"], "cli_tictactoe.fal")
        self.assertEqual(meta["links"]["source_code"], f"https://github.com/apfxtech/FlipCliTictactoe/tree/{sha}")
        self.assertEqual(len(meta["screenshots"]), 1)
        with Image.open(self.out / "bundle" / meta["screenshots"][0]) as image:
            self.assertEqual(image.size, (128, 64))
        self.assertTrue((self.out / "bundle/code/tictactoe.c").is_file())

    def test_cli_must_be_a_plugin_requiring_its_host(self):
        fam = self.code / "application.fam"
        for replacement, wanted in (
            (FAM.replace("FlipperAppType.PLUGIN", "FlipperAppType.EXTERNAL"), "FlipperAppType.PLUGIN"),
            (FAM.replace('requires=["cli"]', 'requires=["loader"]'), 'requires=["cli"]'),
        ):
            fam.write_text(replacement)
            problems = assemble(self.entry, self.code, "a" * 40, self.entry.origin,
                                self.out / "bundle", self.out / "bundle.json")
            self.assertTrue(any(wanted in problem for problem in problems), problems)

    def test_cli_metadata_problems_are_errors_not_warnings(self):
        self.entry.data["screenshots"] = []
        sources = Sources()
        self.addCleanup(shutil.rmtree, sources.root)
        line = Line(manifest=MANIFEST)
        with patch.object(sources, "checkout", return_value=(self.code, "a" * 40, self.entry.origin)):
            _assembled(self.entry, line, sources, build=False, timeout=60)
        self.assertIn("at least one screenshot is required", line.errors)
        self.assertEqual(line.warnings, [])

    def test_changes_to_nested_cli_files_republish_the_entry(self):
        diff = "M\tcli/Games/cli_tictactoe/notes/readme.txt\n"
        with patch("flipp_catalog.manifests.git", return_value=diff):
            self.assertEqual(changed("before", "after"), ([MANIFEST], []))
        with patch("flipp_catalog.manifests.git", return_value=f"D\t{MANIFEST}"):
            self.assertEqual(changed("before", "after"), ([], [MANIFEST]))

    def test_cli_is_discovered_but_kept_sources_cannot_escape_the_entry(self):
        self.assertIn(MANIFEST, [entry.rel for entry in entries(["cli"])])
        self.entry.origin = ""
        self.entry.subdir = "../../../../"
        sources = Sources()
        self.addCleanup(shutil.rmtree, sources.root)
        with self.assertRaisesRegex(BundlerException, "subdir escapes"):
            sources.checkout(self.entry)


if __name__ == "__main__":
    unittest.main()
