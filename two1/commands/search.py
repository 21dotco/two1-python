"""
Find machine-payable endpoints on the MMM
"""
import click
from tabulate import tabulate
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
    """Search for a machine-payable endpoint.
    """
    _search(config, search_string)


@capture_usage
def _search(config, search_string):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)
    if search_string is None:
        click.secho(UxString.list_all, fg="green")

    current_page = 0
    total_pages = get_search_results(client, search_string, current_page)
    if total_pages <= 1:
        return

    while 0 <= current_page < total_pages:
        try:
            prompt_resp = click.prompt(UxString.pagination,
                                       type=str)
            try:
                next_page = get_next_page(prompt_resp, current_page)
            except ValueError:
                continue

            if next_page >= total_pages or next_page < 0:
                continue
            else:
                get_search_results(client, search_string, next_page)
                current_page = next_page

        except click.exceptions.Abort:
            return


def get_search_results(rest_client, search_string, page=0):
    resp = rest_client.search(search_string, page)
    if resp.ok:
        resp_json = resp.json()
        search_results = resp_json["results"]
        if search_results is None or len(search_results) == 0:
            click.secho(UxString.empty_listing.format(search_string))
            return 0

        total_pages = resp_json["total_pages"]
        shorten_search_results(search_results)
        click.secho("\nPage {}/{}".format(page + 1, total_pages), fg="green")
        headers = ["id", "title", "description", "price range", "creator", "category"]
        rows = [[r["id"], r["title"], r["description"],
                 "{} - {}".format(r["min_price"], r["max_price"]), r["username"],
                 r["category"]] for r in search_results]
        click.echo(tabulate(rows, headers, tablefmt="grid"))
        return total_pages
    else:
        raise ServerRequestError()


def shorten_search_results(search_result):
    for result in search_result:
        for key, value in result.items():
            if isinstance(value, str) and len(value) > 50:
                result[key] = value[:50] + "..."


def get_next_page(prompt_response, current_page):
    if prompt_response.lower() in ["n", "next"]:
        return current_page + 1
    elif prompt_response.lower() in ["b", "back"]:
        return current_page - 1
    elif prompt_response.lower() in ["c", "cancel"]:
        raise click.exceptions.Abort()
    else:
        raise ValueError()
