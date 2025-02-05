import time

import sys 
from pathlib import Path
import threading
# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

try:
    import RPi.GPIO as GPIO
except ImportError:
    from utils.mock_gpio import MockGPIO 
    GPIO = MockGPIO()

from utils.utils import IncrementalRandomGenerator

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
    def __init__(self, probe_port, valve_port, target_ph, check_interval=5, max_pump_time=30, margin=0.1, mode="acidic"):
        self.probe_port = probe_port
        self.valve_port = valve_port
        self.target_ph = target_ph
        self.check_interval = check_interval
        self.max_pump_time = max_pump_time
        self.margin = margin
        self.mode = mode
        self.is_running = False
        self.is_pumping = False
        self.random_gen = IncrementalRandomGenerator(1,12,0.1)
        self.init_gpio()

    def set_probe_port(self, pin):
        self.probe_port = pin

    def set_valve_port(self, pin):
        self.valve_port = pin

    def set_target_ph(self, ph):
        self.target_ph = ph

    def set_check_interval(self, interval):
        self.check_interval = interval

    def set_max_pump_time(self, time):
        self.max_pump_time = time
    
    def set_margin(self, ph_margin):
        self.margin = ph_margin
    
    def set_mode(self, mode):
        print(mode)
        if mode != "acidic" or mode != "alkaline" or mode != "auto":
            raise NameError("You are trying to set the controller mode to an invalid mode. Available options: acidic | alkaline | auto")
        self.mode = mode

    def init_gpio(self):
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.probe_port, GPIO.OUT)
        GPIO.setup(self.valve_port, GPIO.OUT)

    def read_ph(self):
        # This method should be implemented to read pH from your sensor
        # For now, we'll use a placeholder
        return self.random_gen.get_next()

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
        t = threading.Thread(target=self.actviate_pump, args=(self.valve_port, pump_time))
        t.start()

    def actviate_pump(self, pump_pin, pump_time):
        if not self.is_pumping:
            self.is_pumping = True
            print(f"Pumping for {pump_time} seconds")
            GPIO.output(pump_pin, GPIO.HIGH)
            time.sleep(pump_time)
            GPIO.output(pump_pin, GPIO.LOW)
            self.is_pumping = False

    def run(self):
        print("Running the pH Controller")
        self.is_running = True
        try:
            while self.is_running:
                self.adjust_ph()
                time.sleep(self.check_interval)
        except Exception as err:
            print(err)
            GPIO.cleanup()
            print("Operation aborted...")

    def stop(self): 
        self.is_running = False
        GPIO.cleanup()
        print("Monitorization stopped")



class SensorManager: 
    def __init__(self, send_data):
        self.send_data = send_data
        self.controllers = []
        self.is_running = False

    def register_sensors(self, locations): 
        
        for loc in locations:
            sensor = loc["sensors"][0]
            controler = {
                "location": loc,
                "controler": PHController(
                    probe_port=sensor["probePort"],
                    valve_port=sensor["valvePort"],
                    target_ph=sensor["targetPh"],
                    check_interval=2, 
                    max_pump_time=sensor["maxValveTimeOpen"],
                    margin=sensor["margin"],
                    mode=sensor["mode"]
                )  
            }
            self.controllers.append(controler)
    
    def start(self, dataAquisitionInterval):
        print("Starting the Timer")
        self.is_running = True
        self.thread = threading.Thread(target=self.run_controllers, args=(dataAquisitionInterval,))
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
        

    def stop_controllers(self): 
        self.is_running = False
        self.controllers = []
        GPIO.cleanup()
        print("Monitorization stopped")

if __name__ == "__main__":
    pass
    # # Usage example:
    # controller = PHController(acid_pump_pin=17, base_pump_pin=18, target_ph=7.0)
    # try: 
    #     controller.set_mode("acidic")
    # except NameError as err:
    #     GPIO.cleanup()
    #     print("An error occured: ", err)
