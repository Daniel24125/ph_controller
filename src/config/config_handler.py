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
from .validation_handler import Validator

forbidden_keys_info = ["id", "createdAt", "status", "configurations"]

# Device Configuration Validations
forbidden_keys_configuration_info = ["id", "createdAt", "locations"]
forbidden_keys_location_info = ["id", "createdAt", "sensors"]
forbidden_keys_sensor_info = ["id", "createdAt"]



class DeviceConfigHandler:
    def __init__(self, config_path: str = 'src/config/config_files/device_config.json'):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.validator = Validator()

  

    def _load_config(self) -> Dict[str, Any]:
        """Load device configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                default_config={
                    "id": uuid.uuid4(), 
                    "name": "pH Monitor Device",
                    "createdAt": datetime.now().isoformat(),
                    "isConnected": False,
                    "status": "ready",
                    "configurations": []
                }
                self._save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

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
        return self.config

    def parse_updated_info(self, info, forbidden_keys):
        for key in forbidden_keys: 
            if key in info: 
                logger.info(f"The new config has the attribute which will be removed: {key}")
                info.pop(key, None)
        return info

    def update_device_info(self, info: Dict[str, Any] )-> bool:
        parsedInfo = self.parse_updated_info(info, forbidden_keys_info)
        self._save_config({
            **self.config, 
            **parsedInfo
        })
        return True
    
    def update_device_configuration_info(self, info: Dict[str, Any] )-> bool:
        for i, conf in enumerate(self.config["configurations"]): 
            if conf["id"] == info["id"]:
                parsedInfo = self.parse_updated_info(info, forbidden_keys_configuration_info)
                self.config["configurations"][i] = {
                    **self.config["configurations"][i],
                    **parsedInfo
                }
        self._save_config(self.config)
        return True

    def add_device_configuration(self, data: Dict[str, Any] )-> bool:
        if not self.validator._validate_device_configuration(data): 
            logger.error("The configuration information submited does not contain the correct fields")
            return False
        self.config["configurations"].append(data)
        self._save_config(self.config)
        return True

    def delete_device_configuration(self, device_configuration_id): 
        for i, c in enumerate(self.config["configurations"]): 
            if c["id"] == device_configuration_id: 
                del self.config["configurations"][i]
        self._save_config(self.config)
        return True
    
    def update_location_info(self, data, configurationID, locationID):
        parsedInfo = self.parse_updated_info(data, forbidden_keys_location_info)
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

    def add_location(self, data, configurationID):
        if not self.validator._validate_location(data): 
            logger.error("The location information submited does not contain the correct fields")
            return False
        for i, conf in enumerate(self.config["configurations"]): 
            if conf["id"] == configurationID:
                self.config["configurations"][i]["locations"].append(data)
        self._save_config(self.config)
        return True

    def delete_location(self, device_configuration_id, locationID): 
        for i, c in enumerate(self.config["configurations"]): 
            if c["id"] == device_configuration_id: 
                for j, loc in enumerate(c["locations"]): 
                    if loc["id"] == locationID:
                        del self.config["configurations"][i]["locations"][j]
        self._save_config(self.config)
        return True

    def update_sensor_info(self, data, configurationID, locationID, sensorID):
        if not self.validator._validate_sensor(data):
            logger.error("The sensor information submited does not contain the correct fields")
            return False
        parsedInfo = self.parse_updated_info(data, forbidden_keys_sensor_info)
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

    def add_sensor(self, data, configurationID, locationID):
        if not self.validator._validate_sensor(data): 
            logger.error("The sensor information submited does not contain the correct fields")
            return False
        for i, conf in enumerate(self.config["configurations"]): 
            if conf["id"] == configurationID:
                for j, loc in enumerate(conf["locations"]):
                    if loc["id"] == locationID:
                        self.config["configurations"][i]["locations"][j]["sensors"].append(data)
        self._save_config(self.config)
        return True

    def delete_sensor(self, device_configuration_id, locationID, sensorID): 
        for i, c in enumerate(self.config["configurations"]): 
            if c["id"] == device_configuration_id: 
                for j, loc in enumerate(c["locations"]): 
                    if loc["id"] == locationID:
                        for k, sen in enumerate(loc["sensors"]): 
                            if sen["id"] == sensorID: 
                                del self.config["configurations"][i]["locations"][j]["sensors"][k]
        self._save_config(self.config)
        return True

if __name__ == "__main__":
    config = DeviceConfigHandler()
    if config.delete_sensor("woevbnwerojibjwfbnw", "sdkjvbirkejwbvweiojrg", "dsvdsvdsvsdv"):
        print("Config updated")
    else: 
        print("Error on updating config")