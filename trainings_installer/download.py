"""Download mit SHA256-Prüfung (KONZEPT.md 2, „Download-Verfahren“).

Erst nach <datei>.tmp laden, prüfen, dann umbenennen. Liegt die Datei schon mit
korrekter SHA256 vor, wird nicht erneut geladen.
"""
from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path
from typing import Callable

CHUNK = 1024 * 1024
USER_AGENT = "TrainingsInstaller"


class DownloadError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url: str, dest: Path, sha256: str,
          progress: Callable[[int, int], None] | None = None) -> bool:
    """Lädt url nach dest. Gibt False zurück, wenn dest schon passte (Cache)."""
    sha256 = sha256.lower()
    if dest.is_file() and sha256_file(dest) == sha256:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    h = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while block := r.read(CHUNK):
                f.write(block)
                h.update(block)
                done += len(block)
                if progress:
                    progress(done, total)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"Download fehlgeschlagen: {url}: {e}") from e
    if h.hexdigest() != sha256:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"SHA256 stimmt nicht: {dest.name} "
                            f"(erwartet {sha256[:12]}…, erhalten {h.hexdigest()[:12]}…)")
    os.replace(tmp, dest)
    return True
