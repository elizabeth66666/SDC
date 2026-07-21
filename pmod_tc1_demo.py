#!/usr/bin/env python3
"""
pmod_tc1_demo.py -- Raspberry Pi port of Digilent's PmodTC1 demo (main.c).

Reads temperature from a Digilent PmodTC1 (built around the Maxim MAX31855
thermocouple-to-digital converter) over the Raspberry Pi's hardware SPI and
streams it to the console in Fahrenheit and Celsius, twice per second.

Wiring (PmodTC1 SPI pins -> Raspberry Pi 40-pin header, using spidev 0.0):
    CS  -> GPIO8  / CE0  (pin 24)
    SDO -> GPIO9  / MISO (pin 21)
    SCK -> GPIO11 / SCLK (pin 23)
    VCC -> 3V3 (pin 1)
    GND -> GND (pin 6)

    PmodTC1 is read-only (MAX31855 has no data-input pin), so SDI/MOSI is
    left unconnected.

Requires: `pip install spidev` and SPI enabled via `raspi-config`.
"""

import time

import spidev


class PmodTC1Fault(Exception):
    """Raised when the MAX31855 reports a thermocouple fault."""


class PmodTC1:
    """Driver for the Digilent PmodTC1 (MAX31855) over Linux spidev."""

    def __init__(self, bus=0, device=0, max_speed_hz=1000000):
        self._spi = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.mode = 0
        self._spi.max_speed_hz = max_speed_hz

    def close(self):
        self._spi.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_temp_c(self):
        """Read the thermocouple junction temperature in Celsius."""
        raw = self._read_raw32()

        if raw & 0x1:
            raise PmodTC1Fault("open circuit (no thermocouple attached)")
        if raw & 0x2:
            raise PmodTC1Fault("thermocouple short to GND")
        if raw & 0x4:
            raise PmodTC1Fault("thermocouple short to VCC")

        temp_raw = (raw >> 18) & 0x3FFF
        if temp_raw & 0x2000:
            temp_raw -= 0x4000
        return temp_raw * 0.25

    def _read_raw32(self):
        data = self._spi.xfer2([0x00, 0x00, 0x00, 0x00])
        return (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]

    @staticmethod
    def temp_c_to_f(celsius):
        return celsius * 9.0 / 5.0 + 32.0


def demo_run(device):
    print("Starting Pmod TC1 Demo...")
    while True:
        try:
            celsius = device.get_temp_c()
            fahrenheit = PmodTC1.temp_c_to_f(celsius)
            print(f"Temperature: {fahrenheit:.6f} deg F   {celsius:.6f} deg C")
        except PmodTC1Fault as fault:
            print(f"Thermocouple fault: {fault}")
        time.sleep(0.5)


def main():
    with PmodTC1(bus=0, device=0) as device:
        try:
            demo_run(device)
        except KeyboardInterrupt:
            print("\nExiting.")


if __name__ == "__main__":
    main()
