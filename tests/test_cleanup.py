"""--cleanup: nur alte Downloads und Logs älter als 90 Tage; nichts anderes."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trainings_installer import cleanup, manifest  # noqa: E402
from trainings_installer.paths import Paths  # noqa: E402
from trainings_installer.report import Reporter  # noqa: E402

DAY = 86400


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.paths = Paths(self.tmp)
        self.paths.ensure()
        self.m = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        dl = self.paths.downloads
        self.current = [dl / manifest.url_filename(self.m[k]["url"]) for k in manifest.TOOLS]
        self.current.append(dl / f"firmware_{self.m['firmware']['sha256'][:12]}.json")
        for f in self.current:
            f.write_text("x")
        self.old_ide = dl / "4diac-ide_3.3.0-alt.zip"
        self.old_ide.write_text("alt")
        self.partial = dl / "irgendwas.zip.tmp"
        self.partial.write_text("halb")
        logs = self.paths.logs
        self.log_old = logs / "install_20260101_000000.log"
        self.log_new = logs / "install_20261120_000000.log"
        self.other = logs / "notiz.txt"
        for f, age in ((self.log_old, 91), (self.log_new, 10), (self.other, 400)):
            f.write_text("log")
            t = time.time() - age * DAY
            os.utime(f, (t, t))
        # Projekt mit Sicherung: darf nie angefasst werden
        self.sub = self.paths.prj / "p" / "Uebung1_sicherung_20260101_000000.SUB"
        self.sub.parent.mkdir(parents=True)
        self.sub.write_text("s")

    def test_plan(self):
        self.assertEqual(set(cleanup.plan(self.paths, self.m)),
                         {self.old_ide, self.partial, self.log_old})

    def test_current_log_is_kept(self):
        t = time.time() - 100 * DAY
        os.utime(self.log_new, (t, t))
        self.assertNotIn(self.log_new, cleanup.plan(self.paths, self.m, keep_log=self.log_new))

    def test_cleanup_deletes_only_plan(self):
        rep = Reporter()
        files = cleanup.plan(self.paths, self.m)
        cleanup.delete(self.paths, files, rep)
        for f in files:
            self.assertFalse(f.exists(), f)
        for f in (*self.current, self.log_new, self.other, self.sub):
            self.assertTrue(f.exists(), f)

    def test_delete_refuses_outside(self):
        rep = Reporter()
        cleanup.delete(self.paths, [self.sub], rep)
        self.assertTrue(self.sub.exists())
        self.assertFalse(rep.report.ok)


if __name__ == "__main__":
    unittest.main()
