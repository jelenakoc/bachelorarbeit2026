# Automatische Zeiterfassung

Lokales Zeiterfassungstool zur automatischen Erfassung und Auswertung von Arbeitszeiten nach Projekt und Aufgabe.

## Description

Diese Anwendung wurde entwickelt, um Arbeitszeiten lokal zu erfassen. Der Tracker erkennt dabei aktive Fenster und Anwendungen automatisch und ermöglicht über ein Popup die Zuordnung zu einem entsprechenden Projekt sowie einer zugehörigen Aufgabe. Im Browser-Dashboard können Projekte, Aufgaben, Zeitblöcke und Auswertungen eingesehen werden. Die Anwendung eignet sich besonders für projektbasierte Arbeit.

## Getting Started

### Dependencies

Getestete Umgebung:

- Windows 10 / Windows 11
- moderner Browser, z. B. Microsoft Edge, Chrome oder Firefox

Für die Ausführung aus dem Quellcode werden benötigt:

- Python 3
- pip
- Abhängigkeiten aus `requirements.txt`
- optional: virtuelle Python-Umgebung `.venv`

Die benötigten Python-Pakete sind:

```text
fastapi
uvicorn
sqlalchemy
psutil
pywin32
```

### Installing

Repository herunterladen oder klonen:

```bat
git clone https://github.com/jelenakoc/bachelorarbeit2026.git
cd bachelorarbeit2026
```

Virtuelle Umgebung erstellen:

```bat
python -m venv .venv
```

Virtuelle Umgebung aktivieren:

```bat
.venv\Scripts\activate
```

Abhängigkeiten installieren:

```bat
python -m pip install -r requirements.txt
```

### Executing program

Dashboard aus dem Quellcode starten:

```bat
python run_dashboard.py
```

Danach:

1. Browser öffnen.
2. `http://127.0.0.1:8000/dashboard` aufrufen.
3. Im Dashboard auf `Tracking einschalten` klicken.
4. Bei Bedarf im Popup Projekt und Aufgabe zuordnen.

Das Dashboard läuft lokal unter:

```text
http://127.0.0.1:8000/dashboard
```

## Help

#### Tracking-API nicht erreichbar

Diese Meldung erscheint, wenn das Dashboard im Browser geöffnet ist, aber das Backend nicht erreichbar ist.

Mögliche Lösungen:

1. Browserfenster schliessen.
2. Im Task-Manager alte Prozesse wie `Dashboard.exe`, `Tracker.exe` oder passende `python.exe` beenden.
3. Danach `python run_dashboard.py` erneut starten.

#### Tracking einschalten macht nichts

Bei Ausführung aus dem Quellcode prüfen, ob alle Abhängigkeiten installiert sind:

```bat
python -m pip install -r requirements.txt
```

## Authors

Jelena Kocic

## Version History

- 0.1


