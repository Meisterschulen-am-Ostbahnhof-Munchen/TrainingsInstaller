"""manifest.json laden und prüfen (KONZEPT.md 3.2)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
TOOLS = ("git", "python", "fordiac_ide", "fordiac_autoimport")


class ManifestError(Exception):
    pass


def url_filename(url: str) -> str:
    return unquote(Path(urlparse(url).path).name)


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ManifestError(f"{path} nicht lesbar: {e}") from e
    problems = validate(data)
    if problems:
        raise ManifestError("manifest.json ungültig:\n  " + "\n  ".join(problems))
    return data


def validate(m: dict) -> list[str]:
    p: list[str] = []
    for key in TOOLS + ("firmware",):
        e = m.get(key)
        if not isinstance(e, dict):
            p.append(f"'{key}' fehlt")
            continue
        for f in ("url", "sha256"):
            if not isinstance(e.get(f), str) or not e[f]:
                p.append(f"'{key}.{f}' fehlt")
        if isinstance(e.get("sha256"), str) and not SHA_RE.match(e["sha256"]):
            p.append(f"'{key}.sha256' ist keine SHA256 (64 Hex-Zeichen, klein)")
        if isinstance(e.get("url"), str) and not e["url"].startswith("https://"):
            p.append(f"'{key}.url' muss https:// sein")
        if key in TOOLS and not e.get("version"):
            p.append(f"'{key}.version' fehlt")
    repos = m.get("repos")
    if not isinstance(repos, dict) or not repos:
        p.append("'repos' fehlt oder ist leer")
        return p
    templates = 0
    for name, r in repos.items():
        if not re.match(r"^[A-Za-z0-9_.-]+$", name):
            p.append(f"Repo-Name ungültig: {name!r}")
        for f in ("url", "ref", "workspace", "shortcut"):
            if not isinstance(r.get(f), str) or not r[f]:
                p.append(f"'repos.{name}.{f}' fehlt")
        if r.get("template_for_new_projects"):
            templates += 1
        for t in r.get("tool_shortcuts", []):
            for f in ("name", "script", "workdir"):
                if not t.get(f):
                    p.append(f"'repos.{name}.tool_shortcuts[].{f}' fehlt")
    if templates != 1:
        p.append(f"genau ein Repo braucht 'template_for_new_projects' (gefunden: {templates})")
    if "4diac_training1" not in repos:
        p.append("'repos.4diac_training1' fehlt (Bezug für die Firmware)")
    return p


def check_firmware_sync(m: dict, firmware_json: dict) -> list[str]:
    """Synchron-Prüfung (KONZEPT.md 2.7): Firmware und alle Repos auf demselben Tag."""
    p: list[str] = []
    t1 = m["repos"]["4diac_training1"]["ref"]
    if firmware_json.get("training1") != t1:
        p.append(f"firmware.json gehört zu {firmware_json.get('training1')!r}, "
                 f"4diac_training1 steht im Manifest auf {t1!r}")
    for name, r in m["repos"].items():
        if r["ref"] != t1:
            p.append(f"{name} steht auf {r['ref']!r}, nicht auf dem training1-Tag {t1!r}")
    if not isinstance(firmware_json.get("targets"), dict) or not firmware_json["targets"]:
        p.append("firmware.json enthält keine Targets")
    return p
