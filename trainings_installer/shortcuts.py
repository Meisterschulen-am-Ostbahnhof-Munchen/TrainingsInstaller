"""Verknüpfungen und Workspace-Liste (KONZEPT.md 2.5).

Keine doppelten Verknüpfungen: Jede Verknüpfung hat einen festen Namen; eigene stehen in
C:\\ms\\sl\\shortcuts.json und werden überschrieben. Eine fremde gleichen Namens bleibt
unangetastet, dann heißt unsere „<Name> (Schule)“.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import repos, winsys
from .paths import Paths
from .report import Reporter

INSTALLER_SHORTCUT = "4diac Trainings-Installer"


@dataclass
class Shortcut:
    name: str
    target: str
    args: str
    workdir: str
    desktop: bool = True
    start_menu: bool = True
    icon: str = ""
    description: str = ""


def _ide_args(paths: Paths, data: str) -> str:
    return f'-data "{data}" -pluginCustomization "{paths.ide_customization}"'


def plan(paths: Paths, m: dict, rep: Reporter | None = None) -> list[Shortcut]:
    ide = str(paths.ide_exe)
    out = [
        Shortcut("4diac Projekte", str(paths.prj), "", str(paths.prj),
                 description="Ordner mit allen 4diac-Trainings"),
        Shortcut("4diac IDE", ide, _ide_args(paths, "@noDefault"), str(paths.prj),
                 description="4diac IDE mit Workspace-Auswahl"),
    ]
    for name, e in m["repos"].items():
        ws = repos.workspace(paths, name, e)
        if ws.is_dir():
            out.append(Shortcut(e["shortcut"], ide, _ide_args(paths, str(ws)), str(paths.ide)))
        for t in e.get("tool_shortcuts", []):
            script = repos.repo_dir(paths, name) / t["script"]
            if not script.is_file():
                if rep:
                    rep.warn(f"Verknüpfung „{t['name']}“ fehlt: {t['script']} ist im Tag "
                             f"{e['ref']} nicht enthalten")
                continue
            out.append(Shortcut(t["name"], str(paths.python / "pythonw.exe"), script.name,
                                str(repos.repo_dir(paths, name) / t["workdir"])))
    tpl = next(e for e in m["repos"].values() if e.get("template_for_new_projects"))
    for proj in repos.own_projects(paths, m):
        out.append(Shortcut(f"4diac – {proj.name}", ide,
                            _ide_args(paths, str(proj / tpl["workspace"])), str(paths.ide)))
    out.append(Shortcut(
        INSTALLER_SHORTCUT, "powershell.exe",
        f'-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{paths.installer / "install.ps1"}"',
        str(paths.installer), desktop=False))
    return out


def _load_owned(paths: Paths) -> set[str]:
    try:
        return set(json.loads(paths.shortcuts_json.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def resolve(planned: list[Shortcut], locations: dict[str, Path], owned: set[str]
            ) -> tuple[list[dict], list[str], list[str]]:
    """Ermittelt die .lnk-Pfade. Gibt (anzulegen, neue Eigentumsliste, Warnungen) zurück."""
    items: list[dict] = []
    keep: list[str] = []
    warnings: list[str] = []
    for s in planned:
        for loc, folder in locations.items():
            if (loc == "desktop" and not s.desktop) or (loc == "start" and not s.start_menu):
                continue
            path = None
            for candidate in (f"{s.name}.lnk", f"{s.name} (Schule).lnk"):
                p = folder / candidate
                if not p.exists() or str(p) in owned:
                    path = p
                    break
            if path is None:
                warnings.append(f"Verknüpfung „{s.name}“ nicht angelegt: fremde Verknüpfungen "
                                f"gleichen Namens in {folder}")
                continue
            keep.append(str(path))
            items.append({"path": str(path), "target": s.target, "args": s.args,
                          "workdir": s.workdir, "icon": s.icon, "description": s.description})
    return items, keep, warnings


def apply(paths: Paths, m: dict, rep: Reporter) -> None:
    locations = {"desktop": winsys.desktop_dir(), "start": winsys.start_menu_dir()}
    owned = _load_owned(paths)
    items, keep, warnings = resolve(plan(paths, m, rep), locations, owned)
    for w in warnings:
        rep.warn(w)
    winsys.create_shortcuts(items)
    for old in owned - set(keep):   # Verknüpfungen zu Trainings, die es nicht mehr gibt
        Path(old).unlink(missing_ok=True)
    paths.shortcuts_json.write_text(json.dumps(sorted(keep), ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    rep.done(f"{len(items)} Verknüpfungen (Desktop + Startmenü)")


# ------------------------------------------------------- Workspace-Liste der IDE

def _escape(path: str) -> str:
    return path.replace("\\", "\\\\").replace(":", "\\:")


def recent_workspaces_prefs(workspaces: list[Path]) -> str:
    entries = "\\n".join(_escape(str(w)) for w in workspaces)
    return ("eclipse.preferences.version=1\n"
            f"MAX_RECENT_WORKSPACES={max(10, len(workspaces))}\n"
            f"RECENT_WORKSPACES={entries}\n"
            "RECENT_WORKSPACES_PROTOCOL=3\n"
            "SHOW_RECENT_WORKSPACES=true\n"
            "SHOW_WORKSPACE_SELECTION_DIALOG=true\n")


def write_workspace_list(paths: Paths, m: dict, rep: Reporter) -> None:
    if not paths.ide.is_dir():
        return
    if winsys.running_ides(paths.tools):
        rep.warn("Workspace-Liste nicht geschrieben, weil die 4diac IDE läuft – "
                 "wird beim nächsten Start des Installers nachgeholt")
        return
    f = paths.ide / "configuration" / ".settings" / "org.eclipse.ui.ide.prefs"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(recent_workspaces_prefs(repos.all_workspaces(paths, m)), encoding="latin-1")
    rep.info("Workspace-Liste der IDE geschrieben")
