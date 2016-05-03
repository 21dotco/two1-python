# standard python imports
import os

# 3rd party imports
from flask import request
from functools import wraps

# two1 imports
from two1.sell.util.stats_db import Two1SellDB

DEFAULT_PRICE = 3000


def track_requests(fn):
    """ Decorator to log 21 sell request data.
    """

    @wraps(fn)
    def decorator(*args, **kwargs):
        service_name = os.environ["SERVICE"]

        url = request.url
        host = request.headers["Host"]

        endpoint = url.strip("https://").strip("http://").strip(host).split("?")[0]

        path_us = endpoint.replace("/", "_")

        price_var = "PRICE_%s%s" % (service_name.upper(), path_us.upper())
        price = os.environ.get(price_var, DEFAULT_PRICE)

        if "Bitcoin-Transfer" in request.headers:
            method = "buffer"

        elif "Bitcoin-Transaction" in request.headers:
            method = "wallet"

        elif "Bitcoin-Payment-Channel-Token" in request.headers:
            method = "channel"

        db = Two1SellDB(db_dir="/usr/src/db/")
        db.update(service_name, method, price)

        return fn(*args, **kwargs)

    return decorator
