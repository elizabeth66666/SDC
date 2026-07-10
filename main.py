from battery import Battery
from safety import check
from telemetry import create_packet
from logger import log
import time


def main():

    battery = Battery()
    for i in range(5): # change to while True when testing

            try:
                battery_data = battery.read()
            
            except Exception as e:
                 print(f"Battery read failed: {e}")
                 break

            status = check(battery_data)

            telemetry = create_packet(battery_data, status)

            print("\n AetherSat Telemetry ")

            for key, value in telemetry.items():
                print(f"{key}: {value}")

            print("---\n")
            log(telemetry)
            time.sleep(5) # Change this accordingly for testing

if __name__ == "__main__":
    main()
