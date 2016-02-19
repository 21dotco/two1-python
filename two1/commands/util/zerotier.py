#!/usr/bin/env python3
"""
Simple wrapper for zerotier-cli
"""
import json
import subprocess


def cli(*args):
    """ Runs zerotier-cli in sudo mode and returns the results

    Args:
        *args: List of string arguments to zerotier-cli

    Returns:
        str: A string with the entire output of the shell command.

    Exceptions:
        CalledProcessError: If the cli call failed.
    """
    return subprocess.check_output(("sudo", "zerotier-cli") + args)


def cli_json(*cmd):
    """ Runs zerotier-cli in sudo mode and returns the results in json format

    Args:
        *args: List of string arguments to zerotier-cli

    Returns:
        dict: A dict with the json parsed results of the command.

    Exceptions:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
    """
    result = cli(*(cmd + ("-j",)))
    text = result.decode('utf-8')
    return json.loads(text)


def is_valid(idstr, idlen=16):
    """ Simple check for a valid zerotier network_id

    Args:
        idstr (str): Zerotier network id

    Returns:
        bool: True if the network_id is valid, False otherwise
    """
    assert len(idstr) == idlen
    for char in idstr:
        assert char in '0123456789abcdef'
    return True


def info():
    """ zerotier-cli info command

    Returns:
        dict: A dict with the json parsed results of the command.

    Exceptions:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
    """
    return dict(cli_json('info'))


def device_address():
    """ Returns Zerotier device id

    Returns:
        str: Zerotier device id

    Exceptions:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
    """
    address = info()['address']
    assert is_valid(address, idlen=10)
    return address


def list_networks():
    """ zerotier-cli listnetworks command

    Returns:
        list: A list of networks (dict) that the device is connected to.

    Exceptions:
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

    Exceptions:
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

    Exceptions:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
    """
    if is_valid(network_id, idlen=16):
        result = cli('join', network_id)
        return result


def leave_network(network_id):
    """ Leave the provided zerotier network

    Args:
        network_id (str): Network id fo the Zerotier network to leave.

    Returns:
        str: Result from the zerotier-cli leave call.

    Exceptions:
        CalledProcessError: If the cli call failed.
        ValueError: If the json string could not be successfully parsed into a dict.
    """
    if is_valid(network_id, idlen=16):
        result = cli('leave', network_id)
        return result


def get_address_for_network(network_name):
    all_addresses = get_all_addresses()
    return all_addresses[network_name]


def get_all_addresses():
    result = {}
    for network in list_networks():
        address_and_mask = network["assignedAddresses"][0]
        address = address_and_mask.split("/")[0]
        result[network["name"]] = address
    return result
