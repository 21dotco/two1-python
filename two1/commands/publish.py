import datetime
import json
from urllib.parse import urlparse

import os
import click
from tabulate import tabulate
from two1.lib.server.analytics import capture_usage
from two1.lib.server import rest_client
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.util.decorators import json_output, check_notifications
from two1.lib.util.uxstring import UxString
from two1.lib.util import zerotier
from two1.commands.config import TWO1_HOST
from two1.commands.search import shorten_search_results, get_next_page


@click.group()
def publish():
    """Publish/Manage your marketplace apps.

\b
Usage
_____
Publish your app to the 21 Marketplace
$ 21 publish submit path_to_manifest/manifest.json


\b
See the help for submit
$ 21 publish submit --help


\b
View all of your published apps
$ 21 publish list

\b
See the help for list
$ 21 publish list --help

\b
Remove one of your published apps from the marketplace
$ 21 publish remove app_id


\b
See the help for remove
$ 21 publish remove --help

    """
    pass


@publish.command()
@click.pass_context
def list(ctx):
    """
Lists all your published apps.

$ 21 publish list

Results from the list command are paginated.
Use 'n' to move to the next page and 'p' to move to the previous page.

You can view detailed admin information about an app by specifying it's id
at the prompt.
    """
    config = ctx.obj["config"]
    _list_apps(config)


@publish.command()
@click.argument('app_id')
@click.pass_context
def remove(ctx, app_id):
    """
Removes a published app from the Marketplace.

$ 21 publish remove app_id

The app_id can be obtained by performing:

$ 21 publish list
    """
    config = ctx.obj["config"]
    _delete_app(config, app_id)


@publish.command()
@click.argument('app_directory', type=click.Path(exists=False))
@click.option('-m', '--marketplace', default='21market',
              help="Selects the marketplace for publishing")
@click.pass_context
def submit(ctx, app_directory, marketplace):
    """
Submits an app to the Marketplace.

\b
$ 21 publish submit path_to_manifest/manifest.json

The contents of the manifest file should follow the guidelines specified at
https://21.co/publish

Before publishing, make sure that you've joined the 21 marketplace by running the `21 join` command.
    """
    _publish(ctx.obj["config"], app_directory, marketplace)


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
                display_app_info(config, client, model_id)
            elif next_page >= total_pages or next_page < 0:
                continue
            else:
                get_search_results(config, client, next_page)
                current_page = next_page

        except click.exceptions.Abort:
            return


@check_notifications
@capture_usage
def _delete_app(config, app_id):
    if click.confirm(UxString.delete_confirmation.format(app_id)):
        client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                                 config.machine_auth,
                                                 config.username)
        resp = client.delete_app(config.username, app_id)
        resp_json = resp.json()
        deleted_title = resp_json["deleted_title"]
        click.secho(UxString.delete_success.format(app_id, deleted_title))


@check_notifications
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
    except KeyError as e:
        click.secho(
                UxString.bad_manifest.format(e.args[0], api_docs_path, UxString.publish_docs_url),
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
                 "{:.2f}%".format(r["average_uptime"] * 100),
                 datetime.datetime.fromtimestamp(r["last_update"]).strftime(
                         "%Y-%m-%d %H:%M")] for r in search_results]
        click.echo(tabulate(rows, headers, tablefmt="grid"))
        return total_pages
    else:
        raise ServerRequestError()


def display_app_info(config, client, app_id):
    try:
        resp = client.get_app_full_info(config.username, app_id)
        result = resp.json()
        app_info = result["app_info"]
        title = click.style("App Name        : ", fg="blue") + click.style(
                "{}".format(app_info["title"]))
        up_status = click.style("Status          : ", fg="blue")
        if app_info["is_up"]:
            up_status += click.style("Up")
        else:
            up_status += click.style("Down")

        last_crawl_str = datetime.datetime.fromtimestamp(
                app_info["last_crawl"]).strftime("%Y-%m-%d %H:%M")

        last_crawl = click.style("Last Crawl Time : ", fg="blue") + click.style(
                "{}".format(last_crawl_str))
        version = click.style("Version         : ", fg="blue") + click.style(
                "{}".format(app_info["version"]))

        last_updated_str = datetime.datetime.fromtimestamp(
                app_info["updated"]).strftime("%Y-%m-%d %H:%M")
        last_update = click.style("Last Update     : ", fg="blue") + click.style(
                "{}".format(last_updated_str))

        availability = click.style("Availability    : ", fg="blue") + click.style(
                "{:.2f}%".format(app_info["average_uptime"] * 100))

        app_url = click.style("App URL         : ", fg="blue") + click.style(
                "{}".format(app_info["app_url"]))
        category = click.style("Category        : ", fg="blue") + click.style(
                "{}".format(app_info["category"]))
        keywords = click.style("Keywords        : ", fg="blue") + click.style(
                "{}".format(', '.join(app_info["keywords"])))
        desc = click.style("Description     : ", fg="blue") + click.style(
                "{}".format(app_info["description"]))
        price = click.style("Price Range     : ", fg="blue") + click.style(
                "{} - {} Satoshis").format(
                app_info["min_price"], app_info["max_price"])
        doc_url = click.style("Docs URL        : ", fg="blue") + click.style(
                "{}".format(app_info["docs_url"]))
        manifest_url = click.style("Manifest URL    : ", fg="blue") + click.style(
                "{}".format(app_info["manifest_url"]))

        quick_start = click.style("Quick Start\n\n", fg="blue") + click.style(
                app_info["quick_buy"])

        usage_docs = click.style("Detailed usage\n\n", fg="blue") + click.style(
                app_info["usage_docs"])

        final_str = "\n".join(
                [title, "\n",
                 up_status, availability, last_crawl, last_update, version, "\n",
                 desc, app_url, doc_url, manifest_url, "\n",
                 category, keywords, price, "\n", quick_start, "\n", usage_docs, "\n\n"])
        config.echo_via_pager(final_str)

    except ServerRequestError as e:
        if e.status_code == 404:
            click.secho(UxString.app_does_not_exist.format(app_id))
        else:
            raise e


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
    try:
        return zerotier.get_address_for_network(marketplace)
    except ValueError as e:
        click.secho(UxString.no_zt_network.format(marketplace, UxString.join_cmd))
        raise e
