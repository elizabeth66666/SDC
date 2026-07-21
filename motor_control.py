# DC Motor Control for Raspberry Pi 4 using an L298N H-Bridge driver.
#
# This is a Python rewrite of an Arduino sketch that used a potentiometer to
# set the motor speed and a push button to flip the motor's direction. Here,
# there is no physical button at all: speed and direction are both controlled
# from the keyboard instead, using the computer keyboard as the "remote
# control" for the motor.
#
# Wiring (Raspberry Pi GPIO pin numbers, using BCM numbering):
#   ENA (speed control / PWM) -> GPIO18
#   IN1 (direction control)   -> GPIO23
#   IN2 (direction control)   -> GPIO24
#   Also connect L298N GND to a Raspberry Pi GND pin, and power the L298N's
#   motor supply (+12V/+9V etc.) from a separate battery/power supply, NOT
#   from the Raspberry Pi.
#
# Keyboard controls (while the script is running):
#   w or Up arrow   -> increase speed
#   s or Down arrow -> decrease speed
#   f               -> spin the motor forward
#   r               -> spin the motor in reverse
#   space           -> stop the motor (speed becomes 0)
#   q               -> quit the program safely
#
# Setup required before running this file:
#   sudo pip install RPi.GPIO keyboard
#   sudo python3 motor_control.py
#   (sudo/root is required because the 'keyboard' library reads raw keyboard
#   events from the operating system, which normal users aren't allowed to do)

import RPi.GPIO as GPIO  # library that lets Python read/write the Raspberry Pi's GPIO pins
import keyboard           # library that lets Python detect which keys are being pressed
import time                # library that lets the program pause/sleep for a short time

# ---------------------------------------------------------------------------
# Pin numbers - change these if you wired your L298N to different GPIO pins
# ---------------------------------------------------------------------------

ENA = 18  # GPIO pin wired to the L298N's ENA pin; this pin's PWM signal sets motor speed
IN1 = 23  # GPIO pin wired to the L298N's IN1 pin; together with IN2 this sets motor direction
IN2 = 24  # GPIO pin wired to the L298N's IN2 pin; together with IN1 this sets motor direction

# ---------------------------------------------------------------------------
# Tunable settings
# ---------------------------------------------------------------------------

PWM_FREQUENCY = 1000  # how many times per second the PWM signal switches on/off (in Hertz)
SPEED_STEP = 10        # how much the speed changes (in percent) each time w/s is pressed
MAX_SPEED = 100        # the fastest allowed speed, as a percentage (100% = full power)
MIN_SPEED = 0          # the slowest allowed speed, as a percentage (0% = motor off)

# ---------------------------------------------------------------------------
# State that changes while the program runs
# ---------------------------------------------------------------------------

speed = 0                # current motor speed as a percentage from 0 to 100, starts stopped
direction = "forward"    # current motor direction, either "forward" or "reverse"
keep_running = True      # flag that stays True until the user presses 'q' to quit


def setup_gpio():
    """Prepare all the GPIO pins and the PWM signal used to drive the motor."""
    GPIO.setmode(GPIO.BCM)     # use Broadcom (GPIO) pin numbering instead of physical board numbering
    GPIO.setwarnings(False)    # silence warnings if a pin was left configured from an earlier run

    GPIO.setup(ENA, GPIO.OUT)  # configure the speed pin as an output, since we send a signal to the motor
    GPIO.setup(IN1, GPIO.OUT)  # configure the first direction pin as an output
    GPIO.setup(IN2, GPIO.OUT)  # configure the second direction pin as an output

    pwm = GPIO.PWM(ENA, PWM_FREQUENCY)  # create a PWM signal generator on the ENA pin at the chosen frequency
    pwm.start(0)                        # start the PWM signal at 0% duty cycle, so the motor begins switched off
    return pwm                          # hand the PWM object back so the rest of the program can control speed


def apply_direction():
    """Push the current 'direction' value out to the IN1/IN2 pins."""
    if direction == "forward":       # check whether we currently want the motor to spin forward
        GPIO.output(IN1, GPIO.LOW)   # set IN1 low
        GPIO.output(IN2, GPIO.HIGH)  # set IN2 high; this LOW/HIGH pair makes the L298N spin the motor forward
    else:                             # otherwise we want the motor to spin in reverse
        GPIO.output(IN1, GPIO.HIGH)  # set IN1 high
        GPIO.output(IN2, GPIO.LOW)   # set IN2 low; this HIGH/LOW pair makes the L298N spin the motor in reverse


