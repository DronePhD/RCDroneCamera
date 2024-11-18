import logging
import os
import time
from datetime import datetime

import click

from drone.camera import CameraService
from drone.mavlink_logging import MAVLinkHandler
from drone.rc import RCService

# location of the Pixhawk6c serial port and baud rate for the connection.
CONNECTION_STRING = "/dev/serial0"
BAUD_RATE = 921600

# location of the media folder. By default, it's the Samba share folder on the Raspberry Pi, so it can be accessed
# from the GCS.
MEDIA_FOLDER = "/srv/samba/share/"

# URL for the video stream. It's a UDP stream from the Raspberry Pi to the GCS. The GCS can connect to it using
# VLC or any other player that supports UDP streams.
VIDEO_STREAM_URL = "192.168.50.29:12345"

# Set up logging
logger = logging.getLogger("camera")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

log_directory = "/var/log/camera"
os.makedirs(log_directory, exist_ok=True)
filename = f"camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(os.path.join(log_directory, filename))
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

shared_directory = "/srv/samba/share/logs/camera"
os.makedirs(shared_directory, exist_ok=True)
shared_file_handler = logging.FileHandler(os.path.join(shared_directory, filename))
shared_file_handler.setFormatter(formatter)
logger.addHandler(shared_file_handler)


@click.command()
@click.option("--stream-resolution", default="1280x720", help="Resolution for the stream")
@click.option("--stream-url", default=VIDEO_STREAM_URL, help="URL for the video stream")
@click.option("--media-folder", default=MEDIA_FOLDER, help="Folder to store media files")
@click.option("--drone-connection", default=CONNECTION_STRING, help="Drone connection string")
@click.option("--drone-baud-rate", default=BAUD_RATE, help="Drone baud rate")
def main(
        stream_resolution: str = "1280x720",
        stream_url: str = VIDEO_STREAM_URL,
        media_folder: str = MEDIA_FOLDER,
        drone_connection: str = CONNECTION_STRING,
        drone_baud_rate: int = BAUD_RATE,
):
    """
    Main function to start the camera and RC services. It initializes the camera service and the RC service
    and listens for changes in the RC channels. It runs forever until the battery runs out.
    """
    mavlink_handler = MAVLinkHandler(drone_connection, drone_baud_rate)
    mavlink_handler.setLevel(logging.INFO)
    logger.addHandler(mavlink_handler)

    stream_resolution = tuple(map(int, stream_resolution.split("x")))
    with CameraService(stream_url, media_folder, stream_resolution) as camera:
        RCService(drone_connection, drone_baud_rate, camera).listen()

        # Health check for the WFB service
        while True:
            camera.wfb_running = os.system("systemctl is-active --quiet wifibroadcast@drone") == 0
            time.sleep(2)  # Run forever (realistically, until the battery runs out)


if __name__ == "__main__":
    main()
