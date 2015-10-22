import sys
import os.path
import json
import time
import logging
import base64
import subprocess
import zipfile
import tempfile
import termios
import glob
import errno

if sys.version_info.major > 2:
    # Python 3
    from urllib.request import urlretrieve
    raw_input = input
else:
    # Python 2
    from urllib import urlretrieve

__version__ = "10-21-2015-23:00:00"


# Logger (for debug)

logger = logging.getLogger(__name__)


# Print helper functions

def print_step(s):
    print("\x1b[1;35m" + s + "\x1b[0m")


def print_warning(s):
    print("\x1b[1;33m" + s + "\x1b[0m")


def print_error(s):
    print("\x1b[1;31m" + s + "\x1b[0m")


# Serial class

class Serial:

    def __init__(self, path):
        """Open serial port at specified device path with baudrate 115200, and
        8N1."""

        self.fd = None
        self.open(path)

    def open(self, path):
        """Open serial port at specified device path with baudrate 115200, and
        8N1."""

        # Open the serial port
        try:
            self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        except OSError as e:
            raise Exception("Opening serial port: {}".format(str(e)))

        # Configure serial port to raw, 115200 8N1
        tty_attr = termios.tcgetattr(self.fd)
        tty_attr[0] = termios.IGNBRK    # iflag
        tty_attr[1] = 0                 # oflag
        tty_attr[2] = termios.CREAD | termios.CLOCAL | termios.B115200 | termios.CS8 # cflag
        tty_attr[3] = 0                 # lflag
        tty_attr[4] = termios.B115200   # ispeed
        tty_attr[5] = termios.B115200   # ospeed

        try:
            termios.tcsetattr(self.fd, termios.TCSANOW, tty_attr)
        except OSError as e:
            raise Exception("Configuring serial port: {}".format(str(e)))

    def read(self, n, timeout=None):
        """Read up to n bytes from the serial port, or until specified timeout
        in seconds.

        Args:
            n (int): number of bytes to read
            timeout (None or int): read timeout

        Returns:
            bytes: data read

        """

        buf = b""

        tic = time.time()
        while len(buf) < n:
            try:
                buf += os.read(self.fd, n - len(buf))
            except OSError as e:
                if e.errno != errno.EAGAIN:
                    raise e
                time.sleep(0.01)

            if timeout and (time.time() - tic) > timeout:
                break

        return buf

    def readline(self):
        """Read a line from the serial port up to \r or \n.

        Returns:
            bytes: line read, without the newline delimiter

        """

        buf = b""

        while True:
            try:
                c = os.read(self.fd, 1)
            except OSError as e:
                if e.errno != errno.EAGAIN:
                    raise e
                time.sleep(0.01)
                continue

            if c in [b"\r", b"\n"]:
                if len(buf):
                    break
                else:
                    continue

            buf += c

        return buf

    def write(self, data):
        """Write data to serial port.

        Args:
            data (bytes): data to write

        """

        os.write(self.fd, data)

    def flush_input(self):
        """Flush input buffer on serial port."""

        termios.tcflush(self.fd, termios.TCIFLUSH)

    def flush_output(self):
        """Flush output buffer on serial port."""

        termios.tcdrain(self.fd)

    def writeline(self, line, wait_time=0.5):
        """Write a line to the serial port. This mimics a user typing in a line and
        pressing enter.

        Args:
            line (str): Line to write
            wait_time (float): Time to wait in seconds after writing the line

        """

        if isinstance(line, str):
            self.write(line.encode() + b"\r\n")
        else:
            self.write(line + b"\r\n")

        self.flush_output()
        time.sleep(wait_time)

    def close(self):
        """Close the serial port."""

        os.close(self.fd)
        self.fd = None


# Cmdmule script and command wrapper

CMDMULE_SCRIPT = b"""
import sys
import json
import subprocess

print("cmdmule started")
try:
    while True:
        s = sys.stdin.readline().strip()
        if len(s) == 0:
            continue

        cmd = json.loads(s)

        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        result = {'returncode': p.returncode, 'stdout': p.stdout.read().decode(), 'stderr': p.stderr.read().decode()}

        sys.stdout.write(json.dumps(result) + '\\n')
except KeyboardInterrupt:
    sys.exit(0)
"""
"""The cmdmule script is loaded onto the target over the serial port and run in
task_cmdmule(). This script listens for commands over the serial port, executes
them, and responds with a JSON object containing the resulting return code,
stdout, and stderr. This simplifies remote command execution over the serial
port, as it propagates the return code of commands, properly escapes newlines
in stderr and stdout, and removes the bash prompt from the serial output."""


