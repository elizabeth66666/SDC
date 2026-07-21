"""
DC Motor Control - PWM | H-Bridge | L298N - Raspberry Pi 4 + Web UI

Rewrite of the Arduino/HowToMechatronics example. Direction and speed are no
longer read from a physical button/potentiometer - both are set from a
browser-based UI served over Flask, and applied immediately via RPi.GPIO.

Wiring (BCM numbering, adjust to match your setup):
    ENA_PIN -> L298N ENA (PWM speed control)
    IN1_PIN -> L298N IN1
    IN2_PIN -> L298N IN2
"""

# atexit lets us register a function that Python will automatically run
# when the program is closing, even if it's closed with Ctrl+C. We use it
# to safely turn the motor off and release the GPIO pins.
import atexit

# threading gives us a "Lock", which is a tool that stops two requests from
# changing the motor's speed/direction at the exact same time and causing
# conflicting commands.
import threading

# RPi.GPIO is the library that lets Python talk to the physical GPIO (General
# Purpose Input/Output) pins on the Raspberry Pi. This is how the code
# actually turns real wires on the board HIGH (3.3V) or LOW (0V).
import RPi.GPIO as GPIO

# Flask is a lightweight web server framework. It lets this Python program
# serve web pages and respond to requests sent from a browser (the UI).
from flask import Flask, jsonify, render_template, request

# These numbers identify which physical GPIO pins on the Pi are wired to the
# L298N motor driver board. "BCM numbering" means these are the Broadcom
# chip pin numbers, not the physical pin position numbers on the header.
ENA_PIN = 18   # Connected to L298N "ENA" - controls motor speed via PWM.
IN1_PIN = 23   # Connected to L298N "IN1" - one of the two direction pins.
IN2_PIN = 24   # Connected to L298N "IN2" - the other direction pin.

# PWM (Pulse Width Modulation) rapidly switches the pin on/off to simulate a
# variable voltage, which is how we control motor speed. This number is how
# many times per second that on/off cycle repeats.
PWM_FREQUENCY_HZ = 1000

# Create the Flask web application. "__name__" tells Flask where to look for
# supporting files, like the templates/ folder containing our HTML page.
app = Flask(__name__)

# A Lock is like a single key to a room: only one piece of code can hold it
# at a time. We use it so that reading/writing "_state" and talking to the
# GPIO pins always happens one request at a time, never simultaneously.
_lock = threading.Lock()

# This dictionary remembers what the motor is currently doing, so the web
# page can ask "what's the motor doing right now?" at any time.
_state = {"direction": "stop", "speed": 0}


def _setup_gpio():
    # Tell the GPIO library we are referring to pins by their Broadcom "BCM"
    # numbers (as opposed to their physical position on the header).
    GPIO.setmode(GPIO.BCM)

    # Configure each pin we use as an OUTPUT, meaning the Pi will send
    # voltage out of these pins rather than read voltage coming in.
    GPIO.setup(ENA_PIN, GPIO.OUT)
    GPIO.setup(IN1_PIN, GPIO.OUT)
    GPIO.setup(IN2_PIN, GPIO.OUT)

    # Create a PWM ("dimmer switch") controller on the ENA pin, running at
    # PWM_FREQUENCY_HZ cycles per second.
    pwm = GPIO.PWM(ENA_PIN, PWM_FREQUENCY_HZ)

    # Start the PWM signal, but with 0% duty cycle - meaning the motor
    # receives no power yet, so it stays off until we tell it otherwise.
    pwm.start(0)

    # Hand back the pwm controller object so the rest of the program can
    # change its speed later on.
    return pwm


# Run the setup once, immediately, when this file is loaded, and keep the
# resulting PWM controller in a variable so every function below can use it.
_pwm = _setup_gpio()


