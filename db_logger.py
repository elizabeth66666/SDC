# Stores each telemetry reading as a row in a local SQLite file, so live data
# survives reboots/crashes and can be queried later (e.g. `sqlite3 telemetry.db`).

import sqlite3               # Python's built-in SQLite driver, no extra install needed
from datetime import datetime  # used to stamp every row with a human-readable time


class DBLogger:

    def __init__(self, db_path="telemetry.db"):
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        # ^ open (or create, if missing) the .db file on disk
        #   check_same_thread=False lets this connection be used from a callback
        #   thread too (RPMSensor's GPIO interrupt runs on its own thread)

        self.cursor = self.connection.cursor()  # cursor is what actually executes SQL statements
        self._create_table()                    # make sure the table exists before anyone tries to log to it

    def _create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                voltage REAL,
                current REAL,
                power REAL,
                rpm REAL,
                status TEXT
            )
        """)
        # ^ CREATE TABLE IF NOT EXISTS: only creates it the first time the program runs,
        #   later runs just reuse the same table and append to it.
        #   id: auto-incrementing row number, used as the primary key.
        #   timestamp: when the reading was taken.
        #   voltage/current/power/rpm: REAL (floating point) sensor readings.
        #   status: text describing system state (e.g. "NORMAL", "LOW BATTERY").

        self.connection.commit()  # write the CREATE TABLE change to disk

    def log(self, telemetry):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # current time as "YYYY-MM-DD HH:MM:SS"

        self.cursor.execute(
            "INSERT INTO telemetry (timestamp, voltage, current, power, rpm, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                timestamp,
                telemetry.get("Voltage"),
                telemetry.get("Current"),
                telemetry.get("Power"),
                telemetry.get("RPM"),
                telemetry.get("Status"),
            ),
        )
        # ^ the "?" placeholders are filled in from the tuple below them.
        #   Using placeholders (instead of f-string-ing values into the SQL text)
        #   prevents SQL injection and correctly handles values that are None.

        self.connection.commit()  # persist this row to the .db file immediately,
        # so data is safe on disk even if the program is later killed/crashes

    def close(self):
        self.connection.close()  # cleanly release the database file handle
