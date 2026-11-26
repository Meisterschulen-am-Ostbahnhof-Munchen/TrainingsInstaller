"""Aufräumen (KONZEPT.md 2.6 „Aufräumen“).

Gelöscht werden nur:
  - Dateien in downloads\\, die das aktuelle Manifest nicht mehr nennt (auch automatisch am
    Ende jedes erfolgreichen Laufs)
  - mit --cleanup zusätzlich Logs in logs\\ älter als 90 Tage
Nie angefasst: Projektdateien, .SUB-Sicherungen, Sicherungs-Branches, Branch arbeit –
dieses Modul arbeitet ausschließlich in downloads\\ und logs\\.
"""
from __future__ import annotations

import time
from pathlib import Path

from . import manifest
from .manifest import url_filename
from .paths import Paths
from .report import Reporter

LOG_DAYS = 90


def unused_downloads(paths: Paths, m: dict) -> list[Path]:
    keep = {url_filename(m[k]["url"]) for k in manifest.TOOLS}
    keep.add(f"firmware_{m['firmware']['sha256'][:12]}.json")
    if not paths.downloads.is_dir():
        return []
    return sorted(f for f in paths.downloads.iterdir() if f.is_file() and f.name not in keep)


def old_logs(paths: Paths, now: float | None = None, keep: Path | None = None) -> list[Path]:
    limit = (now or time.time()) - LOG_DAYS * 86400
    if not paths.logs.is_dir():
        return []
    return sorted(f for f in paths.logs.iterdir()
                  if f.is_file() and f.suffix == ".log" and f != keep and f.stat().st_mtime < limit)


def plan(paths: Paths, m: dict, keep_log: Path | None = None) -> list[Path]:
    """Alles, was --cleanup löschen würde."""
    return unused_downloads(paths, m) + old_logs(paths, keep=keep_log)


def count(n: int) -> str:
    return f"{n} Datei" if n == 1 else f"{n} Dateien"


def _size(files: list[Path]) -> str:
    total = sum(f.stat().st_size for f in files if f.exists())
    return f"{total / 1e6:.1f} MB"


def describe(paths: Paths, files: list[Path]) -> list[str]:
    return [str(f.relative_to(paths.root)) for f in files]


def delete(paths: Paths, files: list[Path], rep: Reporter) -> None:
    allowed = (paths.downloads.resolve(), paths.logs.resolve())
    for f in files:
        if f.resolve().parent not in allowed:   # Schutz: nie außerhalb downloads\ und logs\
            rep.error(f"Nicht gelöscht (außerhalb downloads/logs): {f}")
            continue
        try:
            f.unlink(missing_ok=True)
            rep.info(f"Gelöscht: {f.relative_to(paths.root)}")
        except OSError as e:
            rep.warn(f"Nicht gelöscht: {f.name} ({e})")


def cleanup(rep: Reporter, paths: Paths | None = None, files: list[Path] | None = None) -> bool:
    """--cleanup. `files`: bereits bestätigte Liste aus der GUI; sonst wird neu ermittelt."""
    from . import core   # Zyklus vermeiden
    from .report import current_logfile

    paths = paths or Paths.default()
    paths.ensure()
    rep.info(f"Trainings-Installer {core.installer_version()} – Aufräumen")
    rep.step("Aufräumen")
    if files is None:
        files = plan(paths, core.load_manifest(), keep_log=current_logfile())
    if not files:
        rep.skip("Nichts aufzuräumen (keine alten Downloads, keine Logs älter als "
                 f"{LOG_DAYS} Tage)")
        return rep.report.ok
    rep.info(f"Wird gelöscht ({count(len(files))}, {_size(files)}):")
    for line in describe(paths, files):
        rep.info(f"  {line}")
    delete(paths, files, rep)
    rep.done(f"Aufgeräumt: {count(len(files))}. Sicherungs-Branches und "
             "_sicherung_-Dateien bleiben immer erhalten.")
    return rep.report.ok
