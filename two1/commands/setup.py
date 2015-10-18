import click
import sys
import os.path
import json
import time
import logging
import base64
import subprocess

import serial
import serial.tools.list_ports

from two1.commands.config import pass_config


logger = logging.getLogger(__name__)


# Print helper functions

def print_step(s):
    print("\x1b[1;35m" + s + "\x1b[0m")

def print_warning(s):
    print("\x1b[1;33m" + s + "\x1b[0m")

def print_error(s):
    print("\x1b[1;31m" + s + "\x1b[0m")


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
        ser (pyserial.Serial): Serial port object
        cmd (str): Command to execute

    Returns:
        dict: Dictionary containing returncode, stdout, stderr keys.

    """

    # Write command
    ser.flushInput()
    ser.write(json.dumps(cmd).encode() + b"\n")

    # Read command sent
    _ = ser.readline()
    # Read result
    result = ser.readline()

    # Decode result
    return json.loads(result.strip().decode())


# Serial helper functions

def serial_open():
    """Find and open the USB serial port.

    Returns:
        pyserial.Serial: Serial object

    """

    while True:
        # serial.tools.list_ports does not behave properly on Mac OS X, so we
        # check explicitly for /dev/tty.usbserial when on Mac OS X.
        if sys.platform.startswith("darwin"):
            if os.path.exists("/dev/tty.usbserial"):
                port = "/dev/tty.usbserial"
                break
        else:
            ports = list(serial.tools.list_ports.grep('PL2303'))
            if len(ports) > 0:
                port = ports[0][0]
                break

        print_warning("Please connect the USB serial port cable to the Bitcoin Computer.")
        print_warning("Press enter to continue.")
        input()

    # Open the serial port
    ser = serial.Serial(port, 115200, timeout=0.5)
    ser.flushInput()
    return ser

def serial_writeline(ser, line, wait_time=0.5):
    """Write a line to the serial port. This mimics a user typing in a line and
    pressing enter.

    Args:
        ser (pyserial.Serial): Serial object
        line (str): Line to write
        wait_time (float): Time to wait in seconds after writing the line

    """

    if isinstance(line, str):
        ser.write(line.encode() + b"\r\n")
    else:
        ser.write(line + b"\r\n")
    ser.flush()
    time.sleep(wait_time)

def serial_close(ser):
    """Close the serial port.

    Args:
        ser (pyserial.Serial): Serial object

    """

    ser.close()


# Setup tasks

def task_prompt(ser):
    """This task restores the target to the login prompt.

    Args:
        ser (pyserial.Serial): Serial object

    """

    while True:
        # Get an idea of where we're at
        serial_writeline(ser, "\x03\x03\x03\n\n")
        buf = ser.read(2048).decode()

        if "Raspbian GNU/Linux 8" in buf:
            # At the login prompt
            logger.debug("[login_prompt] at login prompt")
            break
        elif "twenty@" in buf and "$" in buf:
            # At the command line
            logger.debug("[login_prompt] at command line")
            serial_writeline(ser, "exit")

    ser.flushInput()

def task_login(ser):
    """This task logins in under user twenty from the login prompt.

    Args:
        ser (pyserial.Serial): Serial object

    """

    # Login
    print_step("\nLogging into the Bitcoin Computer...")
    serial_writeline(ser, "twenty")
    serial_writeline(ser, "one")

    # Look for command line
    buf = ser.read(2048).decode()
    if not ("twenty@" in buf and "$" in buf):
        raise Exception("Failed to login.")

    logger.debug("[login] logged in")

    ser.flushInput()

def task_cmdmule(ser):
    """This task ships over and starts the cmdmule script on the target.

    Args:
        ser (pyserial.Serial): Serial object

    """

    # Base64 encode cmdmule script
    cmdmule_script = base64.b64encode(CMDMULE_SCRIPT) + b"\n" + b"\x04"

    # Write it to /tmp/cmdule.py
    logger.debug("[cmdmule] sending cmdmule script")
    serial_writeline(ser, "base64 -d > /tmp/cmdmule.py")
    serial_writeline(ser, cmdmule_script)

    # Start running it
    logger.debug("[cmdmule] starting cmdmule script")
    serial_writeline(ser, "python3 /tmp/cmdmule.py")

    # Check that it started
    buf = ser.read(2048).decode()
    if "cmdmule started" not in buf:
        raise Exception("Failed to start cmdmule script.")

    logger.debug("[cmdmule] cmdmule started")

    # Disable timeout on serial port now, as we'll be reading until newline
    # with cmdmule
    ser.timeout = None

    ser.flushInput()

def task_connect_wifi(ser):
    """This task configures WiFi with WPA2-PSK and brings up the wlan0
    interface, or skips the process entirely if the user decides to skip it.

    Args:
        ser (pyserial.Serial): Serial object

    """

    print_step("\nSetting up WiFi...\n")

    while True:
        # Look up wlan interface
        result = cmdmule_command(ser, "ifconfig -a | grep -o \"wlan[0-9]\"")
        if result['returncode'] != 0:
            print_warning("WiFi dongle not found. Please connect the WiFi dongle.")
            print_warning("Press enter or \"skip\" to use Ethernet.")
            if input() == "skip":
                break
            continue
        wlan_interface = result['stdout'].strip()

        logger.debug("[connect_wifi] wlan interface is %s", wlan_interface)

        # Get WiFI access point information from user
        print_step("Please enter WiFi access point information.")
        print_step("")
        ssid = input("    WiFi SSID: ")
        password = input("    WiFi WPA2 Passphrase: ")

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
        ser (pyserial.Serial): Serial object

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

    print_step("\nConnection Information\n")
    print_step("    Hostname      {}".format(hostname))
    print_step("    IP Addresses  {}".format(", ".join(addresses)))

    print_step("\nChecking connectivity to the Bitcoin Computer...")
    print_step("Please enter password \"one\" when prompted.\n")

    # Try SSHing in
    result = subprocess.check_output(["ssh", "twenty@" + addresses[0], "-q", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no", "echo", "test"])
    if result.strip().decode() != "test":
        raise Exception("SSH connection failed.")

    print_step("\nBitcoin Computer configured and online!")
    print_step("")
    print_step("You may connect to the Bitcoin Computer with one of these commands:")
    print_step("")
    print_step("    ssh twenty@{}.local".format(hostname))
    for address in ipv4_addresses:
        print_step("    ssh twenty@{}".format(address))
    print_step("")
    print_step("and with password \"one\".")

def task_21_update(ser):
    """This task runs 21 update on the target.

    Args:
        ser (pyserial.Serial): Serial object

    """

    print_step("\nRunning 21 update...\n")

    # Run 21 update
    result = cmdmule_command(ser, "21 update 2>&1")
    if result['returncode']:
        raise Exception("Running 21 update: " + result['stdout'])

def task_cleanup(ser):
    """This task exits cmdmule and the shell session on the target,
    restoring it to the login prompt.

    Args:
        ser (pyserial.Serial): Serial object

    """

    # Exit cmdmule program
    serial_writeline(ser, "\x03\x03\x03")

    # Exit command line
    serial_writeline(ser, "exit")

# Top-level setup routine

@click.command()
@pass_config
def setup(config):
    """Setup a Bitcoin Computer over the serial port."""

    ser = serial_open()

    try:
        task_prompt(ser)
        task_login(ser)
        task_cmdmule(ser)
        task_connect_wifi(ser)
        task_lookup_connection_info(ser)
        task_21_update(ser)
    except Exception as e:
        print_error("Error: " + str(e))
        print_error("Please contact support@21.co")
        sys.exit(1)
    finally:
        task_cleanup(ser)
        serial_close(ser)

    print_step("\nSetup complete!")

