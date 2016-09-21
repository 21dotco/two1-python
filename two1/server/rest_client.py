# standard python imports
import urllib
import base64
import json
import datetime

# 3rd party imports
import requests

# two1 imports
import two1
from two1.commands.util import exceptions
from two1.commands.util import uxstring
from two1.server import machine_auth_wallet


class TwentyOneRestClient(object):
    def __init__(self, server_url=None, machine_auth=None, username=None,
                 version="0", wallet=None):
        if machine_auth is not None and wallet is not None:
            raise ValueError('You cannot provide both a machine_auth and a wallet.')
        elif machine_auth is None and wallet is not None:
            self.auth = machine_auth_wallet.MachineAuthWallet(wallet)
        elif machine_auth is not None and wallet is None:
            self.auth = machine_auth
        else:
            raise ValueError('You must provide either a machine_auth or a wallet.')

        self.server_url = server_url if server_url is not None else two1.TWO1_HOST
        self.version = version
        if username:
            self.username = username.lower()
        self._session = None
        self._device_id = two1.TWO1_DEVICE_ID or "FREE_CLIENT"
        cb = self.auth.public_key.compressed_bytes
        self._wallet_pk = base64.b64encode(cb).decode()

    # @property
    # def username(self):
    #    return self.email.replace("@", "_AT_").replace(".", "_DOT_") if self.email
    # else None

    def _create_session(self):
        self._session = requests.Session()

    def _request(self, sign_username=None, method="GET", path="", two1_auth=None, **kwargs):
        if self._session is None:
            self._create_session()

        url = self.server_url + path
        headers = {}
        if "data" in kwargs:
            headers["Content-Type"] = "application/json"
            data = kwargs["data"]
        else:
            data = ""
        if sign_username is not None:
            timestamp = datetime.datetime.now().isoformat()
            message = url + timestamp + data
            sig = self.auth.sign_message(message)
            headers["Authorization"] = "21 {} {} {}".format(timestamp,
                                                            sign_username,
                                                            sig)

        if two1_auth is not None:
            auth_string = 'Basic ' + base64.b64encode(
                bytes('{}:{}'.format(two1_auth[0], two1_auth[1]), 'utf-8')
                ).decode().strip()
            headers["Authorization"] = auth_string
        # Change the user agent to contain the 21 CLI and version
        headers["User-Agent"] = "21/{}".format(two1.TWO1_VERSION)
        headers["From"] = "{}@{}".format(self._wallet_pk, self._device_id)

        try:
            response = self._session.request(method, url, headers=headers, **kwargs)
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError):
            raise exceptions.ServerConnectionError(uxstring.UxString.Error.connection.format("21 Servers"))

        # update required
        if response.status_code == 301:
            raise exceptions.UpdateRequiredError(uxstring.UxString.update_required)

        if response.status_code == 403:
            ex = exceptions.ServerRequestError(message=uxstring.UxString.Error.server_403, response=response)
            if "detail" in ex.data and "TO100" in ex.data["detail"]:
                raise exceptions.BitcoinComputerNeededError(uxstring.UxString.bitcoin_computer_needed,
                                                            response=response)
            else:
                raise ex

        if response.status_code >= 300:
            raise exceptions.ServerRequestError(message=uxstring.UxString.Error.server_err, response=response)

        return response

    # GET /pool/accounts
    def account_info(self):
        path = "/pool/accounts/"
        return self._request(sign_username=None, method="GET", path=path)

    # PUT /users/{username}
    def update_password(self, new_password):
        path = "/users/{}/configs/".format(self.username)
        encoded_password = base64.encodebytes(bytes(new_password, 'utf-8')).decode()
        update_body = {"password": encoded_password}
        data = json.dumps(update_body)
        ret = self._request(sign_username=self.username, method="PUT", path=path, data=data)
        return ret

    # POST /pool/account
    def account_post(self, payout_address, email, password, fullname):
        path = "/pool/account/{}/".format(self.username)
        encoded_password = base64.encodebytes(bytes(password, 'utf-8')).decode()

        body = {
            "full_name": fullname,
            "email": email,
            "password": encoded_password,
            "payout_address": payout_address,
            "public_key": self._wallet_pk,
            "device_uuid": self._device_id
        }

        data = json.dumps(body)
        try:
            ret = self._request(sign_username=self.username, method="POST", path=path, data=data)
        except exceptions.ServerRequestError as e:
            if e.status_code == 409:
                raise exceptions.UnloggedException(uxstring.UxString.existing_account.format(e.data["username"]))
            else:
                raise e
        return ret

    def login(self, payout_address, password):
        path = "/users/{}/".format(self.username)
        data = json.dumps({
            "payout_address": payout_address,
            "public_key": self._wallet_pk
        })
        two1_auth = (self.username, password)
        r = self._request(sign_username=None, method="POST", path=path, data=data, two1_auth=two1_auth)
        return r

    # GET /pool/work/{username}
    def get_work(self):
        path = "/pool/work/{}/".format(self.username)
        return self._request(sign_username=self.username, method="GET", path=path)

    # POST /pool/work/{username}
    def send_work(self, data):
        path = "/pool/work/{}/".format(self.username)
        return self._request(sign_username=None, method="POST", path=path, data=data)

    # POST /pool/account/{username}/payoutaddress
    def account_payout_address_post(self, payout_address):
        path = "/pool/account/{}/payout_address/".format(self.username)
        body = {
            "payout_address": payout_address,
        }
        data = json.dumps(body)
        return self._request(sign_username=self.username, method="POST", path=path,
                             data=data)

    # GET /pool/statistics/{username}/shares/
    def get_shares(self):
        path = "/pool/statistics/{}/shares/".format(self.username)
        return (self._request(sign_username=self.username,
                              path=path).json())[self.username]

    # GET /pool/statistics/{username}/earninglogs/
    def get_earning_logs(self):
        path = "/pool/statistics/{}/earninglogs/".format(self.username)
        return self._request(sign_username=self.username,
                             path=path).json()

    def get_mined_satoshis(self):
        """Determine the total number of Satoshis mined locally.
        """
        logs = self.get_earning_logs()
        amts = [xx['amount'] for xx in logs['logs'] if xx['reason'] == 'Shares']
        return sum(amts)

    # POST /pool/{username}/earnings/?action=True
    def flush_earnings(self, amount=None, payout_address=None):
        path = "/pool/account/{}/earnings/?action=flush".format(self.username)
        data = {}
        if amount:
            data["amount"] = amount

        if payout_address:
            data["payout_address"] = payout_address

        data = json.dumps(data)
        return self._request(sign_username=self.username, method="POST", path=path, data=data)

    def join(self, network, device_id):
        data = json.dumps({"network": network, "zerotier_device_id": device_id})
        path = "/pool/account/{}/zerotier/".format(self.username)
        return self._request(sign_username=self.username, method="POST", path=path,
                             data=data)

    def get_notifications(self, username, detailed=False):
        path = "/pool/account/{}/notifications/".format(self.username)
        if detailed:
            path += "?detailed=True"
        return self._request(sign_username=self.username, method="GET", path=path)

    # GET /integrations/coinbase/{username}/status
    def get_coinbase_status(self):
        path = "/integrations/coinbase/{}/status/".format(self.username)
        return self._request(sign_username=self.username, method="GET", path=path)

    # GET /integrations/coinbase/{username}/history
    def get_coinbase_history(self):
        path = "/integrations/coinbase/{}/history/".format(self.username)
        return self._request(sign_username=self.username, method="GET", path=path)

    # GET /integrations/coinbase/price/?amount={amount_in_satoshis}
    def quote_bitcoin_price(self, amount=1e8):
        path = "/integrations/coinbase/price/?amount={}".format(amount)
        return self._request(sign_username=self.username, method="GET", path=path)

    # POST /integrations/coinbase/buys/
    def buy_bitcoin_from_exchange(self, amount, unit, commit=False):
        data = json.dumps({"amount": amount, "unit": unit, "commit": commit})
        path = "/integrations/coinbase/buys/"
        return self._request(sign_username=self.username, method="POST", path=path, data=data)

    def mark_notifications_read(self, username):
        path = "/pool/account/{}/notifications/?action=mark_read".format(self.username)
        return self._request(sign_username=self.username, method="POST", path=path)

    def publish(self, publish_info):
        data = json.dumps(publish_info)
        path = "/market/apps/"
        return self._request(sign_username=self.username, method="POST", path=path,
                             data=data)

    def search(self, query=None, page=0):
        path = "/market/apps/?page={}".format(page)
        if query:
            query = urllib.parse.quote(query)
            path += "&query={}".format(query)

        return self._request(sign_username=self.username, method="GET", path=path)

    def get_sellable_apps(self):
        # currently a fixture until endpoint is in working state.
        return [
            {
                "name": "ping21",
                "git": "https://github.com/21dotco/ping21.git",
                "avg_earnings_day": 10000,
                "avg_earnings_request": 1000,
                "resources:": {
                    "bandwidth": "40kb",
                    "hdd": "40kb",
                    "mem": "128mb"
                }
            }
        ]

    def get_listing_info(self, listing_id):
        path = "/market/apps/{}".format(listing_id)
        return self._request(sign_username=self.username, method="GET", path=path)

    def get_published_apps(self, username, page=0):
        path = "/market/users/{}/apps/?page={}".format(self.username, page)
        return self._request(sign_username=self.username, method="GET", path=path)

    def get_app_full_info(self, username, app_id):
        path = "/market/users/{}/apps/{}/".format(self.username, app_id)
        return self._request(sign_username=self.username, method="GET", path=path)

    def delete_app(self, username, app_id):
        path = "/market/users/{}/apps/{}/".format(self.username, app_id)
        return self._request(sign_username=self.username, method="DELETE", path=path)

    def rate_app(self, app_id, rating):
        path = "/market/apps/{}/rating/".format(app_id)
        data = json.dumps({"rating": rating})
        return self._request(sign_username=self.username, method="POST", path=path, data=data)

    def get_ratings(self):
        path = "/market/users/{}/ratings/".format(self.username)
        return self._request(sign_username=self.username, method="GET", path=path)

    # GET /pool/statistics/{username}/earnings/
    def get_earnings(self):
        path = "/pool/statistics/{}/earnings/".format(self.username)
        return (self._request(sign_username=self.username,
                              path=path).json())[self.username]

    def set_primary_wallet(self, name=None):

        # if name is passed in use that to set the primary wallet
        # otherwise use the public key of the current machine
        if name:
            data = {
                "wallet_name": name
            }
        else:
            public_key = self._wallet_pk
            data = {
                "public_key": public_key
            }

        data_json = json.dumps(data)
        path = "/pool/account/{}/wallets/primary/".format(self.username)
        resp = self._request(sign_username=self.username, method="POST", path=path, data=data_json)
        return resp.json()

    def list_wallets(self):
        path = "/pool/account/{}/wallets/".format(self.username)
        resp = self._request(sign_username=self.username, method="GET", path=path)
        return resp.json()


if __name__ == "__main__":
    # host = "http://127.0.0.1:8000"
    from two1.commands.util import config

    conf = config.Config()
    host = two1.TWO1_HOST
    for n in range(2):
        m = TwentyOneRestClient(host, conf.machine_auth, conf.username)
        try:
            earn = m.get_mined_satoshis()
        except requests.exceptions.ConnectionError:
            print("Error: cannot connect to ", host)
