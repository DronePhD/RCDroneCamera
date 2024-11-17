import threading
import time

import gpiod
import logging
from gpiod.line import Direction, Value

from wfb_client.data_display import DataDisplay

logger = logging.getLogger("display")


class NextButtonListener:
    CHIP = "/dev/gpiochip3"
    PIN = 16

    def __init__(self, display: DataDisplay):
        self.gpio = gpiod.request_lines(
            self.CHIP,
            consumer="next_button",
            config={
                self.PIN: gpiod.LineSettings(
                    direction=Direction.INPUT, output_value=Value.ACTIVE
                ),
            },
        )
        self.display = display
        self._thread_active = True

    def __enter__(self):
        thread = threading.Thread(target=self._track_push)
        logging.info("Starting the button listener thread")
        thread.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._thread_active = False
        self.gpio.release()
        logging.info("Stopping the button listener thread")

    def _track_push(self):
        logging.info("Listening for button press")
        state = self.gpio.get_value(self.PIN)
        while self._thread_active and self.display.active:
            value = self.gpio.get_value(self.PIN)
            if value == Value.ACTIVE and state == Value.INACTIVE:
                logging.info("Button pressed")
                self.display.next_screen()
                state = Value.ACTIVE
            elif value == Value.INACTIVE:
                state = Value.INACTIVE
            time.sleep(0.05)
