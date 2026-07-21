def create_packet(battery, rpm, status):

    telemetry = {
        "Voltage": battery["voltage"],
        "Current": battery["current"],
        "Power": battery["power"],
        "RPM": rpm,
        "Status": status
    }

    return telemetry