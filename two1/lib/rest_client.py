
# This is the 21.co/mining REST client
# Create a/c
# Set payout addresses etc.
from two1.bitcoin.crypto import PrivateKey
from two1.bitcoin.utils import bytes_to_str, address_to_key_hash
import base64
import requests
import json
from urllib.parse import urljoin


class MachineAuth(object):

    def __init__(self, private_key):
        if private_key:
            self.private_key = private_key
            self.public_key = private_key.public_key
        else:
            self.private_key = None
            self.public_key = None

    def create(self):
        pass

    def load(self):
        pass

    def sign(self, message):
        if self.private_key:
            if isinstance(message, str):
                utf8 = message.encode('utf-8')
            else:
                raise ValueError
            signature = self.private_key.sign(utf8).to_base64()
            return signature
        else:
            return None
        # compressed_bytes = base64.b64encode(self.public_key.compressed_bytes)
        # signature = signature.to_base64()

        # print("Things",compressed_bytes,signature,utf8)

        # signature = Signature.from_base64(signature)
        # pubk = PublicKey.from_base64(compressed_bytes)
        # print("VERIFICATION RESULT: %g " % pubk.verify(utf8, signature))


class TwentyOneRestClient(object):

    def __init__(self, server_url, private_key=None, username=None, version="v0"):
        self.auth = MachineAuth(private_key)
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

    # GET /mmm/sells/search/
    def mmm_search(self, query, page_num=1):
        method = "GET"
        path = "/mmm/sells/search/"
        r = self._request(False, method, path, params={"q": query, "page": page_num})
        if r.status_code == 200:
            return json.loads(r.content.decode())
        else:
            raise

    # POST /mmm/{username}/sells
    def mmm_create_sell(self, name, description, price):
        method = "POST"
        path = "/mmm/{}/sells".format(self.username)
        body = {
            "name"          : name,
            "description"   : description,
            "price"         : price
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
