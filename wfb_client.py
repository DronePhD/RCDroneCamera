import os
from datetime import datetime

import logging
from twisted.internet import reactor, defer

from wfb_client.button import NextButtonListener
from wfb_client.client_factory import DisplayAntennaStatsClientFactory
from wfb_client.data_display import DataDisplay
from wfb_client.mavlink import MAVLink

# Set up logging
logger = logging.getLogger("display")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

log_directory = "/var/log/display"
os.makedirs(log_directory, exist_ok=True)
filename = f"camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(os.path.join(log_directory, filename))
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def main(display: DataDisplay):
    logging.info("Starting the client")
    reactor.connectTCP("127.0.0.1", 8003, DisplayAntennaStatsClientFactory(display))


def abort_on_crash(failure, *args, **kwargs):
    if isinstance(failure, defer.FirstError):
        failure = failure.value.subFailure
    logger.error(failure.getTraceback())


if __name__ == "__main__":
    with DataDisplay() as d, NextButtonListener(d), MAVLink(d):
        reactor.callWhenRunning(lambda: defer.maybeDeferred(main, d).addErrback(abort_on_crash))
        reactor.run()
