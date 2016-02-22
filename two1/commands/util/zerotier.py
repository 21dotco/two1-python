#!/usr/bin/env python3
"""
Simple wrapper for zerotier-cli
"""
import json
import subprocess
import shutil
import platform


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
        CalledProcessError: If the cli call failed.
    """
    return subprocess.check_output(("sudo", "zerotier-cli") + args)


def cli_json(*cmd):
    """ Runs zerotier-cli as superuser and returns the results in json format

    Args:
        *args: List of string arguments to zerotier-cli

    Returns:
        dict: A dict with the json parsed results of the command.

    Raises:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
    """
    result = cli(*(cmd + ("-j",)))
    text = result.decode('utf-8')
    return json.loads(text)


def is_valid(id_str, id_len=16):
    """ Simple check for a valid zerotier network_id

    Args:
        id_str (str): Zerotier network id or address

    Returns:
        bool: True if the id_str is valid, False otherwise

    Raises:
        ValueError: if the length of the id string is not equal to the expected id length
    """
    if len(id_str) != id_len:
        raise ValueError("Error: length of the id_str is not equal to the expected length")

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
    """
    address = info()['address']
    assert is_valid(address, id_len=10)
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


def device_ip(network_id=None):
    """ Returns the IP address and network mask for the provided Zerotier network.

        If no network is provided, this will return the IP if the device is connected to
        only one Zerotier network.

    Args:
        network_id (str): Zerotier network id for which the IP address is desired.

    Returns:
        list (IP, mask): Returns the IP and the mask. e.g. [u'172.23.15.14', u'16']

    Raises:
        NameError: if the network_id given is not a valid network id or an IP address
            has not been assigned yet.
    """
    networks = list_networks()
    ret = None
    if network_id:
        ret = next((n for n in networks if n['nwid'] == network_id), None)
        if ret:
            ret = ret["assignedAddresses"][0]
    else:
        if len(networks) == 1:
            if len(networks[0]["assignedAddresses"]) > 0:
                ret = networks[0]["assignedAddresses"][0]
    if not ret:
        raise NameError("Error in looking up Zerotier IP for %s" % network_id)
    else:
        return ret.split("/")


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
        ValueError: If the json string could not be successfully parsed into a dict.
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
        ValueError: If the json string could not be successfully parsed into a dict.
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
    if platform.system() in "Linux":
        if shutil.which("systemctl"):
            cmd = ('sudo', 'systemctl', 'start', 'zerotier-one.service')
        elif shutil.which("service"):
            cmd = ('sudo', 'service', 'zerotier-one', 'start')
        else:
            raise EnvironmentError("Do not know how to start zerotier deamon on your system")
    elif platform.system() in "Darwin":
        # ZT post install for Macs already load the daemon
        return

    return subprocess.check_output(cmd)

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


def get_all_addresses():
    """ Gets all addresses in a dictionary format with the network names as keys

    Returns:
        dict: a dictionary of IP addresses with network names as keys, or an empty dict
            if no networks are found.
    """
    result = {}
    try:
        networks = list_networks()
    except (ValueError, CalledProcessError):
        return result

    for network in networks():
        address_and_mask = network["assignedAddresses"][0]
        address = address_and_mask.split("/")[0]
        result[network["name"]] = address

    return result
