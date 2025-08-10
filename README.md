# Servo-Tuning-Tool für Lichuan A5 Serie

Ein Desktop-Tool zur Analyse, Konfiguration und zum Tuning von **Lichuan A5 Servomotoren** über das Modbus-RTU-Protokoll. Die Anwendung wurde mit Python und PyQt5 entwickelt und bietet eine grafische Oberfläche zur Visualisierung von Servodaten und zur Interaktion mit den Motorregistern.

**Hinweis:** Dies ist ein Entwicklungstool. Obwohl es auf Stabilität ausgelegt ist, erfolgt die Benutzung auf eigene Gefahr. Testen Sie Änderungen immer sorgfältig.

---

## 🚀 Kernfunktionen

*   **Echtzeit-Plotting:** Hochperformante grafische Darstellung von Servodaten wie Soll/Ist-Geschwindigkeit und Drehmoment mit automatischem Scrollen und Zoom-Funktionen.
*   **Parameter-Management:**
    *   Übersicht aller Servoparameter, gruppiert nach Funktion.
    *   Lesen und Schreiben von einzelnen oder mehreren Parametern.
    *   Intelligente Eingabefelder: Dropdown-Menüs für Parameter mit festen Optionen und Validierung für Wertebereiche, um Fehleingaben zu minimieren.
*   **Farbliche Statusanzeige:**
    *   ⚪ **Weiß:** Parameterwert entspricht dem Werks-Default.
    *   🟡 **Gelb:** Gelesener Wert weicht vom Default ab.
    *   🟠 **Orange:** Wert wurde im Programm geändert und ist noch nicht geschrieben.
*   **Import & Export:** Sichern und Laden der gesamten Gerätekonfiguration im JSON-Format.
*   **Diagnose:**
    *   Live-Anzeige des I/O-Status (DI/DO).
    *   Auslesen und Anzeigen der Fehlerhistorie mit Beschreibungen.
*   **Simulationsmodus:** Ermöglicht das Testen der Oberfläche ohne angeschlossene Hardware.

---

## 🛠️ Technische Details

*   **Sprache:** Python 3
*   **GUI-Framework:** PyQt5
*   **Kommunikation:** `pymodbus` für Modbus RTU (seriell)
*   **Plotting:** PyQtGraph (hocheffiziente Echtzeit-Visualisierung)
*   **Datenmanagement:** Alle Konfigurationen (Parameter, Fehler, etc.) werden aus `.json`-Dateien geladen.

---

## ⚙️ Installation

1.  **Repository klonen:**
    ```bash
    git clone https://github.com/IhrBenutzername/IhrRepoName.git
    cd IhrRepoName
    ```

