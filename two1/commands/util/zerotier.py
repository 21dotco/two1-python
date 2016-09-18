#!/usr/bin/env python3
"""
Simple wrapper for zerotier-cli
"""
import json
import logging
import platform
import shutil
import subprocess
import sys

from two1.commands.util import uxstring

logger = logging.getLogger(__name__)


def is_installed():
    """ Checks the system whether zerotier-one is installed

    Returns:
        bool: True if zerotier-one is installed, False otherwise
    """
    return shutil.which('zerotier-cli') is not None


def cli(*args):
    """ Runs zerotier-cli as superuser and returns the results

    Args:
        *args: List of string arguments to zerotier-cli

    Returns:
        str: A string with the entire output of the shell command.

    Raises:
        ValueError: if any of the args are not strings.
        CalledProcessError: If the cli call failed.
    """
    if not is_installed():
        logger.info(uxstring.UxString.install_zerotier)
        sys.exit(1)

    if not all([isinstance(arg, str) for arg in args]):
        raise ValueError("Error: args can only be strings")

    return subprocess.check_output(("sudo", "zerotier-cli") + args)


def cli_json(*args):
    """ Runs zerotier-cli as superuser and returns the results in json format

    Args:
        *args: List of string arguments to zerotier-cli

    Returns:
        dict: A dict with the json parsed results of the command.

    Raises:
        CalledProcessError: If the cli call failed.
        ValueError: if any of the args are not strings.
        json.decoder.JSONDecodeError: If the json string could not be successfully
            parsed into a dict.
    """
    result = cli(*(args + ("-j",)))
    text = result.decode('utf-8')
    return json.loads(text)


def is_valid(id_str, id_len=16):
    """ Simple check for a valid zerotier network_id

    Args:
        id_str (str): Zerotier network id or address

    Returns:
        bool: True if the id_str is valid, False otherwise
    """
    if len(id_str) != id_len:
        return False

    try:
        # expected to be valid hexadecmal string
        int(id_str, 16)
    except ValueError:
        return False

    return True


def info():
    """ zerotier-cli info command

    Returns:
        dict: A dict with the json parsed results of the command.

    Raises:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
    """
    return dict(cli_json('info'))


def device_address():
    """ Returns Zerotier device id

    Returns:
        str: Zerotier device id

    Raises:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
        ValueError: If the address from info is not valid
    """
    address = info()['address']
    if not is_valid(address, id_len=10):
        raise ValueError("Error: address from info() is not valid")

    return address


def list_networks():
    """ zerotier-cli listnetworks command

    Returns:
        list: A list of networks (dict) that the device is connected to.

    Raises:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
    """
    return cli_json('listnetworks')


def list_peers():
    """ zerotier-cli listpeers command

    Returns:
        list: A list of peers (dict) that the device can see.

    Raises:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
    """
    return cli_json('listpeers')


def join_network(network_id):
    """ Join the provided zerotier network

    Args:
        network_id (str): Zerotier network id to connect to.

    Returns:
        str: Result from the zerotier-cli join call.

    Raises:
        CalledProcessError: If the cli call failed.
        ValueError: If the given network_id is invalid.
    """
    if not is_valid(network_id, id_len=16):
        raise ValueError("Error network_id ({}) is not valid")

    return cli('join', network_id)


def leave_network(network_id):
    """ Leave the provided zerotier network

    Args:
        network_id (str): Network id fo the Zerotier network to leave.

    Returns:
        str: Result from the zerotier-cli leave call.

    Raises:
        CalledProcessError: If the cli call failed.
        ValueError: If the given network_id is invalid.
    """
    if not is_valid(network_id, id_len=16):
        raise ValueError("Error network_id ({}) is not valid")

    return cli('leave', network_id)


def start_daemon():
    """ Starts the zerotier daemon if it is installed on your system

    Returns:
       str: output of the subprocess call to check_output

    Raises:
        EnvironmentError: if you your ststem is not yet supported.
        CalledProcessError: if the command to start the daemon failed.
    """
    if not is_installed():
        logger.info(uxstring.UxString.install_zerotier)
        sys.exit(1)

    if platform.system() in "Linux":
        if shutil.which("systemctl"):
            cmd = ('sudo', 'systemctl', 'start', 'zerotier-one.service')
        elif shutil.which("service"):
            cmd = ('sudo', 'service', 'zerotier-one', 'start')
        else:
            raise EnvironmentError("Do not know how to start zerotier deamon on your system")
    elif platform.system() in "Darwin":
        # ZT post install for Macs already load the daemon
        return ""
    else:
        raise EnvironmentError("Do not know how to start zerotier deamon on your system")

    return subprocess.call(cmd)  # Command errors if already started


def get_address(network_name):
    """ Gets the IP address of the given network name

    Returns:
        str: an IP address in string format if the network given exists and has
            an assigned address, None otherwise.
    """
    all_addresses = get_all_addresses()
    if network_name in all_addresses:
        return all_addresses[network_name]

    return None


def get_address_by_id(network_id):
    """ Returns the IP address and network mask for the provided Zerotier network.

    Args:
        network_id (str): Zerotier network id for which the IP address is desired.

    Returns:
        list (IP, mask): Returns the IP and the mask. e.g. [u'172.23.15.14', u'16']

    Raises:
        RuntimeError: if the network_id given is not a valid network id or an IP address
            has not been assigned yet.
    """
    networks = list_networks()
    if not networks:
        raise RuntimeError("Error: not connected to any networks")

    for network in networks:
        # found a match
        if network_id and network_id in network['nwid']:
            if len(network["assignedAddresses"]) > 0:
                return network["assignedAddresses"][0].split("/")

    raise RuntimeError("Error in looking up Zerotier IP for %s" % network_id)


def get_all_addresses():
    """ Gets all addresses in a dictionary format with the network names as keys

    Returns:
        dict: a dictionary of IP addresses with network names as keys, or an empty dict
            if no networks are found.
    """
    result = {}
    networks = list_networks()

    for network in networks:
        if len(network["assignedAddresses"]) > 0:
            for ip_address in network["assignedAddresses"]:
                # Remove the address range (e.g. the "/24" in "1.2.3.4/24")
                address = ip_address.split("/")[0]
                # Preferentially return first IPv6 address (indicated
                # by its containing a colon).  If there are no IPv6
                # addresses found, the last IPv4 address will be returned
                if ":" in address:
                    break
        else:
            address = ""

        result[network["name"]] = address

    return result


def get_network_id(network_name):
    return {
        network['name']: network['nwid'] for network in list_networks()}[network_name]


def leave_all():
    if not is_installed():
        return
    logger.info('Leaving all ZeroTier networks.')
    for network, address in get_all_addresses().items():
        logger.info('Leaving %s.' % network)
        nwid = get_network_id(network)
        leave_network(nwid)