def cmdmule_command(ser, cmd):
    """Execute a command over the serial port in a running cmdmule.

    Args:
        ser (Serial): Serial port object
        cmd (str): Command to execute

    Returns:
        dict: Dictionary containing returncode, stdout, stderr keys.

    """

    # Write command
    ser.flush_input()
    ser.write(json.dumps(cmd).encode() + b"\n")

    # Read command sent
    ser.readline()
    # Read result
    result = ser.readline()

    # Decode result
    return json.loads(result.strip().decode())


# Setup tasks

def task_install_serial_driver():
    """This task install the PL2303 driver on Mac OS X, if it isn't
    installed."""

    PL2303_KEXT = "/System/Library/Extensions/ProlificUsbSerial.kext"
    PL2303_DRIVER_ZIP_URL = "http://prolificusa.com/files/md_PL2303_MacOSX_10.6-10.10_v1.5.1.zip"
    PL2303_DRIVER_PKG = "PL2303_MacOSX_v1.5.1.pkg"

    # Install the PL2303 on Mac OS X, if it isn't installed
    if sys.platform.startswith("darwin") and not os.path.exists(PL2303_KEXT):
        print_step("Installing PL2303 USB serial port driver...")

        # Fetch the driver
        print_step("\nFetching driver from {} ...".format(PL2303_DRIVER_ZIP_URL))
        try:
            zippath, _ = urlretrieve(PL2303_DRIVER_ZIP_URL)
        except Exception as e:
            raise Exception("Fetching PL2303 driver: {}".format(str(e)))

        # Unzip the driver to a temporary directory
        print_step("\nExtracting driver...")
        tmpdir = tempfile.mkdtemp()
        with zipfile.ZipFile(zippath) as f:
            f.extract(PL2303_DRIVER_PKG, tmpdir)

        # Install the driver
        print_step("\nInstalling driver... Please enter system password if prompted.")
        pkgpath = tmpdir + "/" + PL2303_DRIVER_PKG
        print("sudo installer -pkg {} -target /".format(pkgpath))
        try:
            subprocess.check_output("sudo installer -pkg {} -target /".format(pkgpath), shell=True)
        except subprocess.CalledProcessError as e:
            raise Exception("Installing PL2303 driver: {}".format(str(e)))

        # Load the kernel extension
        print_step("\nLoading driver... Please enter system password if prompted.")
        print("sudo kextload {}".format(PL2303_KEXT))
        try:
            subprocess.check_output("sudo kextload {}".format(PL2303_KEXT), shell=True)
        except subprocess.CalledProcessError as e:
            raise Exception("Loading PL2303 driver: {}".format(str(e)))

        print_step("\nDriver successfully installed and loaded!\n")


def task_find_serial_port():
    """This task finds and open the USB serial port.

    Returns:
        Serial: Serial port object

    """

    while True:
        if sys.platform.startswith("darwin"):
            if os.path.exists("/dev/tty.usbserial"):
                port = "/dev/tty.usbserial"
                break
        else:
            # Get a list of /dev/ttyUSB* candidates
            tty_ports = glob.glob("/dev/ttyUSB*")

            def map_vid_pid(tty_port):
                tty_name = os.path.basename(tty_port)

                try:
                    # Read VID
                    with open("/sys/bus/usb-serial/devices/{}/../../idVendor".format(tty_name)) as f:
                        vid = int(f.read().strip(), 16)
                    # Read PID
                    with open("/sys/bus/usb-serial/devices/{}/../../idProduct".format(tty_name)) as f:
                        pid = int(f.read().strip(), 16)
                except Exception:
                    return (None, None)

                return (vid, pid)

            # Map (vid, pid) to each /dev/ttyUSBX
            tty_ports = {tty_port: map_vid_pid(tty_port) for tty_port in tty_ports}
            # Filter by Prolific (vid, pid)
            tty_ports = [tty_port for tty_port in tty_ports if tty_ports[tty_port] in [(0x067b, 0x2303)]]

            if len(tty_ports) > 0:
                # Pick first port
                port = tty_ports[0]
                break

        print_warning("Please connect the USB serial port cable to the Bitcoin Computer.")
        print_warning("Press enter to continue.")
        raw_input()

    return Serial(port)