2.  **Virtuelle Umgebung erstellen (dringend empfohlen):**
    ```bash
    # Für Windows
    py -m venv venv
    venv\Scripts\activate

    # Für macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Abhängigkeiten installieren:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🏁 Anwendung starten

```bash
# Stelle sicher, dass deine virtuelle Umgebung (venv) aktiviert ist
py main.py
```

---

## 🔧 Workflow: Servo-Tuning (Empfohlene Vorgehensweise)

Das korrekte Tuning ist entscheidend für die Performance und Stabilität des Systems. Gehen Sie die Schritte in dieser Reihenfolge durch.

1.  **Verbindung & Vorbereitung:**
    *   Verbinden Sie sich im Tab "Modbus-Verbindung" mit dem Servo.
    *   Stellen Sie sicher, dass der Motor frei und ohne kritische Last laufen kann.

2.  **Schritt 1: Grundeinstellung von Steifigkeit und Trägheit (Einstellvorschrift)**
    *   Diese beiden Werte bedingen sich gegenseitig und sind die **wichtigste Grundlage** für die Stabilität des gesamten Antriebsstrangs.
    *   **Technisches Zusammenspiel:**
        *   **`P09-01 (Rigidity Grade/Steifigkeit)`** beeinflusst direkt die **Bandbreite des Regelkreises**. Ein höherer Wert führt zu einer aggressiveren, schnelleren Regelung, die versucht, Abweichungen sofort zu korrigieren.
        *   **`P08-15 (Load Inertia Ratio)`** informiert den Regelalgorithmus über das **Trägheitsverhältnis zwischen Last und Motor**. Dieses Wissen ist entscheidend für die Vorsteuerung (Feedforward) und die korrekte Berechnung der benötigten Beschleunigungs- und Bremsmomente.
    *   **Wirkungskette:** Ein falsch eingestelltes Trägheitsverhältnis führt dazu, dass der Regler eine falsche Annahme über die Systemdynamik hat. Eine zu aggressive Regelung (hohe Steifigkeit) trifft dann auf eine unerwartete mechanische Reaktion, was unweigerlich zu Schwingungen und Instabilität führt. Nur wenn der Regler die Systemträgheit kennt, kann die Steifigkeit sicher erhöht werden, um die maximale Performance zu erreichen.
    *   Folgen Sie daher diesem iterativen Prozess:
    *   **1. Startwerte setzen:**
        *   Setzen Sie `P08-15 (Load inertia ratio)` auf einen angemessenen Startwert.
        *   Setzen Sie `P09-01 (Rigidity grade)` auf einen niedrigen Wert.
    *   **2. Steifigkeit (`P09-01`) anpassen:**
        *   Erhöhen Sie die Steifigkeit `P09-01` schrittweise, während der Motor läuft (idealerweise ohne komplexe Bewegung).
        *   Stoppen Sie, sobald der Motor beginnt, hörbare Geräusche (Pfeifen, Summen) oder Vibrationen zu entwickeln. Reduzieren Sie den Wert dann wieder, bis der Lauf ruhig ist. Dies ist Ihre maximal mögliche Steifigkeit für die aktuelle Trägheitseinstellung.
    *   **3. Trägheit (`P08-15`) anpassen:**
        *   Starten Sie nun eine für Ihre Anwendung typische Bewegung (z.B. über die Direktbefehle).
        *   **Beobachtung:** Wenn der Motor beim Beschleunigen/Abbremsen oder am Zielpunkt hin- und herschwingt ("überschießt"), ist das Trägheitsverhältnis wahrscheinlich zu niedrig.
        *   **Anpassung:** Erhöhen Sie den Wert für `P08-15` schrittweise und wiederholen Sie die Bewegung, bis das Schwingen minimiert ist.
    *   **4. Wiederholung (optional, aber empfohlen):**
        *   Nachdem Sie die Trägheit (`P08-15`) erhöht haben, hat sich das Systemverhalten geändert. Gehen Sie nun zurück zu Punkt 2 und prüfen Sie, ob Sie die Steifigkeit (`P09-01`) nun vielleicht noch etwas weiter erhöhen können.
        *   Wiederholen Sie die Schritte 2 und 3, bis Sie einen stabilen Zustand gefunden haben, bei dem die Steifigkeit so hoch wie möglich ist, ohne dass es bei realen Bewegungen zu Schwingungen kommt. Erst dann ist die Basis für das Gain-Tuning gelegt.

3.  **Schritt 2: Beobachten und Gain-Tuning (Set 1)**
    *   Geben Sie über die **Direktbefehle** eine typische Zieldrehzahl ein und starten Sie den **Live-Plot**.
    *   **Worauf achten?** Beobachten Sie die `Actual Speed`-Linie. Schwingt sie stark über? Reagiert sie träge?
    *   **Plot-Funktionen nutzen:** Passen Sie die Zeitfenster-Breite an, um den optimalen Blick auf die Daten zu erhalten. Nutzen Sie die Zoom-Funktionen für eine detaillierte Analyse.
    *   Passen Sie nun die Parameter in **"Gain Parameter Set 1"** an:
        *   **`P08-02 (Position loop gain)`:** Ein zentraler Parameter für die Positionsregelung. Beginnen Sie mit einem angemessenen Wert und justieren Sie langsam. Höhere Werte machen die Regelung schneller, aber zu viel davon führt zu Schwingungen.
        *   **`P08-00 (Speed loop gain)`:** Erhöhen, um die Reaktion zu beschleunigen.
        *   **`P08-01 (Speed loop integral time)`:** Verringern, um statische Abweichungen schneller zu korrigieren.
    *   **Ziel:** Eine schnelle Reaktion mit minimalem Überschwingen. Zu hohe Gain-Werte führen zu Vibrationen!

4.  **Schritt 3: Verwendung von Gain-Satz 2 (Optional)**
    *   Wenn Ihre Anwendung unterschiedliche Lastzustände hat, können Sie einen zweiten Parametersatz für diese aktivieren.
    *   Konfigurieren Sie die Werte in **"Gain Parameter Set 2"** (umschaltbar über den Button).
    *   **Aktivierung:** Um diesen Satz zu nutzen, müssen Sie im Tab **"Registerübersicht"** die Parameter `P08-08` (Umschaltung aktivieren) und `P08-09` (Bedingung für Umschaltung definieren) korrekt einstellen.

5.  **Schritt 4: Konfiguration sichern**
    *   Ein funktionierendes Tuning ist wertvoll. Sichern Sie es über `Datei -> Alle Register exportieren...`.

<img width="1481" height="1003" alt="image" src="https://github.com/user-attachments/assets/a069f7c6-ab77-4cc7-825a-13b370752467" />

<img width="1481" height="1003" alt="image" src="https://github.com/user-attachments/assets/66d4305a-dfa5-4de7-9c94-7bf85cf950c2" />
