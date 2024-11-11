import logging
import os
from datetime import datetime

import msgpack
from twisted.internet import reactor, defer
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import Int32StringReceiver

from wfb_client.button import NextButtonListener
from wfb_client.data_display import DataDisplay

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


class DisplayAntennaStat(Int32StringReceiver):
    def stringReceived(self, string):
        """
        Input data format:
        {
            "id": "video rx",
            "packets": {   
                "all": (342, 112535),
                "all_bytes": (465395, 153904506),
                "bad": (0, 0),
                "dec_err": (0, 0),
                "dec_ok": (342, 112535),
                "fec_rec": (65, 10344),
                "lost": (25, 2806),
                "out": (285, 85354),
                "out_bytes": (375275, 112609410)
            },
            "rx_ant_stats": {   
                ((5805, 1, 20), 0): (342, -58, -53, -52, 16, 21, 24),
                ((5805, 1, 20), 1): (342, -48, -44, -44, 16, 25, 31)
            },
            "session": {"epoch": 0, "fec_k": 8, "fec_n": 12, "fec_type": "VDM_RS"},
            "timestamp": 1731082064.316669,
            "tx_ant": 0,
            "type": "rx"
        }
        """
        attrs = msgpack.unpackb(string, strict_map_key=False, use_list=False, raw=False)
        if attrs["type"] != "rx" or attrs.get("id") != "video rx":
            return

        packets = attrs["packets"]
        session = attrs["session"]
        antenna = attrs["rx_ant_stats"]

        packet_data = {
            "recv": packets["all"],
            "udp": packets["out"],
            "fec_r": packets["fec_rec"],
            "lost": packets["lost"],
            "d_err": packets["dec_err"],
            "bad": packets["bad"],
        }
        flow_data = {
            "in": packets["all_bytes"][0],
            "out": packets["out_bytes"][0],
            "fec": (session["fec_k"], session["fec_n"]) if session else (0, 0),
        }
        antenna_data = {
            "rssi": {"min": 0, "avg": 0, "max": 0},
            "snr": {"min": 0, "avg": 0, "max": 0}
        }
        for pkt_s, rssi_min, rssi_avg, rssi_max, snr_min, snr_avg, snr_max in antenna.values():
            antenna_data["rssi"]["min"] += rssi_min
            antenna_data["rssi"]["avg"] += rssi_avg
            antenna_data["rssi"]["max"] += rssi_max
            antenna_data["snr"]["min"] += snr_min
            antenna_data["snr"]["avg"] += snr_avg
            antenna_data["snr"]["max"] += snr_max

        if antenna:
            for key in antenna_data:
                for k in antenna_data[key]:
                    antenna_data[key][k] /= len(antenna)

        self.factory.display.data = {
            "packet": packet_data,
            "flow": flow_data,
            "antenna": antenna_data
        }


class DisplayAntennaStatsClientFactory(ReconnectingClientFactory):
    def __init__(self, display: DataDisplay):
        self.display = display

    def buildProtocol(self, addr):
        self.resetDelay()
        packets = DisplayAntennaStat()
        packets.factory = self
        return packets


def main(display: DataDisplay):
    logging.info("Starting the client")
    reactor.connectTCP("127.0.0.1", 8003, DisplayAntennaStatsClientFactory(display))


def abort_on_crash(display: DataDisplay):
    def abort_on_crash_inner(failure, *args, **kwargs):
        if isinstance(failure, defer.FirstError):
            failure = failure.value.subFailure
        logger.error(failure.getTraceback())
        reactor.stop()
        display.stop()

    return abort_on_crash_inner


if __name__ == "__main__":
    d = DataDisplay()
    d.start()
    NextButtonListener(d)
    reactor.callWhenRunning(lambda: defer.maybeDeferred(main, d).addErrback(abort_on_crash(d)))
    reactor.run()
