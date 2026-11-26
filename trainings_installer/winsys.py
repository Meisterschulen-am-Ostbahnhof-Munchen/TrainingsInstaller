"""Windows-spezifische Helfer: Benutzer-PATH, laufende IDE, Verknüpfungen.

Alles ohne Admin-Rechte und ohne Zusatzpakete (nur Standardbibliothek).
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    """subprocess.run ohne aufpoppendes Konsolenfenster (wichtig unter pythonw)."""
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("errors", "replace")
    kw.setdefault("stdin", subprocess.DEVNULL)   # nie auf Eingabe warten
    return subprocess.run(cmd, creationflags=CREATE_NO_WINDOW, **kw)


def powershell(script: str) -> subprocess.CompletedProcess:
    return run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                "-Command", script])


# --------------------------------------------------------------------------- PATH (2.2)

def merge_path(raw: str, add: list[str]) -> str:
    """Eigene Einträge voranstellen, alte Vorkommen entfernen, Rest unverändert lassen."""
    parts = [p.rstrip("\\") for p in raw.split(";") if p.strip()]
    lower_add = {a.lower() for a in add}
    rest = [p for p in parts if p.lower() not in lower_add]
    return ";".join(add + rest)


def remove_from_path(raw: str, remove: list[str]) -> str:
    lower = {r.lower() for r in remove}
    return ";".join(p for p in raw.split(";") if p.strip() and p.rstrip("\\").lower() not in lower)


def update_user_path(add: list[str]) -> bool:
    """Benutzer-PATH (HKCU\\Environment) roh lesen und als REG_EXPAND_SZ schreiben.

    Nicht setx (1024-Zeichen-Grenze) und nicht Environment.SetEnvironmentVariable
    (würde %VARIABLEN% expandieren). Gibt True zurück, wenn geändert wurde.
    """
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        try:
            raw, _typ = winreg.QueryValueEx(key, "Path")   # liefert den Rohwert
        except FileNotFoundError:
            raw = ""
        new = merge_path(raw, add)
        if new == raw:
            return False
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new)
    broadcast_environment_change()
    return True


def remove_user_path(remove: list[str]) -> bool:
    """Eigene Einträge aus dem Benutzer-PATH entfernen (Rohwert, REG_EXPAND_SZ)."""
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        try:
            raw, _typ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            return False
        new = remove_from_path(raw, remove)
        if new == raw:
            return False
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new)
    broadcast_environment_change()
    return True


def broadcast_environment_change() -> None:
    HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG = 0xFFFF, 0x1A, 0x2
    result = ctypes.c_size_t()
    ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
                                             SMTO_ABORTIFHUNG, 5000, ctypes.byref(result))


def prepend_process_path(add: list[str]) -> None:
    os.environ["PATH"] = merge_path(os.environ.get("PATH", ""), add)


def new_terminal_lookup(name: str) -> str | None:
    """Welches <name>.exe fände ein neu geöffnetes Terminal? (System-PATH vor Benutzer-PATH)"""
    import winreg

    def read(root, sub):
        try:
            with winreg.OpenKey(root, sub) as k:
                return winreg.QueryValueEx(k, "Path")[0]
        except OSError:
            return ""

    system = read(winreg.HKEY_LOCAL_MACHINE,
                  r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
    user = read(winreg.HKEY_CURRENT_USER, "Environment")
    for d in (system + ";" + user).split(";"):
        d = os.path.expandvars(d.strip())
        if d and (Path(d) / f"{name}.exe").is_file():
            return str(Path(d) / f"{name}.exe")
    return None


# ------------------------------------------------------------- IDE geöffnet? (2.5)

def running_ides(tools_dir: Path) -> list[dict]:
    """4diac-ide.exe-Prozesse, deren Programm unter tools_dir liegt."""
    if not IS_WINDOWS:
        return []
    r = powershell("Get-CimInstance Win32_Process -Filter \"Name='4diac-ide.exe'\" | "
                   "Select-Object ExecutablePath, CommandLine | ConvertTo-Json -Compress")
    if r.returncode != 0 or not r.stdout.strip():
        return []
    data = json.loads(r.stdout)
    procs = data if isinstance(data, list) else [data]
    prefix = str(tools_dir).lower().rstrip("\\") + "\\"
    return [p for p in procs if (p.get("ExecutablePath") or "").lower().startswith(prefix)]


def workspace_locked(workspace: Path) -> bool:
    """Hält eine IDE den Workspace? .lock allein sagt nichts – Bytebereich-Sperre versuchen."""
    lock = workspace / ".metadata" / ".lock"
    if not lock.is_file():
        return False
    try:
        import msvcrt
        with open(lock, "r+b") as f:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                return True
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            return False
    except PermissionError:
        return True


def ide_running(tools_dir: Path, workspaces: list[Path]) -> list[str]:
    """Liefert eine Beschreibung je Hinweis auf eine laufende IDE (leer = keine)."""
    hits = [f"4diac IDE läuft ({p.get('ExecutablePath')})" for p in running_ides(tools_dir)]
    hits += [f"Workspace geöffnet: {w}" for w in workspaces if workspace_locked(w)]
    return hits


# ----------------------------------------------------------- Verknüpfungen (2.5)

def desktop_dir() -> Path:
    """Echter Desktop-Ordner (bei OneDrive-Umleitung nicht %USERPROFILE%\\Desktop)."""
    buf = ctypes.create_unicode_buffer(260)
    CSIDL_DESKTOPDIRECTORY = 0x10
    if ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buf) == 0:
        return Path(buf.value)
    return Path(os.environ["USERPROFILE"]) / "Desktop"


def start_menu_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "4diac"


_SHORTCUT_PS = r"""
$items = Get-Content -Raw -Encoding UTF8 -LiteralPath $env:TI_SHORTCUTS | ConvertFrom-Json
$sh = New-Object -ComObject WScript.Shell
foreach ($i in $items) {
    New-Item -ItemType Directory -Force -Path (Split-Path $i.path) | Out-Null
    $l = $sh.CreateShortcut($i.path)
    $l.TargetPath = $i.target
    $l.Arguments = $i.args
    $l.WorkingDirectory = $i.workdir
    if ($i.icon) { $l.IconLocation = $i.icon }
    if ($i.description) { $l.Description = $i.description }
    $l.Save()
}
"""


def create_shortcuts(items: list[dict]) -> None:
    """items: path, target, args, workdir, icon?, description? – per WScript.Shell."""
    if not items:
        return
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
        tmp = f.name
    try:
        env = dict(os.environ, TI_SHORTCUTS=tmp)
        r = run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-Command", _SHORTCUT_PS], env=env)
        if r.returncode != 0:
            raise RuntimeError(f"Verknüpfungen anlegen fehlgeschlagen: {r.stderr.strip()}")
    finally:
        os.unlink(tmp)
