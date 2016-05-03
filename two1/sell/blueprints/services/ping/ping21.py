#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import ipaddress
import json
import re
import shutil
import subprocess
import sys

import requests
from werkzeug.exceptions import *

__all__ = ["get_server_info", "ping"]


def check_compatibility():
    # check for Windows
    if hasattr(sys, 'getwindowsversion'):
        raise InternalServerError("Windows is currently not supported.")

    # check for command presence
    if not shutil.which('ping'):
        raise InternalServerError("error: Missing `ping` binary.")


def get_server_info():
    """Gets network metadata for the machine calling the function.

    see http://ipinfo.io for more info.
    Returns:
        dict: A dictionary with keys ip, hostname, city, region, country, loc, org, postal

    """
    return requests.get('http://ipinfo.io').json()


def is_valid_hostname(hostname):
    # http://stackoverflow.com/a/2532344
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]  # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def validate_cli_args(cli_args, allow_private, default_echo, max_echo):
    parser = argparse.ArgumentParser()
    parser.add_argument('hostname', nargs='?')
    parser.add_argument('-c', type=int)
    # parser.add_argument('-W', type=int)

    knownargs = parser.parse_known_args(cli_args)[0]

    # checking hostname...
    hostname = knownargs.hostname
    if not hostname:
        raise BadRequest("Host query parameter is missing from your request.")
    try:
        if ipaddress.ip_address(hostname).is_private and not allow_private:
            raise Forbidden("Private IP scanning is forbidden")
    except ValueError:  # raised when hostname isn't an ip address
        if not is_valid_hostname(hostname):
            raise Forbidden("Invalid hostname.")

    # checking and defaulting `-c`
    c = knownargs.c
    if not c:
        cli_args = ['-c', str(default_echo)] + cli_args
    elif c > max_echo:
        raise Forbidden("The `-c` argument is larger than that allowed by the server")

    # # standardizing `-W`
    # W = knownargs.W
    # if W and platform.system() == 'Darwin':
    #     cli_args += ['-W', W * 1000]

    return cli_args


def ping(cli_args, allow_private, default_echo, max_echo):
    try:
        data = run_ping_command(validate_cli_args(cli_args, allow_private, default_echo, max_echo))
        response = json.dumps(data, indent=4, sort_keys=True)
        return response
    except ValueError as e:
        raise BadRequest(e.args[0])


def run_ping_command(args):
    check_compatibility()

    try:
        out = subprocess.check_output(['ping'] + args).decode('unicode_escape')
    except subprocess.CalledProcessError:
        raise InternalServerError("An error occured while performing ping on host={}".format(args[-1]))

    # Format into dictionary and return
    return {
        'ping': [line for line in out.split('\n') if line != ''],
        'server': get_server_info()
    }


if __name__ == '__main__':
    url = sys.argv[1]
    data = run_ping_command([url])
    formatted_data = json.dumps(data, indent=4, sort_keys=True)
    print(formatted_data)
