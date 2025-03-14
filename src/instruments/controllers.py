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
from config.config_handler import DeviceInputMappingHandler, DeviceConfigHandler


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
    def __init__(self, location, send_log_to_client, update_client_pump_status, device_port, target_ph, max_pump_time=30, margin=0.1, mode="acidic"):
        self.device_port = device_port
        self.target_ph = target_ph
        self.max_pump_time = max_pump_time
        self.margin = margin
        self.mode = mode
        self.send_log_to_client = send_log_to_client
        self.update_client_pump_status = update_client_pump_status
        self.location = location
        self.init_sensor()
        self.init_gpio()
    
    def init_sensor(self): 
        self.is_running = False
        self.is_pumping_acid = False
        self.is_pumping_base = False
        self.port_mapper = DeviceInputMappingHandler()
        self.alkaline_pump_pin, self.acidic_pump_pin = self.port_mapper.get_pump_pins(self.device_port)
        self.comunicator = AnalogCommunication(
            sensor_config=self.port_mapper.get_input_number(self.device_port)
        )

    def set_mode(self, mode):
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
            pump_pin = self.alkaline_pump_pin
            pump = "alkaline"
        elif not is_acidic and define_acid_pump:
            print("Acidic pump activated!")
            pump_pin = self.acidic_pump_pin
            pump = "acidic"
        else:
            return  # pH is at target, no adjustment needed
        return (pump, pump_pin)

    def adjust_ph(self):
        current_ph = self.read_ph()
        if self.target_ph - self.margin <= current_ph <= self.target_ph + self.margin:
            print("pH value with the margin values. No adjustment necessary")
            return
        pump, pump_pin = self.determine_pump(current_ph)
        if not pump_pin: 
            return 
        pump_time = self.calculate_pump_time(current_ph)
        t = threading.Thread(target=self.change_pump_state, args=(pump, pump_pin , pump_time))
        t.start()

    def change_pump_state(self, pump, pump_pin, pump_time):
        if pump == "acidic": 
            self.is_pumping_acid = True
            self.activate_pump(pump_pin, pump_time)
            self.is_pumping_acid = False
        else: 
            self.is_pumping_base = True
            self.activate_pump(pump_pin, pump_time)
            self.is_pumping_base = False
        
    def activate_pump(self, pump_pin, pump_time):
        self.update_client_pump_status(self.location, "acidic" if pump_pin==self.acidic_pump_pin else self.alkaline_pump_pin, True)
        self.send_log_to_client("info", f"Pumping for {round(pump_time,2)} seconds", self.location)
        print(f"Pumping for {round(pump_time,2)} seconds")
        GPIO.output(pump_pin, GPIO.HIGH)
        time.sleep(pump_time)
        GPIO.output(pump_pin, GPIO.LOW)
        self.update_client_pump_status(self.location, "acidic" if pump_pin==self.acidic_pump_pin else self.alkaline_pump_pin, False)
        self.send_log_to_client("info", "Closing valve",self.location)
        
    def toggle_pump(self, pump, overide_status=None): 
        print(self.alkaline_pump_pin)
        if pump == "acidic": 
            if overide_status != None: 
                self.is_pumping_acid = not overide_status
            action = "Opening" if not self.is_pumping_acid else "Closing"
            GPIO.output(self.acidic_pump_pin, GPIO.HIGH if not self.is_pumping_acid else GPIO.LOW)
            self.send_log_to_client("info", f"{action} acidic pump", self.location)
            self.is_pumping_acid = not self.is_pumping_acid
        else: 
            if overide_status != None: 
                self.is_pumping_base = not overide_status
            action = "Opening" if not self.is_pumping_base else "Closing"
            GPIO.output(self.alkaline_pump_pin, GPIO.HIGH if not self.is_pumping_base else  GPIO.LOW)
            self.send_log_to_client("info", f"{action} alkaline pump", self.location)
            self.is_pumping_base = not self.is_pumping_base
        status = self.is_pumping_acid if pump == "acidic" else self.is_pumping_base
        return (pump, status)
        
        
    def stop(self): 
        self.is_running = False
        GPIO.cleanup()
        print("Monitorization stopped")
 

class SensorManager: 
    def __init__(self, socket, send_data, send_log):
        self.send_data = send_data
        self.controllers = []
        self.is_running = False
        self.socket = socket
        self.send_log_to_client = send_log
        self._register_device_listenners()
        self.device = DeviceConfigHandler().get_config()

    def _register_device_listenners(self):
        self.socket.on("toggle_pump", self._toggle_pump)

    def _toggle_pump(self, pump_data): 
        loc = pump_data["selectedLocation"]
        pump_type = pump_data["pump"]
        status = not loc["isAcidPumping"] if pump_type == "acidic" else not loc["isBasePumping"]
        location_sensor = loc["sensors"][0]
        
        sensor = PHController(
            location=loc["name"],
            send_log_to_client=self.send_log_to_client,
            update_client_pump_status=self.update_client_pump_status,
            device_port=location_sensor["devicePort"],
            target_ph=location_sensor["targetPh"],
            max_pump_time=location_sensor["maxValveTimeOpen"],
            margin=location_sensor["margin"],
            mode=location_sensor["mode"]
        ) 

        pump, status = sensor.toggle_pump(pump_type, status)


    def update_client_pump_status(self, location, pump, status): 
        print("Sending client the pump status")
        self.socket.emit("update_pump_status", {
            "deviceID": self.device["id"],
            "location": location ,
            "pump": pump ,
            "status": status ,
        })

    def register_sensors(self, locations): 
        
        for loc in locations:
            sensor = loc["sensors"][0]
            controler = {
                "location": loc,
                "controler": PHController(
                    location=loc["name"],
                    send_log_to_client=self.send_log_to_client,
                    update_client_pump_status=self.update_client_pump_status,
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
                time.sleep(int(dataAquisitionInterval))
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
    )]

    while True: 
        for controller in probes: 
            read = controller.read_ph()
            print(read)
        time.sleep(2)
    
    #controller.port_mapper.set_calibration_value(probe, "acidic_value", read)
    
