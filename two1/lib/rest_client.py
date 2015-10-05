
# This is the 21.co/mining REST client
import base64
import requests
import json
import datetime
from urllib.parse import urljoin
from two1.bitcoin.crypto import PrivateKey
from two1.bitcoin.utils import bytes_to_str, address_to_key_hash
from two1.lib.exceptions import ServerRequestError
from two1.lib.machine_auth import MachineAuth
import click


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

    # POST /pool/account
    def account_post(self, username, payout_address):
        method = "POST"
        path = "/pool/account/" + username
        body = {
            "payout_address": payout_address,
            "public_key": base64.b64encode(self.auth.public_key.compressed_bytes).decode(),
        }
        data = json.dumps(body)
        return self._request(True, method,
                             path,
                             data=data
                             )

    # GET /pool/work/{username}
    def get_work(self, username):

        method = "GET"
        path = "/pool/work/" + username
        return self._request(True, method, path)

    # POST /pool/work/{username}
    def send_work(self, username, data):
        method = "POST"
        path = "/pool/work/" + username
        return self._request(False, method, path, data=data)

    # POST /pool/account/payout_address/{username}
    def account_payout_address_post(self, username, payout_address):
        method = "POST"
        path = "/pool/account/payout_address/" + username
        body = {
            "payout_address": payout_address,
        }
        data = json.dumps(body)
        return self._request(True, method,
                             path,
                             data=data
                             )

    # GET /pool/statistics/shares/{username}
    def get_shares(self, username):
        method = "GET"
        path = "/pool/statistics/shares/" + username
        r = self._request(False, method, path)
        if r.status_code == 200:
            return json.loads(r.content.decode())
        else:
            raise

    # GET /mmm/listings/search/
    def mmm_search(self, query, page_num=1):
        method = "GET"
        path = "/mmm/listings/search/"
        r = self._request(
            False, method, path, params={"q": query, "page": page_num})
        if r.status_code == 200:
            return r.json()
        else:
            raise ServerRequestError(r.json()['error'])

    # POST /mmm/v1/listings/
    def mmm_create_listing(self, path, name, description, price, device_id):
        method = "POST"
        url = '/mmm/v1/listings/'
        body = {
            "name": name,
            "description": description,
            "price": price,
            "path": path,
            "server": device_id
        }

        data = json.dumps(body)

        return self._request(True, method,
                             url,
                             data=data
                             )

    # todo implement update, maybe use separate command that takes in uuid
    def mmm_update_listing(uuid):
        # method = 'PUT'
        # url = '{}/mmm/v1/listings/{}'.format(TWO1_DEV_HOST, uuid)
        pass

    # def mmm_check_listing_exists(self, ):
    #     import datetime
    #     method = "GET"
    #     url = "{}/mmm/v1/listings/".format(TWO1_DEV_HOST)
    #     params = {
    #         "path": path,
    #         "server": device_id
    #     }
    #     kwargs = {'params': params}
    #     headers = {}
    #     headers["Content-Type"] = "application/json"
    #     response = requests.request(method, url, headers=headers, **kwargs)
    #     if response.status_code == 200:
    #         try:
    #             existing_id = response.json()[0].get('id', None)
    #         except IndexError:
    #             existing_id = None
    #         # if existing_id is not None:
    #         #     method = 'PUT'
    #         #     url = '{}/mmm/v1/listings/{}'.format(TWO1_DEV_HOST, existing_id)
    #         # else:
    #     return existing_id


    # # PUT /mmm/listings/<id>
    # def mmm_delete_listing(self, path, name, description, price, device_uuid):
    #     """Soft deletes listing by setting delete=True
    #     """
    #     method = "GET"
    #     url = "/mmm/v1/listings/"
    #     params = {
    #         "server": device_uuid
    #     }
    #     response = self._request(True, method, url, params=params)
    #     if response.status_code == 201:
    #         method = "PUT"
    #         body = {
    #             "name": name,
    #             "description": description,
    #             "price": price,
    #             "path": path,
    #             "server": device_uuid,
    #             "deleted": True,
    #             "active": False,
    #             "last_active": datetime.datetime.now()
    #         }
    #         data = json.dumps(body)
    #         return self._request(True, method, url, data=data)


    # # GET /mmm/listings/ -- list of listings that belong to this device
    # def mmm_device_listings(self, active=None, page_num=1):
    #     method = "GET"
    #     path = "/mmm/v1/listings/"
    #     params = {
    #         # should this take in device rather than username?
    #         "username": self.username, "page": page_num,
    #         "deleted": False
    #     }
    #     if active is True or active is False:
    #         params['active'] = active
    #     r = self._request(
    #         False, method, path, params=params)
    #     if r.status_code == 200:
    #         return json.loads(r.content.decode())
    #     else:
    #         raise


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
