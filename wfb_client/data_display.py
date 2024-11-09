import abc
import logging
import os
import threading
import time

from PIL import Image, ImageDraw, ImageFont

from wfb_client.display_controller import OLED_WIDTH, OLED_HEIGHT, OLED0in95RGB

logging = logging.getLogger("display")


def human_rate(r):
    rate = r * 8

    if rate >= 1000 * 1000:
        rate = rate / 1024 / 1024
        mod = "mbit/s"
    else:
        rate = rate / 1024
        mod = "kbit/s"

    if rate < 10:
        return "%0.1f %s" % (rate, mod)
    else:
        return "%3d %s" % (rate, mod)


def human_rssi(rssi: int) -> tuple[int, str]:
    percent = 2 * (rssi + 100)
    if percent < 25:
        return percent, "RED"
    if percent < 50:
        return percent, "ORANGE"
    if percent < 75:
        return percent, "YELLOW"
    if percent < 100:
        return percent, "GREEN"
    return percent, "CYAN"


def human_snr(snr: int) -> tuple[int, str]:
    if snr < 15:
        return snr, "RED"
    if snr < 25:
        return snr, "YELLOW"
    if snr < 40:
        return snr, "GREEN"
    return snr, "CYAN"


def human_packet_loss(data) -> tuple[float, str]:
    lost = data.get("lost")
    if not lost:
        return 0, "GREEN"
    received = data.get("recv")
    if not received or received[0] == 0:
        return 100, "RED"

    packet_loss = 100 * (lost[0] / received[0])
    if packet_loss < 1:
        return packet_loss, "GREEN"
    if packet_loss < 5:
        return packet_loss, "YELLOW"
    return packet_loss, "RED"


