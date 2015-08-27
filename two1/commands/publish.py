import click
from two1.lib import login
from two1.lib.rest_client import TwentyOneRestClient
from two1.config import pass_config
from two1.config import TWO1_HOST


@click.command()
@pass_config
@click.argument('name')
@click.argument('description')
@click.argument('price', type=click.INT)
def publish(config, name, description, price):
    """Publish your endpoint to the MMM"""

    rest_client = TwentyOneRestClient(TWO1_HOST,
                                      login.get_auth_key(),
                                      config.username)

    rest_client.mmm_create_sell(name, description, price)
    config.log("Published {} endpoint. Price: {}".format(name,price))
    # return config
