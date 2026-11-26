"""--uninstall: entfernt nur Eigenes; prj nur ohne Schülerarbeit (braucht git im PATH, kein Netz)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trainings_installer import uninstall  # noqa: E402
from trainings_installer.paths import Paths  # noqa: E402
from trainings_installer.report import Reporter  # noqa: E402

GIT = shutil.which("git")
REPO = "4diac_training1"   # muss im echten Manifest stehen


class TPaths(Paths):
    @property
    def git_exe(self) -> Path:
        return Path(GIT)


def g(cwd: Path, *args: str) -> str:
    return subprocess.run([GIT, "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


@unittest.skipUnless(GIT, "git nicht gefunden")
class UninstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.m = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        origin = self.tmp / "origin"
        origin.mkdir()
        g(origin, "init", "-q", "-b", "main")
        (origin / "a.txt").write_text("a")
        g(origin, "add", "-A")
        g(origin, "commit", "-qm", "v")
        g(origin, "tag", "v1")
        self.paths = TPaths(self.tmp / "sl")
        self.paths.ensure()
        self.repo = self.paths.prj / REPO
        g(self.paths.prj, "clone", "-q", "--branch", "v1", str(origin), REPO)
        g(self.repo, "switch", "-q", "-c", "arbeit")
        for d in (self.paths.python, self.paths.git / "cmd", self.paths.ide, self.paths.firmware,
                  self.paths.installer):
            d.mkdir(parents=True, exist_ok=True)
            (d / "x").write_text("x")
        (self.paths.logs / "install_1.log").write_text("l")
        self.lnk_dir = self.tmp / "start"
        self.lnk_dir.mkdir()
        self.own = self.tmp / "desk" / "4diac IDE.lnk"
        self.foreign = self.tmp / "desk" / "Fremd.lnk"
        self.own.parent.mkdir()
        self.own.write_text("o")
        self.foreign.write_text("f")
        self.paths.shortcuts_json.write_text(json.dumps([str(self.own)]), encoding="utf-8")
        for target, kw in (("trainings_installer.winsys.running_ides", {"return_value": []}),
                           ("trainings_installer.winsys.remove_user_path", {"return_value": True}),
                           ("trainings_installer.winsys.start_menu_dir", {"return_value": self.lnk_dir})):
            p = mock.patch(target, **kw)
            p.start()
            self.addCleanup(p.stop)

    def test_clean_repo_is_no_work(self):
        self.assertEqual(uninstall.student_work(self.paths, self.m), [])

    def test_work_detected(self):
        (self.repo / "neu.SUB").write_text("x")
        g(self.repo, "branch", "sicherung_1")
        (self.paths.prj / "Maehwerk").mkdir()
        (self.paths.prj / ".neu_x").mkdir()
        work = uninstall.student_work(self.paths, self.m)
        self.assertEqual(len(work), 3, work)
        self.assertTrue(any("Maehwerk" in w for w in work))

    def test_local_commit_detected(self):
        (self.repo / "a.txt").write_text("meins")
        g(self.repo, "commit", "-qam", "meins")
        self.assertTrue(any("Commits" in w for w in uninstall.student_work(self.paths, self.m)))

    def test_uninstall_without_work_removes_all(self):
        ok = uninstall.uninstall(Reporter(), self.paths, None, deferred=False)
        self.assertTrue(ok)
        self.assertFalse(self.paths.root.exists())
        self.assertFalse(self.own.exists())
        self.assertTrue(self.foreign.exists())

    def test_uninstall_keeps_projects_with_work(self):
        (self.repo / "neu.SUB").write_text("x")
        uninstall.uninstall(Reporter(), self.paths, None, deferred=False)
        self.assertTrue((self.repo / "neu.SUB").is_file())
        self.assertEqual([p.name for p in self.paths.root.iterdir()], ["prj"])

    def test_mit_projekten(self):
        (self.repo / "neu.SUB").write_text("x")
        uninstall.uninstall(Reporter(), self.paths, True, deferred=False)
        self.assertFalse(self.paths.root.exists())

    def test_ide_running_changes_nothing(self):
        with mock.patch("trainings_installer.winsys.running_ides", return_value=[{"ProcessId": 1}]):
            self.assertFalse(uninstall.uninstall(Reporter(), self.paths, True, deferred=False))
        self.assertTrue(self.own.exists())
        self.assertTrue(self.paths.ide.is_dir())

    def test_foreign_files_in_root_stay(self):
        (self.paths.root / "meine_notizen.txt").write_text("n")
        uninstall.uninstall(Reporter(), self.paths, True, deferred=False)
        self.assertEqual([p.name for p in self.paths.root.iterdir()], ["meine_notizen.txt"])


if __name__ == "__main__":
    unittest.main()
