from config.config_handler import DeviceConfigHandler, Validator
from utils.timer import IntervalTimer
from utils.utils import DataBackupHandler
from config.config_handler import DeviceConfigHandler, DeviceInputMappingHandler
from utils.logger import logger
from config.error_logger import ErrorLogger
config_handler = DeviceConfigHandler()
validator = Validator()
backup_handler = DataBackupHandler()
device_handler = DeviceConfigHandler()
device = device_handler.get_config()
timer = IntervalTimer()
port_mapper = DeviceInputMappingHandler()
error_logger = ErrorLogger("src/logs",None, 100,30)