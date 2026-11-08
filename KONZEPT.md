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
| Git for Windows (PortableGit) | Repos klonen, Übungsstände wechseln | **2.56.0.4** – festgedübelt (siehe 2.3) |
| Python         | Hilfsskripte, Generatoren                     | **3.15.2** – festgedübelt (siehe 2.4) |
| Eclipse 4diac IDE | Entwicklungsumgebung für IEC 61499         | **3.4.0 Milestone 2026-11-05_2214** – festgedübelt (siehe 2.1) |
| 4diac IDE Auto-Import-Plugin | Projekte im Workspace beim Start automatisch importieren | **1.0.0** – festgedübelt (siehe 2.5) |
| 4diac FORTE    | Laufzeitumgebung (lokal zum Testen)           | ❓ nötig?        |
| Trainings-Repos | `4diac_training1`, `4diac_training1_empty`, `4diac-SlurryTanker_AX-sample`, `4diac_EasyExampleCounter` … (siehe 2.5) | Branch/Tag ❓ |
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
- **Versionen sind festgedübelt.** Für jede Komponente steht genau eine Version mit URL
  und SHA256 in `manifest.json`. Kein „latest“, kein automatisches Update. Erhöht wird
  **nur manuell**: neue Version, URL und SHA256 eintragen, testen, committen. Bis dahin
  bekommen alle Teilnehmer exakt dieselben Versionen.
- **Download-Verfahren (für alle Komponenten gleich):** Alle Dateien kommen per HTTPS
  direkt vom Hersteller bzw. aus unserem Release-Repo, ohne Login:
  ```powershell
  $tmp = "C:\ms\sl\downloads\$file.tmp"
  Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
  if ((Get-FileHash $tmp -Algorithm SHA256).Hash -ne $sha256) {
      Remove-Item $tmp; throw "SHA256 stimmt nicht: $file"
  }
  Move-Item $tmp "C:\ms\sl\downloads\$file" -Force
  ```
  Liegt die Datei schon mit korrekter SHA256 in `downloads\`, wird nicht erneut geladen.
  Vor dem Download `[Net.ServicePointManager]::SecurityProtocol = 'Tls12'` setzen
  (Windows PowerShell 5.1 nutzt sonst ggf. veraltete TLS-Versionen) und
  `$ProgressPreference = 'SilentlyContinue'` (die Fortschrittsanzeige von 5.1 macht
  große Downloads um ein Vielfaches langsamer).
- **Entpacken:** ZIPs mit dem in Windows 10/11 enthaltenen `tar.exe`
  (`tar -xf <zip> -C <ziel>`), nicht mit `Expand-Archive` – das ist in PowerShell 5.1
  bei Tausenden Dateien (IDE: rund 3 900, Python: rund 2 300) sehr langsam.

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

> **Die Version ist festgedübelt**, bis wir manuell eine andere festlegen.

Installation unter Windows: ZIP nach `C:\ms\sl\tools\` entpacken (die ZIP enthält den
Oberordner `4diac-ide\`) – kein Setup, keine Admin-Rechte nötig.

> ⚠️ **ZWINGEND: Nach dem Entpacken den Ordner `C:\ms\sl\tools\4diac-ide\typelibrary`
> komplett löschen.** Ohne diesen Schritt gilt die Installation als fehlgeschlagen.
> Die Prüfung „bereits installiert?“ muss deshalb auch kontrollieren, dass `typelibrary`
> **nicht** existiert – sonst wird er erneut gelöscht.
>
> ```powershell
> Remove-Item 'C:\ms\sl\tools\4diac-ide\typelibrary' -Recurse -Force
> if (Test-Path 'C:\ms\sl\tools\4diac-ide\typelibrary') { throw 'typelibrary konnte nicht gelöscht werden' }
> ```
>
> Im Manifest als `"delete_after_extract": ["4diac-ide/typelibrary"]` hinterlegt,
> damit es nicht im Code versteckt ist. (Der Ordner heißt im ZIP klein geschrieben
> `typelibrary`; Windows unterscheidet nicht nach Groß-/Kleinschreibung.)

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
$add = @('C:\ms\sl\tools\git\cmd', 'C:\ms\sl\tools\python', 'C:\ms\sl\tools\python\Scripts')

# Rohwert lesen, OHNE %VARIABLEN% aufzulösen (GetEnvironmentVariable würde sie expandieren)
$key   = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey('Environment')
$raw   = $key.GetValue('Path', '', 'DoNotExpandEnvironmentNames')          # '' falls nicht vorhanden
$parts = @($raw -split ';' | Where-Object { $_.Trim() } | ForEach-Object { $_.TrimEnd('\') })

# Eigene Pfade VORANSTELLEN (vor den WindowsApps-Store-Alias), alte Vorkommen entfernen
$rest  = @($parts | Where-Object { $add -notcontains $_ })                 # -notcontains: ohne Groß/klein
$new   = ($add + $rest) -join ';'
if ($new -ne $raw) {
    $key.SetValue('Path', $new, [Microsoft.Win32.RegistryValueKind]::ExpandString)
    # Direktes Registry-Schreiben benachrichtigt niemanden -> WM_SETTINGCHANGE selbst senden
    Add-Type -Namespace Win32 -Name Native -MemberDefinition @'
[DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam,
    string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
'@
    $r = [UIntPtr]::Zero
    [void][Win32.Native]::SendMessageTimeout([IntPtr]0xffff, 0x1A, [UIntPtr]::Zero, 'Environment', 2, 5000, [ref]$r)
}
$key.Close()
```

