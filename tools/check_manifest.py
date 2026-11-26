"""Freigabe-Prüfung für manifest.json – PFLICHT vor jedem Installer-Release.

Ein Manifest darf nur veröffentlicht werden, wenn alle Tags stimmen (KONZEPT.md 2.7, 3.2):

  1. Aufbau gültig (gleiche Prüfung wie im Installer)
  2. Jedes Repo ist öffentlich erreichbar und hat den Tag aus dem Manifest
  3. Alle Repos stehen auf demselben Tag wie 4diac_training1
  4. Der Ordner <workspace>/.lib ist in jedem Repo identisch mit training1
     (gleicher Git-Tree-Hash am Tag = .lib-Sync ist durch)
  5. firmware.json: SHA256 stimmt, gehört zum training1-Tag, alle .bin-Assets vorhanden
  6. tool_shortcuts: Skript existiert im Tag
  7. Werkzeuge (Git, Python, IDE, Plugin): URL erreichbar; Plugin-SHA256 geprüft
     (mit --full werden auch Git, Python und IDE geladen und geprüft, ca. 410 MB)

Aufruf:  python tools/check_manifest.py [manifest.json] [--full]
Exit 0 = freigegeben, 1 = NICHT freigeben.
Optional GITHUB_TOKEN setzen (höheres API-Limit, z. B. in CI).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trainings_installer import manifest as mf  # noqa: E402

UA = {"User-Agent": "TrainingsInstaller-check"}


def http(url: str, method: str = "GET", api: bool = False) -> urllib.request.addinfourl:
    headers = dict(UA)
    token = os.environ.get("GITHUB_TOKEN")
    if api and token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers, method=method), timeout=60)


def sha256_url(url: str) -> tuple[str, bytes | None]:
    h = hashlib.sha256()
    keep = bytearray()
    with http(url) as r:
        while block := r.read(1 << 20):
            h.update(block)
            if len(keep) < 1 << 20:
                keep += block
    return h.hexdigest(), bytes(keep)


def gh_repo(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return path[:-4] if path.endswith(".git") else path


def ls_remote_tag(url: str, tag: str) -> bool:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = subprocess.run(["git", "-c", "credential.helper=", "ls-remote", "--tags", url, f"refs/tags/{tag}"],
                       capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "git ls-remote fehlgeschlagen")
    return bool(r.stdout.strip())


def lib_content(repo: str, workspace: str, tag: str) -> dict[str, str] | None:
    """Alle Dateien unter <workspace>/.lib als {Pfad: Blob-SHA}.

    Verglichen wird der Inhalt, nicht der Tree-Hash: Der würde sich schon durch ein
    anderes Ausführungsbit (100755/100644) ändern, obwohl die ELFs identisch sind.
    """
    with http(f"https://api.github.com/repos/{repo}/contents/{workspace}?ref={tag}", api=True) as r:
        entries = json.load(r)
    sha = next((e["sha"] for e in entries if e["name"] == ".lib" and e["type"] == "dir"), None)
    if not sha:
        return None
    with http(f"https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1", api=True) as r:
        tree = json.load(r)
    if tree.get("truncated"):
        raise RuntimeError(f"{repo}: .lib zu groß für die GitHub-API (truncated)")
    return {e["path"]: e["sha"] for e in tree["tree"] if e["type"] == "blob"}


def exists_in_tag(repo: str, tag: str, path: str) -> bool:
    try:
        with http(f"https://raw.githubusercontent.com/{repo}/{tag}/{path}", method="HEAD"):
            return True
    except urllib.error.HTTPError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", nargs="?", default=str(ROOT / "manifest.json"))
    ap.add_argument("--full", action="store_true", help="auch Git, Python, IDE laden und SHA256 prüfen")
    args = ap.parse_args()

    errors: list[str] = []
    ok = lambda msg: print(f"  ok    {msg}")  # noqa: E731

    def fail(msg: str) -> None:
        errors.append(msg)
        print(f"  FEHLT {msg}")

    m = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    print("1. Aufbau")
    for p in mf.validate(m):
        fail(p)
    if errors:
        return report(errors)
    ok("manifest.json gültig")

    t1 = m["repos"]["4diac_training1"]["ref"]
    print(f"2./3. Tags (alle müssen {t1} sein)")
    for name, e in m["repos"].items():
        if e["ref"] != t1:
            fail(f"{name}: steht auf {e['ref']}, nicht auf {t1}")
            continue
        try:
            if ls_remote_tag(e["url"], e["ref"]):
                ok(f"{name}: Tag {e['ref']} vorhanden (öffentlich erreichbar)")
            else:
                fail(f"{name}: Tag {e['ref']} fehlt – .lib-Sync-PR gemergt und getaggt?")
        except (RuntimeError, subprocess.TimeoutExpired) as ex:
            fail(f"{name}: nicht erreichbar ohne Login ({ex})")

    print(f"4. .lib identisch mit 4diac_training1 @ {t1}")
    ref_repo = m["repos"]["4diac_training1"]
    try:
        ref_lib = lib_content(gh_repo(ref_repo["url"]), ref_repo["workspace"], t1)
        if not ref_lib:
            fail("4diac_training1: kein .lib im Workspace")
        for name, e in m["repos"].items():
            if name == "4diac_training1" or not ref_lib or e["ref"] != t1:
                continue
            try:
                lib = lib_content(gh_repo(e["url"]), e["workspace"], e["ref"])
            except urllib.error.HTTPError as ex:
                fail(f"{name}: Workspace nicht lesbar ({ex.code})")
                continue
            if lib is None:
                fail(f"{name}: kein .lib im Workspace")
                continue
            diff = sorted(p for p in set(ref_lib) | set(lib) if ref_lib.get(p) != lib.get(p))
            if not diff:
                ok(f"{name}: .lib = training1 ({len(lib)} Dateien)")
            else:
                fail(f"{name}: .lib weicht in {len(diff)} Datei(en) von training1 ab, z. B. {diff[0]}")
    except (urllib.error.HTTPError, RuntimeError) as ex:
        fail(f".lib-Vergleich nicht möglich: {ex} (GITHUB_TOKEN setzen?)")

    print("5. Firmware")
    fw = m["firmware"]
    try:
        sha, body = sha256_url(fw["url"])
        if sha != fw["sha256"]:
            fail(f"firmware.json SHA256 {sha[:12]}… ≠ Manifest {fw['sha256'][:12]}…")
        else:
            ok("firmware.json SHA256")
            data = json.loads(body)
            for p in mf.check_firmware_sync(m, data):
                fail(p)
            if data.get("build") != fw.get("build"):
                fail(f"Build in firmware.json {data.get('build')} ≠ Manifest {fw.get('build')}")
            base = fw["url"].rsplit("/", 1)[0]
            missing = []
            for target, t in data["targets"].items():
                for kind in ("application", "merged_flash"):
                    if kind in t:
                        try:
                            with http(f"{base}/{t[kind]['file']}", method="HEAD"):
                                pass
                        except urllib.error.HTTPError:
                            missing.append(t[kind]["file"])
            if missing:
                fail(f"Firmware-Dateien fehlen am Release: {', '.join(missing)}")
            else:
                ok(f"Build {data.get('build')}, {len(data['targets'])} Targets, alle .bin vorhanden")
    except (urllib.error.URLError, ValueError) as ex:
        fail(f"firmware.json nicht ladbar: {ex}")

    print("6. tool_shortcuts")
    for name, e in m["repos"].items():
        for t in e.get("tool_shortcuts", []):
            if exists_in_tag(gh_repo(e["url"]), e["ref"], t["script"]):
                ok(f"{name}: {t['script']}")
            else:
                fail(f"{name}: {t['script']} fehlt im Tag {e['ref']}")

    print("7. Werkzeuge")
    for key in mf.TOOLS:
        e = m[key]
        try:
            if args.full or key == "fordiac_autoimport":
                sha, _ = sha256_url(e["url"])
                (ok if sha == e["sha256"] else fail)(f"{key} {e['version']}: SHA256"
                                                     + ("" if sha == e["sha256"] else f" {sha[:12]}… ≠ Manifest"))
            else:
                with http(e["url"], method="HEAD"):
                    ok(f"{key} {e['version']}: erreichbar (SHA256 nur mit --full)")
        except urllib.error.URLError as ex:
            fail(f"{key}: {e['url']} nicht erreichbar ({ex})")

    return report(errors)


def report(errors: list[str]) -> int:
    print()
    if errors:
        print(f"NICHT FREIGEBEN – {len(errors)} Problem(e):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("FREIGEGEBEN – alle Tags und Prüfsummen stimmen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
