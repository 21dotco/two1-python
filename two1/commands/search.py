""" Two1 command to search the 21 Marketplace """
# standard python imports
from textwrap import wrap
import logging
import json as jsonlib

# 3rd party imports
import click
from tabulate import tabulate

# two1 imports
from two1 import util
from two1.commands.util import exceptions
from two1.commands.util import decorators
from two1.commands.util import uxstring


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command("search")
@click.argument('search_string', default=None, required=False)
@click.option('--json', default=False, is_flag=True, help='Uses JSON output.')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def search(ctx, search_string, json):
    """Search for apps listed on the 21 Marketplace.

\b
Usage
-----
View all the apps in the marketplace.
$ 21 search

\b
Search for specific keywords or terms.
$ 21 search "games social"

\b
Search for all the apps from a particular user.
$ 21 search "snakamoto"

Results from the search command are paginated.
Use 'n' to move to the next page and 'p' to move to the previous page.
You can also enter an app id to view detailed information about the app.

    """
    if json:
        _search_json(ctx.obj['client'], search_string)
    else:
        _search(ctx.obj['client'], search_string)


def _search_json(client, search_string):
    resp = client.search(search_string)
    total_pages = resp.json()['total_pages']
    results = []
    for i in range(total_pages):
        results.extend(client.search(search_string, i).json()['results'])
    logger.info(jsonlib.dumps(results, indent=4, separators=(',', ': ')))


def _search(client, search_string):
    """ Searches the marketplace for apps by the given search_string

        Apps are then displayed in a pager in which the user can get more
        info on a selected app.

        config (Config): Config object used for user specific information
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        wallet (two1.wallet.Wallet): a user's wallet instance

    Args:
        config (Config): config object used for getting .two1 information
        search_string (str): string used to search for apps
    """
    if search_string is None:
        logger.info(uxstring.UxString.list_all, fg="green")

    current_page = 0
    total_pages = get_search_results(client, search_string, current_page)
    if total_pages < 1:
        return

    while 0 <= current_page < total_pages:
        try:
            prompt_resp = click.prompt(uxstring.UxString.pagination,
                                       type=str)
            next_page = get_next_page(prompt_resp, current_page)
            if next_page == -1:
                model_id = prompt_resp
                display_search_info(client, model_id)
            elif next_page >= total_pages or next_page < 0:
                continue
            elif next_page != current_page:
                get_search_results(client, search_string, next_page)
                current_page = next_page

        except click.exceptions.Abort:
            return


def get_search_results(client, search_string, page):
    """ Uses the rest client to get search results in a paginated format

    Args:
        client (TwentyOneRestClient): rest client used for communication with the backend api
        search_string (str): string used to search for apps

    Returns:
        int: the total number of pages returned by the server
    """
    resp = client.search(search_string, page)
    resp_json = resp.json()
    search_results = resp_json["results"]
    if search_results is None or len(search_results) == 0:
        if search_string:
            logger.info(uxstring.UxString.empty_listing.format(search_string))
        else:
            logger.info(uxstring.UxString.no_app_in_marketplace)

        return 0

    total_pages = resp_json["total_pages"]
    logger.info("\nPage {}/{}".format(page + 1, total_pages), fg="green")
    content = market_search_formatter(search_results)
    logger.info(content)
    return total_pages


MAX_PAGE_SIZE = 10


def market_search_formatter(search_results):
    """ Formats the search results into a tabular paginated format

    Args:
        search_results (list): a list of results in dict format returned from the REST API

    Returs:
        str: formatted results in tabular format
    """
    headers = ["id", "Details", "Creator", "Price", "Category", "Rating"]
    rows = []
    for _, item in enumerate(search_results):
        if item["min_price"] != item["max_price"]:
            price_range = click.style("Variable", fg="blue")
        else:
            price_range = click.style("{} Satoshis".format(item["min_price"]),
                                      fg="blue")
        category = click.style("{}".format(item["category"]), fg="blue")
        creator = click.style("{}".format(item["username"]), fg="blue")
        title = click.style(item["title"], fg="blue")
        rating = "Not yet rated"
        if item["rating_count"] != 0:
            rating = "{:.1f} ({} rating".format(item["average_rating"], int(item["rating_count"]))
            if item["rating_count"] > 1:
                rating += "s"
            rating += ")"
        rating = click.style(rating, fg="blue")
        rows.append([item["id"], title, creator, price_range, category, rating])
        for _, l in enumerate(wrap(item["description"])):
            rows.append(["", l, "", "", "", ""])
        rows.append(["", "", "", "", "", ""])

    return tabulate(rows, headers=headers, tablefmt="simple")


