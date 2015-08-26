import click
from two1.config import pass_config
from two1.config import TWO1_HOST
from two1.lib import rest_client
from two1.bitcoin.crypto import PrivateKey

@click.command()
@pass_config
@click.argument('query', nargs=1)
def search(config, query, reverse=False):
    "Search the Many Machine Market (MMM)"
    print("Searching the MMM for %s" % query)
    # create a rest client with a dummy private key because we are using all unsigned get requests
    mining_rest_client = rest_client.MiningRestClient(PrivateKey.from_random(), TWO1_HOST)
    mining_rest_client.get_and_print_all_search_pages(query)
    return query
