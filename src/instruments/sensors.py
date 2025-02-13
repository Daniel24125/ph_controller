
import json
import RPi.GPIO as GPIO
import threading
import time
import datetime

def get_config():
    try:
        with open('/home/pi/Desktop/RPi_socket_client/config.txt') as json_file:
            return json.load(json_file)
    except Exception as err: 
        print(err)

class PhSensor():
    """
        Class associated with the pH sensor registration. 
    """

    def __init__(self, rpi_socket, analog):
        
        self.invert = True
        self.init_ph_sensor()
        self.analog = analog
        self.cancel_calibration = False
        self.listen_for_adjust_ph=False
    

    # This method is responsible for setting the GPIO setup and output 
    def init_ph_sensor(self): 
        GPIO.setmode(GPIO.BCM)


    # This method is responsible for determining if the pH reading is stable 
    def is_stable_sd(self,ph_sd, sd_th=0.07):
        return ph_sd < sd_th

    # This method is responsible for sending the pH sensor stability 
    # during calibration
    def send_read_stability(self, digestion_class):  
        self.cancel_calibration = False
        while not self.cancel_calibration:
            is_stable = self.is_stable_sd(digestion_class.ph_sd)
            
            self.rpi_socket.emit("rpi_cmd",json.dumps({
                "context": "update_ph_calibration",
                "stable": bool(is_stable),
                "msg": "Stable Reading..." if is_stable else "Unstable Reading...",
                "initiated": True
            }), namespace="/rpi")
            time.sleep(1)
    
    # This method is responsible for shutting down the pH sensor calibration
    def cancel_cal(self): 
        print("Canceling Calibration")
        self.cancel_calibration = True

    # This method is responsible for starting the calibration protocol
    def calibrate(self): 
        self.cancel_calibration = False
        active_data = {}
        active_data["4.03"] = self.check_ph()
        active_data["7.09"] = self.check_ph(ph=7.09)
        if not self.cancel_calibration: 
            self.save_config(active_data)
            print("The pH sensor was successfully calibrated")
            self.rpi_socket.emit("rpi_cmd",json.dumps({
                "context": "update_ph_calibration",
                "msg": "Calibration Completed",
                "complete": True
            }), namespace="/rpi")
        else: 
            print("Calibration canceled")

    # This method is responsible for saving the calibration data into the config file
    def save_config(self, ph, analog_value):
        data  = self.analog.get_config()
        has_error=False
        try:
            with open('modules/config.txt', "w") as json_file:
                data["pH_sensing"]["active"][ph] = analog_value
                data["pH_sensing"]["last_calibration"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                json.dump(data, json_file, indent=4)
        except Exception as err:  
            print("ERROR IN SAVE CONFIG")
            self.report_error(err)
            has_error=True
        return has_error

    # This method is responsible for reporting an error into the console.
    def report_error(self,err): 
        print("An error occured:")
        print(err)
        
    # This method is responsible for calculating the pumping time based on 
    # the current difference between the desired pH value and the actual pH 
    # reading. 
    def get_progressive_pumping_time(self, max_pumping_time,digestion_class, max_ph_diff=2):
        ph_diff = abs(self.desired_ph - digestion_class.ph)
        progressive_time = (max_pumping_time*ph_diff)/max_ph_diff
        volume = progressive_time*self.pump_flow/60
        return (volume, progressive_time)

    # This method is responsible for adjusting the pH of the RGM based on 
    # the desired pH value. 
    def adjust_ph(self, port, pump_time, invert, digestion_class):
        self.rpi_socket.emit("rpi_cmd",json.dumps({
            "context": "adjust_ph",
            "data": "acid" if port == self.acid_gpio else "base",
        }), namespace="/rpi")
        volume, prog_pumping_time = self.get_progressive_pumping_time(max_pumping_time=pump_time, digestion_class=digestion_class)
        print(f"Pumping for {prog_pumping_time} s; Corresponding Volume: {volume }")
        GPIO.output(port, not invert)
        time.sleep(prog_pumping_time)
        GPIO.output(port, invert)   
        self.rpi_socket.emit("rpi_cmd",json.dumps({
            "context": "adjust_ph",
            "data": "disabled",
        }), namespace="/rpi")
        self.rpi_socket.emit("rpi_cmd",json.dumps({
            "context": "add_volumes",
            "param": "hclVolume" if port == self.acid_gpio else "naohVolume",
            "volume": volume
        }), namespace="/rpi")
        
  
        
    # This method is responsible for monitoring the pH value and adjust the pH accordingly
    def listen_for_ph(self,digestion_class, th=0.1, pump_time=1, invert=True, check_time=20): 
        try: 
            GPIO.output(self.acid_gpio, invert)
            GPIO.output(self.base_gpio, invert)
            while self.listen_for_adjust_ph:
                print(f"Current pH: {round(digestion_class.ph, 2)} -> {self.desired_ph}")
                is_too_acid = bool(digestion_class.ph < (float(self.desired_ph) - th))
                is_too_base = bool(digestion_class.ph > (float(self.desired_ph) + th))
                if (is_too_acid or is_too_base): 
                    print("Adding Acid..."if is_too_base else "Adding Base")
                    port = self.acid_gpio if is_too_base else self.base_gpio
                    self.adjust_ph(port, pump_time, invert,digestion_class)   
                    while not self.is_stable_sd(digestion_class.ph_sd):
                        time.sleep(0.5)
                        print("\rWaiting for stability...", end=" ")
                time.sleep(check_time)
        except Exception as err: 
            print(err)
            print("ERROR IN listen_for_ph")
            self.shutdown()
    
    # This method is responsible for resetting the pH Sensor class
    def shutdown(self, pause=False):
        print("Shutting down")
        GPIO.output(self.acid_gpio, True)
        GPIO.output(self.base_gpio, True)
        self.listen_for_adjust_ph = False
        if(not pause):
            self.i = 1
            self.delay = 0
            self.user_delay = 0

    # This method is responsible for changing the peristaltic pumps' state
    def change_state(self, device, state): 
        if device == "hcl": 
            GPIO.output(self.acid_gpio, self.invert != state)
        else: 
            GPIO.output(self.base_gpio, self.invert != state)  
