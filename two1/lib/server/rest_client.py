import re
import base64
import json
import click
from collections import namedtuple
import urllib.parse

import requests

from two1.lib.bitcoin.crypto import PrivateKey
from two1.lib.server.machine_auth import MachineAuth
from two1.commands.exceptions import ServerRequestError


class TwentyOneRestClient(object):

    def __init__(self, server_url, machine_auth=None, username=None,
                 version="0"):
        self.auth = machine_auth
        self.server_url = server_url
        self.version = version
        self.username = username

    @staticmethod
    def from_keyring(server_url, username=None, version="0"):
        auth = MachineAuth.from_keyring()
        return TwentyOneRestClient(server_url, auth, username, version)

    def _request(self, signed=False, method="GET", path="", **kwargs):
        url = self.server_url + path
        headers = {}
        if "data" in kwargs:
            headers["Content-Type"] = "application/json"
            data = kwargs["data"]
        else:
            data = ""
        if signed:
            sig = self.auth.sign_message(data)
            headers["Authorization"] = sig.decode()

        result = requests.request(method, url, headers=headers, **kwargs)
        return result

    # POST /pool/account
    def account_post(self, username, payout_address):
        path = "/pool/account/%s/" % username
        cb = self.auth.public_key.compressed_bytes
        body = {
            "payout_address": payout_address,
            "public_key": base64.b64encode(cb).decode(),
        }
        data = json.dumps(body)
        return self._request(signed=True, method="POST", path=path, data=data)

    # GET /pool/work/{username}
    def get_work(self, username):
        path = "/pool/work/%s/" % username
        return self._request(signed=True, method="GET", path=path)

    # POST /pool/work/{username}
    def send_work(self, username, data):
        path = "/pool/work/%s/" % username
        return self._request(signed=False, method="POST", path=path, data=data)

    # POST /pool/account/payout_address/{username}
    def account_payout_address_post(self, username, payout_address):
        path = "/pool/account/payout_address/%s/" % username
        body = {
            "payout_address": payout_address,
        }
        data = json.dumps(body)
        return self._request(signed=True, method="POST", path=path, data=data)

    # GET /pool/statistics/shares/{username}
    def get_shares(self, username):
        path = "/pool/statistics/shares/%s/" % username
        return self._request(path=path).json()

    # POST /pool/{username}/earnings/?action=True
    def flush_earnings(self, username):
        path = "/pool/account/%s/earnings/?action=flush" % username
        return self._request(signed=False, method="POST", path=path)

    # GET /mmm/v1/search
    def mmm_search(self, query, page_num=1, minprice=None, maxprice=None, sort='match', ascending=False):
        method = "GET"
        path = "/mmm/v1/search/"
        params = {
            "q": query,
            "page": page_num,
            'sort': sort,
        }

        if minprice is not None:
            params['minprice'] = minprice
        if maxprice is not None:
            params['maxprice'] = maxprice
        if not ascending:
            params['ascending'] = 'true'

        r = self._request(False, method, path, params=params)
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

    def mmm_check_listing_exists(self):
        pass
        # import datetime
        # method = "GET"
        # url = "{}/mmm/v1/listings/".format(TWO1_DEV_HOST)
        # params = {
        #     "path": path,
        #     "server": device_id
        # }
        # kwargs = {'params': params}
        # headers = {}
        # headers["Content-Type"] = "application/json"
        # response = requests.request(method, url, headers=headers, **kwargs)
        # if response.status_code == 200:
        #     try:
        #         existing_id = response.json()[0].get('id', None)
        #     except IndexError:
        #         existing_id = None
        #     # if existing_id is not None:
        #     #     method = 'PUT'
        #     #     url = '{}/mmm/v1/listings/{}'.format(TWO1_DEV_HOST, existing_id)
        #     # else:
        # return existing_id

    # PUT /mmm/listings/<id>
    def mmm_delete_listing(self, path, name, description, price, device_uuid):
        pass
        # """Soft deletes listing by setting delete=True
        # """
        # method = "GET"
        # url = "/mmm/v1/listings/"
        # params = {
        #     "server": device_uuid
        # }
        # response = self._request(True, method, url, params=params)
        # if response.status_code == 201:
        #     method = "PUT"
        #     body = {
        #         "name": name,
        #         "description": description,
        #         "price": price,
        #         "path": path,
        #         "server": device_uuid,
        #         "deleted": True,
        #         "active": False,
        #         "last_active": datetime.datetime.now()
        #     }
        #     data = json.dumps(body)
        #     return self._request(True, method, url, data=data)

    # GET /mmm/listings/ -- list of listings that belong to this device
    def mmm_device_listings(self, active=None, page_num=1):
        pass
        # method = "GET"
        # path = "/mmm/v1/listings/"
        # params = {
        #     # should this take in device rather than username?
        #     "username": self.username, "page": page_num,
        #     "deleted": False
        # }
        # if active is True or active is False:
        #     params['active'] = active
        # r = self._request(
        #     False, method, path, params=params)
        # if r.status_code == 200:
        #     return json.loads(r.content.decode())
        # else:
        #     raise

    # POST /mmm/v1/ratings/
    def mmm_rating_post(self, purchase, rating):
        method = "POST"
        path = "/mmm/v1/ratings/"
        body = {
            "purchase": purchase,  # uuid of purchase
            "rating": rating
        }
        data = json.dumps(body)
        r = self._request(False, method, path, data=data)

        if (r.status_code == 201):  # 201 == Created, Success
            #click.echo("Success!")
            pass
        elif r.status_code == 200:  # 200 == Success
            click.echo("You made a review of this already")  # Nothing updated
            # TODO: Prompt user to ask if they want to update score
        else:
            click.echo("Error: Bad request, check if purchase uuid is valid.")
            #click.echo("%s (%s): %s" % (r.status_code, r.reason, r.text))
        return r

    # PUT /mmm/v1/ratings/c833e922-4cc1-4f6a-9d1f-181c839c0a08/
    def mmm_rating_put(self, purchase, rating, num_updates):
        method = "PUT"
        path = "/mmm/v1/ratings/{}/".format(purchase)
        num_updates += 1
        body = {
            "purchase": purchase,  # uuid of purchase
            "rating": rating,
            "num_updates": num_updates
        }
        data = json.dumps(body)
        return self._request(False, method, path, data=data)

    # GET /mmm/v1/ratings/c833e922-4cc1-4f6a-9d1f-181c839c0a08/
    def mmm_rating_get(self, purchase, rating):
        method = "GET"
        path = "/mmm/v1/ratings/{}/".format(purchase)
        num_updates = 1
        body = {
            "purchase": purchase,  # uuid of purchase
            "rating": rating,
            "num_updates": num_updates
        }
        data = json.dumps(body)
        return self._request(False, method, path, data=data)

    # GET /pool/statistics/earnings/{username}
    def get_earnings(self, username):
        path = "/pool/statistics/earnings/%s/" % username
        return self._request(path=path).json()

    @staticmethod
    def params2example(parameters, url):
        """Parse Swagger output into 21 buy syntax.

        https://godoc.org/github.com/emicklei/go-restful/swagger#Parameter
        """
        form, formstr, query, querystr = {}, "", {}, ""
        for param in parameters:
            if param['required']:
                if param['paramType'] == 'form':
                    form[param['name']] = "[%s]" % param['type']
                elif param['paramType'] == 'body':
                    #print(param)
                    pass
                elif param['paramType'] == 'query':
                    query[param['name']] = "%s" % param['type']
                elif param['paramType'] == 'path':
                    #print(param)
                    pass
                if param['paramType'] == 'header':
                    #print(param)
                    pass
        if len(query) > 0:
            querystr = "?%s" % urllib.parse.urlencode(query)
        if len(form) > 0:
            formstr = "--data '%s'" % json.dumps(form)
        return "21 buy %s%s %s" % (url, querystr, formstr)

    # GET /docs/api-docs
    def search(self, query="", detail=False, page_num=1):
        """Search the Many Machine Market. If blank query, list all endpoints.
        """
        path = "/docs/api-docs"
        data = self._request(path=path).json()
        apis = []
        for xx in data['apis']:
            apipath = path + xx['path']
            r = self._request(path=apipath).json()['apis']
            apis.append(r)
        fields = ("url", "method", "description", "price", "example")
        Listing = namedtuple("Listing", fields)
        listings = []
        for api in apis:
            for function in api:
                ops = function['operations']
                assert len(ops) == 1
                url = self.server_url + function['path']
                example = self.params2example(ops[0]['parameters'], url) \
                    if detail else ""
                ll = Listing(url=url,
                             method=ops[0]['method'],
                             description=function['description'],
                             price=0,
                             example=example)
                if query == "":
                    listings.append(ll)
                else:
                    if re.search(query, ll.url) or \
                       re.search(query, ll.description):
                        listings.append(ll)

        return listings


if __name__ == "__main__":
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
