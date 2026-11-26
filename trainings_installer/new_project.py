"""Neues eigenes Projekt (KONZEPT.md 2.5, „zweites Empty“).

  0. Namen prüfen – vor jedem anderen Schritt
  1. Vorlage (template_for_new_projects, z. B. 4diac_training1_empty) mit dem Tag aus dem
     Manifest nach C:\\ms\\sl\\prj\\<Name> klonen, Branch `arbeit`
  2. Push-Sperre: origin → upstream, Push-URL ungültig, kein Tracking
  3. Verknüpfung „4diac – <Name>“ und Workspace-Liste
Geklont wird in einen versteckten Hilfsordner und erst am Ende umbenannt: Bricht etwas ab,
bleibt kein halbes Projekt liegen.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import repos, shortcuts
from .paths import Paths
from .repos import GitError, git
from .report import Reporter

NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
# Gerätenamen, die Windows als Ordnernamen nicht zulässt
RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)), *(f"lpt{i}" for i in range(10))}
PUSH_BLOCKED = "PUSH-DEAKTIVIERT-EIGENES-REMOTE-EINTRAGEN"


class NewProjectError(Exception):
    pass


def check_name(name: str, paths: Paths, m: dict) -> str | None:
    """Fehlertext oder None. Läuft vor jedem anderen Schritt."""
    if not NAME_RE.fullmatch(name or ""):
        return ("Ungültiger Name: erlaubt sind nur Buchstaben A–Z, Ziffern, _ und -, "
                "höchstens 40 Zeichen, keine Leerzeichen und keine Umlaute")
    if name.lower() in RESERVED:
        return f"„{name}“ ist unter Windows als Ordnername nicht erlaubt"
    if name.lower() in {r.lower() for r in m["repos"]}:
        return f"„{name}“ ist der Name eines Trainings – bitte einen anderen wählen"
    if (paths.prj / name).exists():
        return f"{paths.prj / name} gibt es schon – nichts überschrieben, bitte anderen Namen wählen"
    return None


def template(m: dict) -> tuple[str, dict]:
    return next((n, e) for n, e in m["repos"].items() if e.get("template_for_new_projects"))


def _source(paths: Paths, tpl_name: str, ref: str) -> str | None:
    """Lokale Vorlage, wenn sie den Tag hat (schnell, offline) – sonst None (aus dem Netz)."""
    d = repos.repo_dir(paths, tpl_name)
    if not (d / ".git").exists():
        return None
    try:
        git(paths, "rev-parse", "--verify", "--quiet", f"refs/tags/{ref}^{{commit}}", cwd=d)
        return str(d)
    except GitError:
        return None


def create(paths: Paths, m: dict, name: str, rep: Reporter) -> Path:
    err = check_name(name, paths, m)
    if err:
        raise NewProjectError(err)
    if not paths.git_exe.is_file():
        raise NewProjectError("Git fehlt – bitte zuerst „Installieren / Reparieren“")
    tpl_name, tpl = template(m)
    ref = tpl["ref"]
    dest = paths.prj / name
    tmp = paths.prj / f".neu_{name}"   # Punkt am Anfang: zählt nicht als Projekt
    if tmp.exists():
        shutil.rmtree(tmp)
    paths.prj.mkdir(parents=True, exist_ok=True)

    src = _source(paths, tpl_name, ref)
    rep.info(f"Kopiere {tpl_name} ({ref}) {'aus der lokalen Vorlage' if src else 'aus dem Netz'} …")
    try:
        git(paths, "clone", "--branch", ref, src or tpl["url"], str(tmp))
        if src:   # Herkunft = Schul-Repo, nicht der lokale Ordner
            git(paths, "remote", "set-url", "origin", tpl["url"], cwd=tmp)
        git(paths, "switch", "-c", repos.WORK_BRANCH, cwd=tmp)
        # Push-Sperre (entschieden 2026-11-26): Updates der Vorlage holen geht, Pushen nicht
        git(paths, "remote", "rename", "origin", "upstream", cwd=tmp)
        git(paths, "remote", "set-url", "--push", "upstream", PUSH_BLOCKED, cwd=tmp)
        try:
            git(paths, "branch", "--unset-upstream", cwd=tmp)
        except GitError:
            pass   # neuer Branch ohne Tracking – nichts zu entfernen
        if not (tmp / tpl["workspace"]).is_dir():
            raise NewProjectError(f"Vorlage {tpl_name} hat keinen Workspace {tpl['workspace']}")
        if dest.exists():   # zwischenzeitlich angelegt
            raise NewProjectError(f"{dest} gibt es schon – nichts überschrieben")
        tmp.rename(dest)
    except (GitError, OSError, NewProjectError):
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    rep.done(f"Projekt {name} angelegt: {dest / tpl['workspace']}")
    return dest


def new_project(rep: Reporter, paths: Paths | None = None, name: str = "") -> bool:
    """--new-project <Name>"""
    from . import core   # Zyklus vermeiden

    paths = paths or Paths.default()
    paths.ensure()
    rep.info(f"Trainings-Installer {core.installer_version()} – Neues Projekt „{name}“")
    m = core.load_manifest()
    rep.step("Projekt anlegen")
    try:
        create(paths, m, name, rep)
    except (NewProjectError, GitError, OSError) as e:
        rep.error(str(e))
        return False
    for title, fn in (("Workspace-Liste", shortcuts.write_workspace_list),
                      ("Verknüpfungen", shortcuts.apply)):
        rep.step(title)
        try:
            fn(paths, m, rep)
        except (OSError, RuntimeError) as e:
            rep.error(f"{title}: {e}")
    if rep.report.ok:
        rep.info(f"Start: Verknüpfung „4diac – {name}“ auf dem Desktop. Die Projekte "
                 "erscheinen beim ersten Start der IDE automatisch.")
    return rep.report.ok
