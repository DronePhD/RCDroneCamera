import logging
import time
from datetime import datetime
from enum import IntEnum

import click
import dronekit
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FfmpegOutput
from pymavlink import mavutil

# location of the Pixhawk6c serial port and baud rate for the connection.
CONNECTION_STRING = "/dev/serial0"
BAUD_RATE = 921600

# location of the media folder. By default, it's the Samba share folder on the Raspberry Pi, so it can be accessed
# from the GCS.
MEDIA_FOLDER = "/srv/samba/share/"

# URL for the video stream. It's a UDP stream from the Raspberry Pi to the GCS. The GCS can connect to it using
# VLC or any other player that supports UDP streams.
VIDEO_STREAM_URL = "udp://192.168.50.29:12345"


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

    def __init__(self, connection_string: str = CONNECTION_STRING, baud_rate: int = BAUD_RATE):
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


# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)
file_handler = logging.FileHandler("camera.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


class CameraService:
    def __init__(
            self,
            video_stream_url: str = VIDEO_STREAM_URL,
            lores_resolution: tuple = None,
            media_folder: str = MEDIA_FOLDER
    ):
        """
        Initialize the camera service with the video stream URL, lores resolution and the media folder.
        It creates the Picamera2 instance and the encoders for the video stream and the video recording.

        :param video_stream_url: URL for the video stream. Default is VIDEO_STREAM_URL
        :param lores_resolution: Resolution for the lores stream. Default is None
        :param media_folder: Folder to store the media files. Default is MEDIA_FOLDER
        """
        self._picam2 = Picamera2()
        video_config = self._picam2.create_video_configuration(
            main={'size': (1920, 1080)},
            lores={'size': lores_resolution or (1280, 720)},
        )
        self._picam2.configure(video_config)

        self._stream_encoder = H264Encoder(repeat=True, iperiod=15)
        self._video_encoder = H264Encoder(10000000)

        self._stream_output = FfmpegOutput(f"-f mpegts {video_stream_url}")
        self._video_output = None

        self.streaming = False
        self.video_active = False

        self._media_folder = media_folder

    def __enter__(self):
        """
        Start the camera service when entering the context manager. It starts the Picamera2 instance.
        """
        self._picam2.start()
        logger.info("Camera service started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stop the camera service when exiting the context manager. It stops the stream and the video recording if active
        and closes the Picamera2, releasing the resources.
        """
        self._picam2.close()
        if self.streaming:
            self.stop_stream()
        if self.video_active:
            self.stop_video()

        if exc_type:
            logger.exception("An error occurred in the stream loop")
            return False

        logger.info("Camera service stopped")
        return True

    def start_stream(self):
        """
        Start the video stream to the specified URL using the lores stream.
        """
        if self.streaming:
            logger.error("Stream is already active")
            return

        self._picam2.start_encoder(self._stream_encoder, self._stream_output, name="lores")
        self.streaming = True
        logger.debug(f"Started streaming to {self._stream_output.output_filename}")

    def stop_stream(self):
        """
        Stop the video stream
        """
        if not self.streaming:
            logger.error("Stream is not active")
            return

        self._picam2.stop_encoder(self._stream_encoder)
        self.streaming = False
        logger.debug(f"Stopped streaming to {self._stream_output.output_filename}")

    def start_video(self):
        """
        Start recording video to a file using the main encoder and the high quality settings.
        """
        if self.video_active:
            logger.error("Video is already active")
            return

        self._video_output = FfmpegOutput(self._generate_filename("video", "mp4"))
        self._picam2.start_encoder(self._video_encoder, self._video_output, quality=Quality.VERY_HIGH)
        self.video_active = True
        logger.debug(f"Started recording video to {self._video_output.output_filename}")

    def stop_video(self):
        """
        Stop the video recording
        """
        if not self.video_active:
            logger.error("Video is not active")
            return

        self._picam2.stop_encoder(self._video_encoder)
        self.video_active = False
        logger.debug(f"Stopped recording video to {self._video_output.output_filename}")
        self._video_output = None

    def capture_photo(self):
        """
        Capture a photo and save it to the media folder. Works via the capture request, so it's non-blocking.
        """
        filename = self._generate_filename("photo", "jpg")
        request = self._picam2.capture_request()
        request.save("main", filename)
        request.release()
        logger.debug(f"Captured photo to {filename}")

    def _generate_filename(self, mode: str, extension: str) -> str:
        """
        Generate a filename for the media files. It includes the mode (photo or video) and the current timestamp.

        :param mode: file mode (photo or video)
        :param extension: file extension (jpg or mp4)
        :return: generated filename
        """
        return self._media_folder + f"{mode}--{datetime.now().strftime('%Y-%m-%d--%H-%M-%S')}.{extension}"


class RCValueEnum(IntEnum):
    LOW = 1000
    MEDIUM = 1500
    HIGH = 2000


class RCService:
    CAMERA_VIDEO_CHANNEL = "7"  # Toggle switch for video recording. Top position starts recording, bottom stops.
    CAMERA_PHOTO_CHANNEL = "9"  # Button for taking a photo. Press to take a photo.

    def __init__(self, connection_string: str, baud_rate: int, camera: CameraService):
        """
        Initialize the RC service with the connection string, baud rate and the camera service.
        It connects to the vehicle and sets up the RC cache for the camera channels.

        :param connection_string: Connection string for the vehicle. Default is CONNECTION_STRING
        :param baud_rate: Baud rate for the connection. Default is BAUD_RATE
        :param camera: Camera service instance
        """
        self._camera = camera
        self._vehicle = dronekit.connect(connection_string, baud=baud_rate, wait_ready=True)
        logger.info(f"Connected to vehicle on {connection_string} at {baud_rate}")

        # Because the RC channels are updated at 1Hz, we need to cache the values and check for changes.
        self._rc_cache = {
            self.CAMERA_VIDEO_CHANNEL: RCValueEnum.LOW,
            self.CAMERA_PHOTO_CHANNEL: RCValueEnum.LOW,
        }

    def listen(self) -> "RCService":
        """
        Start listening for changes in the RC channels and arm status of the vehicle

        :return: self
        """
        self._vehicle.add_attribute_listener("channels", self._channel_observer)
        self._vehicle.add_attribute_listener("armed", self._arm_observer)
        logger.info("Listening for RC events")
        return self

    def close(self) -> None:
        """
        Close the connection to the vehicle
        """
        self._vehicle.close()
        logger.info("Disconnected from vehicle")

    def _channel_observer(self, vehicle_obj: dronekit.Vehicle, name: str, value: dict) -> None:
        """
        Callback observer method for changes in the RC channels

        :param vehicle_obj: vehicle object from dronekit, not used
        :param name: name of the attribute that changed
        :param value: new value of the attribute
        """
        if name != "channels" or not value:
            return

        # Check for changes in selected channels, and update the cache if needed and call the handler
        for channel, rc_value in value.items():
            if channel not in self._rc_cache:
                continue
            rc_value = self._translate_rc_value(rc_value)
            if self._rc_cache[channel] != rc_value:
                self._rc_cache[channel] = rc_value
                self._handle_rc_change(channel, rc_value)

    def _arm_observer(self, vehicle_obj: dronekit.Vehicle, name: str, value: bool) -> None:
        """
        Callback observer method for changes in the armed status of the vehicle. Starts the stream when armed and
        stops when disarmed.

        :param vehicle_obj: vehicle object from dronekit, not used
        :param name: name of the attribute that changed. Not used
        :param value: new value of the attribute
        """
        logger.debug(f"Vehicle armed: {value}")

        if value is True:
            self._camera.start_stream()
            logger.info("Started stream")
        else:
            self._camera.stop_stream()
            logger.info("Stopped stream")

    def _handle_rc_change(self, channel: str, rc_value: RCValueEnum) -> None:
        """
        Handle changes in the RC channels. Ii checks the channel and the value and calls the appropriate method
        to either start or stop the video or take a photo.

        :param channel: Channel number from the RC controller
        :param rc_value: Value of the channel. Can be LOW, MEDIUM or HIGH,
                         depending on the position of the stick or button
        """
        if channel == self.CAMERA_VIDEO_CHANNEL:
            self._handle_video_channel(rc_value)
        elif channel == self.CAMERA_PHOTO_CHANNEL:
            self._handle_photo_channel(rc_value)

    def _handle_photo_channel(self, rc_value: RCValueEnum) -> None:
        """
        Handle changes in the photo channel. It takes a photo when the button is pressed.

        :param rc_value: Value of the channel. Can be LOW, MEDIUM or HIGH,
        """
        # It means the button was pressed. We don't care about the release event
        if rc_value == RCValueEnum.HIGH:
            self._camera.capture_photo()
            logger.info("Captured photo")

    def _handle_video_channel(self, rc_value: RCValueEnum) -> None:
        """
        Handle changes in the video channel. It starts or stops the video recording when the toggle switch is moved.
        If the switch is in the top position, it starts the video recording. If it's in the bottom position,
        it stops it. Middle position is ignored.

        :param rc_value: Value of the channel. Can be LOW or HIGH,
        """
        if rc_value == RCValueEnum.HIGH:
            self._camera.start_video()
            logger.info("Started recording video")
        elif rc_value == RCValueEnum.LOW:
            self._camera.stop_video()
            logger.info("Stopped recording video")
        else:
            logger.error(f"Invalid RC value for video channel: {rc_value}")

    @staticmethod
    def _translate_rc_value(rc_value: int) -> RCValueEnum:
        """
        Translate the raw RC value to the enum value

        :param rc_value: Raw RC value from the controller. Can be any value between 0 and 2000+. But it transmits with
                         errors, so we round it to the nearest 100.
        :return: Enum value of the RC channel
        """
        rc_value = round(rc_value / 100) * 100  # Round to nearest 100, e.g. 1510 -> 1500
        if rc_value == RCValueEnum.LOW:
            return RCValueEnum.LOW
        elif rc_value == RCValueEnum.MEDIUM:
            return RCValueEnum.MEDIUM
        elif rc_value == RCValueEnum.HIGH:
            return RCValueEnum.HIGH
        else:
            logger.error(f"Invalid RC value: {rc_value}")
            return RCValueEnum.LOW


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
    with CameraService(stream_url, stream_resolution, media_folder) as camera:
        RCService(drone_connection, drone_baud_rate, camera).listen()
        time.sleep(1000000)  # Run forever (realistically, until the battery runs out)


if __name__ == "__main__":
    main()

    """
        To run in ipython comment out the main function and run the following code in the ipython terminal.:
        
        mavlink_handler = MAVLinkHandler()
        mavlink_handler.setLevel(logging.INFO)
        logger.addHandler(mavlink_handler)
        with CameraService(VIDEO_STREAM_URL, (1280, 720), MEDIA_FOLDER) as camera:
            RCService(CONNECTION_STRING, BAUD_RATE, camera).listen()
            time.sleep(1000000)
    """
