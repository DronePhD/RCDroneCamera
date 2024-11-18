import abc
import os
from collections import deque

import numpy as np
from PIL import ImageFont, Image, ImageDraw
from matplotlib import font_manager as fm, pyplot as plt

from wfb_client.display_controller import OLED_WIDTH, OLED_HEIGHT
from wfb_client.utils import human_rssi, human_snr, human_packet_loss, human_rate, human_temp


class DataScreen(metaclass=abc.ABCMeta):
    def __init__(self, next_screen: "DataScreen" = None):
        self._font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static/SFMonoRegular.otf")
        self.font = ImageFont.truetype(self._font_path, 9)
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
        temp, temp_color = human_temp(data.get("temp", {}).get("temperature")) if data.get("temp") else (0, "WHITE")
        throttled = data.get("temp", {}).get("throttled", False)

        image = Image.new("RGB", (OLED_WIDTH, OLED_HEIGHT), 0)  # 0: clear the frame
        draw = ImageDraw.Draw(image)
        draw.text(
            xy=(OLED_WIDTH // 2, 0),
            text="OVERVIEW",
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
        draw.text(
            xy=(0, 36),
            text=f"Temp: {temp}°C",
            font=self.font,
            fill=temp_color,
            align="left",
            anchor="la"
        )
        draw.text(
            xy=(OLED_WIDTH - 1, 36),
            text="T" if throttled else "",
            font=self.font,
            fill="RED",
            align="right",
            anchor="ra"
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
        draw.text((0, 9), f"IN: {human_rate(data["in"])}", font=self.font, fill="WHITE")
        draw.text((0, 18), f"OUT: {human_rate(data["out"])}", font=self.font, fill="WHITE")
        draw.text((0, 27), f"FEC: {data["fec"][0]}/{data["fec"][1]}", font=self.font, fill="WHITE")
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
        draw.text((0, 9), f"RSSI:\n{data["rssi"]["min"]}>{data["rssi"]["avg"]}>{data["rssi"]["max"]}",
                  font=self.font, fill="WHITE", spacing=0)
        draw.text((0, 27), f"SNR:\n{data["snr"]["min"]}>{data["snr"]["avg"]}>{data["snr"]["max"]}",
                  font=self.font, fill="WHITE", spacing=0)
        return image


class TempLogScreen(DataScreen):
    MAX_PLOT_SIZE = 60  # Maximum number of data points to plot

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_figure()
        self._plot_data = deque(maxlen=self.MAX_PLOT_SIZE)

    def _init_figure(self):
        # Load the custom font
        fm.fontManager.addfont(self._font_path)
        font_prop = fm.FontProperties(fname=self._font_path)
        plt.rcParams["font.family"] = font_prop.get_name()

        # Create a figure with the specified size
        self._fig = plt.figure(figsize=(OLED_WIDTH / 100, OLED_HEIGHT / 100), dpi=100, facecolor="black")
        self._ax = self._fig.add_subplot()

        # Adjust the position of the plot to include padding for the title
        self._fig.subplots_adjust(left=0, bottom=0, right=1, top=0.7)

        # Set axis limits
        self._ax.set_xlim(left=-60, right=0)
        self._ax.set_ylim(bottom=30, top=90)

        # Set the background color of the plot area
        self._ax.set_facecolor("black")

    def draw(self, data: dict):
        """
        Draw a plot of the temperature log. The plot is a line graph of the temperature values over time.
        """
        if "temp" in data:
            self._plot_data.append((data["temp"]["temperature"], data["temp"]["timestamp"]))

        if not self._plot_data:
            return self._init_screen()

        # Recalculate the timestamps to be relative to the latest data point
        timestamps = [i - self._plot_data[-1][1] for i in [v[1] for v in self._plot_data]]
        values = np.array([v[0] for v in self._plot_data])

        # Plot the data with different colors based on value ranges
        self._ax.clear()
        self._ax.plot(timestamps, values, color="black", linewidth=1)  # Plot the line in black for reference

        # Set title
        self._ax.set_title("TEMP", fontsize=6, color="white")

        # Fill areas with different colors
        self._ax.fill_between(timestamps, values, where=(values < 70), color="green")
        self._ax.fill_between(timestamps, values, where=(values >= 70) & (values < 80), color="yellow")
        self._ax.fill_between(timestamps, values, where=(values >= 80), color="red")

        # Add a horizontal line at the maximum value
        max_value = max(values)
        self._ax.axhline(y=max_value, color="white", linestyle="--", linewidth=.5)
        # Add text to indicate the maximum value
        self._ax.text(0, max_value, f"{max_value}", color="white", fontsize=6, verticalalignment="bottom",
                      horizontalalignment="right")

        # Convert plot to PIL Image
        self._fig.canvas.draw()
        return Image.frombytes("RGB", self._fig.canvas.get_width_height(), self._fig.canvas.tostring_rgb())