def task_prompt(ser):
    """This task restores the target to the login prompt.

    Args:
        ser (Serial): Serial port object

    """

    while True:
        # Get an idea of where we're at
        ser.writeline("\x03\x03\x03\n\n")
        buf = ser.read(2048, timeout=0.25).decode()

        if "Raspbian GNU/Linux 8" in buf:
            # At the login prompt
            logger.debug("[login_prompt] at login prompt")
            break
        elif "twenty@" in buf and "$" in buf:
            # At the command line
            logger.debug("[login_prompt] at command line")
            ser.writeline("exit")

    ser.flush_input()


def task_login(ser):
    """This task logins in under user twenty from the login prompt.

    Args:
        ser (Serial): Serial port object

    """

    # Login
    print_step("\nLogging into the Bitcoin Computer...")
    ser.writeline("twenty")
    ser.writeline("one")

    # Look for command line
    buf = ser.read(2048, timeout=0.25).decode()
    if not ("twenty@" in buf and "$" in buf):
        raise Exception("Failed to login.")

    logger.debug("[login] logged in")

    ser.flush_input()


def task_cmdmule(ser):
    """This task ships over and starts the cmdmule script on the target.

    Args:
        ser (Serial): Serial port object

    """

    # Base64 encode cmdmule script
    cmdmule_script = base64.b64encode(CMDMULE_SCRIPT) + b"\n" + b"\x04"

    # Write it to /tmp/cmdule.py
    logger.debug("[cmdmule] sending cmdmule script")
    ser.writeline("base64 -d > /tmp/cmdmule.py")
    ser.writeline(cmdmule_script)

    # Start running it
    logger.debug("[cmdmule] starting cmdmule script")
    ser.writeline("python3 /tmp/cmdmule.py")

    # Check that it started
    buf = ser.read(2048, timeout=0.25).decode()
    if "cmdmule started" not in buf:
        raise Exception("Failed to start cmdmule script.")

    logger.debug("[cmdmule] cmdmule started")

    ser.flush_input()


def task_connect_wifi(ser):
    """This task configures WiFi with WPA2-PSK and brings up the wlan0
    interface, or skips the process entirely if the user decides to skip it.

    Args:
        ser (Serial): Serial port object

    """

    print_step("\nSetting up WiFi...\n")

    while True:
        # Look up wlan interface
        result = cmdmule_command(ser, "ifconfig -a | grep -o \"wlan[0-9]\"")
        if result['returncode'] != 0:
            print_warning("WiFi dongle not found. Please connect the WiFi dongle.")
            print_warning("Press enter or \"skip\" to use Ethernet.")
            if raw_input() == "skip":
                break
            continue
        wlan_interface = result['stdout'].strip()

        logger.debug("[connect_wifi] wlan interface is %s", wlan_interface)

        # Get WiFI access point information from user
        print_step("Please enter WiFi access point information.")
        print_step("")
        ssid = raw_input("    WiFi SSID: ")
        password = raw_input("    WiFi WPA2 Passphrase: ")

        # Create /etc/wpa_supplicant/wpa_supplicant.conf
        wpa_supplicant_conf = "network={{\n    ssid=\"{}\"\n    psk=\"{}\"\n}}\n".format(ssid, password)
        wpa_supplicant_conf = base64.b64encode(wpa_supplicant_conf.encode()).decode()
        cmdmule_command(ser, "echo {} | base64 -d | sudo tee /etc/wpa_supplicant/wpa_supplicant.conf".format(wpa_supplicant_conf))

        # Decrease dhclient.conf timeout from 60 seconds to 15 seconds
        cmdmule_command(ser, "sudo sed -i 's/#timeout 60;/timeout 15;/' /etc/dhcp/dhclient.conf")

        # Bring up WiFi interface
        print_step("\nConnecting WiFi...")
        cmdmule_command(ser, "sudo ifdown {}".format(wlan_interface))
        cmdmule_command(ser, "sudo ifup {}".format(wlan_interface))

        # Check carrier status
        print_step("\nChecking WiFi connectivity...")
        result = cmdmule_command(ser, "cat /sys/class/net/{}/carrier".format(wlan_interface))
        if result['returncode'] != 0 or int(result['stdout'].strip()) != 1:
            print_error("Error: Failed to associate with WiFi access point.")
            continue
        logger.debug("[connect_wifi] carrier is up")

        # Check IP status
        result = cmdmule_command(ser, "ip addr show {} | grep \"inet \"".format(wlan_interface))
        if result['returncode'] != 0:
            print_error("Error: Failed to get an IP address.")
            continue
        logger.debug("[connect_wifi] interface has ip address")

        break


