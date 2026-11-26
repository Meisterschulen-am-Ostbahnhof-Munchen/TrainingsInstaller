"""Fortschritt und Abschlussbericht.

Der Kern meldet alles über ein Reporter-Objekt; GUI und Konsole hängen sich mit
Rückruf-Funktionen dran (KONZEPT.md 3.1). Alles landet zusätzlich im Log.
"""
from __future__ import annotations

import datetime as _dt
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

log = logging.getLogger("trainings_installer")


def setup_logging(logs_dir: Path, console: bool) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = logs_dir / f"install_{stamp}.log"
    log.setLevel(logging.DEBUG)
    log.handlers.clear()
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
    log.addHandler(fh)
    if console:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(ch)
    return logfile


@dataclass
class Report:
    done: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def text(self) -> str:
        lines = []
        for title, items in (("Erledigt", self.done), ("Unverändert", self.skipped),
                             ("Hinweise", self.warnings), ("FEHLER", self.errors)):
            if items:
                lines.append(f"{title}:")
                lines += [f"  - {i}" for i in items]
        if not lines:
            lines.append("Nichts zu tun.")
        return "\n".join(lines)


class Reporter:
    """Sammelt den Bericht und leitet Meldungen an die Oberfläche weiter."""

    def __init__(self,
                 on_message: Callable[[str, str], None] | None = None,
                 on_progress: Callable[[int, int], None] | None = None) -> None:
        self.report = Report()
        self._on_message = on_message
        self._on_progress = on_progress

    def _emit(self, level: str, msg: str) -> None:
        getattr(log, {"step": "info", "done": "info", "skip": "info"}.get(level, level))(msg)
        if self._on_message:
            self._on_message(level, msg)

    def step(self, msg: str) -> None:
        self._emit("step", f"== {msg}")

    def info(self, msg: str) -> None:
        self._emit("info", msg)

    def done(self, msg: str) -> None:
        self.report.done.append(msg)
        self._emit("done", f"OK: {msg}")

    def skip(self, msg: str) -> None:
        self.report.skipped.append(msg)
        self._emit("skip", f"unverändert: {msg}")

    def warn(self, msg: str) -> None:
        self.report.warnings.append(msg)
        self._emit("warning", f"Hinweis: {msg}")

    def error(self, msg: str) -> None:
        self.report.errors.append(msg)
        self._emit("error", f"FEHLER: {msg}")

    def progress(self, done: int, total: int) -> None:
        if self._on_progress:
            self._on_progress(done, total)
