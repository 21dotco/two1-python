# standard python imports
import datetime
from textwrap import wrap

# 3rd party imports
import click
from tabulate import tabulate

# two1 imports
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.util.decorators import json_output
from two1.lib.util.uxstring import UxString
from two1.lib.server import rest_client


@click.command("search")
@click.pass_context
@click.argument('search_string', required=False)
@json_output
def search(config, search_string=None):
    """Search for app on the 21 Marketplace.

\b
Usage
-----
View all the apps in the marketplace
$ 21 search

\b
Search for specific keywords or terms
$ 21 search "games social"

\b
Search for all the apps from a particular user
$ 21 search "snakamoto"

Results from the search command are paginated.
Use 'n' to move to the next page and 'p' to move to the previous page.

You can view detailed information about an app by specifying it's id
at the prompt.

    """
    _search(config, search_string)


@capture_usage
def _search(config, search_string):
    """ Searches the marketplace for apps by the given search_string

        Apps are then displayed in a pager in which the user can get more
        info on a selected app.

    Args:
        config (Config): config object used for getting .two1 information
        search_string (str): string used to search for apps
    """
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)
    if search_string is None:
        click.secho(UxString.list_all, fg="green")

    current_page = 0
    total_pages = get_search_results(client, search_string, current_page)
    if total_pages < 1:
        return

    while 0 <= current_page < total_pages:
        try:
            prompt_resp = click.prompt(UxString.pagination,
                                       type=str)
            next_page = get_next_page(prompt_resp, current_page)
            if next_page == -1:
                model_id = prompt_resp
                display_search_info(config, client, model_id)
            elif next_page >= total_pages or next_page < 0:
                continue
            else:
                get_search_results(client, search_string, next_page)
                current_page = next_page

        except click.exceptions.Abort:
            return


def get_search_results(rest_client, search_string, page):
    """ Uses the rest client to get search results in a paginated format

    Args:
        client (TwentyOneRestClient): rest client used for communication with the backend api
        search_string (str): string used to search for apps

    Returns:
        int: the total number of pages returned by the server
    """
    resp = rest_client.search(search_string, page)
    if resp.ok:
        resp_json = resp.json()
        search_results = resp_json["results"]
        if search_results is None or len(search_results) == 0:
            if search_string:
                click.secho(UxString.empty_listing.format(search_string))
            else:
                click.secho(UxString.no_app_in_marketplace)

            return 0

        total_pages = resp_json["total_pages"]
        click.secho("\nPage {}/{}".format(page + 1, total_pages), fg="green")
        content = market_search_formatter(search_results, page)
        click.echo(content)
        return total_pages
    else:
        raise ServerRequestError()


MAX_PAGE_SIZE = 10


def market_search_formatter(search_results, current_page):
    """ Formats the search results into a tabular paginated format

    Args:
        search_results (list): a list of results in dict format returned from the REST API
        current_page (int): current page used to go to next or previous pages

    Returs:
        str: formatted results in tabular format
    """
    headers = ["id", "Details", "Creator", "price range", "category", "rating"]
    import pdb; pdb.set_trace()
    rows = []
    for i, item in enumerate(search_results):
        id = item["id"]
        price_range = click.style("{} - {} Satoshis".format(item["min_price"],
                                                            item["max_price"]), fg="blue")

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
        rows.append([id, title, creator, price_range, category, rating])
        rows.append(["", "", "", "", "", ""])
        for indx, l in enumerate(wrap(item["description"])):
            rows.append(["", l, "", "", "", ""])
        rows.append(["", "", "", "", "", ""])

    return tabulate(rows, headers=headers, tablefmt="psql")


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
        return current_page - 1
    elif prompt_response.lower() in ["q", "cancel", "c"]:
        raise click.exceptions.Abort()
    else:
        return -1


def display_search_info(config, client, listing_id):
    """ Given a listing id, format and print detailed information to the command line

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api
        listing_id (str): unique marketplace listing id

    Raises:
        ServerRequestError: If server returns an error code other than a 404
    """
    try:
        resp = client.get_listing_info(listing_id)
    except ServerRequestError as e:
        if e.status_code == 404:
            click.secho(UxString.app_does_not_exist.format(listing_id))
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
    keywords = click.style("Keywords     : ", fg="blue") + click.style(
        "{}".format(', '.join(result_json["keywords"])))
    version = click.style("Version      : ", fg="blue") + click.style(
        "{}".format(result_json["version"]))
    last_updated_str = datetime.datetime.fromtimestamp(
        result_json["updated"]).strftime("%Y-%m-%d %H:%M")
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

    usage_docs = click.style("Detailed usage\n\n", fg="blue") + click.style(
        result_json["usage_docs"])

    final_str = "\n".join(
        [title, desc, created_by, price, rating, "\n",
         is_active, availability, "\n",
         doc_url, app_url, "\n",
         category, keywords, version, last_update, "\n",
         quick_start, "\n",
         usage_docs, "\n\n"])
    config.echo_via_pager(final_str)
