
import sys 
from pathlib import Path
import asyncio

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))


from utils.logger import logger
from config.config_handler import DeviceConfigHandler
from instruments.controllers import PHController 
from utils.timer import IntervalTimer


class ExperimentHandler: 
    def __init__(self, socket): 
        self.duration = 0
        self.socket = socket 
        self.device_handler = DeviceConfigHandler()
        self.device = self.device_handler.get_config()
        self.sensors = []
        self.timer = IntervalTimer()

    def update_socket(self, socket):
        self.socket = socket 

    def start_experiment(self, data): 
        logger.info("Starting the experiment")
        self.initiate_sensors(data["configurationID"])
        self.initiate_experiment_timer()

    def stop_experiment(self, data): 
        logger.info("Stoping the experiment")
        self.timer.stop()
        self.duration = 0
        self.sensors = []

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
            # controler.run()
            self.sensors.append(controler)

    def initiate_experiment_timer(self):
        self.timer.start(1, self.update_duration)

    def update_duration(self): 
        self.duration = self.duration + 1
        self.socket.emit("update_experiment_status", {
            "duration": self.duration
        })



    def send_data_to_client(self, data): 
        self.socket.emit("sensor_data", data)
        logger.info("Sensor data sent to the client")