import datetime

import click
import re
from two1.commands.config import pass_config
from two1.lib.bitcurl.bitrequests import BitRequests

DEFAULT_SELLER_NAME = "---"
URL_REGEXP = re.compile(
    r'^(?:http)s?://'  # http:// or https://
    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


@click.command()
@click.argument('resource', nargs=1)
@click.option('--data', default=None, help="The data/body to send to the seller")
@click.option('--max_price',  default=5000, help="The max amount to pay for the resource")
@click.option('--output', type=click.File('wb'), help="A file to store the seller's response")
@click.option('--input', type=click.File('rb'), help="A file to send to the seller")
@pass_config
def buy(config, resource, data, max_price, output=None, input=None):
    """Buy internet services with Bitcoin
        resource - The digital resource to buy from.

        example: two1 buy en2cn --data {'text':'This is SPARTA'}
    """
    # TODO: Kill logger on non verbose?
    method = "GET"

    # If resource is a URL string then bypass bulk search
    if bool(URL_REGEXP.match(resource)):
        # Direct From ClI
        target_url = resource

        # TODO: Perform search for exact meta data.
        seller = DEFAULT_SELLER_NAME
    else:
        raise ValueError('Endpoint lookup is not implemented!')
        # Run a search
        config.log("Looking for best price for {}...".format(resource))

        # Extract Data from the search results
        target_url = ""
        seller = ""

    # Select HTTP method
    if data or input:
        method = 'POST'

    # Detect Detect Data is raw or file ref
    target_data = None
    if isinstance(data, str):
        try:
            # NOTE: I/O bound?
            target_data = open(data, 'r')
        except OSError:
            target_data = data

    # Catch Error?
    if input:
        files = {'file': (input.name, input)}
    else:
        files = None
    try:
        res = getattr(BitRequests, method.lower())(
            target_url,
            config.wallet,
            data=target_data,
            files=files
            )
    except Exception as e:
        config.log( str(e), fg="red")
        return

    # Output the response text to the console
    if output:
        output.write(res.content)
    else:
        config.log(res.text)

    # Record the transaction
    config.log_purchase(
        s=seller, r=resource, p=res.paid_amount, d=str(datetime.datetime.today()))
