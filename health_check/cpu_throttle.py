import os
from enum import StrEnum


class ThrottleEnum(StrEnum):
    UNDER_VOLTAGE = "Under-voltage detected"
    ARM_FREQ_CAPPED = "Arm frequency capped"
    THROTTLED = "Currently throttled"
    SOFT_TEMP_LIMIT = "Soft temperature limit active"
    UNDER_VOLTAGE_OCCURRED = "Under-voltage has occurred"
    ARM_FREQ_CAPPED_OCCURRED = "Arm frequency capping has occurred"
    THROTTLED_OCCURRED = "Throttling has occurred"
    SOFT_TEMP_LIMIT_OCCURRED = "Soft temperature limit has occurred"


THROTTLE_MAP = {
    0: ThrottleEnum.UNDER_VOLTAGE,
    1: ThrottleEnum.ARM_FREQ_CAPPED,
    2: ThrottleEnum.THROTTLED,
    3: ThrottleEnum.SOFT_TEMP_LIMIT,
}


def check_if_throttled() -> list[bool]:
    """
    Check if the CPU is throttled. Check the value of the get_throttled command and return the result
    based on the value. The value is a bit mask where each bit represents a different type of throttling.
    :return: List of reasons for throttling or None if the CPU is not throttled
    """
    res = os.popen("vcgencmd get_throttled").read().strip()
    res = int(res[res.index("=") + 1:], 0)
    # Should have at least 4 bits
    res_binary = bin(res)[2:]
    res_binary = "0" * (4 - len(res_binary)) + res_binary

    reasons = []
    for bit_n in THROTTLE_MAP.keys():
        bit = res_binary[-bit_n - 1]
        reasons.append(bool(int(bit)))
    return reasons
