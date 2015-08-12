
# This is the 21.co/mining REST client
# Create a/c
# Set payout addresses etc.
from two1.bitcoin.crypto import PrivateKey
from two1.bitcoin.utils import bytes_to_str, address_to_key_hash
import requests
import json
from urllib.parse import urljoin

class MiningAuth(object):
	def __init__(self,private_key):
		self.private_key=private_key
		self.public_key=private_key.public_key

	def create(self):
		pass

	def load(self):
		pass

	def sign(self,message):
		if type(message) == type(''):
			utf8 = message.encode('utf-8')
		else:
			raise ValueError
		return self.private_key.sign_bitcoin(utf8)

class MiningRestClient(object):

	def __init__(self,private_key,server_url,version="v0"):
		self.auth = MiningAuth(private_key)
		self.server_url = server_url
		self.version = version

	def _request(self,signed,method,path,**kwargs):
		url = self.server_url+path+"/"
		headers={}
		if "data" in kwargs:
			headers["Content-Type"]="application/json"
			data = kwargs["data"]
		else:
			data = ""
		if signed:
			sig = self.auth.sign(data)
			headers["Authorization"]=sig
		if len(headers) == 0:
			headers = None
		print("Request: " + str(method)+ " " + str(url)  + " " + str(headers)  + " " + str(kwargs["data"]))
		result = requests.request(method,
								url,
								headers=headers,
								**kwargs)
		print("Result: %s %s " % (result,result.text))
		return result

	#POST /v0/mining/account
	def mining_account_post(self,username,payout_address):
		method = "POST"
		path = "/v0/mining/account/" + username
		body = {
				"payout_address": payout_address,
				"public_key_digest": self.auth.public_key.b58address,
				}
		data=json.dumps(body)
		r=self._request(True,method,
						path,
						data=json.dumps(body)
						);

	#POST /v0/mining/account/payout_address/{username}
	def mining_account_payout_address_post(self,username,payout_address):
		method = "POST"
		path = "/v0/mining/account/payout_address/" + username
		body = {
				"payout_address": payout_address,
				}
		data = json.dumps(body)
		r=self._request(True,method,
						path,
						data=data
						);


if __name__=="__main__":
#	pk = PrivateKey.from_random()
#	m = MiningRestClient(pk,"http://127.0.0.1:8000")
	for n in range(10):
		pk = PrivateKey.from_random()
		m = MiningRestClient(pk,"http://127.0.0.1:8000")
		m.mining_account_post("testuser0_"+str(n),"1BHZExCqojqzmFnyyPEcUMWLiWALJ32Zp5")
		m.mining_account_payout_address_post("testuser0_"+str(n),"1LuckyP83urTUEJE9YEaVG2ov3EDz3TgQw")
