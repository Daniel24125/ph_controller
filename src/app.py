
import socketio
import logging
from typing import Dict, Any
from pathlib import Path
import os
from dotenv import load_dotenv
from config.config_handler import DeviceConfigHandler, Validator

# Load environment variables from .env.local
env_path = Path('.env.local')
load_dotenv(dotenv_path=env_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeviceSocketClient:
    def __init__(
        self, 
        server_url: str = None
    ):
        self.sio = socketio.Client()
        self.server_url = server_url or os.getenv('SOCKET_SERVER_URL')
        self.config_handler = DeviceConfigHandler()
        self.connected = False
        self.event_handlers_registrations()
        self.validator = Validator()

    def event_handlers_registrations(self):
        # Register event handlers
        self.sio.on('connect', self._handle_connect)
        self.sio.on('disconnect', self._handle_disconnect)
        self.sio.on('updateDeviceConfig', self._handle_config_update)
        self.sio.on('requestConfig', self._handle_config_request)

    def _handle_connect(self) -> None:
        """Handle successful connection to server."""
        self.connected = True
        logger.info(f"Connected to server: {self.server_url}")
        # Send initial device configuration
        self.sio.emit("register_client", "rpi")
        self.sio.emit("get_rpi_config", self.config_handler.get_config())

    def _handle_disconnect(self) -> None:
        """Handle disconnection from server."""
        self.connected = False
        logger.info("Disconnected from server")

    def _handle_config_update(self, cmd: Dict[str, Any]) -> None:
        """
            Handle configuration update from server.
            args: 
                cmd: {
                    context: device | configuration | location | sensor, 
                    operation: read | create | update | delete
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
            self.validator.validateConfigOperationCommand(cmd)

        except Exception as e:
            logger.error(f"Error handling config update: {e}")
            self.sio.emit('error', {
                'message': str(e),
                'device_id': self.config_handler.get_config().get('id')
            })

    def _handle_config_request(self) -> None:
        """Handle configuration request from server."""

        # self.sio.emit('configResponse', self.config_handler.get_config())

    def send_sensor_data(self, sensor_data: Dict[str, Any]) -> None:
        """Send sensor data to server."""
        if self.connected:
            print("Send data")
            # self.sio.emit('sensorData', {
            #     'device_id': self.config_handler.get_config().get('device_id'),
            #     'data': sensor_data
            # })
        else:
            logger.warning("Not connected to server. Cannot send sensor data.")

    def connect(self) -> None:
        """Connect to the Socket.IO server."""
        try:
            self.sio.connect(self.server_url)
        except Exception as e:
            logger.error(f"Connection error: {e}")

    def disconnect(self) -> None:
        """Disconnect from the Socket.IO server."""
        if self.connected:
            self.sio.disconnect()

    def start(self) -> None:
        """Start the Socket.IO client with automatic reconnection."""
        while True:
            try:
                if not self.connected:
                    self.connect()
                self.sio.wait()
            except Exception as e:
                logger.error(f"Error in client: {e}")
                if self.connected:
                    self.disconnect()

if __name__ == "__main__": 
    try:
        socket = DeviceSocketClient(server_url="http://localhost:8000")
        socket.start()
    except KeyboardInterrupt:
        logger.info("Disconnecting from the server") 
        socket.disconnect()
