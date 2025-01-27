from typing import Dict, Any
import sys 
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from utils.logger import logger

required_fields = ["context", "operation", "data"]
context_values = ["device", "configuration", "location", "sensor"]
operations_values = ["read", "create", "update", "delete"]

class Validator: 
    def __init__(self):
        pass

    def validateConfigOperationCommand(self, cmd):
        """Parses the commands received from the server for device configuration operations""" 
        for field in required_fields: 
            if field not in cmd:
                raise ValueError(f"Missing required command field: {field}")
        if not cmd["context"] in context_values: 
            raise ValueError("The operation context you provided is invalid.")
        if not cmd["operation"] in operations_values: 
            raise ValueError("The operation type you provided is invalid.")
        
    def _validate_sensor(self, sensor: Dict[str, Any]) -> bool:
        """Validate sensor configuration."""
        required_fields = {
            'id': str,
            'mode': str,
            'margin': (int, float),
            'maxValveTimeOpen': (int, float),
            'targetPh': (int, float),
            'probePort': int,
            'checkInterval': (int, float),
            'createdAt': str
        }

        for field, field_type in required_fields.items():
            if field not in sensor:
                logger.error(f"Missing required sensor field: {field}")
                return False
            if not isinstance(sensor[field], field_type):
                logger.error(f"Invalid type for sensor field {field}")
                return False

        # Additional validation rules
        if sensor['mode'] not in ['acidic', 'alkaline', "auto"]:
            logger.error("Invalid sensor mode")
            return False
        if not (0 < sensor['margin'] <= 1):
            logger.error("Invalid margin value")
            return False
        if not (1 < sensor['maxValveTimeOpen'] <= 300):
            logger.error("Invalid maxValveTimeOpen value")
            return False
        if not (1 <= sensor['targetPh'] <= 14):
            logger.error("Invalid targetPh value")
            return False

        return True

    def _validate_location(self, location: Dict[str, Any]) -> bool:
        """Validate location configuration."""
        required_fields = ['id', 'name', 'createdAt', 'sensors']
        if not all(field in location for field in required_fields):
            logger.error("Some fields are missing in the location data")
            return False
        
        if not isinstance(location['sensors'], list):
            return False

        return all(self._validate_sensor(sensor) for sensor in location['sensors'])

    def _validate_device_configuration(self, device_conf):
        """Validate device configuration."""
        required_fields = ["id", "name", "createdAt", "locations"]
        if not all(field in device_conf for field in required_fields):
            logger.error("Some fields are missing in the device configuraion data")
            return False

        return all(self._validate_location(location) for location in device_conf['locations'])
    

    def _validate_config(self, config) -> bool:
        """Validate the complete configuration structure."""
        try:
            required_fields = ['id', 'name', 'createdAt', 'status', 'configurations']
            if not all(field in config for field in required_fields):
                return False

            if not isinstance(config['configurations'], list):
                return False

            for configuration in config['configurations']:
                if not all(field in configuration for field in ['id', 'createdAt', 'locations']):
                    return False
                
                if not isinstance(configuration['locations'], list):
                    return False

                if not all(self._validate_location(location) for location in configuration['locations']):
                    return False

            return True
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False

if __name__ == "__main__": 
    try: 
        validator = Validator()
        validator.validateConfigOperationCommand({
            "context": "device",
            "operation": "read",
            "data": "feioeoi"
        })
    except Exception as e:
        print(e)