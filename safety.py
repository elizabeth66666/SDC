from config import MIN_BATTERY_VOLTAGE
from config import MAX_BATTERY_CURRENT


def check(battery):
    faults=[]

    if battery["voltage"] < MIN_BATTERY_VOLTAGE:
        return "LOW BATTERY, ENTERING SAFE MODE"

    if battery["current"] > MAX_BATTERY_CURRENT:
        return "OVERCURRENT, EXCEEDING CURRENT LIMIT"
    
    if faults:
        return ", ".join(faults)
        

    return "NORMAL"
