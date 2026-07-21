# Battery Limits
MIN_BATTERY_VOLTAGE = 6.4      # Volts
MAX_BATTERY_CURRENT = 2.0      # Amps

# RPM Sensor
RPM_SENSOR_PIN = 17            # BCM GPIO pin wired to the hall-effect/IR sensor output
PULSES_PER_REVOLUTION = 1      # number of sensor pulses per full revolution (magnets/slots on the wheel)
SAMPLE_INTERVAL = 1.0          # seconds spent counting pulses for each RPM reading

# SQLite Database
DB_PATH = "telemetry.db"       # path to the SQLite file live data is stored in
