import os
import time
from datetime import datetime

from health_check.collector import log_health
from health_check.mavlink_logger import MAVLinkLogger

log_directory = "/var/log/health_check"
shared_directory = "/srv/samba/share/logs/health_check"
os.makedirs(log_directory, exist_ok=True)
os.makedirs(shared_directory, exist_ok=True)
filename = f"health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

file_columns = (
    "datetime",
    "cpu_percent",
    "memory_percent",
    "camera_cpu_percent",
    "camera_memory",
    "wfb_cpu_percent",
    "wfb_memory",
    "temperature",
    "cpu_clock",
    "cpu_voltage",
    "under_voltage",
    "arm_freq_capped",
    "throttled",
    "soft_temp_limit",
)

if __name__ == "__main__":
    counter = 0
    with (open(os.path.join(log_directory, filename), "a") as file,
          open(os.path.join(shared_directory, filename), "a") as shared_file,
          MAVLinkLogger() as mav_logger):
        file.write(",".join(file_columns) + "\n")
        shared_file.write(",".join(file_columns) + "\n")
        while True:
            data = log_health()
            # Append the data to the csv file
            file.write(",".join(map(str, data)) + "\n")
            shared_file.write(",".join(map(str, data)) + "\n")
            # Log the data to the GCS every second
            if counter % 5 == 0:
                mav_logger.log(data)
            time.sleep(.2)
            counter += 1
