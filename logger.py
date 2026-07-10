from datetime import datetime
def log(telemetry):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("telemetry_log.txt", "a") as log_file:
        log_file.write(f"{current_time} \n")

        for key, value in telemetry.items():
            log_file.write(f"{key}: {value}\n") 
