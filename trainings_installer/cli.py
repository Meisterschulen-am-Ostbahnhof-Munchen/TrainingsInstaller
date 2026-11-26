"""Konsole / headless (KONZEPT.md 3.1, 5)."""
from __future__ import annotations

import argparse
import sys

from . import core
from .paths import Paths
from .report import Reporter, setup_logging

COMING = ("update", "new_project", "cleanup", "uninstall", "self_update")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="install.cmd",
                                description="4diac Trainings-Installer (C:\\ms\\sl)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--headless", action="store_true",
                   help="installieren bzw. nachinstallieren, ohne Fenster")
    g.add_argument("--check", action="store_true", help="nur prüfen, nichts verändern")
    g.add_argument("--update", nargs="?", const="*", metavar="REPO",
                   help="Trainings aktualisieren (folgt)")
    g.add_argument("--new-project", metavar="NAME", help="neues eigenes Projekt (folgt)")
    g.add_argument("--cleanup", action="store_true", help="alte Logs löschen (folgt)")
    g.add_argument("--uninstall", action="store_true", help="alles entfernen (folgt)")
    g.add_argument("--self-update", action="store_true", help="Installer aktualisieren (folgt)")
    g.add_argument("--gui", action="store_true", help="grafische Oberfläche")
    return p


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.gui:
        from . import gui
        return gui.main()
    for name in COMING:
        if getattr(args, name):
            print(f"--{name.replace('_', '-')} ist noch nicht verfügbar.")
            return 2
    paths = Paths.default()
    paths.ensure()
    logfile = setup_logging(paths.logs, console=True)
    rep = Reporter()
    ok = core.check(rep, paths) if args.check else core.install(rep, paths)
    print()
    print(rep.report.text())
    print(f"\nLog: {logfile}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
