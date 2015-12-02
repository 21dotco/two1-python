import json
from urllib.parse import urlparse

import os
import click
from two1.lib.server.analytics import capture_usage
from two1.lib.server import rest_client
from two1.lib.util.decorators import json_output
from two1.lib.util.uxstring import UxString
from two1.lib.util import zerotier
from two1.commands.config import TWO1_HOST


@click.command("publish")
@click.argument('app_directory', type=click.Path(exists=False))
@click.option('-m', '--marketplace', default='21market')
@click.pass_context
def publish(ctx, app_directory, marketplace):
    """Publish a machine-payable endpoint to a market.
    """
    config = ctx.obj['config']
    _publish(config, app_directory, marketplace)


@capture_usage
def _publish(config, app_directory, marketplace):
    api_docs_path = os.path.join(app_directory, "api-docs", "manifest.json")
    try:
        manifest_json = check_app_manifest(api_docs_path)
        app_name = manifest_json["info"]["title"]
        app_url = urlparse(manifest_json["host"])
        app_endpoint = "{}://{}{}".format(manifest_json["schemes"][0],
                                          manifest_json["host"],
                                          manifest_json["basePath"])
        app_ip = app_url.path.split(":")[0]
        address = get_zerotier_address(marketplace)

        if address != app_ip:
            if not click.confirm(UxString.wrong_ip.format(app_ip, address, app_ip)):
                click.secho(UxString.switch_host.format(api_docs_path, app_ip, address))
                return

    except ValueError:
        return
    except KeyError:
        click.secho(
            UxString.bad_manifest.format(api_docs_path, UxString.publish_docs_url),
            fg="red")
        return

    click.secho(UxString.publish_start.format(app_name, app_endpoint, marketplace))
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)
    payload = {"manifest": manifest_json, "marketplace": marketplace}
    response = client.publish(payload)
    if response.status_code == 201:
        click.secho(UxString.publish_success.format(app_name, marketplace))


def check_app_manifest(api_docs_path):
    if os.path.exists(api_docs_path):
        click.secho(UxString.reading_manifest.format(api_docs_path))
        try:

            file_size = os.path.getsize(api_docs_path) / 1e6
            if file_size > 2:
                click.secho(
                    UxString.large_manifest.format(api_docs_path,
                                                   UxString.publish_docs_url), fg="red")
                raise ValueError()

            with open(api_docs_path, "r") as f:
                manifest_json = json.loads(f.read())
                return manifest_json
        except ValueError:
            click.secho(
                UxString.bad_manifest.format(api_docs_path, UxString.publish_docs_url),
                fg="red")
            raise ValueError()
    else:
        click.secho(
            UxString.manifest_missing.format(api_docs_path, UxString.publish_docs_url),
            fg="red")
        raise ValueError()


def get_zerotier_address(marketplace):
    click.secho(UxString.update_superuser)
    all_networks = zerotier.list_networks()
    networks = [n for n in all_networks if n['name'] == marketplace]
    if len(networks) != 1:
        click.secho(UxString.no_zt_network.format(marketplace, UxString.join_cmd))
        raise ValueError
    else:
        network = networks[0]
        address_and_mask = network["assignedAddresses"][0]
        address = address_and_mask.split("/")[0]
        return address
