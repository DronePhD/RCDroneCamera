import logging
import os
from datetime import datetime

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
from picamera2.outputs import FfmpegOutput

from src.gstreamer import GStreamerOutput

logger = logging.getLogger("camera")


class CameraService:
    def __init__(
            self,
            video_stream_url: str,
            media_folder: str,
            lores_resolution: tuple = None,
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
        self._video_encoder = H264Encoder()

        self._stream_output = GStreamerOutput(video_stream_url)
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
            logger.warning("Stream is already active")
            return

        # Check if WFB is running. If not, the stream won't work.
        if os.system("systemctl is-active --quiet wifibroadcast@drone") != 0:
            logger.error("Wifibroadcast service is not running")
            return

        self._picam2.start_encoder(self._stream_encoder, self._stream_output, name="lores", quality=Quality.MEDIUM)
        self.streaming = True
        logger.debug(f"Started streaming to {self._stream_output.output_filename}")

    def stop_stream(self):
        """
        Stop the video stream
        """
        if not self.streaming:
            logger.warning("Stream is not active")
            return

        self._picam2.stop_encoder(self._stream_encoder)
        self.streaming = False
        logger.debug(f"Stopped streaming to {self._stream_output.output_filename}")

    def start_video(self):
        """
        Start recording video to a file using the main encoder and the high quality settings.
        """
        if self.video_active:
            logger.warning("Video is already active")
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
            logger.warning("Video is not active")
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
