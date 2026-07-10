import board
import busio
from adafruit_ina219 import INA219

class Battery:

    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        self.ina219 = INA219(i2c)

    def read(self):

        return {
            "voltage": self.ina219.bus_voltage,
            "current": self.ina219.current / 1000,
            "power": self.ina219.power / 1000
        }
    