def apply_speed(pwm):
    """Push the current 'speed' value out to the motor as a PWM duty cycle."""
    pwm.ChangeDutyCycle(speed)  # update the PWM duty cycle (0-100%), which raises or lowers motor power
    print(f"Speed: {speed}%")    # show the new speed in the terminal so the user gets feedback


def increase_speed(pwm):
    """Raise the speed by one step, without going above MAX_SPEED."""
    global speed                              # modify the shared 'speed' variable, not a local copy
    speed = min(MAX_SPEED, speed + SPEED_STEP)  # add one step, but never exceed the maximum allowed speed
    apply_speed(pwm)                           # send the updated speed out to the motor


def decrease_speed(pwm):
    """Lower the speed by one step, without going below MIN_SPEED."""
    global speed                              # modify the shared 'speed' variable, not a local copy
    speed = max(MIN_SPEED, speed - SPEED_STEP)  # subtract one step, but never go below the minimum allowed speed
    apply_speed(pwm)                           # send the updated speed out to the motor


def set_forward():
    """Switch the motor's direction to forward."""
    global direction          # modify the shared 'direction' variable, not a local copy
    direction = "forward"     # record that we now want to spin forward
    apply_direction()         # send the updated direction out to the IN1/IN2 pins
    print("Direction: forward")  # show the new direction in the terminal so the user gets feedback


def set_reverse():
    """Switch the motor's direction to reverse."""
    global direction          # modify the shared 'direction' variable, not a local copy
    direction = "reverse"     # record that we now want to spin in reverse
    apply_direction()         # send the updated direction out to the IN1/IN2 pins
    print("Direction: reverse")  # show the new direction in the terminal so the user gets feedback


def stop_motor(pwm):
    """Immediately stop the motor by dropping speed to 0."""
    global speed          # modify the shared 'speed' variable, not a local copy
    speed = 0              # set speed to zero
    apply_speed(pwm)        # send the zero speed out to the motor, which halts it
    print("Motor stopped")  # show the stop event in the terminal so the user gets feedback


def request_quit():
    """Signal the main loop that it should stop running."""
    global keep_running   # modify the shared 'keep_running' flag, not a local copy
    keep_running = False   # this makes the while loop in main() exit on its next check


def main():
    pwm = setup_gpio()  # configure the GPIO pins and get back the PWM controller object
    apply_direction()   # apply the starting direction ("forward") to the IN1/IN2 pins right away

    # Register each key with the function that should run when it is pressed.
    # 'lambda event: ...' is used so we can pass 'pwm' into functions that need
    # it, since keyboard callbacks are normally only given the key event itself.
    keyboard.on_press_key("w", lambda event: increase_speed(pwm))     # 'w' key raises speed
    keyboard.on_press_key("up", lambda event: increase_speed(pwm))    # Up arrow also raises speed
    keyboard.on_press_key("s", lambda event: decrease_speed(pwm))     # 's' key lowers speed
    keyboard.on_press_key("down", lambda event: decrease_speed(pwm))  # Down arrow also lowers speed
    keyboard.on_press_key("f", lambda event: set_forward())            # 'f' key sets forward direction
    keyboard.on_press_key("r", lambda event: set_reverse())            # 'r' key sets reverse direction
    keyboard.on_press_key("space", lambda event: stop_motor(pwm))     # space bar stops the motor
    keyboard.on_press_key("q", lambda event: request_quit())           # 'q' key quits the program

    print("Motor control ready.")                                  # let the user know the program has started
    print("w/up = faster, s/down = slower, f = forward, r = reverse, space = stop, q = quit")

    try:
        while keep_running:   # keep looping until request_quit() flips this flag to False
            time.sleep(0.1)    # sleep briefly each loop so this thread doesn't hog the CPU while waiting for keys
    finally:
        pwm.stop()          # stop sending the PWM signal to the motor
        GPIO.cleanup()      # reset all GPIO pins back to a safe default state
        print("GPIO cleaned up, exiting.")  # confirm a clean shutdown to the user


if __name__ == "__main__":  # this block only runs when the file is executed directly (not imported)
    main()                    # start the program
