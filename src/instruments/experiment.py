
import sys 
from pathlib import Path


# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime

from utils.logger import logger
from utils.timer import IntervalTimer
from utils.utils import DataBackupHandler
from config.config_handler import DeviceConfigHandler
from instruments.controllers import SensorManager 

backup_handler = DataBackupHandler()
device_handler = DeviceConfigHandler()
device = device_handler.get_config()
timer = IntervalTimer()

DATA_BACKUP_PERIOD = 10

class ExperimentHandler: 
    def __init__(self, socket, connection_handler): 
        self.socket = socket 
        self.connection_handler = connection_handler
        self.sensors = []
        self.sensor_manager = SensorManager(socket, self.send_data_to_client, self.send_log_to_client)
        self.reset_experimental_data()

    def reset_experimental_data(self): 
        self.experiment_data = {
            "duration": 0,
            "deviceID": device["id"],
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
        backup_handler.start_experiment()
        self.initiate_sensors(data)
        self.start_experiment_timer()
        self.send_log_to_client("info","Experiment started","Device")

    def pause_experiment(self, data): 
        logger.info("Pausing the experiment")
        timer.stop()
        self.sensor_manager.pause_controllers()

    def resume_experiment(self, data): 
        logger.info("Resuming the experiment")
        self.start_experiment_timer()
        self.sensor_manager.start(dataAquisitionInterval=data["dataAquisitionInterval"])

    def stop_experiment(self, data): 
        logger.info("Stoping the experiment")
        timer.stop()
        self.sensor_manager.stop_controllers()
        backup_handler.cleanup_experiment()
        self.reset_experimental_data()

    def initiate_sensors(self, data): 
        locations = self.get_experiment_locations(data["configurationID"])
        self.update_experimetal_data({
            **data,
            "status": "running"
        })
        self.sensor_manager.register_sensors(locations=locations)
        self.sensor_manager.start(dataAquisitionInterval=data["dataAquisitionInterval"])
    
    def is_experiment_ongoing(self): 
        return self.experiment_data["status"] == "running" or self.experiment_data["status"] == "busy"

    def get_experiment_locations(self, configurationID): 
        conf = device_handler.get_configuration_by_id(configurationID)
        if len(conf) != 1:
            raise FileNotFoundError("No config or more than one config found") 
        return conf[0]["locations"]
    
    def reset_location_data(self): 
        locations = self.get_experiment_locations(self.experiment_data["configurationID"])
        self.experiment_data["locations"] =  [{"id": l["id"], "data": []} for l in locations]
        self.experiment_data["logs"] = []
        
    
    def start_experiment_timer(self):
        timer.start(1, self.update_duration)

    def update_duration(self): 
        self.update_experimetal_data({"duration": self.experiment_data["duration"]+1})
        self.emit("update_experiment_status", {
            "duration": self.experiment_data["duration"]
        })

    def send_data_to_client(self, data): 
        data_points = []
        for i in range(len(data)):
            location_data = data[i]
            processed_data = {**location_data, "x": self.experiment_data["duration"]}
            data_points.append(processed_data)
            self.experiment_data["locations"][i]["data"].append({
                "x": processed_data["x"], 
                "y": processed_data["y"]
            })

        self.emit("sensor_data", {
            "deviceID": device["id"],
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
        self.experiment_data["logs"].append(log)
        self.emit("update_experiment_log", log)

    def update_experimetal_data(self, data): 
        self.experiment_data={
            **self.experiment_data, 
            **data
        }
        if self.experiment_data["duration"]%DATA_BACKUP_PERIOD == 0: 
            backup_handler.save_data(self.experiment_data)  
            self.reset_location_data() 


    def emit(self, channel, data): 
        if self.connection_handler.connected:
            self.socket.emit(channel, data)
      