def task_lookup_connection_info(ser):
    """This task looks up the hostname and IP addresses of the target, and
    tests connectivity to the target by SSHing to the target.

    Args:
        ser (Serial): Serial port object

    Returns:
        tuple: Tuple of hostname and a list of IP addresses

    """

    print_step("\nLooking up connection information...")

    # Look up hostname
    result = cmdmule_command(ser, "hostname")
    if result['returncode'] != 0:
        raise Exception("Looking up hostname.")

    hostname = result['stdout'].strip()
    logger.debug("[lookup_connection_info] hostname is %s", hostname)

    addresses = []

    # Look up IPv4 addresses
    ipv4_addresses = cmdmule_command(ser, "ip addr show | grep -o \"inet [0-9\.]*\" | cut -d' ' -f2")
    if ipv4_addresses['returncode'] == 0:
        # Split and filter out 127.0.0.1
        ipv4_addresses = ipv4_addresses['stdout'].strip().split('\n')
        ipv4_addresses = list(filter(lambda ip: ip != "127.0.0.1", ipv4_addresses))
        logger.debug("[lookup_connection_info] ipv4 addresses are %s", str(ipv4_addresses))
        addresses += ipv4_addresses

    # Look up IPv6 addresses
    ipv6_addresses = cmdmule_command(ser, "ip addr show | grep -o \"inet6 [0-9a-f:]*\" | cut -d' ' -f2")
    if ipv6_addresses['returncode'] == 0:
        # Split and filter out ::1
        ipv6_addresses = ipv6_addresses['stdout'].strip().split('\n')
        ipv6_addresses = list(filter(lambda ip: ip != "::1", ipv6_addresses))
        logger.debug("[lookup_connection_info] ipv6 addresses are %s", str(ipv6_addresses))
        addresses += ipv6_addresses

    if len(addresses) == 0:
        raise Exception("No IP addresses found.")

    print_step("\nChecking connectivity to the Bitcoin Computer...")
    print_step("Please enter password \"one\" when prompted.\n")

    # Try SSHing in
    result = subprocess.check_output(["ssh", "twenty@" + addresses[0], "-q", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no", "echo", "test"])
    if result.strip().decode() != "test":
        raise Exception("SSH connection failed.")

    return (hostname, ipv4_addresses, ipv6_addresses)


def task_21_update(ip_address):
    """This task runs 21 update on the target.

    Args:
        ip_address (str): IP address

    """

    print_step("\nRunning 21 update...")
    print_step("Please enter password \"one\" when prompted.\n")

    # Run 21 update
    try:
        subprocess.check_call(["ssh", "twenty@" + ip_address, "-q", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no", "21", "update"])
    except subprocess.CalledProcessError:
        raise Exception("Running 21 update.")


def task_cleanup(ser):
    """This task exits cmdmule and the shell session on the target,
    restoring it to the login prompt.

    Args:
        ser (Serial): Serial port object

    """

    # Exit cmdmule program
    ser.writeline("\x03\x03\x03")

    # Exit command line
    ser.writeline("exit")


# Top-level setup routine

def main():
    """Setup a Bitcoin Computer over the serial port."""

    task_install_serial_driver()

    ser = task_find_serial_port()

    try:
        task_prompt(ser)
        task_login(ser)
        task_cmdmule(ser)
        task_connect_wifi(ser)
        (hostname, ipv4_addresses, ipv6_addresses) = task_lookup_connection_info(ser)
        task_21_update(ipv4_addresses[0])
    except Exception as e:
        print_error("Error: " + str(e))
        print_error("Please contact support@21.co")
        sys.exit(1)
    except KeyboardInterrupt:
        print_error("\nSetup interrupted!")
        sys.exit(1)
    finally:
        task_cleanup(ser)
        ser.close()

    print_step("\nSetup complete!")

    print_step("\nBitcoin Computer configured and online!")
    print_step("")
    print_step("Connection Information\n")
    print_step("    Hostname      {}".format(hostname))
    print_step("    IP Addresses  {}".format(", ".join(ipv4_addresses + ipv6_addresses)))
    print_step("")
    print_step("You may connect to the Bitcoin Computer with one of these commands:")
    print_step("")
    print_step("    ssh twenty@{}.local".format(hostname))
    for address in ipv4_addresses:
        print_step("    ssh twenty@{}".format(address))
    print_step("")
    print_step("and with password \"one\".")

if __name__ == "__main__":
    main()
