# Hardware-Bedarf

Gemessener Bedarf der Eclipse 4diac IDE für die Schulungen, damit wir sagen können,
welche Notebooks ausreichen.

Stand: 2026-11-08 – Messung auf einem Entwickler-PC, **nicht** auf einem Schüler-Notebook.

## Ergebnis in Kürze

- **8 GB RAM reichen.** Die IDE läuft mit Training 1 auch dann fehlerfrei, wenn Java auf
  2 GB begrenzt ist (so viel bekommt Java auf einem 8-GB-Notebook standardmäßig).
- **Speicherplatz:** ca. 0,7 GB für die IDE samt Download, dazu ca. 0,1 GB pro Training
  (Training 1). Bei 250 GB SSD (Schulvorgabe) kein Thema.
- **Der erste Start eines Trainings dauert am längsten** (Bibliotheken werden eingelesen),
  danach startet die IDE in ca. 20 s.
- Die Schulvorgaben ([Notebookanforderungen vom 16.07.2024](https://www.meisterschulen-muenchen.de/documents/meisterschulen/fachbereiche/it-admin/beiblatt_notebookanforderung.pdf))
  liegen darüber, für Feinwerk-/Landmaschinenmechanik/Metallbau sogar deutlich.

## Messaufbau

| | |
|---|---|
| IDE | Eclipse 4diac IDE 3.4.0 Milestone 2026-11-05_2214, Windows x86_64, `typelibrary` gelöscht |
| Java | in der IDE enthaltenes JRE (JustJ OpenJDK 25.0.4), G1 GC |
| Projekt | `4diac_training1` (Branch `main`), Workspace `Ventilsteuerung\4diacIDE-workspace`, 3 Projekte (`test_AX`, `test_B`, `test_VV`) mit allen Bibliotheken aus `.lib` |
| Rechner | Intel Core Ultra 7 265 (20 Threads), 191 GB RAM, SSD, Windows 11 |

Gemessen wurden:
- **Arbeitsspeicher des Prozesses** (Working Set) im Abstand von 5–10 s,
- **tatsächlich belegter Java-Heap** nach einer erzwungenen Garbage Collection
  (`jcmd <pid> GC.run`, dann `GC.heap_info`) – das ist der echte Bedarf,
- **Rechenzeit (CPU-Sekunden)** und Zeit, bis die IDE nichts mehr rechnet.

Wichtig: In `4diac-ide.ini` ist **keine** Obergrenze (`-Xmx`) gesetzt. Java nimmt sich dann
bis zu **einem Viertel des eingebauten RAM**. Auf dem Mess-PC mit 191 GB wären das ~48 GB –
Java räumt dann kaum auf und der Prozess wächst entsprechend. Deshalb wurde zusätzlich mit
`-Xmx2g` gemessen, was einem 8-GB-Notebook entspricht.

## Messwerte

### Arbeitsspeicher

| Situation | Prozess (Working Set) | Java-Heap belegt nach GC |
|---|---|---|
| Leerer Workspace, IDE gestartet | ca. 410 MB | – |
| Training 1, erster Start, **ohne** Begrenzung (Heap max. ~48 GB) | bis 5,6 GB | ca. 940 MB |
| Training 1, erster Start, **`-Xmx2g`** (wie 8-GB-Notebook) | ca. 2,5 GB | ca. 790 MB |
| Training 1, zweiter Start, `-Xmx2g` | ca. 330 MB | – |

Fazit: Der eigentliche Bedarf liegt **unter 1 GB Heap**. Was darüber hinausgeht, nimmt sich
Java nur, weil es da ist. Mit 2 GB Heap traten keine Fehler auf (kein `OutOfMemoryError`
im Log `.metadata\.log`).

### Zeit

| Situation | Bis die IDE ruhig ist | Rechenzeit |
|---|---|---|
| Training 1, erster Start (Projekte und Bibliotheken werden eingelesen) | ca. 100 s | ca. 233 CPU-s |
| Training 1, zweiter Start | ca. 20 s | – |

Die 233 CPU-Sekunden verteilen sich auf mehrere Kerne. Auf einem Notebook mit 4 Kernen
(i5) ist für den ersten Start mit **einigen Minuten** zu rechnen – das passiert aber nur
einmal pro Training, nicht bei jedem Start.

### Speicherplatz

| Was | Größe |
|---|---|
| 4diac IDE entpackt (ohne `typelibrary`) | 365 MB |
| Download der IDE (ZIP, bleibt in `downloads\`) | 311 MB |
| Repo `4diac_training1` inkl. Git-Historie | 98 MB |
| `.metadata` des Workspace nach dem ersten Start | ca. 1 MB |

Git (PortableGit) und Python kommen noch hinzu, wurden hier aber nicht gemessen.

## Vergleich mit den Schulvorgaben

| Fachgruppe | RAM Mindestens | RAM Empfohlen | CPU Mindestens | SSD Mindestens |
|---|---|---|---|---|
| Feinwerk-/Landmaschinenmechanik/Metallbau | 16 GB | 16 GB | i7 | 250 GB |
| Elektro-/Informationstechnik | 8 GB | 16 GB | i5 | 250 GB |
| Installateure/Heizungsbau | 8 GB | 8 GB | i5 | 250 GB |

Alle drei Vorgaben reichen für die 4diac IDE mit Training 1. Bei 16 GB bekommt Java
standardmäßig bis zu 4 GB Heap – das ist reichlich Reserve.

## Was noch fehlt

- Messung auf einem **echten Schüler- bzw. Lehrer-Notebook** (i5, 8 GB), vor allem die
  Dauer des ersten Starts.
- Messung bei der Arbeit: Anwendung im Editor öffnen, übersetzen, auf FORTE deployen.
- Weitere Trainings (z. B. `4diac-SlurryTanker_AX-sample`) und mehrere Trainings
  nebeneinander.
- Platzbedarf von Git und Python nach der Installation.
