
import json
# try:
#     import RPi.GPIO as GPIO
# except ImportError:
#     from utils.mock_gpio import GPIO
try: 
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    import busio
    import board 
except Exception: 
    print("Activating simulation mode...")
    simulation_mode = True

import numpy as np
from scipy import stats
import random 

port_map = [ADS.P0, ADS.P1, ADS.P2, ADS.P3]

def get_config():
    try:
        with open('/home/pi/Desktop/RPi_socket_client/config.txt') as json_file:
            return json.load(json_file)
    except Exception as err: 
        print(err)

class AnalogCommunication:
    """
        This class is responsible for establishing an analog connection with de ADS1115 converter.
    """

    def __init__(self, sensor_config):
        self.listen = True
        self.error = False
        self.sensor_config = sensor_config
        self.analog_read = 0
        self.converted_read = 0
        self.ready = True
        self.random_gen = IncrementalRandomGenerator(3000,16000,50)
   
   
    def get_regression_params(self): 
        try:

            x = np.array([self.sensor_config["acidic_value"], self.sensor_config["alkaline_value"]]).astype(np.float64)
            y = np.array([4,7]).astype(np.float64)
            cal = stats.linregress(x,y)
            return (cal.slope, cal.intercept)
        except Exception as err: 
            self.error= True
            print("Error while getting regression params",err)

    # This method is responsible for getting an analog read of the sensors. The read value corresponds to an average of 20 reads (i.e., 20 by default)
    def get_read(self, NUM_MEAS_FOR_AVG=20):
        self.ready=False
        analog_values = np.zeros(NUM_MEAS_FOR_AVG)
        for i in range(NUM_MEAS_FOR_AVG):
            try: 
                if simulation_mode:
                    an_read = self.random_gen.get_next()
                else:     
                    i2c = busio.I2C(board.SCL, board.SDA)
                    an_read = AnalogIn(ADS.ADS1115(i2c), self.sensor_config["probe"]).value
                analog_values[i] = an_read
            except Exception as err: 
                pass
        mask = np.ma.masked_equal(analog_values,0).compressed()
        analog_avg = np.average(mask)
        self.ready=True
        return self.convert_analog(analog_avg)
    
    # This method is responsible for converting the analog read to the pH value according to the sensors' calibration curve
    def convert_analog(self, analog_read):
        m,b=self.get_regression_params()
        return round(analog_read*m+b, 2)
            
    # this method is responsible for updating the classes' current values for the pH sensor
    def update_current_values(self): 
        try: 
            while True:
                for i in range(len(self.sensor_list)): 
                    m,b=self.get_regression_params(self.sensor_list[i])
                    analog_read = self.get_read(self.port)
                    self.analog_read = analog_read
                    self.converted_read = round((analog_read-b)/m, 2)
        except Exception as err:
            print(err)
            self.error=True


class IncrementalRandomGenerator:
    def __init__(self, min_val=0, max_val=7, increment=0.1):
        self.min = min_val
        self.max = max_val
        self.increment = increment
        self.current = random.uniform(min_val, max_val)
    
    def get_next(self):
        direction = random.choice([-1, 1])
        self.current += direction * self.increment
        self.current = max(self.min, min(self.max, self.current))
        return round(self.current, 2)
    

if __name__ == "__main__": 
    sensor = AnalogCommunication()
    value = sensor.get_read()
    print(value)