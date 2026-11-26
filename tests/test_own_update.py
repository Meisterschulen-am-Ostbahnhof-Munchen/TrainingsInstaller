"""Eigene Projekte aktualisieren: Vorlage mergen, bei Konflikt nur .lib; Firmware-Sperre (braucht git, kein Netz)."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trainings_installer import new_project, own_update, update  # noqa: E402
from trainings_installer.paths import Paths  # noqa: E402
from trainings_installer.report import Reporter  # noqa: E402

GIT = shutil.which("git")
WS = "Ventilsteuerung/4diacIDE-workspace"
TPL = "4diac_training1_empty"


class TPaths(Paths):
    @property
    def git_exe(self) -> Path:
        return Path(GIT)


def g(cwd: Path, *args: str) -> str:
    return subprocess.run([GIT, "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


@unittest.skipUnless(GIT, "git nicht gefunden")
class OwnUpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.origin = self.tmp / "origin"
        self.write_origin({".lib/fb.fbt": "v1", "Projekt/Main.SUB": "main v1", ".gitignore": ".metadata/\n"})
        g(self.origin, "tag", "v1")
        self.paths = TPaths(self.tmp / "sl")
        self.paths.ensure()
        self.m = {"repos": {TPL: {"url": str(self.origin), "ref": "v1", "workspace": WS,
                                  "template_for_new_projects": True}}}
        new_project.create(self.paths, self.m, "Maehwerk", Reporter())
        self.prj = self.paths.prj / "Maehwerk"
        self.ws = self.prj / WS
        for target in ("trainings_installer.winsys.running_ides",):
            p = mock.patch(target, return_value=[])
            p.start()
            self.addCleanup(p.stop)

    def write_origin(self, files: dict[str, str]) -> None:
        if not self.origin.exists():
            self.origin.mkdir()
            g(self.origin, "init", "-q", "-b", "main")
        for rel, text in files.items():
            f = self.origin / WS / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        g(self.origin, "add", "-A")
        g(self.origin, "commit", "-qm", "vorlage")

    def new_template(self, files: dict[str, str]) -> None:
        self.write_origin(files)
        g(self.origin, "tag", "v2")
        self.m["repos"][TPL]["ref"] = "v2"

    def test_only_template_projects(self):
        other = self.paths.prj / "Fremd"
        g(self.paths.prj, "clone", "-q", str(self.origin), "Fremd")
        g(other, "remote", "rename", "origin", "upstream")
        g(other, "remote", "set-url", "upstream", "https://example.invalid/anderes.git")
        names = [d.name for d in own_update.template_projects(self.paths, self.m)]
        self.assertEqual(names, ["Maehwerk"])

    def test_already_current(self):
        self.assertTrue(own_update.lib_current(self.paths, self.prj, self.m))
        res = own_update.update_own(self.paths, self.prj, self.m, "1")
        self.assertFalse(res.changed)

    def test_merge_keeps_own_files(self):
        (self.ws / "Projekt" / "Eigen.SUB").write_text("meins")          # neu, nicht committet
        (self.ws / ".metadata").mkdir()
        (self.ws / ".metadata" / "x").write_text("ide")
        self.new_template({".lib/fb.fbt": "v2", ".lib/neu.fbt": "neu"})
        self.assertFalse(own_update.lib_current(self.paths, self.prj, self.m))
        self.assertEqual(own_update.behind(self.paths, self.m), ["Maehwerk"])
        res = own_update.update_own(self.paths, self.prj, self.m, "20260101_000000")
        self.assertTrue(res.changed and res.committed and not res.lib_only)
        self.assertEqual((self.ws / "Projekt" / "Eigen.SUB").read_text(), "meins")
        self.assertEqual((self.ws / ".lib" / "fb.fbt").read_text(), "v2")
        self.assertTrue((self.ws / ".lib" / "neu.fbt").is_file())
        self.assertTrue(own_update.lib_current(self.paths, self.prj, self.m))
        self.assertIn("sicherung_20260101_000000", g(self.prj, "branch", "--list", "sicherung_*"))
        self.assertEqual(g(self.prj, "branch", "--show-current"), "arbeit")
        self.assertEqual(g(self.prj, "status", "--porcelain"), "")
        self.assertNotIn(".metadata", g(self.prj, "ls-files"))

    def test_conflict_updates_only_lib(self):
        main = self.ws / "Projekt" / "Main.SUB"
        main.write_text("meine Version")
        g(self.prj, "commit", "-qam", "eigen")
        self.new_template({".lib/fb.fbt": "v2", "Projekt/Main.SUB": "vorlage v2"})
        rep = Reporter()
        res = own_update.update_own(self.paths, self.prj, self.m, "1")
        own_update.report_own(res, rep)
        self.assertTrue(res.lib_only)
        self.assertEqual(main.read_text(), "meine Version")
        self.assertEqual((self.ws / ".lib" / "fb.fbt").read_text(), "v2")
        self.assertTrue(own_update.lib_current(self.paths, self.prj, self.m))
        self.assertFalse((self.prj / ".git" / "MERGE_HEAD").exists())
        self.assertEqual(g(self.prj, "status", "--porcelain"), "")
        self.assertTrue(rep.report.warnings)

    def test_not_on_arbeit_changes_nothing(self):
        g(self.prj, "switch", "-q", "-c", "anders")
        self.new_template({".lib/fb.fbt": "v2"})
        with self.assertRaises(own_update.OwnUpdateError):
            own_update.update_own(self.paths, self.prj, self.m, "1")
        self.assertEqual((self.ws / ".lib" / "fb.fbt").read_text(), "v1")

    def run_update(self, only=None):
        fw = (self.paths.root / "firmware.neu", {"build": "b"})
        with mock.patch("trainings_installer.core.load_manifest", return_value=self.m), \
                mock.patch("trainings_installer.firmware.prepare", return_value=fw), \
                mock.patch("trainings_installer.firmware.activate") as act:
            rep = Reporter()
            update.update(rep, self.paths, only)
        return rep, act

    def test_update_includes_own_project_and_firmware(self):
        self.new_template({".lib/fb.fbt": "v2"})
        rep, act = self.run_update()
        self.assertEqual((self.ws / ".lib" / "fb.fbt").read_text(), "v2")
        act.assert_called_once()

    def test_firmware_waits_for_own_project(self):
        self.new_template({".lib/fb.fbt": "v2"})
        g(self.prj, "switch", "-q", "-c", "anders")   # Update scheitert → .lib bleibt alt
        rep, act = self.run_update()
        act.assert_not_called()
        self.assertTrue(any("Maehwerk" in w and "firmware.neu" in w for w in rep.report.warnings))

    def test_update_single_own_project(self):
        self.new_template({".lib/fb.fbt": "v2"})
        rep, _ = self.run_update("Maehwerk")
        self.assertEqual(rep.report.errors, [])
        self.assertEqual((self.ws / ".lib" / "fb.fbt").read_text(), "v2")


if __name__ == "__main__":
    unittest.main()
