import logging

from pymavlink import mavutil


class MAVLinkHandler(logging.Handler):
    """
    Custom logging handler that sends logs to the GCS via MAVLink STATUSTEXT messages.
    """
    MAVLINK_STATUSTEXT_SEVERITY = {
        logging.DEBUG: mavutil.mavlink.MAV_SEVERITY_DEBUG,
        logging.INFO: mavutil.mavlink.MAV_SEVERITY_INFO,
        logging.WARNING: mavutil.mavlink.MAV_SEVERITY_WARNING,
        logging.ERROR: mavutil.mavlink.MAV_SEVERITY_ERROR,
        logging.CRITICAL: mavutil.mavlink.MAV_SEVERITY_CRITICAL,
    }

    def __init__(self, connection_string: str, baud_rate: int):
        super().__init__()
        self.master = mavutil.mavlink_connection(connection_string, baud=baud_rate, source_system=1)

    def emit(self, record):
        """
        Emit the log record to the GCS via MAVLink STATUSTEXT message. It sends the log message with the appropriate
        severity level. The log message is prefixed with "CAMERA: " to differentiate it from other logs in the GCS.
        :param record: Log record to emit
        """
        log_entry = "CAMERA: " + self.format(record)
        severity = self.MAVLINK_STATUSTEXT_SEVERITY.get(record.levelno, mavutil.mavlink.MAV_SEVERITY_INFO)
        self.master.mav.statustext_send(severity, log_entry.encode())
