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
| 4diac FORTE    | Laufzeitumgebung (lokal zum Testen)           | **nein** – wird nicht installiert |
| logiBUS-Firmware | ESP32-Firmware für alle 14 Board-Typen, passend zu den ELFs der Trainings-Repos (wird nur abgelegt, nicht geflasht) | **ein Build** aus einem Release von `4diac_training1` (welcher: `manifest.json`) – festgedübelt (siehe 2.7) |
| Trainings-Repos | `4diac_training1`, `4diac_training1_empty` und alle umgestellten Beispiel-Projekte (SlurryTanker, EasyExampleCounter, Modbus …; Liste in 3.2) | je Repo ein **Tag** – festgedübelt (siehe 3.2) |
| weitere …      | keine (kein VS Code, kein Wireshark, keine CAN-Treiber; ISO-Designer lädt jeder selbst, siehe 6) | **nein** |

## 2. Rahmenbedingungen

- **Zielgeräte:** **Persönliche Notebooks** an den
  [Meisterschulen am Ostbahnhof](https://www.meisterschulen-muenchen.de/Landmaschinenmechanik_10_0.html).
  **Ein Gerät = eine Person = ein Windows-Login.** Gemeinsam genutzte PCs gibt es nicht.

  | Gerät              | Beschaffung | Admin-Rechte |
  |--------------------|-------------|--------------|
  | Schüler-Notebook   | privat      | **ja** (Pflicht laut Schulvorgabe) |
  | Lehrer-Notebook    | dienstlich, verwaltet | **nein** (Ordner unter `C:\` anlegen geht) |

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
| Slurry Tanker AX | `C:\ms\sl\prj\4diac-SlurryTanker_AX-sample\Ventilsteuerung\4diacIDE-workspace` |
| Slurry Tanker | `C:\ms\sl\prj\4diac-SlurryTanker-sample\Ventilsteuerung\4diacIDE-workspace` |
| Easy Example Counter | `C:\ms\sl\prj\4diac_EasyExampleCounter\Ventilsteuerung\4diacIDE-workspace` |
| Modbus TCP | `C:\ms\sl\prj\4diac_modbus_tcp_sample\Ventilsteuerung\4diacIDE-workspace` |
| Modbus RTU | `C:\ms\sl\prj\4diac_modbus_rtu_sample\Ventilsteuerung\4diacIDE-workspace` |
| Empty 1 | `C:\ms\sl\prj\4diac_empty1\Ventilsteuerung\4diacIDE-workspace` |
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
| „4diac – Training 1“, „4diac – Slurry Tanker AX“ … (je Training und je `--new-project`) | 4diac IDE mit dem Workspace des Trainings (siehe unten) |
| „logiBUS ELF-Verwaltung“ | grafische ELF-Verwaltung aus `4diac_training1` (siehe unten) |

Zusätzlich **„4diac IDE“** (Desktop + Startmenü) ohne festen Workspace: Sie zeigt beim
Start die Workspace-Auswahl („4diac IDE Launcher“). Damit dort nicht
`%USERPROFILE%\4diacIDE-workspace` (außerhalb von `C:\ms\sl`) vorgeschlagen wird:

- Argumente: `-data @noDefault -pluginCustomization "C:\ms\sl\tools\4diac-ide\ms-sl-customization.ini"`
  (`@noDefault` erzwingt die Auswahl).
- Der Installer füllt die Liste „Recent Workspaces“ mit allen Trainings-Workspaces vor,
  in `C:\ms\sl\tools\4diac-ide\configuration\.settings\org.eclipse.ui.ide.prefs`:
  ```ini
  eclipse.preferences.version=1
  MAX_RECENT_WORKSPACES=<Anzahl Einträge, mindestens 10>
  RECENT_WORKSPACES=C\:\\ms\\sl\\prj\\4diac_training1\\Ventilsteuerung\\4diacIDE-workspace\nC\:\\ms\\sl\\prj\\...
  RECENT_WORKSPACES_PROTOCOL=3
  SHOW_RECENT_WORKSPACES=true
  SHOW_WORKSPACE_SELECTION_DIALOG=true
  ```
  (Einträge durch `\n` getrennt, `\` und `:` escaped; der erste Eintrag ist vorausgewählt.)
  `MAX_RECENT_WORKSPACES` = Anzahl der Workspaces, damit auch bei vielen eigenen Projekten
  keiner aus der Liste fällt. Eclipse nimmt größere Werte an, 10 ist nur das Minimum
  (`ChooseWorkspaceData`: `Math.max(max, RECENT_MAX_LENGTH)`).
  Geprüft am 2026-11-08: Die Auswahl zeigt die vorbelegten Workspaces als anklickbare Liste.
- Die Liste wird neu geschrieben bei jedem `install.cmd`, `--update`, `--new-project`
  **und nach einem IDE-Update** – die Datei liegt in `tools\4diac-ide\configuration\` und
  verschwindet beim Tausch des IDE-Ordners (siehe 2.6).
- Geschrieben wird nur, wenn **keine** IDE aus `C:\ms\sl\tools\` läuft. Eine laufende IDE
  hat die alte Liste im Speicher und würde sie beim Beenden zurückschreiben. Läuft eine,
  holt der nächste Lauf von `install.cmd` das Schreiben nach (Hinweis an den Schüler).
- „Ausführen in“ der Verknüpfung: **`C:\ms\sl\prj`**. Grund (geprüft am 2026-11-08): Ist
  die Liste leer, schlägt die Auswahl `<Ausführen in>\workspace` vor – ein
  `-Dosgi.instance.area.default` in `4diac-ide.ini` wird dabei ignoriert. So bleibt auch
  dieser Ersatzvorschlag innerhalb von `C:\ms\sl`.

> **Regel: Es entsteht nie ein Workspace außerhalb von `C:\ms\sl`.** Jede Verknüpfung
> startet entweder mit festem `-data` unter `C:\ms\sl\prj\` oder mit der vorbelegten
> Workspace-Auswahl.
>
> Grenze: Die Workspace-Auswahl selbst lässt sich nicht sperren – wer dort bewusst einen
> anderen Pfad eintippt oder per „Browse…“ wählt, bekommt ihn. Vorbelegung und
> „Ausführen in“ sorgen dafür, dass das nicht versehentlich passiert.

Aufbau einer IDE-Verknüpfung, z. B. „4diac – Training 1“:

| | |
|---|---|
| Ziel | `C:\ms\sl\tools\4diac-ide\4diac-ide.exe` |
| Argumente | `-data "C:\ms\sl\prj\4diac_training1\Ventilsteuerung\4diacIDE-workspace" -pluginCustomization "C:\ms\sl\tools\4diac-ide\ms-sl-customization.ini"` |
| Ausführen in | `C:\ms\sl\tools\4diac-ide` |

**„logiBUS ELF-Verwaltung“** – grafisches Werkzeug aus dem training1-Repo
(`Ventilsteuerung/scripts_central/elf_manager_gui.py`). Es zeigt für alle Bibliotheken
aus `LIB_VERSIONS` den Stand auf dem Gerät (aktuell, anderer Stand, alte Version, fehlt)
und lädt angehakte Bibliotheken samt Abhängigkeiten als ELF-Grundausstattung hoch
(`elf_grundausstattung.libs.json`, wie das Preload-Skript; andere Manifeste und
`*.fboot` auf dem Gerät werden dabei gelöscht). Ergänzt das Preload-Skript, ersetzt es
nicht.

| | |
|---|---|
| Ziel | `C:\ms\sl\tools\python\pythonw.exe` |
| Argumente | `elf_manager_gui.py` (ohne Argument: Gerät `logibus.local`; optional Host/IP) |
| Ausführen in | `C:\ms\sl\prj\4diac_training1\Ventilsteuerung\scripts_central` |

- „Ausführen in“ ist Pflicht: Das Skript importiert seine Nachbarmodule (`deploy_common`,
  `elf_libs_manifest_lib`, `make_4diac_training1_deploy`,
  `make_4diac_training1_elf_preload`) und findet die ELFs über `../4diacIDE-workspace/.lib`.
- Nur Standardbibliothek inkl. `tkinter` – ist im Python-ZIP enthalten (siehe 2.4).
- Die ELFs kommen aus dem training1-Tag im Manifest und passen damit zur Firmware
  (siehe 2.7).
- Angelegt wird die Verknüpfung nur, wenn die Datei im ausgecheckten Tag existiert
  (erst ab dem ersten training1-Release, das sie enthält); sonst Hinweis im Bericht.

Angelegt per `WScript.Shell`-COM-Objekt (`CreateShortcut`) auf dem Desktop des Benutzers
(`[Environment]::GetFolderPath('Desktop')` – bei OneDrive-Umleitung nicht
`%USERPROFILE%\Desktop`) und unter `%APPDATA%\Microsoft\Windows\Start Menu\Programs\4diac\`
– keine Admin-Rechte nötig.

**Keine doppelten Verknüpfungen.** Jede Verknüpfung hat einen festen Dateinamen (z. B.
`4diac – Training 1.lnk`). Der Installer führt eine Liste aller angelegten
Verknüpfungen in `C:\ms\sl\shortcuts.json`. Existiert eine Verknüpfung schon **und
steht sie in dieser Liste**, wird sie **überschrieben**, nicht daneben neu angelegt – ein
zweiter Lauf von `install.cmd` ändert also nichts. Eine **fremde** Verknüpfung gleichen
Namens (z. B. ein „4diac IDE.lnk“ einer privat installierten IDE) bleibt unangetastet;
der Installer nimmt dann einen anderen festen Namen mit dem Zusatz „(Schule)“, z. B.
„4diac IDE (Schule).lnk“, und merkt sich diesen in der Liste. Aus der Liste entfernt er
Verknüpfungen zu Trainings, die es nicht mehr gibt, und `--uninstall` löscht genau
diese Verknüpfungen wieder (keine fremden). Durch
`-data` öffnet jede **Trainings**-Verknüpfung direkt den richtigen Workspace, ohne
Workspace-Auswahl; nur die allgemeine „4diac IDE“ zeigt bewusst die Auswahl.

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
1. `4diac_training1_empty` mit dem Tag aus dem Manifest nach `C:\ms\sl\prj\Maehwerk\`
   klonen, Arbeits-Branch `arbeit` anlegen.
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

Zusätzlich legt jedes Update vor dem Zurücksetzen einen **Sicherungs-Branch** an – ein
unsichtbares Netz für alles, was die `.SUB`-Kopie nicht abdeckt (geänderte `.fbt`, `.sys`,
`.gcf`, gelöschte Übungen, lokale Commits). Der Schüler sieht davon nichts; der Lehrer
holt im Notfall jede Datei zurück:
`git checkout sicherung_20261108_153012 -- test_AX\MeinBaustein.fbt`.
Eine vom Schüler **gelöschte** Datei steht im Sicherungs-Commit nicht mehr drin; sie
kommt aus dem letzten Commit, der sie noch enthält:
`git log -1 --format=%H sicherung_20261108_153012 -- test_AX\Uebung2.SUB` liefert den
Commit, der sie gelöscht hat, dann `git checkout <commit>^ -- test_AX\Uebung2.SUB`.

1. **IDE geschlossen?** Prüfung wie in 2.5 („IDE geöffnet?“); ist der Workspace noch
   geöffnet, Abbruch mit Hinweis „Bitte 4diac IDE schließen“.
2. **Zuerst holen:** `git fetch --tags origin` – ändert nichts an den Dateien des
   Schülers. Dann den Tag `<ref>` aus dem Manifest auf einen Commit auflösen
   (`git rev-parse --verify refs/tags/<ref>^{commit}`). Ergebnis = **ZIEL**. Nicht
   auflösbar → Abbruch, nichts verändert. (Steht im Manifest ausnahmsweise ein Branch,
   gilt `origin/<ref>`.)
3. **Sicherungs-Branch:** `git stash create` erzeugt einen Commit mit allen Änderungen an
   versionierten Dateien (inkl. Löschungen), **ohne** Arbeitsverzeichnis oder Index
   anzufassen; ohne Änderungen gilt `HEAD`. Darauf
   `git branch sicherung_<JJJJMMTT>_<hhmmss> <commit>`. Lokale Commits des Schülers sind
   damit ebenfalls erreichbar. Ist `HEAD` = ZIEL und nichts geändert, entfällt der Branch
   (keine leeren Sicherungen). Autor per `-c user.name=TrainingsInstaller
   -c user.email=installer@ms-sl.invalid`, falls Git noch keine Identität hat.
4. **Veränderte `.SUB` finden:** `git diff --name-status --no-renames
   ZIEL...<sicherung>` – nur Dateien, die **der Schüler** gegenüber dem gemeinsamen Stand
   verändert, neu committet oder gelöscht hat (Änderungen nur auf Schulseite zählen
   nicht), Endung `.SUB`/`.sub`. Status `A`/`M` → wird in Schritt 5 gesichert. Status `D`
   (gelöscht) → nicht kopiert (es gibt nichts zu kopieren), aber im Bericht genannt; der
   Lehrer holt sie bei Bedarf aus dem Commit davor (siehe oben).
   Ist der Schüler auf einem anderen Branch als `arbeit` und hat der lokale Branch
   `arbeit` Commits, die weder in der Sicherung noch in ZIEL stecken, wird auch dessen
   Stand gesichert: `git branch sicherung_<JJJJMMTT>_<hhmmss>_arbeit arbeit` – Schritt 7
   setzt `arbeit` sonst zurück.
5. **Sicherung schreiben – vor dem Zurücksetzen:** Jede gefundene `.SUB` als
   `<Name>_sicherung_<JJJJMMTT>_<hhmmss>.SUB` in denselben Ordner schreiben (Endung in
   der Schreibweise des Originals) und dabei **in der Datei den Typnamen mit
   umbenennen**: `Name`-Attribut des Wurzelelements `<SubAppType Name="…">` = neuer
   Dateiname ohne Endung, sonst gäbe es in 4diac zwei Typen mit demselben Namen. Nur
   dieses Attribut wird ersetzt, Kodierung und Formatierung bleiben unverändert. Geprüft
   an `ChainOfActionsDemo.sub` aus Training 1: Der Typname steht nur dort. Existiert der
   Dateiname schon, `_2`, `_3` … anhängen.
   Die Sicherungen sind **nicht versioniert**, daher lässt `git reset --hard` sie liegen.
   Bricht das Update danach ab, ist nichts verloren – kein Zwischenordner in
   `downloads\` nötig.
   Verweist eine gesicherte `.SUB` auf eine andere, ebenfalls gesicherte `.SUB`, zeigt
   der Verweis weiter auf das Original → **Warnung** im Bericht (selten; wird nicht
   automatisch umgeschrieben).
6. **Eigene Änderungen verwerfen:** `git reset --hard` (auf den aktuellen `HEAD`) – die
   Änderungen an versionierten Dateien stecken ja im Sicherungs-Branch. Unversionierte
   Dateien bleiben dabei liegen.
7. **Original aktualisieren – ohne `-f`:** `git checkout -B arbeit ZIEL` (auch wenn der
   Schüler auf einem anderen Branch oder im *detached HEAD* war; der Arbeits-Branch steht
   danach auf dem neuen Tag). Ohne `-f` **bricht Git ab**, wenn eine eigene,
   unversionierte Datei des Schülers im Weg wäre – auch wenn eine Datei dort liegt, wo
   ZIEL einen Ordner anlegt, oder umgekehrt – und nennt die betroffenen Pfade. Der
   Installer benennt genau diese zu `…_sicherung_<JJJJMMTT>_<hhmmss>.<Endung>` um (bei
   `.SUB` mit Typnamen wie in Schritt 5) und versucht es erneut; klappt es dann noch
   nicht → Abbruch mit Meldung, nichts weiter verändert.
   **Kein `git clean`:** Neue Dateien, die der Schüler selbst angelegt hat, bleiben
   unangetastet.
   Grenze: Dateien, die per `.gitignore` ausgeschlossen sind (z. B. `.metadata`), behandelt
   Git als entbehrlich und überschreibt sie ohne Abbruch, falls ZIEL denselben Pfad
   mitbringt. Das Schul-Repo bringt solche Pfade nie mit (`.metadata` ist nie
   versioniert, siehe 2.5); daher kein eigener Schutz.
8. **Bericht** (auch: gelöschte `.SUB`, umbenannte Dateien im Weg, Warnungen):
   „Training 1 aktualisiert. Deine geänderten Übungen wurden gesichert:
   test_AX/Uebung1_sicherung_20261108_153012.SUB … Vollständige Sicherung:
   Branch sicherung_20261108_153012.“

Sichtbar gesichert werden nur die `.SUB`. Änderungen an anderen versionierten Dateien
(z. B. `.sys`, `.fbt`, `.gcf`) verschwinden aus dem Projekt, sind aber über den
Sicherungs-Branch wiederherstellbar.

Die Sicherungsdateien sind nicht versioniert. Beim nächsten `--update` werden Dateien
`*_sicherung_*.SUB` daher nicht erneut gesichert, sondern einfach liegen gelassen.

Sicherungs-Branches sammeln sich an (je Update einer, praktisch ohne Speicherbedarf).
Sie werden **nie gelöscht** – auch nicht von `--cleanup`: Sie sind das einzige Netz für
überschriebene `.fbt`, `.sys`, `.gcf` und lokale Commits.

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
      `4diac-ide` umbenennen,
   5. Workspace-Liste für die allgemeine „4diac IDE“ neu schreiben
      (`configuration\.settings\org.eclipse.ui.ide.prefs`, siehe 2.5) – sie lag im
      alten Ordner.

   Bricht unterwegs etwas ab (z. B. Internet weg), bleibt die alte IDE funktionsfähig.
3. **`.metadata` in allen Workspaces unter `C:\ms\sl\prj\` löschen** – nur bei einem
   Versionswechsel. Damit gibt es keine Probleme mit
   veralteten Zwischenspeichern/Typindizes der alten Version. Verloren gehen nur
   IDE-weite Einstellungen (Window → Preferences) und das Fensterlayout; die Projekte
   holt das Auto-Import-Plugin beim nächsten Start zurück, projektspezifische
   Einstellungen liegen im Projekt und bleiben erhalten.

Die Verknüpfungen zeigen weiter auf `tools\4diac-ide\4diac-ide.exe` und bleiben
unverändert. Die alte IDE-ZIP in `downloads\` wird nach erfolgreichem Update gelöscht
(siehe „Aufräumen“).

#### Aufräumen (`--cleanup`)

**Automatisch** am Ende jedes erfolgreichen Laufs: Dateien in `downloads\`, die im
aktuellen Manifest nicht mehr vorkommen (alte IDE-ZIP ca. 300 MB, alte Git-/Python-
Pakete), werden gelöscht. Was das Manifest noch nennt, bleibt als Cache liegen.

**Auf Wunsch** mit `install.cmd --cleanup` bzw. Knopf „Aufräumen“ in der GUI, zusätzlich:
- **Logs** in `C:\ms\sl\logs\` älter als 90 Tage löschen.
- Vorher wird aufgelistet, was gelöscht wird (GUI: Liste mit „Löschen“/„Abbrechen“;
  headless: Liste im Bericht, gelöscht wird ohne Rückfrage, `--check` zeigt nur an).

Nie angefasst werden Projektdateien, die `.SUB`-Sicherungen (`*_sicherung_*.SUB`), die
**Sicherungs-Branches** und der Branch `arbeit`.

### 2.7 Firmware und ELF-Bibliotheken – immer synchron

**Grundregel:** Der Installer lädt genau **eine** Firmware-Fassung. Alle Trainings-Repos
im Manifest müssen die dazu passenden ELF-Bibliotheken enthalten. Firmware und ELFs
werden nur **gemeinsam** gewechselt.

**Was ist was:**
- **Firmware** = logiBUS-Build (FORTE-Kern, ISOBUS-Stack, Treiber, ELF-Lader), je
  Board-Typ (Target) eine Datei. Sie wird auf das Gerät gespielt.
- **ELF-Bibliotheken** = je 4diac-Bibliothek eine Datei, liegen **im Trainings-Repo**
  unter `Ventilsteuerung/4diacIDE-workspace/.lib/<Lib>-<Ver>/elf/<arch>/`, je für
  `riscv32` (ESP32-P4, ESP32-S31) und `xtensa` (ESP32-S3). Sie werden nicht geflasht,
  sondern von den Deploy-/Preload-Skripten des Repos nach `/data/elf-libs/` auf das
  Gerät geladen.
- **Wann passt beides?** Nur wenn Firmware und ELFs aus **demselben Build-Stand**
  stammen. Die ABI-Nummer (`forte_abi`, z. B. 6 bei `v0.28m`, 7 ab `v0.28p`; steht in jeder ELF als
  `ELFLIB:<name>:<version>:<forte_abi>:<arch>`) ist notwendig, aber nicht hinreichend:
  Braucht eine neuere Bibliothek eine Funktion, die erst eine neuere Firmware mitbringt,
  fällt das erst beim Laden auf dem Gerät auf (Beispiel: ELF aus `v0.28k` lädt nur mit
  Firmware b-178).

**Quelle – am training1-Release:** Die Firmware hängt als Assets an **demselben**
GitHub-Release von `4diac_training1`, dessen Tag auch im Manifest steht. Ein Tag = ELFs
im Repo + Firmware im Release, beides kann nicht auseinanderlaufen. Hochgeladen wird mit
`internal-scripts/release_firmware.py` im training1-Repo (berechnet SHA256, schreibt
`firmware.json` und `SHA256SUMS`, lädt hoch und schreibt den Abschnitt „Runtime“ der
Release-Notes: `release_firmware.py --tag <tag> --build <build> --upload --notes`).
Einzeldateien statt ZIP: Wer im Browser lädt, braucht nur `Application_<Board>.bin`.

**Beispiel** (Stand `v0.28m`, wird hier nicht nachgezogen – der gültige Stand steht im
`manifest.json` des Installer-Releases, siehe 3.2):

| | |
|---|---|
| Release  | `4diac_training1` **v0.28m** |
| Build    | `v0.27-alpha-b-190-ge9b19d5f` (LOGIBUS `e9b19d5f`, FORTE `acef1b32`), `forte_abi` 6 |
| Beschreibung | `firmware.json` – <https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_training1/releases/download/v0.28m/firmware.json> |
| SHA256 `firmware.json` | `54ce88c5f4ab14215d4083b799090c2eba4035246d8731a42cecfa9146458fa1` (= GitHub-Digest) |
| Dateien  | je Target `Application_<Target>.bin` und `merged-flash_<Target>.bin`, 14 Targets = 28 Dateien, zusammen ca. **68 MB** |
| Lizenz   | eigene Firmware (Meisterschule) |

`firmware.json` (Auszug, Beispiel `v0.28m`):

```json
{
  "build": "v0.27-alpha-b-190-ge9b19d5f",
  "logibus_commit": "e9b19d5fe1747da4ecaf379f6259531f67b21213",
  "forte_commit": "acef1b326660861bf11cfd9b84c8377d08ac2ed2",
  "training1": "v0.28m",
  "forte_abi": 6,
  "targets": {
    "ESP32P4_NodeISO20": {
      "arch": "riscv32",
      "application":  { "file": "Application_ESP32P4_NodeISO20.bin",  "size": 2223008, "sha256": "6eb1bcdb…" },
      "merged_flash": { "file": "merged-flash_ESP32P4_NodeISO20.bin", "size": 2354080, "sha256": "75cd6efb…" }
    }
  }
}
```

Das Manifest pinnt nur die `firmware.json` (URL + SHA256); die SHA256 der 28 `.bin`
stehen darin. Damit ist jede Datei über die Prüfsummenkette abgesichert.

**Targets** (Schulung nutzt quasi alle, daher werden **alle** geladen):

| arch | Targets (Name wie im Dateinamen) |
|---|---|
| riscv32 | `ESP32P4_NodeISO20`, `ESP32P4_NodeISO20_V3`, `ESP32S31_Trainer20` |
| xtensa  | `ESP32S3_deca_out`, `ESP32S3_dual_can`, `ESP32S3_dual_io`, `ESP32S3_dual_out`, `ESP32S3_octa_out`, `HutschienenmopedXL`, `HutschienenmopedXL26`, `HutschienenmopedXL_1ETH`, `HutschienenmopedXL_2ETH`, `M5_CoreS3_1ETH`, `lilygo_T_Connect_Pro` |

Die Target-Liste kommt aus `firmware.json`, nicht aus dem Code des Installers.

**Ablage auf dem PC:** `C:\ms\sl\firmware\<Target>\` mit beiden Dateien, dazu
`C:\ms\sl\firmware\firmware.json` als Versionsmerker (statt `.ms-sl-version`).

**Synchron-Prüfung durch den Installer** (vor jedem Download/Update, sonst Abbruch):
- `firmware.json` → `training1` muss gleich dem `ref` von `4diac_training1` im Manifest
  sein; `4diac_training1_empty` hat denselben Tag (siehe 3.2).
- Jedes weitere Trainings-Repo muss denselben Tag tragen (`.lib`-Sync, siehe 3.2).
- Optional (`--check`): für jede Bibliothek aus `LIB_VERSIONS`
  (`Ventilsteuerung/scripts_central/elf_libs_manifest_lib.py`) den `ELFLIB`-String der
  ELF lesen und `forte_abi`/`arch` mit `firmware.json` vergleichen. **Nicht** alle Dateien
  unter `.lib` auswerten: dort liegen auch alte, ungenutzte ELF-Versionen (teils ohne
  `ELFLIB`).

**Firmware wechseln** (Manifest zeigt auf ein neues Release):
1. Neue `firmware.json` laden und prüfen, dann alle `.bin` nach
   `C:\ms\sl\firmware.neu\<Target>\` laden und je SHA256 prüfen.
2. Trainings-Repos auf den neuen Tag bringen – genau wie `--update` (2.6, inkl.
   Sicherungs-Branch und `.SUB`-Sicherung). Damit kommen die neuen ELFs.
3. Erst wenn 1 **und** 2 geklappt haben: **alte Firmware löschen** (`firmware\`) und
   `firmware.neu` in `firmware` umbenennen. Bricht 2 ab (z. B. IDE offen), bleibt die
   alte Firmware liegen – sie passt dann weiter zu den alten ELFs.
4. Bericht: „Neue Firmware b-… – Geräte bitte aktualisieren (siehe unten)“.

Es gibt also nie zwei Firmware-Fassungen nebeneinander und nie neue ELFs mit alter
Firmware (oder umgekehrt).

**Auf das Gerät bringen – macht der Installer nicht:**
- **Update** (Gerät hat schon eine aktuelle logiBUS-Firmware): `Application_<Target>.bin`
  im Browser über den Web-File-Server des Geräts hochladen und „update“ wählen (OTA).
  Kein Tool, kein Treiber, kein Admin – das kann der Schüler.
- **Erst-Flashen** neuer Boards bzw. Boards mit alter Partitionstabelle (vor Oktober
  2026): `merged-flash_<Target>.bin` per USB mit `esptool` ab Adresse `0x0`, danach
  `/data` einmal formatieren (Button im File-Server). Das macht der **Trainer**;
  `esptool` installiert der Installer nicht (siehe 6).

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
1. **Bootstrap** – `install.ps1` (Windows PowerShell 5.1, auf jedem Windows vorhanden).
   Lädt **nur Python** – so wenig PowerShell wie möglich:
   - legt `C:\ms\sl\` an, liest den Python-Eintrag aus `manifest.json` mit
     `ConvertFrom-Json` (bordeigen, keine Zusatzmodule)
   - **Python schon da?** Steht in `tools\python\.ms-sl-version` die Version aus dem
     Manifest → nichts laden (zweiter Start lädt Python nicht nochmal). Fehlt die Datei
     oder steht eine andere Version darin → Python laden: `downloads\<datei>.tmp`, SHA256
     prüfen (`Get-FileHash`), alten `tools\python` löschen, entpacken, Funktionsprobe
     (`python.exe -m pip --version`), erst dann `.ms-sl-version` schreiben. So kommt auch
     eine im Manifest erhöhte Python-Version an.
   - TLS 1.2 für den Download ausdrücklich einschalten
     (`[Net.ServicePointManager]::SecurityProtocol`) – Windows PowerShell 5.1 nimmt sonst
     je nach System ältere Protokolle.
   - startet den Hauptinstaller und reicht alle Argumente durch:
     - **ohne Argumente** (Doppelklick) → GUI: `pythonw.exe -m trainings_installer`
       (`pythonw` = kein Konsolenfenster)
     - **mit Argumenten** (`--update`, `--new-project <Name>`, `--check`, `--uninstall`,
       `--headless`) → ohne Fenster auf der Konsole: `python.exe -m trainings_installer …`
2. **Hauptinstaller** – Python-Paket (`trainings_installer/`), erledigt **alles andere**:
   Git, 4diac IDE (inkl. `typelibrary` löschen, Auto-Import-Plugin), Repos klonen
   (Tag, Branch `arbeit`), Workspace-Liste, PATH, Verknüpfungen, Bericht. Herunterladen,
   SHA256-Prüfung und Entpacken gibt es damit nur **einmal** (in Python).

**Aufbau des Hauptinstallers:**
- **Kern** (`core`) ohne jede Oberfläche: alle Schritte aus 4, 2.5 und 2.6. Meldet
  Fortschritt und Ergebnisse über Rückruf-Funktionen.
- **GUI** (`gui`) mit **`tkinter`** – ist im Python-ZIP bereits enthalten (siehe 2.4),
  also kein `pip install`, nichts Zusätzliches aus dem Netz. Knöpfe *Installieren*,
  *Trainings aktualisieren*, *Neues Projekt* (mit Namensfeld) und *Deinstallieren*,
  Fortschrittsbalken, Bericht. Der Kern läuft in einem eigenen Thread, damit das Fenster
  während der Downloads nicht einfriert; Meldungen gehen über eine Queue an die GUI.
  Gerade beim Update zeigt die GUI „IDE bitte schließen“ und die gesicherten `.SUB`.
- **Konsole** (`cli`, headless) – dieselben Funktionen ohne Fenster. Für das
  Lehrer-Notebook, für Tests auf einem frischen Benutzerkonto und für automatische Tests.
- GUI und Konsole sind nur zwei Oberflächen auf denselben Kern – keine Logik doppelt.
- **Log:** immer `C:\ms\sl\logs\install_<JJJJMMTT>_<hhmmss>.log` – wichtig, weil
  `pythonw` keine Konsole hat. Fehler zusätzlich in der GUI mit Hinweis auf die Logdatei.

```
install.cmd → install.ps1:  Python da + richtige Version?  nein → laden, SHA256, entpacken
                            → pythonw -m trainings_installer          (GUI, Doppelklick)
                            → python  -m trainings_installer --…      (headless)
Python-Kern:  Git → 4diac IDE (+ typelibrary löschen, Plugin) → Repos (Tag, Branch arbeit)
              → Workspace-Liste → PATH → Verknüpfungen → Bericht
```

Nicht verwendet: `winget`/Chocolatey/Scoop (Versionen nicht festdübelbar bzw. eigene
Installation nötig) und „alles in PowerShell“ (Git-Logik aus 2.6 und GUI wären in
PowerShell 5.1 deutlich mühsamer).

### 3.2 Manifest-getrieben

Was installiert wird, steht **nicht im Code**, sondern in `manifest.json`.
**JSON statt TOML**, weil der Bootstrap in Windows PowerShell 5.1 läuft: Die kann JSON
bordeigen lesen (`ConvertFrom-Json`), TOML nicht – und Python ist zu diesem Zeitpunkt
noch nicht installiert. Der Python-Hauptinstaller liest dieselbe Datei mit `json`.

> **Alle Versionen, Tags, URLs und SHA256 in diesem Konzept sind Beispiele** (Stand der
> jeweiligen Entscheidung). **Verbindlich ist nur das `manifest.json` im jeweiligen
> Installer-Release** (siehe 3.3). Ein neuer training1-Tag ändert das Manifest, nicht
> dieses Konzept.

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
  "firmware": {
    "build": "v0.27-alpha-b-228-g…",
    "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_training1/releases/download/v0.28q/firmware.json",
    "sha256": "<SHA256 der firmware.json>",
    "target": "firmware"
  },
  "repos": {
    "4diac_training1": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_training1.git",
      "ref": "v0.28q",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Training 1",
      "tool_shortcuts": [
        {
          "name": "logiBUS ELF-Verwaltung",
          "script": "Ventilsteuerung/scripts_central/elf_manager_gui.py",
          "workdir": "Ventilsteuerung/scripts_central"
        }
      ]
    },
    "4diac_training1_empty": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_training1_empty.git",
      "ref": "v0.28q",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Training 1 (leer)",
      "template_for_new_projects": true
    },
    "4diac-SlurryTanker_AX-sample": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-SlurryTanker_AX-sample.git",
      "ref": "v0.28q",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Slurry Tanker AX"
    },
    "4diac-SlurryTanker-sample": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac-SlurryTanker-sample.git",
      "ref": "v0.28q",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Slurry Tanker"
    },
    "4diac_EasyExampleCounter": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_EasyExampleCounter.git",
      "ref": "v0.28q",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Easy Example Counter"
    },
    "4diac_modbus_tcp_sample": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_modbus_tcp_sample.git",
      "ref": "v0.28q",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Modbus TCP"
    },
    "4diac_modbus_rtu_sample": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_modbus_rtu_sample.git",
      "ref": "v0.28q",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Modbus RTU"
    },
    "4diac_empty1": {
      "url": "https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/4diac_empty1.git",
      "ref": "v0.28q",
      "workspace": "Ventilsteuerung/4diacIDE-workspace",
      "shortcut": "4diac – Empty 1"
    }
  }
}
```

Schlüssel `fordiac_ide`: „fordiac“ ist der 4diac-interne Name (`org.eclipse.fordiac`)
und vermeidet einen Schlüssel mit führender Ziffer.

`repos`: Der Schlüssel ist der Repo-Name und zugleich der Ordner unter `C:\ms\sl\prj\`.
`ref` ist ein **Tag** (festgedübelt wie IDE, Git und Python): Jeder Schüler bekommt genau
den freigegebenen Stand, nie einen halbfertigen `main`. Neuer Stand = neuen Tag im
Manifest eintragen. Geklont wird mit `git clone --branch <tag>`; danach legt der
Installer den lokalen Arbeits-Branch **`arbeit`** an (`git switch -c arbeit`), damit
Commits des Schülers (z. B. per EGit) nicht auf einem *detached HEAD* landen.
`4diac_training1` und `4diac_training1_empty` bekommen immer **denselben** Tag (beide
werden gemeinsam released; `_empty` wird per CI aus training1 synchronisiert).
Alle Tags müssen zur Firmware passen (siehe 2.7). Dafür gibt es den **`.lib`-Sync**:
Bei jedem training1-Release ersetzt ein CI-Workflow in training1 (`sync_lib.py`) in jedem
4diac-Projekt der Org den Ordner `<workspace>/.lib` (samt ELFs) durch den Stand des
Tags, je Repo als PR; nach dem Merge bekommt das Repo **denselben Tag wie training1**.
Damit steht im Manifest bei **allen** Repos derselbe Tag.

**Aufgenommen** (Stand 2026-11-26, alle auf IDE 3.x mit `.lib` im Workspace, Branch
`main`, Workspace `Ventilsteuerung/4diacIDE-workspace`, Projekt `test`, alle im
`.lib`-Sync): `4diac_training1`, `4diac_training1_empty`, `4diac-SlurryTanker_AX-sample`,
`4diac-SlurryTanker-sample`, `4diac_EasyExampleCounter`, `4diac_modbus_tcp_sample`,
`4diac_modbus_rtu_sample`, `4diac_empty1`. Die beiden SlurryTanker und `modbus_rtu` sind
ab dem training1-Release `v0.28q` im Sync (training1 PR #422).

**Noch nicht aufgenommen** (nicht umgestellt): `4diac-frequency-converter-sample-APIXON`
(neuer Stil nur auf `feature/fu-demo`), `4diac-SlurryTanker-sample-Hutschienenmoped`,
`4diac_template`. Sie kommen ins Manifest, sobald sie umgestellt sind und im Sync laufen.

Ab `v0.28q` enthält jedes Repo auch `Ventilsteuerung/scripts_central` (Preload,
Deploy-Basis, `elf_manager_gui.py`) sowie `test/scripts/RunSkript_PreloadELF.bat`,
`RunSkript_ElfManager.bat` und passende Launches in `test/Launches` – die ELF-Verwaltung
ist damit **in jedem Projekt aus der IDE heraus** startbar. Auf dem Desktop gibt es
trotzdem nur **eine** Verknüpfung „logiBUS ELF-Verwaltung“ (aus training1): Alle Repos
tragen denselben Tag, ihre ELFs sind identisch – Verknüpfungen je Projekt wären Dubletten.

`firmware`: zeigt auf die `firmware.json` am training1-Release (siehe 2.7); `target`
ist der Ordner unter `C:\ms\sl\`.
`workspace` ist relativ zum Repo-Ordner, `shortcut` der Name der Verknüpfung.
`template_for_new_projects` markiert das Repo, das `--new-project` kopiert.
`tool_shortcuts`: Python-Werkzeuge aus dem Repo, die eine eigene Verknüpfung bekommen
(gestartet mit `pythonw.exe`, Pfade relativ zum Repo-Ordner, siehe 2.5).

Vorteile: neue Schulung = neues Manifest; Versionen werden festgenagelt; Prüfsummen
sichern die Downloads ab.

❓ Ein Manifest pro Schulung (Profile, z. B. `--profile grundkurs`)?

### 3.3 Verteilung, Manifest und Selbst-Update

**Der Installer ist ein GitHub-Release** dieses Repos (`TrainingsInstaller`), Tag z. B.
`v1.0.0`. Einziges Asset ist **`TrainingsInstaller.zip`** – immer derselbe Dateiname, die
Version steht im Tag und in `version.txt` im ZIP. Dadurch gibt es einen festen Link, der
immer auf die neueste Version zeigt:

<https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/TrainingsInstaller/releases/latest/download/TrainingsInstaller.zip>

Inhalt des ZIP:

```
TrainingsInstaller\
├── install.cmd             ← Doppelklick
├── install.ps1             ← Bootstrap (lädt Python, siehe 3.1)
├── trainings_installer\    ← Python-Paket (Kern, GUI, Konsole)
├── manifest.json           ← alle Versionen + SHA256 (siehe 3.2)
├── version.txt             ← Installer-Version, z. B. 1.0.0
└── LIESMICH.txt            ← Kurzanleitung für Teilnehmer
```

**Verteilung an Teilnehmer:** Link (Mail, Moodle, QR-Code im Kursraum) → ZIP laden →
entpacken → `install.cmd` doppelklicken. Auf dem **USB-Stick** liegt dasselbe ZIP bzw.
derselbe entpackte Ordner – kein Sonderweg. **Kein Einzeiler** (`irm … | iex` führt Code
ungeprüft aus dem Netz aus).

Beim ersten Start **kopiert sich der Installer nach `C:\ms\sl\installer\`** und legt im
Startmenü die Verknüpfung **„4diac Trainings-Installer“** (GUI) an. Danach braucht man das
heruntergeladene ZIP nicht mehr; Update, Neues Projekt usw. laufen über diese
Verknüpfung.

⚠ Zu testen: Dateien aus einem heruntergeladenen ZIP tragen die Internet-Markierung
(*Mark of the Web*). `-ExecutionPolicy Bypass` (siehe 3.1) deckt das für `install.ps1` ab;
ob Windows/SmartScreen beim Doppelklick auf `install.cmd` trotzdem nachfragt, prüfen wir auf
einem frischen Schul-PC. Falls ja: Hinweis in `LIESMICH.txt` („ZIP vor dem Entpacken:
Rechtsklick → Eigenschaften → Zulassen“), und `install.ps1` entfernt die Markierung
danach bei seinen eigenen Dateien (`Unblock-File`).

**Woher kommt das Manifest?** **Aus dem ZIP** (lokal neben `install.cmd`), nicht per URL.
Installer-Version und Manifest gehören fest zusammen: **eine Installer-Version = genau
ein Satz Versionen** (IDE, Git, Python, Plugin, Repo-Tags, Firmware). Neuer Stand (z. B.
neuer training1-Tag mit neuer Firmware) = neues Manifest = **neues Installer-Release**.
So ist jederzeit nachvollziehbar, welcher Teilnehmer welchen Stand hat (`version.txt` im
Bericht und im Log).

**Selbst-Update:**
1. Bei jedem Start (nur wenn online) fragt der Installer
   `GET https://api.github.com/repos/Meisterschulen-am-Ostbahnhof-Munchen/TrainingsInstaller/releases/latest`
   ab – ohne Login. Offline oder Fehler → einfach weiter mit der vorhandenen Version.
2. Ist der Tag neuer als `version.txt`:
   - **GUI:** „Neue Version x.y.z verfügbar – jetzt aktualisieren?“ (Ja/Nein)
   - **headless:** nur Hinweis im Bericht; aktualisiert wird mit `--self-update`.
3. Aktualisieren: `TrainingsInstaller.zip` laden, SHA256 gegen den Digest des Assets aus
   der GitHub-API prüfen, nach `C:\ms\sl\installer.neu\` entpacken, erst dann
   `installer\` ersetzen und den Installer **neu starten**. Bricht etwas ab, bleibt die
   alte Version.
4. Nach dem Neustart gilt das **neue Manifest** – die eigentlichen Updates (IDE, Repos,
   Firmware) laufen dann wie in 2.6/2.7.

Der laufende Installer ersetzt sich nicht selbst, während er läuft: Das Austauschen von
`installer\` erledigt `install.ps1` beim Neustart (Python ist dann beendet, keine
gesperrten Dateien).

### 3.4 Verzeichnisstruktur auf dem Ziel-PC (Vorschlag)

```
C:\ms\sl\
├── tools\
│   ├── git\
│   ├── python\           ← mit .ms-sl-version (Prüfung durch install.ps1)
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
│   ├── 4diac-SlurryTanker-sample\
│   ├── 4diac_EasyExampleCounter\
│   ├── 4diac_modbus_tcp_sample\
│   ├── 4diac_modbus_rtu_sample\
│   ├── 4diac_empty1\
│   └── <eigenes Projekt>\  ← per --new-project aus _empty
├── installer\            ← Kopie des Installers (siehe 3.3), mit version.txt
├── firmware\             ← siehe 2.7
│   ├── firmware.json     ← Versionsmerker
│   ├── ESP32S3_dual_can\ ← Application_….bin + merged-flash_….bin
│   └── …                 ← je Target ein Ordner (14)
├── downloads\            ← Cache, ermöglicht Offline-Wiederholung
└── logs\                 ← install_<JJJJMMTT>_<hhmmss>.log je Lauf
```

## 4. Ablauf

0. Bootstrap (`install.ps1`, siehe 3.1): Python prüfen bzw. laden, dann Hauptinstaller
   starten – GUI oder headless. Alle folgenden Schritte macht der Python-Kern.
1. Umgebungsprüfung (OS, Architektur, freier Speicher, Internet)
2. Selbst-Update prüfen (siehe 3.3), dann Manifest aus dem Installer-Ordner laden
3. Für jede Komponente: *bereits in der Manifest-Version vorhanden?* → überspringen
   (4diac IDE: Vergleich mit `.ms-sl-version`; bei abweichender Version Update nach 2.6
   inkl. Löschen von `.metadata`), sonst
   herunterladen nach `downloads\<datei>.tmp` → SHA256 prüfen → erst bei Übereinstimmung
   umbenennen und installieren/entpacken (fehlerhafte Downloads werden verworfen);
   bei der 4diac IDE danach **`typelibrary` löschen** (Pflicht, siehe 2.1);
   Auto-Import-Plugin nach `tools\4diac-ide\dropins\` kopieren,
   `ms-sl-customization.ini` schreiben (siehe 2.5)
4. Repositories nach `C:\ms\sl\prj\<repo>` klonen bzw. aktualisieren
4a. Firmware: Synchron-Prüfung, alle Targets nach `C:\ms\sl\firmware\` laden bzw. bei
   neuem Build gemeinsam mit den Repos wechseln (siehe 2.7)
5. Verknüpfung pro Training anlegen (`-data <workspace>`, siehe 2.5) – den Import der
   Projekte übernimmt das Plugin beim ersten Start der IDE
6. Abschlussbericht: was installiert, was übersprungen, was fehlgeschlagen

## 5. Weitere Funktionen

- [ ] `--new-project <Name>` – neues eigenes Projekt aus `4diac_training1_empty` (siehe 2.5)
- [ ] `--check` – nur prüfen, nichts verändern
- [ ] `--update [<repo>]` – Trainings aktualisieren, veränderte `.SUB` werden umbenannt gesichert
  (siehe 2.6; ersetzt das frühere `--reset-training`)
- [ ] `--cleanup` – alte Logs löschen; Sicherungs-Branches bleiben (siehe 2.6)
- [ ] `--uninstall` – alles wieder entfernen
- [ ] Selbst-Update beim Start bzw. `--self-update` (siehe 3.3)

## 6. Nicht-Ziele

- Kein allgemeiner Paketmanager
- Keine Installation von Treibern/Hardware-Tools (auch keine mit Admin-Pflicht)
- **Kein Flashen:** Der Installer legt die Firmware nur ab; `esptool` wird nicht
  installiert. Update per Browser (Schüler), Erst-Flashen per USB (Trainer), siehe 2.7.
- **ISO-Designer** (Jetter, ISOBUS-VT-Pools) wird **nicht** installiert – den lädt jeder
  Teilnehmer selbst herunter.

## 7. Offene Fragen und Entscheidungen

### Offen

1. **Ein Manifest oder Profile pro Schulung?** (z. B. `--profile grundkurs`, siehe 3.2)
2. **`--new-project`:** Push-Sperre über ungültige Push-URL so in Ordnung? (siehe 2.5;
   Namensprüfung ist festgelegt)

### Entschieden

- **Plattform:** Windows only (Schulvorgabe: macOS/Linux/ARM nicht zugelassen).
- **Admin-Rechte:** ohne Admin; PATH über Benutzer-PATH (2.2).
- **Versionen im Konzept:** nur Beispiele; verbindlich ist allein das `manifest.json` im
  Installer-Release (2026-11-26, siehe 3.2).
- **Lehrer-Notebook:** dienstlich verwaltet, keine Admin-Rechte, Ordner unter `C:\`
  anlegen ist erlaubt → gleicher Weg wie Schüler-Notebooks (2026-11-26).
- **Aufräumen:** unbenutzte Downloads (alte IDE-ZIP) automatisch löschen; `--cleanup`
  löscht Logs älter als 90 Tage. Sicherungs-Branches und `.SUB`-Sicherungen werden
  **nie** gelöscht (2026-11-26, siehe 2.6).
- **Offline:** Installation online; danach muss alles offline laufen.
- **4diac IDE:** 3.4.0 Milestone 2026-11-05_2214, Bezug über GitHub Release (2.1).
- **4diac FORTE:** wird **nicht** installiert (2026-11-13).
- **Ablauf/Architektur:** `install.ps1` lädt nur Python (zweiter Start: nur bei anderer
  Version), danach macht Python alles; GUI mit `tkinter`, auch headless (2026-11-25,
  siehe 3.1).
- **Firmware:** eine Fassung für alle 14 Targets, als Assets am training1-Release mit
  `firmware.json`; Firmware und ELFs immer gemeinsam wechseln; Installer flasht nicht
  (2026-11-25, siehe 2.7).
- **Verteilung, Manifest, Selbst-Update:** Installer als GitHub-Release
  (`TrainingsInstaller.zip`, fester „latest“-Link, auch für USB-Stick); kein Einzeiler;
  Manifest liegt im ZIP (eine Installer-Version = ein Satz Versionen); Selbst-Update über
  die GitHub-API mit Nachfrage in der GUI (2026-11-26, siehe 3.3).
- **`.lib`-Sync:** `.lib` samt ELFs per CI aus training1 in **alle** 4diac-Projekte der
  Org, gleicher Tag wie training1 (2026-11-25, siehe 3.2).
- **Trainings-Repos im Manifest:** training1, _empty, beide SlurryTanker,
  EasyExampleCounter, modbus_tcp, modbus_rtu, empty1; ELF-Verwaltung nur einmal auf dem
  Desktop, je Projekt über die Launches in der IDE (2026-11-26, siehe 3.2).
- **Trainings-Repos:** je Repo ein **Tag** statt `main`, lokaler Arbeits-Branch `arbeit`
  (2026-11-17, siehe 3.2).
- **Weitere Komponenten:** **keine** – kein VS Code, kein Wireshark, keine Treiber;
  ISO-Designer lädt jeder selbst (2026-11-13, siehe 6).
- **Verknüpfungen:** Desktop **unbedingt** (plus Startmenü): „4diac Projekte“
  (`C:\ms\sl\prj`), „4diac IDE“ mit Workspace-Auswahl, je Training eine
  IDE-Verknüpfung und „logiBUS ELF-Verwaltung“ (2026-11-26) (siehe 2.5).
