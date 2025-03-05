
import sys 
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))


from utils.logger import logger
from config.config_handler import DeviceConfigHandler
from instruments.controllers import SensorManager 
from utils.timer import IntervalTimer

class ExperimentHandler: 
    def __init__(self, socket): 
        self.duration = 0
        self.socket = socket 
        self.device_handler = DeviceConfigHandler()
        self.device = self.device_handler.get_config()
        self.sensors = []
        self.timer = IntervalTimer()
        self.sensor_manager = SensorManager(socket, self.send_data_to_client)
       
    def update_socket(self, socket):
        self.socket = socket 

    def start_experiment(self, data): 
        logger.info("Starting the experiment")
        self.initiate_sensors(data)
        self.start_experiment_timer()

    def pause_experiment(self, data): 
        logger.info("Pausing the experiment")
        self.timer.stop()
        self.sensor_manager.pause_controllers()

    def resume_experiment(self, data): 
        logger.info("Resuming the experiment")
        self.start_experiment_timer()
        self.sensor_manager.start(dataAquisitionInterval=data["dataAquisitionInterval"])


    def stop_experiment(self, data): 
        logger.info("Stoping the experiment")
        self.timer.stop()
        self.duration = 0
        self.sensor_manager.stop_controllers()

    def initiate_sensors(self, data): 
        conf = self.device_handler.get_configuration_by_id(data["configurationID"])
        if len(conf) != 1:
            raise FileNotFoundError("No config or more than one config found") 
        locations = conf[0]["locations"]
        self.sensor_manager.register_sensors(locations=locations)
        self.sensor_manager.start(dataAquisitionInterval=data["dataAquisitionInterval"])
       

    def start_experiment_timer(self):
        self.timer.start(1, self.update_duration)

    def update_duration(self): 
        self.duration = self.duration + 1
        self.socket.emit("update_experiment_status", {
            "duration": self.duration
        })

    def send_data_to_client(self, data): 
        self.socket.emit("sensor_data", {
            "deviceID": self.device["id"],
            "data": [{**d, "x": self.duration} for d in data]
        })
