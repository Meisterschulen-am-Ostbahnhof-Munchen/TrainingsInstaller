"""logiBUS-Firmware ablegen (KONZEPT.md 2.7). Der Installer flasht nicht.

Neue Fassung erst nach firmware.neu laden und prüfen; getauscht wird nur, wenn alle
Trainings-Repos auf dem passenden Tag stehen – nie neue Firmware mit alten ELFs.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .download import fetch, sha256_file
from .manifest import check_firmware_sync
from .paths import Paths
from .report import Reporter

MARKER = "firmware.json"


class FirmwareError(Exception):
    pass


def load_firmware_json(paths: Paths, m: dict, rep: Reporter) -> tuple[Path, dict]:
    e = m["firmware"]
    dest = paths.downloads / f"firmware_{e['sha256'][:12]}.json"
    fetch(e["url"], dest, e["sha256"])
    data = json.loads(dest.read_text(encoding="utf-8"))
    problems = check_firmware_sync(m, data)
    if problems:
        raise FirmwareError("Firmware passt nicht zum Manifest: " + "; ".join(problems))
    return dest, data


def _files(data: dict):
    for target, t in data["targets"].items():
        for kind in ("application", "merged_flash"):
            if kind in t:
                yield target, t[kind]


def installed_ok(folder: Path, sha_json: str, data: dict) -> bool:
    marker = folder / MARKER
    if not marker.is_file() or sha256_file(marker) != sha_json:
        return False
    return all((folder / target / f["file"]).is_file()
               and (folder / target / f["file"]).stat().st_size == f["size"]
               for target, f in _files(data))


def prepare(paths: Paths, m: dict, rep: Reporter) -> tuple[Path, dict] | None:
    """Lädt die Firmware nach firmware.neu. None = bereits aktuell."""
    json_file, data = load_firmware_json(paths, m, rep)
    build = data.get("build", "?")
    if installed_ok(paths.firmware, m["firmware"]["sha256"], data):
        rep.skip(f"Firmware {build}")
        return None
    neu = paths.root / "firmware.neu"
    base = m["firmware"]["url"].rsplit("/", 1)[0]
    files = list(_files(data))
    rep.info(f"Lade Firmware {build} ({len(data['targets'])} Targets, {len(files)} Dateien) …")
    for i, (target, f) in enumerate(files, 1):
        fetch(f"{base}/{f['file']}", neu / target / f["file"], f["sha256"])
        rep.progress(i, len(files))
    shutil.copy2(json_file, neu / MARKER)
    return neu, data


def activate(paths: Paths, neu: Path, data: dict, rep: Reporter) -> None:
    if paths.firmware.exists():
        shutil.rmtree(paths.firmware)
    neu.rename(paths.firmware)
    rep.done(f"Firmware {data.get('build')} abgelegt in {paths.firmware}")
    # Projekte und ELFs passen nur zu genau dieser Firmware (KONZEPT 2.7) – der Installer
    # flasht nicht, also deutlich im Bericht erinnern
    rep.warn(f"Geräte auf Firmware {data.get('build')} aktualisieren "
             "(Application_<Board>.bin aus dem Ordner firmware im Browser hochladen). "
             "Mit älterer Firmware laden die ELF-Bibliotheken der Projekte nicht "
             "(z. B. fehlen dann alle logiBUS-IOs).")
