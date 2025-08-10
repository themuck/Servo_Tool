# PyInstaller Build Guide für Servo Tool

## Vorbereitung

### 1. Abhängigkeiten installieren
Stelle sicher, dass alle benötigten Pakete installiert sind:

```bash
pip install -r requirements.txt
```

### 2. PyInstaller installieren
Falls noch nicht geschehen, installiere PyInstaller:

```bash
pip install pyinstaller
```

## Build-Optionen

### Option 1: Einfacher Build (einzelne EXE-Datei)
```bash
pyinstaller --onefile --windowed --name="ServoTool" main.py
```

### Option 2: Build mit Datenordnern (empfohlen)
```bash
pyinstaller --name="ServoTool" --windowed --add-data "ui_tabs;ui_tabs" --add-data "*.json;." main.py
```

### Option 3: Vollständiger Build mit allen Ressourcen
```bash
pyinstaller --name="ServoTool" --windowed --add-data "ui_tabs;ui_tabs" --add-data "*.json;." --icon=icon.ico main.py
```

## Detaillierte Build-Anleitung

### 1. Spec-Datei erstellen (empfohlen)
Erstelle eine Spec-Datei für mehr Kontrolle über den Build-Prozess:

```bash
pyi-makespec --name="ServoTool" --windowed --add-data "ui_tabs;ui_tabs" --add-data "*.json;." main.py
```

### 2. Spec-Datei anpassen
Bearbeite die erstellte `ServoTool.spec`-Datei:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ui_tabs', 'ui_tabs'),  # UI-Tab-Dateien
        ('*.json', '.'),         # JSON-Konfigurationsdateien
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.figure',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ServoTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Falls ein Icon vorhanden ist
)
```

### 3. Build mit Spec-Datei ausführen
```bash
pyinstaller ServoTool.spec
```

## Troubleshooting

### Häufige Probleme und Lösungen

1. **Fehlende Module**: Füge fehlende Module zur `hiddenimports`-Liste in der Spec-Datei hinzu.

2. **Datenordner nicht gefunden**: Stelle sicher, dass alle JSON-Dateien und UI-Tab-Ordner korrekt mit `--add-data` hinzugefügt werden.

3. **Matplotlib-Probleme**: Füge die matplotlib-Backends zu den hiddenimports hinzu.

4. **Pfadprobleme**: Verwende relative Pfade für den Zugriff auf Datenordner in der Anwendung:

```python
import sys
import os

def resource_path(relative_path):
    """Holt den absoluten Pfad zur Ressource, funktioniert für Entwicklung und PyInstaller"""
    try:
        # PyInstaller erstellt einen temporären Ordner und speichert den Pfad in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
```

### Angepasste main.py für PyInstaller
Füge diese Funktion zur main.py hinzu, um Ressourcen korrekt zu laden:

```python
import sys
import os

def resource_path(relative_path):
    """Holt den absoluten Pfad zur Ressource, funktioniert für Entwicklung und PyInstaller"""
    try:
        # PyInstaller erstellt einen temporären Ordner und speichert den Pfad in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Passe die _load_json_data-Methode an
def _load_json_data(self, filename):
    """Load JSON data with proper error handling"""
    try:
        file_path = resource_path(filename)
        with open(file_path, mode='r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Fehler: {filename} nicht gefunden.")
        return {} if 'mapping' in filename else []
    except json.JSONDecodeError:
        print(f"Fehler: {filename} konnte nicht dekodiert werden.")
        return {} if 'mapping' in filename else []
```

## Build-Skript

Erstelle ein Build-Skript `build.bat` (Windows) oder `build.sh` (Linux/Mac):

### Windows (build.bat)
```batch
@echo off
echo Baue Servo Tool mit PyInstaller...

pyinstaller --clean --name="ServoTool" --windowed --add-data "ui_tabs;ui_tabs" --add-data "*.json;." main.py

echo Build abgeschlossen!
pause
```

### Linux/Mac (build.sh)
```bash
#!/bin/bash
echo "Baue Servo Tool mit PyInstaller..."

pyinstaller --clean --name="ServoTool" --windowed --add-data "ui_tabs;ui_tabs" --add-data "*.json;." main.py

echo "Build abgeschlossen!"
```

## Verteilung

Nach dem Build findest du die ausführbare Datei im `dist`-Ordner. Stelle sicher, dass alle JSON-Konfigurationsdateien im selben Ordner wie die EXE-Datei liegen.

## Testen

Teste die kompilierte Anwendung gründlich:
1. Starte die EXE-Datei außerhalb des Entwicklungsordners
2. Überprüfe, ob alle UI-Elemente korrekt geladen werden
3. Teste die Verbindungsfunktionalität
4. Überprüfe, ob alle JSON-Dateien korrekt geladen werden