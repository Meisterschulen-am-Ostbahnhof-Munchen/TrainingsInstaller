# TrainingsInstaller

Trainings-Installer für Git, Python, 4diac IDE, training1 und weitere – alles nach
`C:\ms\sl`, ohne Administratorrechte, Versionen fest im `manifest.json`.
Konzept und Entscheidungen: [KONZEPT.md](KONZEPT.md).

## Aufbau

| Datei | Zweck |
|---|---|
| `install.cmd` | Doppelklick-Starter, ruft `install.ps1` auf |
| `Neues Projekt.cmd` | Doppelklick: neues eigenes Projekt, fragt nach dem Namen |
| `install.ps1` | Bootstrap (Windows PowerShell 5.1): lädt nur Python, startet dann den Hauptinstaller |
| `trainings_installer/` | Hauptinstaller in Python: Kern (`core`), GUI (`gui`, tkinter), Konsole (`cli`) |
| `manifest.json` | **verbindlicher** Stand: Versionen, URLs, SHA256, Repo-Tags, Firmware |
| `version.txt` | Installer-Version |
| `LIESMICH.txt` | Kurzanleitung für Teilnehmer |

## Aufruf

```
install.cmd                 GUI
install.cmd --headless      installieren ohne Fenster
install.cmd --check         nur prüfen
install.cmd --update [REPO] Trainings und eigene Projekte aktualisieren (geänderte .SUB
                            bzw. eigene Dateien bleiben, Sicherungs-Branch)
install.cmd --new-project Maehwerk   neues eigenes Projekt (Kopie der leeren Vorlage)
Neues Projekt.cmd           dasselbe per Doppelklick, fragt nur nach dem Namen
install.cmd --cleanup       alte Downloads und Logs > 90 Tage löschen (Sicherungen bleiben)
install.cmd --uninstall     alles entfernen; prj nur ohne Schülerarbeit
install.cmd --uninstall --mit-projekten   auch prj samt Schülerarbeit löschen
install.cmd --self-update   Installer auf das neueste GitHub-Release bringen
```

Beim Start fragt der Installer `releases/latest` ab (ohne Login, offline wird still
weitergemacht). Die GUI bietet eine neuere Version per Ja/Nein an und startet danach neu,
in der Konsole erscheint nur ein Hinweis.

## Manifest freigeben

Ein neues `manifest.json` (z. B. neuer training1-Tag) darf **nur** veröffentlicht werden,
wenn die Freigabe-Prüfung grün ist:

```
python tools/check_manifest.py          # Tags, .lib-Inhalt, Firmware, Erreichbarkeit
python tools/check_manifest.py --full   # zusätzlich Git, Python, IDE laden und SHA256 prüfen
```

Geprüft wird: alle Repos öffentlich und mit dem Tag aus dem Manifest, alle auf dem Tag
von `4diac_training1`, `.lib` in jedem Repo inhaltsgleich mit training1, `firmware.json`
(SHA256, Tag, Build, alle `.bin` am Release), `tool_shortcuts`-Skripte im Tag, alle URLs.
Hängt der `.lib`-Sync eines Repos, bleibt die Prüfung rot – dann erst den Sync-PR mergen
oder das Repo vorübergehend aus dem Manifest nehmen. In CI läuft die Prüfung bei jeder
Änderung an `manifest.json` (`.github/workflows/manifest-check.yml`).

## Installer veröffentlichen

1. `version.txt` erhöhen (bei neuem Manifest immer – eine Installer-Version = ein Satz
   Versionen), per PR nach `main`.
2. Auf `main` taggen (Git Bash):
   ```
   v="v$(cat version.txt)" && git tag "$v" && git push origin "$v"
   ```
3. `.github/workflows/release.yml` läuft dann:
   - Freigabe-Prüfung `check_manifest.py --full` und alle Tests – sonst **kein** Release;
   - `tools/build_release.py` baut `TrainingsInstaller.zip` (Tag muss zu `version.txt`
     passen) und die Release-Notes mit allen Versionen;
   - Probestart: ZIP entpacken, `install.cmd --help` (lädt Python, startet den Kern);
   - GitHub-Release mit `TrainingsInstaller.zip` als einzigem Asset.

Fester Link für Teilnehmer:
<https://github.com/Meisterschulen-am-Ostbahnhof-Munchen/TrainingsInstaller/releases/latest/download/TrainingsInstaller.zip>

Lokal bauen (ohne Veröffentlichen): `python tools/build_release.py` → `dist/`.

## Entwicklung

```
python -m unittest discover -s tests -v
```

Die Tests brauchen kein Netz und ändern nichts am System. Für einen Probelauf ohne
`C:\ms\sl` die Umgebungsvariable `MS_SL_ROOT` auf einen Testordner setzen – Benutzer-PATH
und Desktop-Verknüpfungen betrifft ein vollständiger Lauf trotzdem.
