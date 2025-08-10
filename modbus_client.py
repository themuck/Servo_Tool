from pymodbus.client import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusException, ConnectionException, ModbusIOException
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian
import time
from custom_exceptions import (
    ModbusConnectionException,
    ModbusReadException,
    ModbusWriteException,
    ModbusTimeoutException
)
from logger_config import logger

class ServoModbusClient:
    def __init__(self, default_timeout=1.0, read_timeout=2.0):
        self.client = None
        self.connected = False
        self.default_timeout = default_timeout
        self.read_timeout = read_timeout
        self.slave_id = None
        self.last_error = None

    def connect(self, port, baudrate, bytesize, parity, stopbits, slave_id):
        """
        Stellt eine Verbindung zum Modbus-Gerät her.
        
        Args:
            port: Serieller Port
            baudrate: Baudrate
            bytesize: Anzahl der Datenbits
            parity: Parität (N/E/O/M/S)
            stopbits: Anzahl der Stoppbits
            slave_id: Slave-ID des Geräts
            
        Returns:
            bool: True bei erfolgreicher Verbindung, False bei Fehler
            
        Raises:
            ModbusConnectionException: Bei Verbindungsfehlern
            ModbusTimeoutException: Bei Timeouts während der Verbindung
        """
        try:
            # Parameter validieren
            if not port:
                error_msg = "Kein Port angegeben"
                logger.log_modbus_connection("unbekannt", False, error_msg)
                raise ModbusConnectionException(error_msg)
                
            try:
                baudrate = int(baudrate)
                bytesize = int(bytesize)
                stopbits = int(stopbits)
                slave_id = int(slave_id)
            except ValueError as e:
                error_msg = f"Ungültige Verbindungsparameter: {e}"
                logger.log_modbus_connection(port, False, error_msg)
                raise ModbusConnectionException(error_msg)
                
            # Client mit Timeout erstellen
            self.client = ModbusClient(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=self.default_timeout
            )
            
            # Verbindung mit Timeout-Überwachung herstellen
            start_time = time.time()
            self.connected = self.client.connect()
            connection_time = time.time() - start_time
            
            if connection_time > self.default_timeout:
                error_msg = f"Timeout bei Verbindungsaufbau nach {connection_time:.2f}s"
                logger.log_modbus_connection(port, False, error_msg)
                raise ModbusTimeoutException(error_msg)
                
            if self.connected:
                self.slave_id = slave_id
                logger.log_modbus_connection(port, True)
                print(f"Modbus-Verbindung erfolgreich hergestellt zu {port} in {connection_time:.2f}s.")
                return True
            else:
                error_msg = f"Modbus-Verbindung konnte nicht hergestellt werden zu {port}"
                logger.log_modbus_connection(port, False, error_msg)
                raise ModbusConnectionException(error_msg)
                
        except ConnectionException as e:
            self.connected = False
            self.last_error = str(e)
            logger.log_modbus_connection(port, False, str(e))
            raise ModbusConnectionException(f"Verbindungsfehler: {e}")
        except ModbusIOException as e:
            self.connected = False
            self.last_error = str(e)
            logger.log_modbus_connection(port, False, str(e))
            raise ModbusTimeoutException(f"Modbus-IO-Fehler (Timeout): {e}")
        except ModbusException as e:
            self.connected = False
            self.last_error = str(e)
            logger.log_modbus_connection(port, False, str(e))
            raise ModbusConnectionException(f"Modbus-Fehler: {e}")
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            logger.log_modbus_connection(port, False, str(e))
            raise ModbusConnectionException(f"Allgemeiner Verbindungsfehler: {e}")

    def disconnect(self):
        """Trennt die Verbindung zum Modbus-Gerät."""
        if self.client and self.connected:
            try:
                self.client.close()
            except Exception as e:
                print(f"Fehler beim Trennen der Verbindung: {e}")
        self.connected = False
        print("Modbus-Verbindung getrennt.")

    def read_holding_register(self, address, count=1):
        """
        Liest Holding-Register vom Modbus-Gerät.
        
        Args:
            address: Startadresse des Registers (1-basiert, wie in der JSON-Datei)
            count: Anzahl der zu lesenden Register (Standard: 1)
            
        Returns:
            list: Liste der Registerwerte oder None bei Fehler
            
        Raises:
            ModbusReadException: Bei Fehlern beim Lesen
            ModbusTimeoutException: Bei Timeouts während des Lesens
            ModbusConnectionException: Bei Verbindungsproblemen
        """
        if not self.connected:
            error_msg = "Keine Verbindung zum Gerät"
            logger.log_modbus_operation("Lesen", address, False, error_msg=error_msg)
            raise ModbusConnectionException(error_msg)
            
        try:
            # Startzeit für Timeout-Überwachung
            start_time = time.time()
            
            # Konvertiere 1-basierte Adresse zu 0-basierter Modbus-Adresse
            result = self.client.read_holding_registers(address, count=count, slave=self.slave_id)
            
            # Überprüfen, ob die Operation zu lange gedauert hat
            operation_time = time.time() - start_time
            if operation_time > self.read_timeout:
                error_msg = f"Timeout beim Lesen von Register {address} nach {self.read_timeout}s"
                logger.log_timeout("Lesen", address, operation_time)
                self.last_error = error_msg
                raise ModbusTimeoutException(error_msg)
                
            if result.isError():
                # Prüfe auf spezifische Modbus-Exception-Codes
                if hasattr(result, 'exception_code'):
                    if result.exception_code == 2:  # Illegal Data Address
                        error_msg = f"Ungültige Registeradresse {address}. Das Register existiert nicht oder ist nicht lesbar."
                    elif result.exception_code == 3:  # Illegal Data Value
                        error_msg = f"Ungültiger Datenwert für Register {address}."
                    else:
                        error_msg = f"Modbus-Fehler (Code {result.exception_code}) beim Lesen von Register {address}: {result}"
                else:
                    error_msg = f"Fehler beim Lesen von Register {address}: {result}"
                
                self.last_error = error_msg
                logger.log_modbus_operation("Lesen", address, False, error_msg=error_msg)
                raise ModbusReadException(error_msg)
                
            # Erfolgreiches Lesen loggen
            logger.log_modbus_operation("Lesen", address, True, value=result.registers)
            return result.registers
            
        except ModbusIOException as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Lesen", address, False, error_msg=str(e))
            raise ModbusTimeoutException(f"Modbus-IO-Fehler (Timeout) beim Lesen von Register {address}: {e}")
        except ModbusException as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Lesen", address, False, error_msg=str(e))
            raise ModbusReadException(f"Modbus-Fehler beim Lesen von Register {address}: {e}")
        except Exception as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Lesen", address, False, error_msg=str(e))
            raise ModbusReadException(f"Allgemeiner Fehler beim Lesen von Register {address}: {e}")

    def read_holding_register_32bit(self, address, is_signed=False, byteorder=Endian.BIG):
        """
        Liest ein 32-Bit-Holding-Register vom Modbus-Gerät.
        
        Args:
            address: Startadresse des Registers (1-basiert, wie in der JSON-Datei)
            is_signed: True, wenn der Wert als vorzeichenbehaftete Ganzzahl interpretiert werden soll
            byteorder: Byte-Reihenfolge (Endian.Big oder Endian.Little)
            
        Returns:
            int: 32-Bit-Registerwert oder None bei Fehler
            
        Raises:
            ModbusReadException: Bei Fehlern beim Lesen
            ModbusTimeoutException: Bei Timeouts während des Lesens
            ModbusConnectionException: Bei Verbindungsproblemen
        """
        if not self.connected:
            error_msg = "Keine Verbindung zum Gerät"
            logger.log_modbus_operation("Lesen 32bit", address, False, error_msg=error_msg)
            raise ModbusConnectionException(error_msg)
            
        try:
            # Debug-Information
            signed_str = "signed" if is_signed else "unsigned"
            byteorder_str = "Big-Endian" if byteorder == Endian.BIG else "Little-Endian"
            logger.debug(f"DEBUG: Lese 32-Bit-Register an Adresse {address} als {signed_str}, Byte-Reihenfolge: {byteorder_str}")
            
            # Startzeit für Timeout-Überwachung
            start_time = time.time()
            
            # Konvertiere 1-basierte Adresse zu 0-basierter Modbus-Adresse
            # Lese zwei aufeinanderfolgende 16-Bit-Register für ein 32-Bit-Register
            logger.debug(f"DEBUG: Sende Leseanfrage für 2 Register ab Modbus-Adresse {address}")
            result = self.client.read_holding_registers(address, count=2, slave=self.slave_id)
            
            # Überprüfen, ob die Operation zu lange gedauert hat
            operation_time = time.time() - start_time
            if operation_time > self.read_timeout:
                error_msg = f"Timeout beim Lesen von 32-Bit-Register {address} nach {self.read_timeout}s"
                logger.log_timeout("Lesen 32bit", address, operation_time)
                self.last_error = error_msg
                raise ModbusTimeoutException(error_msg)
                
            if result.isError():
                # Prüfe auf spezifische Modbus-Exception-Codes
                if hasattr(result, 'exception_code'):
                    if result.exception_code == 2:  # Illegal Data Address
                        logger.error(f"DEBUG: Ungültige Registeradresse {address} für 32-Bit-Lesen")
                        
                        # Versuche, das Register als 16-Bit-Register zu lesen
                        try:
                            logger.debug(f"DEBUG: Versuche Fallback mit 16-Bit-Lesen von Register {address}")
                            single_result = self.client.read_holding_registers(address, count=1, slave=self.slave_id)
                            if not single_result.isError() and len(single_result.registers) >= 1:
                                # Wenn das einzelne Register gelesen werden kann, gib es als 16-Bit-Wert zurück
                                logger.debug(f"DEBUG: Erfolgreich als 16-Bit-Register gelesen: {single_result.registers[0]}")
                                logger.log_modbus_operation("Lesen 32bit", address, True, value=single_result.registers[0])
                                return single_result.registers[0]
                        except Exception as fallback_e:
                            logger.error(f"DEBUG: Fallback-Lesen fehlgeschlagen: {str(fallback_e)}")
                        
                        error_msg = f"Ungültige Registeradresse {address}. Das Register existiert nicht oder ist nicht lesbar."
                    elif result.exception_code == 3:  # Illegal Data Value
                        error_msg = f"Ungültiger Datenwert für Register {address}."
                    else:
                        error_msg = f"Modbus-Fehler (Code {result.exception_code}) beim Lesen von 32-Bit-Register {address}: {result}"
                else:
                    error_msg = f"Fehler beim Lesen von 32-Bit-Register {address}: {result}"
                
                self.last_error = error_msg
                logger.log_modbus_operation("Lesen 32bit", address, False, error_msg=error_msg)
                raise ModbusReadException(error_msg)
                
            # Register-Werte extrahieren und debuggen
            if len(result.registers) >= 2:
                logger.debug(f"DEBUG: Rohdaten empfangen: Register[{address}]={result.registers[0]}, Register[{address+1}]={result.registers[1]}")
                
                # Verwende BinaryPayloadDecoder, um die 32-Bit-Werte zu interpretieren
                # Für 32-Bit-Register verwenden wir Big-Endian Byteorder mit Little-Endian Wordorder
                try:
                    logger.debug(f"DEBUG: Erstelle BinaryPayloadDecoder mit Big-Endian Byteorder und Little-Endian Wordorder")
                    logger.debug(f"DEBUG: Rohdaten für Decoder: {result.registers}")
                    logger.debug(f"DEBUG: Prüfe, ob result.registers existiert und nicht leer ist: {result.registers is not None and len(result.registers) > 0}")
                    
                    decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=byteorder, wordorder=Endian.LITTLE)
                    logger.debug(f"DEBUG: BinaryPayloadDecoder erfolgreich erstellt")
                except Exception as decoder_error:
                    logger.error(f"DEBUG: Fehler bei der Erstellung des BinaryPayloadDecoder: {str(decoder_error)}")
                    logger.error(f"DEBUG: Exception-Typ: {type(decoder_error)}")
                    logger.error(f"DEBUG: Exception-Args: {decoder_error.args}")
                    # Versuche alternative Decodierung
                    try:
                        logger.debug(f"DEBUG: Versuche alternative Decodierung mit Big-Endian Byteorder und Big-Endian Wordorder")
                        decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=byteorder, wordorder=Endian.BIG)
                        logger.debug(f"DEBUG: Alternative BinaryPayloadDecoder-Erstellung erfolgreich")
                    except Exception as alt_error:
                        logger.error(f"DEBUG: Alternative Decodierung fehlgeschlagen: {str(alt_error)}")
                        logger.error(f"DEBUG: Alternative Exception-Typ: {type(alt_error)}")
                        logger.error(f"DEBUG: Alternative Exception-Args: {alt_error.args}")
                        raise ModbusReadException(f"Fehler bei der Decodierung des 32-Bit-Wertes: {str(decoder_error)}")
                
                try:
                    if is_signed:
                        logger.debug(f"DEBUG: Decodiere als 32-Bit signed integer")
                        value_32bit = decoder.decode_32bit_int()
                    else:
                        logger.debug(f"DEBUG: Decodiere als 32-Bit unsigned integer")
                        value_32bit = decoder.decode_32bit_uint()
                    logger.debug(f"DEBUG: Decodierung erfolgreich, Wert: {value_32bit}")
                except Exception as decode_error:
                    logger.error(f"DEBUG: Fehler bei der Decodierung des Wertes: {str(decode_error)}")
                    logger.error(f"DEBUG: Decode Exception-Typ: {type(decode_error)}")
                    raise ModbusReadException(f"Fehler bei der Decodierung des 32-Bit-Wertes: {str(decode_error)}")
                
                logger.debug(f"DEBUG: 32-Bit-Lesen erfolgreich - Interpretiert als {signed_str}: {value_32bit}")
                # Erfolgreiches Lesen loggen
                logger.log_modbus_operation("Lesen 32bit", address, True, value=value_32bit)
                return value_32bit
            elif len(result.registers) == 1:
                # Wenn nur ein Register zurückgegeben wird, verwende es als 16-Bit-Wert
                logger.debug(f"DEBUG: Nur ein Register zurückgegeben, verwende als 16-Bit-Wert: {result.registers[0]}")
                logger.log_modbus_operation("Lesen 32bit", address, True, value=result.registers[0])
                return result.registers[0]
            else:
                error_msg = f"Nicht genügend Daten für 32-Bit-Register {address}"
                self.last_error = error_msg
                logger.log_modbus_operation("Lesen 32bit", address, False, error_msg=error_msg)
                raise ModbusReadException(error_msg)
                
        except ModbusIOException as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Lesen 32bit", address, False, error_msg=str(e))
            raise ModbusTimeoutException(f"Modbus-IO-Fehler (Timeout) beim Lesen von 32-Bit-Register {address}: {e}")
        except ModbusException as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Lesen 32bit", address, False, error_msg=str(e))
            raise ModbusReadException(f"Modbus-Fehler beim Lesen von 32-Bit-Register {address}: {e}")
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"DEBUG: Allgemeine Exception beim Lesen von 32-Bit-Register {address}: {str(e)}")
            logger.error(f"DEBUG: Exception-Typ: {type(e)}")
            logger.log_modbus_operation("Lesen 32bit", address, False, error_msg=str(e))
            raise ModbusReadException(f"Allgemeiner Fehler beim Lesen von 32-Bit-Register {address}: {e}")

    def write_holding_register_32bit(self, address, value, is_signed=False, byteorder=Endian.BIG):
        """
        Schreibt einen 32-Bit-Wert in zwei aufeinanderfolgende Holding-Register des Modbus-Geräts.
        
        Args:
            address: Adresse des ersten Registers (1-basiert, wie in der JSON-Datei)
            value: Zu schreibender 32-Bit-Wert
            is_signed: True, wenn der Wert als vorzeichenbehaftete Ganzzahl interpretiert werden soll
            byteorder: Byte-Reihenfolge (Endian.Big oder Endian.Little)
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
            
        Raises:
            ModbusWriteException: Bei Fehlern beim Schreiben
            ModbusTimeoutException: Bei Timeouts während des Schreibens
            ModbusConnectionException: Bei Verbindungsproblemen
        """
        if not self.connected:
            error_msg = "Keine Verbindung zum Gerät"
            logger.log_modbus_operation("Schreiben 32bit", address, False, value, error_msg)
            raise ModbusConnectionException(error_msg)
            
        try:
            # Debug-Information
            signed_str = "signed" if is_signed else "unsigned"
            byteorder_str = "Big-Endian" if byteorder == Endian.BIG else "Little-Endian"
            logger.debug(f"DEBUG: Schreibe 32-Bit-Register an Adresse {address} als {signed_str}, Wert: {value}, Byte-Reihenfolge: {byteorder_str}")
            
            # Startzeit für Timeout-Überwachung
            start_time = time.time()
            
            # Konvertiere 1-basierte Adresse zu 0-basierter Modbus-Adresse
            # Verwende BinaryPayloadBuilder, um die 32-Bit-Werte zu erstellen
            # Für 32-Bit-Register verwenden wir Big-Endian Byteorder mit Little-Endian Wordorder
            try:
                logger.debug(f"DEBUG: Erstelle BinaryPayloadBuilder mit Big-Endian Byteorder und Little-Endian Wordorder")
                builder = BinaryPayloadBuilder(byteorder=byteorder, wordorder=Endian.LITTLE)
                logger.debug(f"DEBUG: BinaryPayloadBuilder erfolgreich erstellt")
            except Exception as builder_error:
                logger.error(f"DEBUG: Fehler bei der Erstellung des BinaryPayloadBuilder: {str(builder_error)}")
                logger.error(f"DEBUG: Exception-Typ: {type(builder_error)}")
                logger.error(f"DEBUG: Exception-Args: {builder_error.args}")
                # Versuche alternative Codierung
                try:
                    logger.debug(f"DEBUG: Versuche alternative Codierung mit Big-Endian Byteorder und Big-Endian Wordorder")
                    builder = BinaryPayloadBuilder(byteorder=byteorder, wordorder=Endian.BIG)
                    logger.debug(f"DEBUG: Alternative BinaryPayloadBuilder-Erstellung erfolgreich")
                except Exception as alt_error:
                    logger.error(f"DEBUG: Alternative Codierung fehlgeschlagen: {str(alt_error)}")
                    logger.error(f"DEBUG: Alternative Exception-Typ: {type(alt_error)}")
                    logger.error(f"DEBUG: Alternative Exception-Args: {alt_error.args}")
                    raise ModbusWriteException(f"Fehler bei der Codierung des 32-Bit-Wertes: {str(builder_error)}")
            
            if is_signed:
                logger.debug(f"DEBUG: Codiere als 32-Bit signed integer")
                builder.add_32bit_int(value)
            else:
                logger.debug(f"DEBUG: Codiere als 32-Bit unsigned integer")
                builder.add_32bit_uint(value)
            
            payload = builder.build()
            registers_to_write = builder.to_registers()
            
            logger.debug(f"DEBUG: 32-Bit-Wert {value} aufgeteilt in Register: Register[{address}]={registers_to_write[0]}, Register[{address+1}]={registers_to_write[1]}")
            
            # Schreibe die beiden 16-Bit-Werte in aufeinanderfolgende Register
            logger.debug(f"DEBUG: Sende Schreibanfrage für 2 Register ab Modbus-Adresse {address}")
            result = self.client.write_registers(address, registers_to_write, slave=self.slave_id)
            
            # Überprüfen, ob die Operation zu lange gedauert hat
            operation_time = time.time() - start_time
            if operation_time > self.read_timeout:
                error_msg = f"Timeout beim Schreiben von 32-Bit-Register {address} nach {self.read_timeout}s"
                logger.log_timeout("Schreiben 32bit", address, operation_time)
                self.last_error = error_msg
                raise ModbusTimeoutException(error_msg)
                
            if result.isError():
                # Prüfe auf spezifische Modbus-Exception-Codes
                if hasattr(result, 'exception_code'):
                    if result.exception_code == 2:  # Illegal Data Address
                        logger.error(f"DEBUG: Ungültige Registeradresse {address} für 32-Bit-Schreiben")
                        
                        # Versuche, den Wert als 16-Bit-Wert zu schreiben
                        try:
                            logger.debug(f"DEBUG: Versuche Fallback mit 16-Bit-Schreiben von Register {address}")
                            single_result = self.client.write_register(address, value, slave=self.slave_id)
                            if not single_result.isError():
                                logger.debug(f"DEBUG: Erfolgreich als 16-Bit-Register geschrieben: {value}")
                                logger.log_modbus_operation("Schreiben 32bit", address, True, value)
                                return True
                        except Exception as fallback_e:
                            logger.error(f"DEBUG: Fallback-Schreiben fehlgeschlagen: {str(fallback_e)}")
                        
                        error_msg = f"Ungültige Registeradresse {address}. Das Register existiert nicht oder ist nicht schreibbar."
                    elif result.exception_code == 3:  # Illegal Data Value
                        error_msg = f"Ungültiger Datenwert für Register {address}. Der Wert {value} wird nicht unterstützt."
                    else:
                        error_msg = f"Modbus-Fehler (Code {result.exception_code}) beim Schreiben von 32-Bit-Register {address}: {result}"
                else:
                    error_msg = f"Fehler beim Schreiben von 32-Bit-Register {address}: {result}"
                
                self.last_error = error_msg
                logger.log_modbus_operation("Schreiben 32bit", address, False, value, error_msg)
                raise ModbusWriteException(error_msg)
                
            # Erfolgreiches Schreiben loggen
            logger.debug(f"DEBUG: 32-Bit-Schreiben erfolgreich für Adresse {address}")
            logger.log_modbus_operation("Schreiben 32bit", address, True, value)
            return True
            
        except ModbusIOException as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Schreiben 32bit", address, False, value, str(e))
            raise ModbusTimeoutException(f"Modbus-IO-Fehler (Timeout) beim Schreiben von 32-Bit-Register {address}: {e}")
        except ModbusException as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Schreiben 32bit", address, False, value, str(e))
            raise ModbusWriteException(f"Modbus-Fehler beim Schreiben von 32-Bit-Register {address}: {e}")
        except Exception as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Schreiben 32bit", address, False, value, str(e))
            raise ModbusWriteException(f"Allgemeiner Fehler beim Schreiben von 32-Bit-Register {address}: {e}")

    def write_holding_register(self, address, value):
        """
        Schreibt einen Wert in ein Holding-Register des Modbus-Geräts.
        
        Args:
            address: Adresse des Registers (1-basiert, wie in der JSON-Datei)
            value: Zu schreibender Wert
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
            
        Raises:
            ModbusWriteException: Bei Fehlern beim Schreiben
            ModbusTimeoutException: Bei Timeouts während des Schreibens
            ModbusConnectionException: Bei Verbindungsproblemen
        """
        if not self.connected:
            error_msg = "Keine Verbindung zum Gerät"
            logger.log_modbus_operation("Schreiben", address, False, value, error_msg)
            raise ModbusConnectionException(error_msg)
            
        try:
            # Startzeit für Timeout-Überwachung
            start_time = time.time()
            
            # Konvertiere 1-basierte Adresse zu 0-basierter Modbus-Adresse
            result = self.client.write_register(address, value, slave=self.slave_id)
            
            # Überprüfen, ob die Operation zu lange gedauert hat
            operation_time = time.time() - start_time
            if operation_time > self.read_timeout:
                error_msg = f"Timeout beim Schreiben von Register {address} nach {self.read_timeout}s"
                logger.log_timeout("Schreiben", address, operation_time)
                self.last_error = error_msg
                raise ModbusTimeoutException(error_msg)
                
            if result.isError():
                # Prüfe auf spezifische Modbus-Exception-Codes
                if hasattr(result, 'exception_code'):
                    if result.exception_code == 2:  # Illegal Data Address
                        error_msg = f"Ungültige Registeradresse {address}. Das Register existiert nicht oder ist nicht schreibbar."
                    elif result.exception_code == 3:  # Illegal Data Value
                        error_msg = f"Ungültiger Datenwert für Register {address}. Der Wert {value} wird nicht unterstützt."
                    else:
                        error_msg = f"Modbus-Fehler (Code {result.exception_code}) beim Schreiben von Register {address}: {result}"
                else:
                    error_msg = f"Fehler beim Schreiben von Register {address}: {result}"
                
                self.last_error = error_msg
                logger.log_modbus_operation("Schreiben", address, False, value, error_msg)
                raise ModbusWriteException(error_msg)
                
            # Erfolgreiches Schreiben loggen
            logger.log_modbus_operation("Schreiben", address, True, value)
            return True
            
        except ModbusIOException as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Schreiben", address, False, value, str(e))
            raise ModbusTimeoutException(f"Modbus-IO-Fehler (Timeout) beim Schreiben von Register {address}: {e}")
        except ModbusException as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Schreiben", address, False, value, str(e))
            raise ModbusWriteException(f"Modbus-Fehler beim Schreiben von Register {address}: {e}")
        except Exception as e:
            self.last_error = str(e)
            logger.log_modbus_operation("Schreiben", address, False, value, str(e))
            raise ModbusWriteException(f"Allgemeiner Fehler beim Schreiben von Register {address}: {e}")
            
    def get_last_error(self):
        """Gibt die letzte Fehlermeldung zurück."""
        return self.last_error
        
    def set_timeouts(self, default_timeout=None, read_timeout=None):
        """
        Konfiguriert die Timeouts für die Modbus-Operationen.
        
        Args:
            default_timeout: Standard-Timeout in Sekunden
            read_timeout: Lese-Timeout in Sekunden
        """
        if default_timeout is not None:
            self.default_timeout = float(default_timeout)
        if read_timeout is not None:
            self.read_timeout = float(read_timeout)
            
        # Wenn bereits verbunden, Timeout am Client aktualisieren
        if self.client and self.connected:
            self.client.timeout = self.default_timeout