import click
from two1.config import pass_config
from two1.config import TWO1_HOST
from two1.lib.exceptions import ServerRequestError
from two1.lib.rest_client import TwentyOneRestClient

import textwrap

@click.command()
@pass_config
@click.option('--minprice', type=int, help='Minimal resource price in Satoshi')
@click.option('--maxprice', type=int, help='Maximal resource price in Satoshi')
@click.option('--ascending/--descending', is_flag=True, help='Order in descending order')
@click.option('--sort', type=click.Choice(['match', 'seller', 'resource', 'price']), default='match', help='Select sorting method')
@click.option('--page', default=1, help='Page of results')
@click.argument('query', nargs=-1)
def search(config, sort, minprice, maxprice, ascending, page, query):
    """
    Search the Many Machine Market (MMM)

    This command is useful for searching resources that are needed by you

    Example:
        two1 search resource --minprice=2000 --sort=price
    """
    # Preparing params for use
    if len(query) == 0:
        config.log("Enter at least one query", fg='red')
        exit(-1)
    query = ' '.join(query)
    if page < 1:
        config.log("Page number need be at least 1", fg='red')
        exit(-1)

    config.log("\nSearch Query: {}".format(query), fg="magenta")

    # create a rest client without a private key
    # because we are using all unsigned get requests
    rest_client = TwentyOneRestClient(TWO1_HOST)
    try:
        parsed = rest_client.mmm_search(query, page, minprice, maxprice, sort, ascending)
    except ServerRequestError as exc:
        config.log(str(exc), fg='red')
    else:
        if len(parsed['result']) == 0:
            print('No results found for query "{}"'.format(query))
        else:
            # we should not print all pages
            show_search_results_page(config, parsed["result"])


def show_search_results_page(config, data):
    config.log("{:-^40}+{:-^12}".format("", ""))
    config.log("{:<40}|{:^12} ".format("Seller/resource", "Price"))
    config.log("{:-^40}+{:-^12}".format("", ""))
    for sell in data:
        config.log("{:<40.40}|{:>12}".format(sell["username"]+"/"+sell["name"], sell["price"]))
        for l in textwrap.wrap(sell["description"], 40):
            config.log(l)
        config.log("{:-^40}+{:-^12}".format("", ""))
