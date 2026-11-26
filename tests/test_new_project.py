"""--new-project mit echten Git-Repos in einem Temp-Ordner (braucht git im PATH, kein Netz)."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trainings_installer import new_project as npj, repos  # noqa: E402
from trainings_installer.paths import Paths  # noqa: E402
from trainings_installer.report import Reporter  # noqa: E402

GIT = shutil.which("git")
WS = "Ventilsteuerung/4diacIDE-workspace"


class TPaths(Paths):
    @property
    def git_exe(self) -> Path:
        return Path(GIT)


def g(cwd: Path, *args: str) -> str:
    return subprocess.run([GIT, "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


class NameTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.paths = TPaths(self.tmp)
        self.paths.prj.mkdir(parents=True)
        self.m = {"repos": {"4diac_training1_empty": {"template_for_new_projects": True}}}

    def test_valid(self):
        for n in ("Maehwerk", "a", "Projekt_2-b", "x" * 40):
            self.assertIsNone(npj.check_name(n, self.paths, self.m), n)

    def test_invalid(self):
        for n in ("", "x" * 41, "Mähwerk", "mein projekt", "..", r"..\x", "a/b", "a.b",
                  "a&b", "a|b", "a>b", 'a"b', "%PATH%", "CON", "nul", "Com1",
                  "4DIAC_TRAINING1_EMPTY"):
            self.assertIsNotNone(npj.check_name(n, self.paths, self.m), n)

    def test_existing_folder(self):
        (self.paths.prj / "Maehwerk").mkdir()
        self.assertIn("gibt es schon", npj.check_name("maehwerk", self.paths, self.m))


@unittest.skipUnless(GIT, "git nicht gefunden")
class CreateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.origin = self.tmp / "origin"
        p = self.origin / WS / "test_AX"
        p.mkdir(parents=True)
        g(self.origin, "init", "-q", "-b", "main")
        (p / ".project").write_text("x", encoding="utf-8")
        g(self.origin, "add", "-A")
        g(self.origin, "commit", "-qm", "v1")
        g(self.origin, "tag", "v1")
        g(self.origin, "commit", "-q", "--allow-empty", "-m", "nach v1")
        self.paths = TPaths(self.tmp / "sl")
        self.paths.prj.mkdir(parents=True)
        self.m = {"repos": {"tpl": {"url": str(self.origin), "ref": "v1", "workspace": WS,
                                    "shortcut": "x", "template_for_new_projects": True}}}

    def check_project(self, d: Path):
        self.assertTrue((d / WS / "test_AX" / ".project").is_file())
        self.assertEqual(g(d, "branch", "--show-current"), "arbeit")
        self.assertEqual(g(d, "rev-parse", "HEAD"), g(self.origin, "rev-parse", "v1^{commit}"))
        self.assertEqual(g(d, "remote"), "upstream")
        self.assertEqual(g(d, "remote", "get-url", "upstream"), str(self.origin))
        self.assertEqual(g(d, "remote", "get-url", "--push", "upstream"), npj.PUSH_BLOCKED)
        r = subprocess.run([GIT, "push"], cwd=d, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(repos.own_projects(self.paths, self.m), [d])

    def test_from_network(self):
        d = npj.create(self.paths, self.m, "Maehwerk", Reporter())
        self.check_project(d)

    def test_from_local_template(self):
        g(self.paths.prj, "clone", "-q", "--branch", "v1", str(self.origin), "tpl")
        d = npj.create(self.paths, self.m, "Maehwerk", Reporter())
        self.check_project(d)

    def test_unknown_tag_leaves_nothing(self):
        self.m["repos"]["tpl"]["ref"] = "v99"
        with self.assertRaises(repos.GitError):
            npj.create(self.paths, self.m, "Maehwerk", Reporter())
        self.assertEqual(list(self.paths.prj.iterdir()), [])

    def test_bad_name_before_anything(self):
        with self.assertRaises(npj.NewProjectError):
            npj.create(self.paths, self.m, r"..\..\Windows", Reporter())
        self.assertEqual(list(self.paths.prj.iterdir()), [])

    def test_hidden_temp_is_no_project(self):
        (self.paths.prj / ".neu_x" / WS).mkdir(parents=True)
        (self.paths.prj / ".neu_x" / ".git").mkdir()
        self.assertEqual(repos.own_projects(self.paths, self.m), [])


if __name__ == "__main__":
    unittest.main()
