import os
from datetime import datetime

import psutil

from health_check.cpu_throttle import check_if_throttled

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
        *check_if_throttled(),
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
