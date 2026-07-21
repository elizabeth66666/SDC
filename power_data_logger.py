"""Logs voltage, current, and power from the INA219 sensor to a local SQLite
database once per minute. Designed to run continuously on a Raspberry Pi 4
Model B with the INA219 wired to the I2C pins (SDA/SCL)."""

import os
import sqlite3
import time
from datetime import datetime

import board
import busio
from adafruit_ina219 import INA219

# Absolute path to the SQLite database file. Change "pi" if your Pi's
# username is different, or point this at any other absolute location.
DB_PATH = "/home/pi/power_data/power_log.db"

# How often to take and store a reading, in seconds.
SAMPLE_INTERVAL_SECONDS = 60


def init_database(db_path):
    # Create the parent folder (e.g. /home/pi/power_data) if it does not exist yet.
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Connecting to a path that doesn't exist yet creates the .db file.
    conn = sqlite3.connect(db_path)

    # Create the table on first run only; later runs reuse the existing one.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS power_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            voltage_v REAL NOT NULL,
            current_ma REAL NOT NULL,
            power_w REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def read_sensor(ina219):
    return {
        "voltage_v": ina219.bus_voltage,
        "current_ma": ina219.current,
        "power_w": ina219.power,
    }


def log_reading(conn, reading):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute(
        """
        INSERT INTO power_readings (timestamp, voltage_v, current_ma, power_w)
        VALUES (?, ?, ?, ?)
        """,
        (timestamp, reading["voltage_v"], reading["current_ma"], reading["power_w"]),
    )
    conn.commit()

    print(
        f"{timestamp} | "
        f"Voltage: {reading['voltage_v']:.3f} V | "
        f"Current: {reading['current_ma']:.2f} mA | "
        f"Power: {reading['power_w']:.3f} W"
    )


def main():
    i2c = busio.I2C(board.SCL, board.SDA)
    ina219 = INA219(i2c)

    conn = init_database(DB_PATH)
    print(f"Logging to {DB_PATH} every {SAMPLE_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")

    try:
        while True:
            reading = read_sensor(ina219)
            log_reading(conn, reading)
            time.sleep(SAMPLE_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
