from battery import Battery
from rpm_sensor import RPMSensor
from safety import check
from telemetry import create_packet
from db_logger import DBLogger
from config import RPM_SENSOR_PIN, PULSES_PER_REVOLUTION, SAMPLE_INTERVAL, DB_PATH


def main():

    battery = Battery()
    rpm_sensor = RPMSensor(RPM_SENSOR_PIN, PULSES_PER_REVOLUTION)
    db_logger = DBLogger(DB_PATH)

    try:
        while True:  # live loop: keep reading and storing data until interrupted

            try:
                battery_data = battery.read()

            except Exception as e:
                 print(f"Battery read failed: {e}")
                 break

            rpm = rpm_sensor.read_rpm(SAMPLE_INTERVAL)  # blocks for SAMPLE_INTERVAL seconds counting pulses

            status = check(battery_data)

            telemetry = create_packet(battery_data, rpm, status)

            print("\n AetherSat Telemetry ")

            for key, value in telemetry.items():
                print(f"{key}: {value}")

            print("---\n")
            db_logger.log(telemetry)  # persist this reading as a row in telemetry.db

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        rpm_sensor.cleanup()  # release the GPIO pin/interrupt
        db_logger.close()     # close the SQLite connection

if __name__ == "__main__":
    main()
