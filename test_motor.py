"""
Manual bench test for MotorDriver - lets you exercise the motor and L298N
wiring directly from the terminal, without the web UI or a PID controller.

Usage:
    python3 test_motor.py

Commands:
    f <speed>   Drive forward at <speed> percent (0-100), e.g. "f 50"
    b <speed>   Drive backward at <speed> percent (0-100), e.g. "b 30"
    s           Stop the motor
    q           Quit (stops the motor and releases the GPIO pins)
"""

from motor_driver import MotorDriver


def print_state(motor):
    state = motor.state
    print(f"  -> direction={state['direction']} speed={state['speed']}%")


def main():
    motor = MotorDriver()
    print(__doc__)

    try:
        while True:
            raw = input("> ").strip().lower()
            if not raw:
                continue

            parts = raw.split()
            cmd = parts[0]

            if cmd == "q":
                break

            elif cmd == "s":
                motor.stop()
                print_state(motor)

            elif cmd in ("f", "b") and len(parts) == 2:
                try:
                    speed = int(parts[1])
                except ValueError:
                    print("Speed must be a whole number 0-100.")
                    continue

                direction = "forward" if cmd == "f" else "backward"
                motor.set_direction_speed(direction, speed)
                print_state(motor)

            else:
                print("Unrecognized command. Use: f <speed> | b <speed> | s | q")

    except KeyboardInterrupt:
        print("\nInterrupted.")

    finally:
        # Always stop the motor and release the GPIO pins, even if the
        # user hits Ctrl+C, so the motor never keeps spinning after the
        # script exits.
        motor.cleanup()
        print("Motor stopped, GPIO released.")


if __name__ == "__main__":
    main()