def _apply(direction, speed):
    """Drive the H-bridge pins/PWM to match direction and speed (0-100)."""

    # Setting IN1 HIGH (on) and IN2 LOW (off) makes current flow through the
    # motor in the direction the L298N calls "forward".
    if direction == "forward":
        GPIO.output(IN1_PIN, GPIO.HIGH)
        GPIO.output(IN2_PIN, GPIO.LOW)

    # Doing the opposite - IN1 LOW, IN2 HIGH - reverses the current, which
    # spins the motor the opposite way ("backward").
    elif direction == "backward":
        GPIO.output(IN1_PIN, GPIO.LOW)
        GPIO.output(IN2_PIN, GPIO.HIGH)

    # Any other value (including the word "stop") is treated as "stop": both
    # direction pins go LOW so no current flows, and we force speed to 0 so
    # the motor definitely isn't being told to spin.
    else:
        direction = "stop"
        GPIO.output(IN1_PIN, GPIO.LOW)
        GPIO.output(IN2_PIN, GPIO.LOW)
        speed = 0

    # Update the PWM "dimmer switch" to the requested speed percentage
    # (0 = off, 100 = full power). This is what actually makes the motor
    # go faster or slower.
    _pwm.ChangeDutyCycle(speed)

    # Remember what we just set, so future status checks report the truth.
    _state["direction"] = direction
    _state["speed"] = speed


def set_motor(direction, speed):
    """Validate and apply a direction/speed command. Returns the new state."""

    # If someone sends a direction we don't recognize, fall back to "stop"
    # instead of doing something unpredictable with the motor.
    direction = direction if direction in ("forward", "backward", "stop") else "stop"

    # Force the speed to be a whole number between 0 and 100, no matter what
    # was requested, so we never send an invalid value to the PWM controller.
    speed = max(0, min(100, int(speed)))

    # Acquire the lock so no other request can interrupt us while we change
    # the motor's state, then release it automatically when this block ends.
    with _lock:
        _apply(direction, speed)
        # Return a copy of the current state so the caller sees what was
        # actually applied (in case direction/speed got adjusted above).
        return dict(_state)


@app.route("/")
def index():
    # When someone visits the website's home page ("/"), send them the
    # motor_control.html file from the templates/ folder - this is the page
    # with the slider and direction buttons.
    return render_template("motor_control.html")


@app.route("/api/status")
def status():
    # This endpoint lets the web page ask "what is the motor doing right
    # now?" - useful when the page first loads, to show the correct values.
    with _lock:
        return jsonify(_state)


@app.route("/api/control", methods=["POST"])
def control():
    # The browser sends a JSON body like {"direction": "forward", "speed": 50}.
    # get_json(silent=True) parses it without crashing if it's missing/bad,
    # and "or {}" makes sure we always have a dictionary to work with.
    payload = request.get_json(silent=True) or {}

    # Pull out "direction" and "speed" from what the browser sent. If either
    # one is missing, keep using whatever the motor is currently set to.
    direction = payload.get("direction", _state["direction"])
    speed = payload.get("speed", _state["speed"])

    # Make sure "speed" is actually a number. If it isn't (e.g. someone sent
    # text), tell the browser it made a bad request (HTTP 400) instead of
    # crashing the server.
    try:
        speed = int(speed)
    except (TypeError, ValueError):
        return jsonify({"error": "speed must be a number"}), 400

    # Actually change the motor's direction/speed, then send the resulting
    # state back to the browser as JSON so it can update the display.
    new_state = set_motor(direction, speed)
    return jsonify(new_state)


@atexit.register
def _cleanup():
    # This function runs automatically when the program is shutting down.
    # First, make sure the motor is told to stop receiving power...
    with _lock:
        _pwm.ChangeDutyCycle(0)

    # ...then stop the PWM signal entirely...
    _pwm.stop()

    # ...and finally release all the GPIO pins so they return to a safe,
    # neutral state and are free for other programs to use.
    GPIO.cleanup()


# This block only runs when you execute this file directly (for example,
# "python3 motor_control.py"), not when it's imported by another script.
if __name__ == "__main__":
    # Start the Flask web server. host="0.0.0.0" makes it reachable from
    # other devices on the network (not just the Pi itself), port=5000 is
    # the web address port (e.g. http://<pi-ip>:5000), and threaded=True
    # lets it handle more than one browser request at the same time.
    app.run(host="0.0.0.0", port=5000, threaded=True)
