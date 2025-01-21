import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import uuid
from .validation_handler import Validator


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigHandler:
    def __init__(self, config_path: str = 'src/config/config_files/device_config.json'):
        self.config_path = Path(config_path)
        self.config = self._load_config()
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

    def update_config(self, config: Dict[str, Any]) -> bool:
        
        """Update configuration if valid."""
        new_config = {
            **self.config,
            **config,
        }
        config_validator = Validator(new_config)

        if  config_validator._validate_config():
            new_config['last_updated'] = datetime.now().isoformat()
            self.config = new_config
            self._save_config(new_config)
            logger.info("Configuration file successfully updated")
            return True
        return False

   



if __name__ == "__main__":
    config = ConfigHandler()
    if config.update_config({
         "id": "world",
        "name": "pH Monitor Device2",
        "configurations": [
            {
            "id": "dfbndgn",
            }
        ],
    }):
        print("Config updated")
    else: 
        print("Error on updating config")