"""Log INA219 voltage/current/power readings to a local SQLite database.

Run this script on the Raspberry Pi 4. It reads the INA219 sensor once a
minute and appends the reading to a SQLite database file, creating the
database (and its parent folder) the first time it runs if they don't
already exist.
"""

# --- Imports -----------------------------------------------------------
# os: used to build the absolute database path and to create the folder
#     that will hold the database file if it doesn't exist yet.
import os
# sqlite3: Python's built-in SQLite driver. No extra install needed -
#          it ships with every standard Python 3 install, including
#          Raspberry Pi OS.
import sqlite3
# time: gives us time.sleep(), which pauses the loop for 60 seconds
#       between readings.
import time
# datetime: used to stamp every row with a human-readable timestamp of
#           when the reading was taken.
from datetime import datetime

# ina219 / DeviceRangeError: the sensor driver from the pi-ina219 library
# (the ina219.py file you uploaded). Install it on the Pi with:
#   sudo pip3 install pi-ina219 Adafruit-GPIO
# DeviceRangeError is raised by the library when the current/power reading
# has overflowed the sensor's measurable range - we catch it below so a
# single bad reading doesn't crash the whole logging loop.
from ina219 import INA219, DeviceRangeError

# --- Configuration -------------------------------------------------------
# SHUNT_OHMS must match the physical shunt resistor value on your INA219
# breakout board. 0.1 ohm is the Adafruit board's default - change this if
# your board uses a different resistor.
SHUNT_OHMS = 0.1

# How often to take a reading, in seconds. 60 = once per minute.
READ_INTERVAL_SECONDS = 60

# The absolute path to the SQLite database file. Using an absolute path
# (starting with "/") means the script always writes to the same file no
# matter what directory it's launched from (important once this runs as a
# cron job or systemd service, where the working directory isn't
# guaranteed to be this folder).
#
# Change "pi" below to your actual Raspberry Pi username if it's different.
DB_DIR = "/home/pi/sdc_data"
DB_PATH = os.path.join(DB_DIR, "sensor_data.db")


def get_connection():
    """Open (and if needed, create) the SQLite database file."""
    # os.makedirs creates every missing folder in DB_DIR.
    # exist_ok=True means "don't raise an error if the folder is already
    # there" - so this is safe to call every time the script starts.
    os.makedirs(DB_DIR, exist_ok=True)

    # sqlite3.connect() opens the database file at DB_PATH. If the file
    # does not exist yet, SQLite creates it right here - this is what
    # makes the Pi "create the file" the first time the script runs.
    connection = sqlite3.connect(DB_PATH)
    return connection


def create_table(connection):
    """Make sure the readings table exists before we try to insert into it."""
    # "CREATE TABLE IF NOT EXISTS" only creates the table the first time
    # this runs - on every later run it's a harmless no-op, so the script
    # can be restarted without wiping old data.
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            voltage_v REAL,
            current_ma REAL,
            power_mw REAL
        )
        """
    )
    # commit() writes the CREATE TABLE change to disk.
    connection.commit()


def read_sensor(ina):
    """Take one set of readings from the INA219 sensor."""
    # Bus voltage in volts - this call always succeeds.
    voltage = ina.voltage()
    try:
        # Current in milliamps and power in milliwatts. These two calls
        # can raise DeviceRangeError if the current has overflowed the
        # sensor's configured range.
        current = ina.current()
        power = ina.power()
    except DeviceRangeError:
        # If we overflowed, store None (SQL NULL) for current/power
        # instead of crashing, so we still keep the voltage reading.
        print("Current overflow - storing voltage only for this reading")
        current = None
        power = None
    return voltage, current, power


def insert_reading(connection, voltage, current, power):
    """Insert one row of sensor data into the readings table."""
    # Format "now" as a plain, sortable text timestamp.
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # "?" placeholders (rather than f-string/% formatting) let sqlite3
    # safely bind the values as parameters - this avoids SQL injection
    # and correctly handles None/NULL values.
    connection.execute(
        """
        INSERT INTO readings (timestamp, voltage_v, current_ma, power_mw)
        VALUES (?, ?, ?, ?)
        """,
        (timestamp, voltage, current, power),
    )
    # Commit after every insert so data is safely on disk even if the
    # script is later stopped or the Pi loses power.
    connection.commit()


def main():
    # Open the database connection and make sure the table exists.
    connection = get_connection()
    create_table(connection)

    # Create the sensor object using our shunt resistor value.
    ina = INA219(SHUNT_OHMS)
    # configure() calibrates the sensor with sensible defaults (32V range,
    # automatic gain) - see the pi-ina219 README for other options.
    ina.configure()

    print(f"Logging INA219 readings to {DB_PATH} every "
          f"{READ_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")

    try:
        # An infinite loop - keeps taking readings until the script is
        # interrupted (e.g. Ctrl+C, or a system shutdown).
        while True:
            voltage, current, power = read_sensor(ina)
            insert_reading(connection, voltage, current, power)
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
                  f"Voltage: {voltage:.3f} V, "
                  f"Current: {current}, Power: {power}")
            # Pause for a minute before the next reading.
            time.sleep(READ_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        # Ctrl+C raises KeyboardInterrupt - catch it so we can shut down
        # cleanly instead of printing a traceback.
        print("\nStopping data collection.")
    finally:
        # Always close the database connection on the way out, whether
        # we stopped normally or an error occurred.
        connection.close()


# Only run main() when this file is executed directly (e.g.
# `python3 data_collector.py`), not when it's imported by another module.
if __name__ == "__main__":
    main()
