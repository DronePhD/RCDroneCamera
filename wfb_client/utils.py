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
