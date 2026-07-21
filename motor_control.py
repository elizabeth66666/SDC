"""
DC Motor Control - Web UI (Flask) - Raspberry Pi 4 + L298N

This file is only the web layer: it serves the browser page and translates
HTTP requests into calls on MotorDriver (see motor_driver.py), which is the
part that actually talks to the GPIO pins.

Keeping the hardware logic in MotorDriver, separate from this Flask app,
means MotorDriver can be reused later without any of this web server code -
for example, a PID control loop can do:

    from motor_driver import MotorDriver
    motor = MotorDriver()
    motor.set_output(pid_output)

...directly, with no HTTP involved, while this file keeps serving the
manual/browser UI side by side.
"""

# atexit lets us register a function that Python will automatically run
# when the program is closing, even if it's closed with Ctrl+C. We use it
# to safely turn the motor off and release the GPIO pins.
import atexit

# Flask is a lightweight web server framework. It lets this Python program
# serve web pages and respond to requests sent from a browser (the UI).
from flask import Flask, jsonify, render_template, request

# The hardware driver class - all GPIO/PWM details live there, not here.
from motor_driver import MotorDriver

# Create the Flask web application. "__name__" tells Flask where to look for
# supporting files, like the templates/ folder containing our HTML page.
app = Flask(__name__)

# One shared MotorDriver instance for this process. If you later add a PID
# loop running in the same process, it can import and reuse this exact
# object instead of creating a second one (only one thing should own the
# physical GPIO pins at a time).
motor = MotorDriver()


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
    return jsonify(motor.state)


@app.route("/api/control", methods=["POST"])
def control():
    # The browser sends a JSON body like {"direction": "forward", "speed": 50}.
    # get_json(silent=True) parses it without crashing if it's missing/bad,
    # and "or {}" makes sure we always have a dictionary to work with.
    payload = request.get_json(silent=True) or {}

    # Pull out "direction" and "speed" from what the browser sent. If either
    # one is missing, keep using whatever the motor is currently set to.
    current = motor.state
    direction = payload.get("direction", current["direction"])
    speed = payload.get("speed", current["speed"])

    # Make sure "speed" is actually a number. If it isn't (e.g. someone sent
    # text), tell the browser it made a bad request (HTTP 400) instead of
    # crashing the server.
    try:
        speed = int(speed)
    except (TypeError, ValueError):
        return jsonify({"error": "speed must be a number"}), 400

    # Actually change the motor's direction/speed, then send the resulting
    # state back to the browser as JSON so it can update the display.
    new_state = motor.set_direction_speed(direction, speed)
    return jsonify(new_state)


@atexit.register
def _cleanup():
    # This function runs automatically when the program is shutting down,
    # so the motor is always left off and the GPIO pins released cleanly.
    motor.cleanup()


# This block only runs when you execute this file directly (for example,
# "python3 motor_control.py"), not when it's imported by another script.
if __name__ == "__main__":
    # Start the Flask web server. host="0.0.0.0" makes it reachable from
    # other devices on the network (not just the Pi itself), port=5000 is
    # the web address port (e.g. http://<pi-ip>:5000), and threaded=True
    # lets it handle more than one browser request at the same time.
    app.run(host="0.0.0.0", port=5000, threaded=True)
