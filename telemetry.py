def create_packet(battery, status):

    telemetry = {
        "Voltage": battery["voltage"],
        "Current": battery["current"],
        "Power": battery["power"],
        "Status": status
    }

    return telemetry