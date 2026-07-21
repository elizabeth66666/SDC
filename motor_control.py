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

import atexit
import threading

import RPi.GPIO as GPIO
from flask import Flask, jsonify, render_template, request

ENA_PIN = 18
IN1_PIN = 23
IN2_PIN = 24

PWM_FREQUENCY_HZ = 1000

app = Flask(__name__)

_lock = threading.Lock()
_state = {"direction": "stop", "speed": 0}


def _setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ENA_PIN, GPIO.OUT)
    GPIO.setup(IN1_PIN, GPIO.OUT)
    GPIO.setup(IN2_PIN, GPIO.OUT)

    pwm = GPIO.PWM(ENA_PIN, PWM_FREQUENCY_HZ)
    pwm.start(0)
    return pwm


_pwm = _setup_gpio()


def _apply(direction, speed):
    """Drive the H-bridge pins/PWM to match direction and speed (0-100)."""
    if direction == "forward":
        GPIO.output(IN1_PIN, GPIO.HIGH)
        GPIO.output(IN2_PIN, GPIO.LOW)
    elif direction == "backward":
        GPIO.output(IN1_PIN, GPIO.LOW)
        GPIO.output(IN2_PIN, GPIO.HIGH)
    else:
        direction = "stop"
        GPIO.output(IN1_PIN, GPIO.LOW)
        GPIO.output(IN2_PIN, GPIO.LOW)
        speed = 0

    _pwm.ChangeDutyCycle(speed)
    _state["direction"] = direction
    _state["speed"] = speed


def set_motor(direction, speed):
    """Validate and apply a direction/speed command. Returns the new state."""
    direction = direction if direction in ("forward", "backward", "stop") else "stop"
    speed = max(0, min(100, int(speed)))

    with _lock:
        _apply(direction, speed)
        return dict(_state)


@app.route("/")
def index():
    return render_template("motor_control.html")


@app.route("/api/status")
def status():
    with _lock:
        return jsonify(_state)


@app.route("/api/control", methods=["POST"])
def control():
    payload = request.get_json(silent=True) or {}
    direction = payload.get("direction", _state["direction"])
    speed = payload.get("speed", _state["speed"])

    try:
        speed = int(speed)
    except (TypeError, ValueError):
        return jsonify({"error": "speed must be a number"}), 400

    new_state = set_motor(direction, speed)
    return jsonify(new_state)


@atexit.register
def _cleanup():
    with _lock:
        _pwm.ChangeDutyCycle(0)
    _pwm.stop()
    GPIO.cleanup()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
