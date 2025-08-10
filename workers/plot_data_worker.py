import math
import random
import time
from PyQt5.QtCore import QThread, pyqtSignal
from custom_exceptions import (
    ModbusConnectionException,
    ModbusReadException,
    ModbusTimeoutException
)
from logger_config import logger
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
import numpy as np


class PlotDataWorker(QThread):
    """Worker-Klasse für kontinuierliche Modbus-Abfragen für Plot-Daten"""
    data_updated = pyqtSignal(dict)  # Signal für aktualisierte Daten
    watchdog_triggered = pyqtSignal(str)  # Signal für Watchdog-Auslösung
    
    def __init__(self, modbus_client, parameter_manager, main_app=None):
        super().__init__()
        self.modbus_client = modbus_client
        self.parameter_manager = parameter_manager
        self.main_app = main_app  # Referenz zur Hauptanwendung für den Simulationsmodus
        self.is_running = False
        self.visible_lines = []  # Welche Linien im Plot sichtbar sind
        self.simulation_mode = False
        
        # Watchdog und Konfigurationsparameter
        self.config = {
            'min_update_interval': 1,  # ms - minimales Intervall für maximale Geschwindigkeit
            'max_update_interval': 10,  # ms - kurzes maximales Intervall
            'watchdog_timeout': 10,  # s
            'max_reconnect_attempts': 5,
            'reconnect_delay': 5,  # s
            'max_data_points': 1000000  # sehr hohe Anzahl für maximale Datenaufzeichnung
        }
        
        # Watchdog-Zähler
        self.last_response_time = time.time()
        self.last_successful_update = time.time()
        self.consecutive_failures = 0
        self.max_consecutive_failures = 10
        
    def update_visible_lines(self, lines):
        """Aktualisiert die Liste der sichtbaren Linien"""
        self.visible_lines = lines
        
    def set_simulation_mode(self, simulation_mode):
        """Aktualisiert den Simulationsmodus"""
        self.simulation_mode = simulation_mode
        
    def update_config(self, new_config):
        """Aktualisiert die Konfiguration des Workers"""
        self.config.update(new_config)
        logger.info(f"Plot-Worker-Konfiguration aktualisiert: {new_config}")
        
    def _restart_worker(self):
        """Startet den Worker intern neu"""
        logger.info("Plot-Worker wird neu gestartet")
        # Zähler und Zeiten zurücksetzen
        self.last_response_time = time.time()
        self.last_successful_update = time.time()
        self.consecutive_failures = 0
        # Kurze Pause vor dem Neustart
        self.msleep(1000)
        
    def run(self):
        """Hauptmethode des Worker-Threads"""
        self.is_running = True
        last_update_time = 0
        sim_start_time = 0  # Startzeit für die Simulation
        reconnect_attempts = 0
        
        # Watchdog-Zähler zurücksetzen
        self.last_response_time = time.time()
        self.last_successful_update = time.time()
        self.consecutive_failures = 0
        
        logger.info("Plot-Data-Worker gestartet")
        
        while self.is_running:
            current_time = time.time()
            
            # Watchdog-Prüfung
            if current_time - self.last_response_time > self.config['watchdog_timeout']:
                logger.warning("Watchdog ausgelöst - Worker wird neu gestartet")
                self.watchdog_triggered.emit("Worker-Timeout - Neustart erforderlich")
                self._restart_worker()
                self.last_response_time = current_time
                continue
                
            # Prüfe auf zu viele aufeinanderfolgende Fehler
            if self.consecutive_failures >= self.max_consecutive_failures:
                logger.error(f"Maximale Anzahl von Fehlern ({self.max_consecutive_failures}) erreicht - Worker wird beendet")
                self.watchdog_triggered.emit(f"Zu viele Fehler ({self.consecutive_failures}) - Worker wird beendet")
                break
                
            if self.modbus_client.connected:
                try:
                    current_time_ms = current_time * 1000  # Aktuelle Zeit in ms
                    
                    # Prüfe, ob seit dem letzten Update genug Zeit vergangen ist
                    if current_time_ms - last_update_time >= self.config['min_update_interval']:
                        values = self._read_plot_values()
                        
                        # Sende die aktualisierten Daten an den Haupt-Thread
                        if values:
                            self.data_updated.emit(values)
                            last_update_time = current_time_ms
                            self.last_successful_update = current_time
                            self.consecutive_failures = 0  # Fehlerzähler zurücksetzen
                            reconnect_attempts = 0  # Verbindungszähler zurücksetzen
                        else:
                            self.consecutive_failures += 1
                    else:
                        # Warte, um die CPU zu entlasten
                        self.msleep(5)
                        
                except ModbusTimeoutException:
                    # Bei Timeout kurz warten und dann mit der nächsten Abfrage fortfahren
                    logger.warning("Modbus-Timeout im Plot-Worker")
                    self.consecutive_failures += 1
                    self.msleep(10)
                except ModbusConnectionException:
                    # Bei Verbindungsproblemen versuche neu zu verbinden
                    logger.error("Modbus-Verbindungsfehler im Plot-Worker")
                    self.consecutive_failures += 1
                    if reconnect_attempts < self.config['max_reconnect_attempts']:
                        logger.info(f"Versuch {reconnect_attempts + 1} zur Neuverbindung...")
                        
                        # Versuche, die Verbindung wiederherzustellen
                        try:
                            # Zuerst Verbindung trennen
                            if self.modbus_client.client:
                                self.modbus_client.disconnect()
                            
                            # Kurze Pause vor dem Neuverbindungsversuch
                            self.msleep(1000)
                            
                            # Verbindungseinstellungen aus der Hauptanwendung holen
                            if self.main_app and hasattr(self.main_app, 'connection_tab'):
                                connection_params = self.main_app.connection_tab.get_connection_parameters()
                                
                                # Timeouts konfigurieren, falls in den Verbindungseinstellungen angegeben
                                if 'timeout' in connection_params:
                                    self.modbus_client.set_timeouts(default_timeout=connection_params['timeout'])
                                
                                # Versuche neu zu verbinden
                                is_connected = self.modbus_client.connect(**connection_params)
                                
                                if is_connected:
                                    logger.info("Neuverbindung erfolgreich")
                                    self.consecutive_failures = 0  # Fehlerzähler zurücksetzen bei erfolgreicher Verbindung
                                    reconnect_attempts = 0  # Verbindungszähler zurücksetzen
                                    self.last_successful_update = time.time()
                                    
                                    # Benachrichtige die Hauptanwendung über die erfolgreiche Neuverbindung
                                    if hasattr(self.main_app, 'status_label'):
                                        self.main_app.status_label.setText("Verbindung erfolgreich wiederhergestellt")
                                    
                                    # Kurze Pause nach erfolgreicher Verbindung
                                    self.msleep(500)
                                    continue
                                else:
                                    logger.warning(f"Neuverbindungsversuch {reconnect_attempts + 1} fehlgeschlagen")
                            else:
                                logger.warning("Keine Verbindungseinstellungen verfügbar für Neuverbindung")
                        except Exception as reconnect_error:
                            logger.error(f"Fehler beim Neuverbindungsversuch: {reconnect_error}", exc_info=True)
                        
                        # Wartezeit vor dem nächsten Versuch
                        self.msleep(self.config['reconnect_delay'] * 1000)
                        reconnect_attempts += 1
                    else:
                        logger.error("Maximale Anzahl von Neuverbindungsversuchen erreicht")
                        self.watchdog_triggered.emit("Verbindungsfehler - Neuverbindung nicht möglich")
                        
                        # Benachrichtige die Hauptanwendung über den Verbindungsverlust
                        if self.main_app and hasattr(self.main_app, '_disconnect'):
                            self.main_app._disconnect()
                        break
                except Exception as e:
                    # Bei anderen Fehlern kurz warten und dann mit der nächsten Abfrage fortfahren
                    logger.error(f"Unerwarteter Fehler im Plot-Worker: {e}", exc_info=True)
                    self.consecutive_failures += 1
                    self.msleep(10)
            else:
                # Prüfe, ob der Simulationsmodus aktiv ist
                if self.simulation_mode:
                    current_time_ms = current_time * 1000  # Aktuelle Zeit in ms
                    
                    # Initialisiere die Simulationsstartzeit
                    if sim_start_time == 0:
                        sim_start_time = time.time()
                    
                    # Prüfe, ob seit dem letzten Update genug Zeit vergangen ist
                    if current_time_ms - last_update_time >= self.config['min_update_interval']:
                        t = time.time() - sim_start_time
                        sim_values = self._generate_simulation_data(t)
                        
                        # Sende die Simulationsdaten an den Haupt-Thread
                        if sim_values:
                            self.data_updated.emit(sim_values)
                            last_update_time = current_time_ms
                            self.last_successful_update = current_time
                            self.consecutive_failures = 0  # Fehlerzähler zurücksetzen
                    else:
                        # Warte, um die CPU zu entlasten
                        self.msleep(5)
                else:
                    # Keine Verbindung und kein Simulationsmodus, kurz warten und erneut prüfen
                    self.msleep(100)  # 100ms warten bei getrennter Verbindung
                    
            # Aktualisiere die Watchdog-Zeit
            self.last_response_time = time.time()
    
    def _read_plot_values(self):
        """Liest die Plot-Werte von den Modbus-Registern"""
        values = {}
        
        try:
            # Lese die Basis-Register (P0B-00, P0B-01, P0B-02) nur, wenn mindestens eine davon sichtbar ist
            if any(code in self.visible_lines for code in ["P0B-00", "P0B-01", "P0B-02"]):
                d = self.modbus_client.read_holding_register(2816, count=3)
                if d and len(d) == 3:
                    if "P0B-00" in self.visible_lines:
                        value = self._twos_complement_to_int(d[0], 16)
                        if self._validate_modbus_value("P0B-00", value):
                            values["P0B-00"] = value
                    if "P0B-01" in self.visible_lines:
                        value = d[1]
                        if self._validate_modbus_value("P0B-01", value):
                            values["P0B-01"] = value
                    if "P0B-02" in self.visible_lines:
                        value = self._twos_complement_to_int(d[2], 16)
                        if self._validate_modbus_value("P0B-02", value):
                            values["P0B-02"] = value
            
            # Lese P0B-15 nur, wenn es sichtbar ist
            if "P0B-15" in self.visible_lines:
                try:
                    v15 = self.modbus_client.read_holding_register_32bit(2831, is_signed=True)
                    if v15 is not None and self._validate_modbus_value("P0B-15", v15):
                        values["P0B-15"] = v15
                except Exception as e:
                    logger.error(f"Fehler beim Lesen von P0B-15: {e}", exc_info=True)
                    # Verwende keinen Standardwert, um Fehler besser zu erkennen
            
            # Lese P0B-24 nur, wenn es sichtbar ist
            if "P0B-24" in self.visible_lines:
                try:
                    v24 = self.modbus_client.read_holding_register(2840, count=1)
                    if v24 and len(v24) > 0:
                        value = v24[0]
                        if self._validate_modbus_value("P0B-24", value):
                            values["P0B-24"] = value
                except Exception as e:
                    logger.error(f"Fehler beim Lesen von P0B-24: {e}", exc_info=True)
                    # Verwende keinen Standardwert, um Fehler besser zu erkennen
            
            # Lese P0B-58 (Absolute Position) nur, wenn es sichtbar ist
            if "P0B-58" in self.visible_lines:
                try:
                    # Absolute Position ist ein 64-Bit-Wert, bestehend aus zwei 32-Bit-Registern
                    # 2874 (Lower bits) und 2876 (Upper bits)
                    abs_pos = self._read_32bit_pair_as_64bit(2874, 2876)
                    if abs_pos is not None and self._validate_modbus_value("P0B-58", abs_pos):
                        values["P0B-58"] = abs_pos
                except Exception as e:
                    logger.error(f"Fehler beim Lesen von P0B-58: {e}", exc_info=True)
                    # Verwende keinen Standardwert, um Fehler besser zu erkennen
        except Exception as e:
            logger.error(f"Allgemeiner Fehler beim Lesen der Plot-Werte: {e}", exc_info=True)
            # Bei einem allgemeinen Fehler leeres Dictionary zurückgeben
            
        return values
    
    def _twos_complement_to_int(self, val, bits):
        """Konvertiert einen Wert von Zweierkomplement in einen vorzeichenbehafteten Integer."""
        if val & (1 << (bits - 1)):  # Prüfe, ob das höchstwertige Bit gesetzt ist (negativ)
            return val - (1 << bits)
        return val

    def _read_32bit_pair_as_64bit(self, lower_reg_addr, upper_reg_addr):
        """Liest zwei 32-Bit-Register (insgesamt 4 16-Bit-Register) in einem atomaren Vorgang
        und kombiniert sie zu einem 64-Bit-Wert.
        """
        # Die Register 2874 (Lower) und 2876 (Upper) sind 32-Bit-Werte,
        # die jeweils 2 16-Bit-Register belegen.
        # Um sie atomar zu lesen, müssen wir einen Block von 4 Registern lesen:
        # 2874 (Lower-Word1), 2875 (Lower-Word2), 2876 (Upper-Word1), 2877 (Upper-Word2)
        
        # Startadresse ist 2874, Anzahl der Register ist 4
        result = self.modbus_client.client.read_holding_registers(lower_reg_addr, count=4, slave=self.modbus_client.slave_id)
        if result.isError():
            logger.warning(f"Modbus-Fehler beim Lesen von Registern {lower_reg_addr} bis {lower_reg_addr + 3}: {result}")
            return None
        
        registers = result.registers
        if registers is None or len(registers) < 4:
            logger.warning(f"Konnte nicht genügend Register für 64-Bit-Kombination lesen. Erhalten: {result}")
            return None

        # Die Rohregister sind 16-Bit-Werte. Wir müssen sie zu 32-Bit-Werten decodieren.
        # Die Byte-Reihenfolge ist Big-Endian, Word-Reihenfolge ist Little-Endian (vom Benutzer bestätigt)
        decoder = BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE)

        # Decodiere die beiden 32-Bit-Werte
        # Das erste 32-Bit-Wort ist der Lower-Wert (unsigned)
        lower_val = decoder.decode_32bit_uint()
        # Das zweite 32-Bit-Wort ist der Upper-Wert (signed, da es das Vorzeichen des 64-Bit-Wertes trägt)
        upper_val = decoder.decode_32bit_int()

        # Kombiniere die beiden 32-Bit-Werte zu einem 64-Bit-Wert
        # Das obere 32-Bit-Register wird um 32 Stellen nach links verschoben
        # und mit dem unteren 32-Bit-Register ODER-verknüpft.
        # Da upper_val bereits vorzeichenbehaftet ist, wird das Vorzeichen korrekt übertragen.
        combined_val = (upper_val << 32) | lower_val
        
        return combined_val

    def _generate_simulation_data(self, t):
        """Generiert Simulationsdaten für den Plot"""
        sim_values = {}
        
        # Generiere Simulationsdaten nur für sichtbare Linien
        if "P0B-00" in self.visible_lines:
            # Simuliere vorzeichenbehaftete Werte für P0B-00
            sim_values["P0B-00"] = int(500 * math.sin(t * 1.5)) # Werte zwischen -500 und 500
        if "P0B-01" in self.visible_lines:
            sim_values["P0B-01"] = 1500 if (t % 4 < 2) else 1000
        if "P0B-15" in self.visible_lines:
            sim_values["P0B-15"] = int(random.gauss(0, 10))
        if "P0B-02" in self.visible_lines:
            sim_values["P0B-02"] = int(800 * math.cos(t * 1.5))
        if "P0B-24" in self.visible_lines:
            p0b_02_value = int(800 * math.cos(t * 1.5))
            sim_values["P0B-24"] = int(abs(p0b_02_value * 0.75) + random.gauss(0, 5))
        if "P0B-58" in self.visible_lines:
            # Simuliere eine steigende und fallende absolute Position
            sim_values["P0B-58"] = int(1000000 * math.sin(t / 10) + 2000000) # Große Werte für 64-Bit
        
        return sim_values
    
    def _validate_modbus_value(self, code, value):
        """Validiert einen von Modbus gelesenen Wert"""
        try:
            # Prüfe, ob der Wert numerisch ist
            if not isinstance(value, (int, float)):
                return False
            
            # Prüfe auf NaN oder Infinity
            if math.isnan(value) or math.isinf(value):
                return False
            
            # Codespezifische Validierung basierend auf typischen Wertebereichen
            if code == "P0B-00":  # Geschwindigkeit
                # Typischer Bereich für Geschwindigkeit
                if not (-10000 <= value <= 10000):
                    logger.warning(f"P0B-00 Wert außerhalb des erwarteten Bereichs: {value}")
                    return False
            elif code == "P0B-01":  # Strom
                # Typischer Bereich für Strom
                if not (0 <= value <= 2000):
                    logger.warning(f"P0B-01 Wert außerhalb des erwarteten Bereichs: {value}")
                    return False
            elif code == "P0B-02":  # Drehmoment
                # Typischer Bereich für Drehmoment
                if not (-1000 <= value <= 1000):
                    logger.warning(f"P0B-02 Wert außerhalb des erwarteten Bereichs: {value}")
                    return False
            elif code == "P0B-15":  # Temperatur
                # Typischer Bereich für Temperatur
                if not (-50 <= value <= 200):
                    logger.warning(f"P0B-15 Wert außerhalb des erwarteten Bereichs: {value}")
                    return False
            elif code == "P0B-24":  # Leistung
                # Typischer Bereich für Leistung
                if not (0 <= value <= 50000):
                    logger.warning(f"P0B-24 Wert außerhalb des erwarteten Bereichs: {value}")
                    return False
            elif code == "P0B-58":  # Absolute Position
                # Typischer Bereich für absolute Position (64-Bit)
                if not (-2**63 <= value <= 2**63-1):
                    logger.warning(f"P0B-58 Wert außerhalb des 64-Bit-Bereichs: {value}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Fehler bei der Validierung von {code}: {e}")
            return False

    def stop(self):
        """Stoppt den Worker-Thread"""
        self.is_running = False
        self.wait()  # Warte, bis der Thread beendet ist