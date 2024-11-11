# This script logs CPU and memory usage and temperature to a file. It is used to monitor the health of the system.
import os
import time
from datetime import datetime
from enum import StrEnum

import psutil

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

PIDS = {
    "camera": None,
    "wifibroadcast@drone": None,
}


def log_health() -> tuple:
    """
    Log the CPU and memory usage and temperature to the log file
    """
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    temperature = psutil.sensors_temperatures().get("cpu_thermal")
    temperature = temperature[0].current if temperature else None
    cpu_clock = psutil.cpu_freq().current / 1000
    cpu_voltage = os.popen("vcgencmd measure_volts core").read().strip().split("=")[1]

    # Check how many resources the camera.service is using
    camera_cpu_percent, camera_memory = _check_pid("camera")

    # Check how many resources the wifibroadcast.service is using
    wfb_cpu_percent, wfb_memory = _check_pid("wifibroadcast@drone")

    return (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        cpu_percent,
        memory_percent,
        camera_cpu_percent,
        camera_memory,
        wfb_cpu_percent,
        wfb_memory,
        temperature,
        cpu_clock,
        cpu_voltage,
        *_check_if_throttled(),
    )


def _check_pid(service: str) -> tuple:
    """
    Check if the process resource usage
    """
    cpu_percent, memory = None, None

    global PIDS
    if PIDS.get(service) is None:
        pid = int(os.popen(f"systemctl show --property MainPID --value {service}.service").read().strip())
        # If the service is not running
        if pid == 0:
            return cpu_percent, memory
        PIDS[service] = psutil.Process(pid)
    try:
        cpu_percent = PIDS[service].cpu_percent()
        memory = PIDS[service].memory_info().rss / 1024 ** 2
    except psutil.NoSuchProcess:
        new_pid = int(os.popen(f"systemctl show --property MainPID --value {service}.service").read().strip())
        if new_pid == 0:
            return cpu_percent, memory
        PIDS[service] = psutil.Process(new_pid)
        cpu_percent, memory = _check_pid(service)

    return cpu_percent, memory


class ThrottleEnum(StrEnum):
    UNDER_VOLTAGE = "Under-voltage detected"
    ARM_FREQ_CAPPED = "Arm frequency capped"
    THROTTLED = "Currently throttled"
    SOFT_TEMP_LIMIT = "Soft temperature limit active"
    UNDER_VOLTAGE_OCCURRED = "Under-voltage has occurred"
    ARM_FREQ_CAPPED_OCCURRED = "Arm frequency capping has occurred"
    THROTTLED_OCCURRED = "Throttling has occurred"
    SOFT_TEMP_LIMIT_OCCURRED = "Soft temperature limit has occurred"


THROTTLE_MAP = {
    0: ThrottleEnum.UNDER_VOLTAGE,
    1: ThrottleEnum.ARM_FREQ_CAPPED,
    2: ThrottleEnum.THROTTLED,
    3: ThrottleEnum.SOFT_TEMP_LIMIT,
}


def _check_if_throttled() -> list[bool]:
    """
    Check if the CPU is throttled. Check the value of the get_throttled command and return the result
    based on the value. The value is a bit mask where each bit represents a different type of throttling.
    :return: List of reasons for throttling or None if the CPU is not throttled
    """
    res = os.popen("vcgencmd get_throttled").read().strip()
    res = int(res[res.index("=") + 1:], 0)
    # Should have at least 4 bits
    res_binary = bin(res)[2:]
    res_binary = "0" * (4 - len(res_binary)) + res_binary

    reasons = []
    for bit_n in THROTTLE_MAP.keys():
        bit = res_binary[-bit_n - 1]
        reasons.append(bool(int(bit)))
    return reasons


if __name__ == "__main__":
    with (open(os.path.join(log_directory, filename), "a") as file,
          open(os.path.join(shared_directory, filename), "a") as shared_file):
        file.write(",".join(file_columns) + "\n")
        shared_file.write(",".join(file_columns) + "\n")
        while True:
            data = log_health()
            # Append the data to the csv file
            file.write(",".join(map(str, data)) + "\n")
            shared_file.write(",".join(map(str, data)) + "\n")
            time.sleep(.2)