Regeln:
- **Nicht `setx` verwenden** – schneidet bei 1024 Zeichen ab und zerstört so den PATH.
- **Nicht `[Environment]::Get/SetEnvironmentVariable(..., 'User')`** – liest den PATH
  expandiert und schreibt ihn als `REG_SZ` zurück; Einträge wie
  `%USERPROFILE%\AppData\Local\Microsoft\WindowsApps` würden dabei dauerhaft zu festen
  Pfaden. Stattdessen Rohwert lesen und als `REG_EXPAND_SZ` (`ExpandString`) schreiben.
- Eigene Einträge werden **vorangestellt**, nicht angehängt: Im Benutzer-PATH steht
  standardmäßig `…\Microsoft\WindowsApps` mit einem `python.exe`-Alias, der nur den
  Microsoft Store öffnet. Hinten angehängt würde in neuen Terminals dieser Alias gewinnen.
- Nur **eigene Einträge ergänzen/entfernen**, alle übrigen bleiben unverändert
  (idempotent: ein zweiter Lauf ändert nichts).
- Wirkt erst in **neu geöffneten** Terminals/Programmen. Der Installer stellt die eigenen
  Pfade zusätzlich im eigenen Prozess voran (`$env:Path = "<eigene Pfade>;$env:Path"`),
  damit die folgenden Schritte sofort mit den eigenen Werkzeugen laufen.
- `--uninstall` entfernt genau diese Einträge wieder.
- Der System-PATH steht trotzdem **vor** dem Benutzer-PATH: Ist z. B. schon ein anderes
  Python systemweit installiert, gewinnt dieses in neuen Terminals. Am Ende prüft der
  Installer mit `Get-Command git, python`, welche Programme in einem neuen Terminal
  gefunden würden, und **warnt im Abschlussbericht**, falls dort fremde Versionen gewinnen.

Ohne Admin machbar je Komponente:
- **Git:** PortableGit (selbstentpackendes Archiv) nach `C:\ms\sl\tools\git`, Details in 2.3.
- **Python:** offizielles ZIP-Paket von python.org entpacken, Details in 2.4.
- **4diac IDE:** ZIP entpacken, **danach `typelibrary` löschen** (siehe 2.1), braucht
  keinen PATH-Eintrag; Verknüpfung genügt.
  **Java ist enthalten:** eingebettetes JRE JustJ OpenJDK 25.0.4
  (`plugins/org.eclipse.justj.openjdk.hotspot.jre.full.stripped.win32.x86_64_25.0.4…`),
  keine separate Java-Installation nötig (geprüft am Milestone 2026-11-05_2214).

### 2.3 Git

Verwendet wird **Git for Windows als PortableGit**:

| | |
|---|---|
| Version  | **2.56.0.4** (Release `v2.56.0.windows.4` vom 2026-10-26) |
| Datei    | `PortableGit-2.56.0.4-64-bit.7z.exe` (60 MB) |
| URL      | <https://github.com/git-for-windows/git/releases/download/v2.56.0.windows.4/PortableGit-2.56.0.4-64-bit.7z.exe> |
| SHA256   | `b1f3e52216e2ed6882d1bebfd4d3fdf319bec40d2edbbf9fd26ec4fd3fce7ed1` (Release-Notes = GitHub-Digest) |
| Lizenz   | GPL-2.0, kostenlos, kein Konto nötig |

> **Die Version ist festgedübelt.** Der Installer installiert immer genau diese Version –
> kein „latest“, kein automatisches Update. Erhöht wird **nur manuell**: neue Version,
> URL und SHA256 in `manifest.json` eintragen, testen, committen. Bis dahin bekommen alle
> Teilnehmer dieselbe Version, auch wenn es inzwischen neuere gibt.

Download: direkt von GitHub (Release von Git for Windows), Verfahren siehe Abschnitt 2
(`.tmp` → SHA256 prüfen → übernehmen).

