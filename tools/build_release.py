"""TrainingsInstaller.zip und Release-Notes bauen (KONZEPT.md 3.3).

Aufruf:  python tools/build_release.py [--tag vX.Y.Z] [--out dist]
  - prüft, dass der Tag zu version.txt passt (v + version.txt)
  - prüft manifest.json mit derselben Prüfung wie der Installer (die Freigabe-Prüfung
    tools/check_manifest.py --full läuft im Release-Workflow vorher)
  - schreibt dist/TrainingsInstaller.zip (Ordner TrainingsInstaller\\ mit genau den Dateien
    aus KONZEPT 3.3) und dist/RELEASE_NOTES.md
Exit 0 = gebaut, 1 = Fehler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trainings_installer import manifest as mf  # noqa: E402

ZIP_NAME = "TrainingsInstaller.zip"
TOP = "TrainingsInstaller"
FILES = ["install.cmd", "install.ps1", "manifest.json", "version.txt", "LIESMICH.txt"]
PACKAGE = "trainings_installer"
# feste Zeit im ZIP: gleicher Inhalt = gleiche Datei (reproduzierbar)
ZIP_TIME = (2020, 1, 1, 0, 0, 0)


def release_files(root: Path = ROOT) -> list[tuple[Path, str]]:
    """(Quelle, Pfad im ZIP) – nur die Dateien aus KONZEPT 3.3, ohne __pycache__."""
    out = [(root / f, f"{TOP}/{f}") for f in FILES]
    for p in sorted((root / PACKAGE).rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            out.append((p, f"{TOP}/{p.relative_to(root).as_posix()}"))
    return out


def build_zip(dest: Path, root: Path = ROOT) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for src, arc in release_files(root):
            if not src.is_file():
                raise FileNotFoundError(f"fehlt: {src}")
            info = zipfile.ZipInfo(arc, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, src.read_bytes())
    return hashlib.sha256(dest.read_bytes()).hexdigest()


def notes(m: dict, version: str, sha: str) -> str:
    fw = m["firmware"]
    t1 = m["repos"]["4diac_training1"]["ref"]
    lines = [
        f"## 4diac Trainings-Installer {version}",
        "",
        f"**Download:** `{ZIP_NAME}` → entpacken → `install.cmd` doppelklicken "
        "(Anleitung: `LIESMICH.txt` im ZIP).",
        "",
        "Fester Link auf die neueste Version:",
        "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/TrainingsInstaller/releases/latest/download/"
        + ZIP_NAME,
        "",
        "### Enthaltene Versionen (manifest.json)",
        "",
        "| Bestandteil | Version |",
        "|---|---|",
        f"| Git (portabel) | {m['git']['version']} |",
        f"| Python (embeddable) | {m['python']['version']} |",
        f"| 4diac IDE | {m['fordiac_ide']['version']} |",
        f"| Auto-Import-Plugin | {m['fordiac_autoimport']['version']} |",
        f"| logiBUS-Firmware | {t1}, Build `{fw.get('build', '?')}` |",
        "",
        "### Trainings-Repos",
        "",
        "| Repo | Tag | Verknüpfung |",
        "|---|---|---|",
    ]
    for name, e in m["repos"].items():
        lines.append(f"| {name} | {e['ref']} | {e.get('shortcut', '')} |")
    lines += [
        "",
        "Freigabe-Prüfung (`tools/check_manifest.py --full`) war grün.",
        "",
        f"SHA256 `{ZIP_NAME}`: `{sha}`",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="Git-Tag des Releases, muss v<version.txt> sein")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    a = ap.parse_args(argv)

    version = (ROOT / "version.txt").read_text(encoding="utf-8").strip()
    if a.tag and a.tag != f"v{version}":
        print(f"FEHLER: Tag {a.tag} passt nicht zu version.txt ({version}) – erwartet v{version}")
        return 1
    m = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    errors = mf.validate(m)
    if errors:
        print("FEHLER: manifest.json ungültig:\n  " + "\n  ".join(errors))
        return 1

    out = Path(a.out)
    sha = build_zip(out / ZIP_NAME)
    (out / "RELEASE_NOTES.md").write_text(notes(m, version, sha), encoding="utf-8")
    print(f"{out / ZIP_NAME}  SHA256 {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
