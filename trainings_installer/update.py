"""Trainings aktualisieren (KONZEPT.md 2.6) – der Schüler verliert keine Übung.

Je Repo:
 1. IDE für diesen Workspace geschlossen?
 2. git fetch --tags; Tag aus dem Manifest → ZIEL
 3. Sicherungs-Branch sicherung_<ts> (git stash create, ohne Arbeitsverzeichnis anzufassen)
 4. vom Schüler geänderte .SUB finden (ZIEL...Sicherung)
 5. diese .SUB als <Name>_sicherung_<ts>.SUB daneben schreiben, Typname mit umbenannt
 6. git reset --hard
 7. git checkout -B arbeit ZIEL (ohne -f; eigene Dateien im Weg werden umbenannt)
 8. Bericht
Sicherungs-Branches und .SUB-Sicherungen werden nie gelöscht.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import firmware, repos, winsys
from .paths import Paths
from .repos import GitError, git
from .report import Reporter

IDENTITY = ["-c", "user.name=TrainingsInstaller", "-c", "user.email=installer@ms-sl.invalid"]
SUB_RE = re.compile(rb'(<SubAppType\b[^>]*?\bName=")([^"]*)(")', re.S)
BACKUP_MARK = "_sicherung_"


class UpdateError(Exception):
    pass


@dataclass
class RepoResult:
    name: str
    target: str = ""
    changed: bool = False
    backup_branch: str = ""
    backup_branch_arbeit: str = ""
    saved_subs: list[str] = field(default_factory=list)
    deleted_subs: list[str] = field(default_factory=list)
    renamed_in_way: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def rename_sub_type(data: bytes, new_name: str) -> bytes:
    """Nur das Name-Attribut des Wurzelelements <SubAppType Name="…"> ersetzen."""
    return SUB_RE.sub(lambda m: m.group(1) + new_name.encode("utf-8") + m.group(3), data, count=1)


def backup_path(original: Path, ts: str) -> Path:
    """<Name>_sicherung_<ts>.<Endung>, bei Kollision _2, _3 …"""
    stem, suffix = original.stem, original.suffix
    p = original.with_name(f"{stem}{BACKUP_MARK}{ts}{suffix}")
    n = 2
    while p.exists():
        p = original.with_name(f"{stem}{BACKUP_MARK}{ts}_{n}{suffix}")
        n += 1
    return p


def write_backup(original: Path, data: bytes, ts: str) -> Path:
    dest = backup_path(original, ts)
    if original.suffix.lower() == ".sub":
        data = rename_sub_type(data, dest.stem)
    dest.write_bytes(data)
    return dest


def _git_bytes(paths: Paths, d: Path, *args: str) -> bytes:
    r = winsys.run([str(paths.git_exe), "-c", "credential.helper=", *args], cwd=d,
                   text=False, encoding=None, errors=None)
    if r.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def _is_ancestor(paths: Paths, d: Path, a: str, b: str) -> bool:
    try:
        git(paths, "merge-base", "--is-ancestor", a, b, cwd=d)
        return True
    except GitError:
        return False


def _blocking_paths(msg: str) -> list[str]:
    """Pfade aus der Git-Meldung „… would be overwritten by checkout:“ (tab-eingerückt)."""
    out, collecting = [], False
    for line in msg.splitlines():
        if "would be overwritten" in line or "would be removed" in line:
            collecting = True
            continue
        if collecting:
            if line.startswith("\t"):
                out.append(line.strip())
            else:
                collecting = False
    return out


def update_repo(paths: Paths, name: str, entry: dict, rep: Reporter, ts: str | None = None,
                ides: list[dict] | None = None) -> RepoResult:
    ts = ts or timestamp()
    d = repos.repo_dir(paths, name)
    res = RepoResult(name)
    ws = repos.workspace(paths, name, entry)

    # 1. IDE geschlossen?
    if ides is None:
        ides = winsys.running_ides(paths.tools)
    busy = [p for p in ides if str(ws).lower() in (p.get("CommandLine") or "").lower()]
    if busy or winsys.workspace_locked(ws):
        raise UpdateError(f"{name}: Bitte die 4diac IDE schließen (Workspace ist geöffnet)")

    # 2. holen, ZIEL bestimmen
    git(paths, "fetch", "--tags", "--force", "origin", cwd=d)
    ref = entry["ref"]
    try:
        target = git(paths, "rev-parse", "--verify", f"refs/tags/{ref}^{{commit}}", cwd=d)
    except GitError:
        try:
            target = git(paths, "rev-parse", "--verify", f"origin/{ref}^{{commit}}", cwd=d)
        except GitError as e:
            raise UpdateError(f"{name}: {ref} nicht gefunden – nichts verändert") from e
    res.target = ref

    # 3. Sicherungs-Branch
    head = git(paths, "rev-parse", "HEAD", cwd=d)
    stash = git(paths, *IDENTITY, "stash", "create", cwd=d)
    snapshot = stash or head
    current = git(paths, "branch", "--show-current", cwd=d)
    res.changed = snapshot != target or current != repos.WORK_BRANCH
    if snapshot != target:   # HEAD = ZIEL und nichts geändert → keine leere Sicherung
        res.backup_branch = f"sicherung_{ts}"
        git(paths, "branch", res.backup_branch, snapshot, cwd=d)

    # Arbeits-Branch nicht verlieren, wenn der Schüler gerade woanders steht
    if current != repos.WORK_BRANCH:
        try:
            arbeit = git(paths, "rev-parse", "--verify", f"refs/heads/{repos.WORK_BRANCH}", cwd=d)
        except GitError:
            arbeit = ""
        if arbeit and not _is_ancestor(paths, d, arbeit, snapshot) and not _is_ancestor(paths, d, arbeit, target):
            res.backup_branch_arbeit = f"sicherung_{ts}_{repos.WORK_BRANCH}"
            git(paths, "branch", res.backup_branch_arbeit, arbeit, cwd=d)

    # 4. + 5. veränderte .SUB sichern – vor dem Zurücksetzen
    if res.backup_branch:
        out = git(paths, "diff", "--name-status", "--no-renames", "-z",
                  f"{target}...{res.backup_branch}", cwd=d)
        fields = [f for f in out.split("\0") if f]
        for status, path in zip(fields[0::2], fields[1::2]):
            if not path.lower().endswith(".sub") or BACKUP_MARK in Path(path).stem:
                continue
            if status.startswith("D"):
                res.deleted_subs.append(path)
                continue
            if "/.lib/" in f"/{path}":
                # Bibliothek wird per .lib-Sync verwaltet – keine Kopie hineinlegen (wäre ein
                # zusätzlicher Typ in der Bibliothek); die Änderung steckt im Sicherungs-Branch.
                res.warnings.append(f"Bibliotheksdatei {path} war geändert – nur im Branch "
                                    f"{res.backup_branch} gesichert")
                continue
            data = _git_bytes(paths, d, "show", f"{res.backup_branch}:{path}")
            dest = write_backup(d / path, data, ts)
            res.saved_subs.append(str(dest.relative_to(d)).replace("\\", "/"))
        stems = {Path(p).stem for p in res.saved_subs}
        originals = {s.split(BACKUP_MARK)[0] for s in stems}
        for saved in res.saved_subs:
            text = (d / saved).read_bytes()
            for o in originals - {Path(saved).stem.split(BACKUP_MARK)[0]}:
                if f'"{o}"'.encode() in text:
                    res.warnings.append(f"{saved} verweist auf {o} – zeigt weiter auf das Original, "
                                        f"nicht auf dessen Sicherung")

    # 6. eigene Änderungen verwerfen (stecken im Sicherungs-Branch)
    git(paths, "reset", "--hard", "--quiet", cwd=d)

    # 7. auf ZIEL – ohne -f, eigene unversionierte Dateien im Weg umbenennen
    for attempt in (1, 2):
        try:
            git(paths, "checkout", "-B", repos.WORK_BRANCH, target, cwd=d)
            break
        except GitError as e:
            blocking = _blocking_paths(str(e))
            if attempt == 2 or not blocking:
                raise UpdateError(f"{name}: Wechsel auf {ref} nicht möglich: {e}") from e
            for rel in blocking:
                p = d / rel
                if p.exists():
                    dest = write_backup(p, p.read_bytes(), ts) if p.is_file() else None
                    if dest is None:
                        dest = backup_path(p, ts)
                        p.rename(dest)
                    else:
                        p.unlink()
                    res.renamed_in_way.append(f"{rel} → {dest.name}")
    return res


def report_repo(res: RepoResult, rep: Reporter) -> None:
    if not res.changed:
        rep.skip(f"{res.name} ({res.target})")
        return
    lines = [f"{res.name} auf {res.target} aktualisiert"]
    if res.saved_subs:
        lines.append("deine geänderten Übungen wurden gesichert: " + ", ".join(res.saved_subs))
    if res.backup_branch:
        lines.append(f"vollständige Sicherung: Branch {res.backup_branch}")
    rep.done(" – ".join(lines))
    if res.backup_branch_arbeit:
        rep.warn(f"{res.name}: Branch arbeit gesichert als {res.backup_branch_arbeit}")
    for p in res.deleted_subs:
        rep.warn(f"{res.name}: von dir gelöscht, nicht gesichert: {p} (Lehrkraft kann sie "
                 f"aus {res.backup_branch} zurückholen)")
    for r in res.renamed_in_way:
        rep.warn(f"{res.name}: eigene Datei war im Weg und wurde umbenannt: {r}")
    for w in res.warnings:
        rep.warn(f"{res.name}: {w}")


def update(rep: Reporter, paths: Paths | None = None, only: str | None = None) -> bool:
    """--update [<repo>]: Trainings auf die Tags aus dem Manifest bringen, dann Firmware."""
    from . import core   # Zyklus vermeiden

    paths = paths or Paths.default()
    paths.ensure()
    rep.info(f"Trainings-Installer {core.installer_version()} – Trainings aktualisieren")
    m = core.load_manifest()
    if not paths.git_exe.is_file():
        rep.error("Git fehlt – bitte zuerst „Installieren / Reparieren“")
        return False
    if only and only not in m["repos"]:
        rep.error(f"Unbekanntes Training: {only} (bekannt: {', '.join(m['repos'])})")
        return False
    names = [only] if only else list(m["repos"])
    fw = None
    try:
        rep.step("Firmware laden")
        fw = firmware.prepare(paths, m, rep)
    except Exception as e:   # noqa: BLE001 – Firmware-Fehler darf das Update der Übungen nicht verhindern
        rep.error(f"Firmware: {e}")
    ts = timestamp()
    ides = winsys.running_ides(paths.tools)
    for name in names:
        rep.step(name)
        d = repos.repo_dir(paths, name)
        if not (d / ".git").exists():
            repos.clone_all(paths, {**m, "repos": {name: m["repos"][name]}}, rep)
            continue
        try:
            report_repo(update_repo(paths, name, m["repos"][name], rep, ts, ides), rep)
        except (UpdateError, GitError, OSError) as e:
            rep.error(str(e))
    if fw:
        behind = [n for n, e in m["repos"].items()
                  if not repos.at_ref(paths, repos.repo_dir(paths, n), e["ref"])]
        if behind:
            rep.warn("Neue Firmware bleibt in firmware.neu, bis alle Trainings aktuell sind: "
                     + ", ".join(behind))
        else:
            firmware.activate(paths, *fw, rep)
    return rep.report.ok
