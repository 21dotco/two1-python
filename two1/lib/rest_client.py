
# This is the 21.co/mining REST client
import base64
import requests
import json
from urllib.parse import urljoin
from two1.bitcoin.crypto import PrivateKey
from two1.bitcoin.utils import bytes_to_str, address_to_key_hash
from two1.lib.machine_auth import MachineAuth


class TwentyOneRestClient(object):

    def __init__(self, server_url, machine_auth=None, username=None, version="0"):
        self.auth = machine_auth
        self.server_url = server_url
        self.version = version
        self.username = username

    def from_keyring(self, server_url, username=None, version="0"):
        self.auth = MachineAuth.from_keyring()
        self.server_url = server_url
        self.version = version
        self.username = username

    def _request(self, signed, method, path, **kwargs):
        url = self.server_url + path + "/"
        headers = {}
        if "data" in kwargs:
            headers["Content-Type"] = "application/json"
            data = kwargs["data"]
        else:
            data = ""
        if signed:
            sig = self.auth.sign(data)
            headers["Authorization"] = sig.decode()
        if len(headers) == 0:
            headers = None
        result = requests.request(method,
                                  url,
                                  headers=headers,
                                  **kwargs)
        return result

    # POST /v0/mining/account
    def account_post(self, username, payout_address):
        method = "POST"
        path = "/v0/mining/account/" + username
        body = {
            "payout_address": payout_address,
            "public_key": base64.b64encode(self.auth.public_key.compressed_bytes).decode(),
        }
        data = json.dumps(body)
        return self._request(True, method,
                             path,
                             data=data
                             )

    # GET /v0/mining/work/{username}
    def get_work(self, username):

        method = "GET"
        path = "/v0/mining/work/" + username
        return self._request(True, method, path)

    # POST /v0/mining/work/{username}
    def send_work(self, username, data):
        method = "POST"
        path = "/v0/mining/work/" + username
        return self._request(False, method, path, data=data)

    # POST /v0/mining/account/payout_address/{username}
    def account_payout_address_post(self, username, payout_address):
        method = "POST"
        path = "/v0/mining/account/payout_address/" + username
        body = {
            "payout_address": payout_address,
        }
        data = json.dumps(body)
        return self._request(True, method,
                             path,
                             data=data
                             )

    # GET /v0/mining/statistics/shares/{username}
    def get_shares(self, username):
        method = "GET"
        path = "/v0/mining/statistics/shares/" + username
        r = self._request(False, method, path)
        if r.status_code == 200:
            return json.loads(r.content.decode())
        else:
            raise

    # GET /mmm/sells/search/
    def mmm_search(self, query, page_num=1):
        method = "GET"
        path = "/mmm/sells/search/"
        r = self._request(
            False, method, path, params={"q": query, "page": page_num})
        if r.status_code == 200:
            return json.loads(r.content.decode())
        else:
            raise

    # POST /mmm/{username}/sells
    def mmm_create_sell(self, name, description, price):
        method = "POST"
        path = "/mmm/{}/sells".format(self.username)
        body = {
            "name": name,
            "description": description,
            "price": price
        }
        data = json.dumps(body)
        return self._request(True, method,
                             path,
                             data=data
                             )


if __name__ == "__main__":
    # pk = PrivateKey.from_random()
    # m = MiningRestClient(pk,"http://127.0.0.1:8000")
    host = "http://127.0.0.1:8000"
    for n in range(100):
        pk = PrivateKey.from_random()
        m = TwentyOneRestClient(pk, host)
        try:
            m.account_post("testuser11210_" + str(n),
                           "1BHZExCqojqzmFnyyPEcUMWLiWALJ32Zp5")
            m.account_payout_address_post("testuser11210_" + str(n),
                                          "1LuckyP83urTUEJE9YEaVG2ov3EDz3TgQw")

        except requests.exceptions.ConnectionError:
            print("Error: cannot connect to ", host)
