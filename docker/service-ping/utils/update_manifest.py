import os

import yaml

manifest_path = '/usr/src/app/manifest.yaml'
zt_ip, port = os.environ['PAYMENT_SERVER_IP'].replace('https://', '').replace('http://', '').split(':')

with open(manifest_path, "r") as f:
    manifest_json = yaml.load(f)

service = os.environ['SERVICE']
manifest_json["basePath"] = "/%s" % service
manifest_json["host"] = "%s:%s" % (zt_ip, port)
try:
    manifest_json["info"]["x-21-quick-buy"] = manifest_json["info"]["x-21-quick-buy"] % (zt_ip, port, service)
except:
    pass

with open(manifest_path, "w") as f:
    yaml.dump(manifest_json, f)