def get_next_page(prompt_response, current_page):
    """ Parses user input and determines what page is next to search for

    Args:
        prompt_response (str): user response text
        current_page (int): current page used to determine what the next page is

    Returns:
        int: next page, relative to the current page depending upon user response,
            otherwise -1 if response is unknown
    """
    if prompt_response.lower() in ["n", "next", "f", "forward"]:
        return current_page + 1
    elif prompt_response.lower() in ["p", "previous", 'b', "back"]:
        return max(current_page - 1, 0)
    elif prompt_response.lower() in ["q", "cancel", "c"]:
        raise click.exceptions.Abort()
    else:
        return -1


def display_search_info(client, listing_id):
    """ Given a listing id, format and print detailed information to the command line

    Args:
        client (TwentyOneRestClient): rest client used for communication with the backend api
        listing_id (str): unique marketplace listing id

    Raises:
        ServerRequestError: If server returns an error code other than a 404
    """
    try:
        resp = client.get_listing_info(listing_id)
    except exceptions.ServerRequestError as e:
        if e.status_code == 404:
            logger.info(uxstring.UxString.app_does_not_exist.format(listing_id))
            return
        else:
            raise e
    result_json = resp.json()

    title = click.style("App Name     : ", fg="blue") + click.style(
        "{}".format(result_json["title"]))
    created_by = click.style("Created By   : ", fg="blue") + click.style(
        "{}".format(result_json["username"]))

    desc = click.style("Description  : ", fg="blue") + click.style(
        "{}".format(result_json["description"]))
    price = click.style("Price Range  : ", fg="blue") + click.style(
        "{} - {} Satoshis").format(result_json["min_price"], result_json["max_price"])

    if result_json["rating_count"] == 0:
        rating_str = "Not yet rated"
    else:
        rating_str = "{:.1f} ({} rating".format(result_json["average_rating"],
                                                int(result_json["rating_count"]))
        if result_json["rating_count"] > 1:
            rating_str += "s"
        rating_str += ")"
    rating = click.style("Rating       : ", fg="blue") + click.style("{}".format(rating_str))

    doc_url = click.style("Docs URL     : ", fg="blue") + click.style(
        "{}".format(result_json["website_url"]))
    app_url = click.style("App URL      : ", fg="blue") + click.style(
        "{}".format(result_json["app_url"]))
    category = click.style("Category     : ", fg="blue") + click.style(
        "{}".format(result_json["category"]))
    version = click.style("Version      : ", fg="blue") + click.style(
        "{}".format(result_json["version"]))
    last_updated_str = util.format_date(result_json["updated"])
    last_update = click.style("Last Update  : ", fg="blue") + click.style(
        "{}".format(last_updated_str))
    quick_start = click.style("Quick Start\n\n", fg="blue") + click.style(
        result_json["quick_buy"])
    is_active = click.style("Status       : ", fg="blue")
    if result_json["is_active"] and result_json["is_up"] and result_json["is_healthy"]:
        is_active += click.style("Active")
    else:
        is_active += click.style("Inactive")

    availability = click.style("Availability : ", fg="blue") + click.style(
        "{:.2f}%".format(result_json["average_uptime"] * 100))

    usage_docs = None
    if "usage_docs" in result_json:
        usage_docs = click.style("Detailed usage\n\n", fg="blue") + click.style(
            result_json["usage_docs"])

    pager_components = [title, desc, created_by, price, rating, "\n",
                        is_active, availability, "\n",
                        doc_url, app_url, "\n",
                        category, version, last_update, "\n",
                        quick_start, "\n"]

    if usage_docs:
        pager_components.append(usage_docs + "\n")

    final_str = "\n".join(pager_components)

    logger.info(final_str, pager=True)
