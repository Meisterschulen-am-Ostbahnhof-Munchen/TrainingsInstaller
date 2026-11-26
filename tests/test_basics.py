"""Tests ohne Netz und ohne Änderungen am System: python -m unittest discover -s tests"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trainings_installer import download, manifest, shortcuts, winsys  # noqa: E402
from trainings_installer.paths import Paths  # noqa: E402


def real_manifest() -> dict:
    return json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))


class ManifestTest(unittest.TestCase):
    def test_real_manifest_is_valid(self):
        self.assertEqual(manifest.validate(real_manifest()), [])

    def test_all_repos_same_tag_as_training1(self):
        m = real_manifest()
        fw = {"training1": m["repos"]["4diac_training1"]["ref"], "targets": {"x": {}}}
        self.assertEqual(manifest.check_firmware_sync(m, fw), [])

    def test_sync_detects_mismatch(self):
        m = real_manifest()
        m["repos"]["4diac_template"]["ref"] = "v0.1"
        fw = {"training1": "v0.0", "targets": {"x": {}}}
        self.assertEqual(len(manifest.check_firmware_sync(m, fw)), 2)

    def test_bad_sha_and_template_count(self):
        m = copy.deepcopy(real_manifest())
        m["git"]["sha256"] = "ABC"
        m["repos"]["4diac_template"]["template_for_new_projects"] = True
        problems = manifest.validate(m)
        self.assertTrue(any("git.sha256" in p for p in problems))
        self.assertTrue(any("template_for_new_projects" in p for p in problems))

    def test_url_filename(self):
        self.assertEqual(manifest.url_filename("https://x/a/b/python-3.15.2-amd64.zip"),
                         "python-3.15.2-amd64.zip")


class DownloadTest(unittest.TestCase):
    def test_fetch_checks_sha_and_caches(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src.bin"
            src.write_bytes(b"hallo" * 1000)
            sha = hashlib.sha256(src.read_bytes()).hexdigest()
            dest = Path(d) / "dl" / "file.bin"
            self.assertTrue(download.fetch(src.as_uri(), dest, sha))
            self.assertFalse(download.fetch(src.as_uri(), dest, sha))   # Cache
            with self.assertRaises(download.DownloadError):
                download.fetch(src.as_uri(), Path(d) / "other.bin", "0" * 64)
            self.assertFalse((Path(d) / "other.bin").exists())
            self.assertFalse((Path(d) / "other.bin.tmp").exists())


class PathTest(unittest.TestCase):
    ADD = [r"C:\ms\sl\tools\git\cmd", r"C:\ms\sl\tools\python"]

    def test_prepend_and_keep_rest(self):
        raw = r"%USERPROFILE%\AppData\Local\Microsoft\WindowsApps;C:\other"
        self.assertEqual(winsys.merge_path(raw, self.ADD),
                         ";".join(self.ADD) + r";%USERPROFILE%\AppData\Local\Microsoft\WindowsApps;C:\other")

    def test_idempotent_and_dedup(self):
        raw = r"C:\x;c:\ms\sl\tools\python\;C:\y"
        once = winsys.merge_path(raw, self.ADD)
        self.assertEqual(winsys.merge_path(once, self.ADD), once)
        self.assertEqual(once.lower().count(r"c:\ms\sl\tools\python"), 1)

    def test_empty(self):
        self.assertEqual(winsys.merge_path("", self.ADD), ";".join(self.ADD))

    def test_remove(self):
        self.assertEqual(winsys.remove_from_path(r"C:\ms\sl\tools\python;C:\x", self.ADD), r"C:\x")


class ShortcutTest(unittest.TestCase):
    def test_prefs_escaping(self):
        text = shortcuts.recent_workspaces_prefs([Path(r"C:\ms\sl\prj\a\ws"), Path(r"C:\ms\sl\prj\b\ws")])
        self.assertIn(r"RECENT_WORKSPACES=C\:\\ms\\sl\\prj\\a\\ws\nC\:\\ms\\sl\\prj\\b\\ws", text)
        self.assertIn("MAX_RECENT_WORKSPACES=10", text)

    def test_max_recent_grows(self):
        text = shortcuts.recent_workspaces_prefs([Path(f"C:/w{i}") for i in range(13)])
        self.assertIn("MAX_RECENT_WORKSPACES=13", text)

    def test_resolve_foreign_and_owned(self):
        with tempfile.TemporaryDirectory() as d:
            desk = Path(d)
            (desk / "4diac IDE.lnk").write_text("fremd")
            (desk / "4diac Projekte.lnk").write_text("unsere")
            owned = {str(desk / "4diac Projekte.lnk")}
            planned = [shortcuts.Shortcut("4diac IDE", "t", "", "w"),
                       shortcuts.Shortcut("4diac Projekte", "t", "", "w"),
                       shortcuts.Shortcut("Nur Startmenü", "t", "", "w", desktop=False)]
            items, keep, warnings = shortcuts.resolve(planned, {"desktop": desk}, owned)
            self.assertEqual([Path(i["path"]).name for i in items],
                             ["4diac IDE (Schule).lnk", "4diac Projekte.lnk"])
            self.assertEqual(len(keep), 2)
            self.assertEqual(warnings, [])

    def test_plan_without_checkouts(self):
        with tempfile.TemporaryDirectory() as d:
            names = [s.name for s in shortcuts.plan(Paths(Path(d)), real_manifest())]
            self.assertEqual(names, ["4diac Projekte", "4diac IDE", shortcuts.INSTALLER_SHORTCUT])


if __name__ == "__main__":
    unittest.main()
