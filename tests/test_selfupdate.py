"""Selbst-Update (KONZEPT 3.3): Versionsvergleich, API-Auswertung, Laden/Prüfen/Entpacken (ohne Netz)."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import build_release  # noqa: E402
from trainings_installer import selfupdate  # noqa: E402
from trainings_installer.download import sha256_file  # noqa: E402
from trainings_installer.paths import Paths  # noqa: E402
from trainings_installer.report import Reporter  # noqa: E402

VERSION = (ROOT / "version.txt").read_text(encoding="utf-8").strip()
SHA = "a" * 64


def api(tag="v9.9.9", digest="sha256:" + SHA, name="TrainingsInstaller.zip"):
    return {"tag_name": tag, "assets": [{"name": name, "digest": digest,
                                         "browser_download_url": "https://x/TrainingsInstaller.zip"}]}


class VersionTest(unittest.TestCase):
    def test_compare(self):
        self.assertTrue(selfupdate.is_newer("0.1.10", "0.1.9"))
        self.assertTrue(selfupdate.is_newer("v1.0.0", "0.9.9"))
        self.assertFalse(selfupdate.is_newer("0.1.1", "0.1.1"))
        self.assertFalse(selfupdate.is_newer("0.1.0", "0.1.1"))
        self.assertFalse(selfupdate.is_newer("1.0.0-rc1", "0.1.1"))
        self.assertFalse(selfupdate.is_newer("1.0.0", "?"))

    def test_api(self):
        rel = selfupdate.release_from_api(api())
        self.assertEqual((rel.version, rel.sha256), ("9.9.9", SHA))
        for bad in (api(digest=""), api(digest="md5:x"), api(tag="nightly"), api(name="andere.zip")):
            with self.assertRaises(selfupdate.SelfUpdateError):
                selfupdate.release_from_api(bad)

    def test_offline_is_silent(self):
        with mock.patch.object(selfupdate, "latest", side_effect=selfupdate.SelfUpdateError("offline")):
            self.assertIsNone(selfupdate.newer_release("0.1.1"))
            rep = Reporter()
            selfupdate.notice(rep, "0.1.1")
            self.assertEqual((rep.report.warnings, rep.report.errors), ([], []))

    def test_notice(self):
        rel = selfupdate.Release("9.9.9", "https://x", SHA)
        with mock.patch.object(selfupdate, "latest", return_value=rel):
            rep = Reporter()
            selfupdate.notice(rep, "0.1.1")
            self.assertIn("--self-update", rep.report.warnings[0])

    def test_already_current(self):
        rel = selfupdate.Release(VERSION, "https://x", SHA)
        with mock.patch.object(selfupdate, "latest", return_value=rel), \
                tempfile.TemporaryDirectory() as t:
            paths = Paths(Path(t))
            self.assertTrue(selfupdate.self_update(Reporter(), paths))
            self.assertFalse((paths.root / "installer.neu").exists())


class PrepareTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.paths = Paths(self.tmp / "sl")
        self.paths.ensure()
        self.zip = self.tmp / "src" / "TrainingsInstaller.zip"
        self.sha = build_release.build_zip(self.zip)

    def rel(self, zip_path=None, sha=None, version=VERSION):
        return selfupdate.Release(version, (zip_path or self.zip).as_uri(), sha or self.sha)

    def test_prepare_ok(self):
        neu = selfupdate.prepare(self.paths, self.rel(), Reporter())
        self.assertEqual((neu / "version.txt").read_text(encoding="utf-8").strip(), VERSION)
        self.assertTrue((neu / "trainings_installer" / "selfupdate.py").is_file())
        self.assertFalse((self.paths.root / "installer.neu.tmp").exists())

    def test_wrong_sha_keeps_nothing(self):
        rep = Reporter()
        self.assertFalse(selfupdate.self_update(rep, self.paths, self.rel(sha="b" * 64)))
        self.assertIn("SHA256", rep.report.errors[0])
        self.assertFalse((self.paths.root / "installer.neu").exists())

    def test_version_mismatch(self):
        with self.assertRaises(selfupdate.SelfUpdateError):
            selfupdate.prepare(self.paths, self.rel(version="9.9.9"), Reporter())
        self.assertFalse((self.paths.root / "installer.neu").exists())
        self.assertFalse((self.paths.root / "installer.neu.tmp").exists())

    def test_path_traversal_rejected(self):
        evil = self.tmp / "evil.zip"
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("TrainingsInstaller/version.txt", VERSION)
            z.writestr("TrainingsInstaller/../../boese.txt", "x")
        sha = sha256_file(evil)
        with self.assertRaises(selfupdate.SelfUpdateError):
            selfupdate.prepare(self.paths, self.rel(evil, sha), Reporter())
        self.assertFalse((self.tmp / "boese.txt").exists())
        self.assertFalse((self.paths.root / "installer.neu").exists())


if __name__ == "__main__":
    unittest.main()
