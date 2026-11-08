# Konzept: TrainingsInstaller

> Status: **Entwurf** – Stand 2026-11-08
> Punkte mit **❓** sind noch offen und müssen gemeinsam entschieden werden.

## 1. Ziel

Ein Teilnehmer-PC soll mit **einem einzigen Aufruf** in einen schulungsbereiten Zustand
gebracht werden – reproduzierbar, ohne manuelles Zusammensuchen von Downloads.

Alles wird im festen Basisordner **`C:\ms\sl`** abgelegt. Der Installer legt diesen
Ordner an, falls er noch nicht existiert.

Installiert bzw. eingerichtet werden:

| Komponente     | Zweck                                         | Version          |
|----------------|-----------------------------------------------|------------------|
| Git            | Repos klonen, Übungsstände wechseln           | ❓ fest / latest |
| Python         | Hilfsskripte, Generatoren                     | ❓ z. B. 3.12.x  |
| Eclipse 4diac IDE | Entwicklungsumgebung für IEC 61499         | **3.4.0 Milestone 2026-11-05_2214** (siehe 2.1) |
| 4diac FORTE    | Laufzeitumgebung (lokal zum Testen)           | ❓ nötig?        |
| `training1`    | Übungs-Repository der Schulung                | Branch/Tag ❓    |
| weitere …      | ❓ (z. B. VS Code, Wireshark, CAN-Treiber)    |                  |

## 2. Rahmenbedingungen

