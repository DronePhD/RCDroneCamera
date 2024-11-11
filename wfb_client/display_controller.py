import time

import gpiod
import logging
import spidev
from gpiod.line import Direction, Value

DRAW_LINE = 0x21
DRAW_RECTANGLE = 0x22
COPY_WINDOW = 0x23
DIM_WINDOW = 0x24
CLEAR_WINDOW = 0x25
FILL_WINDOW = 0x26
DISABLE_FILL = 0x00
ENABLE_FILL = 0x01
CONTINUOUS_SCROLLING_SETUP = 0x27
DEACTIVE_SCROLLING = 0x2E
ACTIVE_SCROLLING = 0x2F

SET_COLUMN_ADDRESS = 0x15
SET_ROW_ADDRESS = 0x75
SET_CONTRAST_A = 0x81
SET_CONTRAST_B = 0x82
SET_CONTRAST_C = 0x83
MASTER_CURRENT_CONTROL = 0x87
SET_PRECHARGE_SPEED_A = 0x8A
SET_PRECHARGE_SPEED_B = 0x8B
SET_PRECHARGE_SPEED_C = 0x8C
SET_REMAP = 0xA0
SET_DISPLAY_START_LINE = 0xA1
SET_DISPLAY_OFFSET = 0xA2
NORMAL_DISPLAY = 0xA4
ENTIRE_DISPLAY_ON = 0xA5
ENTIRE_DISPLAY_OFF = 0xA6
INVERSE_DISPLAY = 0xA7
SET_MULTIPLEX_RATIO = 0xA8
DIM_MODE_SETTING = 0xAB
SET_MASTER_CONFIGURE = 0xAD
DIM_MODE_DISPLAY_ON = 0xAC
DISPLAY_OFF = 0xAE
NORMAL_BRIGHTNESS_DISPLAY_ON = 0xAF
POWER_SAVE_MODE = 0xB0
PHASE_PERIOD_ADJUSTMENT = 0xB1
DISPLAY_CLOCK_DIV = 0xB3
SET_GRAy_SCALE_TABLE = 0xB8
ENABLE_LINEAR_GRAY_SCALE_TABLE = 0xB9
SET_PRECHARGE_VOLTAGE = 0xBB

SET_V_VOLTAGE = 0xBE

OLED_WIDTH = 96
OLED_HEIGHT = 64

logger = logging.getLogger("display")


class DisplayController:
    RST_PIN_NUM = 15
    DC_PIN_NUM = 17
    SPI_FREQ = 32_000_000  # 32 MHz

    def __init__(self):
        self.spi = spidev.SpiDev(0, 0)

        self.gpio = gpiod.request_lines(
            "/dev/gpiochip3",
            consumer="oled",
            config={
                self.DC_PIN_NUM: gpiod.LineSettings(
                    direction=Direction.OUTPUT, output_value=Value.ACTIVE
                ),
                self.RST_PIN_NUM: gpiod.LineSettings(
                    direction=Direction.OUTPUT, output_value=Value.ACTIVE
                ),
            },
        )

    @property
    def RST_PIN(self):
        return self.gpio.get_value(self.RST_PIN_NUM)

    @property
    def DC_PIN(self):
        return self.gpio.get_value(self.DC_PIN_NUM)

    @RST_PIN.setter
    def RST_PIN(self, value):
        self.gpio.set_value(self.RST_PIN_NUM, value)

    @DC_PIN.setter
    def DC_PIN(self, value):
        self.gpio.set_value(self.DC_PIN_NUM, value)

    def module_init(self):
        self.RST_PIN = Value.INACTIVE
        self.spi.max_speed_hz = self.SPI_FREQ
        self.spi.mode = 0b11
        self.DC_PIN = Value.ACTIVE
        return 0

    def module_exit(self):
        self.spi.close()
        self.RST_PIN = Value.INACTIVE
        self.DC_PIN = Value.INACTIVE

    def command(self, cmd):
        self.DC_PIN = Value.INACTIVE
        self.spi.writebytes([cmd])

    def data(self, data):
        self.DC_PIN = Value.ACTIVE
        self.spi.writebytes2(data)


