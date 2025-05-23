
import socketio
from typing import Dict, Any
from operator import itemgetter
import traceback
import sys
import signal
from instruments.experiment import ExperimentHandler, backup_handler
from utils.logger import logger
from settings import config_handler, validator, error_logger, SERVER_URL, TIMEOUT, INTERVAL_MINUTES, PING_URL
import time 
import requests


sio = socketio.Client(
    reconnection=True,
    reconnection_attempts=float('inf'),  # Unlimited reconnection attempts
    reconnection_delay=1,     # Initial delay
    reconnection_delay_max=30,  # Maximum delay between reconnections
    randomization_factor=0.5   # Add some jitter to reconnection timing
)

def ping_server():
    """
    Ping a server URL and log the response.
    Retries every 5 seconds if the connection times out.
    
    Returns:
        bool: True if ping was successful, False otherwise
    """
    try:
        response = requests.get(PING_URL, timeout=TIMEOUT)
        
        if response.status_code == 200:
            logger.info(f"Successfully pinged {PING_URL} - Status: {response.status_code}")
            return True
        else:
            logger.warning(f"Ping to {PING_URL} returned status code {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        logger.warning(f"Connection to {PING_URL} timed out. Retrying in 5 seconds...")
        time.sleep(5)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to ping {PING_URL}: {str(e)}")
        return False


def keep_server_alive():
     while True:
        logger.info("Trying to ping the server to keep it alive")
        ping_server()
        # Sleep for the specified interval
        time.sleep(INTERVAL_MINUTES * 60)

def signal_handler( sig, frame):
    logger.info("\nShutting down gracefully...")
    cleanup()
    
def cleanup():
    if sio.connected:
        sio.disconnect()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM,signal_handler)


class DeviceSocketClient:

    def __init__(self,server_url: str = None):
        self.server_url = server_url 
        self.connected = False
        self.event_handlers_registrations()
        self.experiment_handler = ExperimentHandler(sio, connection_handler=self)

    def parseCommands(self, command_data): 
        if not isinstance(command_data, dict) or "data" not in command_data or "cmd" not in command_data: 
            raise ValueError("Command data has invalid format") 
        
        commands = {
            "startExperiment": self.experiment_handler.start_experiment,
            "pauseExperiment": self.experiment_handler.pause_experiment,
            "resumeExperiment": self.experiment_handler.resume_experiment,
            "stopExperiment": self.experiment_handler.stop_experiment
        }
        
        if command_data["cmd"] not in commands:
            raise ValueError(f"Unknown command: {command_data['cmd']}")
        
        commands[command_data["cmd"]](command_data["data"])

    def event_handlers_registrations(self):
        # Register event handlers
        sio.on('connect', self._handle_connect)
        sio.on('disconnect', self._handle_disconnect)
        sio.on('updateDeviceConfig', self._handle_config_update)
        sio.on('command', self._receive_command)

   

    def _receive_command(self, command_data): 
        logger.info(f"Command received: {command_data}")
        try: 
            self.parseCommands(command_data)
        except Exception as err: 
            self.report_error(err)
            
    def apply_cmd(self, cmd):
        """Applies the received command after validation"""
        cmd_pipline={
            "device|update": {"fn": config_handler.update_device_info, "args": None},
            "configuration|create": {"fn": config_handler.add_device_configuration, "args": None},
            "configuration|update": {"fn": config_handler.update_device_configuration_info, "args": None},
            "configuration|delete": {"fn": config_handler.delete_device_configuration, "args": ["configurationID"]},
            "location|create": {"fn": config_handler.add_location, "args": ["configurationID"]},
            "location|update": {"fn": config_handler.update_location_info, "args": ["configurationID", "locationID"]},
            "location|delete": {"fn": config_handler.delete_location, "args": ["configurationID", "locationID"]},
            "sensor|create": {"fn": config_handler.add_sensor, "args": ["configurationID", "locationID"]},
            "sensor|update": {"fn": config_handler.update_sensor_info, "args": ["configurationID", "locationID", "sensorID"]},
            "sensor|delete": {"fn": config_handler.delete_sensor, "args": ["configurationID", "locationID", "sensorID"]},
        }
        context, operation, data = itemgetter("context", "operation", "data")(cmd)

        pipe_cmd = f"{context}|{operation}"
        pipeline_fn = cmd_pipline[pipe_cmd]["fn"]
        pipeline_args = cmd_pipline[pipe_cmd]["args"]
        if bool(pipeline_args): 
            args = [data[arg] for arg in pipeline_args]
            pipeline_fn(data, *args)
        else: 
            pipeline_fn(data)

    def _handle_connect(self) -> None:
        """Handle successful connection to server."""
        self.connected = True
        logger.info(f"Connected to server: {self.server_url}")
        # Send initial device configuration
        sio.emit("register_client", "rpi")
        sio.emit("get_rpi_config", config_handler.get_config())
        if self.experiment_handler.is_experiment_ongoing():
            unsent_data = backup_handler.get_full_backup_data()
            sio.emit("get_ongoing_experiment_data", unsent_data)

    def _handle_disconnect(self) -> None:
        """Handle disconnection from server."""
        self.connected = False
        logger.info("Disconnected from server")
        # self.reconnect_to_server()

    def reconnect_to_server(self):
        logger.info("Trying to reconnect...")
 
        tries = 10
        current_attempts = 0
        while tries > current_attempts: 
            self.connect()
            current_attempts = current_attempts + 1
            time.sleep(10)
            

    def _handle_config_update(self, cmd: Dict[str, Any]) -> None:
        """
            Handle configuration update from server.
            args: 
                cmd: {
                    context: device | configuration | location | sensor, 
                    operation: create | update | delete
                    data: {
                        id -> in CUD operations,
                        name -> U operations,
                        configurationData -> U operations, 
                        locationsData -> U operations,
                        sensorData -> U operations,
                    }
                }
        """ 
        
        try:
            logger.info(f"Received config update: {cmd}")
            validator.validateConfigOperationCommand(cmd)
            self.apply_cmd(cmd)
            sio.emit("refresh_device_data", config_handler.get_config())
        except Exception as e:
            logger.error(traceback.format_exc())
            self.report_error(f"Error handling config update: {e}")

    def connect(self) -> None:
        """Connect to the Socket.IO server."""
        try:
            sio.connect(self.server_url, retry=True)
        except Exception as e:
            self.report_error(f"Connection error: {e}")

    def disconnect(self) -> None:
        """Disconnect from the Socket.IO server."""
     
        if self.connected:
            sio.disconnect()


    def start(self) -> None:
        """Start the Socket.IO client with automatic reconnection."""
        while True:
            try:
                if not self.connected:
                    self.connect()
                sio.sleep(1)
            except Exception as e:
                self.report_error(f"Error in client: {e}")
                if self.connected:
                    cleanup()

    def report_error(self, err): 
        logger.error(f"An error occured in a device command: {err}")
        error_logger.log_error(err)
        if self.connected:
            sio.emit("error", {
                "message": f"An error occured in a device command: {err}",
                "device_id": config_handler.get_config()["id"]
            })

import threading

if __name__ == "__main__": 
    try:
        socket = DeviceSocketClient(server_url=SERVER_URL)
        thread = threading.Thread(target=keep_server_alive)
        
        thread.start()
        socket.start()

    except KeyboardInterrupt:
        logger.info("Disconnecting from the server") 
        cleanup() 
 