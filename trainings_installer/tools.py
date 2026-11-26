"""Git, 4diac IDE und Auto-Import-Plugin installieren (KONZEPT.md 2.1, 2.3, 2.5, 2.6).

Immer „erst laden, dann tauschen“: neue Version nach <ordner>.neu entpacken und erst
ersetzen, wenn alles geklappt hat. Bricht etwas ab, bleibt die alte Version nutzbar.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from . import winsys
from .download import fetch
from .manifest import url_filename
from .paths import Paths
from .report import Reporter

VERSION_FILE = ".ms-sl-version"

CUSTOMIZATION_INI = (
    "org.eclipse.ui/showIntro=false\n"
    "org.eclipse.ui/windows.defender.startup.check.skip=true\n"
)


class StepError(Exception):
    pass


def installed_version(folder: Path) -> str:
    f = folder / VERSION_FILE
    return f.read_text(encoding="ascii").strip() if f.is_file() else ""


def _rmtree(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)


def _swap(new: Path, target: Path) -> None:
    _rmtree(target)
    new.rename(target)


def _download(paths: Paths, entry: dict, rep: Reporter) -> Path:
    dest = paths.downloads / url_filename(entry["url"])
    rep.info(f"Lade {dest.name} …")
    if fetch(entry["url"], dest, entry["sha256"], rep.progress):
        rep.info(f"{dest.name} geladen, SHA256 geprüft")
    else:
        rep.info(f"{dest.name} bereits im Cache (SHA256 passt)")
    return dest


# ----------------------------------------------------------------------- Git (2.3)

def install_git(paths: Paths, m: dict, rep: Reporter) -> None:
    e = m["git"]
    if installed_version(paths.git) == e["version"] and paths.git_exe.is_file():
        rep.skip(f"Git {e['version']}")
        return
    archive = _download(paths, e, rep)
    neu = paths.tools / "git.neu"
    _rmtree(neu)
    rep.info("Entpacke Git …")
    r = winsys.run([str(archive), f"-o{neu}", "-y"])
    if r.returncode != 0 or not (neu / "cmd" / "git.exe").is_file():
        _rmtree(neu)
        raise StepError(f"Git entpacken fehlgeschlagen: {r.stderr.strip() or r.stdout.strip()}")
    r = winsys.run([str(neu / "cmd" / "git.exe"), "config", "--system", "http.sslBackend", "schannel"])
    if r.returncode != 0:
        _rmtree(neu)
        raise StepError(f"git config fehlgeschlagen: {r.stderr.strip()}")
    (neu / VERSION_FILE).write_text(e["version"], encoding="ascii")
    _swap(neu, paths.git)
    rep.done(f"Git {e['version']} installiert")


# ------------------------------------------------------------------ 4diac IDE (2.1)

def _delete_after_extract(base: Path, entry: dict) -> None:
    """z. B. typelibrary löschen – Pflicht, sonst gilt die Installation als fehlgeschlagen."""
    for rel in entry.get("delete_after_extract", []):
        p = base / rel
        _rmtree(p)
        if p.exists():
            raise StepError(f"{rel} konnte nicht gelöscht werden")


def _ide_ok(paths: Paths, entry: dict) -> bool:
    if installed_version(paths.ide) != entry["version"] or not paths.ide_exe.is_file():
        return False
    return not any((paths.tools / rel).exists() for rel in entry.get("delete_after_extract", []))


def install_ide(paths: Paths, m: dict, rep: Reporter, workspaces: list[Path]) -> bool:
    """Gibt True zurück, wenn die IDE neu installiert oder gewechselt wurde."""
    e = m["fordiac_ide"]
    if _ide_ok(paths, e):
        rep.skip(f"4diac IDE {e['version']}")
        return False
    old_version = installed_version(paths.ide)
    if paths.ide.exists() and old_version == e["version"]:
        # gleiche Version, aber z. B. typelibrary wieder da → nur nachbessern
        _delete_after_extract(paths.tools, e)
        rep.done("4diac IDE: typelibrary entfernt")
        return False
    busy = winsys.ide_running(paths.tools, workspaces)
    if busy:
        raise StepError("Bitte die 4diac IDE schließen (" + "; ".join(busy) + ")")
    archive = _download(paths, e, rep)
    stage = paths.tools / "4diac-ide.entpacken"
    neu = paths.tools / "4diac-ide.neu"
    _rmtree(stage)
    _rmtree(neu)
    rep.info("Entpacke 4diac IDE (ca. 4 000 Dateien) …")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        for i, member in enumerate(members, 1):
            z.extract(member, stage)
            if i % 200 == 0 or i == len(members):
                rep.progress(i, len(members))
    if not (stage / "4diac-ide" / "4diac-ide.exe").is_file():
        _rmtree(stage)
        raise StepError("ZIP enthält kein 4diac-ide/4diac-ide.exe")
    _delete_after_extract(stage, e)
    (stage / "4diac-ide").rename(neu)
    _rmtree(stage)
    (neu / VERSION_FILE).write_text(e["version"], encoding="ascii")
    _swap(neu, paths.ide)
    if old_version:
        rep.done(f"4diac IDE {old_version} → {e['version']} aktualisiert")
        _delete_metadata(workspaces, rep)
    else:
        rep.done(f"4diac IDE {e['version']} installiert (typelibrary gelöscht)")
    return True


def _delete_metadata(workspaces: list[Path], rep: Reporter) -> None:
    """Nach einem IDE-Versionswechsel .metadata aller Workspaces löschen (2.6)."""
    for w in workspaces:
        md = w / ".metadata"
        if md.is_dir():
            shutil.rmtree(md, ignore_errors=True)
            rep.info(f".metadata gelöscht: {w}")


def install_plugin(paths: Paths, m: dict, rep: Reporter) -> None:
    e = m["fordiac_autoimport"]
    jar = _download(paths, e, rep)
    dropins = paths.root / e.get("target", "tools/4diac-ide/dropins")
    dropins.mkdir(parents=True, exist_ok=True)
    stem = jar.name.split("_")[0]
    for old in dropins.glob(f"{stem}_*.jar"):
        if old.name != jar.name:
            old.unlink()
    dest = dropins / jar.name
    if dest.is_file() and dest.read_bytes() == jar.read_bytes():
        rep.skip(f"Auto-Import-Plugin {e['version']}")
        return
    shutil.copy2(jar, dest)
    rep.done(f"Auto-Import-Plugin {e['version']} nach dropins kopiert")


def write_customization(paths: Paths) -> None:
    if paths.ide.is_dir():
        paths.ide_customization.write_text(CUSTOMIZATION_INI, encoding="ascii")
