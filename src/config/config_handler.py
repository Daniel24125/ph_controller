import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import uuid
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logger import logger
from config.validation_handler import Validator

_forbidden_keys_info = ["id", "createdAt", "status", "configurations"]

# Device Configuration Validations
_forbidden_keys_configuration_info = ["id", "createdAt", "locations"]
_forbidden_keys_location_info = ["id", "createdAt", "sensors"]
_forbidden_keys_sensor_info = ["id", "createdAt"]


class ConfigHandler(): 
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self._default_config = None

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save device configuration to file."""
        try:
            # Create backup before saving
            # if self.config_path.exists():
            #     backup_path = self.config_path.with_suffix('.json.bak')
            #     self.config_path.rename(backup_path)
            with open(self.config_path, 'w') as f:
                self.config = config
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config if hasattr(self, "config") else self._default_config

    def _load_file(self) -> Dict[str, Any]:
        """Load device configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                self._save_config(self._default_config)
                return self._default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def set_default_config(self, config): 
        self._default_config = config


class DeviceConfigHandler(ConfigHandler):
    def __init__(self, config_path: str ="src/config/config_files/device_config.json"):
        super().__init__(config_path)
        self.set_default_config({
            "id": uuid.uuid4(), 
            "name": "pH Monitor Device",
            "createdAt": datetime.now().isoformat(),
            "isConnected": False,
            "status": "ready",
            "configurations": []
        })
        self.config_path = Path(config_path)
        self.config = self._load_file()
        self.validator = Validator()
       
    def get_configuration_by_id(self, configurationID): 
        return [x for x in self.config["configurations"] if x["id"] == configurationID]

    def parse_updated_info(self, info, forbidden_keys):
        """Parses data received to be applied into the config file."""
        for key in forbidden_keys: 
            if key in info: 
                logger.info(f"The new config has the attribute which will be removed: {key}")
                info.pop(key, None)
        return info

    def update_device_info(self, info: Dict[str, Any] )-> bool:
        parsedInfo = self.parse_updated_info(info, _forbidden_keys_info)
        self._save_config({
            **self.config, 
            **parsedInfo
        })
        return True
    
    def add_device_configuration(self, data: Dict[str, Any] )-> bool:
        """Adds a new device configuration, i.e., new locations and sensors"""
        if len(self.config["configurations"]) == 3:
            self.report_error("You reached the maximum number of configurations on this device")

        if not self.validator._validate_device_configuration(data): 
            self.report_error("The configuration information submited does not contain the correct fields")
        self.config["configurations"].append(data)
        self._save_config(self.config)
        return True
 
    def update_device_configuration_info(self, info: Dict[str, Any] )-> bool:
        """Updates the device name"""
        for i, conf in enumerate(self.config["configurations"]): 
            if conf["id"] == info["id"]:
                parsedInfo = self.parse_updated_info(info, _forbidden_keys_configuration_info)
                self.config["configurations"][i] = {
                    **self.config["configurations"][i],
                    **parsedInfo
                }
        self._save_config(self.config)
        return True
    
    def delete_device_configuration(self,_, configurationID): 
        for i, c in enumerate(self.config["configurations"]): 
            if c["id"] == configurationID: 
                del self.config["configurations"][i]
        self._save_config(self.config)
        return True
    
    def add_location(self, data, configurationID):
        if not self.validator._validate_location(data): 
            self.report_error("The location information submited does not contain the correct fields")
        for i, conf in enumerate(self.config["configurations"]): 
            if conf["id"] == configurationID:
                self.config["configurations"][i]["locations"].append(data)
        self._save_config(self.config)
        return True
    
    def update_location_info(self, data, configurationID, locationID):
        parsedInfo = self.parse_updated_info(data, _forbidden_keys_location_info)
        for i, conf in enumerate(self.config["configurations"]): 
            if conf["id"] == configurationID:
                for j, loc in enumerate(conf["locations"]):
                    if loc["id"] == locationID:
                        self.config["configurations"][i]["locations"][j] = {
                            **self.config["configurations"][i]["locations"][j],
                            **parsedInfo
                        }
        self._save_config(self.config)
        return True
  
    def delete_location(self, _ , device_configuration_id, locationID): 
        for i, c in enumerate(self.config["configurations"]): 
            if c["id"] == device_configuration_id: 
                for j, loc in enumerate(c["locations"]): 
                    if loc["id"] == locationID:
                        del self.config["configurations"][i]["locations"][j]
        self._save_config(self.config)
        return True

    def add_sensor(self, data, configurationID, locationID):
        data = {
            **data, 
            "targetPh": int(data["targetPh"]) 
        }
        if not self.validator._validate_sensor(data): 
            self.report_error("The sensor information submited does not contain the correct fields")
        for i, conf in enumerate(self.config["configurations"]): 
            if conf["id"] == configurationID:
                for j, loc in enumerate(conf["locations"]):
                    if loc["id"] == locationID:
                        self.config["configurations"][i]["locations"][j]["sensors"].append(data)
        self._save_config(self.config)
        return True
    
    def update_sensor_info(self, data, configurationID, locationID, sensorID):
        if not self.validator._validate_sensor(data):
            logger.error("The sensor information submited does not contain the correct fields")
            self.report_error("The sensor information submited does not contain the correct fields")
        
        parsedInfo = self.parse_updated_info(data, _forbidden_keys_sensor_info)
        for i, conf in enumerate(self.config["configurations"]): 
            if conf["id"] == configurationID:
                for j, loc in enumerate(conf["locations"]):
                    if loc["id"] == locationID:
                        for k, sen in enumerate(loc["sensors"]): 
                            if sen["id"] == sensorID: 
                                self.config["configurations"][i]["locations"][j]["sensors"][k] = {
                                    **self.config["configurations"][i]["locations"][j]["sensors"][k] ,
                                    **parsedInfo
                                }
        self._save_config(self.config)
        return True
    
    def delete_sensor(self, _, device_configuration_id, locationID, sensorID): 
        for i, c in enumerate(self.config["configurations"]): 
            if c["id"] == device_configuration_id: 
                for j, loc in enumerate(c["locations"]): 
                    if loc["id"] == locationID:
                        for k, sen in enumerate(loc["sensors"]): 
                            if sen["id"] == sensorID: 
                                del self.config["configurations"][i]["locations"][j]["sensors"][k]
        self._save_config(self.config)
        return True

    def report_error(self, msg): 
        logger.error(msg)
        raise ValueError(msg) 


