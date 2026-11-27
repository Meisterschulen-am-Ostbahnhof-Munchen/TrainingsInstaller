"""Grafische Oberfläche mit tkinter (KONZEPT.md 3.1).

Der Kern läuft in einem eigenen Thread; Meldungen kommen über eine Queue, damit das
Fenster während der Downloads nicht einfriert.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from . import core
from .paths import Paths
from .report import Reporter, setup_logging

COLORS = {"error": "#b00020", "warning": "#8a5300", "done": "#1b5e20", "step": "#0d47a1"}


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.q: queue.Queue = queue.Queue()
        self.paths = Paths.default()
        self.paths.ensure()
        self.logfile = setup_logging(self.paths.logs, console=False)
        self.worker: threading.Thread | None = None
        self.done_text = ""

        root.title("4diac Trainings-Installer")
        root.geometry("760x520")
        root.minsize(560, 380)

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="4diac Trainings-Installer", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(top, text=f"Version {core.installer_version()} – alles unter {self.paths.root}"
                  ).pack(anchor="w")

        bar = ttk.Frame(root, padding=(10, 0))
        bar.pack(fill="x")
        self.buttons = [
            ttk.Button(bar, text="Installieren / Reparieren", command=lambda: self.start(core.install)),
            ttk.Button(bar, text="Trainings aktualisieren", command=self.ask_update),
            ttk.Button(bar, text="Neues Projekt", command=self.ask_new_project),
            ttk.Button(bar, text="Aufräumen", command=self.ask_cleanup),
            ttk.Button(bar, text="Prüfen", command=lambda: self.start(core.check)),
            ttk.Button(bar, text="Deinstallieren", command=self.ask_uninstall),
        ]
        for b in self.buttons:
            b.pack(side="left", padx=(0, 6))

        self.progress = ttk.Progressbar(root, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=8)

        frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        frame.pack(fill="both", expand=True)
        self.text = tk.Text(frame, wrap="word", state="disabled", font=("Consolas", 9))
        scroll = ttk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        for tag, color in COLORS.items():
            self.text.tag_configure(tag, foreground=color)

        self.write("info", f"Log: {self.logfile}")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self.poll)
        threading.Thread(target=self.check_self_update, daemon=True).start()

    def check_self_update(self) -> None:
        """Im Hintergrund: offline oder Fehler → einfach weiter (KONZEPT.md 3.3)."""
        from . import selfupdate
        rel = selfupdate.newer_release(core.installer_version())
        if rel:
            self.q.put(("update", rel))

    def offer_self_update(self, rel) -> None:
        from . import selfupdate
        if self.worker and self.worker.is_alive():
            self.write("warning", f"Neue Installer-Version {rel.version} verfügbar – "
                                  "nach diesem Lauf den Installer neu starten")
            return
        if not messagebox.askyesno(
                "Neue Version",
                f"Neue Version {rel.version} des Trainings-Installers verfügbar "
                f"(installiert: {core.installer_version()}).\n\nJetzt aktualisieren?\n\n"
                "Der Installer startet danach neu. Deine Projekte werden dabei nicht verändert."):
            self.write("info", f"Neue Installer-Version {rel.version} nicht installiert")
            return
        self.start(lambda rep, paths: selfupdate.self_update(rep, paths, rel), kind="self_update")

    def write(self, level: str, msg: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", msg + "\n", level)
        self.text.see("end")
        self.text.configure(state="disabled")

    def ask_uninstall(self) -> None:
        from . import uninstall
        if self.worker and self.worker.is_alive():
            return
        if not messagebox.askyesno(
                "Deinstallieren",
                f"Alles unter {self.paths.root} entfernen – Git, Python, 4diac IDE, Firmware, "
                "Verknüpfungen und PATH-Einträge?", icon="warning"):
            return
        work = uninstall.student_work(self.paths, core.load_manifest())
        remove_projects = None   # nichts gefunden: der Lauf prüft unmittelbar davor noch einmal
        if work:
            shown = "\n".join(work[:15]) + (f"\n… und {len(work) - 15} weitere" if len(work) > 15 else "")
            answer = messagebox.askyesnocancel(
                "Projekte behalten?",
                f"In {self.paths.prj} liegt Schülerarbeit:\n\n{shown}\n\n"
                "Ja = Projekte behalten (empfohlen)\n"
                "Nein = auch alle Projekte endgültig löschen\n"
                "Abbrechen = nichts deinstallieren", icon="warning")
            if answer is None:
                return
            remove_projects = not answer
        self.start(lambda rep, paths: uninstall.uninstall(rep, paths, remove_projects),
                   done_text="Deinstalliert. Das Fenster wird jetzt geschlossen."
                   + ("" if remove_projects is not False else f"\n\nDie Projekte liegen weiter in {self.paths.prj}."),
                   kind="uninstall")

    def ask_cleanup(self) -> None:
        from . import cleanup
        if self.worker and self.worker.is_alive():
            return
        files = cleanup.plan(self.paths, core.load_manifest(), keep_log=self.logfile)
        if not files:
            messagebox.showinfo("Aufräumen", "Nichts aufzuräumen: keine alten Downloads und keine "
                                f"Logs älter als {cleanup.LOG_DAYS} Tage.")
            return
        lines = cleanup.describe(self.paths, files)
        shown = "\n".join(lines[:20]) + (f"\n… und {len(lines) - 20} weitere" if len(lines) > 20 else "")
        if messagebox.askyesno(
                "Aufräumen",
                f"Zu löschen ({cleanup.count(len(files))}):\n\n{shown}\n\n"
                "Projekte, Sicherungs-Branches und _sicherung_-Dateien bleiben erhalten.\n\n"
                "Löschen?", icon="warning"):
            self.start(lambda rep, paths: cleanup.cleanup(rep, paths, files),
                       done_text="Aufgeräumt.")

    def ask_update(self) -> None:
        if messagebox.askokcancel(
                "Trainings aktualisieren",
                "Bitte vorher die 4diac IDE schließen.\n\n"
                "Alle Trainings werden auf den aktuellen Stand gebracht. Deine geänderten Übungen "
                "(.SUB) bleiben als „…_sicherung_<Datum>.SUB“ daneben erhalten.\n\n"
                "Eigene Projekte (aus „Neues Projekt“) bekommen den neuen Stand der Vorlage; "
                "deine Dateien darin bleiben, vorher wird ein Sicherungs-Branch angelegt."):
            from . import update
            self.start(update.update)

    def ask_new_project(self) -> None:
        from . import new_project
        name = ""
        while True:
            name = simpledialog.askstring(
                "Neues Projekt",
                "Name des neuen Projekts (nur A–Z, 0–9, _ und -, z. B. Maehwerk):",
                initialvalue=name, parent=self.root)
            if name is None:
                return
            name = name.strip()
            err = new_project.check_name(name, self.paths, core.load_manifest())
            if not err:
                break
            messagebox.showerror("Neues Projekt", err)
        self.start(lambda rep, paths: new_project.new_project(rep, paths, name),
                   done_text="Fertig.\n\nDas Projekt startest du mit der Verknüpfung "
                             f"„4diac – {name}“ auf dem Desktop.")

    def start(self, fn, done_text: str = "", kind: str = "") -> None:
        """kind kommt mit der Fertig-Meldung zurück – Neustart/Schließen gilt nur für genau diesen Lauf."""
        if self.worker and self.worker.is_alive():
            return
        self.done_text = done_text
        for b in self.buttons:
            b.configure(state="disabled")
        self.progress.configure(value=0)
        rep = Reporter(on_message=lambda lvl, m: self.q.put(("msg", lvl, m)),
                       on_progress=lambda d, t: self.q.put(("progress", d, t)))

        def run() -> None:
            try:
                ok = fn(rep, self.paths)
            except Exception as e:   # noqa: BLE001 – alles anzeigen, nichts verschlucken
                rep.error(f"Unerwarteter Fehler: {e}")
                ok = False
            self.q.put(("finished", ok, rep.report.text(), kind))

        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def poll(self) -> None:
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "msg":
                    self.write(item[1], item[2])
                elif item[0] == "progress":
                    done, total = item[1], item[2]
                    if total:
                        self.progress.configure(maximum=total, value=done)
                elif item[0] == "update":
                    self.offer_self_update(item[1])
                elif item[0] == "finished":
                    self.finished(item[1], item[2], item[3])
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def finished(self, ok: bool, summary: str, kind: str = "") -> None:
        for b in self.buttons:
            b.configure(state="normal")
        self.write("step", "\n" + summary)
        if kind == "self_update":
            if ok:
                from . import selfupdate
                messagebox.showinfo("Fertig", "Die neue Version ist geladen. Der Installer startet "
                                    "jetzt neu.\n\nDanach bitte „Installieren / Reparieren“ wählen, "
                                    "damit auch die Trainings den neuen Stand bekommen.")
                selfupdate.restart(self.paths)   # wartet, bis dieses Fenster zu ist
                self.root.destroy()
                return
        if ok:
            messagebox.showinfo("Fertig", self.done_text
                                or "Fertig.\n\nDie 4diac-Verknüpfungen liegen auf dem Desktop.")
        else:
            messagebox.showerror("Fehler", f"Es gab Fehler – Details oben und im Log:\n{self.logfile}")
        if kind == "uninstall":
            if ok:   # Installer wird nach dem Beenden entfernt – Fenster schließen
                self.root.destroy()

    def on_close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("Abbrechen?", "Der Installer arbeitet noch. Trotzdem schließen?"):
                return
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0