Installation ohne Admin: selbstentpackendes Archiv, kein Setup-Assistent:

```powershell
& C:\ms\sl\downloads\PortableGit-2.56.0.4-64-bit.7z.exe -o"C:\ms\sl\tools\git" -y
& C:\ms\sl\tools\git\cmd\git.exe config --system http.sslBackend schannel
```

`--system` schreibt in die Konfiguration von PortableGit unter `C:\ms\sl`, nicht ins
Windows-System. `schannel` = Windows-Zertifikatsspeicher, funktioniert auch hinter
Proxys mit TLS-Prüfung.

**Grafische Oberfläche:** keine zusätzliche. Die 4diac IDE bringt **EGit 8.0.0** mit
(Eclipse-Git-Integration, geprüft im Milestone 2026-11-05_2214) – damit lassen sich
Commit, Branch-Wechsel usw. direkt in der IDE erledigen.
Bewusst **nicht** GitKraken: kommerziell, Konto erforderlich, für private Repos
lizenzpflichtig, und es ersetzt das Kommandozeilen-Git nicht.

### 2.4 Python

Verwendet wird **CPython 3.15.2** von python.org als **ZIP-Paket** (kein Installer):

| | |
|---|---|
| Version  | **3.15.2** (Release vom 2026-10-25, aktuell stabile Version) |
| Datei    | `python-3.15.2-amd64.zip` (37 MB) |
| URL      | <https://www.python.org/ftp/python/3.15.2/python-3.15.2-amd64.zip> |
| SHA256   | `d6da9c33a32cf111e1d52b91392c83ea6a808545b646e0557f66cb6d9ee76785` |
| Quelle SHA256 | offizieller Python-Index <https://www.python.org/ftp/python/index-windows.json> (= eigener Download) |
| Lizenz   | PSF License, kostenlos |

> **Die Version ist festgedübelt**, bis wir sie manuell erhöhen.

**Warum das ZIP und nicht der klassische `.exe`-Installer:**
- Das ZIP ist das offizielle Paket, das auch der neue *Python Install Manager* von
  python.org verwendet. Den klassischen `.exe`-Installer gibt es **ab Python 3.16 nicht
  mehr** (unter `ftp/python/3.16.0/` liegen nur noch ZIPs) – mit dem ZIP bleibt der Weg
  bei späteren Versionen gleich.
- Reines Entpacken: kein Setup, keine Registry-Einträge, keine Startmenü-Einträge,
  keine Admin-Rechte, nichts außerhalb von `C:\ms\sl`. Deinstallieren = Ordner löschen.
- Gleiches Verfahren wie bei Git und 4diac IDE.

**Inhalt geprüft** (nicht das abgespeckte „embeddable package“): `python.exe`,
`pythonw.exe`, `vcruntime140*.dll`, **`pip` bereits installiert** (`Lib/site-packages/pip`),
`venv`, `ensurepip`, `tkinter` – vollständige Standardbibliothek.

Installation:

```powershell
tar -xf C:\ms\sl\downloads\python-3.15.2-amd64.zip -C C:\ms\sl\tools\python
& C:\ms\sl\tools\python\python.exe -m pip --version     # Funktionsprobe
```

Das ZIP hat keinen Oberordner (`python.exe` liegt direkt im Wurzelverzeichnis), daher
direkt nach `tools\python` entpacken. PATH-Einträge `tools\python` und
`tools\python\Scripts` siehe 2.2.

### 2.5 Workspaces und automatischer Projektimport

**Problem:** Nach dem Klonen eines Trainings-Repos zeigt die IDE einen leeren Workspace
(*„There are no projects in your workspace.“*). Jeder Teilnehmer muss die Projekte über
*File → Import → Existing Projects* von Hand importieren – eine Klick-Orgie, die im
Unterricht **bis zu 2 Stunden** kostet. Das muss vollständig automatisch gehen.

**Ein Workspace pro Training.** Jedes Trainings-Repo wird nach `C:\ms\sl\prj\<repo>`
geklont; der 4diac-Workspace ist der Ordner `Ventilsteuerung\4diacIDE-workspace` darin:

| Training | Workspace |
|---|---|
| Training 1 | `C:\ms\sl\prj\4diac_training1\Ventilsteuerung\4diacIDE-workspace` |
| Training 1 (leer) | `C:\ms\sl\prj\4diac_training1_empty\Ventilsteuerung\4diacIDE-workspace` |
| Slurry Tanker | `C:\ms\sl\prj\4diac-SlurryTanker_AX-sample\Ventilsteuerung\4diacIDE-workspace` |
| Easy Example Counter | `C:\ms\sl\prj\4diac_EasyExampleCounter\Ventilsteuerung\4diacIDE-workspace` |
| usw. | `C:\ms\sl\prj\<repo>\Ventilsteuerung\4diacIDE-workspace` |

