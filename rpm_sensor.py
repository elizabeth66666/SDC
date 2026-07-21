# Reads RPM from a hall-effect (or IR slotted) speed sensor wired to a GPIO pin.
# Each full revolution makes the sensor pulse the pin LOW once (or more, if the
# flywheel/wheel has several magnets/slots per rotation).

import RPi.GPIO as GPIO      # low-level Raspberry Pi GPIO access (interrupts, pin modes)
import time                  # used to time how long we count pulses for
import threading             # protects the pulse counter from race conditions


class RPMSensor:

    def __init__(self, pin, pulses_per_revolution=1):
        self.pin = pin                                     # BCM pin number the sensor's signal wire is on
        self.pulses_per_revolution = pulses_per_revolution  # how many pulses = 1 full revolution (magnets/slots on the wheel)
        self._pulse_count = 0                               # running count of pulses seen since the last reset
        self._lock = threading.Lock()                       # guards _pulse_count, since the callback fires on its own thread

        GPIO.setmode(GPIO.BCM)                              # use Broadcom GPIO numbering (GPIO17, not physical pin 11)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # ^ configure the pin as an input with an internal pull-up resistor, so it
        #   reads HIGH by default and only drops LOW when the sensor's open-collector
        #   output switches (this is the standard wiring for hall-effect modules like the A3144)

        GPIO.add_event_detect(self.pin, GPIO.FALLING, callback=self._pulse_callback, bouncetime=2)
        # ^ ask the kernel to call _pulse_callback() on every HIGH->LOW edge (i.e. every pulse)
        #   bouncetime=2 ignores extra edges within 2ms of a real one, filtering out
        #   electrical noise/contact bounce so one physical pulse isn't counted twice

    def _pulse_callback(self, channel):
        with self._lock:          # only one thread may touch _pulse_count at a time
            self._pulse_count += 1  # record that one more pulse arrived

    def read_rpm(self, sample_time=1.0):
        with self._lock:
            self._pulse_count = 0     # zero the counter so this reading only covers the upcoming window

        time.sleep(sample_time)       # let pulses accumulate for sample_time seconds (interrupts keep firing in the background)

        with self._lock:
            pulses = self._pulse_count  # snapshot how many pulses arrived during that window

        revolutions = pulses / self.pulses_per_revolution   # convert pulse count to full revolutions
        rpm = (revolutions / sample_time) * 60               # revolutions per sample window -> revolutions per 60s (RPM)
        return rpm

    def cleanup(self):
        GPIO.remove_event_detect(self.pin)  # stop listening for interrupts on this pin
        GPIO.cleanup(self.pin)              # release the pin back to its default state
