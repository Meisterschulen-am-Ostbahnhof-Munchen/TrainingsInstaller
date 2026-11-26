"""Selbst-Update (KONZEPT.md 3.3).

1. GitHub-API releases/latest abfragen (ohne Login). Offline/Fehler → mit der vorhandenen
   Version weiter.
2. Neuer als version.txt → GUI fragt, headless nur Hinweis; --self-update aktualisiert.
3. TrainingsInstaller.zip laden, SHA256 gegen den Digest des Assets aus der API prüfen,
   nach installer.neu.tmp entpacken, Inhalt prüfen, dann zu installer.neu umbenennen.
4. installer\\ ersetzt install.ps1 beim nächsten Start (Python läuft dann nicht mehr);
   die GUI startet dafür den Installer gleich neu.
Bricht etwas ab, bleibt die alte Version – installer\\ wird hier nie angefasst.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import manifest
from .download import USER_AGENT, DownloadError, fetch
from .paths import Paths
from .report import Reporter, log

REPO = "Meisterschulen-am-Ostbahnhof-Munchen/TrainingsInstaller"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET = "TrainingsInstaller.zip"
TOP = "TrainingsInstaller"
REQUIRED = ("install.cmd", "install.ps1", "manifest.json", "version.txt",
            "trainings_installer/__main__.py")
VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class SelfUpdateError(Exception):
    pass


@dataclass(frozen=True)
class Release:
    version: str   # ohne „v“
    url: str
    sha256: str


def parse_version(s: str) -> tuple[int, int, int] | None:
    m = VERSION_RE.match(s.strip())
    return tuple(int(x) for x in m.groups()) if m else None


def latest(timeout: float = 5) -> Release:
    """Neuestes Release laut GitHub-API. Wirft SelfUpdateError bei jedem Problem."""
    req = urllib.request.Request(API_URL, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError) as e:
        raise SelfUpdateError(f"GitHub nicht erreichbar: {e}") from e
    return release_from_api(data)


def release_from_api(data: dict) -> Release:
    tag = str(data.get("tag_name", ""))
    if not parse_version(tag):
        raise SelfUpdateError(f"Unerwarteter Release-Tag: {tag!r}")
    for a in data.get("assets") or []:
        if a.get("name") == ASSET:
            digest = str(a.get("digest") or "")
            sha = digest.removeprefix("sha256:").lower()
            if not digest.startswith("sha256:") or not manifest.SHA_RE.match(sha):
                raise SelfUpdateError(f"{ASSET} hat keinen SHA256-Digest – nicht prüfbar")
            return Release(tag.lstrip("v"), str(a["browser_download_url"]), sha)
    raise SelfUpdateError(f"Release {tag} hat kein {ASSET}")


def is_newer(candidate: str, current: str) -> bool:
    c, h = parse_version(candidate), parse_version(current)
    return bool(c and h and c > h)


def newer_release(current: str, timeout: float = 5) -> Release | None:
    """Neueres Release oder None (auch offline/Fehler – nur im Log)."""
    try:
        rel = latest(timeout)
    except SelfUpdateError as e:
        log.debug(f"Selbst-Update-Prüfung: {e}")
        return None
    return rel if is_newer(rel.version, current) else None


def notice(rep: Reporter, current: str) -> None:
    """Headless: nur Hinweis, nichts verändern."""
    rel = newer_release(current)
    if rel:
        rep.warn(f"Neue Installer-Version {rel.version} verfügbar (installiert {current}) – "
                 "aktualisieren mit: install.cmd --self-update")


def _extract(zip_path: Path, dest: Path) -> None:
    """Sicher entpacken: nur Einträge unter TrainingsInstaller/, keine Pfade nach außen."""
    base = dest.resolve()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename
            parts = name.split("/")
            if parts[0] != TOP or ".." in parts or "\\" in name or ":" in name:
                raise SelfUpdateError(f"Unerwarteter Eintrag im ZIP: {name!r}")
            rel = "/".join(parts[1:])
            if not rel:
                continue
            target = (dest / rel).resolve()
            if base not in target.parents:
                raise SelfUpdateError(f"Unerwarteter Eintrag im ZIP: {name!r}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def _verify(d: Path, version: str) -> None:
    missing = [f for f in REQUIRED if not (d / f).is_file()]
    if missing:
        raise SelfUpdateError("Im ZIP fehlt: " + ", ".join(missing))
    have = (d / "version.txt").read_text(encoding="utf-8").strip()
    if have != version:
        raise SelfUpdateError(f"version.txt im ZIP ist {have}, erwartet {version}")
    try:
        manifest.load(d / "manifest.json")
    except manifest.ManifestError as e:
        raise SelfUpdateError(str(e)) from e


def prepare(paths: Paths, rel: Release, rep: Reporter) -> Path:
    """ZIP laden, prüfen und als installer.neu bereitlegen. installer\\ bleibt unberührt."""
    zip_path = paths.downloads / f"TrainingsInstaller_{rel.version}.zip"
    try:
        fetch(rel.url, zip_path, rel.sha256, rep.progress)
    except DownloadError as e:
        raise SelfUpdateError(str(e)) from e
    rep.done(f"{ASSET} {rel.version} geladen, SHA256 geprüft")
    neu = paths.root / "installer.neu"
    tmp = paths.root / "installer.neu.tmp"
    for d in (tmp, neu):
        if d.exists():
            shutil.rmtree(d)
    try:
        tmp.mkdir()
        _extract(zip_path, tmp)
        _verify(tmp, rel.version)
    except (OSError, zipfile.BadZipFile) as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise SelfUpdateError(f"ZIP nicht verwendbar: {e}") from e
    except SelfUpdateError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    os.replace(tmp, neu)   # erst jetzt gilt es als fertig (install.ps1 prüft version.txt)
    rep.done(f"Installer {rel.version} liegt bereit: {neu}")
    return neu


def restart(paths: Paths) -> None:
    """install.ps1 neu starten, sobald dieser Prozess beendet ist; es übernimmt installer.neu."""
    env = dict(os.environ, MS_SL_WAIT_PID=str(os.getpid()))
    # NEW_PROCESS_GROUP | NO_WINDOW: unsichtbare Konsole. Nicht DETACHED – ohne Konsole
    # bricht install.ps1 beim ersten Write-Host ab.
    flags = 0x00000200 | 0x08000000
    subprocess.Popen(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden",
                      "-ExecutionPolicy", "Bypass", "-File", str(paths.installer / "install.ps1")],
                     cwd=str(paths.root), env=env, creationflags=flags,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True)


def self_update(rep: Reporter, paths: Paths | None = None, rel: Release | None = None) -> bool:
    """--self-update. `rel`: in der GUI schon ermittelt; sonst wird neu abgefragt."""
    from . import core   # Zyklus vermeiden

    paths = paths or Paths.default()
    paths.ensure()
    current = core.installer_version()
    rep.info(f"Trainings-Installer {current} – Selbst-Update")
    rep.step("Neueste Version abfragen")
    try:
        if rel is None:
            rel = latest(timeout=15)
            if not is_newer(rel.version, current):
                rep.skip(f"Installer ist aktuell ({current}; neuestes Release {rel.version})")
                return True
        rep.step(f"Installer {rel.version} laden")
        prepare(paths, rel, rep)
    except (SelfUpdateError, OSError) as e:
        rep.error(f"Selbst-Update: {e} – die bisherige Version {current} bleibt")
        return False
    return True
