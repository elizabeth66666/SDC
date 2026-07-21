"""Reads current/voltage/power from the INA219 sensor and logs a row to
SQLite every LOG_INTERVAL_SECONDS. Run directly on the Raspberry Pi.
"""
import os
import sqlite3
import time
from datetime import datetime

import board
import busio
from adafruit_ina219 import INA219

DB_PATH = "/home/pi/aethersat/data/current_data.db"
LOG_INTERVAL_SECONDS = 60


def init_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS current_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            bus_voltage_v REAL,
            shunt_voltage_mv REAL,
            current_ma REAL,
            power_mw REAL
        )
        """
    )
    conn.commit()
    return conn


def read_sensor(ina219):
    return {
        "bus_voltage_v": ina219.bus_voltage,
        "shunt_voltage_mv": ina219.shunt_voltage * 1000,
        "current_ma": ina219.current,
        "power_mw": ina219.power,
    }


def insert_reading(conn, reading):
    conn.execute(
        """
        INSERT INTO current_readings
            (timestamp, bus_voltage_v, shunt_voltage_mv, current_ma, power_mw)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            reading["bus_voltage_v"],
            reading["shunt_voltage_mv"],
            reading["current_ma"],
            reading["power_mw"],
        ),
    )
    conn.commit()


def main():
    i2c = busio.I2C(board.SCL, board.SDA)
    ina219 = INA219(i2c)
    conn = init_db(DB_PATH)

    print(f"Logging to {DB_PATH} every {LOG_INTERVAL_SECONDS}s. Press Ctrl+C to stop.")

    try:
        while True:
            start = time.monotonic()

            try:
                reading = read_sensor(ina219)
                insert_reading(conn, reading)
                print(f"{datetime.now().isoformat(timespec='seconds')} -> {reading}")
            except Exception as e:
                print(f"Read/write failed: {e}")

            elapsed = time.monotonic() - start
            time.sleep(max(0, LOG_INTERVAL_SECONDS - elapsed))
    except KeyboardInterrupt:
        print("Stopping logger.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
