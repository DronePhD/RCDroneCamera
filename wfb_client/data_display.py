import threading
import time

import logging

from wfb_client.data_screen import OverviewScreen, PacketScreen, FlowScreen, AntennaScreen, TempLogScreen
from wfb_client.display_controller import OLED0in95RGB

logging = logging.getLogger("display")


class DataDisplay:
    FRAME_RATE = 30  # Limit the frame rate to 30 FPS

    def __init__(self):
        screens = [OverviewScreen(), PacketScreen(), FlowScreen(), AntennaScreen(), TempLogScreen()]
        self.current_screen = screens[0]
        # Link the screens together as a circular linked list
        for s in screens[:-1]:
            s.next_screen = screens[screens.index(s) + 1]
        screens[-1].next_screen = self.current_screen

        self._data = dict()
        self.active = True

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value: dict):
        self._data = value

    def next_screen(self):
        self.current_screen = next(self.current_screen)

    def __enter__(self):
        thread = threading.Thread(target=self._refresh_loop)
        logging.info("Starting the display loop")
        thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.active = False
        logging.info("Stopping the display loop")

    def _refresh_loop(self):
        with OLED0in95RGB() as display:
            while self.active:
                image = self.current_screen.draw(self.data)
                display.show_image(display.get_buffer(image))
                time.sleep(1 / self.FRAME_RATE)


if __name__ == "__main__":
    test_data = {
        "packet": {
            "recv": (342, 112535),
            "udp": (285, 85354),
            "fec_r": (65, 10344),
            "lost": (25, 2806),
            "d_err": (0, 0),
            "bad": (0, 0)
        },
        "flow": {"in": 465395, "out": 375275, "fec": (8, 12)},
        "antenna": {
            "rssi": {"min": -53.0, "avg": -48.5, "max": -48.0},
            "snr": {"min": 16.0, "avg": 23.0, "max": 27.5}
        }
    }
    d = DataDisplay()
    d.data = test_data
    d.next_screen()
    d.next_screen()
    d.next_screen()
    d.next_screen()
