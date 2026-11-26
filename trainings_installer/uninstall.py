"""Deinstallieren (KONZEPT.md 5; entschieden 2026-11-26).

Entfernt wird alles, was der Installer angelegt hat:
  - eigene Verknüpfungen (nur die aus shortcuts.json, nie fremde)
  - eigene Einträge im Benutzer-PATH (alle anderen bleiben)
  - tools\\, firmware\\, downloads\\, logs\\, installer\\, shortcuts.json
  - prj\\ nur, wenn dort keine Schülerarbeit liegt – sonst wird gefragt (GUI) bzw. prj bleibt
    stehen (headless), außer mit --mit-projekten
Gelöscht werden nur diese bekannten Unterordner; C:\\ms\\sl selbst nur, wenn es danach leer ist.
Python und der Installer laufen gerade selbst – die räumt ein kleines Skript nach dem
Beenden weg.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from . import repos, winsys
from .paths import Paths
from .repos import GitError, git
from .report import Reporter


class UninstallError(Exception):
    pass


def _rmtree(p: Path) -> None:
    def onerror(func, path, _exc):   # Git-Objekte sind schreibgeschützt
        os.chmod(path, stat.S_IWRITE)
        func(path)
    if p.is_dir():
        shutil.rmtree(p, onerror=onerror)
    elif p.exists():
        p.unlink()


IGNORE_PARTS = {".metadata", "__pycache__"}   # IDE-Zwischenspeicher, kein Schülerwerk


def _changed_files(paths: Paths, d: Path) -> list[str]:
    """Geänderte, neue UND per .gitignore ignorierte Dateien – ohne IDE-Zwischenspeicher."""
    out = git(paths, "status", "--porcelain=v1", "-z", "--ignored=matching",
              "--untracked-files=all", cwd=d)
    fields = out.split("\0")
    files, i = [], 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        if entry[0] in "RC":
            i += 1   # bei Umbenennung folgt der alte Pfad
        path = entry[3:]
        if not IGNORE_PARTS & set(path.rstrip("/").split("/")):
            files.append(path)
    return files


def student_work(paths: Paths, m: dict) -> list[str]:
    """Was in prj\\ verloren ginge: eigene Projekte, Änderungen, Sicherungen, lokale Commits."""
    out: list[str] = []
    if not paths.prj.is_dir():
        return out
    for d in sorted(paths.prj.iterdir()):
        if d.name.startswith(".neu_"):
            continue   # Rest eines abgebrochenen --new-project
        if d.name not in m["repos"]:
            out.append(f"{d.name}: eigenes Projekt bzw. fremder Ordner")
            continue
        if not (d / ".git").exists():
            out.append(f"{d.name}: kein Git-Repo – Inhalt unbekannt")
            continue
        if not paths.git_exe.is_file():
            out.append(f"{d.name}: nicht prüfbar (Git fehlt)")
            continue
        try:
            changed = _changed_files(paths, d)
            if changed:
                out.append(f"{d.name}: geänderte oder neue Dateien ({len(changed)})")
            backups = git(paths, "branch", "--list", "sicherung_*", "--format=%(refname:short)", cwd=d)
            if backups:
                out.append(f"{d.name}: Sicherungs-Branches ({len(backups.splitlines())})")
            ahead = git(paths, "rev-list", "--count", "HEAD", "--branches", "--not", "--tags", "--remotes", cwd=d)
            if ahead not in ("", "0"):
                out.append(f"{d.name}: eigene Commits ({ahead})")
        except GitError as e:
            out.append(f"{d.name}: nicht prüfbar ({e})")
    return out


def _remove_shortcuts(paths: Paths, rep: Reporter) -> None:
    import json

    from .shortcuts import _load_owned
    n, failed = 0, []
    for p in map(Path, sorted(_load_owned(paths))):
        try:
            if p.suffix.lower() == ".lnk" and p.exists():
                p.unlink()
                n += 1
        except OSError as e:
            failed.append(str(p))
            rep.error(f"Verknüpfung nicht gelöscht: {p} ({e})")
    try:
        start = winsys.start_menu_dir()
        if start.is_dir() and not any(start.iterdir()):
            start.rmdir()
    except OSError:
        pass
    if failed:   # Eigentum merken, damit ein zweiter Lauf sie noch löschen darf
        paths.shortcuts_json.write_text(json.dumps(failed, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    else:
        paths.shortcuts_json.unlink(missing_ok=True)
    rep.done(f"{n} Verknüpfungen entfernt (fremde bleiben)")


def _remove_path(paths: Paths, rep: Reporter) -> None:
    from .core import _tool_path_entries
    if winsys.remove_user_path(_tool_path_entries(paths)):
        rep.done("Eigene Einträge aus dem Benutzer-PATH entfernt")
    else:
        rep.skip("Benutzer-PATH (keine eigenen Einträge)")


def _schedule_removal(paths: Paths, targets: list[Path], rep: Reporter) -> None:
    """Ordner, die der laufende Installer selbst benutzt, nach seinem Ende löschen."""
    pid = os.getpid()
    lines = ["@echo off", "rem TrainingsInstaller: Restordner nach dem Beenden entfernen",
             "set n=0", ":wait",
             f'tasklist /FI "PID eq {pid}" /NH 2>nul | find " {pid} " >nul && '
             '(ping -n 2 127.0.0.1 >nul & goto wait)',
             ":retry"]
    lines += [f'if exist "{t}" rmdir /s /q "{t}"' for t in targets]
    lines += ["set /a n+=1", "if %n% geq 30 goto done"]   # z. B. Konsolenfenster steht noch im Ordner
    lines += [f'if exist "{t}" (ping -n 3 127.0.0.1 >nul & goto retry)' for t in targets]
    lines += [":done", f'rmdir "{paths.root}" 2>nul', 'del "%~f0"']
    script = Path(tempfile.gettempdir()) / f"ms_sl_uninstall_{os.getpid()}.cmd"
    script.write_text("\r\n".join(lines) + "\r\n", encoding="mbcs" if os.name == "nt" else "utf-8")
    flags = 0x00000008 | 0x00000200 | 0x08000000   # DETACHED | NEW_PROCESS_GROUP | NO_WINDOW
    subprocess.Popen(["cmd.exe", "/c", str(script)], creationflags=flags, cwd=tempfile.gettempdir(),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     close_fds=True)
    rep.info("Python, Installer und Logs werden nach dem Beenden entfernt")


def uninstall(rep: Reporter, paths: Paths | None = None, remove_projects: bool | None = None,
              deferred: bool = True) -> bool:
    """--uninstall. remove_projects: True = prj immer löschen, False = immer behalten,
    None = nur löschen, wenn dort keine Schülerarbeit liegt."""
    from . import core   # Zyklus vermeiden

    paths = paths or Paths.default()
    rep.info(f"Trainings-Installer {core.installer_version()} – Deinstallieren")
    m = core.load_manifest()
    try:
        busy = winsys.running_ides(paths.tools, strict=True)
    except (RuntimeError, ValueError) as e:
        rep.error(f"Kann nicht prüfen, ob die 4diac IDE läuft – nichts verändert ({e})")
        return False
    if busy or any(winsys.workspace_locked(w) for w in repos.all_workspaces(paths, m)):
        rep.error("Bitte zuerst die 4diac IDE schließen – sonst sind Dateien gesperrt")
        return False

    rep.step("Projekte prüfen")
    work = student_work(paths, m)
    for w in work:
        rep.info(f"  {w}")
    if remove_projects is None:
        remove_projects = not work
        if work:
            rep.warn(f"{paths.prj} bleibt erhalten: dort liegt Schülerarbeit (oben aufgelistet). "
                     "Löschen mit --uninstall --mit-projekten")

    rep.step("Verknüpfungen")
    _remove_shortcuts(paths, rep)
    rep.step("PATH")
    try:
        _remove_path(paths, rep)
    except OSError as e:
        rep.error(f"PATH: {e}")

    rep.step("Ordner löschen")
    now = [paths.firmware, paths.firmware.with_name("firmware.neu"), paths.downloads,
           paths.root / "installer.neu", paths.root / "installer.tmp"]
    now += [p for p in paths.tools.iterdir() if p != paths.python] if paths.tools.is_dir() else []
    if remove_projects:
        now.append(paths.prj)
    for p in now:
        try:
            if p.exists():
                _rmtree(p)
                rep.done(f"Gelöscht: {p}")
        except OSError as e:
            rep.error(f"Nicht gelöscht: {p} ({e})")
    if not remove_projects:
        rep.skip(f"Projekte behalten: {paths.prj}")

    later = [paths.python, paths.tools, paths.installer, paths.logs]
    if not rep.report.ok:
        # Installer behalten: nach Behebung des Fehlers --uninstall erneut ausführen
        rep.warn("Wegen der Fehler oben bleiben Python, Installer und Logs erhalten – "
                 "nach Behebung „Deinstallieren“ erneut starten")
        return False
    if deferred:
        _schedule_removal(paths, later, rep)
    else:
        for p in later:
            _rmtree(p)
        try:
            paths.root.rmdir()
        except OSError:
            pass
    return rep.report.ok
