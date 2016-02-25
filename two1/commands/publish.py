# standard python imports
import os
import datetime
from urllib.parse import urlparse

# 3rd partyimports
import click
import yaml
from yaml.error import YAMLError
from tabulate import tabulate

# two1 imports
from two1.lib.server import analytics
from two1.lib.server import rest_client
from two1.lib.server.rest_client import ServerRequestError
from two1.commands.util import decorators
from two1.commands.util.exceptions import UnloggedException
from two1.commands.util import uxstring
from two1.commands.util import zerotier
from two1.commands.search import get_next_page


class ValidationError(Exception):
    """ Manifest validation error occurs when parsing manifest file """
    pass


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
@analytics.capture_usage
def list(ctx):
    """
Lists all your published apps.

$ 21 publish list

Results from the list command are paginated.
Use 'n' to move to the next page and 'p' to move to the previous page.

You can view detailed admin information about an app by specifying it's id
at the prompt.
    """
    #pylint: disable=redefined-builtin
    _list_apps(ctx.obj['config'], ctx.obj['client'])


@publish.command()
@click.argument('app_id')
@click.pass_context
@analytics.capture_usage
@decorators.check_notifications
def remove(ctx, app_id):
    """
Removes a published app from the Marketplace.

$ 21 publish remove app_id

The app_id can be obtained by performing:

$ 21 publish list
    """
    _delete_app(ctx.obj['config'], ctx.obj['client'], app_id)


@publish.command()
@click.argument('manifest_path', type=click.Path(exists=False))
@click.option('-m', '--marketplace', default='21market',
              help="Selects the marketplace for publishing")
@click.option('-s', '--skip', is_flag=True, default=False,
              help='Skips the strict checking of the manifest against your current ip.')
@click.pass_context
@analytics.capture_usage
@decorators.check_notifications
def submit(ctx, manifest_path, marketplace, skip):
    """
Submits an app to the Marketplace.

\b
$ 21 publish submit path_to_manifest/manifest.json

The contents of the manifest file should follow the guidelines specified at
https://21.co/publish

Before publishing, make sure that you've joined the 21 marketplace by running the `21 join` command.
    """
    _publish(ctx.obj['config'], ctx.obj['client'], manifest_path, marketplace, skip)


def _list_apps(config, client):
    """ Lists all apps that have been published to the 21 marketplace

    Args:
        config (Config): config object used for getting .two1 information
        client (two1.lib.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
    """
    click.secho(uxstring.UxString.my_apps.format(config.username), fg="green")
    current_page = 0
    total_pages = get_search_results(config, client, current_page)
    if total_pages < 1:
        return

    while 0 <= current_page < total_pages:
        try:
            prompt_resp = click.prompt(uxstring.UxString.pagination,
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


def _delete_app(config, client, app_id):
    """ Deletes an app that has been published to the 21 marketplace

    Args:
        config (Config): config object used for getting .two1 information
        client (two1.lib.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        app_id (str): a unique string that identifies the application
    """
    if click.confirm(uxstring.UxString.delete_confirmation.format(app_id)):
        try:
            resp = client.delete_app(config.username, app_id)
            resp_json = resp.json()
            deleted_title = resp_json["deleted_title"]
            click.secho(uxstring.UxString.delete_success.format(app_id, deleted_title))
        except ServerRequestError as e:
            if e.status_code == 404:
                click.secho(uxstring.UxString.delete_app_not_exist.format(app_id), fg="red")
            elif e.status_code == 403:
                click.secho(uxstring.UxString.delete_app_no_permissions.format(app_id), fg="red")


def _publish(config, client, manifest_path, marketplace, skip):
    """ Publishes application by uploading the manifest to the given marketplace

    Args:
        config (Config): config object used for getting .two1 information
        client (two1.lib.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        manifest_path (str): the path to the manifest file
        marketplace (str): the zerotier marketplace name
        skip (bool): skips strict checking of manifest file
    """
    try:
        manifest_json = check_app_manifest(manifest_path)
        app_url = urlparse(manifest_json["host"])
        app_ip = app_url.path.split(":")[0]

        if not skip:
            address = get_zerotier_address(marketplace)

            if address != app_ip:
                if not click.confirm(uxstring.UxString.wrong_ip.format(app_ip, address, app_ip)):
                    click.secho(uxstring.UxString.switch_host.format(manifest_path, app_ip, address))
                    return

    except ValueError:
        return
    except ValidationError as e:
        click.secho(
            uxstring.UxString.bad_manifest.format(manifest_path, e.args[0], uxstring.UxString.publish_docs_url),
            fg="red")
        return

    app_name = manifest_json["info"]["title"]
    app_endpoint = "{}://{}{}".format(manifest_json["schemes"][0],
                                      manifest_json["host"],
                                      manifest_json["basePath"])

    click.secho(uxstring.UxString.publish_start.format(app_name, app_endpoint, marketplace))
    payload = {"manifest": manifest_json, "marketplace": marketplace}
    response = client.publish(payload)
    if response.status_code == 201:
        click.secho(uxstring.UxString.publish_success.format(app_name, marketplace))


def get_search_results(config, client, page):
    """ Queries the marketplace for published apps

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api
        page (int): the page number used in querying the paginated marketplace api

    Returns:
        int: the total number of pages returned by the server
    """
    resp = client.get_published_apps(config.username, page)
    if resp.ok:
        resp_json = resp.json()
        search_results = resp_json["results"]
        if search_results is None or len(search_results) == 0:
            click.secho(uxstring.UxString.no_published_apps, fg="blue")
            return 0

        total_pages = resp_json["total_pages"]
        click.secho("\nPage {}/{}".format(page + 1, total_pages), fg="green")
        headers = ["id", "Title", "Url", "Rating", "Is up", "Is healthy", "Average Uptime",
                   "Last Update"]
        rows = []
        for r in search_results:
            rating = "Not yet Rated"
            if r["rating_count"] > 0:
                rating = "{:.1f} ({} rating".format(r["average_rating"],
                                                    int(r["rating_count"]))
                if r["rating_count"] > 1:
                    rating += "s"
                rating += ")"
            rows.append([r["id"],
                         r["title"],
                         r["app_url"],
                         rating,
                         str(r["is_up"]),
                         str(r["is_healthy"]),
                         "{:.2f}%".format(r["average_uptime"] * 100),
                         datetime.datetime.fromtimestamp(r["last_update"]).strftime(
                             "%Y-%m-%d %H:%M")])

        click.echo(tabulate(rows, headers, tablefmt="grid"))

        return total_pages
    else:
        raise ServerRequestError()


def display_app_info(config, client, app_id):
    """ Displays info about the application selected

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api

    Raises:
        ServerRequestError: if server returns an error code other than 404
    """
    try:
        resp = client.get_app_full_info(config.username, app_id)
        result = resp.json()
        app_info = result["app_info"]
        title = click.style("App Name        : ", fg="blue") + click.style(
            "{}".format(app_info["title"]))

        if app_info["rating_count"] == 0:
            rating = "Not yet rated"
        else:
            rating = "{:.1f} ({} rating".format(app_info["average_rating"],
                                                int(app_info["rating_count"]))
            if app_info["rating_count"] > 1:
                rating += "s"
            rating += ")"
        rating_row = click.style("Rating          : ", fg="blue") + click.style("{}".format(rating))
        up_status = click.style("Status          : ", fg="blue")
        if app_info["is_up"]:
            up_status += click.style("Up")
        else:
            up_status += click.style("Down")

        last_crawl_str = "Not yet crawled"
        if "last_crawl" in app_info:
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
             rating_row, up_status, availability, last_crawl, last_update, version, "\n",
             desc, app_url, doc_url, manifest_url, "\n",
             category, keywords, price, "\n", quick_start, "\n", usage_docs, "\n\n"])
        config.echo_via_pager(final_str)

    except ServerRequestError as e:
        if e.status_code == 404:
            click.secho(uxstring.UxString.app_does_not_exist.format(app_id))
        else:
            raise e


