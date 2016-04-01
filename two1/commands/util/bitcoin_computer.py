""" Contains methods to interact with the bitcoin computer hardware """
# standard python imports
import socket
import json
from datetime import datetime


# socket timeout value
TIMEOUT = 5

# minerd unix sock location
MINERD_SOCK = '/tmp/minerd.sock'


def get_device_uuid():
    """ Reads the uuid from the device by checking device tree

    Todo:
        throw the FileNotFound exception instead of returning None

    Returns:
        str: full uuid of device

    Raises:
        FileNotFoundError: if uuid file doesn't exist on the device
    """
    uuid = None
    try:
        with open("/proc/device-tree/hat/uuid", "r") as f:
            uuid = f.read().strip("\x00").strip("\n")
    except FileNotFoundError:
        pass
    return uuid if uuid else None


def has_mining_chip():
    """ Check for presence of mining chip via file presence

    The full test is to actually try to boot the chip, but we
    only try that if this file exists.

    We keep this file in two1/commands/status to avoid a circular
    import.
    Todo:
        Move out of status

    Returns:
        bool: True if device is a bitcoin computer, false otherwise
    """
    try:
        with open("/proc/device-tree/hat/product", "r") as f:
            return f.read().startswith('21 Bitcoin')
    except FileNotFoundError:
        return False


def get_hashrate(hashrate_sample):
    """ Uses unix socks to get hashrate of mining chip on current system

        minerd, the bitcoin computer mining client publishes all events to
        a unix socket. This function listens on it's socket until a statistics
        event occurs that contains hashrate information.

    Args:
        hashrate_sample (str): "5min", "15min", or "60min"

    Returns:
        int: The raw hashrate value in hash per second if uptime is greater than the
            specified amount of time in hashrate_sample. Otherwise -1 is returned.

    Raises:
        FileNotFoundError: if minerd is not running and unix sock doesn't exist
        TimeoutError: if a StatisticsEvent isn't found before the timeout duration
            or the socket server disconnects.
        ValueError: if hashrate_sample is not one of "5min", "15min", or "60min"
    """
    uptime_durations = {"5min": 5*60, "15min": 15*60, "60min": 60*60}
    if hashrate_sample not in uptime_durations.keys():
        raise ValueError

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    s.connect(MINERD_SOCK)

    # Bytes received from unix sock is read as bytes
    buf = b""

    # only read for timeout seconds waiting for a StatisticsEvent
    start_time = datetime.now()
    total_time = start_time - start_time

    while total_time.total_seconds() < TIMEOUT:
        total_time = datetime.now() - start_time

        # Blocks until event is received or a timeout occurs
        try:
            chunk = s.recv(4096)
        except socket.timeout:
            raise TimeoutError

        # If server disconnected
        if not chunk:
            s.close()
            raise TimeoutError

        buf += chunk
        while b"\n" in buf:
            pos = buf.find(b"\n")
            data = buf[0:pos].decode('utf-8')
            buf = buf[pos+1:]

            # empty message from minerd
            if not data:
                continue

            event = json.loads(data)

            if event['type'] == "StatisticsEvent":
                if event['payload']['statistics']['uptime'] > uptime_durations[hashrate_sample]:
                    return event['payload']['statistics']['hashrate'][hashrate_sample]
                else:
                    return -1

    raise TimeoutError
