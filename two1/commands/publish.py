""" Two1 command to publish an app to the 21 Marketplace """
from urllib.parse import urlparse
import copy
import functools
import logging
import os
import re

from tabulate import tabulate
from yaml.error import YAMLError
import click
import yaml

from two1 import util
from two1.commands.search import get_next_page
from two1.commands.util import decorators
from two1.commands.util import exceptions
from two1.commands.util import uxstring
from two1.commands.util import zerotier
from two1.commands.util.exceptions import ServerRequestError
from two1.commands.util.exceptions import UnloggedException


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.group()
def publish():
    """Publish apps to the 21 Marketplace.

\b
Usage
_____
Publish your app to the 21 Marketplace.
$ 21 publish submit path_to_manifest/manifest.yaml
To update your published listing, run the above command after modifying your manifest.yaml.

\b
Publish your app to the 21 Marketplace without strict checking of the manifest against your current IP.
$ 21 publish submit -s path_to_manifest/manifest.yaml


\b
See the help for submit.
$ 21 publish submit --help


\b
View all of your published apps.
$ 21 publish list

\b
See the help for list.
$ 21 publish list --help

\b
Remove one of your published apps from the marketplace.
$ 21 publish remove {app_id}


\b
See the help for remove.
$ 21 publish remove --help

    """
    pass


@publish.command()
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def list(ctx):
    """

\b
Lists all your published apps.
$ 21 publish list

Results from the list command are paginated.
Use 'n' to move to the next page and 'p' to move to the previous page.
You can view detailed admin information about an app by specifying it's id
at the prompt.
    """
    # pylint: disable=redefined-builtin
    _list_apps(ctx.obj['config'], ctx.obj['client'])


@publish.command()
@click.argument('app_id')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def remove(ctx, app_id):
    """
\b
Removes a published app from the Marketplace.
$ 21 publish remove {app_id}

\b
The {app_id} can be obtained by performing:
$ 21 publish list
    """
    _delete_app(ctx.obj['config'], ctx.obj['client'], app_id)


@publish.command()
@click.argument('manifest_path', type=click.Path(exists=False))
@click.option('-m', '--marketplace', default='21mkt',
              help="Selects the marketplace for publishing.")
@click.option('-s', '--skip', is_flag=True, default=False,
              help='Skips the strict checking of the manifest against your current ip.')
@click.option('-p', '--parameters', default=None,
              help='Overrides manifest parameters.')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def submit(ctx, manifest_path, marketplace, skip, parameters):
    """
\b
Publishes an app to 21 Marketplace.
$ 21 publish submit path_to_manifest/manifest.yaml

The contents of the manifest file should follow the guidelines specified at
https://21.co/learn/21-publish .

Before publishing, make sure that you've joined the 21 Marketplace by running the `21 join` command.

\b
Publishes an app to 21 Marketplace but overrides the specified fields in the existing manifest.
$ 21 publish submit path_to_manifest/manifest.yaml -p 'title="My App Title" price="2500" host="AUTO"'

\b
Available fields for override:
title       : The title of the app.
description : The description of the app.
price       : The price for each call to your app.
name        : The name of the app publisher.
email       : The email of the app publisher.
host        : The IP address or hostname of the machine hosting the app.
              If you provide AUTO as a value for this field, your 21market IP
              will be automatically detected and added to the manifest.
port        : The port on which the app is running.
    """
    if parameters is not None:
        try:
            parameters = _parse_parameters(parameters)
        except:
            logger.error(
                "Manifest parameter overrides should be in the form 'key1=\"value1\" "
                "key2=\"value2\".",
                fg="red")
            return

    _publish(ctx.obj['client'], manifest_path, marketplace, skip, parameters)


