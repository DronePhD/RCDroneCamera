import gc
import signal
import subprocess

import prctl
from picamera2.outputs import Output


class GStreamerOutput(Output):
    """
    Output class for GStreamer. It receives the output filename in the format host:port and starts the GStreamer
    Is a fork of the picamera2.outputs.FfmpegOutput class with some modifications to work with the GStreamer.
    """

    def __init__(self, output_filename):
        super().__init__(pts=None)
        self.gstreamer = None
        self.output_filename = output_filename
        self.host = output_filename.split(":")[0]
        self.port = output_filename.split(":")[1]

    def start(self):
        general_options = [
            "-v",
            "fdsrc",
            "!",
        ]
        video_input = [
            "h264parse",
            "!",
        ]
        video_encoder = [
            "rtph264pay",
            "config-interval=1",
            "pt=35",
            "!"
        ]
        video_sink = [
            "udpsink",
            f"host={self.host}",
            f"port={self.port}",
        ]
        command = ['gst-launch-1.0'] + general_options + video_input + video_encoder + video_sink
        # The preexec_fn is a slightly nasty way of ensuring GStreamer gets stopped if we quit
        # without calling stop() (which is otherwise not guaranteed).
        self.gstreamer = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            preexec_fn=lambda: prctl.set_pdeathsig(signal.SIGKILL)
        )
        super().start()

    def stop(self):
        super().stop()
        if self.gstreamer is not None:
            self.gstreamer.stdin.close()  # GStreamer needs this to shut down tidily
            try:
                self.gstreamer.terminate()
            except Exception:
                pass
            self.gstreamer = None
            # This seems to be necessary to get the subprocess to clean up fully.
            gc.collect()

    def outputframe(self, frame, keyframe=True, timestamp=None):
        if self.recording and self.gstreamer:
            # Handle the case where the GStreamer process has gone away for reasons of its own.
            try:
                self.gstreamer.stdin.write(frame)
                self.gstreamer.stdin.flush()  # forces every frame to get timestamped individually
            except Exception as e:  # presumably a BrokenPipeError? should we check explicitly?
                self.gstreamer = None
                if self.error_callback:
                    self.error_callback(e)
            else:
                self.outputtimestamp(timestamp)
