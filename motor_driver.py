"""
MotorDriver - hardware abstraction for an L298N-driven DC motor on a
Raspberry Pi 4.

This class ONLY talks to the GPIO pins - it knows nothing about Flask,
HTTP, or any particular UI. Keeping it standalone like this means any
other code can drive the motor directly by importing this class, for
example:

    from motor_driver import MotorDriver

    motor = MotorDriver()
    motor.set_output(pid_output)   # pid_output is -100..100 from a PID loop

That makes it easy to plug in later without touching this file:
  - A PID control loop (call set_output() every loop iteration).
  - A different web UI, a desktop UI, or a CLI script.
  - Automated tests that don't want to spin up a web server.
"""

import threading

import RPi.GPIO as GPIO


class MotorDriver:
    def __init__(self, ena_pin=18, in1_pin=23, in2_pin=24, pwm_freq_hz=1000):
        # Remember the pin numbers so cleanup() can release exactly these
        # pins later without touching any other hardware sharing the Pi
        # (e.g. the camera code elsewhere in this project).
        self.ena_pin = ena_pin
        self.in1_pin = in1_pin
        self.in2_pin = in2_pin

        # One lock per motor instance, so reading/writing this motor's state
        # is safe even if it's driven from multiple threads (e.g. a PID loop
        # thread and a Flask request thread at the same time).
        self._lock = threading.Lock()
        self._direction = "stop"
        self._speed = 0

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.ena_pin, GPIO.OUT)
        GPIO.setup(self.in1_pin, GPIO.OUT)
        GPIO.setup(self.in2_pin, GPIO.OUT)

        # Start the speed (PWM) channel at 0% so the motor is off until
        # something explicitly commands it to move.
        self._pwm = GPIO.PWM(self.ena_pin, pwm_freq_hz)
        self._pwm.start(0)

    def set_direction_speed(self, direction, speed):
        """Direct control: direction is 'forward'/'backward'/'stop', speed is 0-100."""
        direction = direction if direction in ("forward", "backward", "stop") else "stop"
        speed = max(0, min(100, int(speed)))

        with self._lock:
            if direction == "forward":
                GPIO.output(self.in1_pin, GPIO.HIGH)
                GPIO.output(self.in2_pin, GPIO.LOW)
            elif direction == "backward":
                GPIO.output(self.in1_pin, GPIO.LOW)
                GPIO.output(self.in2_pin, GPIO.HIGH)
            else:
                direction = "stop"
                GPIO.output(self.in1_pin, GPIO.LOW)
                GPIO.output(self.in2_pin, GPIO.LOW)
                speed = 0

            self._pwm.ChangeDutyCycle(speed)
            self._direction = direction
            self._speed = speed

            return {"direction": self._direction, "speed": self._speed}

    def set_output(self, value):
        """
        PID-friendly entry point.

        Accepts a single signed value from -100 (full speed backward) to
        100 (full speed forward), which is exactly the shape of output a
        PID controller naturally produces. Sign picks the direction,
        magnitude picks the speed - no need for the PID loop to know
        anything about GPIO pins or direction pins at all.
        """
        value = max(-100, min(100, value))

        if value > 0:
            direction = "forward"
        elif value < 0:
            direction = "backward"
        else:
            direction = "stop"

        return self.set_direction_speed(direction, abs(value))

    def stop(self):
        """Convenience shortcut, equivalent to set_direction_speed('stop', 0)."""
        return self.set_direction_speed("stop", 0)

    @property
    def state(self):
        """Current {'direction', 'speed'} - safe to call from any thread/UI."""
        with self._lock:
            return {"direction": self._direction, "speed": self._speed}

    def cleanup(self):
        """Turn the motor off and release its GPIO pins. Call on shutdown."""
        with self._lock:
            self._pwm.ChangeDutyCycle(0)
        self._pwm.stop()
        GPIO.cleanup([self.ena_pin, self.in1_pin, self.in2_pin])
