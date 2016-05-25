# standard python imports
import sys
import argparse

# 3rd party imports
import yaml

# two1 imports
from two1.commands.util.exceptions import ServerRequestError
from two1.sell.util.cli_helpers import get_rest_client


def publish_manifest(service, zt_ip, port):
    """ Publish manifest to 21 Marketplace index.
    """
    with open('/usr/src/app/manifest.yaml', "r") as f:
        manifest_json = yaml.load(f)

    manifest_json["basePath"] = "/%s" % service
    manifest_json["host"] = "%s:%s" % (zt_ip, port)
    try:
        manifest_json["info"]["x-21-quick-buy"] = manifest_json["info"]["x-21-quick-buy"] % (zt_ip, port, service)
    except Exception:
        pass
    try:
        with open('/usr/src/app/manifest.yaml', "w") as f:
            yaml.dump(manifest_json, f)
        resp = get_rest_client().publish({"manifest": manifest_json,
                                          "marketplace": "21market"})
    except ServerRequestError as e:
        if e.status_code == 403 and e.data.get("error") == "TO600":
            sys.exit(101)  # publish_stats.append((service.title(), False, ["Endpoint already published"]))
        else:
            sys.exit(102)  # publish_stats.append((service.title(), False, ["Failed to publish"]))
    except:
        sys.exit(99)  # publish_stats.append((service.title(), False, ["An unknown error occurred"]))
    else:
        if resp.status_code == 201:
            sys.exit(100)  # publish_stats.append((service.title(), True, ["Published"]))
        else:
            sys.exit(102)  # publish_stats.append((service.title(), False, ["Failed to publish"]))


if __name__ == "__main__":
    """ Run publish tool.
    """
    # parse arguments
    parser = argparse.ArgumentParser(description="Publish service manifest.")
    parser.add_argument('service', action='store')
    parser.add_argument('zt_ip', action='store')
    parser.add_argument('port', action='store')
    args = parser.parse_args()

    # publish manifest
    publish_manifest(args.service,
                     args.zt_ip,
                     args.port)
