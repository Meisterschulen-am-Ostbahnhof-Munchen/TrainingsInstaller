# TrainingsInstaller

Trainings-Installer für Git, Python, 4diac IDE, training1 und weitere – alles nach
`C:\ms\sl`, ohne Administratorrechte, Versionen fest im `manifest.json`.
Konzept und Entscheidungen: [KONZEPT.md](KONZEPT.md).

## Aufbau

| Datei | Zweck |
|---|---|
| `install.cmd` | Doppelklick-Starter, ruft `install.ps1` auf |
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
```

`--update`, `--new-project`, `--cleanup`, `--uninstall` und `--self-update` folgen.

## Entwicklung

```
python -m unittest discover -s tests -v
```

Die Tests brauchen kein Netz und ändern nichts am System. Für einen Probelauf ohne
`C:\ms\sl` die Umgebungsvariable `MS_SL_ROOT` auf einen Testordner setzen – Benutzer-PATH
und Desktop-Verknüpfungen betrifft ein vollständiger Lauf trotzdem.