Die Projekte (z. B. `test_AX`, `test_B`, `test_VV`) liegen direkt im Workspace-Ordner.

> **Regel: Kein Repo enthält einen `.metadata`-Ordner** – er steht immer in `.gitignore`.
> Der Workspace-`.metadata` entsteht beim ersten Start der IDE auf dem Teilnehmer-PC.
> Einstellungen, die mitgeliefert werden sollen, gehören in die projektspezifischen
> Einstellungen (Project Specific Settings) im Projekt.
>
> Achtung: `.gitignore` entfernt bereits versionierte Dateien **nicht**. Stand 2026-11-08
> ist in `4diac_training1_empty` und `4diac-SlurryTanker_AX-sample` noch
> `Ventilsteuerung/4diacIDE-workspace/.metadata/…` eingecheckt (aus der Zeit vor den
> projektspezifischen Einstellungen). Dort einmalig `git rm -r --cached
> Ventilsteuerung/4diacIDE-workspace/.metadata`, Einstellungen in die Projekte überführen,
> `.gitignore` prüfen, committen.

**Automatischer Import: Plugin `4diac-ide-autoimport`**

Eigenes Repo mit eigenem Release-Zyklus:
<https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-ide-autoimport>

| | |
|---|---|
| Version  | **1.0.0** |
| Datei    | `de.meisterschulen.fordiac.ide.autoimport_1.0.0.jar` (4 KB) |
| URL      | <https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-ide-autoimport/releases/download/v1.0.0/de.meisterschulen.fordiac.ide.autoimport_1.0.0.jar> |
| SHA256   | `afde6fd2fddef535492708c9f5e229e678fd1fa7108ff053937b8300c451ae51` |
| Lizenz   | EPL-2.0 |

> **Die Version ist festgedübelt**, bis wir sie manuell erhöhen.

