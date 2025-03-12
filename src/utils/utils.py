
import json
from pathlib import Path
from datetime import datetime
import uuid
import os
import numpy as np
from scipy import stats
import random 

simulation_mode= False
try: 
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    import busio
    import board 
except Exception: 
    print("Activating simulation mode...")
    simulation_mode = True



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
                print(err)
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
    

class DataBackupHandler:
    def __init__(self, ):
        self.backup_dir = Path(os.path.join(os.getcwd(), "src/temp")) 
        
    def start_experiment(self):
        """Set up a new experiment backup session"""
        self.backup_dir.mkdir(exist_ok=True)
    
    def save_data(self, data):
        """Save data to a temporary file"""            
        if not hasattr(self, "backup_dir"): 
            print("ERROR: backup_dir not initialized")
            return 
        
        try:
            # Ensure backup_dir is a Path object
            if not isinstance(self.backup_dir, Path):
                self.backup_dir = Path(self.backup_dir)
            
            # Make sure the directory exists
            if not self.backup_dir.exists():
                print(f"Creating directory: {self.backup_dir}")
                self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create the file
            backup_file = self.backup_dir / f"exp_chunk_{uuid.uuid4()}.jsonl"
            print(f"Writing to file: {backup_file}")
            
            with open(backup_file, 'w') as f:
                f.write(json.dumps(data))
                f.flush()  # Ensure data is written to disk
                os.fsync(f.fileno())  # Force OS to write to physical storage
            # Verify the file was created
            if backup_file.exists():
                print(f"Successfully created file: {backup_file}")
            else:
                print(f"File creation failed. File doesn't exist: {backup_file}")
                
        except Exception as err: 
            print(f"ERROR type: {type(err).__name__}")
            print(f"ERROR message: {str(err)}")
            print(f"ERROR details: {repr(err)}")
            # Print stack trace for more details
            import traceback
            traceback.print_exc()
    
    def get_saved_files(self): 
        if not hasattr(self, "backup_dir"): 
            return []
        return os.listdir(self.backup_dir)
       
        
        
    def get_unsent_data(self):
        """Retrieve unsent data for a specific channel"""
        all_items = self.get_saved_files()
        unsent_data = []
        for item in all_items: 
            access_dir = os.path.join(self.backup_dir, item)
            is_file = os.path.isfile(access_dir)
            if is_file:  
                with open(access_dir, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            # unsent_data.append(entry['data'])
                        except json.JSONDecodeError:
                            pass
        return unsent_data
    
    def cleanup_experiment(self):
        """Remove all temporary files when experiment is complete"""
        if not self.backup_dir:
            return
            
        import shutil
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        

if __name__ == "__main__": 
    sensor = AnalogCommunication()
    value = sensor.get_read()
    print(value)