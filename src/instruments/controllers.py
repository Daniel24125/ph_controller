import time
try:
    import RPi.GPIO as GPIO
except ImportError:
    from utils.mock_gpio import GPIO

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
                both: connects to both the acidic and base pumps and actuates if the pH is above or below the target pH;

    """
    def __init__(self, acid_pump_pin, base_pump_pin, target_ph, check_interval=5, max_pump_time=30, margin=0.1, mode="acidic"):
        self.acid_pump_pin = acid_pump_pin
        self.base_pump_pin = base_pump_pin
        self.target_ph = target_ph
        self.check_interval = check_interval
        self.max_pump_time = max_pump_time
        self.margin = margin
        self.mode = mode
        self.init_gpio()

    def set_acid_pump_pin(self, pin):
        self.acid_pump_pin = pin

    def set_base_pump_pin(self, pin):
        self.base_pump_pin = pin

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
        if mode != "acidic" or mode != "alkaline" or mode != "both":
            raise NameError("You are trying to set the controller mode to an invalid mode. Available options: acidic | alkaline | both")
        self.mode = mode

    def init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.acid_pump_pin, GPIO.OUT)
        GPIO.setup(self.base_pump_pin, GPIO.OUT)


    def read_ph(self):
        # This method should be implemented to read pH from your sensor
        # For now, we'll use a placeholder
        return 7.15

    def calculate_pump_time(self, current_ph):
        ph_difference = abs(self.target_ph - current_ph)
        # Scale the pump time based on pH difference, max 10 seconds
        pump_time = min(ph_difference * 2, self.max_pump_time)
        return pump_time

    def determine_pump(self, current_ph):
        is_acidic = current_ph < self.target_ph ## if the solution is acidic, you need to pump a base solution
        define_base_pump = self.mode == "alkaline" or self.mode == "both"
        define_acid_pump = self.mode == "acidic" or self.mode == "both"
        if is_acidic and define_base_pump:
            print("Base pump activated!")
            pump_pin = self.base_pump_pin
        elif not is_acidic and define_acid_pump:
            print("Acidic pump activated!")
            pump_pin = self.acid_pump_pin
        else:
            return  # pH is at target, no adjustment needed
        return pump_pin

    def adjust_ph(self):
        current_ph = self.read_ph()
        if self.target_ph - self.margin <= current_ph <= self.target_ph + self.margin:
            print("pH value with the margin values. No adjustment necessary")
            return
        pump_pin = self.determine_pump(current_ph)
        if not pump_pin: 
            return 
        pump_time = self.calculate_pump_time(current_ph)
        print(f"Pumping for {pump_time} seconds")
        self.actviate_pump(pump_pin, pump_time)

    def actviate_pump(self, pump_pin, pump_time):
        GPIO.output(pump_pin, GPIO.HIGH)
        time.sleep(pump_time)
        GPIO.output(pump_pin, GPIO.LOW)

    def run(self):
        print("Running the pH Controller")
        try:
            while True:
                self.adjust_ph()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            GPIO.cleanup()
            print("Operation aborted by the user...")

if __name__ == "__main__":
    # Usage example:
    controller = PHController(acid_pump_pin=17, base_pump_pin=18, target_ph=7.0)
    try: 
        controller.set_mode("acidic")
    except NameError as err:
        GPIO.cleanup()
        print("An error occured: ", err)