class DataScreen(metaclass=abc.ABCMeta):
    def __init__(self, next_screen: "DataScreen" = None):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SFMonoRegular.otf")
        self.font = ImageFont.truetype(path, 9)
        self.next_screen = next_screen

    @abc.abstractmethod
    def draw(self, data: dict):
        pass

    def _init_screen(self):
        image = Image.new("RGB", (OLED_WIDTH, OLED_HEIGHT), 0)  # 0: clear the frame
        draw = ImageDraw.Draw(image)
        draw.text(
            xy=(OLED_WIDTH // 2, OLED_HEIGHT // 2),
            text="[No data]",
            font=self.font,
            fill="WHITE",
            align="center",
            anchor="mm"
        )
        return image

    def __next__(self):
        return self.next_screen


class OverviewScreen(DataScreen):
    def draw(self, data: dict):
        rssi_data = data.get("antenna", {}).get("rssi", {}).get("avg")
        snr_data = data.get("antenna", {}).get("snr", {}).get("avg")
        packet_data = data.get("packet", {})
        if not rssi_data and not snr_data and not packet_data:
            return self._init_screen()

        rssi, rssi_color = human_rssi(rssi_data) if rssi_data else (0, "WHITE")
        snr, snr_color = human_snr(snr_data) if snr_data else (0, "WHITE")
        pl_percent, pl_color = human_packet_loss(packet_data) if packet_data else (0, "WHITE")

        image = Image.new("RGB", (OLED_WIDTH, OLED_HEIGHT), 0)  # 0: clear the frame
        draw = ImageDraw.Draw(image)
        draw.text(
            xy=(OLED_WIDTH // 2, 0),
            text="Overview",
            font=self.font,
            fill="WHITE",
            align="center",
            anchor="mt"
        )
        draw.text(
            xy=(0, 9),
            text=f"RSSI: {rssi}%",
            font=self.font,
            fill=rssi_color,
            align="left",
            anchor="la"
        )
        draw.text(
            xy=(0, 18),
            text=f"SNR: {snr}dBm",
            font=self.font,
            fill=snr_color,
            align="left",
            anchor="la"
        )
        draw.text(
            xy=(0, 27),
            text=f"Pct loss: {pl_percent:.2f}%",
            font=self.font,
            fill=pl_color,
            align="left",
            anchor="la"
        )
        return image


class PacketScreen(DataScreen):
    def draw(self, data: dict):
        data = data.get("packet")
        if not data:
            return self._init_screen()

        image = Image.new("RGB", (OLED_WIDTH, OLED_HEIGHT), 0)  # 0: clear the frame
        draw = ImageDraw.Draw(image)
        draw.text((55, 0), "pkt/s", font=self.font, fill="WHITE", spacing=0, align="right", anchor="ra")
        draw.text((60, 0), "pkt", font=self.font, fill="WHITE", spacing=0, align="left")
        for i, (k, v) in enumerate(data.items()):
            height = 9 * (i + 1)
            draw.text((0, height), k, font=self.font, fill="WHITE", spacing=0, align="left")
            fill = "RED" if v[0] > 0 and i > 1 else "WHITE"
            draw.text((55, height), str(v[0]), font=self.font, fill=fill, spacing=0, align="right", anchor="ra")
            draw.text((60, height), str(v[1]), font=self.font, fill=fill, spacing=0, align="left")

        return image


class FlowScreen(DataScreen):
    def draw(self, data: dict):
        data = data.get("flow")
        if not data:
            return self._init_screen()
        image = Image.new("RGB", (OLED_WIDTH, OLED_HEIGHT), "BLACK")
        draw = ImageDraw.Draw(image)
        draw.text(
            xy=(OLED_WIDTH // 2, 0),
            text="FLOW",
            font=self.font,
            fill="WHITE",
            align="center",
            anchor="mt")
        draw.text((0, 9), f"IN: {human_rate(data['in'])}", font=self.font, fill="WHITE")
        draw.text((0, 18), f"OUT: {human_rate(data['out'])}", font=self.font, fill="WHITE")
        draw.text((0, 27), f"FEC: {data['fec'][0]}/{data['fec'][1]}", font=self.font, fill="WHITE")
        return image


class AntennaScreen(DataScreen):
    def draw(self, data: dict):
        data = data.get("antenna")
        if not data:
            return self._init_screen()
        image = Image.new("RGB", (OLED_WIDTH, OLED_HEIGHT), "BLACK")
        draw = ImageDraw.Draw(image)
        draw.text(
            xy=(OLED_WIDTH // 2, 0),
            text="ANTENNA",
            font=self.font,
            fill="WHITE",
            align="center",
            anchor="mt")
        draw.text((0, 9), f"RSSI:\n{data['rssi']['min']}>{data['rssi']['avg']}>{data['rssi']['max']}",
                  font=self.font, fill="WHITE", spacing=0)
        draw.text((0, 27), f"SNR:\n{data['snr']['min']}>{data['snr']['avg']}>{data['snr']['max']}",
                  font=self.font, fill="WHITE", spacing=0)
        return image


class DataDisplay:
    def __init__(self):
        screens = [OverviewScreen(), PacketScreen(), FlowScreen(), AntennaScreen()]
        self.current_screen = screens[0]
        # Link the screens together as a circular linked list
        for s in screens[:-1]:
            s.next_screen = screens[screens.index(s) + 1]
        screens[-1].next_screen = self.current_screen

        self._data = {}
        self._display = OLED0in95RGB()

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value: dict):
        self._data = value

    def next_screen(self):
        self.current_screen = next(self.current_screen)

    def start(self):
        thread = threading.Thread(target=self._refresh_loop)
        thread.start()

    def _refresh_loop(self):
        logging.info("Starting the display loop")
        while True:
            image = self.current_screen.draw(self.data)
            self._display.show_image(self._display.get_buffer(image))
            time.sleep(0.05)


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
    display = DataDisplay()
    display.data = test_data
    display.next_screen()
    display.next_screen()
    display.next_screen()