- Installation: die `.jar` nach `C:\ms\sl\tools\4diac-ide\dropins\` kopieren (Ordner
  anlegen). Keine Admin-Rechte nötig.
- Funktion: Bei jedem Start importiert das Plugin jeden direkten Unterordner des
  Workspace, der eine `.project`-Datei enthält, nicht mit `.` beginnt (`.lib`,
  `.metadata` werden übersprungen), dessen Projektname dem Ordnernamen entspricht und
  der noch nicht im Workspace ist. Bereits importierte Projekte bleiben unangetastet.
  Jeder Import steht im Log `.metadata\.log` (`Imported: test_AX`).
- Getestet am 2026-11-08 mit dem Milestone 2026-11-05_2214 und `4diac_training1`:
  `test_AX`, `test_B`, `test_VV` sind nach dem ersten Start ohne einen Klick da, mit
  Git-Anzeige `[4diac_training1 main]`. Messwerte siehe [HARDWARE-BEDARF.md](HARDWARE-BEDARF.md).
- Vorgestellt in der 4diac-Community:
  <https://github.com/eclipse-4diac/4diac-ide/discussions/3164>

**Dialoge beim ersten Start abschalten.** Der Installer schreibt
`C:\ms\sl\tools\4diac-ide\ms-sl-customization.ini`:

```ini
org.eclipse.ui/showIntro=false
org.eclipse.ui/windows.defender.startup.check.skip=true
```

- `showIntro=false` – keine Willkommensseite.
- `windows.defender.startup.check.skip=true` – keine Abfrage „Microsoft Defender
  Exclusion Check“. Die Abfrage verlangt eine Entscheidung, und die Ausnahme selbst
  bräuchte ohnehin Admin-Rechte. Achtung: Der Präfix ist `org.eclipse.ui`, **nicht**
  `org.eclipse.ui.workbench` (geprüft; mit dem falschen Präfix erscheint der Dialog weiter).
- Eingebunden über den Startparameter `-pluginCustomization` (siehe Verknüpfung). Die Werte
  sind damit Vorgaben; ändert ein Teilnehmer sie in den Einstellungen, gilt seine Wahl.

**Verknüpfungen – UNBEDINGT auf dem Desktop** (zusätzlich im Startmenü). Der Desktop
ist für Schüler der schnellste Einstieg. Der Installer legt dort an:

| Verknüpfung (Desktop + Startmenü) | Ziel |
|---|---|
| „4diac Projekte“ | Ordner `C:\ms\sl\prj` (öffnet den Explorer) |
| „4diac IDE“ | 4diac IDE mit Workspace-Auswahl (siehe unten) |
| „4diac – Training 1“, „4diac – Slurry Tanker“ … (je Training und je `--new-project`) | 4diac IDE mit dem Workspace des Trainings (siehe unten) |

Zusätzlich **„4diac IDE“** (Desktop + Startmenü) ohne festen Workspace: Sie zeigt beim
Start die Workspace-Auswahl („4diac IDE Launcher“). Damit dort nicht
`%USERPROFILE%\4diacIDE-workspace` (außerhalb von `C:\ms\sl`) vorgeschlagen wird:

- Argumente: `-data @noDefault -pluginCustomization "C:\ms\sl\tools\4diac-ide\ms-sl-customization.ini"`
  (`@noDefault` erzwingt die Auswahl).
- Der Installer füllt die Liste „Recent Workspaces“ mit allen Trainings-Workspaces vor,
  in `C:\ms\sl\tools\4diac-ide\configuration\.settings\org.eclipse.ui.ide.prefs`:
  ```ini
  eclipse.preferences.version=1
  MAX_RECENT_WORKSPACES=10
  RECENT_WORKSPACES=C\:\\ms\\sl\\prj\\4diac_training1\\Ventilsteuerung\\4diacIDE-workspace\nC\:\\ms\\sl\\prj\\...
  RECENT_WORKSPACES_PROTOCOL=3
  SHOW_RECENT_WORKSPACES=true
  SHOW_WORKSPACE_SELECTION_DIALOG=true
  ```
  (Einträge durch `\n` getrennt, `\` und `:` escaped; der erste Eintrag ist vorausgewählt.)
  Geprüft am 2026-11-08: Die Auswahl zeigt die vorbelegten Workspaces als anklickbare Liste.
- Bei jedem `--update`/`--new-project` wird die Liste neu geschrieben.

Aufbau einer IDE-Verknüpfung, z. B. „4diac – Training 1“:

| | |
|---|---|
| Ziel | `C:\ms\sl\tools\4diac-ide\4diac-ide.exe` |
| Argumente | `-data "C:\ms\sl\prj\4diac_training1\Ventilsteuerung\4diacIDE-workspace" -pluginCustomization "C:\ms\sl\tools\4diac-ide\ms-sl-customization.ini"` |
| Ausführen in | `C:\ms\sl\tools\4diac-ide` |

Angelegt per `WScript.Shell`-COM-Objekt (`CreateShortcut`) auf dem Desktop des Benutzers
(`[Environment]::GetFolderPath('Desktop')` – bei OneDrive-Umleitung nicht
`%USERPROFILE%\Desktop`) und unter `%APPDATA%\Microsoft\Windows\Start Menu\Programs\4diac\`
– keine Admin-Rechte nötig. `--uninstall` entfernt genau diese Verknüpfungen wieder. Durch
`-data` öffnet jede Verknüpfung direkt den richtigen Workspace, ohne Workspace-Auswahl.

**Neues Projekt anlegen (zweites Empty).** Will ein Schüler ein weiteres eigenes Projekt
beginnen, legt der Installer eine neue Kopie von `4diac_training1_empty` an:

```
install.cmd --new-project Maehwerk
```

0. **Namen prüfen (Pflicht, vor jedem weiteren Schritt):** nur
   `^[A-Za-z0-9_-]{1,40}$` – also keine Leerzeichen, Umlaute, `.`, `\`, `/` oder
   Metazeichen wie `&|<>"`. Sonst Abbruch mit Hinweis. Verhindert, dass der Name aus
   `C:\ms\sl\prj\` herausführt (`..\`) oder in `cmd`/PowerShell Befehle einschleust.
   Existiert `C:\ms\sl\prj\<Name>` schon → Abbruch, nichts überschreiben.
   `Neues Projekt.cmd` übergibt den eingegebenen Namen nur an den Installer und prüft
   ihn dort, nicht selbst in `cmd`.
1. `4diac_training1_empty` nach `C:\ms\sl\prj\Maehwerk\` klonen.
2. Verknüpfung „4diac – Maehwerk“ anlegen (Workspace
   `C:\ms\sl\prj\Maehwerk\Ventilsteuerung\4diacIDE-workspace`).
3. Beim ersten Start importiert das Plugin die Projekte automatisch.

Jedes Projekt hat seinen eigenen Workspace; gleiche Projektnamen (`test_AX` …) in
verschiedenen Workspaces stören sich daher nicht. Für Schüler zusätzlich als
Doppelklick-Datei `Neues Projekt.cmd`, die nur nach dem Namen fragt.

❓ Offen:
- Was passiert mit dem Git-Remote der Kopie? Nur umbenennen (`origin` → `upstream`)
  genügt **nicht**: Das Branch-Tracking bleibt erhalten, ein einfaches `git push` ginge
  weiter ans Schul-Repo. Vorschlag: Fetch-URL behalten (Updates der Vorlage holen), aber
  die Push-URL ungültig setzen, damit ein Push mit klarer Fehlermeldung scheitert:
  ```
  git remote rename origin upstream
  git remote set-url --push upstream PUSH-DEAKTIVIERT-EIGENES-REMOTE-EINTRAGEN
  git branch --unset-upstream
  ```
  Der Schüler kann später ein eigenes Remote als `origin` eintragen.

**Prüfung „IDE geöffnet?“** (für `--update` und das IDE-Update, siehe 2.6). Die Datei
`.metadata\.lock` allein sagt nichts: Sie **bleibt nach dem Beenden liegen** (auch nach
Absturz). Auch „lässt sich zum Schreiben öffnen“ reicht nicht – das gelingt auch bei
laufender IDE. Zuverlässig (geprüft am 2026-11-08):

1. Prozess: läuft ein `4diac-ide.exe`, dessen Pfad unter `C:\ms\sl\tools\` liegt
   (`Win32_Process.ExecutablePath`; eine andere, privat installierte 4diac IDE zählt
   nicht), und – für einen bestimmten Workspace – dessen `CommandLine` dessen `-data`-Pfad
   enthält?
2. Sperre: `.metadata\.lock` öffnen und selbst eine Bytebereich-Sperre versuchen
   (`FileStream.Lock(0,1)` bzw. `msvcrt.locking`). Schlägt das fehl, hält eine IDE den
   Workspace; gelingt es, sofort wieder freigeben.

### 2.6 Aktualisieren

#### Projekte (Trainings-Repos) aktualisieren

Grundsatz: **Der Schüler verliert keine Übung.** Gesichert werden **nur die veränderten
`.SUB`-Dateien** (Subapplikationen) – **nicht** der ganze Ordner. Die Sicherung liegt
umbenannt **direkt neben dem Original im Projekt**, sodass der Schüler seine Version sofort
in der IDE sieht:

```
test_AX/
  Uebung1.SUB                               ← neuer Stand aus dem Schul-Repo
  Uebung1_sicherung_20261108_153012.SUB     ← Version des Schülers (Typ umbenannt)
