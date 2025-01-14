from modules.error import *
import socket
import select
from modules.utils import Periodic, Timer
import json
import RPi.GPIO as GPIO
import threading
import time 
import numpy as np
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import busio
import board 
from scipy import stats
import datetime
import os
import glob

class AnalogCommunication():
    """
        This class is responsible for establishing an analog connection with de ADS1115 converter
        since both pressure and pH sensors are analog sensors.
    """

    # This method is a constructor method, responsible for initialing the
    # ads, rpi_socket, listen, error, ports, sensor_list, current_values,  
    # analog_values and ready variables as well as fetching the configurations 
    # of the pH and pressure sensors
    def __init__(self, rpi_socket,ports=[ADS.P1, ADS.P0], sensor_list=["pH_sensing", "pressure_sensor"]):
        i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(i2c)
        self.rpi_socket = rpi_socket
        self.config  = get_config()
        self.listen = True
        self.error = False
        self.ports= ports
        self.sensor_list=sensor_list
        self.current_values = {}
        self.analog_values = {}
        self.ready = True
   
    # This method is responsible for sending the sensor data to the client
    def send_sensor_data(self, sensor): 
        if self.listen and hasattr(self, "config"): 
            sensor_name = sensor[0]
            index = self.sensor_list.index(sensor_name)
            analog, sd, value, value_sd = self.get_read(sensor_name,self.ports[index])
            self.rpi_socket.emit("rpi_cmd",json.dumps({
                "context": sensor_name,
                "data": value
            }), namespace="/rpi")
     
     # This method is responsible for calculating the intercept and slope for the 
     # sensor's calibration curve. 
    def get_regression_params(self, term): 
        try:
            x = np.array(list(self.config[term]["active"].keys())).astype(np.float64)
            y = np.array(list(self.config[term]["active"].values())).astype(np.float64)
            cal = stats.linregress(x,y)
            return (cal.slope, cal.intercept)
        except Exception as err: 
            self.error= True
            print("Error while getting regression params",err)

    # This method is responsible for getting an analog read of the sensors
    # The read value corresponds to an average of 20 reads (i.e., 20 by default)
    def get_read(self,sensor,port,NUM_MEAS_FOR_AVG=20):
        self.ready=False
        analog_values = np.zeros(NUM_MEAS_FOR_AVG)
        converted_values = np.zeros(NUM_MEAS_FOR_AVG)
        for i in range(NUM_MEAS_FOR_AVG):
            try: 
                an_read = AnalogIn(self.ads, port).value
                analog_values[i] = an_read
                converted_values[i] = self.convert_analog(an_read,sensor)
            except Exception as err: 
                # print("Error on get_read")
                # print(err)
                # self.error=True
                pass
        mask = np.ma.masked_equal(analog_values,0).compressed()
        analog_avg = np.average(mask)
        converted = np.average(converted_values)
        converted_sd = np.std(converted_values) 
        self.ready=True
        return (analog_avg, np.std(mask), converted,converted_sd)
    
    # This method is responsible for converting the analog read to the 
    # pH or presusre value according to the sensors' calibration curve
    def convert_analog(self, analog_read, sensor):
        m,b=self.get_regression_params(sensor)
        return round((analog_read-b)/m, 2)
            
    # this method is responsible for updating the classes' current valeus 
    # for the pH and pressure sensors
    def update_current_values(self): 
        try: 
            while True:
                for i in range(len(self.sensor_list)): 
                    m,b=self.get_regression_params(self.sensor_list[i])
                    analog_read = self.get_read(self.ports[i])
                    self.analog_values[self.sensor_list[i]] = analog_read
                    self.current_values[self.sensor_list[i]] = round((analog_read-b)/m, 2)
        except Exception as err:
            print("ERROR ON UPDATE VALUES")
            print(err)
            error=True
    