def _parse_parameters(parameters):
    """ Parses parameters string and returns a dict of overrides.

    This function assumes that parameters string is in the form of '"key1="value1" key2="value2"'.
    Use of single quotes is optional but is helpful for strings that contain spaces.

    Args:
        parameters (str): A string in the form of '"key="value" key="value"'.

    Returns:
        dict: A dict containing key/value pairs parsed from the parameters string.

    Raises:
        ValueError: if the parameters string is malformed.
    """

    if not re.match(r'^(\w+)="([^=]+)"(\s{1}(\w+)="([^=]+)")*$', parameters):
        raise ValueError

    # first we add tokens that separate key/value pairs.
    # in case of key='ss  sss  ss', we skip tokenizing when we se the first single quote
    # and resume when we see the second
    replace_space = True
    tokenized = ""
    for c in parameters:
        if c == '\"':
            replace_space = not replace_space
        elif c == ' ' and replace_space:
            tokenized += "$$"
        else:
            tokenized += c

    # now get the tokens
    tokens = tokenized.split('$$')
    result = {}
    for token in tokens:
        # separate key/values
        key_value = token.split("=")
        result[key_value[0]] = key_value[1]
    return result


def _list_apps(config, client):
    """ Lists all apps that have been published to the 21 marketplace

    Args:
        config (Config): config object used for getting .two1 information.
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
    """
    logger.info("Listing all the published apps by {}: ".format(config.username), fg="green")
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
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        app_id (str): a unique string that identifies the application.
    """
    if click.confirm("Are you sure that you want to delete the app with id '{}'?".format(app_id)):
        try:
            resp = client.delete_app(config.username, app_id)
            resp_json = resp.json()
            deleted_title = resp_json["deleted_title"]
            logger.info("App {} ({}) was successfully removed from the marketplace.".format(app_id, deleted_title))
        except ServerRequestError as e:
            if e.status_code == 404:
                logger.info("The app with id '{}' does not exist in the marketplace.".format(app_id), fg="red")
            elif e.status_code == 403:
                logger.info(
                    "You don't have permission to delete the app with id '{}'. You "
                    "can only delete apps that you have published.".format(app_id), fg="red")


def _publish(client, manifest_path, marketplace, skip, overrides):
    """ Publishes application by uploading the manifest to the given marketplace

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        manifest_path (str): the path to the manifest file.
        marketplace (str): the zerotier marketplace name.
        skip (bool): skips strict checking of manifest file.
        overrides (dict): Dictionary containing the key/value pairs will be overridden
        in the manifest.

    Raises:
        ValidationError: if an error occurs while parsing the manifest file
    """
    try:
        manifest_json = check_app_manifest(manifest_path, overrides, marketplace)
        app_url = "{}://{}".format(manifest_json["schemes"][0], manifest_json["host"])
        app_ip = urlparse(app_url).hostname

        if not skip:
            address = get_zerotier_address(marketplace)

            if address != app_ip:
                wrong_ip = click.style("It seems that the IP address that you put in your manifest file (") +\
                           click.style("{}", bold=True) +\
                           click.style(") is different than your current 21market IP (") +\
                           click.style("{}", bold=True) +\
                           click.style(")\nAre you sure you want to continue publishing with ") +\
                           click.style("{}", bold=True) +\
                           click.style("?")
                if not click.confirm(wrong_ip.format(app_ip, address, app_ip)):
                    switch_host = click.style("Please edit ") +\
                                  click.style("{}", bold=True) +\
                                  click.style(" and replace ") +\
                                  click.style("{}", bold=True) +\
                                  click.style(" with ") +\
                                  click.style("[{}].", bold=True)
                    logger.info(switch_host.format(manifest_path, app_ip, address))
                    return

    except exceptions.ValidationError as ex:
        # catches and re-raises the same exception to enhance the error message
        publish_docs_url = click.style("https://21.co/learn/21-publish/", bold=True)
        publish_instructions = "For instructions on publishing your app, please refer to {}".format(publish_docs_url)
        raise exceptions.ValidationError(
            "The following error occurred while reading your manifest file at {}:\n{}\n\n{}"
            .format(manifest_path, ex.args[0], publish_instructions),
            json=ex.json)

    app_name = manifest_json["info"]["title"]
    app_endpoint = "{}://{}{}".format(manifest_json["schemes"][0],
                                      manifest_json["host"],
                                      manifest_json["basePath"])

    logger.info(
        (click.style("Publishing {} at ") + click.style("{}", bold=True) + click.style(" to {}."))
        .format(app_name, app_endpoint, marketplace))
    payload = {"manifest": manifest_json, "marketplace": marketplace}
    try:
        response = client.publish(payload)
    except ServerRequestError as e:
        if e.status_code == 403 and e.data.get("error") == "TO600":
            logger.info(
                "The endpoint {} specified in your manifest has already been registered in "
                "the marketplace by another user.\nPlease check your manifest file and make "
                "sure your 'host' field is correct.\nIf the problem persists please contact "
                "support@21.co.".format(app_endpoint), fg="red")
            return
        else:
            raise e

    if response.status_code == 201:
        response_data = response.json()
        mkt_url = response_data['mkt_url']
        permalink = response_data['permalink']
        logger.info(
            click.style(
                "\n"
                "You have successfully published {} to {}. "
                "You should be able to view the listing within a few minutes at {}\n\n"
                "Users will be able to purchase it, using 21 buy, at {} ",
                fg="magenta")
            .format(app_name, marketplace, permalink, mkt_url)
        )


def get_search_results(config, client, page):
    """ Queries the marketplace for published apps

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api.
        page (int): the page number used in querying the paginated marketplace api.

    Returns:
        int: the total number of pages returned by the server
    """
    resp = client.get_published_apps(config.username, page)
    resp_json = resp.json()
    search_results = resp_json["results"]
    if search_results is None or len(search_results) == 0:
        logger.info(
            click.style("You haven't published any apps to the marketplace yet. Use ", fg="blue") +
            click.style("21 publish submit {PATH_TO_MANIFEST_FILE}", bold=True, fg="blue") +
            click.style(" to publish your apps to the marketplace.", fg="blue"), fg="blue")
        return 0

    total_pages = resp_json["total_pages"]
    logger.info("\nPage {}/{}".format(page + 1, total_pages), fg="green")
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
                     util.format_date(r["last_update"])])

    logger.info(tabulate(rows, headers, tablefmt="simple"))

    return total_pages


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
            last_crawl_str = util.format_date(app_info["last_crawl"])

        last_crawl = click.style("Last Crawl Time : ", fg="blue") + click.style(
            "{}".format(last_crawl_str))
        version = click.style("Version         : ", fg="blue") + click.style(
            "{}".format(app_info["version"]))

        last_updated_str = util.format_date(app_info["updated"])
        last_update = click.style("Last Update     : ", fg="blue") + click.style(
            "{}".format(last_updated_str))

        availability = click.style("Availability    : ", fg="blue") + click.style(
            "{:.2f}%".format(app_info["average_uptime"] * 100))

        app_url = click.style("Public App URL  : ", fg="blue") + click.style(
            "{}".format(app_info["app_url"]))
        original_url = click.style("Private App URL : ", fg="blue") + click.style(
            "{}".format(app_info["original_url"]))
        category = click.style("Category        : ", fg="blue") + click.style(
            "{}".format(app_info["category"]))

        desc = click.style("Description     : ", fg="blue") + click.style(
            "{}".format(app_info["description"]))
        price = click.style("Price Range     : ", fg="blue") + click.style(
            "{} - {} Satoshis").format(
                app_info["min_price"], app_info["max_price"])
        doc_url = click.style("Docs URL        : ", fg="blue") + click.style(
            "{}".format(app_info["docs_url"]))

        quick_start = click.style("Quick Start\n\n", fg="blue") + click.style(
            app_info["quick_buy"])

        usage_docs = None
        if "usage_docs" in app_info:
            usage_docs = click.style("Detailed usage\n\n", fg="blue") + click.style(
                app_info["usage_docs"])

        page_components = [title, "\n",
                           rating_row, up_status, availability, last_crawl, last_update, version,
                           "\n",
                           desc, app_url, original_url, doc_url, "\n",
                           category, price, "\n", quick_start, "\n"]
        if usage_docs:
            page_components.append(usage_docs + "\n")
        final_str = "\n".join(page_components)
        logger.info(final_str, pager=True)

    except ServerRequestError as e:
        if e.status_code == 404:
            logger.info(
                "The specified id for the app ({}) does not match any apps in the "
                "marketplace.".format(app_id))
        else:
            raise e


def check_app_manifest(api_docs_path, overrides, marketplace):
    """ Runs validate_manifest and handles any errors that could occur

    Args:
        api_docs_path (str): path to the manifest file
        overrides (dict): Dictionary containing the key/value pairs will be overridden
        in the manifest.
        marketplace (str): the marketplace name

    Raises:
        ValidationError: If manifest is not valid, bad, missing, is a directory, or too large
    """
    if not os.path.exists(api_docs_path):
        raise exceptions.ValidationError(
            click.style("Could not find the manifest file at {}.", fg="red").format(api_docs_path))

    if os.path.isdir(api_docs_path):
        raise exceptions.ValidationError(
            click.style("{} is a directory. Please enter the direct path to the manifest file.",
                        fg="red").format(api_docs_path))

    file_size = os.path.getsize(api_docs_path) / 1e6
    if file_size > 2:
        raise exceptions.ValidationError(
            click.style("The size of the manifest file at {} exceeds the maximum limit of 2MB.", fg="red")
            .format(api_docs_path))

    try:
        with open(api_docs_path, "r") as f:
            original_manifest_dict = yaml.load(f.read())

        manifest_dict = transform_manifest(original_manifest_dict, overrides, marketplace)

        # write back the manifest in case some clean up or overriding has happend
        with open(api_docs_path, "w") as f:
            yaml.dump(manifest_dict, f)

        return manifest_dict
    except (YAMLError, ValueError):
        raise exceptions.ValidationError(
            click.style("Your manifest file at {} is not valid YAML.", fg="red")
            .format(api_docs_path))


def transform_manifest(manifest_dict, overrides, marketplace):
    # empty yaml files do not raise an error, so do it here
    if not manifest_dict:
        raise YAMLError

    manifest_dict = copy.deepcopy(manifest_dict)

    manifest_dict = clean_manifest(manifest_dict)

    manifest_dict = apply_overrides(manifest_dict, overrides, marketplace)

    manifest_dict = replace_auto(manifest_dict, marketplace)

    validate_manifest(manifest_dict)

    return manifest_dict


def clean_manifest(manifest_json):
    """ cleans up possible errors in the user manifest.

    Args:
        manifest_json (dict): dict representation of user manifest.

    Returns:
        dict: The user manifest with its possible errors fixed.
    """
    manifest_json = copy.deepcopy(manifest_json)
    host = manifest_json["host"]
    host = host.strip("/").lstrip("http://").lstrip("https://")
    manifest_json["host"] = host
    return manifest_json


def apply_overrides(manifest_json, overrides, marketplace):
    """ Overrides fields in the manifest file.

    Args:
        manifest_json (dict): a json dict of the entire manifest
        overrides (dict): a json dict of override parameters. If this dict contains invalid
        marketplace (str): the marketplace name

    Raises:
        UnloggedException: if the marketplace doesn't exist
        ValidationError: if a non-integer is passed as the price or port parameter.

    Returns:
        dict: a json dict of the manifest with fields overridden.
    """
    manifest_json = copy.deepcopy(manifest_json)
    if overrides is None:
        return manifest_json

    if "title" in overrides:
        manifest_json["info"]["title"] = overrides["title"]
    if "description" in overrides:
        manifest_json["info"]["description"] = overrides["description"]
    if "price" in overrides:
        invalid_price_format = "Price should be a non-negative integer."
        try:
            price = int(overrides["price"])
            manifest_json["info"]["x-21-total-price"]["min"] = price
            manifest_json["info"]["x-21-total-price"]["max"] = price
            if price < 0:
                raise exceptions.ValidationError(invalid_price_format)
        except ValueError:
            raise exceptions.ValidationError(invalid_price_format)
    if "name" in overrides:
        manifest_json["info"]["contact"]["name"] = overrides["name"]
    if "email" in overrides:
        manifest_json["info"]["contact"]["email"] = overrides["email"]
    if "host" in overrides:
        manifest_json["host"] = overrides["host"]
    if "port" in overrides:
        host = manifest_json["host"]
        # if the host is in the form of https://x.com/ remove the trailing slash
        host = host.strip("/")
        invalid_port_format = "Port should be an integer between 0 and 65536."
        try:
            port = int(overrides["port"])
            if port <= 0 or port > 65536:
                raise exceptions.ValidationError(invalid_port_format)
        except ValueError:
            raise exceptions.ValidationError(invalid_port_format)
        host += ":{}".format(port)
        manifest_json["host"] = host
    if "basePath" in overrides:
        manifest_json["basePath"] = overrides["basePath"]

    return manifest_json


def replace_auto(manifest_dict, marketplace):
    """
    Replace "AUTO" in the host and quick-buy with the ZeroTier IP.

    The server subsequently replaces, in the displayed quick-buy,
    instances of the manifest host value with a mkt.21.co address.
    """
    manifest_dict = copy.deepcopy(manifest_dict)

    def get_formatted_zerotier_address(marketplace):
        host = get_zerotier_address(marketplace)
        if "." not in host:
            return "[{}]".format(host)
        else:
            return host
    if 'AUTO' in manifest_dict['host']:
        manifest_dict['host'] = manifest_dict['host'].replace(
            'AUTO', get_formatted_zerotier_address(marketplace))
    if 'AUTO' in manifest_dict['info']['x-21-quick-buy']:
        manifest_dict['info']['x-21-quick-buy'] = manifest_dict['info']['x-21-quick-buy'].replace(
            'AUTO', get_formatted_zerotier_address(marketplace))
    return manifest_dict


def validate_manifest(manifest_json):
    """ Validates the manifest file

        Ensures that the required fields in the manifest are present and valid

    Args:
        manifest_json (dict): a json dict of the entire manifest

    Raises:
        ValueError: if a required field is not valid or present in the manifest
    """
    manifest_json = copy.deepcopy(manifest_json)
    for field in ["schemes", "host", "basePath", "info"]:
        if field not in manifest_json:
            raise exceptions.ValidationError(
                click.style("Field '{}' is missing from the manifest file.", fg="red").format(field),
                json=manifest_json)

    for field in ["contact", "title", "description", "x-21-total-price", "x-21-quick-buy", "x-21-category"]:
        if field not in manifest_json["info"]:
            raise exceptions.ValidationError(
                click.style(
                    "Field '{}' is missing from the manifest file under the 'info' section.",
                    fg="red").format(field),
                json=manifest_json)

    for field in {"name", "email"}:
        if field not in manifest_json["info"]["contact"]:
            raise exceptions.ValidationError(
                click.style(
                    "Field '{}' is missing from the manifest file under the 'contact' section.", fg="red")
                .format(field),
                json=manifest_json)

    for field in ["min", "max"]:
        if field not in manifest_json["info"]["x-21-total-price"]:
            raise exceptions.ValidationError(
                click.style("Field '{}' is missing from the manifest file under the "
                            "'x-21-total-price' section.",
                            fg="red"),
                json=manifest_json)

    if len(manifest_json["schemes"]) == 0:
        raise exceptions.ValidationError(
            click.style(
                "You have to specify either HTTP or HTTPS for your endpoint under the "
                "`schemes` section.",
                fg="red"),
            json=manifest_json)

    valid_app_categories = {'blockchain', 'entertainment', 'social', 'markets', 'utilities', 'iot'}
    if manifest_json["info"]["x-21-category"].lower() not in valid_app_categories:
        valid_categories = ", ".join(valid_app_categories)
        raise exceptions.ValidationError(
            click.style("'{}' is not a valid category for the 21 marketplace. Valid categories are {}.",
                        fg="red").format(
                            manifest_json["info"]["x-21-category"], valid_categories),
            json=manifest_json)


@functools.lru_cache()
def get_zerotier_address(marketplace):
    """ Gets the zerotier IP address from the given marketplace name

    Args:
        marketplace (str): name of the marketplace network to lookup ip

    Returns:
        str: a string representation of the zerotier IP address

    Raises:
        UnloggedException: if the zt network doesn't exist
    """
    logger.info("You might need to enter your superuser password.")
    address = zerotier.get_address(marketplace)
    if not address:
        join_cmd = click.style("21 join", bold=True, reset=False)
        no_zt_network = click.style(
            "You are not part of the {}. Use {} to join the market.",
            fg="red")
        raise UnloggedException(no_zt_network.format(marketplace, join_cmd))

    return address
