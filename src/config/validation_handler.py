import logging
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Validator: 
    def __init__(self, config):
        self.config = config

    def _validate_sensor(self, sensor: Dict[str, Any]) -> bool:
        """Validate sensor configuration."""
        required_fields = {
            'id': str,
            'mode': str,
            'margin': (int, float),
            'maxValveTimeOpen': (int, float),
            'targetPh': (int, float),
            'probePort': int,
            'valvePort': int,
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
        if sensor['mode'] not in ['acidic', 'basic']:
            logger.error("Invalid sensor mode")
            return False
        if not (0 < sensor['margin'] <= 1):
            logger.error("Invalid margin value")
            return False
        if not (0 < sensor['maxValveTimeOpen'] <= 300):
            logger.error("Invalid maxValveTimeOpen value")
            return False
        if not (0 <= sensor['targetPh'] <= 14):
            logger.error("Invalid targetPh value")
            return False

        return True

    def _validate_location(self, location: Dict[str, Any]) -> bool:
        """Validate location configuration."""
        required_fields = ['id', 'name', 'createdAt', 'sensor']
        if not all(field in location for field in required_fields):
            return False
        
        if not isinstance(location['sensor'], list):
            return False

        return all(self._validate_sensor(sensor) for sensor in location['sensor'])

    def _validate_config(self) -> bool:
        """Validate the complete configuration structure."""
        try:
            required_fields = ['id', 'name', 'createdAt', 'isConnected', 'status', 'configurations']
            if not all(field in self.config for field in required_fields):
                return False

            if not isinstance(self.config['configurations'], list):
                return False

            for configuration in self.config['configurations']:
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
