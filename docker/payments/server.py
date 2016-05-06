""" Payment channels processing server.
"""
from flask import Flask

from two1.bitserv.flask import Payment
from two1.wallet.two1_wallet import Wallet

app = Flask(__name__)
wallet = Wallet()
payment = Payment(app, wallet, endpoint='/payment', db_dir="/usr/src/db")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000)
