"""Trainings-Repos klonen (KONZEPT.md 3.2).

Geklont wird der Tag aus dem Manifest, danach lokaler Arbeits-Branch `arbeit`.
Das Aktualisieren bestehender Repos (2.6, mit .SUB-Sicherung) kommt mit `--update`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import winsys
from .paths import Paths
from .report import Reporter

WORK_BRANCH = "arbeit"


class GitError(Exception):
    pass


GIT_TIMEOUT = 20 * 60   # Sekunden; ein Klon darf nie endlos hängen


def git(paths: Paths, *args: str, cwd: Path | None = None) -> str:
    # Nie nach Zugangsdaten fragen: kein Terminal-Prompt, kein Credential-Helfer
    # (PortableGit startet sonst ein Auswahlfenster und wartet darauf – bei privaten Repos
    # hinge der Installer). Alle Trainings-Repos müssen öffentlich sein.
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    cmd = [str(paths.git_exe), "-c", "credential.helper=", *args]
    try:
        r = winsys.run(cmd, cwd=cwd, env=env, timeout=GIT_TIMEOUT)
    except subprocess.TimeoutExpired as e:
        raise GitError(f"git {' '.join(args)}: keine Antwort nach {GIT_TIMEOUT // 60} min") from e
    if r.returncode != 0:
        msg = (r.stderr or r.stdout).strip()
        if "could not read Username" in msg or "Authentication failed" in msg:
            msg = "kein Zugriff – das Repo ist nicht öffentlich"
        raise GitError(f"git {' '.join(args)}: {msg}")
    return r.stdout.strip()


def repo_dir(paths: Paths, name: str) -> Path:
    return paths.prj / name


def workspace(paths: Paths, name: str, entry: dict) -> Path:
    return repo_dir(paths, name) / Path(entry["workspace"])


def own_projects(paths: Paths, m: dict) -> list[Path]:
    """Eigene Projekte (--new-project): Ordner in prj, die nicht im Manifest stehen."""
    if not paths.prj.is_dir():
        return []
    tpl = next(e for e in m["repos"].values() if e.get("template_for_new_projects"))
    return sorted(d for d in paths.prj.iterdir()
                  if d.is_dir() and d.name not in m["repos"] and not d.name.startswith(".")
                  and (d / ".git").exists() and (d / tpl["workspace"]).is_dir())


def all_workspaces(paths: Paths, m: dict) -> list[Path]:
    tpl = next(e for e in m["repos"].values() if e.get("template_for_new_projects"))
    ws = [workspace(paths, n, e) for n, e in m["repos"].items()]
    ws += [p / tpl["workspace"] for p in own_projects(paths, m)]
    return [w for w in ws if w.is_dir()]


def at_ref(paths: Paths, d: Path, ref: str) -> bool:
    """Enthält der aktuelle Stand den Tag? (Schüler-Commits auf `arbeit` sind erlaubt.)"""
    try:
        git(paths, "rev-parse", "--verify", "--quiet", f"refs/tags/{ref}^{{commit}}", cwd=d)
        git(paths, "merge-base", "--is-ancestor", f"refs/tags/{ref}", "HEAD", cwd=d)
        return True
    except GitError:
        return False


def _has_head(paths: Paths, d: Path) -> bool:
    try:
        git(paths, "rev-parse", "--verify", "--quiet", "HEAD", cwd=d)
        return True
    except GitError:
        return False


def clone_all(paths: Paths, m: dict, rep: Reporter) -> list[str]:
    """Klont fehlende Repos. Gibt die Repos zurück, die nicht auf dem Manifest-Tag stehen."""
    behind: list[str] = []
    for name, e in m["repos"].items():
        d = repo_dir(paths, name)
        if d.exists() and (d / ".git").exists() and not _has_head(paths, d):
            rep.info(f"{name}: abgebrochener Klon wird verworfen")   # ohne Commit nichts zu verlieren
            shutil.rmtree(d, ignore_errors=True)
        if d.exists():
            if not (d / ".git").exists():
                rep.error(f"{d} existiert, ist aber kein Git-Repo – bitte prüfen")
                behind.append(name)
            elif at_ref(paths, d, e["ref"]):
                rep.skip(f"{name} ({e['ref']})")
            else:
                rep.warn(f"{name} steht nicht auf {e['ref']} – aktualisieren mit "
                         f"„Trainings aktualisieren“ (--update)")
                behind.append(name)
            continue
        rep.info(f"Klone {name} ({e['ref']}) …")
        try:
            git(paths, "clone", "--branch", e["ref"], e["url"], str(d))
            git(paths, "switch", "-c", WORK_BRANCH, cwd=d)
        except GitError as ex:
            if d.exists() and not (d / ".git" / "HEAD").is_file():
                shutil.rmtree(d, ignore_errors=True)   # halber Klon blockiert sonst den nächsten Lauf
            rep.error(f"{name}: {ex}")
            behind.append(name)
            continue
        rep.done(f"{name} ({e['ref']}) geklont, Branch {WORK_BRANCH}")
    return behind
