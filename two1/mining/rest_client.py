
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
		return self.private_key.sign(utf8)

class MiningRestClient(object):

	def __init__(self,private_key,server_url,version="v0"):
		self.auth = MiningAuth(private_key)
		self.server_url = server_url
		self.version = version

	def _request(self,method,path,**kwargs):
		url = self.server_url+"/"+self.version+path+"/"
		result = requests.request(method,
								url,
								**kwargs)
		return result

	#POST /mining/account
	def mining_account_post(self,username,payout_address):
		method = "POST"
		path = "/mining/account"
		body = {"username": username,
				"payout_address": payout_address,
				"public_key_digest": self.auth.public_key.b58address,
				}
		r=self._request(method,
						path,
						headers={"Content-Type":"application/json"},
						data=json.dumps(body)
						);

	#POST /mining/account/payout_address/{username}
	def mining_account_payout_address_post(self,username,payout_address):
		method = "POST"
		path = "/mining/account/payout_address/" + username
		body = {
				"payout_address": payout_address,
				}
		data = json.dumps(body)
		sig = self.auth.sign(data)
		r=self._request(method,
						path,
						headers={"Content-Type":"application/json",
								"Authorization":sig.to_hex()
								},
						data=data
						);


if __name__=="__main__":
	pk = PrivateKey.from_random()
	m = MiningRestClient(pk,"http://127.0.0.1:8000")
	m.mining_account_post("haha2","1BHZExCqojqzmFnyyPEcUMWLiWALJ32Zp5")
	m.mining_account_payout_address_post("haha2","1BHZExCqojqzmFnyyPEcUMWLiWALJ32Zp6")
