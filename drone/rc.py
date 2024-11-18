import logging
from enum import IntEnum

import dronekit

from drone import buzzer
from drone.camera import CameraService

logger = logging.getLogger("camera")


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
        buzzer.rc_buzz()
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
            logger.info("Starting stream")
            self._camera.start_stream()
        else:
            logger.info("Stopping stream")
            self._camera.stop_stream()

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
            logger.warning(f"Invalid RC value for video channel: {rc_value}")

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