class OLED0in95RGB:
    def __init__(self):
        self.display = DisplayController()
        self.width = OLED_WIDTH
        self.height = OLED_HEIGHT

    def __enter__(self):
        logging.info("Starting the display")
        self.init_display()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()
        self.display.module_exit()
        self.display.gpio.release()
        logging.info("Stopping the display")

    def init_display(self):
        if self.display.module_init() != 0:
            return -1

        self.reset()

        self.display.command(DISPLAY_OFF)  # Display Off
        self.display.command(SET_CONTRAST_A)  # Set contrast for color A
        self.display.command(0xFF)  # 145 0x91
        self.display.command(SET_CONTRAST_B)  # Set contrast for color B
        self.display.command(0xFF)  # 80 0x50
        self.display.command(SET_CONTRAST_C)  # Set contrast for color C
        self.display.command(0xFF)  # 125 0x7D
        self.display.command(MASTER_CURRENT_CONTROL)  # master current control
        self.display.command(0x06)  # 6
        self.display.command(SET_PRECHARGE_SPEED_A)  # Set Second Pre-change Speed For ColorA
        self.display.command(0x64)  # 100
        self.display.command(SET_PRECHARGE_SPEED_B)  # Set Second Pre-change Speed For ColorB
        self.display.command(0x78)  # 120
        self.display.command(SET_PRECHARGE_SPEED_C)  # Set Second Pre-change Speed For ColorC
        self.display.command(0x64)  # 100
        self.display.command(SET_REMAP)  # set remap & data format
        self.display.command(0x72)  # 0x72
        self.display.command(SET_DISPLAY_START_LINE)  # Set display Start Line
        self.display.command(0x0)
        self.display.command(SET_DISPLAY_OFFSET)  # Set display offset
        self.display.command(0x0)
        self.display.command(NORMAL_DISPLAY)  # Set display mode
        self.display.command(SET_MULTIPLEX_RATIO)  # Set multiplex ratio
        self.display.command(0x3F)
        self.display.command(SET_MASTER_CONFIGURE)  # Set master configuration
        self.display.command(0x8E)
        self.display.command(POWER_SAVE_MODE)  # Set Power Save Mode
        self.display.command(0x00)  # 0x00
        self.display.command(PHASE_PERIOD_ADJUSTMENT)  # phase 1 and 2 period adjustment
        self.display.command(0x31)  # 0x31
        self.display.command(DISPLAY_CLOCK_DIV)  # display clock divider/oscillator frequency
        self.display.command(0xF0)
        self.display.command(SET_PRECHARGE_VOLTAGE)  # Set Pre-Change Level
        self.display.command(0x3A)
        self.display.command(SET_V_VOLTAGE)  # Set vcomH
        self.display.command(0x3E)
        self.display.command(DEACTIVE_SCROLLING)  # disable scrolling

        time.sleep(0.1)
        self.display.command(0xAF)  # --turn on oled panel

    def reset(self):
        """Reset the display"""
        self.display.RST_PIN = Value.ACTIVE
        time.sleep(0.1)
        self.display.RST_PIN = Value.INACTIVE
        time.sleep(0.1)
        self.display.RST_PIN = Value.ACTIVE
        time.sleep(0.1)

    def set_windows(self, x_start, y_start, x_end, y_end):
        self.display.command(SET_COLUMN_ADDRESS)
        self.display.command(x_start)  # column start address
        self.display.command(x_end - 1)  # column end address
        self.display.command(SET_ROW_ADDRESS)
        self.display.command(y_start)  # page start address
        self.display.command(y_end - 1)  # page end address

    def clear(self):
        buffer = [0x00] * (self.width * self.height * 2)
        self.show_image(buffer)

    def get_buffer(self, image):
        buf = [0x00] * ((self.width * 2) * self.height)
        im_width, im_height = image.size
        pixels = image.load()
        for y in range(im_height):
            for x in range(im_width):
                # Set the bits for the column of pixels at the current position.
                buf[x * 2 + y * im_width * 2] = ((pixels[x, y][0] & 0xF8) | (pixels[x, y][1] >> 5))
                buf[x * 2 + 1 + y * im_width * 2] = (((pixels[x, y][1] << 3) & 0xE0) | (pixels[x, y][2] >> 3))
        return buf

    def show_image(self, buff):
        self.display.command(SET_COLUMN_ADDRESS)
        self.display.command(0)  # column start address
        self.display.command(self.width - 1)  # column end address
        self.display.command(SET_ROW_ADDRESS)
        self.display.command(0)  # page start address
        self.display.command(self.height - 1)  # page end address

        # Collect all pixels before sending them to the display
        pixels = list()
        for i in range(0, self.height):
            for j in range(0, self.width * 2):
                pixels.append(buff[j + self.width * 2 * i])
        self.display.data(pixels)
