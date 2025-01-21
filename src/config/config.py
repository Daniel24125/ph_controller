import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigHandler:
    def __init__(self, config_path: str = '.device_config.json'):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load device configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    print(self.config_path)
                    return json.load(f)
            else:
                default_config = {
                    "device_id": "pH_monitor_01",
                    "sensors": [],
                    "last_updated": datetime.now().isoformat()
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
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix('.json.bak')
                self.config_path.rename(backup_path)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update configuration if valid."""
        if self._validate_config(new_config):
            new_config['last_updated'] = datetime.now().isoformat()
            self.config = new_config
            self._save_config(new_config)
            return True
        return False

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration data."""
        required_fields = ['device_id', 'sensors']
        if not all(field in config for field in required_fields):
            return False
        
        # Validate sensors configuration
        for sensor in config.get('sensors', []):
            if not all(field in sensor for field in ['id', 'type']):
                return False
            if sensor['type'] not in ['temperature', 'pH']:
                return False
        
        return True



if __name__ == "__main__":
    config = ConfigHandler()
    #logger.info(config)