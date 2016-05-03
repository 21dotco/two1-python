""" Database for 21 sell purchase stats.
"""
import os
import time
import sqlite3
from contextlib import closing


class Two1SellDB():

    DEFAULT_DB_DIR = "~/.two1/services"

    def __init__(self, db_dir=None):
        """ Init 21 sell database.
        """
        db_directory = db_dir or Two1SellDB.DEFAULT_DB_DIR
        self.db_path = os.path.join(os.path.expanduser(db_directory), "stats.db")
        self.schema_path = os.path.join(os.path.expanduser(db_directory), "schema.sql")

        if not os.path.isfile(self.db_path):
            self.init_db()

    def init_db(self):
        """ Create 21 sell database.
        """
        with closing(self.connect_db()) as db:
            with open(self.schema_path, "r") as f:
                db.cursor().executescript(f.read())
            db.commit()

    def connect_db(self):
        """ Connect to db.
        """
        return sqlite3.connect(self.db_path)

    def update(self, service, request_type, price):
        """ Update db with request, buffer, wallet and channel stats.
        """
        if request_type not in ["buffer", "wallet", "channel"]:
            raise ValueError("request_type must be \"buffer\", \"wallet\" or \"channel\"")
        with closing(self.connect_db()) as db:
            c = db.cursor()
            existing_services = [i[0] for i in c.execute("select service from services_stats").fetchall()]
            if service not in existing_services:
                c.execute("insert into services_stats (service, buffer_earnings, wallet_earnings, channel_earnings, request_count, last_buy_time) "
                          "values (:service, :buffer_earnings, :wallet_earnings, :channel_earnings, :request_count, :last_buy_time) ",
                          {"service": service,
                           "buffer_earnings": price if request_type == "buffer" else 0,
                           "wallet_earnings": price if request_type == "wallet" else 0,
                           "channel_earnings": price if request_type == "channel" else 0,
                           "request_count": 1,
                           "last_buy_time": int(time.time())})
            else:
                query_string = ("update services_stats set %s_earnings = %s_earnings + :price, "
                                "request_count = request_count + 1, "
                                "last_buy_time = :last_buy_time "
                                "where service = :service" % (request_type, request_type))
                update_vars = {"price": price,
                               "last_buy_time": int(time.time()),
                               "service": service}
                c.execute(query_string, update_vars)
            db.commit()

    def get_earnings(self, service):
        """ Compute service earnings.
        """
        with closing(self.connect_db()) as db:
            c = db.cursor()
            existing_services = [i[0] for i in c.execute("select service from services_stats").fetchall()]
            if service not in existing_services:
                never_bought = {"service": service,
                                "buffer_earnings": 0,
                                "wallet_earnings": 0,
                                "channel_earnings": 0,
                                "request_count": 0,
                                "last_buy_time": -1}
                return never_bought
            stats = c.execute("select buffer_earnings, wallet_earnings, channel_earnings, "
                              "request_count, last_buy_time from services_stats where service=:service",
                              {"service": service}).fetchone()
            to_return = {"service": service,
                         "buffer_earnings": int(stats[0]),
                         "wallet_earnings": int(stats[1]),
                         "channel_earnings": int(stats[2]),
                         "request_count": int(stats[3]),
                         "last_buy_time": int(stats[4])}
            return to_return
