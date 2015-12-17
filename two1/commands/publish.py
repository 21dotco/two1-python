import json
from urllib.parse import urlparse

import os
import click
from tabulate import tabulate
from two1.lib.server.analytics import capture_usage
from two1.lib.server import rest_client
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.util.decorators import json_output
from two1.lib.util.uxstring import UxString
from two1.lib.util import zerotier
from two1.commands.config import TWO1_HOST
from two1.commands.search import shorten_search_results, get_next_page


@click.command("publish")
@click.option('-l', '--list', is_flag=True, default=False,
              help='Lists all the apps published by you.')
@click.option('-d', '--delete', help="Deletes a published app by its id.")
@click.option('-a', '--app_directory', type=click.Path(exists=False),
              help="Publishes an app directory to the marketplace.")
@click.option('-m', '--marketplace', default='21market',
              help="Selects the marketplace to publish the app to. Must be used with the "
                   "-a option")
@click.pass_context
def publish(ctx, app_directory, marketplace, list, delete):
    """Publish a machine-payable endpoint to a market.
    """

    config = ctx.obj['config']
    if list:
        _list_apps(config)
        return
    elif delete:
        print("DELETE")
        return
    elif app_directory:
        _publish(config, app_directory, marketplace)
        return
    else:
        click.secho(ctx.command.get_help(ctx))


@capture_usage
def _list_apps(config):
    click.secho(UxString.my_apps.format(config.username), fg="green")
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)
    current_page = 0
    total_pages = get_search_results(config, client, current_page)
    if total_pages < 1:
        return

    while 0 <= current_page < total_pages:
        try:
            prompt_resp = click.prompt(UxString.pagination,
                                       type=str)

            next_page = get_next_page(prompt_resp, current_page)

            if next_page == -1:
                model_id = prompt_resp
                print(model_id)
            elif next_page >= total_pages or next_page < 0:
                    continue
            else:
                get_search_results(config, client, next_page)
                current_page = next_page

        except click.exceptions.Abort:
            return


def get_search_results(config, client, page):
    resp = client.get_published_apps(config.username, page)
    if resp.ok:
        resp_json = resp.json()
        search_results = resp_json["results"]
        if search_results is None or len(search_results) == 0:
            click.secho(UxString.no_published_apps, fg="blue")
            return 0

        total_pages = resp_json["total_pages"]
        shorten_search_results(search_results)
        click.secho("\nPage {}/{}".format(page + 1, total_pages), fg="green")
        headers = ["id", "Title", "Url", "Is up", "Is healthy", "Average Uptime",
                   "Last Update"]
        rows = [[r["id"], r["title"], r["app_url"], str(r["is_up"]), str(r["is_healthy"]),
                 "{}%".format(r["average_uptime"] * 100),
                 r["last_update"]] for r in search_results]
        click.echo(tabulate(rows, headers, tablefmt="grid"))
        return total_pages
    else:
        raise ServerRequestError()


def _delete_app(config, app_id):
    pass


@capture_usage
def _publish(config, app_directory, marketplace):
    api_docs_path = os.path.join(app_directory, "manifest", "manifest.json")
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
                                                       UxString.publish_docs_url),
                        fg="red")
                raise ValueError()

            with open(api_docs_path, "r") as f:
                manifest_json = json.loads(f.read())
                return manifest_json
        except ValueError:
            click.secho(
                    UxString.bad_manifest.format(api_docs_path,
                                                 UxString.publish_docs_url),
                    fg="red")
            raise ValueError()
    else:
        click.secho(
                UxString.manifest_missing.format(api_docs_path,
                                                 UxString.publish_docs_url),
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
