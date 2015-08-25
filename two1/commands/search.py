import click
from two1.config import pass_config
from two1.config import TWO1_HOST
from two1.lib.rest_client import TwentyOneRestClient
from two1.bitcoin.crypto import PrivateKey

@click.command()
@pass_config
@click.argument('query', nargs=1)
def search(config, query, reverse=False):
    "Search the Many Machine Market (MMM)"
    print("Searching the MMM for %s" % query)
    # create a rest client without a private key 
    # because we are using all unsigned get requests
    rest_client = TwentyOneRestClient(TWO1_HOST)
    page_num = 1
    parsed = rest_client.mmm_search(query,page_num)
    if len(parsed["data"]) == 0:
        print('No results found for query "{}"'.format(query))
    else:
        # print all the pages of search results
        while len(parsed["data"]) > 0:
            show_search_results_page(parsed["data"])
            #if more pages
            if parsed["pages"]["current_page"] < parsed["pages"]["total_pages"]:
                page_num += 1
                parsed = rest_client.mmm_search(query, page_num)
            else:
                break

def show_search_results_page(self, data):
    for sell in data:
        print("{} by user {}".format(sell["name"], sell["username"]))
        print("\tDescription: {}".format(sell["description"]))
        print("\tRating: {}".format(sell["rating"]))
        print("\tPrice: {}".format(sell["price"]))
