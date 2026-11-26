"""--update mit echten Git-Repos in einem Temp-Ordner (braucht git im PATH, kein Netz)."""
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

from trainings_installer import repos, update  # noqa: E402
from trainings_installer.paths import Paths  # noqa: E402
from trainings_installer.report import Reporter  # noqa: E402

GIT = shutil.which("git")
WS = "Ventilsteuerung/4diacIDE-workspace"


class TPaths(Paths):
    @property
    def git_exe(self) -> Path:
        return Path(GIT)


def sub(name: str, body: str = "") -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<SubAppType Name="{name}" Comment="x">\n'
            f'  <SubAppNetwork>{body}</SubAppNetwork>\n</SubAppType>\n')


def g(cwd: Path, *args: str) -> str:
    return subprocess.run([GIT, "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


@unittest.skipUnless(GIT, "git nicht gefunden")
class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # Schul-Repo mit Tag v1
        self.origin = self.tmp / "origin"
        p = self.origin / WS / "test_AX"
        p.mkdir(parents=True)
        g(self.origin, "init", "-q", "-b", "main")
        (p / "Uebung1.SUB").write_text(sub("Uebung1"), encoding="utf-8")
        (p / "Uebung2.SUB").write_text(sub("Uebung2"), encoding="utf-8")
        (p / "Baustein.fbt").write_text("alt", encoding="utf-8")
        g(self.origin, "add", "-A")
        g(self.origin, "commit", "-qm", "v1")
        g(self.origin, "tag", "v1")
        # Schüler klont v1, Arbeits-Branch arbeit
        self.paths = TPaths(self.tmp / "sl")
        self.paths.prj.mkdir(parents=True)
        self.entry = {"url": str(self.origin), "ref": "v1", "workspace": WS, "shortcut": "x"}
        self.d = self.paths.prj / "train"
        g(self.paths.prj, "clone", "-q", "--branch", "v1", str(self.origin), "train")
        g(self.d, "switch", "-q", "-c", "arbeit")
        self.ws = self.d / WS / "test_AX"
        self.patch = mock.patch("trainings_installer.winsys.running_ides", return_value=[])
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def school_release_v2(self):
        p = self.origin / WS / "test_AX"
        (p / "Uebung1.SUB").write_text(sub("Uebung1", "<neu/>"), encoding="utf-8")
        (p / "Neu.SUB").write_text(sub("Neu"), encoding="utf-8")
        (p / "Baustein.fbt").write_text("neu", encoding="utf-8")
        g(self.origin, "add", "-A")
        g(self.origin, "commit", "-qm", "v2")
        g(self.origin, "tag", "v2")
        self.entry["ref"] = "v2"

    def run_update(self):
        return update.update_repo(self.paths, "train", self.entry, Reporter(), ts="20261126_120000")

    def test_nothing_to_do(self):
        res = self.run_update()
        self.assertFalse(res.changed)
        self.assertEqual(res.backup_branch, "")
        self.assertNotIn("sicherung", g(self.d, "branch"))

    def test_student_changes_are_saved(self):
        (self.ws / "Uebung1.SUB").write_text(sub("Uebung1", "<meins/>"), encoding="utf-8")
        (self.ws / "Uebung2.SUB").unlink()
        (self.ws / "Baustein.fbt").write_text("meins", encoding="utf-8")
        (self.ws / "Eigen.SUB").write_text(sub("Eigen"), encoding="utf-8")   # unversioniert
        (self.ws / "Neu.SUB").write_text("meine eigene Datei", encoding="utf-8")   # liegt im Weg
        self.school_release_v2()

        res = self.run_update()

        # neuer Stand auf Branch arbeit
        self.assertEqual(g(self.d, "branch", "--show-current"), "arbeit")
        self.assertEqual(g(self.d, "rev-parse", "HEAD"), g(self.d, "rev-parse", "v2^{commit}"))
        self.assertIn("<neu/>", (self.ws / "Uebung1.SUB").read_text(encoding="utf-8"))
        self.assertEqual((self.ws / "Baustein.fbt").read_text(encoding="utf-8"), "neu")
        # .SUB-Sicherung daneben, Typname umbenannt
        saved = self.ws / "Uebung1_sicherung_20261126_120000.SUB"
        text = saved.read_text(encoding="utf-8")
        self.assertIn('<SubAppType Name="Uebung1_sicherung_20261126_120000"', text)
        self.assertIn("<meins/>", text)
        self.assertEqual(res.saved_subs, [f"{WS}/test_AX/Uebung1_sicherung_20261126_120000.SUB"])
        self.assertEqual(res.deleted_subs, [f"{WS}/test_AX/Uebung2.SUB"])
        # unversionierte Datei bleibt, Datei im Weg umbenannt (kein Datenverlust)
        self.assertTrue((self.ws / "Eigen.SUB").is_file())
        moved = self.ws / "Neu_sicherung_20261126_120000.SUB"
        self.assertEqual(moved.read_text(encoding="utf-8"), "meine eigene Datei")
        self.assertEqual(len(res.renamed_in_way), 1)
        # Sicherungs-Branch enthält auch die .fbt-Änderung
        self.assertEqual(res.backup_branch, "sicherung_20261126_120000")
        self.assertEqual(g(self.d, "show", f"{res.backup_branch}:{WS}/test_AX/Baustein.fbt"), "meins")

    def test_local_commits_survive(self):
        (self.ws / "Uebung1.SUB").write_text(sub("Uebung1", "<commit/>"), encoding="utf-8")
        g(self.d, "commit", "-qam", "meine Arbeit")
        mine = g(self.d, "rev-parse", "HEAD")
        self.school_release_v2()
        res = self.run_update()
        self.assertEqual(g(self.d, "rev-parse", res.backup_branch), mine)
        self.assertTrue((self.ws / "Uebung1_sicherung_20261126_120000.SUB").is_file())

    def test_second_update_keeps_backups(self):
        (self.ws / "Uebung1.SUB").write_text(sub("Uebung1", "<meins/>"), encoding="utf-8")
        self.school_release_v2()
        self.run_update()
        res2 = self.run_update()
        self.assertFalse(res2.changed)
        self.assertTrue((self.ws / "Uebung1_sicherung_20261126_120000.SUB").is_file())
        self.assertIn("sicherung_20261126_120000", g(self.d, "branch"))

    def test_lib_sub_not_copied_into_library(self):
        lib = self.d / WS / ".lib" / "x-1.0.0"
        lib.mkdir(parents=True)
        (lib / "LibTyp.SUB").write_text(sub("LibTyp"), encoding="utf-8")
        g(self.d, "add", "-A")
        g(self.d, "commit", "-qm", "lib")
        g(self.origin, "fetch", "-q", str(self.d), "arbeit:libstand")
        g(self.origin, "tag", "v1lib", "libstand")
        self.entry["ref"] = "v1lib"
        g(self.d, "fetch", "-q", "--tags", "origin")
        g(self.d, "reset", "-q", "--hard", "v1lib")
        (lib / "LibTyp.SUB").write_text(sub("LibTyp", "<meins/>"), encoding="utf-8")
        self.school_release_v2()   # v2 basiert auf v1, ohne die Bibliothek
        res = self.run_update()
        self.assertEqual(list(lib.glob("*sicherung*")) if lib.exists() else [], [])
        self.assertTrue(any("Bibliotheksdatei" in w for w in res.warnings))
        self.assertIn("<meins/>", g(self.d, "show", f"{res.backup_branch}:{WS}/.lib/x-1.0.0/LibTyp.SUB"))

    def test_unknown_tag_changes_nothing(self):
        (self.ws / "Uebung1.SUB").write_text("x", encoding="utf-8")
        self.entry["ref"] = "v99"
        with self.assertRaises(update.UpdateError):
            self.run_update()
        self.assertEqual((self.ws / "Uebung1.SUB").read_text(encoding="utf-8"), "x")
        self.assertNotIn("sicherung", g(self.d, "branch"))


class SubRenameTest(unittest.TestCase):
    def test_only_root_name(self):
        data = sub("A", '<SubApp Name="A" Type="B"/>').encode("utf-8")
        out = update.rename_sub_type(data, "A_sicherung_1").decode("utf-8")
        self.assertIn('<SubAppType Name="A_sicherung_1" Comment="x">', out)
        self.assertIn('<SubApp Name="A" Type="B"/>', out)

    def test_blocking_paths(self):
        msg = ("error: The following untracked working tree files would be overwritten by checkout:\n"
               "\tVentilsteuerung/a b/Neu.SUB\n\tx.txt\nPlease move or remove them\nAborting")
        self.assertEqual(update._blocking_paths(msg), ["Ventilsteuerung/a b/Neu.SUB", "x.txt"])


if __name__ == "__main__":
    unittest.main()
