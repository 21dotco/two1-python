import urllib
import base64
import json
import click
import datetime
import requests
from simplejson import JSONDecodeError
from two1.lib.util.exceptions import UpdateRequiredError, BitcoinComputerNeededError, \
    UnloggedException
from two1.lib.util.uxstring import UxString
from two1.commands.config import TWO1_VERSION, TWO1_DEVICE_ID


class ServerRequestError(Exception):
    pass


class ServerConnectionError(Exception):
    pass


class TwentyOneRestClient(object):
    def __init__(self, server_url, machine_auth, username=None,
                 version="0"):
        self.auth = machine_auth
        self.server_url = server_url
        self.version = version
        self.username = username
        self._session = None
        self._device_id = TWO1_DEVICE_ID or "local"
        cb = self.auth.public_key.compressed_bytes
        self._wallet_pk = base64.b64encode(cb).decode()

    # @property
    # def username(self):
    #    return self.email.replace("@", "_AT_").replace(".", "_DOT_") if self.email
    # else None

    def _create_session(self):
        self._session = requests.Session()

    def _request(self, sign_username=None, method="GET", path="", **kwargs):
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
        # Change the user agent to contain the 21 CLI and version
        headers["User-Agent"] = "21/{}".format(TWO1_VERSION)
        headers["From"] = "{}@{}".format(self._wallet_pk, self._device_id)

        try:
            result = self._session.request(method, url, headers=headers, **kwargs)
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError):
            raise ServerConnectionError

        # update required
        if result.status_code == 301:
            click.secho(UxString.update_required, fg="red")
            raise UpdateRequiredError()

        if result.status_code == 403:
            try:
                r = result.json()
                if "detail" in r and "TO100" in r["detail"]:
                    click.secho(UxString.bitcoin_computer_needed, fg="red")
                    raise BitcoinComputerNeededError()
            # in case the response does not have json raise generic server exception
            except JSONDecodeError:
                x = ServerRequestError()
                x.status_code = result.status_code
                raise x

        if result.status_code > 299:
            x = ServerRequestError()
            x.status_code = result.status_code
            # attempt to interpret the returned content as JSON
            try:
                x.data = result.json()
            except:
                x.data = {"error": "Request Error"}
            raise x

        return result

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
    def account_post(self, payout_address, email, password):
        path = "/pool/account/%s/" % self.username
        encoded_password = base64.encodebytes(bytes(password, 'utf-8')).decode()
        body = {
            "email": email,
            "password": encoded_password,
            "payout_address": payout_address,
            "public_key": self._wallet_pk,
            "device_uuid": self._device_id
        }

        data = json.dumps(body)
        try:
            ret = self._request(sign_username=self.username, method="POST", path=path, data=data)
        except ServerRequestError as e:
            if e.status_code == 409:
                username = e.data["username"]
                click.secho(UxString.existing_account.format(username), fg="red")
                raise UnloggedException()
            else:
                raise e
        return ret

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
        path = "/pool/account/%s/payout_address/" % self.username
        body = {
            "payout_address": payout_address,
        }
        data = json.dumps(body)
        return self._request(sign_username=self.username, method="POST", path=path,
                             data=data)

    # GET /pool/statistics/{username}/shares/
    def get_shares(self):
        path = "/pool/statistics/%s/shares/" % self.username
        return (self._request(sign_username=self.username,
                              path=path).json())[self.username]

    # GET /pool/statistics/{username}/earninglogs/
    def get_earning_logs(self):
        path = "/pool/statistics/%s/earninglogs/" % self.username
        return self._request(sign_username=self.username,
                             path=path).json()

    def get_mined_satoshis(self):
        """Determine the total number of Satoshis mined locally.
        """
        logs = self.get_earning_logs()
        amts = [xx['amount'] for xx in logs['logs'] if xx['reason'] == 'Shares']
        return sum(amts)

    # POST /pool/{username}/earnings/?action=True
    def flush_earnings(self):
        path = "/pool/account/%s/earnings/?action=flush" % self.username
        return self._request(sign_username=self.username, method="POST", path=path)

    def join(self, network, device_id):
        data = json.dumps({"network": network, "zerotier_device_id": device_id})
        path = "/pool/account/%s/zerotier/" % self.username
        return self._request(sign_username=self.username, method="POST", path=path,
                             data=data)

    def get_notifications(self, username, detailed=False):
        path = "/pool/account/%s/notifications/" % self.username
        if detailed:
            path += "?detailed=True"
        return self._request(sign_username=self.username, method="GET", path=path)

    # GET /integrations/coinbase/{username}/status
    def get_coinbase_status(self):
        path = "/integrations/coinbase/{}/status/".format(self.username)
        return self._request(sign_username=self.username, method="GET", path=path)

    # POST /integrations/coinbase/buys/
    def buy_bitcoin_from_exchange(self, amount, unit):
        data = json.dumps({"amount": amount, "unit": unit})
        path = "/integrations/coinbase/buys/"
        return self._request(sign_username=self.username, method="POST", path=path, data=data)

    # POST /integrations/coinbase/sends/
    def send_bitcoin_from_exchange(self, amount):
        data = json.dumps({"amount": amount})
        path = "/integrations/coinbase/sends/"
        return self._request(sign_username=self.username, method="POST", path=path, data=data)

    # GET /mmm/v1/search
    def mmm_search(self, query, page_num=1, minprice=None, maxprice=None, sort='match', ascending=False):
        method = "GET"
        path = "/mmm/v1/search/"
        params = {
            "q": query,
            "page": page_num,
            'sort': sort,
        }

    def mark_notifications_read(self, username):
        path = "/pool/account/%s/notifications/?action=mark_read" % self.username
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
        data = json.dumps({"rating" : rating})
        return self._request(sign_username=self.username, method="POST", path=path, data=data)

    def get_ratings(self):
        path = "/market/users/{}/ratings/".format(self.username)
        return self._request(sign_username=self.username, method="GET", path=path)

    # GET /pool/statistics/{username}/earnings/
    def get_earnings(self):
        path = "/pool/statistics/%s/earnings/" % self.username
        return (self._request(sign_username=self.username,
                              path=path).json())[self.username]


if __name__ == "__main__":
    # host = "http://127.0.0.1:8000"
    from two1.commands.config import Config
    from two1.commands.config import TWO1_HOST

    conf = Config()
    host = TWO1_HOST
    for n in range(2):
        m = TwentyOneRestClient(host, conf.machine_auth, conf.username)
        try:
            earn = m.get_mined_satoshis()
        except requests.exceptions.ConnectionError:
            print("Error: cannot connect to ", host)
