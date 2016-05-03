# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import subprocess

import click
import psutil
import yaml
from flask import Flask
from flask import request, jsonify
from two1.bitserv.flask import Payment
from two1.wallet.two1_wallet import Wallet
from werkzeug.exceptions import *

from ping21 import get_server_info, ping

from two1.sell.util.decorators import track_requests
from two1.sell.util.decorators import DEFAULT_PRICE

app = Flask(__name__)

# setup wallet
wallet = Wallet()
payment = Payment(app, wallet, db_dir="/usr/src/db")

# hide logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


@app.route('/manifest')
def manifest():
    """Provide the app manifest to the 21 crawler.
    """
    with open(os.path.join("/usr/src/db", "ping_manifest.yaml"), 'r') as f:
        manifest = yaml.load(f)
    return jsonify(**manifest)


@app.route('/info')
def info():
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
    try:
        uri = request.args['uri'].replace('https://', '').replace('http://', '')
    except KeyError:
        raise BadRequest("Host query parameter is missing from your request.")

    return ping([uri],
                app.config['PING21_ALLOW_PRIVATE'],
                app.config['PING21_DEFAULT_ECHO'],
                app.config['PING21_MAX_ECHO'])


@app.route('/cli', methods=['POST'])
@payment.required(os.environ.get("PRICE_PING_CLI", DEFAULT_PRICE),
                  server_url=os.environ.get("PAYMENT_SERVER_IP", None))
@track_requests
def cli_ping():
    return ping(request.get_json()['args'],
                app.config['PING21_ALLOW_PRIVATE'],
                app.config['PING21_DEFAULT_ECHO'],
                app.config['PING21_MAX_ECHO'])


@click.command()
@click.option("-d", "--daemon", default=False, is_flag=True,
              help="Run in daemon mode.")
@click.option("-p", "--private", default=False, is_flag=True,
              help="Allow ping21 to ping private ips.")
@click.argument('defaultecho', type=click.IntRange(min=1), default=3)
@click.argument('maxecho', type=click.IntRange(min=1), default=5)
def run(daemon, private, maxecho, defaultecho):
    if defaultecho > maxecho:
        raise ValueError("default echo count cannot be more than the maximum echo count")
    app.config['PING21_MAX_ECHO'] = maxecho
    app.config['PING21_DEFAULT_ECHO'] = defaultecho
    app.config['PING21_ALLOW_PRIVATE'] = private
    if daemon:
        pid_file = './ping21.pid'
        if os.path.isfile(pid_file):
            pid = int(open(pid_file).read())
            os.remove(pid_file)
            try:
                p = psutil.Process(pid)
                p.terminate()
            except:
                pass
        try:
            p = subprocess.Popen(['python3', 'ping21.py', maxecho, defaultecho])
            open(pid_file, 'w').write(str(p.pid))
        except subprocess.CalledProcessError:
            raise ValueError("error starting ping21.py daemon")
    else:
        print("Server running...")
        app.run(host='0.0.0.0', port=int(os.environ["PORT"]))


if __name__ == '__main__':
    run()
