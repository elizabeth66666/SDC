#!/usr/bin/env python3
# Tells the shell which interpreter to run this file with if executed directly.
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
# The block above is the module docstring; it documents the file's purpose,
# the wiring needed, and setup requirements.

import time
# Standard library module used for time.sleep() to pace the read loop.

import spidev
# Third-party module that gives Python access to the Pi's /dev/spidev*
# kernel SPI device nodes.


class PmodTC1Fault(Exception):
    # Custom exception class, subclassing the built-in Exception.
    """Raised when the MAX31855 reports a thermocouple fault."""
    # Docstring explaining when this exception is raised.
    # (no body needed beyond the docstring; Exception already does the work)


class PmodTC1:
    # Defines the driver class that talks to the PmodTC1/MAX31855 chip.
    """Driver for the Digilent PmodTC1 (MAX31855) over Linux spidev."""
    # Docstring describing the class's purpose.

    def __init__(self, bus=0, device=0, max_speed_hz=1000000):
        # Constructor: bus/device select which /dev/spidev{bus}.{device}
        # node to open; max_speed_hz sets the SPI clock rate (1 MHz here).
        self._spi = spidev.SpiDev()
        # Create a new SpiDev object; the SPI device isn't open yet.
        self._spi.open(bus, device)
        # Open /dev/spidev{bus}.{device}, e.g. /dev/spidev0.0.
        self._spi.mode = 0
        # SPI mode 0 (CPOL=0, CPHA=0), which is what the MAX31855 requires.
        self._spi.max_speed_hz = max_speed_hz
        # Set the SPI clock speed to the value passed in (default 1 MHz).

    def close(self):
        # Releases the underlying SPI file handle.
        self._spi.close()
        # Closes /dev/spidev{bus}.{device}.

    def __enter__(self):
        # Called when the object is used in a "with PmodTC1(...) as x:" block.
        return self
        # Return this same instance so it can be bound to "as device".

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Called automatically when the "with" block is exited, even on error.
        self.close()
        # Ensure the SPI device is always closed when leaving the block.

    def get_temp_c(self):
        # Public method: returns the thermocouple temperature in Celsius.
        """Read the thermocouple junction temperature in Celsius."""
        # Docstring describing what this method returns.
        raw = self._read_raw32()
        # Read the raw 32-bit word out of the MAX31855 over SPI.

        if raw & 0x1:
            # Bit 0 is the "open circuit" fault flag.
            raise PmodTC1Fault("open circuit (no thermocouple attached)")
            # No thermocouple is connected; report it as a fault.
        if raw & 0x2:
            # Bit 1 is the "short to GND" fault flag.
            raise PmodTC1Fault("thermocouple short to GND")
            # Thermocouple wire is shorted to ground; report it as a fault.
        if raw & 0x4:
            # Bit 2 is the "short to VCC" fault flag.
            raise PmodTC1Fault("thermocouple short to VCC")
            # Thermocouple wire is shorted to the supply rail; report it.

        temp_raw = (raw >> 18) & 0x3FFF
        # Shift out the low 18 bits (internal-junction temp + fault bits),
        # then mask to the 14 bits that hold the thermocouple temperature.
        if temp_raw & 0x2000:
            # Bit 13 of the 14-bit field is the sign bit (two's complement).
            temp_raw -= 0x4000
            # Value is negative: subtract 2^14 to get the signed integer.
        return temp_raw * 0.25
        # Each count represents 0.25 degrees Celsius; scale and return it.

    def _read_raw32(self):
        # Private helper: performs the actual SPI transfer and packs the
        # 4 received bytes into a single 32-bit integer.
        data = self._spi.xfer2([0x00, 0x00, 0x00, 0x00])
        # Clock out 4 dummy zero bytes while simultaneously reading back
        # 4 bytes from the MAX31855 (it only ever drives data, never reads).
        return (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
        # Combine the 4 bytes (MSB first) into one 32-bit value.

    @staticmethod
    def temp_c_to_f(celsius):
        # Utility conversion function; doesn't need "self" since it has no
        # dependency on instance state.
        return celsius * 9.0 / 5.0 + 32.0
        # Standard Celsius-to-Fahrenheit formula.


def demo_run(device):
    # Runs the main read/print loop, given an already-open PmodTC1 device.
    print("Starting Pmod TC1 Demo...")
    # Print a startup banner, mirroring the original C demo's message.
    while True:
        # Loop forever until interrupted (e.g. Ctrl+C).
        try:
            celsius = device.get_temp_c()
            # Read the current temperature in Celsius; may raise PmodTC1Fault.
            fahrenheit = PmodTC1.temp_c_to_f(celsius)
            # Convert the Celsius reading to Fahrenheit for display.
            print(f"Temperature: {fahrenheit:.6f} deg F   {celsius:.6f} deg C")
            # Print both readings, formatted to 6 decimal places.
        except PmodTC1Fault as fault:
            # Catch a thermocouple fault instead of letting it crash the loop.
            print(f"Thermocouple fault: {fault}")
            # Report the fault message to the console.
        time.sleep(0.5)
        # Wait half a second before the next reading (twice per second).


def main():
    # Entry point: opens the device, runs the demo, and cleans up on exit.
    with PmodTC1(bus=0, device=0) as device:
        # Open spidev0.0 and guarantee it's closed when this block ends.
        try:
            demo_run(device)
            # Run the read/print loop using the opened device.
        except KeyboardInterrupt:
            # Catch Ctrl+C so it exits cleanly instead of printing a traceback.
            print("\nExiting.")
            # Print a friendly exit message before the program ends.


if __name__ == "__main__":
    # Only run main() if this file is executed directly (not imported).
    main()
    # Kick off the program.