```

Aufruf: `install.cmd --update` (alle Trainings) bzw. `install.cmd --update 4diac_training1`.

1. **IDE geschlossen?** Prüfung wie in 2.5 („IDE geöffnet?“); ist der Workspace noch
   geöffnet, Abbruch mit Hinweis „Bitte 4diac IDE schließen“.
2. **Veränderte `.SUB` finden:** `git status --porcelain` → alle **versionierten**
   `.SUB`-Dateien mit Änderungen (Groß-/Kleinschreibung der Endung egal). Zusätzlich
   `.SUB`-Dateien, die sich durch lokale Commits vom Schul-Repo unterscheiden
   (`git diff --name-only origin/<ref>...HEAD`).
3. **Inhalt merken:** Diese Dateien in einen temporären Ordner unter
   `C:\ms\sl\downloads\` kopieren (bevor Git sie überschreibt).
4. **Original aktualisieren:** `git fetch`, `git checkout -f <ref>` (falls der Schüler auf
   einem anderen Branch oder im *detached HEAD* ist), `git reset --hard origin/<ref>`.
   **Kein `git clean`:** Neue Dateien, die der Schüler selbst angelegt hat (nicht
   versioniert), bleiben unangetastet.
5. **Sicherung zurückschreiben:** Jede gemerkte `.SUB` als
   `<Name>_sicherung_<JJJJMMTT>_<hhmmss>.SUB` in denselben Ordner schreiben und dabei den
   **Typnamen in der Datei mit umbenennen** (`Name`-Attribut des Wurzelelements
   `SubAppType`). Sonst gäbe es in 4diac zwei Typen mit demselben Namen. Existiert der
   Dateiname schon, `_2`, `_3` … anhängen.
6. **Bericht:** „Training 1 aktualisiert. Deine geänderten Übungen wurden gesichert:
   test_AX/Uebung1_sicherung_20261108_153012.SUB …“

Was **nicht** gesichert wird: Änderungen an anderen versionierten Dateien (z. B. `.sys`,
`.fbt`, `.gcf`) werden beim Update verworfen – die Übungen stecken in den `.SUB`.

Die Sicherungsdateien sind nicht versioniert. Beim nächsten `--update` werden Dateien
`*_sicherung_*.SUB` daher nicht erneut gesichert, sondern einfach liegen gelassen.

#### 4diac IDE aktualisieren

Auslöser: Wir erhöhen die IDE-Version in `manifest.json` von Hand (festgedübelt, siehe
2.1). Der Installer merkt sich die installierte Version in
`C:\ms\sl\tools\4diac-ide\.ms-sl-version`. Weicht sie vom Manifest ab, wird beim
nächsten `install.cmd` aktualisiert:

1. **Läuft eine IDE?** Läuft ein `4diac-ide.exe` aus `C:\ms\sl\tools\` oder ist ein
   Workspace unter `C:\ms\sl\prj\` gesperrt (Prüfung wie in 2.5) → Abbruch mit Hinweis
   (Windows sperrt geöffnete Dateien, Löschen/Umbenennen würde fehlschlagen).
2. **Erst laden, dann löschen:**
   1. neue ZIP nach `downloads\` laden, SHA256 prüfen,
   2. nach `C:\ms\sl\tools\4diac-ide.neu\` entpacken,
   3. dort **`typelibrary` löschen** (Pflicht, siehe 2.1), Auto-Import-Plugin nach
      `dropins\` kopieren, `ms-sl-customization.ini` und `.ms-sl-version` schreiben,
   4. erst wenn alles geklappt hat: `tools\4diac-ide` löschen und `4diac-ide.neu` in
      `4diac-ide` umbenennen.

   Bricht unterwegs etwas ab (z. B. Internet weg), bleibt die alte IDE funktionsfähig.
3. **`.metadata` in allen Workspaces unter `C:\ms\sl\prj\` löschen** – nur bei einem
   Versionswechsel. Damit gibt es keine Probleme mit
   veralteten Zwischenspeichern/Typindizes der alten Version. Verloren gehen nur
   IDE-weite Einstellungen (Window → Preferences) und das Fensterlayout; die Projekte
   holt das Auto-Import-Plugin beim nächsten Start zurück, projektspezifische
   Einstellungen liegen im Projekt und bleiben erhalten.

Die Verknüpfungen zeigen weiter auf `tools\4diac-ide\4diac-ide.exe` und bleiben
unverändert. ❓ Alte IDE-ZIPs aus `downloads\` löschen (spart ca. 300 MB je Version)?

## 3. Architektur (Vorschlag)

### 3.1 Henne-Ei-Problem

Python soll installiert werden, kann also nicht Voraussetzung für den Installer sein.
Daher zweistufig:

0. **Starter** – `install.cmd` (Doppelklick), ruft auf:
   `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*`
   (`%*` reicht alle Argumente wie `--new-project Maehwerk` an den Bootstrap weiter; der
   Bootstrap gibt sie unverändert an den Python-Hauptinstaller weiter, der sie auswertet.)
   Nötig, weil Windows `.ps1`-Skripte standardmäßig blockiert (Ausführungsrichtlinie
   `Restricted`/`RemoteSigned`, Internet-Markierung bei heruntergeladenen Dateien).
   `-ExecutionPolicy Bypass` gilt nur für diesen einen Aufruf, keine Systemänderung.
1. **Bootstrap** – `install.ps1` (Windows PowerShell 5.1, auf jedem Windows vorhanden)
   - prüft Umgebung, legt Basisverzeichnis an
   - liest `manifest.json` mit `ConvertFrom-Json` (bordeigen, keine Zusatzmodule)
   - installiert Git und Python
2. **Hauptinstaller** – Python-Skript (`trainings_installer/`)
   - liest Manifest, installiert restliche Komponenten, klont Repos, richtet Workspace ein

❓ Alternative: alles in PowerShell, oder Verwendung von `winget` / Chocolatey / Scoop.

### 3.2 Manifest-getrieben

Was installiert wird, steht **nicht im Code**, sondern in `manifest.json`.
**JSON statt TOML**, weil der Bootstrap in Windows PowerShell 5.1 läuft: Die kann JSON
bordeigen lesen (`ConvertFrom-Json`), TOML nicht – und Python ist zu diesem Zeitpunkt
noch nicht installiert. Der Python-Hauptinstaller liest dieselbe Datei mit `json`.

```json
{
  "git": {
    "version": "2.56.0.4",
    "url": "https://github.com/git-for-windows/git/releases/download/v2.56.0.windows.4/PortableGit-2.56.0.4-64-bit.7z.exe",
    "sha256": "b1f3e52216e2ed6882d1bebfd4d3fdf319bec40d2edbbf9fd26ec4fd3fce7ed1"
  },
  "python": {
    "version": "3.15.2",
    "url": "https://www.python.org/ftp/python/3.15.2/python-3.15.2-amd64.zip",
    "sha256": "d6da9c33a32cf111e1d52b91392c83ea6a808545b646e0557f66cb6d9ee76785"
  },
  "fordiac_ide": {
    "version": "3.4.0-milestone-2026-11-05_2214",
    "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-ide-release-history-milestone/releases/download/4diac-ide_3.4.0_milestone_2026-11-05_2214/4diac-ide_3.4.0-win32.win32.x86_64_milestone_2026-11-05_2214.zip",
    "sha256": "e6f821ddeb60cb06258292c76a80a36eaf456d6f31f7c679d899ca00b56269c9",
    "delete_after_extract": ["4diac-ide/typelibrary"]
  },
  "fordiac_autoimport": {
    "version": "1.0.0",
    "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-ide-autoimport/releases/download/v1.0.0/de.meisterschulen.fordiac.ide.autoimport_1.0.0.jar",
    "sha256": "afde6fd2fddef535492708c9f5e229e678fd1fa7108ff053937b8300c451ae51",
    "target": "tools/4diac-ide/dropins"
  },
  "repos": {
    "4diac_training1": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_training1.git",
      "ref": "main",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Training 1"
    },
    "4diac_training1_empty": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_training1_empty.git",
      "ref": "main",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Training 1 (leer)",
      "template_for_new_projects": true
    },
    "4diac-SlurryTanker_AX-sample": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-SlurryTanker_AX-sample.git",
      "ref": "main",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Slurry Tanker"
    },
    "4diac_EasyExampleCounter": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_EasyExampleCounter.git",
      "ref": "main",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Easy Example Counter"
    }
  }
}
```

Schlüssel `fordiac_ide`: „fordiac“ ist der 4diac-interne Name (`org.eclipse.fordiac`)
und vermeidet einen Schlüssel mit führender Ziffer.

`repos`: Der Schlüssel ist der Repo-Name und zugleich der Ordner unter `C:\ms\sl\prj\`.
`workspace` ist relativ zum Repo-Ordner, `shortcut` der Name der Verknüpfung.
`template_for_new_projects` markiert das Repo, das `--new-project` kopiert.

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
│       ├── dropins\
│       │   └── de.meisterschulen.fordiac.ide.autoimport_1.0.0.jar
│       └── ms-sl-customization.ini
├── prj\                  ← ein Ordner pro Trainings-Repo (git clone)
│   ├── 4diac_training1\
│   │   └── Ventilsteuerung\
│   │       └── 4diacIDE-workspace\   ← Workspace für Training 1 (-data)
│   ├── 4diac_training1_empty\
│   ├── 4diac-SlurryTanker_AX-sample\
│   ├── 4diac_EasyExampleCounter\
│   └── <eigenes Projekt>\  ← per --new-project aus _empty
├── downloads\            ← Cache, ermöglicht Offline-Wiederholung
└── install.log
```

