"""
Benutzerdefinierte Exception-Klassen für die Servo-Steuerungsanwendung.
Diese Klassen ermöglichen eine spezifischere Fehlerbehandlung und -meldung.
"""

class ServoToolException(Exception):
    """Basisklasse für alle benutzerdefinierten Exceptions in dieser Anwendung."""
    pass


class ModbusConnectionException(ServoToolException):
    """Exception für Fehler bei der Modbus-Verbindung."""
    pass


class ModbusReadException(ServoToolException):
    """Exception für Fehler beim Lesen von Modbus-Registern."""
    pass


class ModbusWriteException(ServoToolException):
    """Exception für Fehler beim Schreiben von Modbus-Registern."""
    pass


class ModbusTimeoutException(ServoToolException):
    """Exception für Timeouts bei Modbus-Operationen."""
    pass


class ParameterValidationException(ServoToolException):
    """Exception für Fehler bei der Validierung von Parametern."""
    pass


class FileOperationException(ServoToolException):
    """Exception für Fehler bei Dateioperationen (Import/Export)."""
    pass


class ConfigurationException(ServoToolException):
    """Exception für Fehler in der Konfiguration."""
    pass