- **Zielgeräte:** **Persönliche Notebooks** an den
  [Meisterschulen am Ostbahnhof](https://www.meisterschulen-muenchen.de/Landmaschinenmechanik_10_0.html).
  **Ein Gerät = eine Person = ein Windows-Login.** Gemeinsam genutzte PCs gibt es nicht.

  | Gerät              | Beschaffung | Admin-Rechte |
  |--------------------|-------------|--------------|
  | Schüler-Notebook   | privat      | **ja** (Pflicht laut Schulvorgabe) |
  | Lehrer-Notebook    | ❓ dienstlich/verwaltet | **nein** |

  Grundlage für Schüler-Notebooks: [Notebookanforderungen der Schule](https://www.meisterschulen-muenchen.de/documents/meisterschulen/fachbereiche/it-admin/beiblatt_notebookanforderung.pdf)
  (Stand 16.07.2024):
  - Windows 10/11 (Pro) 64-Bit, Intel/AMD x64; „Windows 10 S“, Windows ≤ 8.1 nicht zulässig
  - macOS/Linux und ARM-Geräte (z. B. Macbooks mit M-Prozessor) sind an der Schule
    **nicht zugelassen**
- **Zielplattform:** daraus folgt **Windows only (Windows 10/11 x64)**. macOS/Linux
  werden nicht unterstützt.
- **Rechte:** **Der Installer muss ohne Administratorrechte laufen**, weil Lehrkräfte
  keine haben. Auch auf Schüler-Notebooks wird Admin bewusst nicht verwendet (keine
  UAC-Abfrage, ein einheitlicher Weg für alle Geräte). Alle Werkzeuge werden portabel
  bzw. als Benutzer-Installation nach `C:\ms\sl` gelegt.
- **Basisordner:** `C:\ms\sl` (fest vorgegeben). Ohne Admin lässt sich ein Ordner direkt
  unter `C:\` anlegen – **auf einem Lehrer-Notebook ohne Admin-Rechte getestet
  (2026-11-08): funktioniert.** Der Installer prüft trotzdem vorab, ob er in `C:\ms\sl`
  schreiben darf, und bricht sonst mit klarer Meldung ab.
  Da jedes Gerät nur einen Benutzer hat, sind die geerbten Schreibrechte auf `C:\ms\sl`
  unkritisch.
- **Netzwerk:** **Während der Installation wird Internet vorausgesetzt.** Ein Offline-Paket
  ist nicht vorgesehen. In der Schulung selbst ist nicht immer Internet da – nach der
  Installation muss daher **alles offline funktionieren** (keine Nachladungen beim
  ersten Start, Repos vollständig geklont, keine Online-Update-Site als Pflicht).
- **Wiederholbarkeit:** Der Installer muss mehrfach ausführbar sein (idempotent) –
  bereits installierte Komponenten in der richtigen Version werden übersprungen.
- **Lizenz:** EPL-2.0 (siehe `LICENSE`).

### 2.1 Quelle der 4diac IDE

Verwendet wird der **Milestone-Build 3.4.0 vom 2026-11-05 22:14**, bereitgestellt als
GitHub Release im Repo
[`4diac-ide-release-history-milestone`](https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-ide-release-history-milestone):

Release: <https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-ide-release-history-milestone/releases/tag/4diac-ide_3.4.0_milestone_2026-11-05_2214>

| Plattform            | Datei                                                                    | Größe   |
|----------------------|--------------------------------------------------------------------------|---------|
| **Windows x64**      | `4diac-ide_3.4.0-win32.win32.x86_64_milestone_2026-11-05_2214.zip`       | 311 MB  |
| Linux x64            | `4diac-ide_3.4.0-linux.gtk.x86_64_milestone_2026-11-05_2214.tar.gz`      | 311 MB  |
| macOS Apple Silicon  | `4diac-ide_3.4.0-macosx.cocoa.aarch64_milestone_2026-11-05_2214.dmg`     | 307 MB  |
| macOS Intel          | `4diac-ide_3.4.0-macosx.cocoa.x86_64_milestone_2026-11-05_2214.dmg`      | 308 MB  |

(Für macOS gibt es zusätzlich `.tar.gz`-Varianten; Prüfsummen in `SHA256SUMS.txt` am Release.)

Windows-ZIP:
- URL: <https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-ide-release-history-milestone/releases/download/4diac-ide_3.4.0_milestone_2026-11-05_2214/4diac-ide_3.4.0-win32.win32.x86_64_milestone_2026-11-05_2214.zip>
- SHA256: `e6f821ddeb60cb06258292c76a80a36eaf456d6f31f7c679d899ca00b56269c9`

Installation unter Windows: ZIP nach `C:\ms\sl\tools\4diac-ide\` entpacken – kein Setup,
keine Admin-Rechte nötig.

**Release-Repos**

Pro Channel gibt es ein eigenes Repo (`4diac-ide-release-history-milestone`, `-nightly`,
`-rc`, `-latest`); befüllt werden sie vom Nightly-Download-Script. Der Installer nutzt
nur `-milestone`.

- Tag-Schema: Dateiname ohne Plattform und Endung →
  `4diac-ide_<version>_<channel>_<YYYY-MM-DD>_<HHMM>`, offizielle Releases `4diac-ide_<version>`.
- URL-Schema:
  `https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-ide-release-history-<channel>/releases/download/<tag>/<dateiname>`

Getrennt vom Installer-Repo, weil:
- Installer-Code und große Binärdateien unabhängig voneinander versioniert werden,
- die Repos auch von anderen Stellen (andere Kurse, Doku, manuelle Downloads) genutzt werden können,
- dort die Historie aller IDE-Stände an einem Ort liegt.

Warum GitHub Releases:
- Feste, öffentliche URL, kein Login nötig – ein einfaches `Invoke-WebRequest` genügt.
- Limit 2 GB pro Datei (wir haben 311 MB), kein Download-Kontingent für öffentliche Repos.
- Versionen liegen nachvollziehbar nebeneinander; das Manifest verweist auf Tag + SHA256.
- Lizenz: 4diac steht unter EPL-2.0, Weitergabe der Binärdateien ist erlaubt
  (Lizenzdateien sind im ZIP enthalten).

### 2.2 PATH ohne Admin

Geht: Windows hat neben dem System-PATH (`HKLM`, braucht Admin) einen **Benutzer-PATH**
(`HKCU\Environment`), den jeder Benutzer selbst ändern darf. Windows hängt beide zusammen.

```powershell
$add   = @('C:\ms\sl\tools\git\cmd', 'C:\ms\sl\tools\python', 'C:\ms\sl\tools\python\Scripts')
$path  = [Environment]::GetEnvironmentVariable('Path', 'User')       # kann $null sein
$parts = @($path -split ';' | Where-Object { $_.Trim() } | ForEach-Object { $_.TrimEnd('\') })
foreach ($p in $add) { if ($parts -notcontains $p) { $parts += $p } }  # -notcontains: ohne Groß/klein
[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')
# SetEnvironmentVariable(..., 'User') sendet WM_SETTINGCHANGE selbst – kein eigener Win32-Aufruf nötig.
```

Regeln:
- **Nicht `setx` verwenden** – schneidet bei 1024 Zeichen ab und zerstört so den PATH.
- Nur **eigene Einträge ergänzen/entfernen**, nie den ganzen PATH überschreiben
  (idempotent: Eintrag nur hinzufügen, wenn noch nicht vorhanden).
- Wirkt erst in **neu geöffneten** Terminals/Programmen; bereits offene Fenster sehen
  die Änderung nicht. Der Installer stellt die eigenen Pfade zusätzlich im eigenen
  Prozess **voran** (`$env:Path = "<eigene Pfade>;$env:Path"`), damit die folgenden
  Schritte sofort und garantiert mit den eigenen Werkzeugen laufen.
- `--uninstall` entfernt genau diese Einträge wieder.
- Benutzer-PATH steht **hinter** dem System-PATH: Ist z. B. schon ein anderes Python
  systemweit installiert, gewinnt dieses in neuen Terminals. Der Installer selbst ist
  davon nicht betroffen (Pfade im eigenen Prozess vorangestellt). Am Ende prüft er mit
  `Get-Command git, python`, welche Programme in einem neuen Terminal gefunden würden,
  und **warnt im Abschlussbericht**, falls dort fremde Versionen gewinnen.

Ohne Admin machbar je Komponente:
- **Git:** PortableGit (selbstentpackendes Archiv) nach `C:\ms\sl\tools\git`.
- **Python:** offizieller Installer mit
  `/quiet InstallAllUsers=0 TargetDir=C:\ms\sl\tools\python PrependPath=0 Include_launcher=0`
  (PATH setzen wir selbst, s. o.). Bewusst der **vollständige Installer** und nicht das
  „embeddable package“: Dieses enthält weder `pip` noch `venv`, beides wird in der
  Schulung gebraucht. Die benötigte Laufzeit (UCRT) ist seit Windows 10 Bestandteil
  von Windows.
- **4diac IDE:** ZIP entpacken, braucht keinen PATH-Eintrag; Verknüpfung genügt.

## 3. Architektur (Vorschlag)

### 3.1 Henne-Ei-Problem

Python soll installiert werden, kann also nicht Voraussetzung für den Installer sein.
Daher zweistufig:

1. **Bootstrap** – `install.ps1` (PowerShell, auf jedem Windows vorhanden)
   - prüft Umgebung, legt Basisverzeichnis an
   - installiert Git und Python
2. **Hauptinstaller** – Python-Skript (`trainings_installer/`)
   - liest Manifest, installiert restliche Komponenten, klont Repos, richtet Workspace ein

❓ Alternative: alles in PowerShell, oder Verwendung von `winget` / Chocolatey / Scoop.

### 3.2 Manifest-getrieben

Was installiert wird, steht **nicht im Code**, sondern in einer Konfigurationsdatei,
z. B. `manifest.toml`:

```toml
[git]
version = "2.47.0"
url     = "https://github.com/git-for-windows/git/releases/download/..."
sha256  = "..."

[python]
version = "3.12.7"
url     = "https://www.python.org/ftp/python/..."
sha256  = "..."

[fordiac_ide]   # „fordiac“ = 4diac-interner Name (org.eclipse.fordiac); Schlüssel ohne führende Ziffer
version = "3.4.0-milestone-2026-11-05_2214"
url     = "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-ide-release-history-milestone/releases/download/4diac-ide_3.4.0_milestone_2026-11-05_2214/4diac-ide_3.4.0-win32.win32.x86_64_milestone_2026-11-05_2214.zip"
sha256  = "e6f821ddeb60cb06258292c76a80a36eaf456d6f31f7c679d899ca00b56269c9"

[repos.training1]
url    = "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_training1.git"
ref    = "main"
target = "workspace/training1"
```

Vorteile: neue Schulung = neues Manifest; Versionen werden festgenagelt; Prüfsummen
sichern die Downloads ab.

❓ Ein Manifest pro Schulung (Profile, z. B. `--profile grundkurs`)?

### 3.3 Verzeichnisstruktur auf dem Ziel-PC (Vorschlag)

```
C:\ms\sl\
├── tools\
│   ├── git\
│   ├── python\
│   └── 4diac-ide\
├── workspace\            ← 4diac-Workspace, vorkonfiguriert
│   └── training1\
├── downloads\            ← Cache, ermöglicht Offline-Wiederholung
└── install.log
```

## 4. Ablauf

1. Umgebungsprüfung (OS, Architektur, freier Speicher, Internet)
2. Manifest laden (lokal oder ❓ von URL)
3. Für jede Komponente: *bereits vorhanden?* → überspringen, sonst
   herunterladen nach `downloads\<datei>.tmp` → SHA256 prüfen → erst bei Übereinstimmung
   umbenennen und installieren/entpacken (fehlerhafte Downloads werden verworfen)
4. Repositories klonen bzw. aktualisieren
5. 4diac-Workspace einrichten (Projekte importieren, ❓ Preferences vorbelegen)
6. Startmenü-/Desktop-Verknüpfungen ❓
7. Abschlussbericht: was installiert, was übersprungen, was fehlgeschlagen

## 5. Weitere Funktionen

- [ ] `--check` – nur prüfen, nichts verändern
- [ ] `--reset-training` – Übungs-Repo auf Ausgangszustand zurücksetzen
- [ ] `--uninstall` – alles wieder entfernen
- [ ] ❓ Aktualisierung des Installers selbst

## 6. Nicht-Ziele

- Kein allgemeiner Paketmanager
- ❓ Keine Installation von Treibern/Hardware-Tools mit Admin-Pflicht

## 7. Offene Fragen (Zusammenfassung)

1. ~~Welche Plattformen außer Windows?~~ → **Windows only** (Schulvorgabe: macOS/Linux/ARM nicht zugelassen).
2. ~~Admin-Rechte verfügbar oder nicht?~~ → Ohne Admin; PATH über Benutzer-PATH (2.2).
3. ~~Offline-Betrieb nötig?~~ → Installation online; danach muss alles offline laufen.
4. Eigene Downloads (portable) oder `winget`/Chocolatey/Scoop?
5. ~~Welche 4diac-IDE-Version?~~ → 3.4.0 Milestone 2026-11-05_2214. Bezug über
   GitHub Release (siehe 2.1). Offen: wird FORTE benötigt?
6. Welche „weiteren“ Komponenten?
7. Ein Manifest oder Profile pro Schulung?
8. Verteilung an Teilnehmer: Einzeiler, ZIP, oder USB-Stick?
   Hinweis: `irm … | iex` führt Code ungeprüft direkt aus dem Netz aus und wird daher
   **nicht** verwendet. Falls Einzeiler, dann so, dass das Skript erst als Datei
   gespeichert und dann gestartet wird (Quelle: GitHub Release des Installers per HTTPS,
   alles Weitere prüft der Installer per SHA256 aus dem Manifest).
