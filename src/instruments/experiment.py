
import sys 
from pathlib import Path
import json 

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime

from utils.logger import logger
from utils.timer import IntervalTimer
from utils.utils import DataBackupHandler
from config.config_handler import DeviceConfigHandler
from instruments.controllers import SensorManager 

class ExperimentHandler: 
    def __init__(self, socket, connection_handler): 
        self.socket = socket 
        self.connection_handler = connection_handler
        self.device_handler = DeviceConfigHandler()
        self.device = self.device_handler.get_config()
        self.sensors = []
        self.timer = IntervalTimer()
        self.sensor_manager = SensorManager(socket, self.send_data_to_client, self.send_log_to_client)
        self.backup_handler = DataBackupHandler()
        self.reset_experimental_data()

    def reset_experimental_data(self): 
        self.experiment_data = {
            "duration": 0,
            "deviceID": self.device["id"],
            "projectID": None, 
            "dataAquisitionInterval": None,
            "configurationID": None,
            "userID": None,
            "status": "ready",
            "locations": [],
            "logs": [],
            "createdAt": None
        }

    def update_socket(self, socket):
        self.socket = socket 

    def start_experiment(self, data): 
        logger.info("Starting the experiment")
        self.initiate_sensors(data)
        self.start_experiment_timer()
        # self.backup_handler.start_experiment()
        logger.info(data)

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
        self.sensor_manager.stop_controllers()
        # self.backup_handler.cleanup_experiment()
        self.reset_experimental_data()

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
        self.update_experimetal_data({"duration": self.experiment_data["duration"]+1})
        self.emit("update_experiment_status", {
            "duration": self.experiment_data["duration"]
        })

    def send_data_to_client(self, data): 
        data_points = [{**d, "x": self.experiment_data["duration"]} for d in data]
        self.emit("sensor_data", {
            "deviceID": self.device["id"],
            "data": data_points
        })

    def send_log_to_client(self, type, desc, location): 
        print("Sending log to client from location: ", location)
        log ={
            # "id": uuid.uuid4(),
            "type": type,
            "desc": desc,
            "createdAt":  datetime.now().isoformat(),
            "location": location
        }
        self.emit("update_experiment_log", log)

    def update_experimetal_data(self, data): 
        self.experiment_data={
            **self.experiment_data, 
            **data
        }

    def emit(self, channel, data): 
        # self.backup_handler.save_data(channel, data)
        if self.connection_handler.connected:
            # If there's unsent data, send it first
            # unsent_data = self.backup_handler.get_unsent_data(channel)
            # for item in unsent_data:
            #     self.socket.emit(channel, item)
                
            # Now send current data
            self.socket.emit(channel, data)
        else:
            # Connection lost - save to temp file
           
            print(f"Connection lost - saving {channel} data to temporary file")
        