class DeviceInputMappingHandler(ConfigHandler): 
    def __init__(self, config_path: str ="src/config/config_files/device_input_map.json"):
        super().__init__(config_path)
        self._default_config = {
            "i1":{
                "probe": 0,
                "acidic": 9, #GPIO 0
                "alkaline": 11, #GPIO 2
                "acidic_value": 0,
                "alkaline_value": 0
            },
             "i2":{
                "probe": 1,
                "acidic": 13, #GPIO 2
                "alkaline": 15, #GPIO 3
                "acidic_value": 0,
                "alkaline_value": 0
            },
             "i3":{
                "probe": 2,
                "acidic": 16, #GPIO 4
                "alkaline": 18, #GPIO 5
                "acidic_value": 0,
                "alkaline_value": 0

            },
             "i4":{
                "probe": 3,
                "acidic": 19, #GPIO 12
                "alkaline": 21, #GPIO 13
                "acidic_value": 0,
                "alkaline_value": 0
            }
        }
        self.config = self._load_file()

    def get_probe_pin(self, input_number): 
        return self.get_sensor_key(input_number,"probe")

    def get_pump_pins(self, input_number): 
        config=self.get_input_number(input_number)
        return (config["acidic"], config["alkaline"])

    def set_calibration_value(self, input_number, value_channel, value):
        config = self.get_input_number(input_number)
        self.get_sensor_key(input_number, value_channel)
        config[value_channel] = value
        self._save_config({
            **self.config,
            input_number: config
        })

    def get_input_number(self, input_number):
        if not input_number in self.config: 
            raise ValueError("There is no input number configurtion for the provided input")
        return self.config[input_number]

    def get_sensor_key(self, input_number, key): 
        config = self.get_input_number(input_number)
        if not key in config: 
            raise ValueError("You are trying to access the value of an unknown key")
        return config[key]


if __name__ == "__main__":
    try:
        config = DeviceInputMappingHandler()
        pin = config.get_probe_pin("i1")
        config.set_calibration_value("i1", "acidic_value", 25000)
        print(pin)
    except Exception as err: 
        print(err)
 