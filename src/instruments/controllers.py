import time

import sys 
from pathlib import Path
import threading
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
try:
    import RPi.GPIO as GPIO
except ImportError:
    from utils.mock_gpio import MockGPIO 
    GPIO = MockGPIO()

from utils.utils import  AnalogCommunication
from config.config_handler import DeviceInputMappingHandler


class PHController:
    """
        PHController class to monitor and control the pH of an aquous solution
        args: 
            acid_pump_pin: Pin in the RPi associated with the acid pump;
            base_pump_pin: Pin in the RPi associated with the base pump;
            target_ph: pH value that the user whats to reach;
            check_interval: period of time in seconds that the controller will compare the pH read with the target_pH;
            max_pump_time: maximum time in seconds that the pump/vsalve will be open;
            margin: the pH margin in wich the controller will accept the pH value;
            mode: controller mode. Possible values: 
                acidic: only connects to the acidic pump and only actuates if the pH is above the target pH;
                alkaline: only connects to the base pump and only actuates if the pH is below the target pH;
                auto: connects to both the acidic and base pumps and actuates if the pH is above or below the target pH;
    """
    def __init__(self, location, send_log_to_client, device_port, target_ph, max_pump_time=30, margin=0.1, mode="acidic"):
        self.device_port = device_port
        self.target_ph = target_ph
        self.max_pump_time = max_pump_time
        self.margin = margin
        self.mode = mode
        self.send_log_to_client = send_log_to_client
        self.location = location
        self.init_sensor()
        #self.init_gpio()
    
    def init_sensor(self): 
        self.is_running = False
        self.is_pumping = False
        self.port_mapper = DeviceInputMappingHandler()
        self.alkaline_pump_pin, self.acidic_pump_pin = self.port_mapper.get_pump_pins(self.device_port)
        self.comunicator = AnalogCommunication(
            sensor_config=self.port_mapper.get_input_number(self.device_port)
        )

    def set_mode(self, mode):
        print(mode)
        if mode != "acidic" or mode != "alkaline" or mode != "auto":
            raise NameError("You are trying to set the controller mode to an invalid mode. Available options: acidic | alkaline | auto")
        self.mode = mode

    def init_gpio(self):  
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.alkaline_pump_pin, GPIO.OUT)
        GPIO.setup(self.acidic_pump_pin, GPIO.OUT)

    def read_ph(self):
        try: 
            return self.comunicator.get_read()
        except Exception as err: 
            print(err)
            self.send_log_to_client("error", "An error occured while trying to aquire pH data: {err}", self.location )
            
    def calculate_pump_time(self, current_ph):
        ph_difference = abs(self.target_ph - current_ph)
        # Scale the pump time based on pH difference, max 10 seconds
        pump_time = min(ph_difference * 2, self.max_pump_time)
        return pump_time

    def determine_pump(self, current_ph):
        is_acidic = current_ph < self.target_ph ## if the solution is acidic, you need to pump a base solution
        define_base_pump = self.mode == "alkaline" or self.mode == "auto"
        define_acid_pump = self.mode == "acidic" or self.mode == "auto"
        if is_acidic and define_base_pump:
            print("Base pump activated!")
            pump_pin = self.base_pump_pin
        elif not is_acidic and define_acid_pump:
            print("Acidic pump activated!")
            # pump_pin = self.acid_pump_pin
        else:
            return  # pH is at target, no adjustment needed
        return pump_pin

    def adjust_ph(self):
        current_ph = self.read_ph()
        if self.target_ph - self.margin <= current_ph <= self.target_ph + self.margin:
            print("pH value with the margin values. No adjustment necessary")
            return
        # pump_pin = self.determine_pump(current_ph)
        # if not pump_pin: 
        #     return 
        pump_time = self.calculate_pump_time(current_ph)
        t = threading.Thread(target=self.actviate_pump, args=(self.acidic_pump_pin , pump_time))
        t.start()

    def actviate_pump(self, pump_pin, pump_time):
        if not self.is_pumping:
            self.is_pumping = True
            self.send_log_to_client("info", f"Openning valve for {round(pump_time,2)} seconds", self.location )
            print(f"Pumping for {round(pump_time,2)} seconds")
            GPIO.output(pump_pin, GPIO.HIGH)
            time.sleep(pump_time)
            GPIO.output(pump_pin, GPIO.LOW)
            self.is_pumping = False
            self.send_log_to_client("info", "Closing valve",self.location )

    def stop(self): 
        self.is_running = False
        GPIO.cleanup()
        print("Monitorization stopped")



class SensorManager: 
    def __init__(self, socket, send_data):
        self.send_data = send_data
        self.controllers = []
        self.is_running = False
        self.socket = socket

    def register_sensors(self, locations): 
        
        for loc in locations:
            sensor = loc["sensors"][0]
            controler = {
                "location": loc,
                "controler": PHController(
                    location=loc["name"],
                    send_log_to_client=self.send_log_to_client,
                    device_port=sensor["devicePort"],
                    target_ph=sensor["targetPh"],
                    max_pump_time=sensor["maxValveTimeOpen"],
                    margin=sensor["margin"],
                    mode=sensor["mode"]
                )  
            }
            self.controllers.append(controler)
    
    def start(self, dataAquisitionInterval):
        print("Starting the Timer")
        if not hasattr(self, "dataAquisitionInterval"): 
            self.dataAquisitionInterval = dataAquisitionInterval
        self.is_running = True
        self.thread = threading.Thread(target=self.run_controllers, args=(self.dataAquisitionInterval,))
        self.thread.start()

    def run_controllers(self, dataAquisitionInterval): 
        try:
            while self.is_running:
                send_data = []
                for con in self.controllers: 
                    controler = con["controler"]
                    read = controler.read_ph()
                    send_data.append({
                        "id": con["location"]["id"],
                        "y": read
                    })
                    controler.adjust_ph()
                self.send_data(send_data)
                
                time.sleep(dataAquisitionInterval)
        except Exception as err:
            print(err)
            GPIO.cleanup()
            print("Operation aborted by the user...")
            self.send_log_to_client("error", f"An error occured during data aquisition: {err}", "Device")
           
    def pause_controllers(self): 
        self.is_running = False

    def stop_controllers(self): 
        self.is_running = False
        self.controllers = []
        GPIO.cleanup()
        print("Monitorization stopped")

    def send_log_to_client(self, type, desc, location): 
        print("Sending log to client from location: ", location)
        log ={
            # "id": uuid.uuid4(),
            "type": type,
            "desc": desc,
            "createdAt":  datetime.now().isoformat(),
            "location": location
        }
        self.socket.emit("update_experiment_log", log)

if __name__ == "__main__":
    pass
     # Usage example:
    probe = "i4"
    probes = [ PHController(
        location=None, 
        send_log_to_client=None,
        device_port=probe, 
        target_ph=7.0, 
        mode="acidic"
    ),  PHController(
        location=None, 
        send_log_to_client=None,
        device_port=probe, 
        target_ph=7.0, 
        mode="acidic"
    ),  PHController(
        location=None, 
        send_log_to_client=None,
        device_port=probe, 
        target_ph=7.0, 
        mode="acidic"
    ),  PHController(
        location=None, 
        send_log_to_client=None,
        device_port=probe, 
        target_ph=7.0, 
        mode="acidic"
    )]
    while True: 
        for controller in probes: 
            read = controller.read_ph()
            print(read)
        time.sleep(2)
    
    #controller.port_mapper.set_calibration_value(probe, "acidic_value", read)
    
