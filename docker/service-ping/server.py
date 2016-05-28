import ipaddress
import logging
import os
import subprocess

import click
import re
import yaml
from flask import Flask
from flask import request, jsonify
from two1.bitserv.flask import Payment
from two1.wallet.two1_wallet import Wallet
from werkzeug import exceptions
import requests


from two1.sell.util.decorators import track_requests
from two1.sell.util.decorators import DEFAULT_PRICE

app = Flask(__name__)

# setup wallet
wallet = Wallet()
payment = Payment(app, wallet, db_dir="/usr/src/db")

# hide logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


def get_server_info():
    """Gets network metadata for the machine calling the function.

    see http://ipinfo.io for more info.
    Returns:
        dict: A dictionary with keys ip, hostname, city, region, country, loc, org, postal if sucessful,
              or a dictionary with key "error" with the error code as the corresponding value

    """
    r = requests.get('http://ipinfo.io')
    try:
        r.raise_for_status()
    except requests.HTTPError:
        return {"error": r.status_code}
    else:
        try:
            return r.json()
        except Exception as e:
            return {"error": e}


def is_valid_hostname(hostname):
    # http://stackoverflow.com/a/2532344
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]  # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


@app.route('/manifest')
def manifest():
    """Provide the app manifest to the 21 crawler.
    """
    manifest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manifest.yaml')
    with open(manifest_path, 'r') as f:
        manifest_dict = yaml.load(f)
    return jsonify(**manifest_dict)


@app.route('/info')
def info():
    """

    Returns: A JSON response composed of the contents of get_server_info

    """
    return jsonify(**get_server_info())


@app.route('/')
@payment.required(os.environ.get("PRICE_PING_", DEFAULT_PRICE),
                  server_url=os.environ.get("PAYMENT_SERVER_IP", None))
@track_requests
def standard_ping():
    """ Runs ping on the provided url

    Returns: HTTPResponse 200 with a json containing the ping info.
    BadRequest 400 if no uri is specified or the uri is malformed/cannot be pingd.
    """

    # strip protocol part of URL
    try:
        hostname = request.args['uri'].replace('https://', '').replace('http://', '')
    except KeyError:
        raise exceptions.BadRequest("Host query parameter is missing from your request.")

    if not hostname:
        raise exceptions.BadRequest("Host query parameter is missing from your request.")

    # disallow private addresses
    try:
        if ipaddress.ip_address(hostname).is_private:
            raise exceptions.Forbidden("Private IP scanning is forbidden")
    except ValueError:  # raised when hostname isn't an ip address
        if not is_valid_hostname(hostname):
            raise exceptions.Forbidden("Invalid hostname.")

    # call ping
    args = ['ping', '-c', str(app.config['PING21_DEFAULT_ECHO']), hostname]
    try:
        out = subprocess.check_output(args, universal_newlines=True)
    except subprocess.CalledProcessError:
        raise exceptions.InternalServerError("An error occured while performing ping on host={}".format(hostname))

    # format, jsonify, and return
    return jsonify(**{
        'ping': [line for line in out.split('\n') if line != ''],
        'server': get_server_info()
    })


@click.command()
@click.argument('defaultecho', type=click.IntRange(min=1), default=3)
def run(defaultecho):
    app.config['PING21_DEFAULT_ECHO'] = defaultecho
    print("Server running...")
    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    run()
