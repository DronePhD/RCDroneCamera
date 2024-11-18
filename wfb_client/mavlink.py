import threading

from pymavlink import mavutil

from wfb_client.data_display import DataDisplay


class MAVLink:
    HOST = "127.0.0.1"
    PORT = 14550

    def __init__(self, display: DataDisplay):
        self._display = display
        self._mav = None
        self._thread_active = True

    def __enter__(self):
        self._mav = mavutil.mavlink_connection(f"udp:{self.HOST}:{self.PORT}", input=True)
        thread = threading.Thread(target=self._get_logs)
        thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._thread_active = False
        self._mav.close()

    def _get_logs(self):
        """
        Log the RasbPI data from Drone via MAVLink messages.
        """
        while self._thread_active:
            msg = self._mav.recv_match()
            if msg and msg.get_type() == "STATUSTEXT":
                log = msg.text.split(", ")
                self._display.data = {
                    "temp": {
                        "timestamp": float(log[0]),
                        "temperature": float(log[1]),
                        "throttled": bool(log[2])
                    }
                }
