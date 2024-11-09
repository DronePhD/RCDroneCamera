import logging
import threading
import time

import gpiod
from gpiod.line import Direction, Value

from wfb_client.data_display import DataDisplay

logger = logging.getLogger("display")


class NextButtonListener:
    PIN = 16

    def __init__(self, display: DataDisplay):
        self.gpio = gpiod.request_lines(
            "/dev/gpiochip3",
            consumer="next_button",
            config={
                self.PIN: gpiod.LineSettings(
                    direction=Direction.INPUT, output_value=Value.ACTIVE
                ),
            },
        )
        self.display = display

    def start(self):
        thread = threading.Thread(target=self._track_push)
        thread.start()

    def _track_push(self):
        logging.info("Listening for button press")
        state = self.gpio.get_value(self.PIN)
        while True:
            value = self.gpio.get_value(self.PIN)
            if value == Value.ACTIVE and state == Value.INACTIVE:
                logging.info("Button pressed")
                self.display.next_screen()
                state = Value.ACTIVE
            elif value == Value.INACTIVE:
                state = Value.INACTIVE
            time.sleep(0.05)

    def __del__(self):
        self.gpio.release()