## 4. Ablauf

1. Umgebungsprüfung (OS, Architektur, freier Speicher, Internet)
2. Manifest laden (lokal oder ❓ von URL)
3. Für jede Komponente: *bereits in der Manifest-Version vorhanden?* → überspringen
   (4diac IDE: Vergleich mit `.ms-sl-version`; bei abweichender Version Update nach 2.6
   inkl. Löschen von `.metadata`), sonst
   herunterladen nach `downloads\<datei>.tmp` → SHA256 prüfen → erst bei Übereinstimmung
   umbenennen und installieren/entpacken (fehlerhafte Downloads werden verworfen);
   bei der 4diac IDE danach **`typelibrary` löschen** (Pflicht, siehe 2.1);
   Auto-Import-Plugin nach `tools\4diac-ide\dropins\` kopieren,
   `ms-sl-customization.ini` schreiben (siehe 2.5)
4. Repositories nach `C:\ms\sl\prj\<repo>` klonen bzw. aktualisieren
5. Verknüpfung pro Training anlegen (`-data <workspace>`, siehe 2.5) – den Import der
   Projekte übernimmt das Plugin beim ersten Start der IDE
6. Abschlussbericht: was installiert, was übersprungen, was fehlgeschlagen

## 5. Weitere Funktionen

- [ ] `--new-project <Name>` – neues eigenes Projekt aus `4diac_training1_empty` (siehe 2.5)
- [ ] `--check` – nur prüfen, nichts verändern
- [ ] `--update [<repo>]` – Trainings aktualisieren, veränderte `.SUB` werden umbenannt gesichert
  (siehe 2.6; ersetzt das frühere `--reset-training`)
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
   **nicht** verwendet. Gestartet wird immer über `install.cmd` (siehe 3.1). Falls
   Einzeiler, dann so, dass das Skript erst als Datei gespeichert und dann gestartet wird (Quelle: GitHub Release des Installers per HTTPS,
   alles Weitere prüft der Installer per SHA256 aus dem Manifest).
9. ~~Verknüpfungen nur im Startmenü oder zusätzlich auf dem Desktop?~~ → **Desktop
   unbedingt** (plus Startmenü): „4diac Projekte“ (`C:\ms\sl\prj`), „4diac IDE“ mit
   Workspace-Auswahl und je Training eine IDE-Verknüpfung (siehe 2.5).
10. `--new-project`: Push-Sperre über ungültige Push-URL so in Ordnung? (siehe 2.5;
    Namensprüfung ist festgelegt).
