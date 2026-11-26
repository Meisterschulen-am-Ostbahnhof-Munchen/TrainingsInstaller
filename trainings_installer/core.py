"""Kern ohne Oberfläche (KONZEPT.md 3.1, Ablauf 4).

GUI und Konsole rufen nur diese Funktionen auf – keine Logik doppelt.
"""
from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

from . import firmware, manifest, repos, shortcuts, tools, winsys
from .download import DownloadError
from .manifest import url_filename
from .paths import Paths
from .report import Reporter, log

MIN_FREE_GB = 3   # IDE ~0,3 GB als ZIP + ~0,6 GB entpackt, Repos, Firmware, Puffer


def installer_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def installer_version() -> str:
    f = installer_dir() / "version.txt"
    return f.read_text(encoding="utf-8").strip() if f.is_file() else "?"


def load_manifest() -> dict:
    return manifest.load(installer_dir() / "manifest.json")


def check_environment(paths: Paths, rep: Reporter) -> bool:
    ok = True
    if sys.platform != "win32":
        rep.error("Nur Windows wird unterstützt")
        return False
    if platform.machine().lower() not in ("amd64", "x86_64"):
        rep.error(f"Nur Windows x64 wird unterstützt (gefunden: {platform.machine()})")
        ok = False
    free_gb = shutil.disk_usage(paths.root).free / 1e9
    if free_gb < MIN_FREE_GB:
        rep.error(f"Zu wenig freier Speicher auf {paths.root.drive}: {free_gb:.1f} GB "
                  f"(mindestens {MIN_FREE_GB} GB)")
        ok = False
    return ok


def _tool_path_entries(paths: Paths) -> list[str]:
    return [str(paths.git / "cmd"), str(paths.python), str(paths.python / "Scripts")]


def _cleanup_downloads(paths: Paths, m: dict, rep: Reporter) -> None:
    """Automatisch: Downloads löschen, die das Manifest nicht mehr nennt (2.6 „Aufräumen“)."""
    keep = {url_filename(m[k]["url"]) for k in manifest.TOOLS}
    keep.add(f"firmware_{m['firmware']['sha256'][:12]}.json")
    for f in paths.downloads.iterdir():
        if f.is_file() and f.name not in keep:
            f.unlink(missing_ok=True)
            rep.info(f"Alter Download gelöscht: {f.name}")


def install(rep: Reporter, paths: Paths | None = None) -> bool:
    """Vollständige Installation bzw. Nachinstallation (idempotent)."""
    paths = paths or Paths.default()
    paths.ensure()
    rep.info(f"Trainings-Installer {installer_version()}")
    rep.step("Umgebung prüfen")
    if not check_environment(paths, rep):
        return False
    try:
        m = load_manifest()
    except manifest.ManifestError as e:
        rep.error(str(e))
        return False

    def guarded(title: str, fn, *args):
        rep.step(title)
        try:
            return fn(*args)
        except (tools.StepError, repos.GitError, firmware.FirmwareError, DownloadError,
                OSError, RuntimeError) as e:
            log.exception(title)
            rep.error(f"{title}: {e}")
            return None

    guarded("Git", tools.install_git, paths, m, rep)
    winsys.prepend_process_path(_tool_path_entries(paths))

    workspaces = repos.all_workspaces(paths, m)
    guarded("4diac IDE", tools.install_ide, paths, m, rep, workspaces)
    if paths.ide.is_dir():
        guarded("Auto-Import-Plugin", tools.install_plugin, paths, m, rep)
        tools.write_customization(paths)

    fw = guarded("Firmware laden", firmware.prepare, paths, m, rep)

    behind = None
    if paths.git_exe.is_file():
        behind = guarded("Trainings-Repos", repos.clone_all, paths, m, rep)
    else:
        rep.error("Trainings-Repos übersprungen: Git fehlt")

    if fw:
        if behind == []:
            guarded("Firmware ablegen", firmware.activate, paths, *fw, rep)
        else:
            rep.warn("Neue Firmware liegt in firmware.neu bereit, wird aber erst übernommen, "
                     "wenn alle Trainings aktualisiert sind (sonst passen die ELFs nicht)")

    guarded("Workspace-Liste", shortcuts.write_workspace_list, paths, m, rep)
    guarded("Verknüpfungen", shortcuts.apply, paths, m, rep)

    rep.step("PATH")
    try:
        if winsys.update_user_path(_tool_path_entries(paths)):
            rep.done("Benutzer-PATH ergänzt (gilt in neu geöffneten Fenstern)")
        else:
            rep.skip("Benutzer-PATH")
        for exe, own in (("git", paths.git / "cmd"), ("python", paths.python)):
            found = winsys.new_terminal_lookup(exe)
            if found and Path(found).parent != own:
                rep.warn(f"In neuen Terminals gewinnt ein anderes {exe}: {found} "
                         f"(System-PATH steht vor dem Benutzer-PATH)")
    except OSError as e:
        rep.error(f"PATH: {e}")

    if rep.report.ok:
        _cleanup_downloads(paths, m, rep)
    return rep.report.ok


def check(rep: Reporter, paths: Paths | None = None) -> bool:
    """Nur prüfen, nichts verändern (--check)."""
    paths = paths or Paths.default()
    rep.info(f"Trainings-Installer {installer_version()} – nur Prüfung")
    try:
        m = load_manifest()
    except manifest.ManifestError as e:
        rep.error(str(e))
        return False
    for key, folder in (("git", paths.git), ("python", paths.python), ("fordiac_ide", paths.ide)):
        have, want = tools.installed_version(folder), m[key]["version"]
        (rep.skip if have == want else rep.warn)(
            f"{key}: installiert {have or '–'}, Manifest {want}")
    for rel in m["fordiac_ide"].get("delete_after_extract", []):
        if (paths.tools / rel).exists():
            rep.error(f"{rel} existiert – muss gelöscht sein")
    if paths.git_exe.is_file():
        for name, e in m["repos"].items():
            d = repos.repo_dir(paths, name)
            if not d.exists():
                rep.warn(f"{name}: nicht geklont")
            elif repos.at_ref(paths, d, e["ref"]):
                rep.skip(f"{name}: {e['ref']}")
            else:
                rep.warn(f"{name}: nicht auf {e['ref']}")
    marker = paths.firmware / firmware.MARKER
    if marker.is_file():
        from .download import sha256_file
        (rep.skip if sha256_file(marker) == m["firmware"]["sha256"] else rep.warn)(
            f"Firmware: {m['firmware']['build']}")
    else:
        rep.warn("Firmware: nicht abgelegt")
    return rep.report.ok
