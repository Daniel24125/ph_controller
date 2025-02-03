
import sys 
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))


from utils.logger import logger
from config.config_handler import DeviceConfigHandler
from instruments.controllers import PHController 

class ExperimentHandler: 
    def __init__(self, socket): 
        self.duration = 0
        self.socket = socket 
        self.device_handler = DeviceConfigHandler()
        self.device = self.device_handler.get_config()
        self.sensors = []

    def update_socket(self, socket):
        self.socket = socket 

    def start_experiment(self, data): 
        self.initiate_sensors(data["configurationID"])

    def initiate_sensors(self, configurationID): 
        conf = self.device_handler.get_configuration_by_id(configurationID)
        if len(conf) != 1:
            raise FileNotFoundError("No config or more than one config found") 
        
        locations = conf[0]["locations"]
        for loc in locations: 
            sensor = loc["sensors"][0]
            controler = PHController(
                    probe_port=sensor["probePort"],
                    valve_port=sensor["valvePort"],
                    target_ph=sensor["targetPh"],
                    check_interval=sensor["checkInterval"], 
                    max_pump_time=sensor["maxValveTimeOpen"],
                    margin=sensor["margin"],
                    mode=sensor["mode"]
                )
            controler.run()
            self.sensors.append(controler)


    def send_data_to_client(self, data): 
        self.socket.emit("sensor_data", data)
        logger.info("Sensor data sent to the client")