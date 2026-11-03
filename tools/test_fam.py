import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from flipp_catalog.assemble import _offered
from flipp_catalog.fam import fam_apps

FUZZER = """
App(
    appid="fuzzer_ibtn",
    name="iButton Fuzzer",  # (not a call)
    apptype=FlipperAppType.EXTERNAL,
    fap_version=(1, 4),
    fap_private_libs=[
        Lib(name="worker", cflags=["-Wno-error"], sources=["worker.c"]),
    ],
)
App(appid="fuzzer_rfid", name="RFID Fuzzer", apptype=FlipperAppType.EXTERNAL,
    fap_private_libs=[Lib(name="worker")])
App(appid="fuzzer_helper", name="Helper", apptype=FlipperAppType.PLUGIN)
"""


def apps_of(text: str):
    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / "application.fam").write_text(text)
        return fam_apps(Path(folder))


class TestFam(unittest.TestCase):
    def test_a_lib_name_is_not_the_apps(self):
        apps = apps_of(FUZZER)
        self.assertEqual([(a.appid, a.name, a.apptype) for a in apps], [
            ("fuzzer_ibtn", "iButton Fuzzer", "EXTERNAL"),
            ("fuzzer_rfid", "RFID Fuzzer", "EXTERNAL"),
            ("fuzzer_helper", "Helper", "PLUGIN"),
        ])
        self.assertEqual(apps[0].version, "1.4")


class TestOffered(unittest.TestCase):
    def offered(self, data: dict):
        apps = apps_of(FUZZER)
        problems = []
        return [a.appid for a in _offered(SimpleNamespace(data=data), apps, apps[0], problems)], problems

    def test_no_list_is_every_external_app(self):
        self.assertEqual(self.offered({}), (["fuzzer_ibtn", "fuzzer_rfid"], []))
        self.assertEqual(self.offered({"apps": []}), (["fuzzer_ibtn", "fuzzer_rfid"], []))

    def test_one_name_is_the_entrys_app_alone(self):
        self.assertEqual(self.offered({"apps": ["fuzzer_ibtn"]}), (["fuzzer_ibtn"], []))

    def test_more_names_are_variants(self):
        self.assertEqual(self.offered({"apps": ["fuzzer_ibtn", "fuzzer_rfid"]}), (["fuzzer_ibtn", "fuzzer_rfid"], []))

    def test_what_a_list_may_not_name(self):
        offered, problems = self.offered({"apps": ["fuzzer_rfid", "fuzzer_helper", "nope"]})
        self.assertEqual(offered, ["fuzzer_ibtn", "fuzzer_rfid"])
        self.assertEqual(problems, [
            "apps must start with fuzzer_ibtn, the entry's own app",
            "apps: fuzzer_helper is not an EXTERNAL App() of application.fam",
            "apps: nope is not an EXTERNAL App() of application.fam",
        ])
        self.assertEqual(self.offered({"apps": "fuzzer_ibtn"})[1], ["apps must be a list of appids"])
