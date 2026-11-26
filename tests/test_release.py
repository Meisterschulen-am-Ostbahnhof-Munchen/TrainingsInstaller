"""Release-ZIP (tools/build_release.py): Inhalt nach KONZEPT 3.3, reproduzierbar."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_release  # noqa: E402


class ReleaseZipTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_content_and_reproducible(self):
        sha1 = build_release.build_zip(self.tmp / "a.zip")
        sha2 = build_release.build_zip(self.tmp / "b.zip")
        self.assertEqual(sha1, sha2)
        names = zipfile.ZipFile(self.tmp / "a.zip").namelist()
        for f in build_release.FILES:
            self.assertIn(f"TrainingsInstaller/{f}", names)
        self.assertIn("TrainingsInstaller/trainings_installer/__main__.py", names)
        self.assertTrue(all(n.startswith("TrainingsInstaller/") for n in names))
        self.assertFalse([n for n in names if "__pycache__" in n or n.endswith(".pyc")])
        self.assertFalse([n for n in names if "/tests/" in n or "/tools/" in n or "KONZEPT" in n])

    def test_tag_must_match_version(self):
        version = (ROOT / "version.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(build_release.main(["--tag", "v0.0.0-falsch", "--out", str(self.tmp)]), 1)
        self.assertEqual(build_release.main(["--tag", f"v{version}", "--out", str(self.tmp)]), 0)
        notes = (self.tmp / "RELEASE_NOTES.md").read_text(encoding="utf-8")
        m = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        for name in m["repos"]:
            self.assertIn(name, notes)


if __name__ == "__main__":
    unittest.main()
