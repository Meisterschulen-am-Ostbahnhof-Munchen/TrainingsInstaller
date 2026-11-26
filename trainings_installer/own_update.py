"""Eigene Projekte (--new-project) aktualisieren (KONZEPT.md 2.6, entschieden 2026-11-26).

Eigene Projekte sind Kopien der leeren Vorlage und kennen sie als `upstream` (nur holen).
Anders als bei den Trainings gehört hier ALLES dem Schüler – nichts wird zurückgesetzt:
 1. IDE für diesen Workspace geschlossen? Branch arbeit? kein halber Merge?
 2. neuen Vorlagen-Tag holen (lokale Vorlage zuerst, sonst upstream)
 3. Sicherungs-Branch sicherung_<ts> (Stand inkl. nicht committeter Änderungen)
 4. eigene Änderungen als Commit auf arbeit festhalten
 5. git merge <Tag>: eigene Dateien bleiben, Vorlagenänderungen (auch .lib) kommen dazu
 6. bei Konflikt: Merge abbrechen und nur <workspace>/.lib auf den Tag setzen – die
    Bibliothek gehört der Vorlage und muss zur Firmware passen (KONZEPT 2.7)
Neue Firmware wird erst übernommen, wenn auch alle eigenen Projekte die passende .lib haben.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import repos, winsys
from .new_project import _source, template
from .paths import Paths
from .repos import GitError, git
from .report import Reporter

IDENTITY = ["-c", "user.name=TrainingsInstaller", "-c", "user.email=installer@ms-sl.invalid"]


class OwnUpdateError(Exception):
    pass


@dataclass
class OwnResult:
    name: str
    target: str
    changed: bool = False
    backup_branch: str = ""
    committed: bool = False
    lib_only: bool = False
    warnings: list[str] = field(default_factory=list)


def lib_path(tpl: dict) -> str:
    return f"{tpl['workspace']}/.lib"


def _norm(url: str) -> str:
    return url.strip().replace("\\", "/").rstrip("/").lower().removesuffix(".git")


def template_projects(paths: Paths, m: dict) -> list[Path]:
    """Eigene Projekte, deren upstream die Vorlage aus dem Manifest ist."""
    _, tpl = template(m)
    out = []
    for d in repos.own_projects(paths, m):
        try:
            url = git(paths, "remote", "get-url", "upstream", cwd=d)
        except GitError:
            continue
        if _norm(url) == _norm(tpl["url"]):
            out.append(d)
    return out


def lib_current(paths: Paths, d: Path, m: dict) -> bool:
    """Hat das Projekt (committet) genau die .lib des Vorlagen-Tags aus dem Manifest?"""
    _, tpl = template(m)
    lib = lib_path(tpl)
    try:
        want = git(paths, "rev-parse", "--verify", "--quiet", f"refs/tags/{tpl['ref']}:{lib}", cwd=d)
        have = git(paths, "rev-parse", "--verify", "--quiet", f"HEAD:{lib}", cwd=d)
    except GitError:
        return False
    return want == have


def base_tag(paths: Paths, d: Path) -> str:
    """Neuester Vorlagen-Tag im Stand des Projekts (für den Bericht)."""
    try:
        return git(paths, "describe", "--tags", "--abbrev=0", "HEAD", cwd=d)
    except GitError:
        return "?"


def behind(paths: Paths, m: dict) -> list[str]:
    return [d.name for d in template_projects(paths, m) if not lib_current(paths, d, m)]


def _is_ancestor(paths: Paths, d: Path, a: str, b: str) -> bool:
    try:
        git(paths, "merge-base", "--is-ancestor", a, b, cwd=d)
        return True
    except GitError:
        return False


def _fetch_tag(paths: Paths, d: Path, m: dict) -> None:
    tpl_name, tpl = template(m)
    spec = f"+refs/tags/{tpl['ref']}:refs/tags/{tpl['ref']}"
    local = _source(paths, tpl_name, tpl["ref"])
    if local:
        try:
            git(paths, "fetch", "--no-tags", local, spec, cwd=d)
            return
        except GitError:
            pass   # dann aus dem Netz
    git(paths, "fetch", "--no-tags", "upstream", spec, cwd=d)


def update_own(paths: Paths, d: Path, m: dict, ts: str, ides: list[dict] | None = None) -> OwnResult:
    tpl_name, tpl = template(m)
    ref = tpl["ref"]
    tag = f"refs/tags/{ref}"
    res = OwnResult(d.name, ref)

    # 1. Vorbedingungen – sonst nichts anfassen
    ws = d / tpl["workspace"]
    if ides is None:
        ides = winsys.running_ides(paths.tools)
    if any(str(ws).lower() in (p.get("CommandLine") or "").lower() for p in ides) \
            or winsys.workspace_locked(ws):
        raise OwnUpdateError(f"{d.name}: Bitte die 4diac IDE schließen (Workspace ist geöffnet)")
    if (d / ".git" / "MERGE_HEAD").exists():
        raise OwnUpdateError(f"{d.name}: unterbrochener Merge – bitte Lehrkraft fragen, nichts verändert")
    if git(paths, "branch", "--show-current", cwd=d) != repos.WORK_BRANCH:
        raise OwnUpdateError(f"{d.name}: steht nicht auf Branch {repos.WORK_BRANCH} – nicht aktualisiert")

    # 2. holen
    try:
        _fetch_tag(paths, d, m)
    except GitError as e:
        raise OwnUpdateError(f"{d.name}: Vorlage {ref} nicht erreichbar – nichts verändert ({e})") from e
    if _is_ancestor(paths, d, tag, "HEAD"):
        return res   # schon aktuell

    # 3. Sicherung (inkl. nicht committeter Änderungen, Arbeitsverzeichnis bleibt unberührt)
    snapshot = git(paths, *IDENTITY, "stash", "create", cwd=d) or git(paths, "rev-parse", "HEAD", cwd=d)
    res.backup_branch = f"sicherung_{ts}"
    git(paths, "branch", res.backup_branch, snapshot, cwd=d)
    res.changed = True

    # 4. eigenen Stand festhalten
    if git(paths, "status", "--porcelain", cwd=d):
        git(paths, "add", "-A", cwd=d)
        git(paths, *IDENTITY, "commit", "-q", "-m", f"Eigener Stand vor Update auf {ref}", cwd=d)
        res.committed = True

    # 5. Vorlage übernehmen
    try:
        git(paths, *IDENTITY, "merge", "--no-edit", "-m", f"Vorlage {tpl_name} {ref} übernommen",
            tag, cwd=d)
        return res
    except GitError:
        try:
            git(paths, "merge", "--abort", cwd=d)
        except GitError:
            pass

    # 6. Konflikt: nur die Bibliothek
    lib = lib_path(tpl)
    git(paths, "restore", f"--source={tag}", "--staged", "--worktree", "--", lib, cwd=d)
    try:
        git(paths, "diff", "--cached", "--quiet", cwd=d)
    except GitError:   # es gibt etwas zu committen
        git(paths, *IDENTITY, "commit", "-q", "-m", f"Bibliothek (.lib) auf {ref}", cwd=d)
    res.lib_only = True
    res.warnings.append(f"Vorlage {ref} passte nicht konfliktfrei zu deinen Änderungen – nur die "
                        f"Bibliothek (.lib) wurde aktualisiert, sonst nichts verändert")
    return res


def report_own(res: OwnResult, rep: Reporter) -> None:
    if not res.changed:
        rep.skip(f"{res.name} (eigenes Projekt, {res.target})")
        return
    what = "Bibliothek (.lib)" if res.lib_only else "Vorlage"
    lines = [f"{res.name}: {what} auf {res.target} aktualisiert, deine Dateien bleiben"]
    if res.committed:
        lines.append("deine Änderungen wurden vorher als Commit festgehalten")
    lines.append(f"Sicherung: Branch {res.backup_branch}")
    rep.done(" – ".join(lines))
    for w in res.warnings:
        rep.warn(f"{res.name}: {w}")
