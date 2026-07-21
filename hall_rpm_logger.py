# hall_rpm_logger.py
#
# Reads a KY-003 Hall effect sensor on a Raspberry Pi 4 Model B, counts
# magnet passes with a GPIO interrupt, computes RPM once per sampling
# window, and writes every reading into a local SQLite database.
#
# Wiring (KY-003 3-pin module — pin order/labels vary by seller, always
# check the silkscreen printed on your specific board):
#   "-"            -> Raspberry Pi GND   (e.g. physical pin 6)
#   "middle" / "+" -> Raspberry Pi 3V3   (physical pin 1)   <-- do NOT use 5V, GPIO inputs are 3.3V only
#   "S" (signal)   -> Raspberry Pi GPIO17 (physical pin 11) <-- change SENSOR_PIN below if wired elsewhere
#
# Install the GPIO library if it isn't already present:
#   pip install RPi.GPIO

import RPi.GPIO as GPIO         # controls the Pi's GPIO pins (reading the sensor, interrupts)
import sqlite3                  # built-in library for creating/writing the SQLite database
import threading                 # gives us Lock, needed because the interrupt callback runs on its own thread
import time                      # used for the sampling-loop timing (time.sleep)
from datetime import datetime    # produces human-readable timestamps for each stored row

# ---------------------------------------------------------------------------
# Configuration — edit these to match your wiring and mechanical setup
# ---------------------------------------------------------------------------
SENSOR_PIN = 17             # BCM GPIO number the KY-003 "S" pin is wired to
MAGNETS_PER_REV = 1         # how many magnets pass the sensor per one full revolution of the wheel/shaft
SAMPLE_INTERVAL_SEC = 1.0   # how often (seconds) we compute RPM and write a row to the database
DEBOUNCE_MS = 5             # ignore extra edges within this many ms (electrical/mechanical noise); lower this if you expect very high RPM
DB_PATH = "rpm_data.db"     # SQLite file created next to this script

# ---------------------------------------------------------------------------
# Shared state between the interrupt callback (fires on its own thread) and
# the main loop. A Lock stops the two from touching pulse_count at the same
# instant, which is the Python equivalent of the Arduino noInterrupts() /
# interrupts() pair used to read a volatile counter safely.
# ---------------------------------------------------------------------------
pulse_count = 0                    # number of magnet passes seen since the last sample
pulse_lock = threading.Lock()      # guards pulse_count against concurrent access


def _on_pulse(channel):
    """Interrupt callback — runs every time SENSOR_PIN goes HIGH -> LOW (a magnet passing)."""
    global pulse_count             # we're updating the module-level counter, not creating a local one
    with pulse_lock:               # block until we can safely modify pulse_count
        pulse_count += 1           # register one magnet pass


def setup_gpio():
    """Configure the sensor pin and attach the falling-edge interrupt handler."""
    GPIO.setmode(GPIO.BCM)                                     # use Broadcom GPIO numbers (GPIO17), not physical pin numbers
    GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # KY-003 output idles HIGH; the pull-up guarantees a clean HIGH when no magnet is present
    GPIO.add_event_detect(                                     # ask the kernel to notify us on edges instead of polling in a loop
        SENSOR_PIN,
        GPIO.FALLING,               # trigger on HIGH -> LOW, i.e. when a magnet arrives at the sensor
        callback=_on_pulse,         # function invoked on each falling edge
        bouncetime=DEBOUNCE_MS,     # suppress duplicate triggers caused by signal bounce
    )


def setup_database():
    """Create the SQLite database/table if needed and return an open connection."""
    conn = sqlite3.connect(DB_PATH)   # opens rpm_data.db, creating the file the first time it's called
    cursor = conn.cursor()             # cursor object used to run SQL statements
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rpm_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique row id, assigned automatically by SQLite
            timestamp TEXT NOT NULL,               -- when the reading was taken (ISO 8601 string)
            pulse_count INTEGER NOT NULL,           -- raw magnet-pass count during this sample window
            rpm REAL NOT NULL                       -- calculated revolutions per minute
        )
        """
    )                                   # only actually creates the table the first time the script runs
    conn.commit()                       # persist the CREATE TABLE statement to disk
    return conn                         # hand the open connection back to the caller


def read_and_reset_pulses():
    """Atomically snapshot the pulse counter and reset it to zero for the next window."""
    global pulse_count
    with pulse_lock:            # block the interrupt thread from updating pulse_count while we read it
        count = pulse_count     # copy out the current value
        pulse_count = 0         # reset the counter for the next sampling window
    return count                # give the caller the snapshot


def calculate_rpm(pulse_count_sample, interval_sec):
    """Convert a raw pulse count taken over `interval_sec` seconds into RPM."""
    revolutions = pulse_count_sample / MAGNETS_PER_REV   # pulses divided by magnets-per-rev = number of full revolutions
    revolutions_per_sec = revolutions / interval_sec      # scale to a per-second rate
    return revolutions_per_sec * 60.0                     # convert revolutions/second to revolutions/minute


def main():
    setup_gpio()                  # configure the pin and interrupt before we start timing anything
    conn = setup_database()       # open (and initialize, if needed) the SQLite database
    cursor = conn.cursor()        # cursor reused for every INSERT in the loop below

    print(f"Logging RPM to {DB_PATH} every {SAMPLE_INTERVAL_SEC}s — press Ctrl+C to stop.")

    try:
        while True:                                          # run continuously until the user stops the script
            time.sleep(SAMPLE_INTERVAL_SEC)                   # wait one sampling window while the interrupt counts pulses in the background
            count = read_and_reset_pulses()                   # grab this window's pulse count and reset the counter for the next one
            rpm = calculate_rpm(count, SAMPLE_INTERVAL_SEC)    # turn the pulse count into an RPM figure
            timestamp = datetime.now().isoformat(timespec="seconds")  # e.g. "2026-07-21T14:03:05"

            cursor.execute(                                   # '?' placeholders let SQLite bind values safely (prevents SQL injection)
                "INSERT INTO rpm_readings (timestamp, pulse_count, rpm) VALUES (?, ?, ?)",
                (timestamp, count, rpm),                       # values substituted into the placeholders, in order
            )
            conn.commit()                                     # flush the new row to disk immediately so the data is "live" for any other process reading the file

            print(f"{timestamp}  pulses={count:3d}  RPM={rpm:8.2f}")  # console feedback while it runs

    except KeyboardInterrupt:                                 # user pressed Ctrl+C
        print("\nStopping — closing GPIO and database connection...")

    finally:
        GPIO.remove_event_detect(SENSOR_PIN)   # detach the interrupt handler
        GPIO.cleanup()                          # release the GPIO pins so other programs can use them afterwards
        conn.close()                            # close the SQLite connection cleanly


if __name__ == "__main__":   # only runs main() when this file is executed directly (not when imported elsewhere)
    main()
