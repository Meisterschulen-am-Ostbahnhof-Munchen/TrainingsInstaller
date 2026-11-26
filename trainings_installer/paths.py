"""Verzeichnisstruktur unter C:\\ms\\sl (KONZEPT.md 3.4)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = r"C:\ms\sl"


@dataclass(frozen=True)
class Paths:
    root: Path

    @classmethod
    def default(cls) -> "Paths":
        # MS_SL_ROOT nur für Tests; im Betrieb immer C:\ms\sl
        return cls(Path(os.environ.get("MS_SL_ROOT", DEFAULT_ROOT)))

    @property
    def tools(self) -> Path:
        return self.root / "tools"

    @property
    def git(self) -> Path:
        return self.tools / "git"

    @property
    def git_exe(self) -> Path:
        return self.git / "cmd" / "git.exe"

    @property
    def python(self) -> Path:
        return self.tools / "python"

    @property
    def ide(self) -> Path:
        return self.tools / "4diac-ide"

    @property
    def ide_exe(self) -> Path:
        return self.ide / "4diac-ide.exe"

    @property
    def ide_customization(self) -> Path:
        return self.ide / "ms-sl-customization.ini"

    @property
    def prj(self) -> Path:
        return self.root / "prj"

    @property
    def firmware(self) -> Path:
        return self.root / "firmware"

    @property
    def downloads(self) -> Path:
        return self.root / "downloads"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def installer(self) -> Path:
        return self.root / "installer"

    @property
    def shortcuts_json(self) -> Path:
        return self.root / "shortcuts.json"

    def ensure(self) -> None:
        for p in (self.root, self.tools, self.prj, self.downloads, self.logs):
            p.mkdir(parents=True, exist_ok=True)
