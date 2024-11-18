from datetime import datetime

from pymavlink import mavutil


class MAVLinkLogger:
    HOST = "127.0.0.1"
    PORT = 14550

    def __init__(self):
        self.master = None

    def __enter__(self):
        self.master = mavutil.mavlink_connection(f"udp:{self.HOST}:{self.PORT}", input=False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.master.close()

    def log(self, data: tuple):
        """
        Log the RasbPI data to the GCS via MAVLink messages. Pass only the data that is needed to be logged. Like
        timestamp, temperature and if the CPU is throttled.
        :param data: tuple of data to log in format (
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
            "soft_temp_limit"
        )
        """
        timestamp = datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S").timestamp()
        log_entry = f"{timestamp}, {data[7]}, {data[11]:b}"
        self.master.mav.statustext_send(mavutil.mavlink.MAV_SEVERITY_INFO, log_entry.encode())