def check_app_manifest(api_docs_path):
    """ Runs validate_manifest and handles any errors that could occur

    Args:
        api_docs_path (str): path to the manifest file

    Raises:
        ValidationError: If manifest is missing, is a directory, or too large
        ValueError: If the manifest is not valid or bad
    """
    if not os.path.exists(api_docs_path):
        raise ValidationError(
            uxstring.UxString.manifest_missing.format(
                api_docs_path, uxstring.UxString.publish_docs_url))

    if os.path.isdir(api_docs_path):
        raise ValidationError(
            uxstring.UxString.manifest_is_directory.format(api_docs_path), fg="red")

    file_size = os.path.getsize(api_docs_path) / 1e6
    if file_size > 2:
        raise ValidationError(
            uxstring.UxString.large_manifest.format(api_docs_path,
                                           uxstring.UxString.publish_docs_url))
    try:
        with open(api_docs_path, "r") as f:
            manifest_dict = yaml.load(f.read())
            validate_manifest(manifest_dict)
            return manifest_dict
    except YAMLError:
        click.secho(uxstring.UxString.malformed_yaml.format(api_docs_path, uxstring.UxString.publish_docs_url), fg="red")
        raise ValueError()
    except ValueError as e:
        click.secho(uxstring.UxString.bad_manifest.format(
            api_docs_path,
            e.args[0],
            uxstring.UxString.publish_docs_url), fg="red")
        raise ValueError()


def validate_manifest(manifest_json):
    """ Validates the manifest file

        Ensures that the required fields in the manifest are present and valid

    Args:
        manifest_json (dict): a json dict of the entire manifest

    Raises:
        ValueError: if a required field is not valid or present in the manifest
    """
    for field in uxstring.UxString.valid_top_level_manifest_fields:
        if field not in manifest_json:
            raise ValidationError(uxstring.UxString.top_level_manifest_field_missing.format(field))

    for field in uxstring.UxString.manifest_info_fields:
        if field not in manifest_json["info"]:
            raise ValidationError(uxstring.UxString.manifest_info_field_missing.format(field))

    for field in uxstring.UxString.price_fields:
        if field not in manifest_json["info"]["x-21-total-price"]:
            raise ValidationError(uxstring.UxString.price_fields_missing.format(field))

    if len(manifest_json["schemes"]) == 0:
        raise ValidationError(uxstring.UxString.scheme_missing)

    if manifest_json["info"]["x-21-category"].lower() not in uxstring.UxString.valid_app_categories:
        valid_categories = ", ".join(uxstring.UxString.valid_app_categories)
        raise ValidationError(uxstring.UxString.invalid_category.format(
            manifest_json["info"]["x-21-category"], valid_categories))


def get_zerotier_address(marketplace):
    """ Gets the zerotier IP address from the given marketplace name

    Args:
        marketplace (str): name of the marketplace network to lookup ip

    Returns:
        str: a string representation of the zerotier IP address

    Raises:
        UnloggedException: if the zt network doesn't exist
    """
    click.secho(uxstring.UxString.update_superuser)
    try:
        return zerotier.get_address_for_network(marketplace)
    except KeyError:
        click.secho(uxstring.UxString.no_zt_network.format(marketplace, uxstring.UxString.join_cmd))
        raise UnloggedException()
