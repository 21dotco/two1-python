import click
from tabulate import tabulate
from two1.commands.config import TWO1_HOST
from two1.lib.server.rest_client import ServerRequestError
from two1.commands.config import pass_config
from two1.commands.config import TWO1_API_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.server.rest_client import TwentyOneRestClient


def search_lib(query="", order=None, detail=False, silent=False):
    rest_client = TwentyOneRestClient(TWO1_API_HOST)
    listings = rest_client.search(query, detail=detail)
    if order is not None and order in listings[0]._fields:
        listings = sorted(listings, key=lambda xx: getattr(xx, order))
    if not silent:
        click.echo(tabulate(listings, headers="keys", tablefmt="psql"))
    return listings


@click.command()
@pass_config
@click.option('--query', default="", nargs=1,
              help="Search listings on the Many Machine Market")
@click.option('--order', default=None,
              help="Column to order search results")
@click.option('--detail', default=False, is_flag=True,
              help="Return detailed results with parameter information")
@click.option('--silent', default=False, is_flag=True,
              help="Do not echo results to the command line")
def search(config, query, order, detail, silent):
    "Search the Many Machine Market (MMM)."
    search_lib(query, order, detail, silent)
