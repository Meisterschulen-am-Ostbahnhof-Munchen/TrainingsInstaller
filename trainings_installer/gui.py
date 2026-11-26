"""Grafische Oberfläche mit tkinter (KONZEPT.md 3.1).

Der Kern läuft in einem eigenen Thread; Meldungen kommen über eine Queue, damit das
Fenster während der Downloads nicht einfriert.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

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
            ttk.Button(bar, text="Prüfen", command=lambda: self.start(core.check)),
        ]
        for b in self.buttons:
            b.pack(side="left", padx=(0, 6))
        for text in ("Trainings aktualisieren", "Neues Projekt", "Aufräumen", "Deinstallieren"):
            ttk.Button(bar, text=text, state="disabled").pack(side="left", padx=(0, 6))

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

    def write(self, level: str, msg: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", msg + "\n", level)
        self.text.see("end")
        self.text.configure(state="disabled")

    def start(self, fn) -> None:
        if self.worker and self.worker.is_alive():
            return
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
            self.q.put(("finished", ok, rep.report.text()))

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
                elif item[0] == "finished":
                    self.finished(item[1], item[2])
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def finished(self, ok: bool, summary: str) -> None:
        for b in self.buttons:
            b.configure(state="normal")
        self.write("step", "\n" + summary)
        if ok:
            messagebox.showinfo("Fertig", "Fertig.\n\nDie 4diac-Verknüpfungen liegen auf dem Desktop.")
        else:
            messagebox.showerror("Fehler", f"Es gab Fehler – Details oben und im Log:\n{self.logfile}")

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
