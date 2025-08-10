import json
import os
import sys

def resource_path(relative_path):
    """Holt den absoluten Pfad zur Ressource, funktioniert für Entwicklung und PyInstaller"""
    try:
        # PyInstaller erstellt einen temporären Ordner und speichert den Pfad in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class Parameter:
    def __init__(self, code, name, unit, default, hex_val, decimal_val, validation=None):
        self.code = code
        self.name = name
        self.unit = unit
        self.default = default
        self.hex = hex_val
        self.decimal = decimal_val
        self.validation = validation if validation else {}

    def __repr__(self):
        return f"Parameter({self.code}, {self.name}, Hex: {self.hex})"

class ParameterManager:
    def __init__(self, json_file_path="servo_parameter_definitions.json", fun_in_path="servo_FunIN.json", fun_out_path="servo_FunOUT.json"):
        self.json_file_path = json_file_path
        self.parameters = {}
        self.raw_parameters = []
        self.fun_in_map = {}
        self.fun_out_map = {}
        self.fun_in_path = fun_in_path
        self.fun_out_path = fun_out_path

    def load_parameters(self):
        # Load main parameters
        try:
            file_path = resource_path(self.json_file_path)
            with open(file_path, mode='r', encoding='utf-8') as file:
                self.raw_parameters = json.load(file)
            for param_data in self.raw_parameters:
                code = param_data.get('code')
                if code:
                    param = Parameter(
                        code=code,
                        name=param_data.get('name'),
                        unit=param_data.get('unit'),
                        default=param_data.get('default'),
                        hex_val=param_data.get('hex'),
                        decimal_val=param_data.get('decimal'),
                        validation=param_data.get('validation')
                    )
                    self.parameters[code] = param
            print(f"Parameters loaded successfully from {self.json_file_path}")
        except FileNotFoundError:
            print(f"Fehler: {self.json_file_path} nicht gefunden.")
        except json.JSONDecodeError:
            print(f"Fehler: {self.json_file_path} konnte nicht dekodiert werden.")
        except Exception as e:
            print(f"Fehler beim Laden der Parameter: {e}")

        # Load FunIN definitions
        try:
            fun_in_path = resource_path(self.fun_in_path)
            with open(fun_in_path, mode='r', encoding='utf-8') as file:
                fun_in_data = json.load(file)
                self.fun_in_map = {item['Option']: item for item in fun_in_data}
            print(f"FunIN definitions loaded successfully from {self.fun_in_path}")
        except FileNotFoundError:
            print(f"Fehler: {self.fun_in_path} nicht gefunden.")
        except json.JSONDecodeError:
            print(f"Fehler: {self.fun_in_path} konnte nicht dekodiert werden.")
        except Exception as e:
            print(f"Fehler beim Laden der FunIN-Definitionen: {e}")

        # Load FunOUT definitions
        try:
            fun_out_path = resource_path(self.fun_out_path)
            with open(fun_out_path, mode='r', encoding='utf-8') as file:
                 fun_out_data = json.load(file)
                 self.fun_out_map = {item['Option']: item for item in fun_out_data}
            print(f"FunOUT definitions loaded successfully from {self.fun_out_path}")
        except FileNotFoundError:
            print(f"Fehler: {self.fun_out_path} nicht gefunden.")
        except json.JSONDecodeError:
            print(f"Fehler: {self.fun_out_path} konnte nicht dekodiert werden.")
        except Exception as e:
            print(f"Fehler beim Laden der FunOUT-Definitionen: {e}")

    def get_parameter(self, code):
        return self.parameters.get(code)

    def get_all_parameters(self):
        return list(self.parameters.values())
        
    def get_all_parameters_raw(self):
        return self.raw_parameters

# Example Usage (for testing)
if __name__ == "__main__":
    manager = ParameterManager()
    manager.load_parameters()

    # Test retrieving a specific parameter
    param_p02_00 = manager.get_parameter("P02-00")
    if param_p02_00:
        print(f"\nDetails for P02-00: {param_p02_00.name}")
    
    # Test FunIN/FunOUT loading
    print(f"\nLoaded {len(manager.fun_in_map)} FunIN definitions.")
    print(f"Example FunIN '1': {manager.fun_in_map.get('1')}")
    
    print(f"\nLoaded {len(manager.fun_out_map)} FunOUT definitions.")
    print(f"Example FunOUT '5': {manager.fun_out_map.get('5')}")