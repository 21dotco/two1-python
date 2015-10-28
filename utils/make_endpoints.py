import os
import subprocess


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    subprocess.call(BASE_DIR + "/make_endpoints.sh")
except PermissionError:
    print("Permission Error. "
          "Make sure you change the make_endpoints.sh to an executable: "
          "chmod +x utils/make_endpoints.sh")

print("Checking Endpoints")


import two1.commands.config as config

assert config.TWO1_PROD_HOST == "https://dotco-prod-pool2.herokuapp.com"
assert config.TWO1_LOGGER_SERVER == "http://prod-pool-api-logger-2111347410.us-east-1.elb.amazonaws.com"
assert config.TWO1_POOL_URL == "swirl+tcp://ac79afc13446427189326683b47d1e7e-803620906.us-east-1.elb.amazonaws.com:21006"
assert config.TWO1_MERCHANT_HOST == "http://two1-merchant-server-prod-1287.herokuapp.com"

print("Correct Endpoints")